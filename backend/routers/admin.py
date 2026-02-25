"""
Admin Router — Job Posting Management
Provides CRUD endpoints for HR staff to register and list job postings.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

from database import get_db
from models import JobPosting, JobStatus

router = APIRouter(tags=["admin"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class JobPostingCreate(BaseModel):
    title: str = Field(..., description="Job title")
    description: str = Field(..., description="Full job description (JD)")
    requirements: Optional[str] = Field(None, description="Required skills / qualifications")
    min_experience: int = Field(0, ge=0, description="Minimum years of experience")
    target_capabilities: Optional[str] = Field(None, description="Target capabilities")
    conditions: Optional[str] = Field(None, description="근무조건 / 급여 / 근무시간")
    procedures: Optional[str] = Field(None, description="전형절차 / 면접방식")
    application_method: Optional[str] = Field(None, description="지원방법")
    deadline: Optional[datetime] = Field(None, description="모집 마감일시")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Python Backend Developer",
                "description": "FastAPI 기반 백엔드 개발",
                "requirements": "Python 3.8+, FastAPI, PostgreSQL",
                "min_experience": 2,
                "conditions": "재택근무 가능, 연봉 협의",
                "procedures": "서류 → 코딩테스트 → 기술면접 → 최종면접",
                "application_method": "이메일 제출 또는 채용 사이트 지원",
                "deadline": "2026-12-31T23:59:59",
            }
        }


class JobPostingResponse(BaseModel):
    id: int
    title: str
    description: str
    requirements: Optional[str]
    min_experience: int
    target_capabilities: Optional[str]
    conditions: Optional[str]
    procedures: Optional[str]
    application_method: Optional[str]
    status: str
    posted_date: date
    deadline: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/jobs", response_model=JobPostingResponse, status_code=201)
def create_job(payload: JobPostingCreate, db: Session = Depends(get_db)):
    """Create a new Job Posting with full JD details."""
    job = JobPosting(
        title=payload.title,
        description=payload.description,
        requirements=payload.requirements,
        min_experience=payload.min_experience,
        target_capabilities=payload.target_capabilities,
        conditions=payload.conditions,
        procedures=payload.procedures,
        application_method=payload.application_method,
        status=JobStatus.ACTIVE,
        deadline=payload.deadline,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=List[JobPostingResponse])
def list_jobs(db: Session = Depends(get_db)):
    """List ALL Job Postings (admin sees both ACTIVE and CLOSED)."""
    jobs = (
        db.query(JobPosting)
        .order_by(JobPosting.created_at.desc())
        .all()
    )
    return jobs


@router.get("/jobs/{job_id}", response_model=JobPostingResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Fetch a single Job Posting by ID."""
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return job


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Soft-close a Job Posting."""
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    job.status = JobStatus.CLOSED
    db.commit()


@router.patch("/jobs/{job_id}/reopen", response_model=JobPostingResponse)
def reopen_job(job_id: int, db: Session = Depends(get_db)):
    """Re-open a previously CLOSED job posting."""
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    job.status = JobStatus.ACTIVE
    db.commit()
    db.refresh(job)
    return job


@router.put("/jobs/{job_id}", response_model=JobPostingResponse)
def update_job(job_id: int, payload: JobPostingCreate, db: Session = Depends(get_db)):
    """Edit an existing job posting."""
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/copy", response_model=JobPostingResponse, status_code=201)
def copy_job(job_id: int, db: Session = Depends(get_db)):
    """Duplicate an existing job posting (creates a new DRAFT copy)."""
    original = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Job posting not found")
    copy = JobPosting(
        title=f"[사본] {original.title}",
        description=original.description,
        requirements=original.requirements,
        min_experience=original.min_experience,
        target_capabilities=original.target_capabilities,
        conditions=original.conditions,
        procedures=original.procedures,
        application_method=original.application_method,
        status=JobStatus.ACTIVE,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


@router.get("/jobs/{job_id}/applicants")
def get_job_applicants(job_id: int, db: Session = Depends(get_db)):
    """
    Return leaderboard of all candidates who completed an AI interview
    for this specific job posting, sorted by total_score descending.
    """
    from models import InterviewSession, SessionStatus, EvaluationReport, User as UserModel

    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    sessions = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.job_posting_id == job_id,
            InterviewSession.status == SessionStatus.COMPLETED,
        )
        .order_by(InterviewSession.created_at.desc())
        .all()
    )

    results = []
    for s in sessions:
        user = db.query(UserModel).filter(UserModel.id == s.user_id).first()
        report = db.query(EvaluationReport).filter(EvaluationReport.session_id == s.id).first()
        results.append({
            "session_id": s.id,
            "user_id": s.user_id,
            "candidate_name": user.name if user else "Unknown",
            "candidate_email": user.email if user else "",
            "resume_path": user.resume_path if user else None,
            "resume_text": user.resume_text if user else None,
            "interview_date": s.created_at.isoformat(),
            "total_score": report.total_score if report else None,
            "tech_score": report.tech_score if report else None,
            "communication_score": report.communication_score if report else None,
            "non_verbal_score": report.non_verbal_score if report else None,
            "has_report": report is not None,
        })

    # Sort by total_score descending (None scores go to bottom)
    results.sort(key=lambda x: (x["total_score"] is None, -(x["total_score"] or 0)))
    return results


@router.get("/analytics/categories")
def get_category_stats(db: Session = Depends(get_db)):
    """
    Return global statistics for AI generated question categories.
    Queries the QuestionBank table via JOIN for predefined questions,
    and falls back to JSON parsing for dynamic RAG questions.
    """
    from sqlalchemy import func
    from models import Transcript, QuestionBank
    import json
    
    stats = {}
    
    # 1. Join QuestionBank for predefined categories
    results = db.query(
        QuestionBank.category, 
        func.count(Transcript.id)
    ).join(
        QuestionBank, 
        Transcript.question_id == QuestionBank.id
    ).filter(
        Transcript.sender == "ai"
    ).group_by(QuestionBank.category).all()
        
    for cat, count in results:
        if cat:
            clean_cat = cat.replace('#', '').strip()
            stats[clean_cat] = stats.get(clean_cat, 0) + count
            
    # 2. Fallback for JSON content (RAG dynamic tags)
    msgs = db.query(Transcript).filter(
        Transcript.sender == "ai"
    ).all()
    for msg in msgs:
        if msg.content and "{" in msg.content:
            try:
                data = json.loads(msg.content)
                c = data.get("category") or data.get("tags")
                if c:
                    cc = str(c).replace('#', '').strip()
                    stats[cc] = stats.get(cc, 0) + 1
            except:
                pass
                
    return stats

