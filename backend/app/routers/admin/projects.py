from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.auth.dependencies import get_current_admin
from app.models.user import User
from app.models.project import Project, ProjectSubmission
from app.utils.audit import log_audit

router = APIRouter(prefix="/admin/projects", tags=["Admin - Projects"])

class ProjectPayload(BaseModel):
    domain_id: int
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    technologies: Optional[List[str]] = None
    due_date: Optional[str] = None
    max_marks: float = 100.0
    submission_instructions: Optional[str] = None
    is_published: bool = False

@router.get("")
async def list_projects(domain_id: Optional[int] = Query(None), admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    q = db.query(Project)
    if domain_id: q = q.filter(Project.domain_id == domain_id)
    return [_format(p) for p in q.order_by(Project.created_at.desc()).all()]

@router.post("", status_code=201)
async def create_project(payload: ProjectPayload, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    from datetime import datetime
    p = Project(
        domain_id=payload.domain_id, title=payload.title, description=payload.description,
        requirements=payload.requirements, technologies=payload.technologies or [],
        due_date=datetime.fromisoformat(payload.due_date) if payload.due_date else None,
        max_marks=payload.max_marks, submission_instructions=payload.submission_instructions,
        is_published=payload.is_published, status="published" if payload.is_published else "draft",
        created_by=admin.id,
    )
    db.add(p); db.commit(); db.refresh(p)
    log_audit(db, "create_project", admin.id, admin.email, "project", p.id)
    return _format(p)

@router.patch("/{project_id}/publish")
async def publish_project(project_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    p = _get(project_id, db); p.is_published = True; p.status = "published"; db.commit(); return {"message": "Project published"}

@router.patch("/{project_id}/unpublish")
async def unpublish_project(project_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    p = _get(project_id, db); p.is_published = False; p.status = "draft"; db.commit(); return {"message": "Project unpublished"}

@router.delete("/{project_id}")
async def delete_project(project_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    p = _get(project_id, db); db.delete(p); db.commit(); return {"message": "Project deleted"}

@router.get("/{project_id}/submissions/{submission_id}/files/{file_id}")
async def download_project_submission_file(
    project_id: int, submission_id: int, file_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from app.models.project import ProjectSubmissionFile
    sub = db.query(ProjectSubmission).filter(ProjectSubmission.id == submission_id, ProjectSubmission.project_id == project_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Project submission not found")
    f = db.query(ProjectSubmissionFile).filter(ProjectSubmissionFile.id == file_id, ProjectSubmissionFile.submission_id == submission_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(f.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored file not found")
    return FileResponse(path=str(path), filename=f.original_name or f.file_name, media_type=f.file_mime or "application/octet-stream")

@router.get("/{project_id}/submissions")
async def get_project_submissions(
    project_id: int,
    status: Optional[str] = Query(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    project = _get(project_id, db)
    query = db.query(ProjectSubmission).filter(ProjectSubmission.project_id == project_id)
    if status:
        query = query.filter(ProjectSubmission.status == status)
    return [_format_submission(s) for s in query.order_by(ProjectSubmission.submitted_at.desc()).all()]

@router.patch("/{project_id}/submissions/{submission_id}/review")
async def review_project_submission(
    project_id: int,
    submission_id: int,
    marks_obtained: Optional[float] = None,
    feedback: Optional[str] = None,
    status: str = "reviewed",
    correction_request: Optional[str] = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    sub = db.query(ProjectSubmission).filter(
        ProjectSubmission.id == submission_id,
        ProjectSubmission.project_id == project_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Project submission not found")
    allowed = {"under_review", "reviewed", "returned", "resubmitted", "approved", "rejected"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid review status")
    sub.marks_obtained = marks_obtained
    sub.feedback = feedback
    sub.status = status
    sub.correction_request = correction_request
    sub.reviewed_by = admin.id
    sub.reviewed_at = __import__("datetime").datetime.utcnow()
    if status == "approved": sub.approved_at = __import__("datetime").datetime.utcnow()
    if status == "rejected": sub.rejected_at = __import__("datetime").datetime.utcnow()
    if status == "returned": sub.returned_at = __import__("datetime").datetime.utcnow()
    db.commit(); db.refresh(sub)
    return _format_submission(sub)

def _format_submission(s: ProjectSubmission) -> dict:
    return {
        "id": s.id, "project_id": s.project_id, "student_id": s.student_id,
        "student_name": s.student.profile.full_name if s.student and s.student.profile else None,
        "student_email": s.student.email if s.student else None,
        "submission_number": s.submission_number, "description": s.description,
        "github_link": s.github_link, "live_demo_link": s.live_demo_link,
        "status": s.status, "marks_obtained": float(s.marks_obtained) if s.marks_obtained is not None else None,
        "feedback": s.feedback, "correction_request": s.correction_request,
        "submitted_at": s.submitted_at, "reviewed_at": s.reviewed_at,
        "files": [{"id": f.id, "file_name": f.file_name, "original_name": f.original_name, "file_size": f.file_size, "file_mime": f.file_mime} for f in s.files],
    }

def _get(project_id, db):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p: raise HTTPException(status_code=404, detail="Project not found")
    return p

def _format(p):
    return {"id": p.id, "domain_id": p.domain_id, "title": p.title, "description": p.description,
            "requirements": p.requirements, "technologies": p.technologies, "due_date": p.due_date,
            "max_marks": float(p.max_marks) if p.max_marks is not None else None,
            "submission_instructions": p.submission_instructions, "is_published": p.is_published,
            "status": p.status, "created_at": p.created_at}
