"""
Migration script to create product_variants table.
Run this script to update the database schema.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine

def migrate():
    """Create product_variants table if it doesn't exist"""
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        try:
            # Check if table exists
            check_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='product_variants'
            """)
            result = conn.execute(check_query).fetchone()
            
            if not result:
                # Create table
                create_table_query = text("""
                    CREATE TABLE product_variants (
                        id SERIAL PRIMARY KEY,
                        product_id INTEGER NOT NULL,
                        variant_name VARCHAR NOT NULL,
                        variant_sku VARCHAR UNIQUE,
                        edition VARCHAR,
                        platform VARCHAR,
                        activation_territory VARCHAR,
                        localization VARCHAR,
                        selling_price FLOAT NOT NULL,
                        original_price FLOAT,
                        cost_price FLOAT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        stock_quantity INTEGER DEFAULT 0,
                        yandex_market_id VARCHAR UNIQUE,
                        yandex_market_sku VARCHAR UNIQUE,
                        is_synced BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE,
                        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                    )
                """)
                conn.execute(create_table_query)
                
                # Create indexes
                create_indexes = [
                    text("CREATE INDEX ix_product_variants_product_id ON product_variants(product_id)"),
                    text("CREATE INDEX ix_product_variants_variant_sku ON product_variants(variant_sku)"),
                    text("CREATE INDEX ix_product_variants_yandex_market_id ON product_variants(yandex_market_id)"),
                    text("CREATE INDEX ix_product_variants_yandex_market_sku ON product_variants(yandex_market_sku)"),
                ]
                for idx_query in create_indexes:
                    conn.execute(idx_query)
                
                print("✓ Created product_variants table and indexes")
            else:
                print("⊘ Table product_variants already exists")
            
            # Commit transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    print("Running database migration for product_variants...")
    migrate()
