# AI 모의 면접 시스템 V2: 면접 요소 정의 및 평가 지표 (Scoring Logic)

본 문서는 백엔드 시스템(`ai_service.py`)에 구현된 최종 면접 평가 리포트(`generate_final_report`)의 정밀한 점수 산출 로직을 코드 레벨 수식과 함께 분석한 기술 명세입니다.

이 시스템은 평가의 일관성과 신뢰성을 확보하기 위해 LLM의 자의적 점수 생성을 원천 차단하고, **Python의 하드코딩된 수리적 연산(Heuristic Rule)**을 통해서만 정량적인 스코어를 도출합니다.

---

## 1. 언어적 평가 점수 산출 로직 (Verbal Scores) 💬

매 턴(Turn)마다 AI 면접관이 지원자의 답변을 채점한 `turn_score`들의 단순 평균(`avg_turn_score`)을 베이스라인으로 삼고, 각 역량의 난이도에 따라 패널티 비율을 적용하여 100점 만점으로 환산합니다.

- **1단계: Base Average 산출**
  - 수학적 연산: `avg_turn_score = sum(scored_turns) / len(scored_turns)`
  
- **2단계: 역량별 최종 환산 수식 (`ai_service.py` L707-810 대)**
  1. **직무 역량 (Tech Score)**: `max(0, min(100, int(avg_turn_score * 0.95)))`
     - 엄격한 기술적 허들을 반영하여 평균 점수 대비 **5%의 패널티**가 부과됩니다.
  2. **문제해결력 (Problem Solving Score)**: `max(0, min(100, int(avg_turn_score * 0.90)))`
     - 논리적 STAR 구조가 완벽하지 않은 경우를 대비해 가장 엄격한 잣대인 **10% 패널티**가 부과됩니다.
  3. **의사소통 (Communication Score)**: `max(0, min(100, int(avg_turn_score * 1.0)))`
     - 지원자의 표현력 자체는 턴 평균이 곧 대화의 응집력을 뜻하므로, **패널티 없이 1:1 (100%)**로 온전히 반영합니다.

---

## 2. 비언어적 평가 점수 산출 로직 (Non-verbal Attitude) 😐

Vision AI 모듈이 초 단위로 누적시킨 지원자의 표정 데이터(프론트엔드의 `vision_data` JSON 카운트)를 백엔드에서 100점 만점 수식으로 직접 파싱합니다.

- **분석 대상 로그**: `{'neutral': 120, 'happy': 34, 'fear': 2, 'sad': 1, ...}`
- **산출 공식 (`ai_service.py` L801-803)**:
  - `total_v` = 수집된 전체 프레임 카운트 수
  - `positive_v` = 긍정 및 안정적 표정 횟수 총합 (`neutral` + `happy`)
  - **`nv_score = int(50 + ((positive_v / total_v) * 50))`**
- **로직 해석**:
  - 지원자가 웹캠을 켜기만 해도 **기본점수 50점**이 무조건 보장됩니다.
  - 나머지 50점은 전체 표정 중 **안정적/긍정적 표정(Neutral, Happy)이 차지하는 비율(%)**만큼 가산점으로 부여받습니다. 
  - 극단적인 부정적 표정(Angry, Fear)이 많이 노출될수록 가산점 비율이 0에 수렴하여 최저 50점이 될 수 있습니다.
  - *단, 웹캠을 아예 사용하지 않거나 카메라 권한이 없는 경우(No vision_data) 형평성을 위해 디폴트 **70점**이 고정 부여됩니다.*

---

## 3. 최종 총점 산출 방식 (Total Score Calculation) 🏆

마지막으로 도출된 4가지 개별 영역의 점수는 합산되어 사용자의 최종 당락 지표인 **종합 점수(`total_score`)**로 저장됩니다. 시스템의 인재상 기준에 부합하도록 코드 상에 고정된 퍼센티지(Weights)가 적용됩니다.

- **Weight (반영 비율)**:
  - **직무역량 (Tech Score)**: `40%` (가장 높은 중요도)
  - **문제해결력 (Problem Solving)**: `25%`
  - **의사소통 (Communication)**: `25%`
  - **비언어적 태도 (Non-verbal)**: `10%` (Vision AI 기반의 태양성 보조 지표)

- **최종 적용 수식 (`ai_service.py` L813-818)**:
  ```python
  total = int(round(
      tech_score            * 0.40 +
      comm_score            * 0.25 +
      problem_solving_score * 0.25 +
      nv_score              * 0.10
  ))
  ```

### 💡 결론 요약
LLM은 텍스트(강점, 약점, 요약) 생성 용도로만 쓰이며, 모든 정량적 평가는 턴별 베이스 평균과 Vision 데이터를 Python 정수 연산으로 계산하여 **LLM 환각에 의한 '점수 조작'을 원천적으로 차단한 신뢰도 높은 평가 구조**를 취하고 있습니다.
