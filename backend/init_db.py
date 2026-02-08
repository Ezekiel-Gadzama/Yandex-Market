"""
Initialize database - creates tables and default data
Run this after database is created
"""
import sys
from app.database import engine, Base, SessionLocal
from app import models
from app.initial_data import create_default_email_template
from sqlalchemy import text

def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created successfully")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        sys.exit(1)
    
    # Add attachments columns if they don't exist (migration)
    print("Adding attachments columns if needed...")
    db = SessionLocal()
    try:
        # Add column to email_templates
        db.execute(text("""
            ALTER TABLE email_templates 
            ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb
        """))
        
        # Add column to marketing_email_templates
        db.execute(text("""
            ALTER TABLE marketing_email_templates 
            ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb
        """))
        
        db.commit()
        print("✓ Attachments columns added/verified")
    except Exception as e:
        db.rollback()
        print(f"⚠ Warning: Could not add attachments columns: {e}")
    finally:
        db.close()
    
    print("Creating default email template...")
    try:
        create_default_email_template()
        print("✓ Default email template created")
    except Exception as e:
        print(f"⚠ Warning: Could not create default template: {e}")

if __name__ == "__main__":
    init_database()
