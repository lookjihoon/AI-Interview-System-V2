"""
Migration script: Add `resume_text` column to `interview_sessions` table.
Run this ONCE after updating models.py.
Usage:
    cd backend
    python migrate_resume_text.py
"""
import sys
from sqlalchemy import text
from database import engine

ALTER_SQL = """
ALTER TABLE interview_sessions
ADD COLUMN IF NOT EXISTS resume_text TEXT;
"""

def main():
    try:
        with engine.connect() as conn:
            conn.execute(text(ALTER_SQL))
            conn.commit()
        print("✅ Migration successful: 'resume_text' column added to interview_sessions.")
    except Exception as e:
        print(f"❌ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
