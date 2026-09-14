from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.auth.dependencies import get_current_approved_student, verify_student_domain_access
from app.models.user import User
from app.models.domain import StudentDomain, DomainAccessStatus, Domain
from app.models.recording import VideoProgress, Recording
from app.models.quiz import QuizAttempt
from app.models.assignment import AssignmentSubmission
from app.models.project import ProjectSubmission

router = APIRouter(prefix="/student/progress", tags=["Student - Progress"])


@router.get("")
async def get_overall_progress(
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    """Get overall progress summary across all assigned domains."""
    active_domains = (
        db.query(StudentDomain)
        .filter(
            StudentDomain.student_id == student.id,
            StudentDomain.status == DomainAccessStatus.active,
        )
        .all()
    )

    result = []
    totals_done = 0
    totals_available = 0
    for sd in active_domains:
        domain = db.query(Domain).filter(Domain.id == sd.domain_id).first()
        if not domain:
            continue

        domain_progress = _get_domain_progress(student.id, sd.domain_id, db)
        result.append({
            "domain_id": domain.id,
            "domain_name": domain.name,
            "access_expires_at": sd.access_expires_at,
            **domain_progress,
        })
        for key in ("recordings", "quizzes", "assignments", "projects"):
            item = domain_progress.get(key, {})
            if key == "recordings":
                totals_done += item.get("completed", 0)
                totals_available += item.get("total", 0)
            elif key == "quizzes":
                totals_done += item.get("passed", 0)
                totals_available += item.get("total", 0)
            else:
                field = "submitted"
                totals_done += item.get(field, 0)
                totals_available += item.get("total", 0)

    overall_percentage = round((totals_done / totals_available * 100) if totals_available else 0.0, 1)
    return {"domains": result, "overall_percentage": overall_percentage}


@router.get("/domain/{domain_id}")
async def get_domain_progress(
    domain_id: int,
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    """Get detailed progress for a specific domain."""
    if not verify_student_domain_access(student, domain_id, db):
        raise HTTPException(status_code=403, detail="No access to this domain")

    return _get_domain_progress(student.id, domain_id, db)


def _get_domain_progress(student_id: int, domain_id: int, db: Session) -> dict:
    # Recordings
    total_recs = db.query(Recording).filter(
        Recording.domain_id == domain_id, Recording.is_published == True
    ).count()
    completed_recs = (
        db.query(VideoProgress)
        .join(Recording, VideoProgress.recording_id == Recording.id)
        .filter(
            VideoProgress.student_id == student_id,
            Recording.domain_id == domain_id,
            VideoProgress.is_completed == True,
        )
        .count()
    )
    rec_pct = (completed_recs / total_recs * 100) if total_recs > 0 else 0.0

    # Quizzes
    from app.models.quiz import Quiz
    total_quizzes = db.query(Quiz).filter(Quiz.domain_id == domain_id, Quiz.is_published == True).count()
    passed_quizzes = (
        db.query(QuizAttempt)
        .join(Quiz)
        .filter(
            QuizAttempt.student_id == student_id,
            Quiz.domain_id == domain_id,
            QuizAttempt.is_passed == True,
        )
        .count()
    )

    # Assignments
    from app.models.assignment import Assignment
    total_assignments = db.query(Assignment).filter(Assignment.domain_id == domain_id, Assignment.is_published == True).count()
    submitted_assignments = (
        db.query(AssignmentSubmission)
        .join(Assignment)
        .filter(
            AssignmentSubmission.student_id == student_id,
            Assignment.domain_id == domain_id,
        )
        .count()
    )

    # Projects
    from app.models.project import Project
    total_projects = db.query(Project).filter(Project.domain_id == domain_id, Project.is_published == True).count()
    submitted_projects = (
        db.query(ProjectSubmission)
        .join(Project)
        .filter(
            ProjectSubmission.student_id == student_id,
            Project.domain_id == domain_id,
        )
        .count()
    )

    overall = _calc_overall([
        (completed_recs, total_recs),
        (passed_quizzes, total_quizzes),
        (submitted_assignments, total_assignments),
        (submitted_projects, total_projects),
    ])

    return {
        "recordings": {"completed": completed_recs, "total": total_recs, "percentage": round(rec_pct, 1)},
        "quizzes": {"passed": passed_quizzes, "total": total_quizzes},
        "assignments": {"submitted": submitted_assignments, "total": total_assignments},
        "projects": {"submitted": submitted_projects, "total": total_projects},
        "overall_percentage": round(overall, 1),
    }


def _calc_overall(pairs: list) -> float:
    scored = sum(done for done, _ in pairs)
    total = sum(tot for _, tot in pairs)
    return (scored / total * 100) if total > 0 else 0.0


# ─── Student Dashboard ───────────────────────────────────────

dashboard_router = APIRouter(prefix="/student/dashboard", tags=["Student - Dashboard"])


@dashboard_router.get("")
async def get_dashboard(
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    from app.models.domain import StudentDomain, DomainAccessStatus
    from app.models.audit import Notification, Announcement

    # Assigned domains
    active_sds = (
        db.query(StudentDomain)
        .filter(StudentDomain.student_id == student.id, StudentDomain.status == DomainAccessStatus.active)
        .all()
    )
    domain_ids = [sd.domain_id for sd in active_sds]

    # Recently uploaded recordings
    recent_recordings = (
        db.query(Recording)
        .filter(Recording.domain_id.in_(domain_ids), Recording.is_published == True)
        .order_by(Recording.created_at.desc())
        .limit(5)
        .all()
    )

    # Continue watching
    continue_watching = (
        db.query(VideoProgress)
        .join(Recording)
        .filter(
            VideoProgress.student_id == student.id,
            VideoProgress.is_completed == False,
            VideoProgress.watched_seconds > 0,
            Recording.domain_id.in_(domain_ids),
        )
        .order_by(VideoProgress.last_watched_at.desc())
        .limit(5)
        .all()
    )

    # Pending assignments
    from app.models.assignment import Assignment, AssignmentSubmission
    pending_assignments = (
        db.query(Assignment)
        .filter(
            Assignment.domain_id.in_(domain_ids),
            Assignment.is_published == True,
            ~Assignment.id.in_(
                db.query(AssignmentSubmission.assignment_id)
                .filter(AssignmentSubmission.student_id == student.id)
            )
        )
        .order_by(Assignment.due_date.asc())
        .limit(5)
        .all()
    )

    # Unread notifications
    unread_count = db.query(Notification).filter(
        Notification.user_id == student.id, Notification.is_read == False
    ).count()

    # Announcements
    announcements = (
        db.query(Announcement)
        .filter(
            Announcement.is_published == True,
            (Announcement.is_global == True) | (Announcement.domain_id.in_(domain_ids))
        )
        .order_by(Announcement.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "student_name": student.profile.full_name if student.profile else "",
        "domains_count": len(active_sds),
        "unread_notifications": unread_count,
        "recent_recordings": [
            {"id": r.id, "title": r.title, "domain_id": r.domain_id, "created_at": r.created_at}
            for r in recent_recordings
        ],
        "continue_watching": [
            {
                "recording_id": p.recording_id,
                "title": p.recording.title if p.recording else "",
                "percentage": float(p.percentage_watched),
                "last_watched_at": p.last_watched_at,
            }
            for p in continue_watching
        ],
        "pending_assignments": [
            {"id": a.id, "title": a.title, "due_date": a.due_date, "domain_id": a.domain_id}
            for a in pending_assignments
        ],
        "announcements": [
            {"id": a.id, "title": a.title, "type": a.type, "created_at": a.created_at}
            for a in announcements
        ],
    }
