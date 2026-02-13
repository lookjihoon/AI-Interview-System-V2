"""
Candidate API Router
Handles user registration and resume management
"""
from fastapi import APIRouter, Depends, HTTPException
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
        "uploaded_at": user.created_at
    }
