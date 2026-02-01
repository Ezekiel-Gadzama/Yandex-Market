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

# Create directories if they don't exist
MEDIA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)


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
