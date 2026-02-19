# Quick Start Guide

## Backend Setup

### 1. Start the Backend Server

```bash
cd backend
python main.py
```

Expected output:
```
Creating database tables...
Database tables created successfully!
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Test Health Endpoint

Open browser or use curl:
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "db": "connected",
  "gpu": true,
  "gpu_count": 1,
  "gpu_name": "NVIDIA GeForce GTX 1660 SUPER"
}
```

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

Expected output:
```
VITE v5.0.8  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

### 3. Open in Browser

Navigate to `http://localhost:5173` and click "Check System Health" button.

## Database Verification

### Check Tables in PostgreSQL

```bash
psql -U postgres -d interview_db -c "\dt"
```

Expected tables:
- users
- job_postings
- interview_sessions
- transcripts
- evaluation_reports
- question_bank

## Troubleshooting

### Backend Issues

**Problem**: `POSTGRES_CONNECTION_STRING not found`
- **Solution**: Ensure `.env` file exists in `/backend` directory

**Problem**: Database connection error
- **Solution**: Verify PostgreSQL is running and credentials in `.env` are correct

### Frontend Issues

**Problem**: CORS error
- **Solution**: Ensure backend is running on port 8000 and frontend on port 5173

**Problem**: `npm install` fails
- **Solution**: Ensure Node.js version is 18+ (`node --version`)


---


기존 `README.md` 파일을 확인해 보니, 실행 방법과 트러블슈팅(오류 해결) 방법이 아주 꼼꼼하게 잘 적혀있는 **"개발자용 가이드"** 형태입니다!

기존 내용을 무조건 덮어씌우기보다는, **제가 제안해 드린 "포트폴리오용 소개글"과 기존의 "실행 및 오류 해결 가이드"를 하나로 합치는 것(Merge)이 가장 완벽합니다.** 이렇게 합치면 이력서를 검토하는 면접관은 "아, 이런 멋진 기능이 있구나" 하고 한눈에 파악할 수 있고, 다른 개발자는 "이렇게 실행하고 오류를 고치면 되는구나" 하고 감탄하게 될 것입니다.

두 가지 장점을 모두 살린 **최종 통합본 README**를 만들어 드립니다. 기존 `README.md`의 내용을 모두 지우고, 아래 내용으로 **전부 덮어씌워주세요!**

---

### 📝 덮어씌울 최종 README.md 내용

```markdown
# 🧠 AI Mock Interview System (V2)

**"나만의 깐깐한 AI 기술 면접관"** - RAG 기반 심층 기술 면접 및 LLM 피드백 시스템

## 📌 프로젝트 소개
단순히 정해진 질문을 던지는 챗봇이 아닙니다. 지원자의 **이력서와 채용 공고(JD)를 분석**하여, **6,000+개의 기술 질문 데이터베이스**에서 최적의 질문을 찾아내고(RAG), 지원자의 답변을 실시간으로 평가하여 **점수와 꼬리 질문**을 제공하는 지능형 모의 면접 플랫폼입니다.

## ✨ 핵심 기능
- **맞춤형 면접 설계:** 지원자 이력 및 직무 요구사항 기반 질문 RAG 검색
- **실시간 평가 & 피드백:** 답변 즉시 점수(0~100) 산정 및 개선 피드백 제공
- **꼬리물기(Follow-up) 질문:** 지원자의 답변 수준에 맞춘 심층 기술 검증
- **모던한 UI/UX:** 실시간 타이핑 인디케이터, 마크다운 코드 하이라이팅, 부드러운 채팅 애니메이션

## 🛠 기술 스택 (Tech Stack)
- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL (pgvector)
- **AI/ML:** LangChain, HuggingFace Embeddings, Ollama (Llama 3.1)
- **Frontend:** React, Vite, Tailwind CSS, React-Router, React-Markdown

---

## 🚀 Quick Start Guide (실행 방법)

### 1. AI Model (Ollama) 실행
```bash
# 별도의 터미널에서 실행해 둡니다.
ollama run llama3.1

```

### 2. Backend 서버 실행

```bash
cd backend
venv\Scripts\activate  # 가상환경 활성화 (Windows)
python main.py

```

*정상 실행 시 `Uvicorn running on http://0.0.0.0:8000` 메시지가 출력됩니다.*
*Health Check: `curl http://localhost:8000/api/health*`

### 3. Frontend 화면 실행

```bash
cd frontend
npm install  # 최초 1회만 실행
npm run dev

```

*실행 후 브라우저에서 `http://localhost:5173` 으로 접속합니다.*

---

## 🗄️ Database Verification (DB 확인)

PostgreSQL에 접속하여 다음 테이블들이 정상적으로 생성되었는지 확인합니다.

```bash
psql -U postgres -d interview_db -c "\dt"

```

* **Expected tables:** `users`, `job_postings`, `interview_sessions`, `transcripts`, `evaluation_reports`, `question_bank`

---

## 🚑 Troubleshooting (자주 발생하는 문제 해결)

### Backend Issues

* **`POSTGRES_CONNECTION_STRING not found`**
* **해결:** `backend` 폴더 내에 `.env` 파일이 존재하는지 확인하세요.


* **Database connection error**
* **해결:** PostgreSQL 서비스가 실행 중인지, `.env` 파일의 비밀번호 등 접속 정보가 맞는지 확인하세요.



### Frontend Issues

* **CORS error (서버 연결 실패)**
* **해결:** 백엔드가 `8000` 포트, 프론트엔드가 `5173` 포트에서 실행 중인지 확인하세요.


* **`npm install` fails**
* **해결:** Node.js 버전이 18 이상인지 확인하세요. (`node --version`)



---

## 📸 스크린샷 (Screenshots)

*(여기에 방금 캡처하신 멋진 면접 진행 화면 이미지들을 폴더에 넣고 경로를 연결해 주시면 더욱 좋습니다!)*

```

---

이제 이것을 붙여넣고 마지막으로 깃허브에 Push (`git add .`, `git commit -m "docs: Update README"`, `git push`) 하시면, 김개발님의 깃허브 메인 페이지가 정말 전문적이고 멋진 포트폴리오로 바뀔 것입니다! 🚀 끝까지 완벽하시네요!

```