<div align="center">
  <h1>🎙️ AI 모의면접 시스템 V2 (AI Interview System V2)</h1>
  <p><strong>초개인화 RAG 질문 생성과 비언어적 멀티모달 프레임워크가 결합된 차세대 압박 면접 시뮬레이터</strong></p>

  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/React-18.2-blue?logo=react&logoColor=white" alt="React" />
    <img src="https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/PostgreSQL-%2B%20pgvector-336791.svg?logo=postgresql&logoColor=white" alt="PostgreSQL" />
    <br/>
    <img src="https://img.shields.io/badge/LLM-Exaone%203.5-black.svg?logo=ollama&logoColor=white" alt="LLM" />
    <img src="https://img.shields.io/badge/TailwindCSS-3.3-38B2AC.svg?logo=tailwind-css&logoColor=white" alt="Tailwind" />
  </p>
</div>

---

## 📖 1. 프로젝트 개요 및 핵심 기능 (About the Project)

**AI 모의면접 시스템 V2**는 구직자가 실제 기업의 면접 환경과 동일한 압박감을 경험하며 실전 감각을 키울 수 있도록 설계된 풀스택 면접 시뮬레이션 플랫폼입니다. 사용자의 이력서와 직무 기술서를 분석하여 지능적으로 꼬리 질문을 던집니다.

* **🎯 초개인화 RAG 기반 꼬리 질문**: `all-mpnet-base-v2` 임베딩과 `pgvector`를 활용하여 단순히 정해진 질문을 묻는 것이 아니라, 지원자의 답변 내용과 JD를 매핑하여 가장 날카로운 후속 질문을 동적으로 검색 및 생성합니다.
* **👁️ 멀티모달 (언어 + 비언어) 평가**: 텍스트(답변의 논리성 및 STAR 기법 준수 여부)뿐만 아니라, Vision 모델을 통해 웹캠 프레임의 표정(긴장도, 표정 변화)을 초 단위로 분석하여 비언어적 태도 점수까지 종합적으로 산출합니다.
* **🔒 100% 로컬 보안 환경 (On-Premise Ready)**: 민감한 개인정보(이력서 등)가 외부 클라우드 LLM으로 유출되는 것을 막기 위해 `Ollama (exaone 3.5)` 기반의 로컬 인퍼런스를 완벽히 지원합니다.

---

## 🛠️ 2. 기술 스택 (Tech Stack)

| 계층 (Layer) | 주요 기술 및 라이브러리 |
| :--- | :--- |
| **Frontend** | React 18, Vite, Tailwind CSS, Zustand, Recharts (데이터 시각화), React Router |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy, Alembic |
| **Database** | PostgreSQL, `pgvector` (Vector DB), Redis (세션/캐시용) |
| **AI / ML** | Ollama (`exaone 3.5`), HuggingFace (`all-mpnet-base-v2`), LangChain, DeepFace / OpenCV (비전) |
| **Audio / RTC** | Deepgram (STT), Hume AI (TTS), WebRTC (`aiortc`), WebSockets |

---

## 📂 3. 디렉토리 구조 (Directory Structure)

```text
AI_Interview_System_V2/
├── frontend/                # React 기반 프론트엔드 프로젝트
│   ├── src/
│   │   ├── components/      # UI 컴포넌트 (ChatRoom, MyPage, AdminDashboard 등)
│   │   ├── api/             # Axios 기반 API 통신 모듈
│   │   ├── App.jsx          # React Router 라우팅 설정
│   │   └── index.css        # Tailwind 글로벌 스타일시트
│   ├── package.json         # 프론트엔드 의존성 파일
│   └── vite.config.js       # Vite 빌드 설정
│
└── backend/                 # FastAPI 기반 백엔드 프로젝트
    ├── app/
    │   ├── routers/         # API 엔드포인트 분리 (admin.py, candidate.py, interview.py)
    │   └── services/        # 비즈니스 로직 (ai_service.py - 핵심 RAG/채점 로직)
    ├── models.py            # SQLAlchemy ORM 데이터베이스 스키마
    ├── schemas.py           # Pydantic 기반 요청/응답 검증 모델
    ├── database.py          # DB 커넥션 및 세션 관리
    ├── main.py              # FastAPI 진입점 및 미들웨어 (CORS, 정적 파일 마운트)
    ├── .env                 # 환경 변수 (GitHub 제외)
    └── requirements.txt     # 백엔드 의존성 패키지 명세
```

---

## 💻 4. 사전 요구사항 (Prerequisites)

이 프로젝트의 AI 모델(로컬 추론) 및 고성능 연산을 로컬에서 실행하기 위한 권장 사항입니다.

* **하드웨어 (Hardware)**: 
  * 로컬 LLM 구동을 위한 VRAM이 확보된 GPU 권장 (예: NVIDIA GTX 1660 SUPER 이상 / 6GB VRAM 이상)
  * RAM 16GB 이상 권장
* **소프트웨어 (Software)**:
  * **Python**: `3.10` 이상
  * **Node.js**: `v18` 이상 (또는 v20 권장)
  * **Database**: PostgreSQL 15+ 및 **`pgvector` Extension** 설치 필수
  * **로컬 LLM 서버**: [Ollama](https://ollama.ai/) 설치

---

## 🚀 5. 설치 및 실행 가이드 (Getting Started)

### 5.1 로컬 LLM (Ollama) 및 Redis 서버 구동
백그라운드 포트에서 로컬 모델들을 띄워둡니다.
```bash
# Ollama 백그라운드 실행 및 Exaone 3.5 모델 서빙
ollama run exaone3.5

# Redis 서버 구동 (Windows의 경우 WSL 또는 포터블 Redis 활용)
redis-server
```

### 5.2 Database 셋업 및 pgvector 활성화
PostgreSQL 데이터베이스 생성 후, RAG를 위한 벡터 확장을 반드시 등록해야 합니다.
```sql
CREATE DATABASE interview_db;
\c interview_db;
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5.3 Backend 패키지 설치 및 실행
```bash
cd backend

# 가상 환경 생성 및 진입
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# 의존성 모듈 설치 (PyTorch 등 OS 별도 설치 권장)
pip install -r requirements.txt

# DB 마이그레이션 적용 및 QnA 뱅크 레코드 시딩 로드
# (초기 세팅 스크립트 실행)

# FastAPI 서버 실행 (http://localhost:8000)
uvicorn main:app --reload
```

### 5.4 Frontend 패키지 설치 및 실행
새로운 터미널 창을 열고 프론트엔드를 실행합니다.
```bash
cd frontend

# NPM 패키지 설치
npm install

# Vite 개발 서버 실행 (http://localhost:5173)
npm run dev
```

---

## 🔐 6. 환경 변수 설정 (Environment Variables)

`backend/.env` 파일을 만들고 아래의 형식에 맞춰 할당받은 API 키와 DB 주소를 입력합니다. (보안상의 이유로 실제 값은 Git에 커밋하지 않습니다.)

```env
# --- AI 연결 키 ---
# RAG 컨텍스트 추출 시 보조 모델 생성을 위한 OpenAI 키 (필요 시)
OPENAI_API_KEY=sk-proj-...
# 실시간 음성 인식을 위한 Deepgram API 키
DEEPGRAM_API_KEY=your_deepgram_api_key...
# 로컬 임베딩(all-mpnet-base-v2 등) 모델 다운로드에 필요한 HF 토큰
HUGGING_FACE_TOKEN=hf_...

# --- Database 연결 주소 ---
# 세션 및 Async Job 큐잉용
REDIS_URL=redis://localhost:6379/0
# 메인 RDBMS 주소 (반드시 pgvector 지원 버전일 것)
POSTGRES_CONNECTION_STRING=postgresql+psycopg2://[계정명]:[비밀번호]@127.0.0.1:5432/interview_db
```