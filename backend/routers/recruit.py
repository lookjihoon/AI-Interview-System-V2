"""
Recruitment API Router
Handles job posting creation and management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

from database import get_db
from models import JobPosting, JobStatus

router = APIRouter(
    prefix="/api/recruit",
    tags=["recruitment"]
)


# Pydantic Schemas
class JobPostingCreate(BaseModel):
    """Schema for creating a new job posting"""
    title: str = Field(..., min_length=1, max_length=200, description="Job title")
    description: str = Field(..., min_length=1, description="Job description")
    requirements: str = Field(..., description="Required skills and qualifications")
    min_experience: int = Field(0, ge=0, description="Minimum years of experience required")
    target_capabilities: Optional[str] = Field(None, description="Target capabilities for evaluation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Python Backend Developer",
                "description": "We are looking for an experienced Python backend developer to join our team.",
                "requirements": "Python, FastAPI, PostgreSQL, Docker",
                "min_experience": 3,
                "target_capabilities": "API development, database design, system architecture"
            }
        }


class JobPostingResponse(BaseModel):
    """Schema for job posting response"""
    id: int
    title: str
    description: str
    requirements: str
    min_experience: int
    target_capabilities: Optional[str]
    status: str
    posted_date: date
    
    class Config:
        from_attributes = True


# API Endpoints
@router.post("/jobs", response_model=JobPostingResponse, status_code=201)
async def create_job_posting(
    job: JobPostingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new job posting
    
    - **title**: Job title
    - **description**: Detailed job description
    - **requirements**: Required skills and qualifications
    - **min_experience**: Minimum years of experience
    - **target_capabilities**: Target capabilities for AI evaluation
    """
    # Create new job posting
    new_job = JobPosting(
        title=job.title,
        description=job.description,
        requirements=job.requirements,
        min_experience=job.min_experience,
        target_capabilities=job.target_capabilities,
        status=JobStatus.ACTIVE
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    return new_job


@router.get("/jobs", response_model=List[JobPostingResponse])
async def get_job_postings(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all job postings
    
    - **status**: Filter by status (ACTIVE, CLOSED, DRAFT)
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    query = db.query(JobPosting)
    
    # Filter by status if provided
    if status:
        try:
            status_enum = JobStatus[status.upper()]
            query = query.filter(JobPosting.status == status_enum)
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in JobStatus]}"
            )
    
    # Apply pagination
    jobs = query.offset(skip).limit(limit).all()
    
    return jobs


@router.get("/jobs/{job_id}", response_model=JobPostingResponse)
async def get_job_posting(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific job posting by ID
    """
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    
    return job
