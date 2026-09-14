from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.database import get_db
from app.auth.dependencies import get_current_approved_student, verify_student_domain_access
from app.models.user import User
from app.models.domain import Domain, StudentDomain, DomainAccessStatus
from app.models.project import Project
from app.models.audit import Announcement, Notification

router = APIRouter(prefix="/student", tags=["Student - Learning Content"])


def _domain_dict(d: Domain, access=None):
    return {
        "id": d.id, "name": d.name, "slug": d.slug,
        "description": d.description, "duration_weeks": d.duration_weeks,
        "is_active": d.is_active,
        "max_active_recordings": d.max_active_recordings,
        "recording_retention_days": d.recording_retention_days,
        "access_expires_at": access.access_expires_at if access else None,
        "granted_at": access.granted_at if access else None,
    }


@router.get("/domains")
async def list_my_domains(
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(StudentDomain, Domain)
        .join(Domain, Domain.id == StudentDomain.domain_id)
        .filter(
            StudentDomain.student_id == student.id,
            StudentDomain.status == DomainAccessStatus.active,
            Domain.is_active == True,
        )
        .order_by(Domain.name.asc())
        .all()
    )
    return [_domain_dict(domain, access) for access, domain in rows]


@router.get("/projects")
async def list_my_projects(
    domain_id: Optional[int] = Query(None),
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    from app.models.project import ProjectSubmission
    domain_ids = [
        row.domain_id for row in db.query(StudentDomain).filter(
            StudentDomain.student_id == student.id,
            StudentDomain.status == DomainAccessStatus.active,
        ).all()
    ]
    if domain_id:
        if domain_id not in domain_ids:
            raise HTTPException(status_code=403, detail="No access to this domain")
        domain_ids = [domain_id]
    if not domain_ids:
        return []
    projects = db.query(Project).filter(
        Project.domain_id.in_(domain_ids), Project.is_published == True
    ).order_by(Project.due_date.asc(), Project.created_at.desc()).all()
    result = []
    for p in projects:
        sub = db.query(ProjectSubmission).filter(
            ProjectSubmission.project_id == p.id,
            ProjectSubmission.student_id == student.id,
        ).order_by(ProjectSubmission.submitted_at.desc()).first()
        result.append({
            "id": p.id, "domain_id": p.domain_id, "title": p.title,
            "description": p.description, "requirements": p.requirements,
            "technologies": p.technologies, "due_date": p.due_date,
            "max_marks": float(p.max_marks) if p.max_marks is not None else None,
            "submission_instructions": p.submission_instructions,
            "submission": {
                "id": sub.id, "status": sub.status,
                "marks_obtained": float(sub.marks_obtained) if sub and sub.marks_obtained is not None else None,
                "feedback": sub.feedback if sub else None,
                "submitted_at": sub.submitted_at if sub else None,
            } if sub else None,
        })
    return result


@router.get("/announcements")
async def list_my_announcements(
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    domain_ids = [
        row.domain_id for row in db.query(StudentDomain).filter(
            StudentDomain.student_id == student.id,
            StudentDomain.status == DomainAccessStatus.active,
        ).all()
    ]
    q = db.query(Announcement).filter(Announcement.is_published == True)
    if domain_ids:
        q = q.filter((Announcement.is_global == True) | Announcement.domain_id.in_(domain_ids))
    else:
        q = q.filter(Announcement.is_global == True)
    announcements = q.order_by(Announcement.created_at.desc()).all()
    return [{
        "id": a.id, "title": a.title, "content": a.content, "type": a.type,
        "is_global": a.is_global, "domain_id": a.domain_id,
        "published_at": a.published_at, "expires_at": a.expires_at,
        "created_at": a.created_at,
    } for a in announcements]


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = Query(False),
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    q = db.query(Notification).filter(Notification.user_id == student.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    items = q.order_by(Notification.created_at.desc()).limit(100).all()
    return [{
        "id": n.id, "title": n.title, "message": n.message,
        "type": n.type, "is_read": n.is_read, "created_at": n.created_at,
    } for n in items]

@router.post("/projects/{project_id}/submit", status_code=201)
async def submit_project(
    project_id: int,
    description: Optional[str] = Form(None),
    github_link: Optional[str] = Form(None),
    live_demo_link: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    from app.models.project import ProjectSubmission, ProjectSubmissionStatus, ProjectSubmissionFile
    from app.utils.file_handler import save_upload_file
    from app.config import settings
    project = db.query(Project).filter(Project.id == project_id, Project.is_published == True).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not verify_student_domain_access(student, project.domain_id, db):
        raise HTTPException(status_code=403, detail="No access to this domain")
    previous = db.query(ProjectSubmission).filter(
        ProjectSubmission.project_id == project_id,
        ProjectSubmission.student_id == student.id,
    ).count()
    sub = ProjectSubmission(
        project_id=project_id, student_id=student.id, submission_number=previous + 1,
        description=description, github_link=github_link, live_demo_link=live_demo_link,
        status=ProjectSubmissionStatus.resubmitted if previous else ProjectSubmissionStatus.submitted,
    )
    db.add(sub); db.flush()
    for upload in files:
        if upload and upload.filename:
            path, name, size, mime = await save_upload_file(upload, settings.media_projects_path)
            suffix = (upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else "other")
            file_type = "image" if (mime or "").startswith("image/") else (suffix if suffix in {"zip", "pdf", "docx"} else "other")
            db.add(ProjectSubmissionFile(
                submission_id=sub.id, file_type=file_type, file_path=path,
                file_name=name, original_name=upload.filename, file_size=size, file_mime=mime,
            ))
    db.commit(); db.refresh(sub)
    return {"message": "Project submitted successfully", "submission_id": sub.id, "status": sub.status}
