from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole, UserStatus, UserProfile
from app.models.domain import StudentDomain, DomainAccessStatus, Domain
from app.auth.dependencies import get_current_admin
from app.utils.audit import log_audit, create_notification
from app.utils.file_handler import save_upload_file
from app.config import settings
from app.models.assignment import AssignmentSubmission
from app.models.project import ProjectSubmission
from app.models.quiz import QuizAttempt
from app.models.recording import VideoProgress

router = APIRouter(prefix="/admin/students", tags=["Admin - Students"])


@router.get("")
async def list_students(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    domain_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all students with search, filter, and pagination."""
    query = (
        db.query(User)
        .join(UserProfile, User.id == UserProfile.user_id, isouter=True)
        .filter(User.role == UserRole.student)
    )

    if search:
        query = query.filter(
            or_(
                User.email.ilike(f"%{search}%"),
                UserProfile.full_name.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%"),
            )
        )
    if status:
        query = query.filter(User.status == status)
    if domain_id:
        query = query.join(StudentDomain, User.id == StudentDomain.student_id).filter(
            StudentDomain.domain_id == domain_id,
            StudentDomain.status == DomainAccessStatus.active,
        )

    total = query.count()
    students = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "students": [_format_student(s) for s in students],
    }


@router.get("/{student_id:int}")
async def get_student(
    student_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get a student's full profile."""
    student = _get_student_or_404(student_id, db)
    domains = (
        db.query(StudentDomain)
        .join(Domain)
        .filter(StudentDomain.student_id == student_id)
        .all()
    )
    return {
        **_format_student(student),
        "domains": [
            {
                "id": sd.id,
                "domain_id": sd.domain_id,
                "domain_name": sd.domain.name if sd.domain else None,
                "status": sd.status,
                "granted_at": sd.granted_at,
                "access_expires_at": sd.access_expires_at,
                "revoked_at": sd.revoked_at,
            }
            for sd in domains
        ],
    }


@router.get("/{student_id}/overview")
async def get_student_overview(
    student_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return a detailed admin-only overview for one student."""
    student = _get_student_or_404(student_id, db)
    domains = db.query(StudentDomain).join(Domain).filter(StudentDomain.student_id == student_id).all()
    assignment_subs = db.query(AssignmentSubmission).filter(AssignmentSubmission.student_id == student_id).order_by(AssignmentSubmission.submitted_at.desc()).all()
    project_subs = db.query(ProjectSubmission).filter(ProjectSubmission.student_id == student_id).order_by(ProjectSubmission.submitted_at.desc()).all()
    quiz_attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).order_by(QuizAttempt.created_at.desc()).all()
    completed_videos = db.query(VideoProgress).filter(VideoProgress.student_id == student_id, VideoProgress.is_completed == True).count()
    return {
        **_format_student(student),
        "domains": [{"id": sd.id, "domain_id": sd.domain_id, "domain_name": sd.domain.name if sd.domain else None, "status": sd.status, "granted_at": sd.granted_at, "access_expires_at": sd.access_expires_at} for sd in domains],
        "summary": {
            "assignment_submissions": len(assignment_subs),
            "project_submissions": len(project_subs),
            "quiz_attempts": len(quiz_attempts),
            "completed_recordings": completed_videos,
        },
        "assignment_submissions": [{"id": x.id, "assignment_id": x.assignment_id, "status": x.status, "marks_obtained": float(x.marks_obtained) if x.marks_obtained is not None else None, "feedback": x.feedback, "submitted_at": x.submitted_at} for x in assignment_subs],
        "project_submissions": [{"id": x.id, "project_id": x.project_id, "status": x.status, "marks_obtained": float(x.marks_obtained) if x.marks_obtained is not None else None, "feedback": x.feedback, "github_link": x.github_link, "live_demo_link": x.live_demo_link, "submitted_at": x.submitted_at} for x in project_subs],
        "quiz_attempts": [{"id": x.id, "quiz_id": x.quiz_id, "attempt_number": x.attempt_number, "score": float(x.score) if x.score is not None else None, "percentage": float(x.percentage) if x.percentage is not None else None, "is_passed": x.is_passed, "status": x.status, "submitted_at": x.submitted_at} for x in quiz_attempts],
    }


@router.patch("/{student_id}/approve")
async def approve_student(
    student_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    student = _get_student_or_404(student_id, db)
    student.status = UserStatus.approved
    if student.profile:
        student.profile.approved_at = datetime.utcnow()
        student.profile.approved_by = admin.id
    db.commit()
    try:
        from app.utils.google_sheets import sync_student_to_google_sheet
        sync_student_to_google_sheet(student)
    except Exception:
        import logging
        logging.getLogger("qodekraft").exception(
            "Google Sheets sync failed after approving student %s", student.id
        )

    create_notification(db, student.id, "Account Approved",
                        "Your account has been approved. You can now log in and access your learning domains.",
                        "approval")
    log_audit(db, "approve_student", admin.id, admin.email, "user", student_id,
              ip_address=request.client.host if request.client else None)
    return {"message": "Student approved successfully"}


@router.patch("/{student_id}/reject")
async def reject_student(
    student_id: int,
    reason: Optional[str] = None,
    request: Request = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    student = _get_student_or_404(student_id, db)
    student.status = UserStatus.rejected
    if student.profile:
        student.profile.rejected_at = datetime.utcnow()
        student.profile.rejected_by = admin.id
        student.profile.rejection_reason = reason
    db.commit()
    try:
        from app.utils.google_sheets import sync_student_to_google_sheet
        sync_student_to_google_sheet(student)
    except Exception:
        import logging
        logging.getLogger("qodekraft").exception(
            "Google Sheets sync failed after rejecting student %s", student.id
        )
    create_notification(db, student.id, "Account Application Rejected",
                        f"Your account application has been rejected. {reason or ''}", "rejection")
    log_audit(db, "reject_student", admin.id, admin.email, "user", student_id)
    return {"message": "Student rejected"}


@router.patch("/{student_id}/block")
async def block_student(
    student_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    student = _get_student_or_404(student_id, db)
    student.status = UserStatus.blocked
    db.commit()
    log_audit(db, "block_student", admin.id, admin.email, "user", student_id)
    return {"message": "Student blocked"}


@router.patch("/{student_id}/unblock")
async def unblock_student(
    student_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    student = _get_student_or_404(student_id, db)
    student.status = UserStatus.approved
    db.commit()
    create_notification(db, student.id, "Account Unblocked", "Your account has been unblocked.")
    log_audit(db, "unblock_student", admin.id, admin.email, "user", student_id)
    return {"message": "Student unblocked"}


@router.patch("/{student_id}/suspend")
async def suspend_student(
    student_id: int,
    reason: Optional[str] = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    student = _get_student_or_404(student_id, db)
    student.status = UserStatus.suspended
    if student.profile:
        student.profile.suspended_at = datetime.utcnow()
        student.profile.suspended_by = admin.id
        student.profile.suspension_reason = reason
    db.commit()
    log_audit(db, "suspend_student", admin.id, admin.email, "user", student_id)
    return {"message": "Student suspended"}


@router.post("/{student_id}/domains/{domain_id}")
async def assign_domain(
    student_id: int,
    domain_id: int,
    access_expires_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Assign a domain to a student."""
    student = _get_student_or_404(student_id, db)
    if student.status != UserStatus.approved:
        raise HTTPException(status_code=400, detail="Approve the student account before assigning a learning domain.")
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    existing = db.query(StudentDomain).filter(
        StudentDomain.student_id == student_id,
        StudentDomain.domain_id == domain_id,
    ).first()

    if existing:
        # Re-activate if previously revoked/suspended
        existing.status = DomainAccessStatus.active
        existing.access_expires_at = access_expires_at
        existing.granted_at = datetime.utcnow()
        existing.granted_by = admin.id
        existing.revoked_at = None
        existing.notes = notes
    else:
        sd = StudentDomain(
            student_id=student_id,
            domain_id=domain_id,
            status=DomainAccessStatus.active,
            access_expires_at=access_expires_at,
            granted_by=admin.id,
            notes=notes,
        )
        db.add(sd)

    db.commit()
    create_notification(db, student_id, "Domain Access Granted",
                        f"You have been granted access to: {domain.name}", "domain_access",
                        "domain", domain_id)
    log_audit(db, "assign_domain", admin.id, admin.email, "student_domain", student_id,
              details={"domain_id": domain_id})
    return {"message": f"Domain '{domain.name}' assigned to student"}


@router.delete("/{student_id}/domains/{domain_id}")
async def revoke_domain(
    student_id: int,
    domain_id: int,
    reason: Optional[str] = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Revoke domain access from a student (preserves all progress)."""
    sd = db.query(StudentDomain).filter(
        StudentDomain.student_id == student_id,
        StudentDomain.domain_id == domain_id,
    ).first()
    if not sd:
        raise HTTPException(status_code=404, detail="Domain assignment not found")

    sd.status = DomainAccessStatus.revoked
    sd.revoked_at = datetime.utcnow()
    sd.revoked_by = admin.id
    sd.revocation_reason = reason
    db.commit()

    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    create_notification(db, student_id, "Domain Access Removed",
                        f"Your access to '{domain.name if domain else domain_id}' has been removed.",
                        "domain_access")
    log_audit(db, "revoke_domain", admin.id, admin.email, "student_domain", student_id,
              details={"domain_id": domain_id, "reason": reason})
    return {"message": "Domain access revoked (student progress preserved)"}


# ─── Google Sheets Sync ─────────────────────────────────────

@router.post("/sync-to-google-sheets")
async def sync_all_students_to_google_sheets(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Synchronize all student details from MySQL to the configured Google Sheet."""
    students = (
        db.query(User)
        .join(UserProfile, User.id == UserProfile.user_id, isouter=True)
        .filter(User.role == UserRole.student)
        .all()
    )
    from app.utils.google_sheets import sync_students_to_google_sheet
    return sync_students_to_google_sheet(students)


# ─── Excel Export ───────────────────────────────────────────

@router.get("/export/excel")
async def export_students_excel(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from app.utils.excel_export import create_excel_response
    students = (
        db.query(User)
        .join(UserProfile, isouter=True)
        .filter(User.role == UserRole.student)
        .all()
    )
    data = []
    for s in students:
        p = s.profile
        data.append({
            "ID": s.id,
            "Full Name": p.full_name if p else "",
            "Email": s.email,
            "Phone": s.phone or "",
            "Status": s.status,
            "Qualification": p.qualification if p else "",
            "Preferred Domain": p.preferred_domain if p else "",
            "Registered At": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
            "Last Login": s.last_login_at.strftime("%Y-%m-%d %H:%M") if s.last_login_at else "",
        })
    return create_excel_response(data, "Students", "students_export.xlsx")


# ─── Helpers ─────────────────────────────────────────────────

def _get_student_or_404(student_id: int, db: Session) -> User:
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.student).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def _format_student(s: User) -> dict:
    p = s.profile
    return {
        "id": s.id,
        "email": s.email,
        "phone": s.phone,
        "status": s.status,
        "is_active": s.is_active,
        "last_login_at": s.last_login_at,
        "created_at": s.created_at,
        "full_name": p.full_name if p else "",
        "qualification": p.qualification if p else "",
        "preferred_domain": p.preferred_domain if p else "",
        "profile_image_url": p.profile_image_url if p else None,
    }
