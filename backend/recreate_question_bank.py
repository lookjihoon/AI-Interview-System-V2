"""
Quick script to drop and recreate the question_bank table with the new schema
"""
from database import engine
from sqlalchemy import text

# Drop the old table
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS question_bank CASCADE"))
    conn.commit()
    print("Dropped question_bank table")

# Recreate with new schema
from models import QuestionBank
from database import Base
Base.metadata.create_all(bind=engine, tables=[QuestionBank.__table__])
print("Recreated question_bank table with Vector column")
