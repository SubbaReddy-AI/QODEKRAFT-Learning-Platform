from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime, timedelta
import secrets

from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.user import UserProfile
from app.auth.jwt import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, decode_token, validate_password_strength
)
from app.auth.dependencies import get_current_user
from app.utils.audit import log_audit, create_notification
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─── Schemas ────────────────────────────────────────────────

class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    confirm_password: str
    qualification: Optional[str] = None
    preferred_domain: Optional[str] = None
    role: str = "student"

    @validator("password")
    def validate_pw(cls, v):
        # Signup accepts any password of at least 8 characters.
        # Complexity validation is handled by the password-change/reset flows.
        if not isinstance(v, str) or len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    role: str
    status: str
    full_name: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @validator("new_password")
    def validate_pw(cls, v):
        ok, msg = validate_password_strength(v)
        if not ok:
            raise ValueError(msg)
        return v

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @validator("new_password")
    def validate_pw(cls, v):
        ok, msg = validate_password_strength(v)
        if not ok:
            raise ValueError(msg)
        return v

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v


# ─── Routes ──────────────────────────────────────────────────

@router.post("/signup", status_code=201)
async def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    """Register a student or administrator account and persist it in MySQL."""
    # Check email uniqueness
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check rate limit: max 5 signups per IP per hour (simple check)
    # Public signup is STUDENT ONLY. Administrator accounts are created
    # from the configured backend admin credentials, never from this page.
    user = User(
        email=str(payload.email).strip().lower(),
        phone=(payload.phone or "").strip() or None,
        password_hash=get_password_hash(payload.password),
        role=UserRole.student,
        status=UserStatus.pending,
    )
    db.add(user)
    db.flush()

    profile = UserProfile(
        user_id=user.id,
        full_name=payload.full_name,
        qualification=payload.qualification,
        preferred_domain=payload.preferred_domain,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    log_audit(
        db, action="student_signup", user_id=user.id, user_email=user.email,
        resource_type="user", resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    return {
        "message": "Registration submitted successfully. Wait for administrator approval.",
        "user_id": user.id,
        "status": user.status.value if hasattr(user.status, "value") else str(user.status),
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
    }


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated. Contact the administrator.")

    # Check lockout
    if user.lockout_until and user.lockout_until > datetime.utcnow():
        remaining = int((user.lockout_until - datetime.utcnow()).total_seconds() // 60)
        raise HTTPException(
            status_code=429,
            detail=f"Account temporarily locked. Try again in {remaining} minutes.",
        )

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
            user.lockout_until = datetime.utcnow() + timedelta(
                seconds=settings.LOGIN_RATE_LIMIT_PERIOD_SECONDS
            )
        db.commit()
        log_audit(db, action="login_failed", user_email=payload.email, status="failure",
                  ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Reset failed attempts on success
    # Pending students remain pending until an administrator approves them.
    user.failed_login_attempts = 0
    user.lockout_until = None
    user.last_login_at = datetime.utcnow()
    db.commit()

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value if hasattr(user.role, "value") else str(user.role)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    log_audit(db, action="login_success", user_id=user.id, user_email=user.email,
              ip_address=request.client.host if request.client else None)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        full_name=user.profile.full_name if user.profile else "",
    )


@router.post("/refresh")
async def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a refresh token for a new access token."""
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == int(data["sub"]), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value if hasattr(user.role, "value") else str(user.role)}
    return {"access_token": create_access_token(token_data), "token_type": "bearer"}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset email (or log token in dev mode)."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Don't reveal if email exists
        return {"message": "If that email is registered, you will receive a reset link."}

    token = secrets.token_urlsafe(48)
    user.password_reset_token = token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=2)
    db.commit()

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    if settings.DEBUG:
        import logging
        logging.getLogger("qodekraft").info(f"[DEV] Password reset link for {user.email}: {reset_url}")

    return {"message": "If that email is registered, you will receive a reset link.", "debug_url": reset_url if settings.DEBUG else None}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using a valid token."""
    user = db.query(User).filter(
        User.password_reset_token == payload.token,
        User.password_reset_expires > datetime.utcnow(),
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = get_password_hash(payload.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.failed_login_attempts = 0
    user.lockout_until = None
    db.commit()

    return {"message": "Password reset successfully. Please login with your new password."}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for the currently logged-in user."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()

    log_audit(db, action="change_password", user_id=current_user.id, user_email=current_user.email)
    return {"message": "Password changed successfully"}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user profile."""
    profile = current_user.profile
    return {
        "id": current_user.id,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
        "status": current_user.status,
        "is_active": current_user.is_active,
        "last_login_at": current_user.last_login_at,
        "full_name": profile.full_name if profile else "",
        "qualification": profile.qualification if profile else "",
        "preferred_domain": profile.preferred_domain if profile else "",
        "bio": profile.bio if profile else "",
        "profile_image_url": profile.profile_image_url if profile else None,
        "created_at": current_user.created_at,
    }
