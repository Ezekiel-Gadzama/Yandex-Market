from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_ as sql_or, func
from typing import List
from app.database import get_db
from app import models, schemas
from app.auth import get_current_active_user, get_business_id

router = APIRouter()


@router.get("/", response_model=List[schemas.EmailTemplate])
def get_email_templates(
    search: str = Query(None, description="Search by name or body"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all email templates with optional search. Only returns templates for the current user's business."""
    business_id = get_business_id(current_user)
    query = db.query(models.EmailTemplate).filter(models.EmailTemplate.business_id == business_id)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            sql_or(
                func.lower(models.EmailTemplate.name).like(search_term),
                func.lower(models.EmailTemplate.body).like(search_term)
            )
        )
    
    templates = query.all()
    return templates


@router.get("/{template_id}", response_model=schemas.EmailTemplate)
def get_email_template(
    template_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a single email template by ID. Only returns template if it belongs to the current user's business."""
    business_id = get_business_id(current_user)
    template = db.query(models.EmailTemplate).filter(
        models.EmailTemplate.id == template_id,
        models.EmailTemplate.business_id == business_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    return template


@router.post("/", response_model=schemas.EmailTemplate, status_code=status.HTTP_201_CREATED)
def create_email_template(
    template: schemas.EmailTemplateCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new email template"""
    business_id = get_business_id(current_user)
    template_data = template.dict()
    template_data['business_id'] = business_id
    db_template = models.EmailTemplate(**template_data)
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
