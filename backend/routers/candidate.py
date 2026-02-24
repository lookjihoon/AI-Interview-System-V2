"""
Candidate API Router
Handles user registration and resume management
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from database import get_db
from models import User, UserRole

router = APIRouter(
    prefix="/api/candidate",
    tags=["candidate"]
)


# Pydantic Schemas
class UserCreate(BaseModel):
    """Schema for creating a new user"""
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    role: str = Field("CANDIDATE", description="User role (ADMIN, INTERVIEWER, CANDIDATE)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Kim Developer",
                "email": "kim.dev@example.com",
                "role": "CANDIDATE"
            }
        }


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    name: str
    email: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ResumeUpload(BaseModel):
    """Schema for uploading a resume"""
    user_id: int = Field(..., description="User ID who owns this resume")
    content: str = Field(..., min_length=10, description="Resume content in text format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "content": "Kim Developer\n\nExperience:\n- 5 years Python development\n- FastAPI, Django\n- PostgreSQL, Redis\n\nEducation:\n- BS Computer Science"
            }
        }


class ResumeResponse(BaseModel):
    """Schema for resume response"""
    id: int
    user_id: int
    content: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


# API Endpoints
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user (simple registration)
    
    - **name**: User's full name
    - **email**: User's email address (must be unique)
    - **role**: User role (ADMIN, INTERVIEWER, CANDIDATE)
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Validate role
    try:
        role_enum = UserRole[user.role.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}"
        )
    
    # Create new user
    new_user = User(
        name=user.name,
        email=user.email,
        role=role_enum
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get user information by ID
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.post("/resumes", response_model=UserResponse, status_code=200)
async def upload_resume(
    resume: ResumeUpload,
    db: Session = Depends(get_db)
):
    """
    Upload a resume for a user
    
    - **user_id**: ID of the user who owns this resume
    - **content**: Resume content in text format
    """
    # Verify user exists
    user = db.query(User).filter(User.id == resume.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user's resume_text field
    user.resume_text = resume.content
    db.commit()
    db.refresh(user)
    
    return user


@router.get("/users/{user_id}/resume")
async def get_user_resume(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get resume for a specific user
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.resume_text:
        raise HTTPException(status_code=404, detail="Resume not found for this user")
    
    return {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "resume_text": user.resume_text,
        "resume_path": getattr(user, "resume_path", None),
        "uploaded_at": user.created_at
    }


@router.get("/users/{user_id}/interviews")
async def get_user_interviews(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all completed interview sessions for a user, with evaluation scores.
    Used by MyPage interview history section.
    """
    from models import InterviewSession, SessionStatus, EvaluationReport, JobPosting

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sessions = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.user_id == user_id,
            InterviewSession.status == SessionStatus.COMPLETED
        )
        .order_by(InterviewSession.created_at.desc())
        .all()
    )

    result = []
    for s in sessions:
        job = db.query(JobPosting).filter(JobPosting.id == s.job_posting_id).first()
        report = db.query(EvaluationReport).filter(EvaluationReport.session_id == s.id).first()
        result.append({
            "session_id": s.id,
            "job_title": job.title if job else "(공고 삭제됨)",
            "job_id": s.job_posting_id,
            "date": s.created_at.isoformat(),
            "total_score": report.total_score if report else None,
            "tech_score": report.tech_score if report else None,
            "communication_score": report.communication_score if report else None,
            "non_verbal_score": report.non_verbal_score if report else None,
            "status": s.status.value,
        })
    return result


@router.post("/resume/parse")
async def parse_resume_pdf(file: UploadFile = File(...)):
    """
    Parse a PDF resume and return extracted text (temp file, no DB save).
    Frontend populates textarea; user edits then saves separately.
    """
    import uuid, shutil
    from pathlib import Path
    from routers.interview import parse_pdf

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")

    tmp_dir = Path("uploads/tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{uuid.uuid4().hex}_{file.filename}"
    try:
        with tmp_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        text = parse_pdf(str(tmp_path))
    finally:
        await file.close()
        try: tmp_path.unlink()
        except Exception: pass

    if not text:
        raise HTTPException(status_code=422, detail="PDF에서 텍스트를 추출하지 못했습니다. 스캔본 PDF는 지원되지 않습니다.")

    return {"text": text}


@router.post("/resume/upload")
async def upload_resume_pdf(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload PDF resume: saves file to disk, extracts text, stores both in DB.
    Returns resume_path (relative URL) so frontend can show a preview link.
    """
    import uuid, shutil
    from pathlib import Path
    from routers.interview import parse_pdf

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")

    # Save PDF to a permanent location
    save_dir = Path(f"uploads/resumes/{user_id}")
    save_dir.mkdir(parents=True, exist_ok=True)
    # Use a fixed filename per user (overwrites previous) so they have one resume
    safe_name = f"resume_{uuid.uuid4().hex[:8]}.pdf"
    save_path = save_dir / safe_name

    try:
        with save_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        text = parse_pdf(str(save_path))
    finally:
        await file.close()

    if not text:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="PDF에서 텍스트를 추출하지 못했습니다.")

    # Remove previous PDF if any
    old_path = getattr(user, "resume_path", None)
    if old_path:
        old_file = Path(old_path.lstrip("/").replace("static/resumes", f"uploads/resumes/{user_id}"))
        if old_file.exists() and old_file != save_path:
            try: old_file.unlink()
            except Exception: pass

    # Persist to DB
    url_path = f"/static/resumes/{user_id}/{safe_name}"
    user.resume_text = text
    user.resume_path = url_path
    db.commit()
    db.refresh(user)

    return {
        "text": text,
        "resume_path": url_path,
        "filename": file.filename,
    }
