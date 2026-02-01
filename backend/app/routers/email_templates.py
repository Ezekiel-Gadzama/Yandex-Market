from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.EmailTemplate])
def get_email_templates(db: Session = Depends(get_db)):
    """Get all email templates"""
    templates = db.query(models.EmailTemplate).all()
    return templates


@router.get("/{template_id}", response_model=schemas.EmailTemplate)
def get_email_template(template_id: int, db: Session = Depends(get_db)):
    """Get a single email template by ID"""
    template = db.query(models.EmailTemplate).filter(models.EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    return template


@router.post("/", response_model=schemas.EmailTemplate, status_code=status.HTTP_201_CREATED)
def create_email_template(template: schemas.EmailTemplateCreate, db: Session = Depends(get_db)):
    """Create a new email template"""
    db_template = models.EmailTemplate(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.put("/{template_id}", response_model=schemas.EmailTemplate)
def update_email_template(
    template_id: int,
    template_update: schemas.EmailTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update an email template"""
    db_template = db.query(models.EmailTemplate).filter(models.EmailTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    update_data = template_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_template, field, value)
    
    db.commit()
    db.refresh(db_template)
    return db_template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email_template(template_id: int, db: Session = Depends(get_db)):
    """Delete an email template"""
    db_template = db.query(models.EmailTemplate).filter(models.EmailTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    db.delete(db_template)
    db.commit()
    return None
