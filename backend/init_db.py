"""
Initialize database - runs migrations and creates default data
Run this after database is created
"""
import sys
import subprocess
from app.database import engine, Base, SessionLocal
from app import models
from app.initial_data import create_default_email_template
from sqlalchemy import text

def init_database():
    """Run Alembic migrations and create default data"""
    print("Running database migrations...")
    try:
        # Run Alembic migrations
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ Database migrations completed successfully")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"⚠ Migration output: {result.stdout}")
            print(f"⚠ Migration errors: {result.stderr}")
            # Don't exit on migration errors - they might be expected (e.g., already up to date)
    except FileNotFoundError:
        print("⚠ Alembic not found, falling back to create_all()...")
        try:
            Base.metadata.create_all(bind=engine)
            print("✓ Database tables created using create_all()")
        except Exception as e2:
            print(f"✗ Error creating tables: {e2}")
            sys.exit(1)
    except Exception as e:
        print(f"⚠ Warning: Could not run migrations: {e}")
        print("  Falling back to create_all()...")
        try:
            Base.metadata.create_all(bind=engine)
            print("✓ Database tables created using create_all()")
        except Exception as e2:
            print(f"✗ Error creating tables: {e2}")
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
    
    # Add business_id columns if they don't exist (migration)
    print("Adding business_id columns if needed...")
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
        ]
        
        for table_name, alter_sql in tables_to_update:
            try:
                db.execute(text(alter_sql))
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"  ⚠ Warning: Could not add business_id to {table_name}: {str(e)}")
        
        # Special handling for app_settings (needs UNIQUE constraint)
        try:
            db.execute(text("ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS business_id INTEGER REFERENCES users(id)"))
            db.commit()
            # Try to add unique constraint (might fail if duplicates exist)
            try:
                db.execute(text("ALTER TABLE app_settings ADD CONSTRAINT app_settings_business_id_unique UNIQUE (business_id)"))
                db.commit()
            except:
                pass  # Constraint might already exist or duplicates exist
        except Exception as e:
            db.rollback()
            print(f"  ⚠ Warning: Could not add business_id to app_settings: {str(e)}")
        
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
                print(f"  ⚠ Warning: Could not create index: {str(e)}")
        
        print("✓ Business ID columns added/verified")
    except Exception as e:
        db.rollback()
        print(f"⚠ Warning: Could not add business_id columns: {e}")
    finally:
        db.close()
    
    # Add smtp_user column to app_settings if it doesn't exist
    print("Adding smtp_user column if needed...")
    db = SessionLocal()
    try:
        db.execute(text("""
            ALTER TABLE app_settings 
            ADD COLUMN IF NOT EXISTS smtp_user VARCHAR
        """))
        db.commit()
        print("✓ smtp_user column added/verified")
    except Exception as e:
        db.rollback()
        print(f"⚠ Warning: Could not add smtp_user column: {e}")
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
