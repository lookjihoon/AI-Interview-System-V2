"""
Interview API Router
Handles interview session management and AI-powered chat
"""
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import get_db
from models import InterviewSession, Transcript, User, JobPosting, SessionStatus, EvaluationReport
from app.services.ai_service import get_ai_service, generate_final_report

# Upload directories
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
AUDIO_DIR = Path("uploads/audio")
AUDIO_DIR.mkdir(exist_ok=True)


def generate_tts(text: str, session_id: int, turn: int) -> Optional[str]:
    """
    Generate a Korean TTS MP3 using gTTS and return the static URL.
    Returns None silently if gTTS is not installed or generation fails.
    """
    try:
        from gtts import gTTS
        filename = f"session_{session_id}_turn_{turn}.mp3"
        filepath = AUDIO_DIR / filename
        tts = gTTS(text=text, lang="ko", slow=False)
        tts.save(str(filepath))
        print(f"[TTS] Saved {filepath}")
        return f"/static/audio/{filename}"
    except ImportError:
        print("[TTS] gTTS not installed — skipping audio generation")
        return None
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return None


def parse_pdf(file_path: str) -> str:
    """Extract text from a PDF file using PyPDFLoader. Returns empty string on failure."""
    try:
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        text = "\n".join(page.page_content for page in pages)
        print(f"[PDF] Extracted {len(text)} chars from {file_path}")
        return text.strip()
    except Exception as e:
        print(f"[PDF] Parse error: {e}")
        return ""

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
    audio_url: Optional[str] = None

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Schema for chat interaction"""
    session_id: int = Field(..., description="Interview session ID")
    user_answer: Optional[str] = Field(None, description="User's answer to previous question")
    vision_data: Optional[Dict[str, Any]] = Field(None, description="Emotion percentages from webcam analysis e.g. {neutral: 50, happy: 30}")
    answer_time: Optional[int] = Field(0, description="Time taken to type/speak the answer in seconds")
    total_time: Optional[int] = Field(0, description="Total elapsed interview time in seconds")

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
    audio_url: Optional[str] = Field(None, description="TTS audio URL for next_question")


class TranscriptItem(BaseModel):
    """Schema for transcript item"""
    sender: str
    content: str
    timestamp: datetime
    score: Optional[int] = None
    feedback: Optional[str] = None
    answer_time: Optional[int] = None   # seconds; None for AI turns

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
    user_id: int = Form(..., description="ID of the candidate"),
    job_id: int  = Form(..., description="ID of the job posting"),
    resume: Optional[UploadFile] = File(None, description="PDF resume (optional)"),
    db: Session = Depends(get_db)
):
    """
    Start a new interview session (multipart/form-data).

    - **user_id**: candidate ID
    - **job_id**: job posting ID
    - **resume**: optional PDF file — parsed text is stored for personalised questions
    """
    # Verify user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # Verify job
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="채용 공고를 찾을 수 없습니다.")

    # ── PDF 파싱 ───────────────────────────────────────────────────
    resume_path_str = None
    resume_text_str = None

    if resume and resume.filename:
        if not resume.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")

        # 고유 파일명으로 저장
        safe_name = f"{uuid.uuid4().hex}_{resume.filename}"
        save_path  = UPLOAD_DIR / safe_name
        try:
            with save_path.open("wb") as f:
                shutil.copyfileobj(resume.file, f)
            resume_path_str = str(save_path)
            resume_text_str = parse_pdf(resume_path_str) or None
            print(f"[UPLOAD] Resume saved → {save_path}")
        except Exception as e:
            print(f"[UPLOAD] Failed to save resume: {e}")
            # Don't crash — proceed without resume
        finally:
            await resume.close()

    # ── 세션 생성 ──────────────────────────────────────────────────
    session = InterviewSession(
        user_id=user_id,
        job_posting_id=job_id,
        resume_path=resume_path_str,
        resume_text=resume_text_str,
        status=SessionStatus.IN_PROGRESS
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Combine greeting + first self-intro question into ONE message / ONE TTS
    if resume_text_str:
        opening = (
            f"안녕하세요, {user.name}님! "
            f"{job.title} 직무 면접에 오신 것을 환영합니다. "
            f"이력서를 잘 받았습니다. 이력서를 바탕으로 맞춤형 질문을 드리겠습니다. "
            f"먼저, 1분 내외로 자신을 소개해 주시겠어요?"
        )
    else:
        opening = (
            f"안녕하세요, {user.name}님! "
            f"{job.title} 직무 면접에 오신 것을 환영합니다. "
            f"저는 AI 면접관입니다. 편안한 마음으로 면접에 임해주세요. "
            f"먼저, 1분 내외로 자신을 소개해 주시겠어요?"
        )

    db.add(Transcript(session_id=session.id, sender="ai", content=opening))
    db.commit()

    # Generate TTS for the combined opening message
    opening_audio_url = generate_tts(opening, session.id, 0)

    return InterviewStartResponse(
        session_id=session.id,
        message=opening,
        user_name=user.name,
        job_title=job.title,
        audio_url=opening_audio_url,
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
        # Save user's answer to transcript first (score=None until evaluated)
        human_tx = Transcript(session_id=session.id, sender="human", content=request.user_answer,
                              answer_time=request.answer_time or 0)
        db.add(human_tx)
        db.commit()
        db.refresh(human_tx)  # get the new row's id

        # Count human turns to detect final turn (turn 7 = answer to closing question)
        human_turn_count = db.query(Transcript).filter(
            Transcript.session_id == session.id,
            Transcript.sender == "human"
        ).count()

        # Turn 8: user answered the closing question → generate farewell then COMPLETED
        if human_turn_count >= 8:
            print(f"[CHAT] Turn 8 reached — vision_data received: {request.vision_data!r}")
            goodbye = ai_service.generate_closing_response(request.user_answer or "")
            db.add(Transcript(session_id=session.id, sender="ai", content=goodbye))
            session.status = SessionStatus.COMPLETED
            db.commit()
            # Generate final report with vision data (best-effort, won't block response)
            try:
                generate_final_report(
                    session_id=session.id,
                    db=db,
                    vision_data=request.vision_data,
                    total_time=request.total_time or 0
                )
            except Exception as report_err:
                print(f"[REPORT] Non-blocking error: {report_err}")
            audio_url = generate_tts(goodbye, session.id, human_turn_count)
            return ChatResponse(
                evaluation=None,
                next_question=goodbye,
                question_id=None,
                category="CLOSING / 면접 종료",
                audio_url=audio_url
            )

        # Normal evaluation for turns 1-6
        previous_question = db.query(Transcript).filter(
            Transcript.session_id == session.id,
            Transcript.sender == "ai"
        ).order_by(Transcript.timestamp.desc()).first()

        if previous_question:
            job = db.query(JobPosting).filter(JobPosting.id == session.job_posting_id).first()
            job_context = f"{job.requirements or ''} {job.target_capabilities or ''}"
            evaluation = ai_service.evaluate_answer(
                question_text=previous_question.content,
                user_answer=request.user_answer,
                job_context=job_context
            )
            # ── Persist score AND feedback to the transcript row ───────────────────
            if evaluation and evaluation.get("score") is not None:
                human_tx.score    = int(evaluation["score"])
                human_tx.feedback = evaluation.get("feedback") or evaluation.get("comment") or ""
                db.commit()

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
        session_id=session.id,
        session_resume_text=session.resume_text  # use uploaded PDF resume if available
    )
    
    # ── CLOSING phase (turn 6): ask closing question, keep IN_PROGRESS ────────
    if next_question_obj and getattr(next_question_obj, "category", "") == "CLOSING":
        db.add(Transcript(session_id=session.id, sender="ai", content=next_question_obj.question_text))
        # Do NOT set COMPLETED yet — user still needs to reply
        db.commit()
        turn_n = db.query(Transcript).filter(Transcript.session_id == session.id, Transcript.sender == "ai").count()
        audio_url = generate_tts(next_question_obj.question_text, session.id, turn_n)
        return ChatResponse(
            evaluation=evaluation,
            next_question=next_question_obj.question_text,
            question_id=None,
            category="CLOSING / 마무리",
            audio_url=audio_url
        )

    # ── No question found ────────────────────────────────────────────────────
    if not next_question_obj:
        goodbye = "오늘 면접은 여기까지입니다. 수고하셨습니다. 결과를 분석 후 안내드리겠습니다."
        db.add(Transcript(session_id=session.id, sender="ai", content=goodbye))
        session.status = SessionStatus.COMPLETED
        db.commit()
        turn_n = db.query(Transcript).filter(Transcript.session_id == session.id, Transcript.sender == "ai").count()
        audio_url = generate_tts(goodbye, session.id, turn_n)
        return ChatResponse(
            evaluation=evaluation,
            next_question=goodbye,
            question_id=None,
            category="CLOSING / 마무리",
            audio_url=audio_url
        )

    # ── Normal question flow ─────────────────────────────────────────────────
    # Save the new question to transcript with question_id
    ai_transcript = Transcript(
        session_id=session.id,
        sender="ai",
        content=next_question_obj.question_text,
        question_id=next_question_obj.id
    )
    db.add(ai_transcript)
    db.commit()

    turn_n = db.query(Transcript).filter(Transcript.session_id == session.id, Transcript.sender == "ai").count()
    audio_url = generate_tts(next_question_obj.question_text, session.id, turn_n)
    return ChatResponse(
        evaluation=evaluation,
        next_question=next_question_obj.question_text,
        question_id=next_question_obj.id,
        category=f"{next_question_obj.category} / {next_question_obj.sub_category or ''}",
        audio_url=audio_url
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


@router.get("/session/{session_id}/transcript", response_model=List[TranscriptItem])
async def get_transcript(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the transcript for an interview session.
    Returns an empty list [] for new sessions with no messages yet.
    Never returns 404 — an empty transcript is a valid state.
    """
    # Verify the session exists first
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    transcripts = db.query(Transcript).filter(
        Transcript.session_id == session_id
    ).order_by(Transcript.timestamp.asc()).all()

    # Return empty list for brand-new sessions — this is correct REST behaviour
    return [
        TranscriptItem(
            sender=t.sender,
            content=t.content,
            timestamp=t.timestamp,
            score=t.score,
            feedback=t.feedback,
            answer_time=t.answer_time,
        )
        for t in transcripts
    ]




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


# ── Pydantic schema for Report response ─────────────────────────────────────
class ReportResponse(BaseModel):
    session_id: int
    total_score: int
    tech_score: Optional[int] = None
    communication_score: Optional[int] = None
    problem_solving_score: Optional[int] = None
    non_verbal_score: Optional[int] = None      # ← was MISSING — FastAPI was stripping this field!
    summary: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/session/{session_id}/report", response_model=ReportResponse)
async def get_report(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Fetch the final evaluation report for a completed session.
    Returns 404 while report is still being generated.
    """
    report = db.query(EvaluationReport).filter(
        EvaluationReport.session_id == session_id
    ).first()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="리포트가 아직 생성 중입니다. 잠시 후 다시 시도해 주세요."
        )

    return ReportResponse(
        session_id=report.session_id,
        total_score=report.total_score,
        tech_score=report.tech_score,
        communication_score=report.communication_score,
        problem_solving_score=report.problem_solving_score,
        non_verbal_score=report.non_verbal_score,     # ← explicitly included now
        summary=report.summary,
        details=report.details,
        created_at=report.created_at
    )
