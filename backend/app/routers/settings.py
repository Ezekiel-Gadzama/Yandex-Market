from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.auth import get_current_active_user, has_permission, get_business_id

router = APIRouter()


def get_or_create_settings(business_id: int, db: Session) -> models.AppSettings:
    """Get or create the settings record for a business"""
    settings = db.query(models.AppSettings).filter(models.AppSettings.business_id == business_id).first()
    if not settings:
        # Create default settings for this business
        settings = models.AppSettings(business_id=business_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/", response_model=schemas.AppSettings)
def get_settings(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get application settings. Requires view_settings permission."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_settings"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: view_settings"
        )
    business_id = get_business_id(current_user)
    return get_or_create_settings(business_id, db)


@router.put("/", response_model=schemas.AppSettings)
def update_settings(
    settings_update: schemas.AppSettingsUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update application settings. Requires view_settings permission."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_settings"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: view_settings"
        )
    business_id = get_business_id(current_user)
    settings = get_or_create_settings(business_id, db)
    
    update_data = settings_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    return settings
