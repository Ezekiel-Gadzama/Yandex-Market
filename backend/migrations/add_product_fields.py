"""
Migration script to add new Yandex Market product fields to the database.
Run this script to update the database schema.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine

def migrate():
    """Add new columns to products table"""
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        try:
            # Add new columns if they don't exist
            columns_to_add = [
                ("yandex_model", "VARCHAR", "DEFAULT 'DBS'"),
                ("yandex_category_id", "VARCHAR", ""),
                ("yandex_category_path", "VARCHAR", ""),
                ("yandex_brand", "VARCHAR", ""),
                ("yandex_platform", "VARCHAR", ""),
                ("yandex_localization", "VARCHAR", ""),
                ("yandex_publication_type", "VARCHAR", ""),
                ("yandex_activation_territory", "VARCHAR", "DEFAULT 'all countries'"),
                ("yandex_edition", "VARCHAR", ""),
                ("yandex_series", "VARCHAR", ""),
                ("yandex_age_restriction", "VARCHAR", ""),
                ("yandex_activation_instructions", "BOOLEAN", "DEFAULT TRUE"),
                ("original_price", "FLOAT", ""),
                ("discount_percentage", "FLOAT", "DEFAULT 0"),
                ("yandex_images", "TEXT", ""),
                ("yandex_videos", "TEXT", ""),
            ]
            
            for column_name, column_type, default in columns_to_add:
                try:
                    # Check if column exists
                    check_query = text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='products' AND column_name='{column_name}'
                    """)
                    result = conn.execute(check_query).fetchone()
                    
                    if not result:
                        # Column doesn't exist, add it
                        alter_query = f"ALTER TABLE products ADD COLUMN {column_name} {column_type} {default}"
                        conn.execute(text(alter_query))
                        print(f"✓ Added column: {column_name}")
                    else:
                        print(f"⊘ Column already exists: {column_name}")
                except Exception as e:
                    print(f"✗ Error adding column {column_name}: {str(e)}")
            
            # Commit transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    print("Running database migration...")
    migrate()
