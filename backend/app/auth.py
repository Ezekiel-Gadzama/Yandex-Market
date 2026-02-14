from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app import models, schemas

# Password hashing
# Use lazy initialization to avoid bcrypt version detection issues during import
_pwd_context_instance = None

def _get_pwd_context():
    """Get or create password context (lazy initialization to avoid bcrypt version issues)"""
    global _pwd_context_instance
    if _pwd_context_instance is None:
        try:
            # Initialize with explicit backend to avoid version detection issues
            _pwd_context_instance = CryptContext(
                schemes=["bcrypt"],
                deprecated="auto",
                bcrypt__ident="2b"
            )
        except Exception as e:
            # If initialization fails, try without explicit settings
            try:
                _pwd_context_instance = CryptContext(schemes=["bcrypt"], deprecated="auto")
            except Exception as e2:
                print(f"Error initializing bcrypt: {e2}")
                raise
    return _pwd_context_instance

# For backward compatibility, create a property-like accessor
class PwdContextProxy:
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return _get_pwd_context().verify(plain_password, hashed_password)
    
    def hash(self, password: str) -> str:
        return _get_pwd_context().hash(password)

pwd_context = PwdContextProxy()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return _get_pwd_context().verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return _get_pwd_context().hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_password_reset_token(email: str) -> str:
    """Create a password reset token"""
    delta = timedelta(hours=24)  # Token expires in 24 hours
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"sub": email, "exp": exp, "type": "password_reset"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify a password reset token and return the email"""
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if decoded_token.get("type") != "password_reset":
            return None
        email: str = decoded_token.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """Get the current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


# Permission checking functions
def has_permission(user: models.User, permission: str) -> bool:
    """Check if user has a specific permission"""
    # Admin has all permissions
    if user.is_admin:
        return True
    
    # Check user's permissions dict
    if not user.permissions:
        return False
    
    # Default value for view_product_prices is True
    if permission == "view_product_prices":
        return user.permissions.get(permission, True)
    
    return user.permissions.get(permission, False)


def require_permission(permission: str):
    """Dependency to require a specific permission"""
    async def permission_checker(
        current_user: models.User = Depends(get_current_active_user)
    ) -> models.User:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return current_user
    return permission_checker


def require_admin():
    """Dependency to require admin role"""
    async def admin_checker(
        current_user: models.User = Depends(get_current_active_user)
    ) -> models.User:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user
    return admin_checker


def get_business_id(user: models.User) -> int:
    """Get the business ID for a user.
    
    For admins, business_id is their own user ID.
    For staff, business_id is their created_by_id (the admin who created them).
    """
    if user.is_admin:
        return user.id
    else:
        # Staff members belong to their admin's business
        if user.created_by_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff account must be linked to an admin"
            )
        return user.created_by_id