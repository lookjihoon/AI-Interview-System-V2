"""
AI Interview Service
Implements the core AI interviewer logic using LangChain and RAG.
Phase logic follows docs/Scenario.md (6-turn, ~20 minutes).
"""
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select
import json
import re

from langchain_ollama import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage

from models import User, JobPosting, QuestionBank, InterviewSession, Transcript
from database import SessionLocal


# ─── Phase Turn Boundaries ───────────────────────────────────────────────────
PHASE2_TURNS = range(1, 4)   # turns 1-3  → Technical Hard Skills
PHASE3_TURNS = range(4, 6)   # turns 4-5  → Behavioral / Soft Skills
CLOSING_TURN = 6              # turn 6     → closing question (session stays IN_PROGRESS)
# turn 7 is handled by the router (user answers closing q → goodbye + COMPLETED)

BEHAVIORAL_CATEGORIES = {"BEHAVIORAL", "SOFT_SKILL", "SOFT SKILL", "PERSONALITY"}


class InterviewAI:
    """
    AI Interviewer Brain
    Handles question selection via phase-aware RAG and answer evaluation.
    """

    # Hardcoded fail-safe feedback strings (prevents gibberish from LLM)
    _FAILSAFE_PATTERNS = [
        "모르겠", "모르겠습니다", "모르겠어요", "잘 모르",
        "i don't know", "idk", "pass", "패스", "skip",
    ]
    _FAILSAFE_RESULT = {
        "score": 15,
        "feedback": (
            "해당 질문에 대한 경험이나 지식이 부족하여 답변을 완료하지 못했습니다. "
            "관련 개념에 대한 학습과 보완이 필요합니다."
        ),
        "follow_up_question": (
            "이 주제에 대해 평소에 어떻게 학습하고 계신지 말씀해 주시겠어요?"
        ),
    }

    def __init__(self):
        """Initialize LLM and embedding models"""
        self.llm = ChatOllama(
            model="llama3.1",
            temperature=0.1,
            num_predict=768,
            format="json"
        )
        # Text-only LLM for question rewriting (no JSON constraint)
        self.llm_text = ChatOllama(
            model="llama3.1",
            temperature=0.2,
            num_predict=200,
        )
        # Dedicated evaluation LLM — temperature=0.2 for stable, grounded scoring
        # (0.0 can cause repetition loops in Llama 3.1; 0.2 is the sweet spot)
        self.llm_eval = ChatOllama(
            model="llama3.1",
            temperature=0.2,
            num_predict=512,
            format="json"
        )
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"
        )
        print("✓ InterviewAI initialized (llama3.1 + all-mpnet-base-v2)")

    # ─────────────────────────────────────────────────────────────────────────
    # Phase Detection
    # ─────────────────────────────────────────────────────────────────────────
    def _get_turn_count(self, session_id: int, db: Session) -> int:
        """
        Count the number of non-greeting AI turns (question_id != NULL means
        it is a real RAG/phase question; self-intro transcript has question_id=NULL).
        We count ALL ai messages except the opening greeting and self-intro.
        """
        # Count transcripts where sender=ai and content contains
        # "자기소개" (intro) or not (real question).
        # Simpler: count all human turns — each human answer corresponds to one AI question.
        human_turns = db.query(Transcript).filter(
            Transcript.session_id == session_id,
            Transcript.sender == "human"
        ).count()
        return human_turns  # 0 = never answered anything (first AI question)

    def _get_last_human_answer(self, session_id: int, db: Session) -> str:
        """Return the most recent human transcript content, or empty string."""
        last = db.query(Transcript).filter(
            Transcript.session_id == session_id,
            Transcript.sender == "human"
        ).order_by(Transcript.id.desc()).first()
        return last.content if last else ""

    def _intro_already_asked(self, session_id: int, db: Session) -> bool:
        """Check whether the self-intro question has already been asked."""
        return db.query(Transcript).filter(
            Transcript.session_id == session_id,
            Transcript.sender == "ai",
            Transcript.content.contains("자기소개")
        ).first() is not None

    # ─────────────────────────────────────────────────────────────────────────
    # Smart RAG Query Builder
    # ─────────────────────────────────────────────────────────────────────────
    def _build_rag_query(
        self,
        job: JobPosting,
        last_answer: str,
        session_resume_text: Optional[str],
        user: Optional[User],
        force_behavioral: bool = False
    ) -> str:
        """
        Build a focused, keyword-rich query for similarity search.

        Instead of dumping the raw resume (noisy), we compose a short query:
          "job.title  <3 skill keywords from last answer>  <optional JD keywords>"
        """
        parts = [job.title or ""]

        # Extract up to 5 meaningful keywords from last answer (skip stopwords)
        if last_answer:
            tokens = re.findall(r"[A-Za-z가-힣]{2,}", last_answer)
            stopwords = {"있다", "입니다", "이다", "했습니다", "하고", "그리고", "있습니다",
                         "저는", "제가", "했고", "하여", "에서", "으로", "을"}
            keywords = [t for t in tokens if t not in stopwords][:5]
            if keywords:
                parts.append(" ".join(keywords))

        if force_behavioral:
            parts.append("teamwork collaboration conflict resolution behavioral")
        else:
            # Light JD signal (not full 500-char blob)
            if job.requirements:
                jd_tokens = re.findall(r"[A-Za-z가-힣]{3,}", job.requirements)
                parts.append(" ".join(jd_tokens[:8]))

        # Resume: use only top-3 skill lines, not full text
        resume = session_resume_text or (user.resume_text if user else None)
        if resume and not force_behavioral:
            skill_lines = [l.strip() for l in resume.splitlines() if l.strip()][:5]
            parts.append(" ".join(skill_lines))

        query = " ".join(parts)
        print(f"[RAG] Smart query ({len(query)} chars): {query[:120]}")
        return query

    # ─────────────────────────────────────────────────────────────────────────
    # Question Personaliser (lightweight LLM rewrite)
    # ─────────────────────────────────────────────────────────────────────────
    def _personalise_question(
        self,
        base_question: str,
        last_answer: str,
        session_resume_text: Optional[str] = None
    ) -> str:
        """
        Rewrite the fetched question so it naturally references the candidate's
        last answer or resume. Falls back to base_question on error.
        """
        if not last_answer:
            return base_question

        resume_hint = ""
        resume_preview = ""
        if session_resume_text:
            skill_lines = [l.strip() for l in session_resume_text.splitlines() if l.strip()]
            resume_hint = " ".join(skill_lines[:3])
            resume_preview = session_resume_text[:600]  # Full preview for anti-gaslighting check

        prompt = f"""[SYSTEM] You are a PROFESSIONAL KOREAN INTERVIEWER. Your role is ONLY to ask questions.

[ABSOLUTE RULES - NEVER VIOLATE]
1. You are the INTERVIEWER. You MUST ONLY generate the question text.
2. DO NOT answer the question yourself.
3. DO NOT write example answers or hints for the candidate.
4. DO NOT continue generating text after the question mark (?).
5. Output EXACTLY ONE sentence ending with '?' or '습니다.' — then STOP.

[TASK] Rewrite the base question below in natural Korean business polite form (존댓말).

[PRONOUN CONVERSION RULE - CRITICAL]
- The candidate's previous answer uses 1st-person pronouns (저는, 제가, 나의).
- NEVER copy these 1st-person pronouns into the rewritten question.
- ALWAYS convert to 3rd/2nd person context, for example:
  * '저는 A를 했습니다' -> '지원자님께서 A를 하셨다고 하셨는데' or '이전 답변에서 A를 언급하셨는데'
- Ensure the final sentence is grammatically natural.

[ANTI-GASLIGHTING RULE - CRITICAL]
- You have access to the candidate's [이력서 원문] below.
- If the [기본 질문] is about a technology, domain, or experience (e.g., Banking, UX, Web Worker, Kubernetes)
  that does NOT appear in the [이력서 원문], you MUST NOT say '이력서에 ~경험이 있다고 하셨는데'.
- Instead, frame it as a general hypothetical: '만약 ~상황이 주어진다면 어떻게 접근하시겠습니까?'
  or '~에 대해 어떻게 생각하시는지 설명해 주시겠어요?'
- NEVER fabricate or invent candidate experiences that are not in the resume.

[필수 형식 규칙]
- 반드시 정중하고 자연스러운 한국어 비즈니스 경어체(존댓말)로 완성형 문장을 작성하세요.
- 문장의 끝은 반드시 '~하셨나요?', '~설명해 주시겠어요?', '~말씀해 주시겠어요?', '~있으신가요?' 등으로 정중하게 끝맺으세요.
- 명사형('~방법은?', '~노하우는?')이나 반말로 끝나면 절대 안 됩니다.
- 질문 문장 1개만 출력하세요. 설명·예시·인사말 불가.

[기본 질문] {base_question}
[지원자 이전 답변] {last_answer[:200]}
[이력서 원문] {resume_preview if resume_preview else '(이력서 없음)'}

질문:"""

        try:
            response = self.llm_text.invoke([HumanMessage(content=prompt)])
            rewritten = response.content.strip()
            # Sanity check: must be Korean and not too short/long
            if len(rewritten) > 15 and "?" in rewritten:
                print(f"[RAG] Personalised question: {rewritten[:80]}")
                return rewritten
        except Exception as e:
            print(f"[RAG] Personalise error: {e}")

        return base_question

    # ─────────────────────────────────────────────────────────────────────────
    # Closing Response Generator
    # ─────────────────────────────────────────────────────────────────────────
    def generate_closing_response(self, user_message: str) -> str:
        """
        Generate a polite 1-2 sentence reply to the candidate's final remark or
        question, then append the mandatory closing farewell phrase.
        """
        CLOSING_SUFFIX = (
            " 긴 시간 동안 수고하셨습니다. 면접이 모두 종료되었습니다. "
            "창을 닫거나 결과를 확인해 주세요."
        )
        prompt = f"""[SYSTEM] You are a professional Korean interviewer closing the interview.
The candidate has just provided their final remark or question.
Respond politely and briefly in 1-2 sentences in Korean business polite form (존댓말).
DO NOT ask any further questions. DO NOT continue the interview topic.
Output ONLY your brief response — plain text, no JSON, no markdown.

[CANDIDATE'S FINAL MESSAGE]
{user_message[:400]}

응답:"""
        try:
            response = self.llm_text.invoke([HumanMessage(content=prompt)])
            reply = response.content.strip()
            # Strip any trailing question mark that invites further conversation
            if reply.endswith("?"):
                reply = reply[:-1] + "."
            return (reply + CLOSING_SUFFIX) if reply else CLOSING_SUFFIX.strip()
        except Exception as e:
            print(f"[CLOSING] LLM error: {e}")
            return (
                "좋은 말씀 감사합니다. "
                "긴 시간 동안 수고하셨습니다. 면접이 모두 종료되었습니다. "
                "창을 닫거나 결과를 확인해 주세요."
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Main: get_optimal_question
    # ─────────────────────────────────────────────────────────────────────────
    def get_optimal_question(
        self,
        user_id: int,
        job_id: int,
        history_ids: List[int],
        db: Session,
        session_id: int = None,
        session_resume_text: str = None
    ) -> Optional[QuestionBank]:
        """
        Phase-aware question selection:
          Phase 1 (turn 0): self-introduction
          Phase 2 (turn 1-3): technical RAG questions (personalised)
          Phase 3 (turn 4-5): behavioral/soft-skill RAG questions
          Phase 4 (turn 6+): closing → returns dummy with id=None
        """
        # ── Turn counting ────────────────────────────────────────────────────
        turn = self._get_turn_count(session_id, db) if session_id else len(history_ids)
        print(f"[Phase] Session {session_id} | turn={turn} | history={len(history_ids)}")

        # ── Phase 4: Closing ─────────────────────────────────────────────────
        if turn >= CLOSING_TURN:
            print("[Phase] → Phase 4 CLOSING")
            dummy = QuestionBank()
            dummy.id = None
            dummy.question_text = (
                "오늘 긴 시간 동안 수고 많으셨습니다. "
                "마지막으로 하고 싶으신 말씀이나 궁금한 점이 있으시면 말씀해 주세요."
            )
            dummy.category = "CLOSING"
            dummy.sub_category = "마무리"
            return dummy

        # ── Phase 1: Self-Introduction ───────────────────────────────────────
        if session_id and not self._intro_already_asked(session_id, db):
            print("[Phase] → Phase 1 SELF-INTRO")
            dummy = QuestionBank()
            dummy.id = None
            dummy.question_text = "먼저, 간단하게 1분 자기소개를 부탁드립니다."
            dummy.category = "BEHAVIORAL"
            dummy.sub_category = "자기소개"
            return dummy

        # ── Phase 2 / 3: RAG ────────────────────────────────────────────────
        user = db.query(User).filter(User.id == user_id).first()
        job  = db.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not job:
            raise ValueError(f"Job posting {job_id} not found")

        last_answer    = self._get_last_human_answer(session_id, db) if session_id else ""
        force_behavioral = turn in PHASE3_TURNS

        if force_behavioral:
            print("[Phase] → Phase 3 BEHAVIORAL")
        else:
            print(f"[Phase] → Phase 2 TECHNICAL (turn {turn})")

        # Smart focused query
        query_text = self._build_rag_query(
            job=job,
            last_answer=last_answer,
            session_resume_text=session_resume_text,
            user=user,
            force_behavioral=force_behavioral
        )

        query_embedding = self.embeddings.embed_query(query_text)

        # Build SQL: exclude asked IDs
        real_history = [qid for qid in history_ids if qid and qid > 0]
        stmt = select(QuestionBank).order_by(
            QuestionBank.embedding.cosine_distance(query_embedding)
        )
        if real_history:
            stmt = stmt.where(QuestionBank.id.notin_(real_history))

        # Phase 3: force behavioral category filter
        if force_behavioral:
            stmt = stmt.where(
                QuestionBank.category.in_(list(BEHAVIORAL_CATEGORIES))
            )

        result = db.execute(stmt.limit(1)).scalar_one_or_none()

        if result:
            print(f"[RAG] Fetched: [{result.category}] {result.question_text[:80]}")
            # Personalise using last answer / resume
            result.question_text = self._personalise_question(
                base_question=result.question_text,
                last_answer=last_answer,
                session_resume_text=session_resume_text
            )
        else:
            print("[RAG] No suitable question found")

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Answer Evaluation
    # ─────────────────────────────────────────────────────────────────────────
    def evaluate_answer(
        self,
        question_text: str,
        user_answer: str,
        job_context: str
    ) -> Dict[str, Any]:
        """Evaluate user's answer against Rubric_Detail.md criteria."""

        # ── Fail-safe: bypass LLM entirely for clearly invalid answers ─────────
        answer_lower = user_answer.strip().lower()
        if (
            len(user_answer.strip()) < 8
            or any(p in answer_lower for p in self._FAILSAFE_PATTERNS)
        ):
            print(f"[EVAL] Fail-safe triggered for short/unknown answer")
            return dict(self._FAILSAFE_RESULT)

        prompt_template = PromptTemplate(
            input_variables=["job_context", "question", "answer"],
            template="""You are a strict Korean technical interviewer grading a job candidate's answer.
Follow every rule below without exception.

## SCORING ANCHORS (read carefully before assigning scores)
- 80-100: Excellent. Candidate gives specific technical examples, discusses trade-offs, uses STAR structure.
- 60-79:  Average. Mentions correct concepts but lacks depth or concrete real-world examples.
- 40-59:  Below average. Partially correct, vague, or no structured reasoning.
- 0-39:   Poor. Answer is irrelevant, technically wrong, or candidate is simply pointing out the AI's mistake.

## HALLUCINATION CORRECTION RULE
If the candidate's answer is pointing out that your previous question was based on a false assumption
(e.g. 'I never mentioned X', 'I did not say that', 'That is not in my resume'),
then: acknowledge the mistake briefly in the feedback, and evaluate only the technical merit
of whatever else the candidate said. Do NOT artificially inflate the score to compensate.
Such responses score 0-39 unless they also provide substantial technical content.

## FAIL-SAFE (HIGHEST PRIORITY)
If the answer is: a single word, pure gibberish, a meta-question about the AI, or a surrender
(e.g. 'I don't know'), assign score 10-20 regardless of other rules.

## RUBRIC — score each dimension 0-100 then compute: score = hard*0.4 + logic*0.3 + comm*0.3

1. Hard Skill x40%:
   100 = accurate concept + trade-offs + real example with specifics
    60 = correct concept, no practical example
    20 = wrong concept or irrelevant answer
     0 = no technical content

2. Logic x30%:
   100 = defines the problem, compares 2+ solutions, reaches optimal choice
    60 = presents one solution with reasoning
    20 = vague or illogical
     0 = no structure

3. Communication (STAR) x30%:
   100 = Situation -> Task -> Action -> Result, clear and concise
    60 = has conclusion but not structured
    20 = long-winded or unclear
     0 = incoherent

## PENALTIES
- Minus 20 if no specific numbers, project names, or examples when technically expected.
- Minus 15 if answer is shorter than 2 full sentences.

## OUTPUT LANGUAGE RULE
You MUST write the 'feedback' and 'follow_up_question' values in natural, professional KOREAN.
Do NOT use English in those text values.

## JOB CONTEXT
{job_context}

## INTERVIEW QUESTION
{question}

## CANDIDATE ANSWER
{answer}

## OUTPUT — JSON ONLY, NO OTHER TEXT
{{"score": <integer 0-100>, "feedback": "<2-3 sentences in Korean. State what was good and what must improve>", "follow_up_question": "<1 Korean follow-up question>"}}""")

        formatted_prompt = prompt_template.format(
            job_context=job_context[:500],
            question=question_text,
            answer=user_answer
        )

        print(f"\n[EVAL] Evaluating ({len(user_answer)} chars)")

        try:
            response = self.llm_eval.invoke([HumanMessage(content=formatted_prompt)])
            response_text = response.content.strip()

            # Strip markdown code fences if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            evaluation = json.loads(response_text)

            for field in ["score", "feedback", "follow_up_question"]:
                if field not in evaluation:
                    raise ValueError(f"Missing field: {field}")

            evaluation["score"] = max(0, min(100, int(evaluation["score"])))
            print(f"[EVAL] Score: {evaluation['score']}/100")
            return evaluation

        except json.JSONDecodeError as e:
            print(f"[EVAL] JSON parse error: {e}")
            return {
                "score": 15, # Fail-safe score for JSON errors
                "feedback": "답변 형식이 올바르지 않거나 처리 중 오류가 발생했습니다. 다시 시도해 주세요.",
                "follow_up_question": "이 주제에 대해 좀 더 명확하고 구체적으로 설명해 주시겠어요?"
            }
        except Exception as e:
            print(f"[EVAL] Evaluation error: {e}")
            return {
                "score": 15, # Fail-safe score for other errors
                "feedback": "답변 감사합니다. 관련하여 실무에서 겪으신 사례가 있으신가요?",
                "follow_up_question": "관련하여 실무에서 겪으신 사례가 있으신가요?"
            }



# ─── Singleton ────────────────────────────────────────────────────────────────
_ai_service: Optional[InterviewAI] = None

def get_ai_service() -> InterviewAI:
    """Get or create AI service singleton"""
    global _ai_service
    if _ai_service is None:
        _ai_service = InterviewAI()
    return _ai_service


def generate_final_report(session_id: int, db: Session) -> None:
    """
    Generate a comprehensive evaluation report for a completed interview session.
    Fetches all human answers, prompts the LLM to score across 3 rubric dimensions,
    then persists an EvaluationReport row.
    """
    from models import EvaluationReport, InterviewSession, Transcript, JobPosting

    # Skip if report already exists
    existing = db.query(EvaluationReport).filter(
        EvaluationReport.session_id == session_id
    ).first()
    if existing:
        print(f"[REPORT] Report already exists for session {session_id}")
        return

    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        print(f"[REPORT] Session {session_id} not found")
        return

    job = db.query(JobPosting).filter(JobPosting.id == session.job_posting_id).first()
    job_title = job.title if job else "Unknown Position"

    # Collect all AI question → Human answer pairs
    transcripts = db.query(Transcript).filter(
        Transcript.session_id == session_id
    ).order_by(Transcript.id.asc()).all()

    qa_pairs = []
    last_q = None
    for t in transcripts:
        if t.sender == "ai" and not t.content.startswith("안녕하세요"):
            last_q = t.content
        elif t.sender == "human" and last_q:
            qa_pairs.append(f"Q: {last_q}\nA: {t.content}")
            last_q = None

    if not qa_pairs:
        print(f"[REPORT] No Q&A pairs found for session {session_id}")
        return

    interview_text = "\n\n".join(qa_pairs[:7])  # Max 7 pairs

    prompt = f"""You are a Chief Interviewer writing a final evaluation report in JSON format.
Evaluate the candidate based ONLY on the Q&A transcript provided below.
Output ONLY valid JSON — no markdown fences, no explanation, no extra text.

## JOB POSITION
{job_title}

## INTERVIEW TRANSCRIPT
{interview_text}

## SCORING ANCHORS — apply these strictly
- 80-100: Excellent. Candidate gives specific technical examples, STAR structure, discusses trade-offs.
- 60-79:  Average. Correct concepts but lacks depth or concrete examples.
- 40-59:  Below average. Partially correct, vague, or no structured reasoning.
- 0-39:   Poor. Irrelevant, wrong, evasive, or candidate only complained about question quality.

## DIMENSIONS TO SCORE (each 0-100, based on the full transcript)
- tech_score: Accuracy of technical knowledge, depth of expertise, precise terminology.
- communication_score: Clarity, STAR structure (Situation->Task->Action->Result), conciseness.
- problem_solving_score: Ability to define problems, compare approaches, reach optimal solutions.

## OUTPUT LANGUAGE RULE
You MUST write 'summary', 'strengths', 'weaknesses', and 'jd_fit' values in natural, professional KOREAN.
Do NOT use English in those text fields.

## REQUIRED JSON OUTPUT
{{
  "tech_score": <integer 0-100>,
  "communication_score": <integer 0-100>,
  "problem_solving_score": <integer 0-100>,
  "summary": "<1-2 sentence overall Korean summary>",
  "details": {{
    "strengths": "<Korean: 2-3 specific strengths with evidence from transcript>",
    "weaknesses": "<Korean: 2-3 specific improvement areas with evidence>",
    "jd_fit": "<Korean: How well does the candidate fit the {job_title} role? Rate and explain.>"
  }}
}}"""


    try:
        ai = get_ai_service()
        response = ai.llm_eval.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        # Strip markdown fences
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        data = json.loads(raw)

        tech   = max(0, min(100, int(data.get("tech_score", 50))))
        comm   = max(0, min(100, int(data.get("communication_score", 50))))
        prob   = max(0, min(100, int(data.get("problem_solving_score", 50))))
        total  = round((tech + comm + prob) / 3)

        report = EvaluationReport(
            session_id=session_id,
            total_score=total,
            tech_score=tech,
            communication_score=comm,
            problem_solving_score=prob,
            summary=data.get("summary", ""),
            details=data.get("details", {})
        )
        db.add(report)
        db.commit()
        print(f"[REPORT] Generated for session {session_id}: total={total}")

    except Exception as e:
        print(f"[REPORT] Generation failed: {e}")
        # Persist fallback report so the frontend always gets something
        try:
            fallback = EvaluationReport(
                session_id=session_id,
                total_score=50,
                tech_score=50,
                communication_score=50,
                problem_solving_score=50,
                summary="자동 분석 중 오류가 발생했습니다. 면접을 수고하셨습니다.",
                details={
                    "strengths": "분석 불가",
                    "weaknesses": "분석 불가",
                    "jd_fit": "분석 불가"
                }
            )
            db.add(fallback)
            db.commit()
        except Exception as e2:
            print(f"[REPORT] Fallback also failed: {e2}")
