"""
Migration: add resume_path column to users table.
Run once:
    cd backend && python add_user_resume_path.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from database import engine


def run():
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS resume_path VARCHAR(512)"
        ))
        conn.commit()
    print("[Migration] ✅  resume_path column ensured on users table.")


if __name__ == "__main__":
    run()
