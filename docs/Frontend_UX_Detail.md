# AI 모의 면접 시스템 V2: Frontend UX 및 세부 기능 명세서

본 문서는 프론트엔드 핵심 컴포넌트(`ChatRoom.jsx`, `InterviewSetup.jsx`, `MyPage.jsx` 등)의 코드를 정밀하게 스캔하여, 플랫폼의 **사용자 경험(UX) 및 인터페이스(UI) 최적화 전략**을 정리한 기술 명세서입니다.

---

## 1. 미디어 권한 및 예외 처리 (WebRTC & Error Handling) 📷

브라우저 기반 화상 면접의 가장 큰 병목인 '하드웨어 권한 문제'를 해결하기 위해 방어적 UI 설계가 적용되었습니다.

- **권한 진입점 (Green Room UX)**: 
  - `InterviewSetup.jsx`에서 사전 모의 환경(Setup Mode)을 제공합니다. 
  - `navigator.mediaDevices.getUserMedia({ video: true, audio: true })` 호출 시 `catch (err)` 블록을 통해 사용자가 권한을 거부하거나 카메라가 없을 경우, 에러 스택을 캐치하고 **"카메라 및 마이크 권한을 허용해주세요"**라는 Red Toast 알림(상단 중앙 팝업)을 띄워 인지시킵니다.
- **카메라 이탈 및 인식 실패 (Fallback UI)**:
  - `ChatRoom.jsx` 진행 중 카메라가 꺼지거나 예외가 발생하면 `cameraActive` 상태 플래그가 꺼지며, 검은색 `slate-800` 배경 중앙에 **"👤❌ 카메라 꺼짐"** 이라는 슬레이트 대체 화면이 오버레이됩니다.
  - 얼굴 인식(Face Detection) 실패 시엔 `faceError` 상태를 감지해, 웹캠 위에 75% 불투명도의 검은막(`bg-black/75 z-20`)을 씌우고 **"카메라에 얼굴 인식이 제대로 이루어지지 않고 있습니다"**라는 경고 텍스트를 `animate-pulse` 효과로 강력하게 안내합니다.

---

## 2. 상태 관리 최적화 (React Hooks State Management) ⚡

Zustand나 Redux 같은 무거운 외부 전역 상태 라이브러리 없이, React Native Hook만으로 초단위의 면접 타이머와 실시간 오디오/채팅 데이터를 무결점으로 관리합니다.

- **불필요한 리렌더링 통제 (`useRef` vs `useState`)**:
  - 초 단위로 변하는 인터뷰 `totalTimeSec`을 `useState`로 두면 전체 컴포넌트가 매초 렌더링되므로, 이는 내부 텍스트 노드에만 마운트시켰습니다.
  - 반면 **오디오 객체(`${API_BASE_URL}${messages[0].audio_url}`)**와 **WebRTC Stream(`userVideoRef.current.srcObject`)**은 React 생명주기에서 분리하기 위해 `useRef`(`audioRef`, `userVideoRef`)에 담아 리렌더링 중에도 미디어가 끊기지 않고 연속 재생되도록 설계했습니다.
- **비전 프레임루프 (Vision Interval Hook)**:
  - 타임라인 기반 표정 분석 시, `setInterval` 내부 클로저 문제를 해결하기 위해 참조형 `emotionLogs` 배열 대신 `setEmotionLogs(prev => [...prev])` 함수형 업데이트를 통해 최신 State를 안전하게 캡처하여 메모리 누수를 막았습니다.

---

## 3. 비동기 로딩 및 피드백 시각화 (Loading & Delay UX) ⏳

AI 답변을 기다리는 3~5초의 로딩(Latency) 시간 동안, 사용자가 '시스템이 멈췄다'고 오인하지 않게 생동감 있는 피드백을 부여합니다.

- **스마트 스피너 및 진행 단계 텍스트 (`InterviewSetup.jsx`)**:
  - 이력서를 분석하거나 최초 질문을 생성할 때, `loadingMsg` 상태를 단계별로 변경(`이력서 분석 중...` → `면접 시작 중...`)하며, 글자 자체에 `animate-pulse` 효과를 줘서 진행 상황을 시각화합니다.
  - 배경은 `bg-slate-900/80 backdrop-blur-sm`를 통해 뒷배경을 블러 처리하고 클릭을 방지하여 트랜잭션의 안전성을 확보합니다.
- **채팅방 타이핑 인디케이터 (`ChatRoom.jsx` - `TypingIndicator()`)**:
  - LLM과 TTS 생성 간 `isLoading=true` 일 때 팝업되는 전용 로딩 버블입니다.
  - `{animationDelay: '0.2s'}` 등 `delay` 속성을 0s, 0.2s, 0.4s로 계단식 분배한 3개의 점(Dots) `animate-bounce` UI를 삽입했습니다. 이로 인해 마치 **AI 면접관이 직접 펜으로 글을 쓰고 있는 듯한 의인화된 경험**을 선사합니다.

---

## 4. 반응형 레이아웃 및 디자인 (Tailwind CSS) 🎨

복잡한 미디어 레이아웃(좌측 카메라/제어, 우측 채팅로그)을 브라우저나 디바이스 크기에 구애받지 않고 유려하게 반응토록 디자인했습니다.

- **Split View System (2분할 패널)**:
  - 메인 레이아웃은 `<div className="flex h-screen ... md:flex-row flex-col">` 로 구성되어 있습니다.
  - **PC(Desktop)** 환경(`md:` 768px 이상)에서는 좌우 `2:3` 비율(`md:w-2/5`, `md:w-3/5`)로 웹캠과 채팅창을 양옆으로 나란히 분할(`flex-row`)합니다.
  - **Mobile/Tablet** 환경에서는 상하로 쌓이는 구조(`flex-col`)로 우아하게 스와프되어 화면 크기 부족 현상을 방지합니다.
- **Glassmorphism & Color Scheme**:
  - 전체적으로 무거운 심해 톤(`bg-slate-900`)에 기반하지만, 특정 UI는 `bg-gradient-to-b from-slate-800 to-slate-900`의 그라디언트를 사용해 입체감을 주었습니다.
  - AI의 텍스트 버블은 흰색(`bg-white`), 사용자의 텍스트 버블은 파란색(`bg-blue-600`), 즉시 평가(Evaluation) 패널은 초록색 계열(`bg-green-50`)의 명도가 높은 색을 써서 정보의 가독성 대비를 극대화했습니다.
- **시각적 마이크 피드백**: 타이핑 영역 외에도 음성 인식이 동작 중일 땐 마이크 버튼 테두리에 펄스(Pulse)가 유지되며, '실시간 비전 분석 작동 중' 문구 옆에는 `<span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />` 레코딩 불빛을 구현하여 방송 스튜디오와 같은 인터페이스를 완성했습니다.
