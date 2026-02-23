"""Add feedback column to transcripts table if not exists."""
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE transcripts ADD COLUMN IF NOT EXISTS feedback TEXT;"
    ))
    conn.commit()
    print("✅ feedback column added (or already existed).")
