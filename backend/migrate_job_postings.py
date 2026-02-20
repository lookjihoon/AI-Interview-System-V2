"""
Migration script: Add conditions, procedures, application_method columns to job_postings.
Run ONCE after updating models.py.

Usage:
    cd backend
    python migrate_job_postings.py
"""
import sys
from sqlalchemy import text
from database import engine

ALTER_STATEMENTS = [
    "ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS conditions TEXT;",
    "ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS procedures TEXT;",
    "ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS application_method TEXT;",
]

def main():
    try:
        with engine.connect() as conn:
            for stmt in ALTER_STATEMENTS:
                conn.execute(text(stmt))
                print(f"  ✓ {stmt.strip()}")
            conn.commit()
        print("\n✅ Migration successful: job_postings columns added.")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
