from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, Enum, JSON, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class AnnouncementType(str, enum.Enum):
    general = "general"
    assignment = "assignment"
    quiz = "quiz"
    project = "project"
    recording = "recording"
    important = "important"

class NotificationType(str, enum.Enum):
    approval = "approval"
    rejection = "rejection"
    domain_access = "domain_access"
    recording = "recording"
    assignment = "assignment"
    quiz = "quiz"
    project = "project"
    announcement = "announcement"
    system = "system"

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="CASCADE"))
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(Enum(AnnouncementType), default=AnnouncementType.general)
    is_global = Column(Boolean, default=False)
    is_published = Column(Boolean, default=True)
    published_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    domain = relationship("Domain", back_populates="announcements")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(Enum(NotificationType), default=NotificationType.system)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    related_entity_type = Column(String(50))
    related_entity_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="notifications")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    user_email = Column(String(255))
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    status = Column(Enum("success", "failure", "warning"), default="success")
    created_at = Column(DateTime, server_default=func.now())

class StorageCleanupLog(Base):
    __tablename__ = "storage_cleanup_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(Enum("scheduled", "manual"), default="scheduled")
    triggered_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    status = Column(Enum("running", "completed", "failed", "partial"), default="running")
    recordings_processed = Column(Integer, default=0)
    recordings_deleted = Column(Integer, default=0)
    assignments_processed = Column(Integer, default=0)
    assignments_deleted = Column(Integer, default=0)
    total_bytes_freed = Column(BigInteger, default=0)
    errors = Column(JSON)
    notes = Column(Text)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text)
    setting_type = Column(Enum("string", "integer", "boolean", "json"), default="string")
    description = Column(Text)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())
