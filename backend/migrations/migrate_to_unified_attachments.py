"""
Migration script to migrate from separate template_files/template_images/template_videos
to unified attachments field.

Run this script to migrate existing data:
    python backend/migrations/migrate_to_unified_attachments.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app import models
from sqlalchemy import text

def migrate_attachments():
    """Migrate separate media fields to unified attachments field"""
    print("Migrating email templates and marketing email templates to unified attachments...")
    
    db = SessionLocal()
    try:
        # Migrate EmailTemplate (activation templates)
        email_templates = db.query(models.EmailTemplate).all()
        print(f"  - Found {len(email_templates)} email templates")
        
        for template in email_templates:
            attachments = []
            
            # Migrate template_files
            if template.template_files:
                for url in template.template_files:
                    if url:
                        attachments.append({
                            "url": url,
                            "type": "file",
                            "name": url.split('/')[-1] if '/' in url else url
                        })
            
            # Migrate template_images
            if template.template_images:
                for url in template.template_images:
                    if url:
                        attachments.append({
                            "url": url,
                            "type": "image",
                            "name": url.split('/')[-1] if '/' in url else url
                        })
            
            # Migrate template_videos
            if template.template_videos:
                for url in template.template_videos:
                    if url:
                        attachments.append({
                            "url": url,
                            "type": "video",
                            "name": url.split('/')[-1] if '/' in url else url
                        })
            
            template.attachments = attachments
            print(f"    Migrated template '{template.name}': {len(attachments)} attachments")
        
        # Migrate MarketingEmailTemplate
        marketing_templates = db.query(models.MarketingEmailTemplate).all()
        print(f"  - Found {len(marketing_templates)} marketing email templates")
        
        for template in marketing_templates:
            attachments = []
            
            # Migrate template_files
            if template.template_files:
                for url in template.template_files:
                    if url:
                        attachments.append({
                            "url": url,
                            "type": "file",
                            "name": url.split('/')[-1] if '/' in url else url
                        })
            
            # Migrate template_images
            if template.template_images:
                for url in template.template_images:
                    if url:
                        attachments.append({
                            "url": url,
                            "type": "image",
                            "name": url.split('/')[-1] if '/' in url else url
                        })
            
            # Migrate template_videos
            if template.template_videos:
                for url in template.template_videos:
                    if url:
                        attachments.append({
                            "url": url,
                            "type": "video",
                            "name": url.split('/')[-1] if '/' in url else url
                        })
            
            template.attachments = attachments
            print(f"    Migrated template '{template.name}': {len(attachments)} attachments")
        
        db.commit()
        print("✓ Migration completed successfully")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    migrate_attachments()
