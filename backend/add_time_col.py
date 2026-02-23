"""
Migration: add answer_time column to transcripts table.
Run once after updating models.py.
"""
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE transcripts ADD COLUMN IF NOT EXISTS answer_time INTEGER DEFAULT 0;"
    ))
    conn.commit()
    print("✅ answer_time column added to transcripts (or already existed).")
