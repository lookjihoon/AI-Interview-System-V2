"""
Migration: add deadline column to job_postings table.
Run once:
    cd backend && python add_job_deadline.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from database import engine

def run():
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS deadline TIMESTAMP"
        ))
        conn.commit()
    print("[Migration] ✅ deadline column ensured on job_postings table.")

if __name__ == "__main__":
    run()
