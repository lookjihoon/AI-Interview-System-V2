# AI 모의면접 시스템 정량 평가 루브릭 (Evaluation Rubric Specification)

## 1. 개요 (Overview)
본 문서는 AI 모의면접 시스템의 평가 로직을 정의한다. 평가는 **STAR 기법(Situation, Task, Action, Result)**을 기반으로 하며, **5점 척도**의 정량적 기준을 적용한다.
AI 에이전트(LLM 및 Vision Analyzer)는 아래 기준에 따라 지원자의 답변(Verbal)과 비언어적 태도(Non-verbal)를 분석하여 점수를 산출해야 한다.

---

## 2. 평가 영역 및 상세 기준 (Evaluation Criteria)

평가 영역은 크게 **Verbal(언어적/내용)** 평가와 **Non-verbal(비언어적/시각)** 평가로 나뉜다.

### 2.1. Verbal Evaluation (내용 및 논리) - LLM 처리 영역

| 대분류 | 중분류 | 1점 (미흡 - Poor) | 3점 (보통 - Average) | 5점 (탁월 - Excellent) | 💡 AI 판단 로직 (Implementation Logic) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **직무 역량**<br>(Hard Skill) | **개념 정확성** | 핵심 개념을 오해하거나 틀린 정보를 자신 있게 답변함. | 개념은 정확히 정의하나, 실무 적용 사례를 제시하지 못함. | 개념을 정확히 이해하고, 장단점(Trade-off)과 실제 적용 사례를 논리적으로 설명함. | **Keyword Matching:** 답변 내에 질문 의도에 부합하는 기술 키워드(예: "Deadlock", "Index")가 포함되었는지 검사. |
| **직무 역량**<br>(Hard Skill) | **내용 적합성**<br>*(New)* | 질문의 의도와 동떨어진 답변을 하거나 회피함. | 질문의 의도는 파악했으나, 깊이가 얕음. | 질문의 의도를 정확히 파악하고, **모범 답안의 핵심 가치**를 포함함. | **Cosine Similarity:**<br>`Vector(지원자답변)` vs `Vector(모범답안)` 유사도가 **0.8 이상**일 경우 고득점 부여. |
| **문제 해결력**<br>(Logic) | **논리적 사고** | 힌트를 주어도 문제 해결의 실마리를 찾지 못함. | 힌트를 통해 문제를 해결하나, 최적화된 방법은 아님. | 문제를 스스로 정의하고, 다양한 해결책을 비교 분석하여 **최적해(Optimal Solution)**를 도출함. | **Structure Check:** "문제 정의 -> 대안 제시 -> 해결"의 논리적 흐름이 존재하는지 LLM이 판단. |
| **의사소통**<br>(Soft Skill) | **구조화**<br>(STAR) | 답변이 장황하고 핵심이 불분명하며, 두괄식이 아님. | 대답은 하나, 구조화가 부족하여 인과관계가 약함. | **두괄식**으로 명확히 답변하며, **STAR 기법(상황-과제-행동-결과)**에 맞춰 구조적으로 설명함. | **Regex/LLM:** 답변 내에 "결론적으로", "예를 들어", "결과적으로" 등의 접속사 및 문단 구분이 명확한지 분석. |

---

### 2.2. Non-verbal Evaluation (비언어적 태도) - Vision/Audio 처리 영역

**※ 개발 1단계 목표: Vision AI (DeepFace/MediaPipe) 활용**

| 평가 항목 | 1점 (미흡 - Poor) | 3점 (보통 - Average) | 5점 (탁월 - Excellent) | 💡 Vision/Audio 알고리즘 로직 |
| :--- | :--- | :--- | :--- | :--- |
| **시선 처리**<br>(Eye Contact) | 카메라를 거의 보지 않고 시선이 불안정하게 흔들림 (회피). | 가끔 시선이 분산되나(천장, 바닥), 대체로 화면을 응시함. | **지속적인 Eye Contact**를 유지하며, 자신감 있는 태도를 보임. | **Gaze Tracking:**<br>눈동자가 카메라 영역(Center Box) 내에 머무른 시간 비율(%) 측정.<br>- 80% 이상: 5점<br>- 50~79%: 3점<br>- 50% 미만: 1점 |
| **표정 안정성**<br>(Facial Expression) | 무표정이거나 긴장/당황한 표정이 역력함 (Fear/Sad). | 평이한 표정을 유지하나, 감정 변화가 거의 없음. | **긍정적인 표정(Happy)**과 상황에 맞는 제스처를 보임. | **Emotion Recognition (DeepFace):**<br>- `Fear` + `Sad` 비율이 30% 초과 시 감점.<br>- `Happy` + `Neutral` 비율이 높으면 가산점. |
| **음성 전달력**<br>(Voice) | 목소리가 너무 작거나 떨림, 혹은 발음이 부정확함. | 적절한 크기이나 톤의 변화가 없어 단조로움. | 명료하고 안정된 발성으로 신뢰감을 줌. | **Audio Analysis:**<br>- 데시벨(dB) 평균이 기준치(예: 40dB) 미만이면 감점.<br>- 음성 떨림(Jitter) 분석 (추후 구현). |

---

## 3. 시스템 프롬프트 가이드 (System Prompt Guide)

LLM이 평가 리포트를 생성할 때, 반드시 아래의 **JSON 포맷**을 준수해야 한다.

```json
{
  "total_score": 85,
  "summary": "직무에 대한 이해도가 높고 논리적인 답변을 하였으나, 시선 처리가 다소 불안정함.",
  "details": {
    "hard_skill": {
      "score": 90,
      "feedback": "RESTful API의 개념과 장단점을 정확하게 설명하였습니다."
    },
    "logic": {
      "score": 80,
      "feedback": "트래픽 처리에 대한 해결책을 제시했으나, 구체적인 수치가 부족합니다."
    },
    "communication": {
      "score": 85,
      "feedback": "STAR 기법에 맞춰 답변하였으나, 서론이 다소 길었습니다."
    },
    "vision_analysis": {
      "score": 70,
      "feedback": "답변 도중 시선이 자주 오른쪽 위를 향했습니다. (불안감 감지)"
    }
  }
}