from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.auth.dependencies import get_current_admin
from app.models.user import User
from app.models.audit import Announcement
from app.utils.audit import log_audit, create_notification
from app.models.domain import StudentDomain, DomainAccessStatus

router = APIRouter(prefix="/admin/announcements", tags=["Admin - Announcements"])

class AnnouncementPayload(BaseModel):
    title: str
    content: str
    type: str = "general"
    is_global: bool = True
    domain_id: Optional[int] = None
    is_published: bool = True
    expires_at: Optional[str] = None

@router.get("")
async def list_announcements(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return [_fmt(a) for a in db.query(Announcement).order_by(Announcement.created_at.desc()).all()]

@router.post("", status_code=201)
async def create_announcement(payload: AnnouncementPayload, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    a = Announcement(title=payload.title, content=payload.content, type=payload.type,
        is_global=payload.is_global, domain_id=payload.domain_id,
        is_published=payload.is_published, published_at=datetime.utcnow() if payload.is_published else None,
        expires_at=datetime.fromisoformat(payload.expires_at) if payload.expires_at else None, created_by=admin.id)
    db.add(a); db.commit(); db.refresh(a)
    if a.is_published:
        q = db.query(StudentDomain).filter(StudentDomain.status == DomainAccessStatus.active)
        if not a.is_global and a.domain_id: q = q.filter(StudentDomain.domain_id == a.domain_id)
        for sd in q.all(): create_notification(db, sd.student_id, a.title, a.content, "announcement", "announcement", a.id)
        db.commit()
    log_audit(db, "create_announcement", admin.id, admin.email, "announcement", a.id)
    return _fmt(a)

@router.patch("/{announcement_id}/toggle")
async def toggle(announcement_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    a = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not a: raise HTTPException(status_code=404, detail="Announcement not found")
    a.is_published = not a.is_published
    a.published_at = datetime.utcnow() if a.is_published else None
    db.commit(); return _fmt(a)

@router.delete("/{announcement_id}")
async def delete(announcement_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    a = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not a: raise HTTPException(status_code=404, detail="Announcement not found")
    db.delete(a); db.commit(); return {"message": "Announcement deleted"}

def _fmt(a):
    return {"id": a.id, "title": a.title, "content": a.content, "type": a.type,
            "is_global": a.is_global, "domain_id": a.domain_id, "is_published": a.is_published,
            "published_at": a.published_at, "expires_at": a.expires_at, "created_at": a.created_at}
