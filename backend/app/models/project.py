from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, Enum, BigInteger, DECIMAL, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class ProjectSubmissionStatus(str, enum.Enum):
    submitted = "submitted"
    under_review = "under_review"
    reviewed = "reviewed"
    returned = "returned"
    resubmitted = "resubmitted"
    approved = "approved"
    rejected = "rejected"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    requirements = Column(Text)
    technologies = Column(JSON)
    due_date = Column(DateTime)
    max_marks = Column(DECIMAL(8, 2), default=100.00)
    submission_instructions = Column(Text)
    is_published = Column(Boolean, default=False)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.draft)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    domain = relationship("Domain", back_populates="projects")
    reference_files = relationship("ProjectReferenceFile", back_populates="project", cascade="all, delete-orphan")
    submissions = relationship("ProjectSubmission", back_populates="project", cascade="all, delete-orphan")


class ProjectReferenceFile(Base):
    __tablename__ = "project_reference_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255))
    file_path = Column(String(512), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger)
    file_mime = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="reference_files")


class ProjectSubmission(Base):
    __tablename__ = "project_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    submission_number = Column(Integer, default=1)
    description = Column(Text)
    github_link = Column(String(512))
    live_demo_link = Column(String(512))
    status = Column(Enum(ProjectSubmissionStatus), default=ProjectSubmissionStatus.submitted)
    marks_obtained = Column(DECIMAL(8, 2))
    feedback = Column(Text)
    correction_request = Column(Text)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime)
    approved_at = Column(DateTime)
    rejected_at = Column(DateTime)
    submitted_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="submissions")
    student = relationship("User", back_populates="project_submissions", foreign_keys=[student_id])
    files = relationship("ProjectSubmissionFile", back_populates="submission", cascade="all, delete-orphan")


class ProjectSubmissionFile(Base):
    __tablename__ = "project_submission_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("project_submissions.id", ondelete="CASCADE"), nullable=False)
    file_type = Column(Enum("zip", "pdf", "docx", "image", "other"), default="other")
    file_path = Column(String(512), nullable=False)
    file_name = Column(String(255), nullable=False)
    original_name = Column(String(255))
    file_size = Column(BigInteger)
    file_mime = Column(String(100))
    uploaded_at = Column(DateTime, server_default=func.now())

    submission = relationship("ProjectSubmission", back_populates="files")
