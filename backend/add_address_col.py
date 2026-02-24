"""
Migration: add address column to users table and ensure password_hash column exists.
Run once after pulling this update:
    cd backend && python add_address_col.py
"""
import sys
import os

# Allow running from the backend directory
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from database import engine


def run():
    with engine.connect() as conn:
        # Add address column (safe — IF NOT EXISTS)
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS address VARCHAR(255)"
        ))
        # Ensure password_hash column exists (was nullable from the start, but double-check)
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"
        ))
        conn.commit()
    print("[Migration] ✅ address + password_hash columns ensured on users table.")


if __name__ == "__main__":
    run()
