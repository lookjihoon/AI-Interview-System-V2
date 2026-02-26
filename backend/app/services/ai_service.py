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


# ─── Phase Turn Boundaries (0-based human_turn count) ────────────────────────────
# turn=0  → Ask self-intro (no human answers yet)
# turn=1,2  → Technical RAG
# turn=3,4  → Behavioral (team project + follow-up)
# turn=5,6  → Personality (culture-fit + follow-up)
# turn=7    → Closing question (├ the 8th AI question asked)
# turn=8+   → Router ends the session after closing answer
PHASE2_TURNS = range(1, 3)   # turns 1-2  → Technical Hard Skills (RAG)
PHASE3_TURNS = range(3, 7)   # turns 3-6  → Behavioral / Personality (LLM-generated)
CLOSING_TURN = 7              # turn 7     → Closing question

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
            model="exaone3.5",
            temperature=0.1,
            num_predict=768,
            format="json"
        )
        # Text-only LLM for question rewriting (no JSON constraint)
        self.llm_text = ChatOllama(
            model="exaone3.5",
            temperature=0.2,
            num_predict=200,
        )
        # Dedicated evaluation LLM — temperature=0.4: sweet spot for Korean JSON with Llama 3.1 8B
        # (0.1 causes token stuttering/loop on Korean; 0.4 keeps outputs stable + readable)
        self.llm_eval = ChatOllama(
            model="exaone3.5",
            temperature=0.4,
            num_predict=512,
            format="json"
        )
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"
        )
        print("✓ InterviewAI initialized (exaone3.5 + all-mpnet-base-v2)")

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

    def _get_asked_questions(self, session_id: int, db: Session) -> List[str]:
        """Return list of AI question texts already asked this session (for anti-repetition)."""
        rows = db.query(Transcript).filter(
            Transcript.session_id == session_id,
            Transcript.sender == "ai",
            Transcript.question_id.isnot(None)  # only real RAG questions, not greetings
        ).order_by(Transcript.id.asc()).all()
        return [r.content for r in rows]

    def _generate_behavioral_question(self, turn: int, last_answer: str, resume_text: Optional[str]) -> str:
        """
    For Turn 4: team project / conflict behavioral question.
    For Turn 5: LLM follow-up on Turn 4 answer.
    For Turn 6: personality / cultural-fit question.
    For Turn 7: LLM follow-up on Turn 6 answer.
    Falls back to a hardcoded question on error.
    """
        resume_snippet = ""
        if resume_text:
            lines = [l.strip() for l in resume_text.splitlines() if l.strip()][:5]
            resume_snippet = " ".join(lines)

        if turn == 3:
            prompt = (
                "[SYSTEM] You are a professional Korean interviewer conducting a behavioral interview.\n"
                "Generate EXACTLY ONE behavioral interview question IN KOREAN that asks about:\n"
                "  - Team project experience\n"
                "  - The candidate's role in the team\n"
                "  - The most difficult challenge encountered and how they resolved it\n"
                f"Candidate resume summary: {resume_snippet or '(not provided)'}\n"
                "STRICT FORMAT RULE: End your question with a single proper Korean question ending such as "
                "'~하셨나요?', '~인가요?', '~있으신가요?', or '~주시겠어요?'.\n"
                "DO NOT append extra words or '~요.' after the question mark. Output ONLY the question sentence."
            )
            fallback = (
                "이력서를 바탕으로 말씀해 주시겠어요? 팀 프로젝트 경험 중 "
                "가장 어렵거나 갈등이 있었던 상황을, 본인이 어떤 역할을 맡아 어떻게 해결했는지 "
                "구체적으로 설명해 주시겠어요?"
            )
        elif turn == 4:  # team project follow-up
            prompt = (
                "[SYSTEM] You are a professional Korean interviewer.\n"
                "The candidate just answered a question about their team project and problem-solving experience.\n"
                f"Their answer: {last_answer[:300] if last_answer else '(no answer yet)'}\n"
                "Generate EXACTLY ONE follow-up question IN KOREAN that:\n"
                "  - Digs deeper into the specific process, decision, or lesson learned\n"
                "  - Does NOT repeat, rephrase, or re-ask the same question\n"
                "STRICT FORMAT RULE: End your question with a single proper Korean question ending such as "
                "'~하셨나요?', '~인가요?', '~있으신가요?', or '~주시겠어요?'.\n"
                "DO NOT append extra words or '~요.' after the question mark. Output ONLY the question sentence."
            )
            fallback = (
                "방금 말씀하신 경험에서 가장 인상 깊었던 배움이나, "
                "그 이후 유사한 상황에서 어떻게 다르게 접근하셨는지 구체적으로 말씀해 주시겠어요?"
            )
        elif turn == 5:  # personality / cultural fit
            prompt = (
                "[SYSTEM] You are a professional Korean interviewer conducting a personality and cultural-fit interview.\n"
                "Generate EXACTLY ONE personality/인성 interview question IN KOREAN.\n"
                "Choose ONE topic from the following list:\n"
                "  - 가장 크게 실패했던 경험과 그 극복 과정\n"
                "  - 스트레스나 압박을 받을 때 어떻게 관리하고 대처하는지\n"
                "  - 입사 후 3~5년 뒤 어때 모습을 목표로 하고 있는지\n"
                "  - 동료나 선배와 의견 충돌이 있을 때 어떻게 소통하는지\n"
                f"Candidate background hint: {resume_snippet or '(not provided)'}\n"
                "STRICT FORMAT RULE: End your question with a single proper Korean question ending such as "
                "'~하셨나요?', '~인가요?', '~있으신가요?', or '~주시겠어요?'.\n"
                "DO NOT append extra words or '~요.' after the question mark. Output ONLY the question sentence."
            )
            fallback = (
                "지금까지의 커리어에서 가장 크게 실패했던 경험과, "
                "그 상황을 어떻게 극복하고 어떤 교훈을 얻으셨는지 말씀해 주시겠어요?"
            )
        else:  # turn == 6 — personality follow-up
            prompt = (
                "[SYSTEM] You are a professional Korean interviewer.\n"
                "The candidate just answered a personality/인성 question.\n"
                f"Their answer: {last_answer[:300] if last_answer else '(no answer yet)'}\n"
                "Generate EXACTLY ONE follow-up question IN KOREAN that:\n"
                "  - Explores their values, mindset, or growth from the experience more deeply\n"
                "  - Does NOT repeat, rephrase, or re-ask the same question\n"
                "STRICT FORMAT RULE: End your question with a single proper Korean question ending such as "
                "'~하셨나요?', '~인가요?', '~있으신가요?', or '~주시겠어요?'.\n"
                "DO NOT append extra words or '~요.' after the question mark. Output ONLY the question sentence."
            )
            fallback = (
                "그 경험을 통해 본인의 어떤 가치관이나 업무 방식이 변화했는지, "
                "구체적인 사례와 함께 말씀해 주시겠어요?"
            )

        try:
            response = self.llm_text.invoke([HumanMessage(content=prompt)])
            q = response.content.strip()
            # Post-process: strip any trailing '~요.' duplicate suffix
            # e.g. '...주시겠어요?요.' -> '...주시겠어요?'
            q = q.rstrip()
            if q.endswith('요.') and '?' in q:
                q = q[: q.rfind('?') + 1]
            # Must be Korean, reasonably long, end with ? or proper Korean ending
            if len(q) > 15 and any(c in q for c in ['?', '요', '까']):
                print(f"[BEHAVIORAL] Turn {turn} LLM question: {q[:80]}")
                return q
        except Exception as e:
            print(f"[BEHAVIORAL] LLM error: {e}")
        return fallback

    def _get_last_human_answer(self, session_id: int, db: Session) -> str:
        """Return the most recent human transcript content, or empty string."""
        last = db.query(Transcript).filter(
            Transcript.session_id == session_id,
            Transcript.sender == "human"
        ).order_by(Transcript.id.desc()).first()
        return last.content if last else ""

    def _intro_already_asked(self, session_id: int, db: Session) -> bool:
        """Check whether the self-intro question has already been asked.
        Matches both '자기소개' and '자신을 소개' (the combined opening greeting phrase).
        """
        from sqlalchemy import or_
        return db.query(Transcript).filter(
            Transcript.session_id == session_id,
            Transcript.sender == "ai",
            or_(
                Transcript.content.contains("자기소개"),
                Transcript.content.contains("자신을 소개")
            )
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
        session_resume_text: Optional[str] = None,
        job_requirements: Optional[str] = None,
        asked_questions: Optional[List[str]] = None
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
[JD 자격 요건] {job_requirements[:300] if job_requirements else '(없음)'}
[이전 질문 목록 — 절대 반복 금지]
{chr(10).join(f'  - {q[:100]}' for q in (asked_questions or [])) or '  (없음)'}

[ANTI-REPETITION RULE - CRITICAL]
- Look at [이전 질문 목록] above.
- DO NOT ask about a topic or technology that has already been asked.
- DO NOT rephrase or restate any of the previous questions.
- If the base question is too similar to a previous one, change the topic angle entirely.

[SEMANTIC ANTI-REPETITION — CRITICAL]
- Even if the BASE QUESTION uses different wording, if the CONCEPT is the same as any previous question, you MUST refuse it and generate a question about a COMPLETELY DIFFERENT topic.
- Example: if "MSA Saga pattern" was already asked, do NOT ask about "distributed transaction", "eventual consistency", or any other MSA sub-topic.
- To determine if two questions are conceptually similar, ask: "Would answering one question also answer the other?" If YES, they are too similar.
- Pick a topic from the RESUME or JD that has NOT been covered yet.

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
        Phase-aware question selection (0-based human_turn count):
          Phase 1 (turn=0): self-introduction
          Phase 2 (turn=1,2): technical RAG questions (personalised)
          Phase 3 (turn=3-6): behavioral + personality questions (LLM-generated)
          Phase 4 (turn=7): closing question → returns dummy with category=CLOSING
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

        # ── Phase 3 (Turns 4-7): LLM-generated behavioral/personality questions — bypass RAG ──
        if turn in (3, 4, 5, 6):
            sub = "팀 프로젝트 / 갈등" if turn <= 4 else "인성 / 컬처핏"
            print(f"[Phase] → Phase 3 BEHAVIORAL/PERSONALITY (LLM-generated, turn={turn})")
            dummy = QuestionBank()
            dummy.id = None  # Not a RAG question
            dummy.question_text = self._generate_behavioral_question(
                turn=turn,
                last_answer=last_answer,
                resume_text=session_resume_text
            )
            dummy.category = "BEHAVIORAL"
            dummy.sub_category = sub
            return dummy

        if force_behavioral:
            print("[Phase] → Phase 3 BEHAVIORAL (RAG fallback)")
        else:
            print(f"[Phase] → Phase 2 TECHNICAL (turn {turn})")

        # Collect previously asked question texts for anti-repetition
        asked_questions = self._get_asked_questions(session_id, db) if session_id else []

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
        # Primary: IDs passed in from the router's history tracking
        real_history = [qid for qid in history_ids if qid and qid > 0]
        # Secondary: also query all question_ids from this session's transcripts (DB-level hard dedup)
        if session_id:
            db_used = db.query(Transcript.question_id).filter(
                Transcript.session_id == session_id,
                Transcript.question_id.isnot(None)
            ).all()
            db_used_ids = [row[0] for row in db_used if row[0]]
            # Merge both lists; set removes duplicates
            all_exclude = list(set(real_history + db_used_ids))
        else:
            all_exclude = real_history

        stmt = select(QuestionBank).order_by(
            QuestionBank.embedding.cosine_distance(query_embedding)
        )
        if all_exclude:
            stmt = stmt.where(QuestionBank.id.notin_(all_exclude))

        # Phase 3: force behavioral category filter
        if force_behavioral:
            stmt = stmt.where(
                QuestionBank.category.in_(list(BEHAVIORAL_CATEGORIES))
            )

        result = db.execute(stmt.limit(1)).scalar_one_or_none()

        if result:
            print(f"[RAG] Fetched: [{result.category}] {result.question_text[:80]}")
            # Personalise using last answer / resume / JD requirements + anti-repeat history
            result.question_text = self._personalise_question(
                base_question=result.question_text,
                last_answer=last_answer,
                session_resume_text=session_resume_text,
                job_requirements=job.requirements,
                asked_questions=asked_questions
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

        # ── Pre-LLM Python Guardrail (rule-based, never hallucinates) ───────────
        _stripped = user_answer.strip()
        _GIVEUP_KEYWORDS = ["모르겠", "기억나지", "없습니다", "잘 모르", "모릅니다", "패스", "pass"]
        if (
            len(_stripped) < 30
            or any(kw in _stripped for kw in _GIVEUP_KEYWORDS)
        ):
            print(f"[EVAL] Guardrail triggered (len={len(_stripped)}) — returning fixed score")
            return {
                "score": 15,
                "feedback": (
                    "답변이 너무 짧거나 핵심 내용이 포함되지 않았습니다. "
                    "직무 역량을 어필할 수 있는 구체적인 경험을 덧붙여주세요."
                ),
                "follow_up_question": (
                    "관련하여 조금이라도 알고 계신 부분이나, "
                    "유사한 경험이 있다면 말씀해 주시겠어요?"
                ),
            }

        # ── Legacy keyword fail-safe (very short / known surrender phrases) ──────
        answer_lower = _stripped.lower()
        if any(p in answer_lower for p in self._FAILSAFE_PATTERNS):
            print(f"[EVAL] Fail-safe triggered for known surrender pattern")
            return dict(self._FAILSAFE_RESULT)

        prompt_template = PromptTemplate(
            input_variables=["job_context", "question", "answer"],
            template="""You are a strict Korean technical interviewer. Score the candidate's answer and return ONLY valid JSON.

Scoring guide (0-100):
- 80-100: Correct answer WITH specific concrete examples, measurable metrics, explicit trade-offs, AND a clear STAR structure (Situation → Task → Action → Result).
- 60-79:  Correct concepts but lacks depth, concrete examples, or measurable results.
- 40-59:  Partially correct or vague reasoning without specifics.
- 0-39:   Wrong answer, irrelevant content, or just complaining about the question.

[CRITICAL SCORING RULES - MUST ENFORCE]
1. If the answer lacks at least ONE concrete technical example OR measurable metric (e.g., "reduced latency by 30%", "handled 10k RPS"), the MAXIMUM score is 50.
2. If the STAR structure (Situation, Task, Action, Result) is not clearly present, the MAXIMUM score is 55.
3. You MUST explicitly state in the feedback what specific examples or metrics are missing.
4. Never give a score above 60 for vague or generic answers, even if they sound plausible.
5. If the answer is 'I don't know', gibberish, or a single word: score must be 10-20.
6. If candidate says your question was wrong/hallucinated: score 0-39, acknowledge briefly in feedback.

Job context: {job_context}
Question: {question}
Answer: {answer}

You MUST output ONLY this JSON structure with EXACTLY these keys. All text values must be in Korean:
{{"score": 75, "feedback": "피드백 내용을 여기에 한국어로 작성 (부족한 구체적 예시 명시 필필)", "follow_up_question": "한국어 꼬리질문"}}

Now output the JSON for the answer above:""")

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


def generate_final_report(
    session_id: int, 
    db: Session, 
    vision_data: Optional[Dict[str, Any]] = None, 
    emotion_timeline: Optional[List[Dict[str, Any]]] = None,
    total_time: int = 0
) -> None:
    """
    Generate a comprehensive evaluation report for a completed interview session.

    SCORING STRATEGY (Phase 8.9):
    - Numerical scores are computed with Python math — LLM cannot inflate them.
    - avg_turn_score: simple average of all human Transcript.score values.
    - tech_score / problem_solving_score: derived from avg_turn_score with bias.
    - non_verbal_score: pure heuristic from vision_data percentages.
    - communication_score: single LLM-only text-based score (harder to game).
    - LLM is called ONLY for text fields: summary, strengths, weaknesses, jd_fit, vision_analysis.
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

    # ── Collect all transcripts ──────────────────────────────────────────────
    transcripts = db.query(Transcript).filter(
        Transcript.session_id == session_id
    ).order_by(Transcript.id.asc()).all()

    # ── MATH: Average turn score from persisted per-turn scores ─────────────
    scored_turns = [t.score for t in transcripts if t.sender == "human" and t.score is not None]
    if scored_turns:
        avg_turn_score = round(sum(scored_turns) / len(scored_turns))
    else:
        avg_turn_score = 50  # fallback if no scores were persisted
    print(f"[REPORT] avg_turn_score={avg_turn_score} from {len(scored_turns)} scored turns: {scored_turns}")

    # ── MATH: Derive component scores from avg ───────────────────────────────
    # tech_score: weighted toward avg, slightly penalised (technical bar is high)
    tech_score = max(0, min(100, int(avg_turn_score * 0.95)))
    # problem_solving_score: same base, slightly harsher penalty for lack of STAR
    problem_solving_score = max(0, min(100, int(avg_turn_score * 0.90)))

    # ── MATH: Non-verbal score from vision_data (pre-LLM, for prompt context only) ─
    vision_summary = "(not provided)"
    pre_nv_score = 70  # used only for the LLM prompt
    if vision_data and isinstance(vision_data, dict) and vision_data:
        # vision_data is raw counts: { 'neutral': 12, 'happy': 3, 'sad': 1, ... }
        total_emotions = sum(v for v in vision_data.values() if isinstance(v, (int, float)))
        if total_emotions > 0:
            positive = vision_data.get('neutral', 0) + vision_data.get('happy', 0)
            ratio = positive / total_emotions
            # Base score 50 + up to 50 points based on positive expression ratio
            pre_nv_score = int(50 + (ratio * 50))
            pre_nv_score = max(0, min(100, pre_nv_score))
            pct_str = ", ".join(
                f"{k}: {round(v/total_emotions*100, 1)}%" for k, v in vision_data.items() if isinstance(v, (int, float))
            )
            vision_summary = f"{pct_str} ({int(total_emotions)} frames)"
        else:
            vision_summary = "(no frames captured)"
    print(f"[REPORT] pre_nv_score={pre_nv_score}, vision_summary={vision_summary}")

    # ── Build Q&A text for LLM (text generation only) ────────────────────────
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

    interview_text = "\n\n".join(qa_pairs[:7])

    # Scored turn breakdown for LLM context
    score_breakdown = ", ".join(f"Turn {i+1}: {s}" for i, s in enumerate(scored_turns)) or "(none)"

    # ── LLM prompt: TEXT FIELDS ONLY, scores pre-computed ───────────────────
    prompt = f"""You are a Korean interviewer writing a final evaluation report. Return ONLY valid JSON.

Job position: {job_title}
Job requirements: {job.requirements[:300] if job and job.requirements else '(none)'}

Interview transcript:
{interview_text}

Per-turn scores (already computed, DO NOT change): {score_breakdown}
Average turn score: {avg_turn_score}/100
Tech score (pre-computed): {tech_score}/100
Problem-solving score (pre-computed): {problem_solving_score}/100
Non-verbal attitude score (pre-computed): {pre_nv_score}/100
Candidate facial/emotion data: {vision_summary}

YOUR ONLY JOB: Write honest Korean text for summary, strengths, weaknesses, jd_fit, vision_analysis.

Rules:
1. The summary MUST reflect the actual avg_turn_score={avg_turn_score}. If it is below 60, the summary MUST be critical.
2. If avg_turn_score < 50, state the candidate struggled significantly.
3. If avg_turn_score >= 75, state performance was strong.
4. weaknesses MUST explicitly mention any LOW-scoring turns (below 50) and what was missing (e.g., 구체적 예시 부재, STAR 구조 미적용).
5. vision_analysis: write 1-2 Korean sentences about non-verbal attitude from emotion data. If no data, write "카메라 미사용으로 비언어 분석 불가."
6. 지원자의 비언어적 면접 태도 점수는 {pre_nv_score}/100점입니다. Summary 또는 Strengths/Weaknesses 작성 시, 표정, 긴장도, 눈맞춤 등 면접 태도에 대한 피드백을 반드시 1-2문장 포함하세요.

Output ONLY this JSON (all text in Korean, do NOT change the numeric fields):
{{"summary": "한국어 종합 평가 1-2문장", "strengths": "강점 2-3가지 한국어 서술", "weaknesses": "개선점 — 낙은 점수 턴 언급 포함 2-3가지 한국어 서술", "jd_fit": "JD 적합도 한국어 서술 + 상/중/하 평가", "vision_analysis": "비언어 표정 분석 한국어 1-2문장", "non_verbal_feedback": "표정/긴장도/눈맞춤 등 면접 태도 종합 1줄 한국어"}}

Now output the JSON:"""

    try:
        ai = get_ai_service()
        response = ai.llm_eval.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        # Strip markdown fences
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        text_data = json.loads(raw)

        # ── HARD-OVERRIDE: recalculate scores in Python AFTER LLM parse ──────
        # Non-verbal: count-based formula (vision_data = raw counts from frontend)
        nv_score = 70  # default when no camera data
        try:
            if vision_data and isinstance(vision_data, dict):
                total_v = sum(v for v in vision_data.values() if isinstance(v, (int, float)))
                if total_v > 0:
                    positive_v = vision_data.get('neutral', 0) + vision_data.get('happy', 0)
                    nv_score = int(50 + ((positive_v / total_v) * 50))
                    nv_score = max(0, min(100, nv_score))
            print(f"[REPORT] POST-LLM nv_score={nv_score} (vision_data keys: {list(vision_data.keys()) if vision_data else None})")
        except Exception as nv_err:
            print(f"[REPORT] nv_score calculation FAILED: {nv_err!r} — keeping default 70")
            nv_score = 70

        # communication_score close to avg_turn_score
        comm_score = max(0, min(100, int(avg_turn_score * 1.0)))

        # Weighted total: Tech 40% | Comm 25% | Problem 25% | NV 10%
        total = int(round(
            tech_score            * 0.40 +
            comm_score            * 0.25 +
            problem_solving_score * 0.25 +
            nv_score              * 0.10
        ))
        print(f"[REPORT] FINAL SCORES — tech={tech_score}, comm={comm_score}, "
              f"ps={problem_solving_score}, nv={nv_score}, total={total}")

        details = {
            # ── Text fields from LLM ───────────────────────────────────────
            "strengths":           text_data.get("strengths", ""),
            "weaknesses":          text_data.get("weaknesses", ""),
            "jd_fit":              text_data.get("jd_fit", ""),
            "vision_analysis":     text_data.get("vision_analysis", "카메라 미사용으로 비언어 분석 불가."),
            "non_verbal_feedback": text_data.get("non_verbal_feedback", ""),  # ← dedicated 1-line attitude badge
            "score_breakdown":     score_breakdown,
            "avg_turn_score":      avg_turn_score,
            # ── Total interview elapsed time (seconds) ────────────────────
            "total_time":          total_time,
            # ── AUTHORITATIVE Python-computed scores (overrides any LLM value) ─
            "tech_score":             tech_score,
            "communication_score":    comm_score,
            "problem_solving_score":  problem_solving_score,
            "non_verbal_score":       nv_score,
            "total_score":            total,
        }

        report = EvaluationReport(
            session_id=session_id,
            total_score=total,
            tech_score=tech_score,
            communication_score=comm_score,
            problem_solving_score=problem_solving_score,
            non_verbal_score=nv_score,
            summary=text_data.get("summary", ""),
            details=details,
            emotion_timeline=emotion_timeline
        )
        # ── ULTIMATE OVERRIDE: explicit property write before INSERT ──────────
        # Guards against any ORM default / constructor scoping issue
        report.non_verbal_score = nv_score
        report.total_score      = total
        db.add(report)
        db.commit()
        print(f"[REPORT] Saved for session {session_id}: avg_turn={avg_turn_score}, total={total}, nv={nv_score}")

    except Exception as e:
        print(f"[REPORT] Generation failed: {e}")
        # Persist fallback report so the frontend always gets something
        try:
            fallback_details = {
                "strengths": "",
                "weaknesses": "보고서 생성 중 오류 발생.",
                "jd_fit": "",
                "vision_analysis": "비언어 분석 불가.",
                "score_breakdown": score_breakdown,
                "avg_turn_score": avg_turn_score,
            }
            total_fb = round(
                tech_score * 0.35 + avg_turn_score * 0.25 +
                problem_solving_score * 0.25 + non_verbal_score * 0.15
            )
            fallback = EvaluationReport(
                session_id=session_id,
                total_score=total_fb,
                tech_score=tech_score,
                communication_score=avg_turn_score,
                problem_solving_score=problem_solving_score,
                non_verbal_score=non_verbal_score,
                summary="보고서 생성 중 오류가 발생했습니다.",
                details=fallback_details
            )
            db.add(fallback)
            db.commit()
            print(f"[REPORT] Fallback report saved for session {session_id}")
        except Exception as fb_err:
            print(f"[REPORT] Fallback also failed: {fb_err}")


