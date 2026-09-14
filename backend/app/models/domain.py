from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class DomainAccessStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    expired = "expired"
    revoked = "revoked"


class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    image_path = Column(String(512))
    image_url = Column(String(512))
    image_name = Column(String(255))
    duration_weeks = Column(Integer)
    is_active = Column(Boolean, default=True)
    max_active_recordings = Column(Integer, default=45)
    recording_retention_days = Column(Integer, default=15)
    assignment_retention_days = Column(Integer, default=45)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    student_domains = relationship("StudentDomain", back_populates="domain", cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="domain", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="domain", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="domain", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="domain", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="domain", cascade="all, delete-orphan")


class StudentDomain(Base):
    __tablename__ = "student_domains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(DomainAccessStatus), default=DomainAccessStatus.active, nullable=False)
    access_expires_at = Column(DateTime)
    granted_at = Column(DateTime, server_default=func.now())
    granted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    revoked_at = Column(DateTime)
    revoked_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    revocation_reason = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    student = relationship("User", back_populates="student_domains", foreign_keys=[student_id])
    domain = relationship("Domain", back_populates="student_domains")
