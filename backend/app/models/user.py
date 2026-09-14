from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    Enum, ForeignKey, DECIMAL, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    student = "student"


class UserStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    blocked = "blocked"
    suspended = "suspended"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.student)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.pending)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime)
    password_reset_token = Column(String(255))
    password_reset_expires = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    lockout_until = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    profile = relationship("UserProfile", back_populates="user", foreign_keys="UserProfile.user_id", uselist=False, cascade="all, delete-orphan")
    student_domains = relationship("StudentDomain", back_populates="student", foreign_keys="StudentDomain.student_id", cascade="all, delete-orphan")
    video_progress = relationship("VideoProgress", back_populates="student", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="student", cascade="all, delete-orphan")
    assignment_submissions = relationship("AssignmentSubmission", back_populates="student", foreign_keys="AssignmentSubmission.student_id", cascade="all, delete-orphan")
    project_submissions = relationship("ProjectSubmission", back_populates="student", foreign_keys="ProjectSubmission.student_id", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    qualification = Column(String(255))
    preferred_domain = Column(String(255))
    bio = Column(Text)
    profile_image_path = Column(String(512))
    profile_image_url = Column(String(512))
    profile_image_name = Column(String(255))
    profile_image_size = Column(BigInteger)
    profile_image_mime = Column(String(100))
    rejection_reason = Column(Text)
    suspension_reason = Column(Text)
    approved_at = Column(DateTime)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    rejected_at = Column(DateTime)
    rejected_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    suspended_at = Column(DateTime)
    suspended_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile", foreign_keys=[user_id])
