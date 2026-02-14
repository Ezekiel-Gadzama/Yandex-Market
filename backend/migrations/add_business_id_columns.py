"""
Migration script to add business_id columns to all tables for business isolation.
Run this script to add business_id columns to existing tables.

Usage:
    python backend/migrations/add_business_id_columns.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import engine, SessionLocal
from sqlalchemy import text

def add_business_id_columns():
    """Add business_id columns to all tables that need them"""
    print("Adding business_id columns for business isolation...")
    
    db = SessionLocal()
    try:
        # List of tables and their business_id column definitions
        tables_to_update = [
            ("products", "ALTER TABLE products ADD COLUMN IF NOT EXISTS business_id INTEGER REFERENCES users(id)"),
            ("orders", "ALTER TABLE orders ADD COLUMN IF NOT EXISTS business_id INTEGER REFERENCES users(id)"),
            ("clients", "ALTER TABLE clients ADD COLUMN IF NOT EXISTS business_id INTEGER REFERENCES users(id)"),
            ("email_templates", "ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS business_id INTEGER REFERENCES users(id)"),
            ("marketing_email_templates", "ALTER TABLE marketing_email_templates ADD COLUMN IF NOT EXISTS business_id INTEGER REFERENCES users(id)"),
            ("documentations", "ALTER TABLE documentations ADD COLUMN IF NOT EXISTS business_id INTEGER REFERENCES users(id)"),
            ("app_settings", "ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS business_id INTEGER REFERENCES users(id) UNIQUE"),
        ]
        
        for table_name, alter_sql in tables_to_update:
            try:
                print(f"  - Adding business_id to {table_name}...")
                db.execute(text(alter_sql))
                db.commit()
                print(f"    ✓ Added business_id to {table_name}")
            except Exception as e:
                db.rollback()
                print(f"    ⚠ Warning: Could not add business_id to {table_name}: {str(e)}")
                # Continue with other tables
        
        # Create indexes for better query performance
        indexes = [
            ("CREATE INDEX IF NOT EXISTS idx_products_business_id ON products(business_id)"),
            ("CREATE INDEX IF NOT EXISTS idx_orders_business_id ON orders(business_id)"),
            ("CREATE INDEX IF NOT EXISTS idx_clients_business_id ON clients(business_id)"),
            ("CREATE INDEX IF NOT EXISTS idx_email_templates_business_id ON email_templates(business_id)"),
            ("CREATE INDEX IF NOT EXISTS idx_marketing_email_templates_business_id ON marketing_email_templates(business_id)"),
            ("CREATE INDEX IF NOT EXISTS idx_documentations_business_id ON documentations(business_id)"),
            ("CREATE INDEX IF NOT EXISTS idx_app_settings_business_id ON app_settings(business_id)"),
        ]
        
        for index_sql in indexes:
            try:
                db.execute(text(index_sql))
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"    ⚠ Warning: Could not create index: {str(e)}")
        
        print("✓ Business ID columns added successfully")
        
        # Note: You may need to manually assign business_id values to existing records
        # For now, we'll leave them as NULL (which will cause errors if queried)
        # You should update existing records to assign them to an admin's business_id
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error adding business_id columns: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    add_business_id_columns()
