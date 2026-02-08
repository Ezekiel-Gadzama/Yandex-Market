from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter()


def get_or_create_settings(db: Session) -> models.AppSettings:
    """Get or create the singleton settings record"""
    settings = db.query(models.AppSettings).first()
    if not settings:
        # Create default settings
        settings = models.AppSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/", response_model=schemas.AppSettings)
def get_settings(db: Session = Depends(get_db)):
    """Get application settings"""
    return get_or_create_settings(db)


@router.put("/", response_model=schemas.AppSettings)
def update_settings(
    settings_update: schemas.AppSettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update application settings"""
    settings = get_or_create_settings(db)
    
    update_data = settings_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    return settings
