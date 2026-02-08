"""
Migration to add WAITING_CONFIRMATION to orderstatus enum in PostgreSQL
"""
from sqlalchemy import text
from app.database import engine


def upgrade():
    """Add WAITING_CONFIRMATION to orderstatus enum"""
    with engine.connect() as conn:
        # Check if WAITING_CONFIRMATION already exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'waiting_confirmation' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'orderstatus')
            );
        """))
        exists = result.scalar()
        
        if not exists:
            # Add the enum value
            conn.execute(text("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'waiting_confirmation'"))
            conn.commit()
            print("✅ Added 'waiting_confirmation' to orderstatus enum")
        else:
            print("ℹ️  'waiting_confirmation' already exists in orderstatus enum")


def downgrade():
    """Remove WAITING_CONFIRMATION from orderstatus enum (not easily reversible)"""
    # Note: PostgreSQL doesn't support removing enum values easily
    # This would require recreating the enum type
    print("⚠️  Cannot easily remove enum values in PostgreSQL. Manual intervention required.")
    pass


if __name__ == "__main__":
    upgrade()
