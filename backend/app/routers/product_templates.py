from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from app.database import get_db
from app import models, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.ProductTemplate])
def get_templates(db: Session = Depends(get_db)):
    """Get all product templates"""
    templates = db.query(models.ProductTemplate).order_by(models.ProductTemplate.created_at.desc()).all()
    return templates


@router.get("/{template_id}", response_model=schemas.ProductTemplate)
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific product template"""
    template = db.query(models.ProductTemplate).filter(models.ProductTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/", response_model=schemas.ProductTemplate, status_code=status.HTTP_201_CREATED)
def create_template(template: schemas.ProductTemplateCreate, db: Session = Depends(get_db)):
    """Create a new product template from a product"""
    # Convert template data to JSON string
    template_data = json.dumps(template.template_data)
    
    db_template = models.ProductTemplate(
        name=template.name,
        template_data=template_data
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    
    # Parse back for response
    template_dict = db_template.__dict__.copy()
    template_dict["template_data"] = json.loads(db_template.template_data)
    return schemas.ProductTemplate(**template_dict)


@router.put("/{template_id}", response_model=schemas.ProductTemplate)
def update_template(
    template_id: int,
    template_update: schemas.ProductTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update a product template"""
    db_template = db.query(models.ProductTemplate).filter(models.ProductTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = template_update.dict(exclude_unset=True)
    if "template_data" in update_data:
        update_data["template_data"] = json.dumps(update_data["template_data"])
    
    for field, value in update_data.items():
        setattr(db_template, field, value)
    
    db.commit()
    db.refresh(db_template)
    
    # Parse back for response
    template_dict = db_template.__dict__.copy()
    template_dict["template_data"] = json.loads(db_template.template_data)
    return schemas.ProductTemplate(**template_dict)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a product template"""
    db_template = db.query(models.ProductTemplate).filter(models.ProductTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(db_template)
    db.commit()
    return None
