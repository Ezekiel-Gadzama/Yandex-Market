from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import or_ as sql_or, func
from typing import List
from app.database import get_db
from app import models, schemas
from app.auth import get_current_active_user, get_business_id
from app.utils.export_utils import (
    extract_text_from_file,
    build_txt_activation,
    build_pdf_bytes,
    strip_html,
)

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


@router.get("/{template_id}/export")
def export_activation_template(
    template_id: int,
    format: str = Query("txt", regex="^(txt|pdf)$"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Export activation template as TXT or PDF."""
    business_id = get_business_id(current_user)
    template = db.query(models.EmailTemplate).filter(
        models.EmailTemplate.id == template_id,
        models.EmailTemplate.business_id == business_id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    full_text = build_txt_activation(template.name, template.body or "")
    safe_name = "".join(c for c in template.name if c.isalnum() or c in " -_")[:80].strip() or "activation-template"
    if format == "pdf":
        pdf_bytes = build_pdf_bytes(template.name, full_text)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
        )
    return Response(
        content=full_text.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.txt"'},
    )


@router.post("/from-file", response_model=schemas.EmailTemplate, status_code=status.HTTP_201_CREATED)
async def create_activation_template_from_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create an activation template from a TXT or PDF file. Name from filename, body from file content."""
    if not file.filename or not file.filename.lower().endswith((".txt", ".pdf")):
        raise HTTPException(status_code=400, detail="Only .txt or .pdf files are allowed")
    content = await file.read()
    body = extract_text_from_file(content, file.filename)
    if not body.strip():
        raise HTTPException(status_code=400, detail="File appears empty or could not extract text")
    import os
    base_name = os.path.splitext(file.filename or "template")[0]
    name = base_name.replace("_", " ").replace("-", " ").strip() or "Imported Template"
    business_id = get_business_id(current_user)
    db_template = models.EmailTemplate(
        business_id=business_id,
        name=name,
        body=body,
        random_key=True,
        required_login=False,
        activate_till_days=30,
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


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
