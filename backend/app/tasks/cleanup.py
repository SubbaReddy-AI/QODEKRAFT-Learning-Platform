"""
Daily cleanup job for media files.
- Checks recordings beyond active limit + retention period → deletes video/thumbnail files
- Checks assignments beyond retention period → deletes instruction attachments
- Keeps all MySQL records and student progress
- Logs everything to storage_cleanup_logs
"""
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.recording import Recording, RecordingStatus
from app.models.assignment import Assignment, AssignmentStatus
from app.models.audit import StorageCleanupLog, SystemSetting
from app.utils.file_handler import delete_file_safe

logger = logging.getLogger(__name__)


def get_setting(db: Session, key: str, default: str = "") -> str:
    """Get a system setting value."""
    setting = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
    return setting.setting_value if setting else default


def run_cleanup(db: Session = None, triggered_by: int = None, job_type: str = "scheduled") -> dict:
    """Run the media cleanup job. Returns a summary dict."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    log = StorageCleanupLog(job_type=job_type, triggered_by=triggered_by, status="running")
    db.add(log)
    db.commit()
    db.refresh(log)

    errors = []
    recordings_processed = 0
    recordings_deleted = 0
    assignments_processed = 0
    assignments_deleted = 0
    total_bytes_freed = 0

    try:
        # Get settings
        retention_days = int(get_setting(db, "recording_retention_days", "15"))
        auto_cleanup = get_setting(db, "auto_cleanup_enabled", "true").lower() == "true"

        if not auto_cleanup and job_type == "scheduled":
            log.status = "completed"
            log.notes = "Auto cleanup is disabled — skipped"
            log.completed_at = datetime.utcnow()
            db.commit()
            return {"status": "skipped", "reason": "Auto cleanup disabled"}

        # ── RECORDINGS CLEANUP ──────────────────────────────────────────
        # For each domain, find recordings beyond max_active_recordings + retention period
        from app.models.domain import Domain
        domains = db.query(Domain).filter(Domain.is_active == True).all()

        for domain in domains:
            max_active = domain.max_active_recordings or 45
            domain_retention = domain.recording_retention_days or retention_days

            # Get all published recordings for this domain, ordered newest first
            all_recordings = (
                db.query(Recording)
                .filter(
                    Recording.domain_id == domain.id,
                    Recording.is_published == True,
                    Recording.status != RecordingStatus.media_deleted,
                )
                .order_by(Recording.created_at.desc())
                .all()
            )

            for idx, rec in enumerate(all_recordings):
                recordings_processed += 1
                position = idx + 1  # 1-based position (1 = newest)

                if position <= max_active:
                    # Still within active limit — keep it
                    if rec.status in [RecordingStatus.retention_period, RecordingStatus.archived]:
                        rec.status = RecordingStatus.published
                        db.commit()
                    continue

                # Beyond active limit
                if rec.status == RecordingStatus.published:
                    rec.status = RecordingStatus.retention_period
                    rec.archived_at = datetime.utcnow()
                    db.commit()

                # Check if retention period has passed
                if rec.archived_at:
                    expiry = rec.archived_at + timedelta(days=domain_retention)
                    if datetime.utcnow() >= expiry and rec.video_path:
                        # Delete video file
                        freed = 0
                        if rec.video_path and delete_file_safe(rec.video_path):
                            if rec.video_size:
                                freed += rec.video_size
                            recordings_deleted += 1

                        # Delete thumbnail
                        if rec.thumbnail_path:
                            delete_file_safe(rec.thumbnail_path)

                        # Update status
                        rec.status = RecordingStatus.media_deleted
                        rec.media_deleted_at = datetime.utcnow()
                        rec.video_path = None
                        rec.thumbnail_path = None
                        rec.cleanup_log = f"Media deleted by {'scheduled' if job_type == 'scheduled' else 'manual'} cleanup on {datetime.utcnow().isoformat()}"
                        total_bytes_freed += freed
                        db.commit()

        # ── ASSIGNMENTS CLEANUP ─────────────────────────────────────────
        assign_retention = int(get_setting(db, "assignment_retention_days", "45"))
        assign_extra = int(get_setting(db, "assignment_extra_retention_days", "15"))
        cutoff = datetime.utcnow() - timedelta(days=assign_retention + assign_extra)

        old_assignments = (
            db.query(Assignment)
            .filter(
                Assignment.created_at <= cutoff,
                Assignment.status == AssignmentStatus.published,
            )
            .all()
        )

        for assign in old_assignments:
            assignments_processed += 1
            # Delete reference files (instruction attachments)
            for resource in assign.resources:
                if resource.file_path and delete_file_safe(resource.file_path):
                    assignments_deleted += 1
                    if resource.file_size:
                        total_bytes_freed += resource.file_size
                    resource.file_path = ""

            assign.status = AssignmentStatus.media_deleted
            assign.media_deleted_at = datetime.utcnow()
            db.commit()

        # ── FINALIZE LOG ────────────────────────────────────────────────
        log.status = "completed"
        log.recordings_processed = recordings_processed
        log.recordings_deleted = recordings_deleted
        log.assignments_processed = assignments_processed
        log.assignments_deleted = assignments_deleted
        log.total_bytes_freed = total_bytes_freed
        log.errors = errors if errors else None
        log.completed_at = datetime.utcnow()
        db.commit()

        result = {
            "status": "completed",
            "recordings_processed": recordings_processed,
            "recordings_deleted": recordings_deleted,
            "assignments_processed": assignments_processed,
            "assignments_deleted": assignments_deleted,
            "bytes_freed": total_bytes_freed,
        }
        logger.info(f"Cleanup completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Cleanup job failed: {e}", exc_info=True)
        errors.append(str(e))
        log.status = "failed"
        log.errors = errors
        log.completed_at = datetime.utcnow()
        db.commit()
        return {"status": "failed", "error": str(e)}
    finally:
        if close_db:
            db.close()


def setup_scheduler(app):
    """Attach APScheduler to the FastAPI app."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.config import settings

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_cleanup,
        trigger="cron",
        hour=settings.CLEANUP_JOB_HOUR,
        minute=settings.CLEANUP_JOB_MINUTE,
        id="daily_media_cleanup",
        replace_existing=True,
    )
    from app.tasks.reminders import run_deadline_reminders
    scheduler.add_job(
        run_deadline_reminders,
        trigger="interval",
        hours=1,
        id="hourly_deadline_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Cleanup scheduler started — runs daily at {settings.CLEANUP_JOB_HOUR:02d}:{settings.CLEANUP_JOB_MINUTE:02d} UTC")

    import atexit
    atexit.register(lambda: scheduler.shutdown())
    return scheduler
