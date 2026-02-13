"""
Update JobStatus enum in database
"""
from sqlalchemy import text
from database import engine

def update_job_status_enum():
    """Update JobStatus enum to include ACTIVE, CLOSED, DRAFT"""
    print("=" * 80)
    print("Updating JobStatus Enum")
    print("=" * 80)
    
    with engine.connect() as conn:
        try:
            # Drop the old enum type (CASCADE will update all dependent columns)
            print("\nDropping old jobstatus enum...")
            conn.execute(text("DROP TYPE IF EXISTS jobstatus CASCADE"))
            conn.commit()
            print("  [OK] Dropped old enum")
            
            # Create new enum with updated values
            print("\nCreating new jobstatus enum...")
            conn.execute(text("CREATE TYPE jobstatus AS ENUM ('ACTIVE', 'CLOSED', 'DRAFT')"))
            conn.commit()
            print("  [OK] Created new enum with values: ACTIVE, CLOSED, DRAFT")
            
            # Recreate the job_postings table to use the new enum
            print("\nRecreating job_postings table...")
            conn.execute(text("DROP TABLE IF EXISTS job_postings CASCADE"))
            conn.execute(text("""
                CREATE TABLE job_postings (
                    id SERIAL NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    description TEXT NOT NULL,
                    requirements TEXT,
                    min_experience INTEGER NOT NULL DEFAULT 0,
                    target_capabilities TEXT,
                    status jobstatus NOT NULL DEFAULT 'ACTIVE',
                    posted_date DATE DEFAULT CURRENT_DATE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                    PRIMARY KEY (id)
                )
            """))
            conn.execute(text("CREATE INDEX ix_job_postings_status ON job_postings (status)"))
            conn.execute(text("CREATE INDEX ix_job_postings_id ON job_postings (id)"))
            conn.commit()
            print("  [OK] Recreated job_postings table")
            
            print("\n" + "=" * 80)
            print("JobStatus Enum Update Complete!")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n[ERROR] Failed to update enum: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    update_job_status_enum()
