# AI 모의면접 시스템 온프레미스 개발 로드맵 (Development Roadmap)

## 1. 개요 (Overview)
본 문서는 '웹 AI 모의면접 프로젝트 계획서'와 'UI/기능 명세서'를 기반으로, 현재 온프레미스(Streamlit+FastAPI) 환경에서의 개발 현황을 분석하고 단계별 실행 계획을 정의한다.
**핵심 목표:** 제한된 로컬 자원(GPU VRAM 6GB) 하에서 '멀티모달 상호작용'과 '심층 평가'가 가능한 MVP(Minimum Viable Product) 완성.

---

## 2. 현황 분석 (Gap Analysis: As-Is vs To-Be)

| 구분 | 현재 구현 상태 (As-Is) | 목표 시스템 (To-Be) | 개발 난이도 |
| :--- | :--- | :--- | :--- |
| **아키텍처** | **Monolithic** (Streamlit이 UI+로직 처리) | **Event-Driven Microservices** (FastAPI Core + Celery + React) | ★★★★☆ |
| **Vision** | **단순 스트리밍** (WebRTC) | **감정/비언어 분석** (DeepFace, 시선 추적) | ★★★☆☆ |
| **기능** | **화상 면접** (Chat 중심) |  |
| **사용자** | **단일 사용자** (세션 ID로 구분) | **회원/관리자 분리** (로그인, 대시보드) | ★★☆☆☆ |
| **데이터** | **기본 저장** (파일/DB 단순 기록) | **상세 리포트 & 통계** (STAR 기법, Radar Chart) | ★★★☆☆ |

---

## 3. 단계별 실행 계획 (Action Plan)

현재 개발 전략은 **Option A (Streamlit 고도화)**를 채택한다. React로의 전면 재개발보다는, Streamlit 생태계를 활용하여 기능적 요구사항을 우선 충족하는 것을 목표로 한다.

### [Phase 1] Vision 분석 모듈 탑재 (Brain & Eye 연결) 
* **목표:** 면접 도중 지원자의 표정(긴장, 당황, 자신감)과 시선 처리를 분석하여 평가 루브릭에 반영.
* **기술 스택:** `DeepFace`, `OpenCV`, `WebRTC / WebSocket`
* **세부 작업:**
    1.  `app.py`: WebRTC 스트리머에 `VideoProcessor` 클래스 구현.
    2.  **Sampling 전략:** GPU 부하 방지를 위해 매 프레임이 아닌 **0.5초~1초 간격**으로 프레임 캡처 및 분석.
    3.  `main_yjh.py`: 분석된 감정 데이터(Emotion JSON)를 수신하고 시계열 DB(또는 Redis)에 저장하는 로직 추가.
    4.  **평가 반영:** 면접 종료 후 `EvaluationReport` 생성 시 Vision 점수(비언어적 태도) 합산.

### [Phase 2] 관리자(Recruiter) 기능 및 대시보드 구현
* **목표:** 채용 공고 관리, 공고 등록, 면접 결과 통계 확인 기능 구현.
* **기술 스택:** `Streamlit-Authenticator`, `Plotly`
* **세부 작업:**
    1.  **인증:** 관리자/지원자 로그인 분리 (Simple Auth).
    2.  **Admin Page:** 공고 등록 및 RAG 벡터 DB 인덱싱 관리 UI.
    3.  **Dashboard:** 지원자별 종합 점수(Radar Chart), 상세 피드백 조회 화면 구현.

### [Phase 3] 비동기 처리 및 최적화 (Architecture Refactoring)
* **목표:** 리포트 생성, 영상 인코딩 등 무거운 작업의 백그라운드 처리로 반응 속도 개선.
* **기술 스택:** `Celery`, `Redis`
* **세부 작업:**
    1.  **Task Queue:** `generate_report` 등 3초 이상 걸리는 작업을 Celery 워커로 위임.
    2.  **Notification:** 작업 완료 시 UI에 알림을 주는 Polling 또는 WebSocket 구조 적용.

---

## 4. 제약 사항 (Constraints)
* **Hardware:** Local GPU (GTX 1660 Super, VRAM 6GB) 환경을 준수해야 함.
* **Model Selection:** VRAM 용량을 고려하여 LLM은 `llama3.1` 수준의 경량 모델을 유지하며, Vision 모델(DeepFace) 로드시 메모리 관리에 유의할 것.