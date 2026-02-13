"""
Verification script to check if QnA seeding was successful
"""
from database import SessionLocal
from models import QuestionBank
from sqlalchemy import func

def verify_seeding():
    """Verify that QnA data was seeded correctly"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("QnA Seeding Verification Report")
        print("=" * 80)
        
        # 1. Check total count
        total_count = db.query(QuestionBank).count()
        print(f"\n1. Total Questions: {total_count}")
        if total_count == 6108:
            print("   [OK] SUCCESS: All 6,108 questions loaded")
        elif total_count > 0:
            print(f"   [WARNING] Expected 6,108 but found {total_count}")
        else:
            print("   [ERROR] No questions found in database")
            return
        
        # 2. Check categories
        print("\n2. Questions by Category:")
        categories = db.query(
            QuestionBank.category, 
            func.count(QuestionBank.id)
        ).group_by(QuestionBank.category).all()
        
        for category, count in categories:
            print(f"   - {category}: {count} questions")
        
        # 3. Check sub-categories
        print("\n3. Questions by Sub-Category:")
        sub_categories = db.query(
            QuestionBank.sub_category, 
            func.count(QuestionBank.id)
        ).group_by(QuestionBank.sub_category).all()
        
        for sub_cat, count in sub_categories:
            print(f"   - {sub_cat}: {count} questions")
        
        # 4. Check embeddings
        print("\n4. Embedding Verification:")
        questions_with_embeddings = db.query(QuestionBank).filter(
            QuestionBank.embedding.isnot(None)
        ).count()
        
        print(f"   - Questions with embeddings: {questions_with_embeddings}/{total_count}")
        
        if questions_with_embeddings == total_count:
            print("   [OK] SUCCESS: All questions have embeddings")
        else:
            print(f"   [WARNING] {total_count - questions_with_embeddings} questions missing embeddings")
        
        # 5. Sample questions
        print("\n5. Sample Questions:")
        samples = db.query(QuestionBank).limit(3).all()
        
        for i, sample in enumerate(samples, 1):
            print(f"\n   Sample {i}:")
            print(f"   - ID: {sample.id}")
            print(f"   - Category: {sample.category} / {sample.sub_category}")
            print(f"   - Question: {sample.question_text[:80]}...")
            print(f"   - Has Answer: {sample.model_answer is not None}")
            print(f"   - Has Embedding: {sample.embedding is not None}")
            if sample.embedding is not None:
                print(f"   - Embedding Dimension: {len(sample.embedding)}")
        
        # 6. Check embedding dimensions
        print("\n6. Embedding Dimension Check:")
        sample_with_embedding = db.query(QuestionBank).filter(
            QuestionBank.embedding.isnot(None)
        ).first()
        
        if sample_with_embedding and sample_with_embedding.embedding is not None:
            dim = len(sample_with_embedding.embedding)
            print(f"   - Embedding dimension: {dim}")
            if dim == 768:
                print("   [OK] SUCCESS: Correct dimension (768)")
            else:
                print(f"   [ERROR] Expected 768 but found {dim}")
        
        print("\n" + "=" * 80)
        print("Verification Complete!")
        print("=" * 80)
        
        # Summary
        if total_count == 6108 and questions_with_embeddings == total_count:
            print("\n[OK] ALL CHECKS PASSED - Seeding was successful!")
        else:
            print("\n[WARNING] SOME ISSUES DETECTED - Please review the report above")
        
    except Exception as e:
        print(f"\n[ERROR] during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_seeding()
