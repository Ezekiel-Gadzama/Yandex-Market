from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from datetime import datetime
from app.database import get_db
from app import models, schemas
from app.auth import get_current_active_user, get_business_id

router = APIRouter()

# Media upload directory - new structure: media/documentation/files, images, videos
from pathlib import Path
MEDIA_BASE = Path("media")
DOCUMENTATION_FILES_DIR = MEDIA_BASE / "documentation" / "files"
DOCUMENTATION_IMAGES_DIR = MEDIA_BASE / "documentation" / "images"
DOCUMENTATION_VIDEOS_DIR = MEDIA_BASE / "documentation" / "videos"

# Create directories if they don't exist
DOCUMENTATION_FILES_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTATION_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTATION_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_model=List[schemas.Documentation])
def get_documentations(
    search: Optional[str] = None,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all documentations with optional search. Only returns documentations for the current user's business."""
    from urllib.parse import quote, unquote
    
    business_id = get_business_id(current_user)
    query = db.query(models.Documentation).filter(models.Documentation.business_id == business_id)
    if search:
        query = query.filter(models.Documentation.name.ilike(f"%{search}%"))
    
    docs = query.order_by(models.Documentation.created_at.desc()).all()
    
    # Ensure file_url is properly encoded
    for doc in docs:
        if doc.file_url and doc.file_url.startswith('/api/media/files/'):
            path_part = doc.file_url.replace('/api/media/files/', '')
            try:
                decoded = unquote(path_part)
                segments = decoded.split('/')
                encoded = '/'.join(quote(seg, safe='') for seg in segments)
                doc.file_url = f"/api/media/files/{encoded}"
            except:
                pass
    
    return docs


@router.get("/{documentation_id}", response_model=schemas.Documentation)
def get_documentation(documentation_id: int, db: Session = Depends(get_db)):
    """Get a single documentation by ID"""
    from urllib.parse import quote, unquote
    
    documentation = db.query(models.Documentation).filter(models.Documentation.id == documentation_id).first()
    if not documentation:
        raise HTTPException(status_code=404, detail="Documentation not found")
    
    # Ensure file_url is properly encoded
    if documentation.file_url and documentation.file_url.startswith('/api/media/files/'):
        path_part = documentation.file_url.replace('/api/media/files/', '')
        try:
            decoded = unquote(path_part)
            segments = decoded.split('/')
            encoded = '/'.join(quote(seg, safe='') for seg in segments)
            documentation.file_url = f"/api/media/files/{encoded}"
        except:
            pass  # If encoding fails, leave as-is
    
    return documentation


@router.post("/", response_model=schemas.Documentation, status_code=status.HTTP_201_CREATED)
def create_documentation(
    documentation: schemas.DocumentationCreate,
    current_user: models.User = Depends(get_current_active_user),
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
    
    business_id = get_business_id(current_user)
    doc_data = documentation.dict()
    doc_data['business_id'] = business_id
    db_documentation = models.Documentation(**doc_data)
    db.add(db_documentation)
    db.commit()
    db.refresh(db_documentation)
    return db_documentation


@router.post("/upload", response_model=dict)
async def upload_documentation_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a documentation file - stores in media/documentation/files, images, or videos based on file type"""
    from datetime import datetime
    import re
    
    # Determine file type and target directory
    content_type = file.content_type or ''
    original_filename = file.filename or 'file'
    
    # Sanitize filename: remove parentheses, spaces, and other special characters, replace with underscore
    # Keep only alphanumeric, dots, hyphens, and underscores
    sanitized_name = re.sub(r'[()\[\]{}]', '_', original_filename)
    sanitized_name = re.sub(r'\s+', '_', sanitized_name)  # Replace spaces with underscore
    sanitized_name = re.sub(r'[^\w\.-]', '_', sanitized_name)  # Remove any remaining special chars
    sanitized_name = re.sub(r'_+', '_', sanitized_name)  # Replace multiple underscores with single
    sanitized_name = sanitized_name.strip('_')  # Remove leading/trailing underscores
    
    # Get base name and extension
    base_name, ext = os.path.splitext(sanitized_name)
    
    # Append date to filename: YYYYMMDD format
    date_str = datetime.now().strftime('%Y%m%d')
    filename = f"{base_name}_{date_str}{ext}"
    
    # Determine target directory
    if content_type.startswith('image/'):
        target_dir = DOCUMENTATION_IMAGES_DIR
        relative_path = f"documentation/images/{filename}"
    elif content_type.startswith('video/'):
        target_dir = DOCUMENTATION_VIDEOS_DIR
        relative_path = f"documentation/videos/{filename}"
    else:
        target_dir = DOCUMENTATION_FILES_DIR
        relative_path = f"documentation/files/{filename}"
    
    # Handle filename conflicts by appending counter
    file_path = target_dir / filename
    counter = 1
    while file_path.exists():
        filename = f"{base_name}_{date_str}_{counter}{ext}"
        if content_type.startswith('image/'):
            relative_path = f"documentation/images/{filename}"
        elif content_type.startswith('video/'):
            relative_path = f"documentation/videos/{filename}"
        else:
            relative_path = f"documentation/files/{filename}"
        file_path = target_dir / filename
        counter += 1
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Return file URL - simple path, no encoding needed since we sanitized the filename
    file_url = f"/api/media/files/{relative_path}"
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
def delete_documentation(
    documentation_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a documentation. Only deletes if it belongs to the current user's business."""
    business_id = get_business_id(current_user)
    db_documentation = db.query(models.Documentation).filter(
        models.Documentation.id == documentation_id,
        models.Documentation.business_id == business_id
    ).first()
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
