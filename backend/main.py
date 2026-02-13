from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import torch

from database import engine, get_db, Base
from models import User, JobPosting, InterviewSession, Transcript, EvaluationReport, QuestionBank

# Import routers
from routers import recruit, candidate, interview

app = FastAPI(
    title="AI Interview System API",
    description="Backend API for AI-powered mock interview system",
    version="2.0.0"
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Create pgvector extension and database tables on startup"""
    print("Creating pgvector extension...")
    try:
        # Create pgvector extension if it doesn't exist
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        print("pgvector extension created successfully!")
    except Exception as e:
        print(f"Warning: Could not create pgvector extension: {e}")
    
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "AI Interview System API v2.0"}


@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with GPU and database status"""
    db_status = "connected"
    try:
        # Test database connection by executing a simple query
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "db": db_status,
        "gpu": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    }


@app.post("/api/system/init-data")
async def initialize_seed_data():
    """
    Initialize seed data for the system
    Creates admin user, sample candidate, job posting, and resume
    """
    from seed_data import init_seed_data
    
    try:
        result = init_seed_data()
        return {
            "message": "Seed data initialized successfully",
            "data": result
        }
    except Exception as e:
        return {
            "message": "Seed data initialization failed",
            "error": str(e)
        }


# Include routers
app.include_router(recruit.router)
app.include_router(candidate.router)
app.include_router(interview.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

