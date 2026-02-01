"""
Migration script to add product_templates table.
Run this script to update the database schema.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine

def migrate():
    """Create product_templates table if it doesn't exist"""
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        try:
            # Check if table exists
            check_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='product_templates'
            """)
            result = conn.execute(check_query).fetchone()
            
            if not result:
                # Create table
                create_table_query = text("""
                    CREATE TABLE product_templates (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR NOT NULL,
                        template_data TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """)
                conn.execute(create_table_query)
                
                # Create index on name
                create_index_query = text("""
                    CREATE INDEX ix_product_templates_name ON product_templates(name)
                """)
                conn.execute(create_index_query)
                
                print("✓ Created product_templates table")
            else:
                print("⊘ Table product_templates already exists")
            
            # Commit transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    print("Running database migration for product_templates...")
    migrate()
