import sys
import os
from sqlalchemy import text

# 현재 폴더(backend)를 파이썬이 모듈로 인식할 수 있도록 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 폴더 구조에 맞춰 안전하게 데이터베이스 엔진 불러오기
try:
    from app.database import engine
except ModuleNotFoundError:
    try:
        from database import engine
    except ModuleNotFoundError:
        print("❌ 에러: database.py 파일을 찾을 수 없습니다.")
        sys.exit(1)

def run_migration():
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE transcripts ADD COLUMN IF NOT EXISTS score INTEGER;"))
            print("✅ 성공: transcripts 테이블에 score 컬럼이 추가되었습니다!")
    except Exception as e:
        print(f"❌ 마이그레이션 중 오류 발생: {e}")

if __name__ == "__main__":
    run_migration()