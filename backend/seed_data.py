"""
Seed Data Script for Initial System Setup
Creates admin user, sample candidate, job posting, and resume
"""
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import User, JobPosting, UserRole, JobStatus


def init_seed_data():
    """Initialize seed data for the system"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("Initializing Seed Data")
        print("=" * 80)
        
        # 1. Create Admin User
        print("\n1. Creating Admin User...")
        admin = db.query(User).filter(User.email == "admin@interview.com").first()
        if not admin:
            admin = User(
                name="System Admin",
                email="admin@interview.com",
                role=UserRole.ADMIN,
                password_hash=None  # Simple registration without password
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"   [OK] Created Admin: {admin.name} ({admin.email})")
        else:
            print(f"   [SKIP] Admin already exists: {admin.name}")
        
        # 2. Create Sample Candidate
        print("\n2. Creating Sample Candidate (KimDev)...")
        kimdev = db.query(User).filter(User.email == "kim.dev@example.com").first()
        if not kimdev:
            kimdev = User(
                name="Kim Developer",
                email="kim.dev@example.com",
                role=UserRole.CANDIDATE,
                password_hash=None
            )
            db.add(kimdev)
            db.commit()
            db.refresh(kimdev)
            print(f"   [OK] Created Candidate: {kimdev.name} ({kimdev.email})")
        else:
            print(f"   [SKIP] Candidate already exists: {kimdev.name}")
        
        # 3. Create Sample Job Posting
        print("\n3. Creating Sample Job Posting (Python Backend Developer)...")
        job = db.query(JobPosting).filter(JobPosting.title == "Python Backend Developer").first()
        if not job:
            job = JobPosting(
                title="Python Backend Developer",
                description="""
We are looking for an experienced Python Backend Developer to join our growing team.

Responsibilities:
- Design and develop RESTful APIs using FastAPI
- Build scalable backend systems with PostgreSQL
- Implement AI/ML features for our products
- Collaborate with frontend developers and product team
- Write clean, maintainable, and well-documented code

Work Environment:
- Remote-friendly with flexible hours
- Modern tech stack (Python, FastAPI, PostgreSQL, Docker, Kubernetes)
- Collaborative and innovative team culture
                """.strip(),
                requirements="""
Required Skills:
- 3+ years of Python development experience
- Strong knowledge of FastAPI or Django
- Experience with PostgreSQL and database design
- Understanding of RESTful API design principles
- Git version control proficiency

Preferred Skills:
- Experience with AI/ML frameworks (PyTorch, TensorFlow)
- Knowledge of Docker and Kubernetes
- Experience with Redis and caching strategies
- Understanding of microservices architecture
- Familiarity with cloud platforms (AWS, GCP, Azure)
                """.strip(),
                min_experience=3,
                target_capabilities="""
Technical Competency:
- Python programming and best practices
- API design and development
- Database design and optimization
- System architecture and scalability

Problem Solving:
- Debugging and troubleshooting skills
- Algorithm and data structure knowledge
- Performance optimization
- Security best practices

Communication:
- Clear technical communication
- Collaboration with cross-functional teams
- Code review and documentation
                """.strip(),
                status=JobStatus.ACTIVE
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            print(f"   [OK] Created Job Posting: {job.title} (ID: {job.id})")
        else:
            print(f"   [SKIP] Job Posting already exists: {job.title}")
        
        # 4. Upload Sample Resume for KimDev
        print("\n4. Uploading Sample Resume for KimDev...")
        if not kimdev.resume_text:
            kimdev.resume_text = """
Kim Developer
Email: kim.dev@example.com
Phone: +82-10-1234-5678

PROFESSIONAL SUMMARY
Experienced Python Backend Developer with 5+ years of expertise in building scalable web applications
and RESTful APIs. Proficient in FastAPI, Django, PostgreSQL, and modern DevOps practices.
Strong background in AI/ML integration and microservices architecture.

WORK EXPERIENCE

Senior Backend Developer | TechCorp Inc. | 2021 - Present
- Designed and implemented RESTful APIs using FastAPI serving 1M+ daily requests
- Optimized database queries reducing response time by 60%
- Integrated AI/ML models for recommendation system using PyTorch
- Implemented Redis caching strategy improving performance by 40%
- Led migration from monolithic to microservices architecture

Backend Developer | StartupXYZ | 2019 - 2021
- Developed Django-based e-commerce platform handling 100K+ transactions/month
- Built real-time notification system using WebSockets
- Implemented CI/CD pipeline with Docker and GitHub Actions
- Collaborated with frontend team to design and implement RESTful APIs

TECHNICAL SKILLS
Languages: Python, SQL, JavaScript
Frameworks: FastAPI, Django, Flask
Databases: PostgreSQL, MySQL, Redis, MongoDB
AI/ML: PyTorch, TensorFlow, scikit-learn, LangChain
DevOps: Docker, Kubernetes, AWS, GitHub Actions
Tools: Git, Linux, Nginx, Celery

EDUCATION
Bachelor of Science in Computer Science
Seoul National University | 2015 - 2019
GPA: 3.8/4.0

PROJECTS
AI-Powered Interview System
- Built FastAPI backend with PostgreSQL and pgvector for semantic search
- Integrated LangChain for RAG-based question generation
- Implemented real-time emotion analysis using DeepFace

E-commerce Recommendation Engine
- Developed collaborative filtering system using PyTorch
- Achieved 25% increase in conversion rate
- Processed 10M+ user interactions daily

CERTIFICATIONS
- AWS Certified Solutions Architect - Associate
- Google Cloud Professional Data Engineer
            """.strip()
            db.commit()
            db.refresh(kimdev)
            print(f"   [OK] Uploaded resume for {kimdev.name}")
        else:
            print(f"   [SKIP] Resume already exists for {kimdev.name}")
        
        print("\n" + "=" * 80)
        print("Seed Data Initialization Complete!")
        print("=" * 80)
        print(f"\nCreated/Verified:")
        print(f"  - Admin: {admin.name} ({admin.email})")
        print(f"  - Candidate: {kimdev.name} ({kimdev.email})")
        print(f"  - Job Posting: {job.title} (ID: {job.id})")
        print(f"  - Resume: {'✓' if kimdev.resume_text else '✗'}")
        
        return {
            "success": True,
            "admin": {"id": admin.id, "name": admin.name, "email": admin.email},
            "candidate": {"id": kimdev.id, "name": kimdev.name, "email": kimdev.email},
            "job_posting": {"id": job.id, "title": job.title},
            "resume_uploaded": bool(kimdev.resume_text)
        }
        
    except Exception as e:
        print(f"\n[ERROR] Seed data initialization failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_seed_data()
