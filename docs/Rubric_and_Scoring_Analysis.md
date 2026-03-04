# AI 모의 면접 시스템 V2: 평가 루브릭 및 점수 도출 알고리즘 분석

본 문서는 백엔드 인프라(`ai_service.py`)의 `evaluate_answer` 함수와 `generate_final_report` 로직을 정밀하게 스캔하여, 대형 언어 모델(LLM)에게 하달되는 **절대적 평가 기준(Rubric)**과 이로부터 추출된 **수리적 점수 도출 로직**을 기술적으로 분석한 문서입니다.

---

## 1. 평가 루브릭 템플릿 및 LLM 프롬프트 지시 내용 📝

LLM(exaone 3.5)에게 지원자의 매 턴(Turn) 답변을 평가하게 할 때, 포괄적이고 주관적인 평가를 방지하기 위해 매우 엄격한 0-100점 척도와 페널티 룰이 하드코딩된 **System Prompt**가 주입됩니다.

### 📌 프롬프트 원문 발췌 (System Format)
```text
You are a strict Korean technical interviewer. Score the candidate's answer and return ONLY valid JSON.

Scoring guide (0-100):
- 80-100: Correct answer WITH specific concrete examples, measurable metrics, explicit trade-offs, AND a clear STAR structure (Situation → Task → Action → Result).
- 60-79:  Correct concepts but lacks depth, concrete examples, or measurable results.
- 40-59:  Partially correct or vague reasoning without specifics.
- 0-39:   Wrong answer, irrelevant content, or just complaining about the question.
```

### 🚫 환각 및 과대 점수 방지 규칙 (CRITICAL SCORING RULES)
특히, 기술 면접의 변별력을 높이기 위해 다음 6가지의 `[MUST ENFORCE]` 제약 조건을 프롬프트에 명시했습니다.
1. **정량적 수치 부재 패널티**: 구체적 예시나 측정 가능한 수치("지연 시간을 30% 줄였다", "1만 RPS를 버텼다" 등)가 **단 하나도 없다면, 최대 점수는 50점으로 강제 제한**됩니다.
2. **STAR 기법 미준수 패널티**: 상황(S), 과제(T), 행동(A), 결과(R) 구조가 명확하지 않다면 **최대 점수는 55점으로 제한**됩니다.
3. **피드백 강제화**: 점수를 감점했다면 어떤 구체적 예시나 지표가 누락되었는지 피드백 스트링에 무조건 명시해야 합니다.
4. **모호성 엄단**: 그럴싸한 일반론(Generic answers)에는 60점 이상을 부여하지 못하도록 통제합니다.
5. **포기/무응답**: "모르겠습니다" 등 포기성 발언은 10~20점을 강제합니다.
6. **AI 환각 지적 대응**: 만약 지원자가 "그 질문은 제 이력서에 없는 내용입니다"라고 AI의 오류를 지적할 경우, 0-39점을 부여하되 피드백에서 이를 인정하고 넘어가도록 설계했습니다.

---

## 2. 세부 역량별 점수 (직무, 의사소통, 문제해결) 도출 로직 🧮

언어 모델은 매 턴의 답변마다 0~100점 사이의 단일 `score`만을 반환합니다. 
지원자의 최종 리포트 화면상에 보여지는 **'직무 역량', '문제해결력', '의사소통'** 항목 점수는 LLM이 각자 마음대로 평가한 것이 아니라, 백엔드 서버(Python)가 전체 턴의 평균 점수(`avg_turn_score`)를 바탕으로 수학적 알고리즘을 거쳐 도출(Override)합니다.

### ⚙️ Python 기반 백엔드 변환 알고리즘 (`ai_service.py` 700번대 라인)

#### 1) 턴 단위 기본 평균 산출 (Base Average)
```python
scored_turns = [t.score for t in transcripts if t.sender == "human" and t.score is not None]
avg_turn_score = round(sum(scored_turns) / len(scored_turns))
```
- 모든 턴에서 평가된 LLM의 Score들(위 루브릭 규정을 통과한 점수들)을 단순 평균 내어 기준점(`avg_turn_score`)을 설정합니다.

#### 2) 항목별 가중치 연산
LLM의 모호성을 제거하고자, 각 역량 성격에 맞춰 상한선 100점(`min(100, ...)`) 내에서 패널티 팩터를 곱셈(Weighting) 처리합니다.

- **직무 역량 (Tech Score)**: `tech_score = max(0, min(100, int(avg_turn_score * 0.95)))`
  - 기술적 난이도 허들을 고려하여 총평균에서 **5% 감점 패널티(0.95)**를 적용합니다.
- **문제해결력 (Problem Solving)**: `problem_solving_score = max(0, min(100, int(avg_turn_score * 0.90)))`
  - 문제해결의 근거인 'STAR 구조'의 완벽한 달성 및 성과 지표 유무가 매우 까다롭다고 판단하여, 가장 높은 비율인 **10% 감점 패널티(0.90)**를 적용합니다.
- **의사소통 (Communication)**: `comm_score = max(0, min(100, int(avg_turn_score * 1.0)))`
  - 발화의 맥락이 끊기지 않는 것 자체가 의사소통 능력을 대변하므로 단일 텍스트 평균값을 **패널티 없이(1.0) 100% 온전히 반영**합니다.

### 💡 아키텍처 의의 (Architectural Value)
이러한 설계 방식은 LLM에게 세부 지표(직무 점수는 몇 점, 문제해결력은 몇 점)를 각각 평가해서 JSON으로 넘기라고 했을 때 흔히 겪는 **수치의 불확실성/인과관계 왜곡 현상을 원천 차단**합니다. 오직 '정확한 팩트와 논리가 있는가?'라는 한 가지 척도로만 대답의 견고함(`avg_turn_score`)을 뽑아낸 뒤, 백엔드 로직이 이를 세부 역량 지표로 분산시키는 매우 **안정성 높은(Deterministic) 채점 파이프라인**을 완성했습니다.
