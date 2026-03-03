from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app import models, schemas
from app.auth import (
    verify_password, get_password_hash, create_access_token,
    create_password_reset_token, verify_password_reset_token,
    get_current_active_user, require_admin
)
from app.config import settings
from app.services.email_service import EmailService

router = APIRouter()


def _resolve_admin_by_identifier(db: Session, identifier: str):
    """Resolve admin user by email or business_username.
    Usernames are stored with @ prefix (e.g. @Goal_sale). If user enters 'Goal_sale' without @,
    we try '@Goal_sale' when looking up business_username.
    """
    iden = (identifier or "").strip()
    if not iden:
        return None
    # Try exact match as email first
    admin = db.query(models.User).filter(
        models.User.email == iden,
        models.User.is_admin == True
    ).first()
    if admin:
        return admin
    # Try exact match as business_username
    admin = db.query(models.User).filter(
        models.User.business_username == iden,
        models.User.is_admin == True
    ).first()
    if admin:
        return admin
    # Try with @ prefix if identifier doesn't start with @ (e.g. "digital_sales" -> "@digital_sales")
    if not iden.startswith("@"):
        admin = db.query(models.User).filter(
            models.User.business_username == ("@" + iden),
            models.User.is_admin == True
        ).first()
    return admin


@router.post("/signup", response_model=schemas.Token)
def signup(user_data: schemas.UserSignup, db: Session = Depends(get_db)):
    """Sign up a new user. First user becomes admin."""
    existing_admin = db.query(models.User).filter(
        models.User.email == user_data.email,
        models.User.is_admin == True
    ).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered as admin"
        )
    if user_data.business_username:
        existing_username = db.query(models.User).filter(
            models.User.business_username == user_data.business_username,
            models.User.is_admin == True
        ).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business username already taken"
            )
    
    # Check if this is the first user (becomes admin)
    user_count = db.query(models.User).count()
    is_admin = user_count == 0
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    
    # Set default permissions
    default_permissions = {
        "view_staff": False,
        "view_settings": False,
        "client_right": False,
        "view_marketing_emails": False,
        "dashboard_right": False,
        "view_product_prices": True  # Default: True
    }
    
    db_user = models.User(
        email=user_data.email,
        hashed_password=hashed_password,
        is_admin=is_admin,
        permissions=default_permissions,
        is_active=True,
        business_name=(user_data.business_name or "").strip() or None,
        business_username=((user_data.business_username or "").strip() or None) if is_admin else None,
    )
    
    db.add(db_user)
    db.flush()  # Flush to get the user ID
    
    # For admin, business_id is their own ID (set after flush)
    # For staff, business_id will be set when they're created by admin
    
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={},
        expires_delta=access_token_expires,
        user_id=db_user.id
    )
    
    # Convert permissions dict to UserPermissions schema
    permissions = schemas.UserPermissions(**db_user.permissions)
    business_name = db_user.business_name if db_user.is_admin else None
    if not db_user.is_admin and db_user.created_by_id:
        admin_user = db.query(models.User).filter(models.User.id == db_user.created_by_id).first()
        business_name = admin_user.business_name if admin_user else None

    user_response = schemas.User(
        id=db_user.id,
        email=db_user.email,
        is_admin=db_user.is_admin,
        created_by_id=db_user.created_by_id,
        permissions=permissions,
        is_active=db_user.is_active,
        business_name=business_name,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at
    )
    
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """Login with business email/username + staff/admin email + password. Business identifier identifies the business."""
    admin = _resolve_admin_by_identifier(db, credentials.business_identifier)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect business email, username, or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.email == credentials.business_identifier.strip():
        user = admin
    else:
        user = db.query(models.User).filter(
            models.User.email == credentials.email,
            models.User.created_by_id == admin.id,
            models.User.is_admin == False
        ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.hashed_password or not user.hashed_password.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not activated. Please set your password using the link sent to your email, or ask your administrator to resend it.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={},
        expires_delta=access_token_expires,
        user_id=user.id
    )
    
    # Convert permissions dict to UserPermissions schema
    permissions = schemas.UserPermissions(**user.permissions) if user.permissions else schemas.UserPermissions()
    business_name = user.business_name if user.is_admin else None
    if not user.is_admin and user.created_by_id:
        admin_user = db.query(models.User).filter(models.User.id == user.created_by_id).first()
        business_name = admin_user.business_name if admin_user else None

    user_response = schemas.User(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        created_by_id=user.created_by_id,
        permissions=permissions,
        is_active=user.is_active,
        business_name=business_name,
        created_at=user.created_at,
        updated_at=user.updated_at
    )
    
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.get("/me", response_model=schemas.User)
def get_current_user_info(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user information"""
    permissions = schemas.UserPermissions(**current_user.permissions) if current_user.permissions else schemas.UserPermissions()
    business_name = current_user.business_name if current_user.is_admin else None
    if not current_user.is_admin and current_user.created_by_id:
        admin_user = db.query(models.User).filter(models.User.id == current_user.created_by_id).first()
        business_name = admin_user.business_name if admin_user else None
    return schemas.User(
        id=current_user.id,
        email=current_user.email,
        is_admin=current_user.is_admin,
        created_by_id=current_user.created_by_id,
        permissions=permissions,
        is_active=current_user.is_active,
        business_name=business_name,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.post("/request-password-reset")
def request_password_reset(request: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    """Request a password reset. Only admins can use this endpoint."""
    user = _resolve_admin_by_identifier(db, request.identifier)
    if not user:
        # Don't reveal if user exists (security best practice)
        return {"message": "If the email exists and is an admin account, a password reset link has been sent"}
    
    # Only allow password reset for admins
    if not user.is_admin:
        return {
            "message": "Password reset is only available for admin accounts. Please contact your administrator to reset your password."
        }
    
    reset_token = create_password_reset_token(user.id)
    
    # Store token in database
    from datetime import datetime, timedelta, timezone
    user.password_reset_token = reset_token
    user.password_reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()
    
    # Send email with reset link
    try:
        from app.auth import get_business_id
        from app.services.config_validator import ConfigurationError, format_config_error_response
        
        business_id = get_business_id(user)
        email_service = EmailService(business_id=business_id, db=db)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        email_body = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You requested a password reset for your admin account.</p>
            <p>Click the following link to reset your password:</p>
            <p><a href="{reset_url}">{reset_url}</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you did not request this, please ignore this email.</p>
        </body>
        </html>
        """
        
        email_service.send_email(
            to_email=user.email,
            subject="Password Reset Request - Admin Account",
            body=email_body
        )
    except ConfigurationError as e:
        # Configuration error - return helpful message
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_config_error_response(e)
        )
    except Exception as e:
        print(f"Error sending password reset email: {str(e)}")
        # Don't fail the request if email fails (avoid leaking email existence)
    
    return {"message": "If the email exists and is an admin account, a password reset link has been sent"}


@router.post("/reset-password")
def reset_password(reset_data: schemas.PasswordReset, db: Session = Depends(get_db)):
    """Reset password using a reset token (token contains user_id)."""
    user_id = verify_password_reset_token(reset_data.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if token matches and hasn't expired
    if user.password_reset_token != reset_data.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    from datetime import datetime, timezone
    if user.password_reset_token_expires and user.password_reset_token_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.password_reset_token = None
    user.password_reset_token_expires = None
    db.commit()
    
    return {"message": "Password reset successfully"}


@router.post("/change-password")
def change_password(
    data: schemas.ChangePassword,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change password when logged in. No business email needed - uses session."""
    if not verify_password(data.previous_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Previous password is incorrect"
        )
    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.password_reset_token = None
    current_user.password_reset_token_expires = None
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/reset-password-with-previous")
def reset_password_with_previous(
    data: schemas.PasswordResetWithPrevious, db: Session = Depends(get_db)
):
    """Reset staff password using business email/username, staff email, and previous password.
    Allows staff to set their own password without needing an email token.
    """
    admin = _resolve_admin_by_identifier(db, data.business_identifier)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid business email or staff email",
        )

    # Find staff under this business
    staff = db.query(models.User).filter(
        models.User.email == data.staff_email,
        models.User.created_by_id == admin.id,
        models.User.is_admin == False,
    ).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid business email or staff email",
        )

    if not staff.hashed_password or not staff.hashed_password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has not set a password yet. Please use the password reset link sent to your email, or ask your administrator to resend it.",
        )
    if not verify_password(data.previous_password, staff.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Previous password is incorrect",
        )

    # Update password
    staff.hashed_password = get_password_hash(data.new_password)
    db.commit()

    return {"message": "Password reset successfully"}
