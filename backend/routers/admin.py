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
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=List[JobPostingResponse])
def list_jobs(db: Session = Depends(get_db)):
    """List all active Job Postings."""
    jobs = (
        db.query(JobPosting)
        .filter(JobPosting.status == JobStatus.ACTIVE)
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
    """Soft-delete (CLOSED) a Job Posting."""
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    job.status = JobStatus.CLOSED
    db.commit()
