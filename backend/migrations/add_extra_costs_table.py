"""
Migration script to create extra_costs table for dashboard extra costs (per business).
Run: python backend/migrations/add_extra_costs_table.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import engine
from sqlalchemy import text


def add_extra_costs_table():
    print("Creating extra_costs table...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS extra_costs (
                id SERIAL PRIMARY KEY,
                business_id INTEGER NOT NULL REFERENCES users(id),
                description VARCHAR(500) NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_extra_costs_business_id ON extra_costs(business_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_extra_costs_date ON extra_costs(date)"))
        conn.commit()
    print("Done. extra_costs table created.")


if __name__ == "__main__":
    add_extra_costs_table()
