# AI 모의면접 시스템 DB 스키마 설계서 (Database Schema: interview_v2)

## 1. 개요 (Overview)
본 문서는 'UI 세부기능명세서'를 기반으로 설계된 온프레미스 AI 모의면접 시스템의 데이터베이스(`interview_v2`) 구조를 정의한다.
데이터베이스는 **PostgreSQL**을 사용하며, RAG(검색 증강 생성)를 위한 벡터 연산(`pgvector`)과 유연한 데이터 저장을 위한 JSONB 타입을 적극 활용한다.

---

## 2. 엔티티 관계도 (ERD Structure)

시스템은 크게 **사용자(User)**, **채용공고(Job)**, **면접(Interview)**, **평가(Evaluation)**, **질문은행(Question)**의 5대 핵심 모듈로 구성된다.

### 2.1. Users (사용자 및 관리자)
시스템의 모든 사용자(지원자 및 인사담당자) 정보를 관리한다.
* **Table Name:** `users`
* **Columns:**
    * `id` (PK, Integer): 고유 식별자 (Auto Increment)
    * `email` (String, Unique): 로그인 ID (이메일 형식)
    * `password_hash` (String): 암호화된 비밀번호 (bcrypt)
    * `name` (String): 사용자 실명
    * `phone` (String): 전화번호
    * `birth_date` (Date): 생년월일
    * `role` (Enum): `CANDIDATE` (지원자), `ADMIN` (관리자/면접관)
    * `created_at` (DateTime): 가입 일시

### 2.2. JobPostings (채용 공고)
관리자가 등록한 면접 공고를 관리하며, 면접 세션의 기준이 된다.
* **Table Name:** `job_postings`
* **Columns:**
    * `id` (PK, Integer): 고유 식별자
    * `title` (String): 공고 제목 (예: "2026 상반기 백엔드 공채")
    * `content` (Text): 직무 기술서(JD) 및 자격 요건
    * `status` (String): `OPEN` (진행중), `CLOSED` (마감)
    * `required_keywords` (String): RAG 매칭을 위한 필수 직무 키워드 (예: "Python, AWS")
    * `created_at` (DateTime): 등록 일시

### 2.3. InterviewSessions (면접 세션)
지원자가 특정 공고에 지원하여 진행한 면접의 단위(Session)를 저장한다.
* **Table Name:** `interview_sessions`
* **Columns:**
    * `id` (PK, Integer): 고유 식별자
    * `user_id` (FK -> users.id): 지원자 ID
    * `job_posting_id` (FK -> job_postings.id): 지원한 공고 ID
    * `resume_path` (String): 업로드된 이력서 파일 경로 (`uploads/...`)
    * `status` (String): `IN_PROGRESS` (진행중), `COMPLETED` (완료), `CANCELED` (취소)
    * `created_at` (DateTime): 면접 시작 일시

### 2.4. Transcripts (대화 기록)
면접 중 오간 모든 대화 내용과 감정 상태를 시계열로 저장한다.
* **Table Name:** `transcripts`
* **Columns:**
    * `id` (PK, Integer): 고유 식별자
    * `session_id` (FK -> interview_sessions.id): 세션 ID
    * `sender` (String): `ai` (면접관) 또는 `human` (지원자)
    * `content` (Text): 대화 내용 (STT 결과 또는 AI 생성 질문)
    * `emotion` (String): Vision/Audio 분석 결과 (예: `{"fear": 0.8, "neutral": 0.2}`)
    * `timestamp` (DateTime): 발화 시간

### 2.5. EvaluationReports (최종 평가 리포트)
면접 종료 후 산출된 정량적 점수와 상세 피드백을 저장한다.
* **Table Name:** `evaluation_reports`
* **Columns:**
    * `id` (PK, Integer): 고유 식별자
    * `session_id` (FK -> interview_sessions.id): 세션 ID
    * `total_score` (Integer): 종합 점수 (0~100)
    * `tech_score` (Integer): 기술 역량 점수
    * `communication_score` (Integer): 의사소통 점수
    * `problem_solving_score` (Integer): 문제해결력 점수
    * `non_verbal_score` (Integer): **(New)** 비언어적 태도 점수 (Vision 분석 기반)
    * `summary` (Text): AI의 한 줄 총평
    * `details` (JSONB): 항목별 상세 피드백 및 루브릭 매칭 결과 (JSON 구조)
    * `created_at` (DateTime): 생성 일시

### 2.6. QuestionBank (면접 질문 데이터셋)
6,000여 개의 면접 질문과 임베딩 벡터를 저장하는 RAG 지식 베이스.
* **Table Name:** `question_bank`
* **Columns:**
    * `id` (PK, Integer): 고유 식별자
    * `category` (String): 대분류 (BASIC, INDUSTRY, COMPANY)
    * `sub_category` (String): 소분류 (인성, 기술, CS 등)
    * `question_text` (Text): 질문 내용
    * `model_answer` (Text): 모범 답안 (평가 기준용)
    * `embedding_json` (JSON/Vector): 질문 텍스트의 임베딩 벡터값 (pgvector 연동)

---

## 3. 구현 가이드 (Implementation Guide)

### 3.1. SQLAlchemy Models
에이전트는 위 스키마를 바탕으로 `models.py`를 작성할 때 다음 사항을 준수해야 한다.
1.  **JSONB 사용:** `EvaluationReports.details`와 `QuestionBank.embedding_json`은 유연성을 위해 JSON 타입으로 정의한다.
2.  **관계 설정:** `relationship`을 사용하여 `Session` -> `Transcripts`, `Session` -> `EvaluationReport` 간의 1:N, 1:1 관계를 명시한다.
3.  **확장성:** 추후 `Users` 테이블에 소셜 로그인(SNS) 컬럼이 추가될 수 있음을 고려한다.

### 3.2. RAG 검색 최적화
* `QuestionBank` 테이블은 자주 조회되므로 `category`와 `sub_category`에 인덱스(Index)를 설정한다.
* `required_keywords`를 활용하여 1차 필터링 후, 벡터 유사도 검색을 수행한다.