from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, Enum, BigInteger, DECIMAL
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class RecordingStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    unpublished = "unpublished"
    retention_period = "retention_period"
    archived = "archived"
    media_deleted = "media_deleted"


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    topic = Column(String(255))
    class_number = Column(Integer)
    video_path = Column(String(512))
    video_url = Column(String(512))
    video_name = Column(String(255))
    video_size = Column(BigInteger)
    video_mime = Column(String(100))
    thumbnail_path = Column(String(512))
    thumbnail_url = Column(String(512))
    thumbnail_name = Column(String(255))
    duration_seconds = Column(Integer)
    status = Column(Enum(RecordingStatus), default=RecordingStatus.draft, nullable=False)
    is_published = Column(Boolean, default=False)
    publish_date = Column(DateTime)
    media_deleted_at = Column(DateTime)
    archived_at = Column(DateTime)
    cleanup_log = Column(Text)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    related_quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="SET NULL"))
    related_assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    domain = relationship("Domain", back_populates="recordings")
    resources = relationship("RecordingResource", back_populates="recording", cascade="all, delete-orphan")
    video_progress = relationship("VideoProgress", back_populates="recording", cascade="all, delete-orphan")


class RecordingResource(Base):
    __tablename__ = "recording_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger)
    file_mime = Column(String(100))
    is_downloadable = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    recording = relationship("Recording", back_populates="resources")


class VideoProgress(Base):
    __tablename__ = "video_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False)
    watched_seconds = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    percentage_watched = Column(DECIMAL(5, 2), default=0.00)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    last_watched_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    student = relationship("User", back_populates="video_progress")
    recording = relationship("Recording", back_populates="video_progress")
