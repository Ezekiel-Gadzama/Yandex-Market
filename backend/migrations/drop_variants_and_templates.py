"""
Migration script to drop product_variants and product_templates tables
Run this script to remove the unused tables from the database.

Usage:
    python backend/migrations/drop_variants_and_templates.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import engine, SessionLocal
from sqlalchemy import text

def drop_tables():
    """Drop product_variants and product_templates tables"""
    print("Dropping product_variants and product_templates tables...")
    
    db = SessionLocal()
    try:
        # Drop product_variants table
        print("  - Dropping product_variants table...")
        db.execute(text("DROP TABLE IF EXISTS product_variants CASCADE"))
        
        # Drop product_templates table
        print("  - Dropping product_templates table...")
        db.execute(text("DROP TABLE IF EXISTS product_templates CASCADE"))
        
        db.commit()
        print("✓ Tables dropped successfully")
        
        # Verify tables are dropped
        result = db.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('product_variants', 'product_templates')
        """))
        remaining = result.fetchall()
        if remaining:
            print(f"⚠ Warning: Some tables still exist: {[r[0] for r in remaining]}")
        else:
            print("✓ Verified: Tables have been removed")
            
    except Exception as e:
        db.rollback()
        print(f"✗ Error dropping tables: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    drop_tables()
