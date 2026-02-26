from database import engine
from sqlalchemy import text

def upgrade():
    try:
        with engine.connect() as conn:
            # PostgreSQL에 맞게 JSONB 타입으로 컬럼 추가
            conn.execute(text("ALTER TABLE evaluation_reports ADD COLUMN IF NOT EXISTS emotion_timeline JSONB;"))
            conn.commit()
        print("✅ 성공: PostgreSQL DB에 emotion_timeline 컬럼이 무사히 추가되었습니다!")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    upgrade()