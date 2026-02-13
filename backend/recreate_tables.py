"""
Recreate all tables with updated schema
"""
from sqlalchemy import text
from database import engine, Base
from models import User, JobPosting, InterviewSession, Transcript, EvaluationReport, QuestionBank

def recreate_tables():
    """Drop and recreate all tables except question_bank"""
    print("=" * 80)
    print("Recreating Database Tables")
    print("=" * 80)
    
    with engine.connect() as conn:
        # Drop tables in reverse dependency order
        print("\nDropping existing tables...")
        tables_to_drop = [
            "evaluation_reports",
            "transcripts",
            "interview_sessions",
            "job_postings",
            "users"
        ]
        
        for table in tables_to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"  [OK] Dropped table: {table}")
            except Exception as e:
                print(f"  [ERROR] Failed to drop {table}: {e}")
        
        conn.commit()
    
    # Recreate tables
    print("\nRecreating tables with new schema...")
    Base.metadata.create_all(bind=engine)
    print("  [OK] All tables recreated successfully!")
    
    print("\n" + "=" * 80)
    print("Table Recreation Complete!")
    print("=" * 80)
    print("\nNote: question_bank table was preserved with existing data")

if __name__ == "__main__":
    recreate_tables()
