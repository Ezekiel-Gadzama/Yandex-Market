"""
Migration script to add stock_quantity and warehouse_id fields to products table.
Run this script to update the database schema.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine

def migrate():
    """Add stock fields to products table"""
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        try:
            # Add stock_quantity column if it doesn't exist
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='products' AND column_name='stock_quantity'
            """)
            result = conn.execute(check_query).fetchone()
            
            if not result:
                alter_query = text("ALTER TABLE products ADD COLUMN stock_quantity INTEGER DEFAULT 0")
                conn.execute(alter_query)
                print("✓ Added column: stock_quantity")
            else:
                print("⊘ Column already exists: stock_quantity")
            
            # Add warehouse_id column if it doesn't exist
            check_query2 = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='products' AND column_name='warehouse_id'
            """)
            result2 = conn.execute(check_query2).fetchone()
            
            if not result2:
                alter_query2 = text("ALTER TABLE products ADD COLUMN warehouse_id INTEGER")
                conn.execute(alter_query2)
                print("✓ Added column: warehouse_id")
            else:
                print("⊘ Column already exists: warehouse_id")
            
            # Commit transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    print("Running database migration for stock fields...")
    migrate()
