from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.recording import Recording, RecordingStatus
from app.models.domain import Domain
from app.models.audit import Notification
from app.auth.dependencies import get_current_admin
from app.models.user import User
from app.utils.file_handler import save_upload_file, delete_file_safe
from app.utils.audit import log_audit, create_notification
from app.config import settings

router = APIRouter(prefix="/admin/recordings", tags=["Admin - Recordings"])


@router.get("")
async def list_recordings(
    domain_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Recording)
    if domain_id:
        query = query.filter(Recording.domain_id == domain_id)
    if status:
        query = query.filter(Recording.status == status)
    total = query.count()
    recordings = query.order_by(Recording.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "recordings": [_format_rec(r) for r in recordings]}


@router.post("", status_code=201)
async def upload_recording(
    domain_id: int = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
    class_number: Optional[int] = Form(None),
    duration_seconds: Optional[int] = Form(None),
    is_published: bool = Form(False),
    video: Optional[UploadFile] = File(None),
    thumbnail: Optional[UploadFile] = File(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    video_path = video_name = video_size = video_mime = None
    thumb_path = thumb_name = None

    if video:
        video_path, video_name, video_size, video_mime = await save_upload_file(
            video, settings.media_recordings_path,
            allowed_extensions=["mp4", "webm", "mkv", "avi", "mov"],
            max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
        )

    if thumbnail:
        thumb_path, thumb_name, _, _ = await save_upload_file(
            thumbnail, settings.media_thumbnails_path,
            allowed_extensions=["jpg", "jpeg", "png", "webp"],
        )

    rec = Recording(
        domain_id=domain_id,
        title=title,
        description=description,
        topic=topic,
        class_number=class_number,
        video_path=video_path,
        video_name=video_name,
        video_size=video_size,
        video_mime=video_mime,
        thumbnail_path=thumb_path,
        thumbnail_name=thumb_name,
        duration_seconds=duration_seconds,
        status=RecordingStatus.published if is_published else RecordingStatus.draft,
        is_published=is_published,
        publish_date=datetime.utcnow() if is_published else None,
        uploaded_by=admin.id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    if is_published:
        # Notify all students in this domain
        _notify_domain_students(db, domain_id, "New Recording Available",
                                f"A new class '{title}' is available in {domain.name}",
                                "recording", rec.id)

    log_audit(db, "upload_recording", admin.id, admin.email, "recording", rec.id)
    return _format_rec(rec)


@router.get("/{recording_id}")
async def get_recording(
    recording_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rec = _get_rec_or_404(recording_id, db)
    return _format_rec(rec)


@router.put("/{recording_id}")
async def update_recording(
    recording_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
    class_number: Optional[int] = Form(None),
    duration_seconds: Optional[int] = Form(None),
    video: Optional[UploadFile] = File(None),
    thumbnail: Optional[UploadFile] = File(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rec = _get_rec_or_404(recording_id, db)
    if title: rec.title = title
    if description is not None: rec.description = description
    if topic is not None: rec.topic = topic
    if class_number is not None: rec.class_number = class_number
    if duration_seconds is not None: rec.duration_seconds = duration_seconds

    if video:
        if rec.video_path: delete_file_safe(rec.video_path)
        rec.video_path, rec.video_name, rec.video_size, rec.video_mime = await save_upload_file(
            video, settings.media_recordings_path,
            allowed_extensions=["mp4", "webm", "mkv", "avi", "mov"],
        )
        rec.status = RecordingStatus.draft
        rec.is_published = False

    if thumbnail:
        if rec.thumbnail_path: delete_file_safe(rec.thumbnail_path)
        rec.thumbnail_path, rec.thumbnail_name, _, _ = await save_upload_file(
            thumbnail, settings.media_thumbnails_path,
            allowed_extensions=["jpg", "jpeg", "png", "webp"],
        )

    db.commit()
    log_audit(db, "update_recording", admin.id, admin.email, "recording", recording_id)
    return _format_rec(rec)


@router.patch("/{recording_id}/publish")
async def publish_recording(
    recording_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rec = _get_rec_or_404(recording_id, db)
    rec.is_published = True
    rec.status = RecordingStatus.published
    rec.publish_date = datetime.utcnow()
    db.commit()
    log_audit(db, "publish_recording", admin.id, admin.email, "recording", recording_id)
    return {"message": "Recording published"}


@router.patch("/{recording_id}/unpublish")
async def unpublish_recording(
    recording_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rec = _get_rec_or_404(recording_id, db)
    rec.is_published = False
    rec.status = RecordingStatus.unpublished
    db.commit()
    log_audit(db, "unpublish_recording", admin.id, admin.email, "recording", recording_id)
    return {"message": "Recording unpublished"}


@router.delete("/{recording_id}")
async def delete_recording(
    recording_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rec = _get_rec_or_404(recording_id, db)
    if rec.video_path: delete_file_safe(rec.video_path)
    if rec.thumbnail_path: delete_file_safe(rec.thumbnail_path)
    log_audit(db, "delete_recording", admin.id, admin.email, "recording", recording_id)
    db.delete(rec)
    db.commit()
    return {"message": "Recording deleted"}


def _get_rec_or_404(recording_id: int, db: Session) -> Recording:
    r = db.query(Recording).filter(Recording.id == recording_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recording not found")
    return r


def _format_rec(r: Recording) -> dict:
    return {
        "id": r.id,
        "domain_id": r.domain_id,
        "title": r.title,
        "description": r.description,
        "topic": r.topic,
        "class_number": r.class_number,
        "video_name": r.video_name,
        "video_size": r.video_size,
        "thumbnail_name": r.thumbnail_name,
        "duration_seconds": r.duration_seconds,
        "status": r.status,
        "is_published": r.is_published,
        "publish_date": r.publish_date,
        "media_deleted_at": r.media_deleted_at,
        "created_at": r.created_at,
    }


def _notify_domain_students(db, domain_id: int, title: str, message: str, entity_type: str, entity_id: int):
    from app.models.domain import StudentDomain, DomainAccessStatus
    from app.models.user import User, UserStatus
    students = (
        db.query(StudentDomain)
        .filter(StudentDomain.domain_id == domain_id, StudentDomain.status == DomainAccessStatus.active)
        .all()
    )
    for sd in students:
        create_notification(db, sd.student_id, title, message, entity_type, entity_type, entity_id)
