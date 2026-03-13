"""
Migration script to add timezone column to app_settings.
Run: python backend/migrations/add_timezone_to_app_settings.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import engine
from sqlalchemy import text


def add_timezone_column():
    print("Adding timezone column to app_settings...")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS timezone VARCHAR"))
        conn.commit()
    print("Done. timezone column added.")


if __name__ == "__main__":
    add_timezone_column()

