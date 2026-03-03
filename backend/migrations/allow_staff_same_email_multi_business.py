"""
Migration: Allow same staff email in multiple businesses.
- Remove unique constraint on email
- Add unique index: admins have unique email; staff have unique (email, created_by_id)

Usage: python backend/migrations/allow_staff_same_email_multi_business.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from sqlalchemy import text

def run():
    db = SessionLocal()
    try:
        # Drop existing unique constraint on email (PostgreSQL)
        try:
            db.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key"))
            db.commit()
        except Exception:
            db.rollback()
        # Create partial unique index for admins (email unique among admins)
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_admin_email_unique
            ON users (email) WHERE is_admin = true
        """))
        db.commit()
        # Create unique index for staff (email + created_by_id)
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_staff_email_business_unique
            ON users (email, created_by_id) WHERE is_admin = false AND created_by_id IS NOT NULL
        """))
        db.commit()
        print("Migration completed: staff can now use same email across businesses")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run()
