from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.assignment import Assignment, AssignmentResource, AssignmentSubmission, AssignmentStatus, SubmissionStatus
from app.auth.dependencies import get_current_admin
from app.models.user import User
from app.utils.file_handler import save_upload_file
from app.utils.audit import log_audit, create_notification
from app.config import settings
import json

router = APIRouter(prefix="/admin/assignments", tags=["Admin - Assignments"])


@router.get("")
async def list_assignments(
    domain_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Assignment)
    if domain_id: query = query.filter(Assignment.domain_id == domain_id)
    if status: query = query.filter(Assignment.status == status)
    total = query.count()
    assignments = query.order_by(Assignment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "assignments": [_format_assignment(a) for a in assignments]}


@router.post("", status_code=201)
async def create_assignment(
    domain_id: int = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
    due_date: Optional[datetime] = Form(None),
    max_marks: float = Form(100.0),
    allowed_extensions: Optional[str] = Form(None),  # JSON string
    max_file_size_mb: int = Form(50),
    is_published: bool = Form(False),
    reference_files: List[UploadFile] = File(default=[]),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    ext_list = json.loads(allowed_extensions) if allowed_extensions else None

    assignment = Assignment(
        domain_id=domain_id,
        title=title,
        description=description,
        instructions=instructions,
        topic=topic,
        due_date=due_date,
        max_marks=max_marks,
        allowed_extensions=ext_list,
        max_file_size_mb=max_file_size_mb,
        is_published=is_published,
        status=AssignmentStatus.published if is_published else AssignmentStatus.draft,
        created_by=admin.id,
    )
    db.add(assignment)
    db.flush()

    for ref in reference_files:
        if ref.filename:
            path, name, size, mime = await save_upload_file(ref, settings.media_assignments_path)
            resource = AssignmentResource(
                assignment_id=assignment.id, file_path=path, file_name=name,
                file_size=size, file_mime=mime,
            )
            db.add(resource)

    db.commit()
    db.refresh(assignment)
    log_audit(db, "create_assignment", admin.id, admin.email, "assignment", assignment.id)
    return _format_assignment(assignment)


@router.get("/{assignment_id}")
async def get_assignment(
    assignment_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    a = _get_or_404(assignment_id, db)
    result = _format_assignment(a)
    result["resources"] = [{"id": r.id, "file_name": r.file_name, "file_size": r.file_size} for r in a.resources]
    return result


@router.get("/{assignment_id}/submissions/{submission_id}/files/{file_id}")
async def download_assignment_submission_file(
    assignment_id: int, submission_id: int, file_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from app.models.assignment import AssignmentSubmissionFile
    sub = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id, AssignmentSubmission.assignment_id == assignment_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Assignment submission not found")
    f = db.query(AssignmentSubmissionFile).filter(AssignmentSubmissionFile.id == file_id, AssignmentSubmissionFile.submission_id == submission_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(f.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored file not found")
    return FileResponse(path=str(path), filename=f.original_name or f.file_name, media_type=f.file_mime or "application/octet-stream")

@router.get("/{assignment_id}/submissions")
async def get_submissions(
    assignment_id: int,
    status: Optional[str] = Query(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(AssignmentSubmission).filter(AssignmentSubmission.assignment_id == assignment_id)
    if status:
        query = query.filter(AssignmentSubmission.status == status)
    subs = query.all()
    return [_format_submission(s) for s in subs]


@router.patch("/{assignment_id}/submissions/{submission_id}/review")
async def review_submission(
    assignment_id: int,
    submission_id: int,
    marks_obtained: Optional[float] = None,
    feedback: Optional[str] = None,
    status: str = "reviewed",
    correction_request: Optional[str] = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    sub = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.id == submission_id,
        AssignmentSubmission.assignment_id == assignment_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    sub.marks_obtained = marks_obtained
    sub.feedback = feedback
    sub.status = status
    sub.correction_request = correction_request
    sub.reviewed_by = admin.id
    sub.reviewed_at = datetime.utcnow()

    if status == "approved":
        sub.approved_at = datetime.utcnow()
    elif status == "rejected":
        sub.rejected_at = datetime.utcnow()
    elif status == "returned":
        sub.returned_at = datetime.utcnow()

    db.commit()

    msg = f"Your assignment submission has been {status}."
    if feedback:
        msg += f" Feedback: {feedback}"
    create_notification(db, sub.student_id, "Assignment Reviewed", msg, "assignment", "assignment", assignment_id)
    log_audit(db, f"review_assignment_submission", admin.id, admin.email, "assignment_submission", submission_id)
    return _format_submission(sub)


@router.patch("/{assignment_id}/publish")
async def publish_assignment(
    assignment_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    a = _get_or_404(assignment_id, db)
    a.is_published = True
    a.status = AssignmentStatus.published
    db.commit()
    return {"message": "Assignment published"}


@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    a = _get_or_404(assignment_id, db)
    log_audit(db, "delete_assignment", admin.id, admin.email, "assignment", assignment_id)
    db.delete(a)
    db.commit()
    return {"message": "Assignment deleted"}


def _get_or_404(assignment_id: int, db: Session) -> Assignment:
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a


def _format_assignment(a: Assignment) -> dict:
    return {
        "id": a.id, "domain_id": a.domain_id, "title": a.title,
        "description": a.description, "topic": a.topic,
        "due_date": a.due_date, "max_marks": float(a.max_marks),
        "allowed_extensions": a.allowed_extensions,
        "max_file_size_mb": a.max_file_size_mb,
        "is_published": a.is_published, "status": a.status,
        "created_at": a.created_at,
    }


def _format_submission(s: AssignmentSubmission) -> dict:
    return {
        "id": s.id, "assignment_id": s.assignment_id, "student_id": s.student_id,
        "student_name": s.student.profile.full_name if s.student and s.student.profile else None,
        "student_email": s.student.email if s.student else None,
        "submission_number": s.submission_number, "status": s.status,
        "marks_obtained": float(s.marks_obtained) if s.marks_obtained else None,
        "feedback": s.feedback, "correction_request": s.correction_request,
        "submitted_at": s.submitted_at, "reviewed_at": s.reviewed_at,
        "is_late": s.is_late,
        "files": [{"id": f.id, "file_name": f.file_name, "original_name": f.original_name, "file_size": f.file_size, "file_mime": f.file_mime} for f in s.files],
    }
