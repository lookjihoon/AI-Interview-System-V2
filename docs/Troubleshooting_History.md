# AI 모의 면접 시스템 V2: 핵심 트러블슈팅 (Troubleshooting History)

본 문서는 플랫폼 개발 과정에서 직면했던 가장 치명적인 기술적 장애 현상들(병목 현상, 데이터 증발, 오디오 동기화 문제 등)을 분석하고, 이를 아키텍처 및 코드 레벨에서 근본적으로 해결한 과정을 기록한 문서입니다.

---

### 1. 웹 브라우저 Autoplay 정책 제어 및 Audio/TTS 동기화 레이스 컨디션 충돌
- **문제 상황 (Problem)**: 
  초기 애플리케이션에서는 AI 면접 방(`ChatRoom.jsx`) 진입 시, LLM이 생성한 첫 인사말 오디오(TTS) 파일이 재생되지 않는 현상이 빈번하게 발생했습니다. 간헐적으로는 에러 로그 없이 조용히 실패하기도 했으며, 컴포넌트 마운트 생명주기와 비동기 오디오 Fetch 속도가 엇갈리며 *NotSupportedError (404)* 에러를 뿜기도 했습니다.
- **원인 분석 (Root Cause)**:
  1. **브라우저의 보안 정책 (Autoplay Policy)**: 크롬 등 모던 브라우저는 사용자의 명시적 인터랙션(Click, Tap) 없이 미디어 음원이 자동 재생되는 것을 엄격히 차단(DOMException: play() failed)합니다. 면접 방에 라우팅 되자마자 TTS를 재생하려 했기에 블락당한 것입니다.
  2. **React 상태와 Audio 재생의 레이스 컨디션**: 기존 코드는 `useEffect` 훅 내에서 `audioRef`와 상태 변수를 реак티브하게 엮어 두었는데, TTS 음성이 백엔드 스태틱 볼륨(`uploads/audio`)에 마운트되기 이전에 프론트엔드 컴포넌트가 재생을 시도하는 타이밍 역전 현상이 발생했습니다.
- **해결 방안 (Solution)**:
  - **사용자 인터랙션 사전 유도 구조 (Green Room 설계)**: 면접 방 진입 직전 `InterviewSetup.jsx` 대기실을 신설하여, 사용자가 **"면접 시작" 버튼을 직접 클릭**하게 만들었습니다. 이 인터랙션 이벤트를 통해 브라우저 오디오 컨텍스트가 뚫리도록 하였으며, `sessionStorage`를 경유해 첫 오디오 URL을 안전하게 패스했습니다.
  - **단일 Audio 객체 관리 (`new Audio()`)**: 동적 렌더링에 휘둘리지 않도록, React State에서 미디어 객체를 완전히 분리했습니다. `ChatRoom.jsx` 내부에 `audioRef.current = new Audio()`로 바닐라 DOM 객체를 명시적으로 생성하고, 비동기 호출이 완벽히 끝난 `.then()` 체인 안에서만 `.src`를 할당하고 `.play()`를 트리거하여 레이스 컨디션을 완벽히 수습했습니다.

---

### 2. LLM 환각(Hallucination)에 의한 JSON 파싱 에러 및 시스템 마비
- **문제 상황 (Problem)**:
  면접이 끝나고 `generate_final_report` 엔드포인트가 호출될 때, 간헐적으로 `json.decoder.JSONDecodeError`를 뱉으며 백엔드 처리가 중단되는 크래시가 발생했습니다. 이로 인해 지원자에게 최종 리포트 결과 화면이 노출되지 않고 로딩 스피너에서 영원히 멈추는(Infinite Loading) 병목 현상을 겪었습니다.
- **원인 분석 (Root Cause)**:
  - 평가 리포트 텍스트(강점, 약점 등)를 작성하는 `exaone 3.5` LLM 모델이 프롬프트 지시를 무시하고 출력물에 Markdown 마크업 기호(`````json ... `````)를 강제로 씌우거나, 생성 토큰 길이(`num_predict`)에 도달하여 중도 하차(Token Collapse)하며 깨진 JSON 포맷을 반환했기 때문입니다.
- **해결 방안 (Solution)**:
  - **순수 컴파일 파서 (Sanitization) 탑재**: 백엔드 파이썬 코드(`ai_service.py`) 내에 응답 결과를 중간 가공하는 로직을 삽입했습니다. 반환된 Raw Text에서 `if "```json"` 문구를 찾아내 강제로 걷어내고, 알맹이만 `split`하여 정제했습니다.
  - **Hard-Override 기반 파이썬 점수 분리**: LLM이 JSON 형식을 파괴할 때를 대비해, 숫자로 된 **핵심 채점 지표(평균 턴 점수, 비언어적 점수)들은 LLM 프롬프트 생성 이전에 미리 파이썬 정수(`int`) 연산으로 도출하여 최종 딕셔너리에 덮어쓰도록(Hard Override) 아키텍처를 변경**했습니다. 최악의 경우(`Fallback`)에도 점수는 사용자에게 반환되게 끔 Exception 처리를 강화해 시스템 마비를 원천 봉쇄했습니다.

---

### 3. Pydantic 스키마 검증 누락으로 인한 데이터 사일로(Data Silo) 증발 현상
- **문제 상황 (Problem)**:
  Vision AI를 도입해 화면에 표정(감정) 카운트를 기록하고 DB(`EvaluationReport.non_verbal_score`, `emotion_timeline`)에도 성공적으로 적재했으나, 정작 최종 면접 리포트 화면(Report.jsx)에는 이 값들이 계속 빈 값(Null)으로 내려와 그래프가 그려지지 않는 현상이 발생했습니다.
- **원인 분석 (Root Cause)**:
  - FastAPI의 강력한 타입 검증기인 **Pydantic Schema**가 양날의 검으로 작용했습니다. DB 모델 파일(`models.py`)에는 컬럼이 정상적으로 추가되었고 ORM 쿼리도 통과했지만, 프론트엔드로 데이터를 반환하는 `Response Model` 패키지(`serializers`/`schemas`, 본 프로젝트에서는 `ReportResponse` 스키마) 내에 실수로 해당 신규 필드(`non_verbal_score`, `emotion_timeline`)를 누락시켰던 것입니다. 
  - FastAPI는 선언되지 않은 응답 데이터를 보안상의 이유로 **Silent Stripping(알림 없이 데이터 잘라내기)** 처리하기 때문에, 백엔드에는 떡하니 데이터가 있는데 프론트엔드로 나가는 JSON 통로에선 데이터가 증발해버린 것입니다.
- **해결 방안 (Solution)**:
  - `routers/interview.py` 파일상에 종속된 `class ReportResponse(BaseModel):` 스키마를 점검하고, `non_verbal_score: Optional[int] = None`와 `emotion_timeline: Optional[list] = None` 명세를 즉각 업데이트했습니다.
  - RESTful API 개발에서 데이터베이스 마이그레이션을 할 때는 항상 **"DB 모델 스키마 ➡️ 데이터 매핑 ➡️ API 응답 스키마"** 3계층을 동시에 추적(Trace)해야 한다는 규칙을 정립하는 계기가 되었습니다.
