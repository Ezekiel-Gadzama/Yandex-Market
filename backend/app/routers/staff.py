from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app import models, schemas
from app.auth import (
    get_current_active_user, require_admin, has_permission,
    create_password_reset_token, get_password_hash, get_business_id
)
from app.services.email_service import EmailService
from app.services.config_validator import ConfigurationError, format_config_error_response
from app.config import settings

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
def get_staff(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all staff accounts. Only admin or users with view_staff permission can access."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_staff"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: view_staff"
        )
    
    business_id = get_business_id(current_user)
    if current_user.is_admin:
        staff = db.query(models.User).filter(
            models.User.is_admin == False,
            models.User.created_by_id == business_id
        ).all()
    else:
        # Staff can only see staff created by their admin
        staff = db.query(models.User).filter(
            models.User.is_admin == False,
            models.User.created_by_id == current_user.created_by_id
        ).all()
    
    # Convert to response format
    result = []
    for user in staff:
        permissions = schemas.UserPermissions(**user.permissions) if user.permissions else schemas.UserPermissions()
        result.append(schemas.User(
            id=user.id,
            email=user.email,
            name=user.name,
            is_admin=user.is_admin,
            created_by_id=user.created_by_id,
            permissions=permissions,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        ))
    
    return result


@router.get("/business-account", response_model=schemas.User)
def get_business_account(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the business admin account. Access: admin or users with view_staff permission."""
    if not current_user.is_admin and not has_permission(current_user, "view_staff"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: view_staff"
        )
    business_id = get_business_id(current_user)
    admin_user = db.query(models.User).filter(
        models.User.id == business_id,
        models.User.is_admin == True
    ).first()
    if not admin_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business account not found")
    permissions = schemas.UserPermissions(**admin_user.permissions) if admin_user.permissions else schemas.UserPermissions()
    return schemas.User(
        id=admin_user.id,
        email=admin_user.email,
        is_admin=admin_user.is_admin,
        created_by_id=admin_user.created_by_id,
        permissions=permissions,
        is_active=admin_user.is_active,
        business_name=admin_user.business_name,
        business_username=admin_user.business_username,
        created_at=admin_user.created_at,
        updated_at=admin_user.updated_at
    )


@router.put("/business-account", response_model=schemas.User)
def update_business_account(
    data: schemas.BusinessAccountUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update business admin email, password, and/or business name. Uses business_id (not email). Access: admin or users with view_staff."""
    if not current_user.is_admin and not has_permission(current_user, "view_staff"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: view_staff"
        )
    business_id = get_business_id(current_user)
    admin_user = db.query(models.User).filter(
        models.User.id == business_id,
        models.User.is_admin == True
    ).first()
    if not admin_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business account not found")
    if data.new_email is not None:
        existing_admin = db.query(models.User).filter(
            models.User.email == data.new_email,
            models.User.is_admin == True,
            models.User.id != admin_user.id
        ).first()
        if existing_admin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        admin_user.email = data.new_email
    if data.new_password:
        admin_user.hashed_password = get_password_hash(data.new_password)
        admin_user.password_reset_token = None
        admin_user.password_reset_token_expires = None
    if data.business_name is not None:
        admin_user.business_name = data.business_name.strip() or None
    admin_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(admin_user)
    permissions = schemas.UserPermissions(**admin_user.permissions) if admin_user.permissions else schemas.UserPermissions()
    return schemas.User(
        id=admin_user.id,
        email=admin_user.email,
        is_admin=admin_user.is_admin,
        created_by_id=admin_user.created_by_id,
        permissions=permissions,
        is_active=admin_user.is_active,
        business_name=admin_user.business_name,
        business_username=admin_user.business_username,
        created_at=admin_user.created_at,
        updated_at=admin_user.updated_at
    )


@router.post("/", response_model=schemas.User)
def create_staff(
    staff_data: schemas.StaffCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new staff account. Only admin or users with view_staff permission can create staff."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_staff"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: view_staff"
        )
    
    created_by_id = current_user.id if current_user.is_admin else current_user.created_by_id
    existing_staff = db.query(models.User).filter(
        models.User.email == staff_data.email,
        models.User.created_by_id == created_by_id
    ).first()
    if existing_staff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered for this business"
        )
    
    # Determine created_by_id
    created_by_id = current_user.id if current_user.is_admin else current_user.created_by_id
    
    # Set default permissions (all False except view_product_prices which is True)
    default_permissions = {
        "view_staff": False,
        "view_settings": False,
        "client_right": False,
        "view_marketing_emails": False,
        "dashboard_right": False,
        "view_product_prices": True  # Default: True
    }

    # If password provided, use it; otherwise empty (will send reset link via email)
    hashed_password = get_password_hash(staff_data.password) if staff_data.password else ""
    
    db_user = models.User(
        email=staff_data.email,
        name=(staff_data.name or "").strip() or None,
        hashed_password=hashed_password,
        is_admin=False,
        created_by_id=created_by_id,
        permissions=default_permissions,
        is_active=True
    )
    
    db.add(db_user)
    db.flush()
    
    # When no password: set reset token and optionally send email (never block staff creation)
    if not staff_data.password:
        reset_token = create_password_reset_token(db_user.id)
        db_user.password_reset_token = reset_token
        db_user.password_reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        
        try:
            from app.auth import get_business_id
            
            business_id = get_business_id(current_user)
            email_service = EmailService(business_id=business_id, db=db)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            email_body = f"""
            You have been invited to join the Yandex Market management system.
            
            Click the following link to set your password and activate your account:
            {reset_url}
            
            This link will expire in 24 hours.
            
            If you did not expect this invitation, please contact your administrator.
            """
            
            result = email_service.send_email(
                to_email=db_user.email,
                subject="Welcome to Yandex Market - Set Your Password",
                body=email_body
            )
            if result.get("success"):
                print(f"[Staff] Invitation email sent to {db_user.email}")
            else:
                print(f"[Staff] Invitation email not sent: {result.get('message', 'unknown')}")
        except ConfigurationError as e:
            print(f"[Staff] SMTP not configured - invitation email skipped: {e}")
        except Exception as e:
            print(f"[Staff] Failed to send invitation email: {e}")
    
    db.commit()
    db.refresh(db_user)
    
    # Convert to response format
    permissions = schemas.UserPermissions(**db_user.permissions) if db_user.permissions else schemas.UserPermissions()
    return schemas.User(
        id=db_user.id,
        email=db_user.email,
        name=db_user.name,
        is_admin=db_user.is_admin,
        created_by_id=db_user.created_by_id,
        permissions=permissions,
        is_active=db_user.is_active,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at
    )


@router.put("/{staff_id}", response_model=schemas.User)
def update_staff(
    staff_id: int,
    staff_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update staff account permissions. Only admin or users with view_staff permission can update."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_staff"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: view_staff"
        )
    
    # Find staff user
    staff_user = db.query(models.User).filter(models.User.id == staff_id).first()
    if not staff_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user not found"
        )
    
    # Check if user is trying to update an admin (not allowed)
    if staff_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update admin accounts"
        )
    
    # Check if current user has permission to update this staff member
    if not current_user.is_admin:
        # Staff can only update staff created by their admin
        if staff_user.created_by_id != current_user.created_by_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update staff created by your admin"
            )
    
    # Update permissions if provided
    if staff_update.permissions is not None:
        # Convert permissions to dict
        permissions_dict = staff_update.permissions.dict()
        # Merge with existing permissions (preserve defaults)
        if staff_user.permissions:
            staff_user.permissions.update(permissions_dict)
        else:
            staff_user.permissions = permissions_dict
    
    # Update is_active if provided
    if staff_update.is_active is not None:
        staff_user.is_active = staff_update.is_active

    # Update password if provided (admin can set staff password directly)
    if staff_update.new_password:
        staff_user.hashed_password = get_password_hash(staff_update.new_password)
        staff_user.password_reset_token = None
        staff_user.password_reset_token_expires = None

    # Update name if provided
    if staff_update.name is not None:
        staff_user.name = (staff_update.name or "").strip() or None
    
    staff_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(staff_user)
    
    # Convert to response format
    permissions = schemas.UserPermissions(**staff_user.permissions) if staff_user.permissions else schemas.UserPermissions()
    return schemas.User(
        id=staff_user.id,
        email=staff_user.email,
        name=staff_user.name,
        is_admin=staff_user.is_admin,
        created_by_id=staff_user.created_by_id,
        permissions=permissions,
        is_active=staff_user.is_active,
        created_at=staff_user.created_at,
        updated_at=staff_user.updated_at
    )


@router.delete("/{staff_id}")
def delete_staff(
    staff_id: int,
    current_user: models.User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Delete a staff account. Only admin can delete staff."""
    staff_user = db.query(models.User).filter(models.User.id == staff_id).first()
    if not staff_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user not found"
        )
    
    # Cannot delete admin accounts
    if staff_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete admin accounts"
        )
    
    db.delete(staff_user)
    db.commit()
    
    return {"message": "Staff account deleted successfully"}


@router.post("/{staff_id}/resend-password-reset")
def resend_password_reset(
    staff_id: int,
    current_user: models.User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Resend password reset link to a staff member. Only admin can do this."""
    staff = db.query(models.User).filter(models.User.id == staff_id).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user not found"
        )
    
    # Prevent resetting admin passwords
    if staff.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset password for admin accounts. Use the forgot password feature instead."
        )
    
    # Generate reset token
    reset_token = create_password_reset_token(staff.id)
    
    # Store token in database
    staff.password_reset_token = reset_token
    staff.password_reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()
    
    # Send email with reset link
    try:
        business_id = get_business_id(current_user)
        email_service = EmailService(business_id=business_id, db=db)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        email_body = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Your administrator has requested a password reset for your account.</p>
            <p>Click the following link to set your password:</p>
            <p><a href="{reset_url}">{reset_url}</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you did not request this, please contact your administrator.</p>
        </body>
        </html>
        """
        
        result = email_service.send_email(
            to_email=staff.email,
            subject="Password Reset Request - Staff Account",
            body=email_body
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result.get("message", "Failed to send password reset email. Check SMTP settings and server network (e.g. firewall allows outbound port 587).")
            )
    except HTTPException:
        raise
    except ConfigurationError as e:
        error_detail = format_config_error_response(e)
        error_detail["action_required"] = "Please configure your email settings (SMTP) in the Settings page to send password reset emails."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail
        )
    except Exception as e:
        print(f"Error sending password reset email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send password reset email: {str(e)}"
        )
    
    return {"message": "Password reset link has been sent to the staff member's email"}
