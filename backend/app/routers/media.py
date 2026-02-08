from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import uuid
from pathlib import Path
from app.database import get_db
from app.config import settings

router = APIRouter()

# Media directory
MEDIA_DIR = Path("media")
IMAGES_DIR = MEDIA_DIR / "images"
VIDEOS_DIR = MEDIA_DIR / "videos"
FILES_DIR = MEDIA_DIR / "files"

# Create directories if they don't exist
MEDIA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)
FILES_DIR.mkdir(exist_ok=True)


def get_media_url(file_path: str) -> str:
    """Convert file path to URL"""
    return f"/api/media/files/{file_path}"


@router.post("/upload/images", response_model=List[str])
async def upload_images(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload image files"""
    uploaded_urls = []
    
    for file in files:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not an image")
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = IMAGES_DIR / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return relative path for database storage
        relative_path = f"images/{unique_filename}"
        uploaded_urls.append(relative_path)
    
    return uploaded_urls


@router.post("/upload/videos", response_model=List[str])
async def upload_videos(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload video files"""
    uploaded_urls = []
    
    for file in files:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a video")
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = VIDEOS_DIR / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return relative path for database storage
        relative_path = f"videos/{unique_filename}"
        uploaded_urls.append(relative_path)
    
    return uploaded_urls


@router.get("/files/{file_path:path}")
async def get_media_file(file_path: str):
    """Serve media files"""
    full_path = MEDIA_DIR / file_path
    
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Security check: ensure file is within media directory
    try:
        full_path.resolve().relative_to(MEDIA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(full_path)


@router.post("/upload/files", response_model=List[str])
async def upload_files(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload generic files (documents, etc.)"""
    uploaded_urls = []
    
    for file in files:
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = FILES_DIR / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return relative path for database storage
        relative_path = f"files/{unique_filename}"
        uploaded_urls.append(relative_path)
    
    return uploaded_urls


@router.post("/upload", response_model=List[dict])
async def upload_any_files(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Unified upload endpoint - accepts any file type and returns attachment objects"""
    uploaded_attachments = []
    
    for file in files:
        # Determine file type
        content_type = file.content_type or ''
        if content_type.startswith('image/'):
            file_type = 'image'
            target_dir = IMAGES_DIR
            relative_dir = 'images'
        elif content_type.startswith('video/'):
            file_type = 'video'
            target_dir = VIDEOS_DIR
            relative_dir = 'videos'
        else:
            file_type = 'file'
            target_dir = FILES_DIR
            relative_dir = 'files'
        
        # Generate unique filename
        file_ext = Path(file.filename or 'file').suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = target_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return attachment object
        relative_path = f"{relative_dir}/{unique_filename}"
        uploaded_attachments.append({
            "url": relative_path,
            "type": file_type,
            "name": file.filename or unique_filename
        })
    
    return uploaded_attachments


@router.delete("/files/{file_path:path}")
async def delete_media_file(file_path: str):
    """Delete a media file"""
    full_path = MEDIA_DIR / file_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Security check
    try:
        full_path.resolve().relative_to(MEDIA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    full_path.unlink()
    return {"success": True, "message": "File deleted"}
