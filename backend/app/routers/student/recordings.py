from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
from datetime import datetime

from app.database import get_db
from app.models.recording import Recording, VideoProgress, RecordingStatus
from app.models.domain import StudentDomain, DomainAccessStatus
from app.auth.dependencies import get_current_approved_student, verify_student_domain_access
from app.models.user import User

router = APIRouter(prefix="/student/recordings", tags=["Student - Recordings"])


@router.get("")
async def list_recordings(
    domain_id: int = Query(...),
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    """List published recordings for a domain the student has access to."""
    if not verify_student_domain_access(student, domain_id, db):
        raise HTTPException(status_code=403, detail="You do not have access to this domain")

    recordings = (
        db.query(Recording)
        .filter(
            Recording.domain_id == domain_id,
            Recording.is_published == True,
            Recording.status.in_([RecordingStatus.published, RecordingStatus.retention_period]),
        )
        .order_by(Recording.class_number.asc(), Recording.created_at.asc())
        .all()
    )

    # Get progress for each recording
    result = []
    for rec in recordings:
        progress = db.query(VideoProgress).filter(
            VideoProgress.student_id == student.id,
            VideoProgress.recording_id == rec.id,
        ).first()
        result.append({
            "id": rec.id, "title": rec.title, "description": rec.description,
            "topic": rec.topic, "class_number": rec.class_number,
            "duration_seconds": rec.duration_seconds, "status": rec.status,
            "thumbnail_available": bool(rec.thumbnail_name),
            "has_video": bool(rec.video_path),
            "publish_date": rec.publish_date,
            "progress": {
                "watched_seconds": progress.watched_seconds if progress else 0,
                "percentage": float(progress.percentage_watched) if progress else 0.0,
                "is_completed": progress.is_completed if progress else False,
                "last_watched_at": progress.last_watched_at if progress else None,
            },
        })
    return result


@router.get("/{recording_id}")
async def get_recording_detail(
    recording_id: int,
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    """Get full recording details (verifies domain access)."""
    rec = db.query(Recording).filter(Recording.id == recording_id, Recording.is_published == True).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not verify_student_domain_access(student, rec.domain_id, db):
        raise HTTPException(status_code=403, detail="You do not have access to this domain")

    progress = db.query(VideoProgress).filter(
        VideoProgress.student_id == student.id,
        VideoProgress.recording_id == rec.id,
    ).first()

    # Find prev/next in domain
    domain_recs = (
        db.query(Recording)
        .filter(Recording.domain_id == rec.domain_id, Recording.is_published == True)
        .order_by(Recording.class_number.asc())
        .all()
    )
    ids = [r.id for r in domain_recs]
    idx = ids.index(rec.id) if rec.id in ids else -1
    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if idx < len(ids) - 1 else None

    return {
        "id": rec.id, "title": rec.title, "description": rec.description,
        "topic": rec.topic, "class_number": rec.class_number,
        "duration_seconds": rec.duration_seconds, "publish_date": rec.publish_date,
        "has_video": bool(rec.video_path),
        "thumbnail_available": bool(rec.thumbnail_name),
        "resources": [{"id": r.id, "title": r.title, "file_name": r.file_name, "is_downloadable": r.is_downloadable} for r in rec.resources],
        "prev_recording_id": prev_id,
        "next_recording_id": next_id,
        "related_quiz_id": rec.related_quiz_id,
        "related_assignment_id": rec.related_assignment_id,
        "progress": {
            "watched_seconds": progress.watched_seconds if progress else 0,
            "percentage": float(progress.percentage_watched) if progress else 0.0,
            "is_completed": progress.is_completed if progress else False,
        },
    }


@router.get("/{recording_id}/stream")
async def stream_video(
    recording_id: int,
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    """Protected video streaming endpoint — verifies auth + domain access."""
    rec = db.query(Recording).filter(Recording.id == recording_id, Recording.is_published == True).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not verify_student_domain_access(student, rec.domain_id, db):
        raise HTTPException(status_code=403, detail="Access denied")

    if not rec.video_path or rec.status == RecordingStatus.media_deleted:
        raise HTTPException(status_code=410, detail="Video file is no longer available")

    video_file = Path(rec.video_path)
    if not video_file.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        path=str(video_file),
        media_type=rec.video_mime or "video/mp4",
        filename=rec.video_name,
    )


@router.post("/{recording_id}/progress")
async def update_progress(
    recording_id: int,
    watched_seconds: int,
    duration_seconds: Optional[int] = None,
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    """Update video watch progress (called periodically by player)."""
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not verify_student_domain_access(student, rec.domain_id, db):
        raise HTTPException(status_code=403, detail="Access denied")

    progress = db.query(VideoProgress).filter(
        VideoProgress.student_id == student.id,
        VideoProgress.recording_id == recording_id,
    ).first()

    dur = duration_seconds or rec.duration_seconds or 1
    pct = min(100.0, (watched_seconds / dur) * 100) if dur > 0 else 0.0
    is_complete = pct >= 90.0

    if progress:
        progress.watched_seconds = max(progress.watched_seconds, watched_seconds)
        progress.duration_seconds = dur
        progress.percentage_watched = pct
        progress.last_watched_at = datetime.utcnow()
        if is_complete and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = datetime.utcnow()
    else:
        progress = VideoProgress(
            student_id=student.id,
            recording_id=recording_id,
            watched_seconds=watched_seconds,
            duration_seconds=dur,
            percentage_watched=pct,
            is_completed=is_complete,
            completed_at=datetime.utcnow() if is_complete else None,
            last_watched_at=datetime.utcnow(),
        )
        db.add(progress)

    db.commit()
    return {"percentage": pct, "is_completed": is_complete}


@router.post("/{recording_id}/complete")
async def mark_completed(
    recording_id: int,
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    """Manually mark a recording as completed."""
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec or not verify_student_domain_access(student, rec.domain_id, db):
        raise HTTPException(status_code=403, detail="Access denied")

    progress = db.query(VideoProgress).filter(
        VideoProgress.student_id == student.id,
        VideoProgress.recording_id == recording_id,
    ).first()

    if not progress:
        progress = VideoProgress(
            student_id=student.id, recording_id=recording_id,
            watched_seconds=rec.duration_seconds or 0,
            duration_seconds=rec.duration_seconds or 0,
            percentage_watched=100.0, is_completed=True,
            completed_at=datetime.utcnow(), last_watched_at=datetime.utcnow(),
        )
        db.add(progress)
    else:
        progress.is_completed = True
        progress.percentage_watched = 100.0
        progress.completed_at = datetime.utcnow()

    db.commit()
    return {"message": "Marked as completed"}
