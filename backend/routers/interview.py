"""
Interview API Router
Handles interview session management and AI-powered chat
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import get_db
from models import InterviewSession, Transcript, User, JobPosting, SessionStatus
from app.services.ai_service import get_ai_service

router = APIRouter(
    prefix="/api/interview",
    tags=["interview"]
)


# Pydantic Schemas
class InterviewStartRequest(BaseModel):
    """Schema for starting an interview"""
    user_id: int = Field(..., description="ID of the candidate")
    job_id: int = Field(..., description="ID of the job posting")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 2,
                "job_id": 1
            }
        }


class InterviewStartResponse(BaseModel):
    """Schema for interview start response"""
    session_id: int
    message: str
    user_name: str
    job_title: str
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Schema for chat interaction"""
    session_id: int = Field(..., description="Interview session ID")
    user_answer: Optional[str] = Field(None, description="User's answer to previous question")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": 1,
                "user_answer": "I have 5 years of experience with Python, focusing on FastAPI and Django..."
            }
        }


class ChatResponse(BaseModel):
    """Schema for chat response"""
    evaluation: Optional[Dict[str, Any]] = Field(None, description="Evaluation of user's answer")
    next_question: str = Field(..., description="Next interview question")
    question_id: Optional[int] = Field(None, description="ID of the question (None for self-intro)")
    category: str = Field(..., description="Question category")


class TranscriptItem(BaseModel):
    """Schema for transcript item"""
    sender: str
    content: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


class SessionDetailResponse(BaseModel):
    """Schema for session details"""
    session_id: int
    user_name: str
    job_title: str
    status: str
    created_at: datetime
    transcript: List[TranscriptItem]
    
    class Config:
        from_attributes = True


# API Endpoints
@router.post("/start", response_model=InterviewStartResponse, status_code=201)
async def start_interview(
    request: InterviewStartRequest,
    db: Session = Depends(get_db)
):
    """
    Start a new interview session
    
    - **user_id**: ID of the candidate
    - **job_id**: ID of the job posting
    
    Returns the session ID and initial greeting
    """
    # Verify user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify job posting exists
    job = db.query(JobPosting).filter(JobPosting.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    
    # Create new interview session
    session = InterviewSession(
        user_id=request.user_id,
        job_posting_id=request.job_id,
        status=SessionStatus.IN_PROGRESS
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Add initial greeting to transcript
    greeting = (
        f"안녕하세요, {user.name}님! "
        f"{job.title} 직무 면접에 오신 것을 환영합니다. "
        f"저는 AI 면접관입니다. 편안한 마음으로 면접에 임해주세요."
    )
    
    greeting_transcript = Transcript(
        session_id=session.id,
        sender="ai",
        content=greeting
    )
    
    db.add(greeting_transcript)
    db.commit()
    
    return InterviewStartResponse(
        session_id=session.id,
        message=greeting,
        user_name=user.name,
        job_title=job.title
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Continue interview conversation
    
    - **session_id**: Interview session ID
    - **user_answer**: User's answer to the previous question (optional for first turn)
    
    Returns evaluation of the answer and the next question
    """
    # Verify session exists
    session = db.query(InterviewSession).filter(
        InterviewSession.id == request.session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    if session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Interview session is not active")
    
    # Get AI service
    ai_service = get_ai_service()
    
    evaluation = None
    
    # If user provided an answer, evaluate it
    if request.user_answer:
        # Save user's answer to transcript
        user_transcript = Transcript(
            session_id=session.id,
            sender="human",
            content=request.user_answer
        )
        db.add(user_transcript)
        db.commit()
        
        # Get the previous question from transcript
        previous_question = db.query(Transcript).filter(
            Transcript.session_id == session.id,
            Transcript.sender == "ai"
        ).order_by(Transcript.timestamp.desc()).first()
        
        if previous_question:
            # Get job context for evaluation
            job = db.query(JobPosting).filter(
                JobPosting.id == session.job_posting_id
            ).first()
            
            job_context = f"{job.requirements or ''} {job.target_capabilities or ''}"
            
            # Evaluate the answer
            evaluation = ai_service.evaluate_answer(
                question_text=previous_question.content,
                user_answer=request.user_answer,
                job_context=job_context
            )
    
    # Get history of asked questions by extracting question_ids from transcript
    asked_transcripts = db.query(Transcript).filter(
        Transcript.session_id == session.id,
        Transcript.sender == "ai",
        Transcript.question_id.isnot(None)
    ).all()
    
    # Extract question IDs
    history_ids = [t.question_id for t in asked_transcripts]
    
    print(f"[CHAT] Session {session.id}: {len(history_ids)} questions already asked")
    
    # Get the next optimal question
    next_question_obj = ai_service.get_optimal_question(
        user_id=session.user_id,
        job_id=session.job_posting_id,
        history_ids=history_ids,
        db=db,
        session_id=session.id   # needed for transcript-based self-intro check
    )
    
    if not next_question_obj:
        # No more questions available, end interview
        session.status = SessionStatus.COMPLETED
        db.commit()
        
        raise HTTPException(
            status_code=200,
            detail="Interview completed! No more questions available."
        )
    
    # Save the new question to transcript with question_id
    ai_transcript = Transcript(
        session_id=session.id,
        sender="ai",
        content=next_question_obj.question_text,
        question_id=next_question_obj.id  # Track which question was asked
    )
    db.add(ai_transcript)
    db.commit()
    
    return ChatResponse(
        evaluation=evaluation,
        next_question=next_question_obj.question_text,
        question_id=next_question_obj.id,
        category=f"{next_question_obj.category} / {next_question_obj.sub_category}"
    )


@router.get("/session/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Get interview session details and transcript
    
    - **session_id**: Interview session ID
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    # Get user and job info
    user = db.query(User).filter(User.id == session.user_id).first()
    job = db.query(JobPosting).filter(JobPosting.id == session.job_posting_id).first()
    
    # Get transcript
    transcripts = db.query(Transcript).filter(
        Transcript.session_id == session_id
    ).order_by(Transcript.timestamp.asc()).all()
    
    return SessionDetailResponse(
        session_id=session.id,
        user_name=user.name if user else "Unknown",
        job_title=job.title if job else "Unknown",
        status=session.status.value,
        created_at=session.created_at,
        transcript=[TranscriptItem(
            sender=t.sender,
            content=t.content,
            timestamp=t.timestamp
        ) for t in transcripts]
    )


@router.post("/session/{session_id}/end")
async def end_interview(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    End an interview session
    
    - **session_id**: Interview session ID
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    session.status = SessionStatus.COMPLETED
    db.commit()
    
    return {
        "message": "Interview session ended successfully",
        "session_id": session_id,
        "status": session.status.value
    }
