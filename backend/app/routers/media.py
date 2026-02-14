from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import uuid
from pathlib import Path
from urllib.parse import unquote
from app.database import get_db
from app.config import settings

router = APIRouter()

# Media directory structure
# media/documentation/files, media/documentation/images, media/documentation/videos
# media/marketing/files, media/marketing/photos
MEDIA_DIR = Path("media")

# Documentation directories
DOCUMENTATION_FILES_DIR = MEDIA_DIR / "documentation" / "files"
DOCUMENTATION_IMAGES_DIR = MEDIA_DIR / "documentation" / "images"
DOCUMENTATION_VIDEOS_DIR = MEDIA_DIR / "documentation" / "videos"

# Marketing directories
MARKETING_FILES_DIR = MEDIA_DIR / "marketing" / "files"
MARKETING_PHOTOS_DIR = MEDIA_DIR / "marketing" / "photos"

# Create directories if they don't exist
MEDIA_DIR.mkdir(exist_ok=True)
DOCUMENTATION_FILES_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTATION_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTATION_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
MARKETING_FILES_DIR.mkdir(parents=True, exist_ok=True)
MARKETING_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def get_media_url(file_path: str) -> str:
    """Convert file path to URL"""
    return f"/api/media/files/{file_path}"


@router.post("/upload/images", response_model=List[str])
async def upload_images(
    files: List[UploadFile] = File(...),
    context: str = Query("marketing", description="Context: 'marketing' or 'documentation'"),
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
        
        # Use context-appropriate directory
        if context == "documentation":
            file_path = DOCUMENTATION_IMAGES_DIR / unique_filename
            relative_path = f"documentation/images/{unique_filename}"
        else:
            file_path = MARKETING_PHOTOS_DIR / unique_filename
            relative_path = f"marketing/photos/{unique_filename}"
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        uploaded_urls.append(relative_path)
    
    return uploaded_urls


@router.post("/upload/videos", response_model=List[str])
async def upload_videos(
    files: List[UploadFile] = File(...),
    context: str = Query("documentation", description="Context: 'marketing' or 'documentation'"),
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
        
        # Videos only supported for documentation
        file_path = DOCUMENTATION_VIDEOS_DIR / unique_filename
        relative_path = f"documentation/videos/{unique_filename}"
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        uploaded_urls.append(relative_path)
    
    return uploaded_urls


@router.get("/files/{file_path:path}")
async def get_media_file(file_path: str):
    """Serve media files - simple and straightforward"""
    # FastAPI automatically URL-decodes path parameters, but handle both cases
    # If path still has encoded chars, decode them
    decoded_path = unquote(file_path) if '%' in file_path else file_path
    full_path = MEDIA_DIR / decoded_path
    
    # If file doesn't exist, try to find files with matching suffix (handles timestamp prefix)
    if not full_path.exists() or not full_path.is_file():
        parent_dir = full_path.parent
        if parent_dir.exists():
            requested_filename = full_path.name
            # Look for files ending with the requested filename
            matching_files = [f for f in parent_dir.iterdir() 
                            if f.is_file() and f.name.endswith(requested_filename)]
            if matching_files:
                full_path = matching_files[0]
            else:
                raise HTTPException(status_code=404, detail=f"File not found: {decoded_path}")
        else:
            raise HTTPException(status_code=404, detail=f"Directory not found: {parent_dir}")
    
    # Security check
    try:
        full_path.resolve().relative_to(MEDIA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(full_path)


@router.post("/upload/files", response_model=List[str])
async def upload_files(
    files: List[UploadFile] = File(...),
    context: str = Query("marketing", description="Context: 'marketing' or 'documentation'"),
    db: Session = Depends(get_db)
):
    """Upload generic files (documents, etc.)"""
    uploaded_urls = []
    
    for file in files:
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Use context-appropriate directory
        if context == "documentation":
            file_path = DOCUMENTATION_FILES_DIR / unique_filename
            relative_path = f"documentation/files/{unique_filename}"
        else:
            file_path = MARKETING_FILES_DIR / unique_filename
            relative_path = f"marketing/files/{unique_filename}"
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        uploaded_urls.append(relative_path)
    
    return uploaded_urls


@router.post("/upload", response_model=List[dict])
async def upload_any_files(
    files: List[UploadFile] = File(...),
    context: str = Query("marketing", description="Context: 'marketing' or 'documentation'"),
    db: Session = Depends(get_db)
):
    """Unified upload endpoint - accepts any file type and returns attachment objects
    
    Context determines the storage location:
    - 'marketing': stores in media/marketing/files or media/marketing/photos
    - 'documentation': stores in media/documentation/files, images, or videos
    """
    uploaded_attachments = []
    
    for file in files:
        # Determine file type
        content_type = file.content_type or ''
        
        if context == "documentation":
            # Documentation: files, images, videos
            if content_type.startswith('image/'):
                file_type = 'image'
                target_dir = DOCUMENTATION_IMAGES_DIR
                relative_dir = 'documentation/images'
            elif content_type.startswith('video/'):
                file_type = 'video'
                target_dir = DOCUMENTATION_VIDEOS_DIR
                relative_dir = 'documentation/videos'
            else:
                file_type = 'file'
                target_dir = DOCUMENTATION_FILES_DIR
                relative_dir = 'documentation/files'
        else:
            # Marketing: files and photos (images)
            if content_type.startswith('image/'):
                file_type = 'image'
                target_dir = MARKETING_PHOTOS_DIR
                relative_dir = 'marketing/photos'
            else:
                file_type = 'file'
                target_dir = MARKETING_FILES_DIR
                relative_dir = 'marketing/files'
        
        # Sanitize filename: remove parentheses and special characters, append date
        from datetime import datetime
        import re
        
        original_filename = file.filename or 'file'
        # Remove parentheses, spaces, and other special characters, replace with underscore
        sanitized_name = re.sub(r'[()\[\]{}]', '_', original_filename)
        sanitized_name = re.sub(r'\s+', '_', sanitized_name)  # Replace spaces with underscore
        sanitized_name = re.sub(r'[^\w\.-]', '_', sanitized_name)  # Remove any remaining special chars
        sanitized_name = re.sub(r'_+', '_', sanitized_name)  # Replace multiple underscores with single
        sanitized_name = sanitized_name.strip('_')  # Remove leading/trailing underscores
        
        # Get base name and extension
        base_name, ext = os.path.splitext(sanitized_name)
        
        # Append date: YYYYMMDD format
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{base_name}_{date_str}{ext}"
        
        # Handle conflicts by appending counter
        file_path = target_dir / filename
        counter = 1
        while file_path.exists():
            filename = f"{base_name}_{date_str}_{counter}{ext}"
            file_path = target_dir / filename
            counter += 1
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return attachment object
        relative_path = f"{relative_dir}/{filename}"
        uploaded_attachments.append({
            "url": f"/api/media/files/{relative_path}",
            "type": file_type,
            "name": file.filename or filename
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
