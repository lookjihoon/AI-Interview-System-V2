# 웹 AI 모의면접 프로젝트 계획서 (Project Plan)

## 1. 프로젝트 개요
* **프로젝트명:** 온프레미스 AI 모의면접 시스템 구축
* **목표:** 생성형 AI(Generative AI), 컴퓨터 비전(Computer Vision), 음성 분석(Audio Analysis) 기술을 융합하여 실제 면접관을 대체/보조하는 AI 에이전트 개발.
* **핵심 가치:** 시공간 제약 없는 면접 훈련, 객관적이고 정량적인 피드백 제공.

## 2. 기술 스택 (Tech Stack)
* **Language:** Python 3.10+
* **Backend:** FastAPI (RESTful API, 비동기 처리)
* **Frontend:** Streamlit (초기 MVP), React (최종 목표)
* **AI/ML:**
    * **LLM:** llama3.1 (Local Ollama) - 질문 생성 및 답변 평가
    * **Vision:** DeepFace / MediaPipe - 비언어적 태도 분석
    * **Audio:** gTTS (TTS), Google Web Speech / Faster-Whisper (STT)
* **Database:** PostgreSQL (Vector DB: pgvector)
* **RAG:** LangChain, pypdf (이력서 분석)

## 3. 핵심 기능 요구사항 (Functional Requirements)
1.  **실시간 상호작용:** WebRTC를 통한 지연 없는 영상/음성 대화.
2.  **멀티모달 분석:** 사용자의 답변(Text) + 표정(Vision) + 목소리(Audio) 동시 분석.
3.  **RAG 기반 질문:** 사용자의 이력서와 관리자가 올린 공고(직무, 필요 기술) 대조하여 맞춤형 질문 생성.
4.  **정량적 평가:** STAR 기법 및 루브릭에 의거한 5점 척도 점수 산출.

## 4. 개발 단계 (Phases) - [Current Status: Completed]
* **Phase 1 (완료):** 기본 화상 면접 기능 구현 (STT/TTS/LLM 연동) + Vision 모듈 조기 구현.
* **Phase 2 (완료):** RAG 고도화 및 관리자 대시보드(Admin) 구축.
* **Phase 3 (완료):** 기술 면접 심화 기능 (라이브 코딩, 화이트보드) 구현.
* **Phase 4 (완료):** 시스템 최적화 (Vision Cooldown), 평가 로직 고도화 및 버그 수정.