"""
AI Interview Service
Implements the core AI interviewer logic using LangChain and RAG
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
import json

from langchain_ollama import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage

from models import User, JobPosting, QuestionBank, InterviewSession, Transcript
from database import SessionLocal


class InterviewAI:
    """
    AI Interviewer Brain
    Handles question selection via RAG and answer evaluation
    """
    
    def __init__(self):
        """Initialize LLM and embedding models"""
        # Initialize Ollama LLM
        self.llm = ChatOllama(
            model="llama3.1",
            temperature=0.1,   # Low temperature = more deterministic, less hallucination
            num_predict=768,
            format="json"      # Force JSON output to prevent wrappers
        )
        
        # Initialize embedding model (same as used for question bank)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"
        )
        
        print("✓ InterviewAI initialized with llama3.1 and all-mpnet-base-v2")
    
    def get_optimal_question(
        self,
        user_id: int,
        job_id: int,
        history_ids: List[int],
        db: Session,
        session_id: int = None
    ) -> Optional[QuestionBank]:
        """
        Get the most relevant question using RAG.
        For the very first turn, returns a fixed self-introduction prompt.
        """
        # ── 첫 번째 질문: 자기소개 여부를 transcript 텍스트로 확인 ────
        # history_ids 기반 체크는 id=None인 자기소개를 감지 못하므로
        # transcript를 직접 조회해 "자기소개" 포함 여부를 확인한다
        intro_already_asked = False
        if session_id is not None:
            intro_already_asked = db.query(Transcript).filter(
                Transcript.session_id == session_id,
                Transcript.sender == "ai",
                Transcript.content.contains("자기소개")
            ).first() is not None

        if not intro_already_asked:
            print("[RAG] First question → self-introduction (skipping vector search)")
            dummy = QuestionBank()
            dummy.id = None
            dummy.question_text = "먼저, 간단하게 1분 자기소개를 부탁드립니다."
            dummy.category = "BEHAVIORAL"
            dummy.sub_category = "자기소개"
            return dummy

        # ── 이후 질문은 RAG 벡터 검색 ────────────────────────────────
        # 1. Fetch context
        user = db.query(User).filter(User.id == user_id).first()
        job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
        
        if not job:
            raise ValueError(f"Job posting {job_id} not found")
        
        # 2. Create query string from context
        query_parts = []
        
        if job.requirements:
            query_parts.append(f"Job Requirements: {job.requirements[:500]}")
        if job.target_capabilities:
            query_parts.append(f"Target Skills: {job.target_capabilities[:300]}")
        if user and user.resume_text:
            query_parts.append(f"Candidate Background: {user.resume_text[:400]}")
        
        query_text = " | ".join(query_parts)
        
        print(f"\n[RAG] Query context length: {len(query_text)} chars")
        print(f"[RAG] Filtering out {len(history_ids)} used questions")
        
        # 3. Generate query embedding
        query_embedding = self.embeddings.embed_query(query_text)
        
        # 4. Vector search – exclude already-asked question IDs
        # Filter out placeholder id=-1 as well just in case
        real_history = [qid for qid in history_ids if qid and qid > 0]
        stmt = select(QuestionBank).order_by(
            QuestionBank.embedding.cosine_distance(query_embedding)
        )
        if real_history:
            stmt = stmt.where(QuestionBank.id.notin_(real_history))
        
        result = db.execute(stmt.limit(1)).scalar_one_or_none()
        
        if result:
            print(f"[RAG] Selected question: {result.question_text[:80]}...")
            print(f"[RAG] Category: {result.category} / {result.sub_category}")
        else:
            print("[RAG] No suitable question found")
        
        return result

    
    def evaluate_answer(
        self,
        question_text: str,
        user_answer: str,
        job_context: str
    ) -> Dict[str, Any]:
        """
        Evaluate user's answer using LLM
        
        Args:
            question_text: The interview question
            user_answer: User's response
            job_context: Job requirements and context
            
        Returns:
            Dict with score, feedback, and follow_up_question
        """
        # Create evaluation prompt
        prompt_template = PromptTemplate(
            input_variables=["job_context", "question", "answer"],
            template="""당신은 한국어로 기술 면접을 진행하는 전문 AI 면접관입니다.

[직무 맥락]
{job_context}

[면접 질문]
{question}

[지원자 답변]
{answer}

[지시사항]
1. 위 답변을 평가하고 점수(0-100), 피드백, 후속 질문을 생성하세요.
2. 답변이 "모르겠습니다"이거나 불충분한 경우, 피드백에서 정중하게 격려하세요.
3. 모든 텍스트는 반드시 자연스러운 비즈니스 한국어로 작성하세요. 영어를 절대 사용하지 마세요.
4. 아래 JSON 형식만 출력하세요. JSON 이외의 텍스트는 절대 출력하지 마세요.

{{"score": <0-100 사이 정수>, "feedback": "<2-3문장의 한국어 피드백>", "follow_up_question": "<한국어 후속 질문>"}}"""
        )
        
        # Format prompt
        formatted_prompt = prompt_template.format(
            job_context=job_context[:500],  # Limit context length
            question=question_text,
            answer=user_answer
        )
        
        print(f"\n[EVAL] Evaluating answer (length: {len(user_answer)} chars)")
        
        try:
            # Get LLM response
            response = self.llm.invoke([HumanMessage(content=formatted_prompt)])
            response_text = response.content.strip()
            
            print(f"[EVAL] LLM response length: {len(response_text)} chars")
            
            # Parse JSON response
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            evaluation = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["score", "feedback", "follow_up_question"]
            for field in required_fields:
                if field not in evaluation:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure score is in valid range
            evaluation["score"] = max(0, min(100, int(evaluation["score"])))
            
            print(f"[EVAL] Score: {evaluation['score']}/100")
            
            return evaluation
            
        except json.JSONDecodeError as e:
            print(f"[EVAL] JSON parse error: {e}")
            print(f"[EVAL] Response text: {response_text[:200]}")
            
            # Korean fallback evaluation
            return {
                "score": 50,
                "feedback": "답변을 잘 받았습니다. 다음 질문으로 넘어가겠습니다.",
                "follow_up_question": "이 주제에 대해 경험하신 것을 좀 더 구체적으로 설명해 주시겠어요?"
            }
        except Exception as e:
            print(f"[EVAL] Evaluation error: {e}")
            
            # Korean fallback evaluation
            return {
                "score": 50,
                "feedback": "답변 감사합니다. 괜찮으시다면 좀 더 자세히 설명해 주세요.",
                "follow_up_question": "관련하여 실무에서 겪으신 사례가 있으신가요?"
            }


# Singleton instance
_ai_service = None

def get_ai_service() -> InterviewAI:
    """Get or create AI service singleton"""
    global _ai_service
    if _ai_service is None:
        _ai_service = InterviewAI()
    return _ai_service
