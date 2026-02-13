"""
QnA Dataset Seeding Script with Vector Embeddings

This script loads the qna_data.json file and populates the question_bank table
with embeddings generated using sentence-transformers/all-mpnet-base-v2.

Usage:
    python seed_qna.py

Requirements:
    - PostgreSQL with pgvector extension enabled
    - All dependencies from requirements.txt installed
    - qna_data.json file in backend/data/ directory
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict

from sqlalchemy.orm import Session
from tqdm import tqdm
from langchain_community.embeddings import HuggingFaceEmbeddings

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from database import SessionLocal, engine, Base
from models import QuestionBank


def load_qna_data(file_path: str) -> List[Dict]:
    """Load QnA data from JSON file"""
    print(f"Loading QnA data from {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} questions")
    return data


def initialize_embeddings():
    """Initialize HuggingFace embeddings model"""
    print("Initializing embedding model (sentence-transformers/all-mpnet-base-v2)...")
    print("This may take a few minutes on first run as it downloads the model...")
    
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        model_kwargs={'device': 'cuda'},  # Use 'cpu' if no GPU available
        encode_kwargs={'normalize_embeddings': True}
    )
    
    print("Embedding model initialized successfully!")
    return embeddings


def categorize_question(question_id: int, question_text: str) -> tuple:
    """
    Categorize questions based on content.
    This is a simple heuristic - can be improved with ML classification.
    
    Returns: (category, sub_category)
    """
    question_lower = question_text.lower()
    
    # Technical keywords
    tech_keywords = ['딥러닝', '머신러닝', 'cnn', 'rnn', 'transformer', '알고리즘', 
                     '데이터', '모델', '학습', 'gpu', 'python', 'sql']
    
    # Behavioral keywords
    behavioral_keywords = ['경험', '프로젝트', '팀', '협업', '문제', '해결', 
                          '도전', '실패', '성공', '리더십']
    
    # Check for technical questions
    if any(keyword in question_lower for keyword in tech_keywords):
        category = "TECHNICAL"
        # Further subcategorization
        if any(word in question_lower for word in ['딥러닝', 'cnn', 'rnn', 'transformer']):
            sub_category = "AI/ML"
        elif any(word in question_lower for word in ['알고리즘', '자료구조']):
            sub_category = "CS"
        else:
            sub_category = "GENERAL_TECH"
    
    # Check for behavioral questions
    elif any(keyword in question_lower for keyword in behavioral_keywords):
        category = "BEHAVIORAL"
        sub_category = "EXPERIENCE"
    
    # Default to basic
    else:
        category = "BASIC"
        sub_category = "GENERAL"
    
    return category, sub_category


def seed_questions(db: Session, qna_data: List[Dict], embeddings):
    """Seed questions into database with embeddings"""
    print(f"\nSeeding {len(qna_data)} questions into database...")
    print("Generating embeddings and inserting records...")
    
    # Check if table already has data
    existing_count = db.query(QuestionBank).count()
    if existing_count > 0:
        print(f"Warning: question_bank table already contains {existing_count} records.")
        response = input("Do you want to clear existing data? (yes/no): ")
        if response.lower() == 'yes':
            print("Clearing existing data...")
            db.query(QuestionBank).delete()
            db.commit()
            print("Existing data cleared.")
        else:
            print("Skipping seeding. Exiting...")
            return
    
    # Process in batches for efficiency
    batch_size = 50
    total_batches = (len(qna_data) + batch_size - 1) // batch_size
    
    for batch_idx in tqdm(range(total_batches), desc="Processing batches"):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(qna_data))
        batch = qna_data[start_idx:end_idx]
        
        # Extract questions for batch embedding
        questions = [item['question'] for item in batch]
        
        # Generate embeddings for batch
        batch_embeddings = embeddings.embed_documents(questions)
        
        # Create database records
        for item, embedding in zip(batch, batch_embeddings):
            category, sub_category = categorize_question(item['id'], item['question'])
            
            question_record = QuestionBank(
                category=category,
                sub_category=sub_category,
                question_text=item['question'],
                model_answer=item['answer'],
                embedding=embedding  # pgvector will handle the list conversion
            )
            db.add(question_record)
        
        # Commit batch
        db.commit()
    
    print(f"\n✅ Successfully seeded {len(qna_data)} questions with embeddings!")


def verify_seeding(db: Session):
    """Verify that data was seeded correctly"""
    print("\nVerifying seeded data...")
    
    total_count = db.query(QuestionBank).count()
    print(f"Total questions in database: {total_count}")
    
    # Count by category
    categories = db.query(QuestionBank.category, 
                         db.func.count(QuestionBank.id)).group_by(QuestionBank.category).all()
    
    print("\nQuestions by category:")
    for category, count in categories:
        print(f"  {category}: {count}")
    
    # Sample a few questions
    print("\nSample questions:")
    samples = db.query(QuestionBank).limit(3).all()
    for sample in samples:
        print(f"\n  ID: {sample.id}")
        print(f"  Category: {sample.category} / {sample.sub_category}")
        print(f"  Question: {sample.question_text[:100]}...")
        print(f"  Has embedding: {sample.embedding is not None}")
        if sample.embedding:
            print(f"  Embedding dimension: {len(sample.embedding)}")


def main():
    """Main execution function"""
    print("=" * 80)
    print("QnA Dataset Seeding Script")
    print("=" * 80)
    
    # Paths
    data_file = Path(__file__).parent / "data" / "qna_data.json"
    
    if not data_file.exists():
        print(f"Error: QnA data file not found at {data_file}")
        sys.exit(1)
    
    # Load data
    qna_data = load_qna_data(str(data_file))
    
    # Initialize embeddings model
    embeddings = initialize_embeddings()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Seed questions
        seed_questions(db, qna_data, embeddings)
        
        # Verify
        verify_seeding(db)
        
        print("\n" + "=" * 80)
        print("✅ Seeding completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
