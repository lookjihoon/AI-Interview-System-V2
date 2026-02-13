from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from database import Base
import enum


# Enums for type safety
class UserRole(str, enum.Enum):
    CANDIDATE = "CANDIDATE"
    ADMIN = "ADMIN"


class JobStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    DRAFT = "DRAFT"


class SessionStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"


class User(Base):
    """
    User model for both candidates and administrators.
    Supports authentication and role-based access control.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Made nullable for simple registration
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    birth_date = Column(Date, nullable=True)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CANDIDATE)
    resume_text = Column(Text, nullable=True)  # Resume content in text format
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    interview_sessions = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role={self.role})>"


class JobPosting(Base):
    """
    Job posting model for managing recruitment positions.
    Contains job description and required keywords for RAG matching.
    """
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)  # Job Description (JD)
    requirements = Column(Text, nullable=True)  # Required skills and qualifications
    min_experience = Column(Integer, nullable=False, default=0)  # Minimum years of experience
    target_capabilities = Column(Text, nullable=True)  # Target capabilities for evaluation
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.ACTIVE, index=True)
    posted_date = Column(Date, server_default=func.current_date(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    interview_sessions = relationship("InterviewSession", back_populates="job_posting", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<JobPosting(id={self.id}, title='{self.title}', status={self.status})>"


class InterviewSession(Base):
    """
    Interview session model linking users to job postings.
    Tracks the progress of each interview attempt.
    """
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_path = Column(String(500), nullable=True)  # Path to uploaded resume file
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.IN_PROGRESS, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="interview_sessions")
    job_posting = relationship("JobPosting", back_populates="interview_sessions")
    transcripts = relationship("Transcript", back_populates="session", cascade="all, delete-orphan")
    evaluation_report = relationship("EvaluationReport", back_populates="session", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<InterviewSession(id={self.id}, user_id={self.user_id}, status={self.status})>"


class Transcript(Base):
    """
    Transcript model for storing interview conversation history.
    Records both AI questions and user answers.
    """
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(50), nullable=False)  # 'ai' or 'human'
    content = Column(Text, nullable=False)
    question_id = Column(Integer, ForeignKey("question_bank.id"), nullable=True)  # Track which question was asked
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("InterviewSession", back_populates="transcripts")

    def __repr__(self):
        return f"<Transcript(id={self.id}, session_id={self.session_id}, sender='{self.sender}')>"


class EvaluationReport(Base):
    """
    Evaluation report model for storing interview assessment results.
    Contains multi-dimensional scoring and detailed feedback in JSONB format.
    """
    __tablename__ = "evaluation_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    total_score = Column(Integer, nullable=False)  # 0-100
    tech_score = Column(Integer, nullable=True)  # Technical competency
    communication_score = Column(Integer, nullable=True)  # Communication skills
    problem_solving_score = Column(Integer, nullable=True)  # Problem-solving ability
    non_verbal_score = Column(Integer, nullable=True)  # Non-verbal behavior (Vision analysis)
    summary = Column(Text, nullable=True)  # AI-generated summary
    details = Column(JSON, nullable=True)  # JSONB: Detailed rubric matching results
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("InterviewSession", back_populates="evaluation_report")

    def __repr__(self):
        return f"<EvaluationReport(id={self.id}, session_id={self.session_id}, total_score={self.total_score})>"


class QuestionBank(Base):
    """
    Question bank model for storing 6,000+ interview questions.
    Supports RAG (Retrieval-Augmented Generation) with embedding vectors.
    """
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category = Column(String(100), nullable=False, index=True)  # BASIC, INDUSTRY, COMPANY
    sub_category = Column(String(100), nullable=True, index=True)  # 인성, 기술, CS, etc.
    question_text = Column(Text, nullable=False)
    model_answer = Column(Text, nullable=True)  # Reference answer for evaluation
    embedding = Column(Vector(768), nullable=True)  # 768-dim vector for sentence-transformers/all-mpnet-base-v2

    def __repr__(self):
        return f"<QuestionBank(id={self.id}, category='{self.category}', sub_category='{self.sub_category}')>"
