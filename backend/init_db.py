"""
Initialize database - creates tables and default data
Run this after database is created
"""
import sys
from app.database import engine, Base, SessionLocal
from app import models
from app.initial_data import create_default_email_template

def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created successfully")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        sys.exit(1)
    
    print("Creating default email template...")
    try:
        create_default_email_template()
        print("✓ Default email template created")
    except Exception as e:
        print(f"⚠ Warning: Could not create default template: {e}")

if __name__ == "__main__":
    init_database()
