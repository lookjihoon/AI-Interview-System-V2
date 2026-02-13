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
            temperature=0.7,
            num_predict=512
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
        db: Session
    ) -> Optional[QuestionBank]:
        """
        Get the most relevant question using RAG
        
        Args:
            user_id: User ID
            job_id: Job posting ID
            history_ids: List of already asked question IDs
            db: Database session
            
        Returns:
            QuestionBank object or None
        """
        # 1. Fetch context
        user = db.query(User).filter(User.id == user_id).first()
        job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
        
        if not job:
            raise ValueError(f"Job posting {job_id} not found")
        
        # 2. Create query string from context
        query_parts = []
        
        # Add job requirements
        if job.requirements:
            query_parts.append(f"Job Requirements: {job.requirements[:500]}")
        
        # Add target capabilities
        if job.target_capabilities:
            query_parts.append(f"Target Skills: {job.target_capabilities[:300]}")
        
        # Add resume context if available
        if user and user.resume_text:
            # Extract key skills from resume (first 400 chars as summary)
            resume_summary = user.resume_text[:400]
            query_parts.append(f"Candidate Background: {resume_summary}")
        
        # Combine into single query
        query_text = " | ".join(query_parts)
        
        print(f"\n[RAG] Query context length: {len(query_text)} chars")
        print(f"[RAG] Filtering out {len(history_ids)} used questions")
        
        # 3. Generate query embedding
        query_embedding = self.embeddings.embed_query(query_text)
        
        # 4. Vector search with filtering
        stmt = select(QuestionBank).order_by(
            QuestionBank.embedding.cosine_distance(query_embedding)
        )
        
        # Filter out already asked questions
        if history_ids:
            stmt = stmt.where(QuestionBank.id.notin_(history_ids))
        
        # Get top result
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
            template="""You are an expert technical interviewer evaluating a candidate's response.

**CRITICAL: YOU MUST RESPOND IN KOREAN (한국어). All feedback, follow-up questions, and evaluations MUST be written in Korean.**

Job Context:
{job_context}

Interview Question:
{question}

Candidate's Answer:
{answer}

Evaluate the answer and provide (IN KOREAN):
1. A score from 0-100 (0=completely wrong, 100=perfect answer)
2. Constructive feedback in Korean (2-3 sentences)
3. A relevant follow-up question in Korean to probe deeper

Return ONLY a valid JSON object in this exact format:
{{
    "score": <number 0-100>,
    "feedback": "<한국어로 피드백>",
    "follow_up_question": "<한국어로 후속 질문>"
}}

Do not include any text before or after the JSON. All text fields must be in Korean."""
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
            
            # Return fallback evaluation
            return {
                "score": 50,
                "feedback": "I received your answer. Let's continue with the next question.",
                "follow_up_question": "Can you elaborate on your experience with this topic?"
            }
        except Exception as e:
            print(f"[EVAL] Evaluation error: {e}")
            
            # Return fallback evaluation
            return {
                "score": 50,
                "feedback": "Thank you for your response.",
                "follow_up_question": "What other aspects of this topic are you familiar with?"
            }


# Singleton instance
_ai_service = None

def get_ai_service() -> InterviewAI:
    """Get or create AI service singleton"""
    global _ai_service
    if _ai_service is None:
        _ai_service = InterviewAI()
    return _ai_service
