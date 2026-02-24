"""
Auth Router — Sign-up and Login
Simple password-based authentication using bcrypt hashing.
No JWT tokens; session info is returned directly and stored client-side in localStorage.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date

from database import get_db
from models import User, UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        # Fallback: plain SHA-256 (install bcrypt for production)
        import hashlib
        return "sha256:" + hashlib.sha256(password.encode()).hexdigest()


def _verify(password: str, password_hash: str) -> bool:
    try:
        import bcrypt
        if password_hash.startswith("sha256:"):
            raise ValueError("sha256")
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ImportError, ValueError):
        import hashlib
        expected = "sha256:" + hashlib.sha256(password.encode()).hexdigest()
        return password_hash == expected


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4, description="비밀번호 (영문+숫자 권장)")
    name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    address: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "hong@example.com",
                "password": "hong1234",
                "name": "홍길동",
                "phone": "010-1234-5678",
                "birth_date": "1995-03-22",
                "address": "서울특별시 강남구",
            }
        }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    address: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new CANDIDATE account.
    Email must be unique. Password is bcrypt-hashed before storage.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다.")

    # Alphanumeric password validation (soft — allow special chars too)
    if not any(c.isalpha() for c in payload.password) or not any(c.isdigit() for c in payload.password):
        raise HTTPException(
            status_code=422,
            detail="비밀번호는 영문자와 숫자를 모두 포함해야 합니다."
        )

    user = User(
        email=payload.email,
        password_hash=_hash(payload.password),
        name=payload.name,
        phone=payload.phone,
        birth_date=payload.birth_date,
        address=getattr(payload, "address", None),
        role=UserRole.CANDIDATE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email + password.
    Returns user object (role included) so the frontend can redirect accordingly.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    if not _verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    return _to_response(user)


def _to_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "phone": user.phone,
        "birth_date": user.birth_date,
        "address": getattr(user, "address", None),
    }
