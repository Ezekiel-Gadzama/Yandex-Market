"""
Quick script to add attachments columns to database tables.
Run this from the backend container or with database access.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, engine
from sqlalchemy import text

def add_attachments_columns():
    """Add attachments column to email_templates and marketing_email_templates"""
    print("Adding attachments columns to email_templates and marketing_email_templates...")
    
    db = SessionLocal()
    try:
        # Add column to email_templates
        print("  - Adding attachments column to email_templates...")
        db.execute(text("""
            ALTER TABLE email_templates 
            ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb
        """))
        
        # Add column to marketing_email_templates
        print("  - Adding attachments column to marketing_email_templates...")
        db.execute(text("""
            ALTER TABLE marketing_email_templates 
            ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb
        """))
        
        db.commit()
        print("✓ Columns added successfully")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error adding columns: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    add_attachments_columns()
