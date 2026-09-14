from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, Enum, BigInteger, DECIMAL, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class AssignmentStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"
    media_deleted = "media_deleted"


class SubmissionStatus(str, enum.Enum):
    not_submitted = "not_submitted"
    submitted = "submitted"
    under_review = "under_review"
    reviewed = "reviewed"
    returned = "returned"
    resubmitted = "resubmitted"
    late = "late"
    approved = "approved"
    rejected = "rejected"


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="SET NULL"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    instructions = Column(Text)
    topic = Column(String(255))
    due_date = Column(DateTime)
    max_marks = Column(DECIMAL(8, 2), default=100.00)
    allowed_extensions = Column(JSON)
    max_file_size_mb = Column(Integer, default=50)
    is_published = Column(Boolean, default=False)
    status = Column(Enum(AssignmentStatus), default=AssignmentStatus.draft)
    archived_at = Column(DateTime)
    media_deleted_at = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    domain = relationship("Domain", back_populates="assignments")
    resources = relationship("AssignmentResource", back_populates="assignment", cascade="all, delete-orphan")
    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")


class AssignmentResource(Base):
    __tablename__ = "assignment_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255))
    file_path = Column(String(512), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger)
    file_mime = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    assignment = relationship("Assignment", back_populates="resources")


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    submission_number = Column(Integer, default=1)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.submitted)
    marks_obtained = Column(DECIMAL(8, 2))
    feedback = Column(Text)
    correction_request = Column(Text)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime)
    approved_at = Column(DateTime)
    rejected_at = Column(DateTime)
    returned_at = Column(DateTime)
    submitted_at = Column(DateTime, server_default=func.now())
    is_late = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", back_populates="assignment_submissions", foreign_keys=[student_id])
    files = relationship("AssignmentSubmissionFile", back_populates="submission", cascade="all, delete-orphan")


class AssignmentSubmissionFile(Base):
    __tablename__ = "assignment_submission_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("assignment_submissions.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_name = Column(String(255), nullable=False)
    original_name = Column(String(255))
    file_size = Column(BigInteger)
    file_mime = Column(String(100))
    uploaded_at = Column(DateTime, server_default=func.now())

    submission = relationship("AssignmentSubmission", back_populates="files")
