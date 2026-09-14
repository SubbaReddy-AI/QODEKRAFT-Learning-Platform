from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.audit import AuditLog, StorageCleanupLog, SystemSetting
from app.auth.dependencies import get_current_admin
from app.models.user import User
from app.utils.audit import log_audit

router = APIRouter(prefix="/admin/settings", tags=["Admin - Settings"])


SETTING_KEYS = [
    "max_active_recordings",
    "recording_retention_days",
    "assignment_retention_days",
    "assignment_extra_retention_days",
    "auto_cleanup_enabled",
    "archive_before_deletion",
    "permanent_deletion_enabled",
    "max_upload_size_mb",
    "allowed_video_types",
    "allowed_document_types",
    "allowed_code_types",
    "student_approval_required",
    "domain_access_expiry_enabled",
]


@router.get("")
async def get_settings(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings = db.query(SystemSetting).all()
    return {s.setting_key: {"value": s.setting_value, "type": s.setting_type, "description": s.description} for s in settings}


@router.patch("")
async def update_settings(
    updates: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    for key, value in updates.items():
        setting = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
        if setting:
            setting.setting_value = str(value)
            setting.updated_by = admin.id

    db.commit()
    log_audit(db, "update_settings", admin.id, admin.email, details={"keys": list(updates.keys())})
    return {"message": "Settings updated successfully"}


# ─── Audit Logs ──────────────────────────────────────────────

audit_router = APIRouter(prefix="/admin/audit-logs", tags=["Admin - Audit Logs"])


@audit_router.get("")
async def get_audit_logs(
    search: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if search:
        from sqlalchemy import or_
        query = query.filter(
            or_(AuditLog.action.ilike(f"%{search}%"), AuditLog.user_email.ilike(f"%{search}%"))
        )
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "logs": [
            {
                "id": l.id, "user_id": l.user_id, "user_email": l.user_email,
                "action": l.action, "resource_type": l.resource_type,
                "resource_id": l.resource_id, "status": l.status,
                "ip_address": l.ip_address, "created_at": l.created_at,
            }
            for l in logs
        ],
    }


# ─── Cleanup ─────────────────────────────────────────────────

cleanup_router = APIRouter(prefix="/admin/cleanup", tags=["Admin - Storage Cleanup"])


@cleanup_router.get("/logs")
async def get_cleanup_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    total = db.query(StorageCleanupLog).count()
    logs = db.query(StorageCleanupLog).order_by(StorageCleanupLog.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {
        "total": total,
        "logs": [
            {
                "id": l.id, "job_type": l.job_type, "status": l.status,
                "recordings_processed": l.recordings_processed,
                "recordings_deleted": l.recordings_deleted,
                "assignments_processed": l.assignments_processed,
                "assignments_deleted": l.assignments_deleted,
                "total_bytes_freed": l.total_bytes_freed,
                "started_at": l.started_at, "completed_at": l.completed_at,
            }
            for l in logs
        ],
    }


@cleanup_router.post("/run")
async def run_manual_cleanup(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Trigger a manual cleanup job (requires admin confirmation)."""
    from app.tasks.cleanup import run_cleanup
    result = run_cleanup(db=db, triggered_by=admin.id, job_type="manual")
    log_audit(db, "manual_cleanup_triggered", admin.id, admin.email, details=result)
    return result


# ─── Dashboard Stats ─────────────────────────────────────────

dashboard_router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])


@dashboard_router.get("/stats")
async def get_dashboard_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from app.models.user import User as UserModel, UserRole, UserStatus
    from app.models.domain import Domain
    from app.models.recording import Recording
    from app.models.assignment import Assignment, AssignmentSubmission
    from app.models.quiz import Quiz, QuizAttempt
    from app.models.project import Project, ProjectSubmission

    total_students = db.query(UserModel).filter(UserModel.role == UserRole.student).count()
    pending = db.query(UserModel).filter(UserModel.role == UserRole.student, UserModel.status == UserStatus.pending).count()
    approved = db.query(UserModel).filter(UserModel.role == UserRole.student, UserModel.status == UserStatus.approved).count()
    blocked = db.query(UserModel).filter(UserModel.role == UserRole.student, UserModel.status == UserStatus.blocked).count()
    total_domains = db.query(Domain).count()
    active_domains = db.query(Domain).filter(Domain.is_active == True).count()
    total_recordings = db.query(Recording).count()
    total_assignments = db.query(Assignment).count()
    total_projects = db.query(Project).count()
    total_quizzes = db.query(Quiz).count()
    recent_submissions = db.query(AssignmentSubmission).order_by(AssignmentSubmission.submitted_at.desc()).limit(5).all()
    recent_students = db.query(UserModel).filter(UserModel.role == UserRole.student).order_by(UserModel.created_at.desc()).limit(5).all()

    return {
        "students": {
            "total": total_students,
            "pending": pending,
            "approved": approved,
            "blocked": blocked,
        },
        "domains": {"total": total_domains, "active": active_domains},
        "content": {
            "recordings": total_recordings,
            "assignments": total_assignments,
            "projects": total_projects,
            "quizzes": total_quizzes,
        },
        "recent_submissions": [
            {"id": s.id, "student_id": s.student_id, "assignment_id": s.assignment_id,
             "status": s.status, "submitted_at": s.submitted_at}
            for s in recent_submissions
        ],
        "recent_registrations": [
            {"id": u.id, "email": u.email, "status": u.status, "created_at": u.created_at,
             "full_name": u.profile.full_name if u.profile else ""}
            for u in recent_students
        ],
    }
