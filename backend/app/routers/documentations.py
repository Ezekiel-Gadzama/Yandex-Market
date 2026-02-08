from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from datetime import datetime
from app.database import get_db
from app import models, schemas

router = APIRouter()

# Media upload directory
MEDIA_DIR = "uploads/documentations"
os.makedirs(MEDIA_DIR, exist_ok=True)


@router.get("/", response_model=List[schemas.Documentation])
def get_documentations(
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all documentations with optional search"""
    query = db.query(models.Documentation)
    if search:
        query = query.filter(models.Documentation.name.ilike(f"%{search}%"))
    return query.order_by(models.Documentation.created_at.desc()).all()


@router.get("/{documentation_id}", response_model=schemas.Documentation)
def get_documentation(documentation_id: int, db: Session = Depends(get_db)):
    """Get a single documentation by ID"""
    documentation = db.query(models.Documentation).filter(models.Documentation.id == documentation_id).first()
    if not documentation:
        raise HTTPException(status_code=404, detail="Documentation not found")
    return documentation


@router.post("/", response_model=schemas.Documentation, status_code=status.HTTP_201_CREATED)
def create_documentation(
    documentation: schemas.DocumentationCreate,
    db: Session = Depends(get_db)
):
    """Create a new documentation"""
    # Validate that required fields are provided based on type
    if documentation.type == 'file' and not documentation.file_url:
        raise HTTPException(status_code=400, detail="file_url is required for file type documentation")
    if documentation.type == 'link' and not documentation.link_url:
        raise HTTPException(status_code=400, detail="link_url is required for link type documentation")
    if documentation.type == 'text' and not documentation.content:
        raise HTTPException(status_code=400, detail="content is required for text type documentation")
    
    db_documentation = models.Documentation(**documentation.dict())
    db.add(db_documentation)
    db.commit()
    db.refresh(db_documentation)
    return db_documentation


@router.post("/upload", response_model=dict)
async def upload_documentation_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a documentation file"""
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ''
    filename = f"{timestamp}_{file.filename or 'file'}"
    file_path = os.path.join(MEDIA_DIR, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Return file URL
    file_url = f"/api/media/files/{MEDIA_DIR}/{filename}"
    return {"file_url": file_url, "filename": filename}


@router.put("/{documentation_id}", response_model=schemas.Documentation)
def update_documentation(
    documentation_id: int,
    documentation: schemas.DocumentationUpdate,
    db: Session = Depends(get_db)
):
    """Update a documentation"""
    db_documentation = db.query(models.Documentation).filter(models.Documentation.id == documentation_id).first()
    if not db_documentation:
        raise HTTPException(status_code=404, detail="Documentation not found")
    
    update_data = documentation.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_documentation, field, value)
    
    db.commit()
    db.refresh(db_documentation)
    return db_documentation


@router.delete("/{documentation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_documentation(documentation_id: int, db: Session = Depends(get_db)):
    """Delete a documentation"""
    db_documentation = db.query(models.Documentation).filter(models.Documentation.id == documentation_id).first()
    if not db_documentation:
        raise HTTPException(status_code=404, detail="Documentation not found")
    
    # Delete file if it exists
    if db_documentation.file_url:
        file_path = db_documentation.file_url.replace("/api/media/files/", "")
        full_path = os.path.join("uploads", file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    
    db.delete(db_documentation)
    db.commit()
    return None
