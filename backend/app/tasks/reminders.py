import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, UserRole, UserStatus
from app.models.domain import StudentDomain, DomainAccessStatus
from app.models.quiz import Quiz, QuizAttempt, AttemptStatus
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.project import Project, ProjectSubmission
from app.utils.email import send_email

logger = logging.getLogger(__name__)


def _state_path() -> Path:
    path = Path(settings.MEDIA_ROOT) / "reminders" / "sent.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_sent() -> set[str]:
    try:
        return set(json.loads(_state_path().read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()


def _save_sent(sent: set[str]) -> None:
    path = _state_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(sent)), encoding="utf-8")
    tmp.replace(path)


def _due_label(kind: str) -> str:
    return {"quiz": "quiz", "assignment": "assignment", "project": "project"}[kind]


def _reminder_stage(due_date: datetime, now: datetime, stage: str) -> bool:
    """Match one reminder stage during an hourly scheduler window."""
    remaining = (due_date - now).total_seconds()

    # The scheduler runs hourly. A one-hour window prevents a stage from
    # being missed while keeping the requested reminder timing.
    windows = {
        "20d": (19 * 86400 + 23 * 3600, 20 * 86400),
        "10d": (9 * 86400 + 23 * 3600, 10 * 86400),
        "12h": (11 * 3600, 12 * 3600),
    }
    lower, upper = windows[stage]
    return lower < remaining <= upper


def _send_item_reminder(
    student: User,
    kind: str,
    item,
    stage: str,
    sent: set[str],
    now: datetime,
) -> bool:
    key = f"{student.id}:{kind}:{item.id}:{stage}"
    if key in sent:
        return False

    due = item.due_date
    remaining_seconds = max(0, (due - now).total_seconds())
    remaining_hours = int(remaining_seconds // 3600)
    if remaining_hours >= 24:
        days = remaining_hours // 24
        hours = remaining_hours % 24
        when = f"in about {days} day(s)" + (f" and {hours} hour(s)" if hours else "")
    else:
        when = f"in about {max(1, remaining_hours)} hour(s)"

    label = _due_label(kind)
    subject = f"QODEKRAFT reminder: pending {label} - {item.title}"
    body = (
        f"Hello {student.profile.full_name if student.profile else 'Student'},\n\n"
        f"This is an automatic reminder from QODEKRAFT. Your {label} is still pending.\n\n"
        f"{label.title()}: {item.title}\n"
        f"Deadline: {due.strftime('%d %B %Y, %I:%M %p')} UTC\n"
        f"Reminder: {stage}\n"
        f"Time remaining: {when}\n\n"
        f"Please complete and submit it before the deadline.\n\n"
        f"Regards,\nQODEKRAFT Admin"
    )
    if send_email(student.email, subject, body):
        sent.add(key)
        return True
    return False


def run_deadline_reminders(db: Session | None = None) -> dict:
    """
    Send automatic reminders for incomplete work.

    Quiz:       12 hours before deadline only.
    Assignment: 12 hours before deadline only.
    Project:    20 days, 10 days, and 12 hours before deadline.
    """
    close_db = False
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
        close_db = True

    sent = _load_sent()
    now = datetime.utcnow()

    try:
        students = db.query(User).filter(
            User.role == UserRole.student,
            User.status == UserStatus.approved,
            User.is_active == True,
        ).all()

        sent_count = 0
        pending_count = 0

        for student in students:
            domains = db.query(StudentDomain).filter(
                StudentDomain.student_id == student.id,
                StudentDomain.status == DomainAccessStatus.active,
            ).all()
            domain_ids = [x.domain_id for x in domains]
            if not domain_ids:
                continue

            # QUIZ — only 12-hour reminder
            quizzes = db.query(Quiz).filter(
                Quiz.domain_id.in_(domain_ids),
                Quiz.is_published == True,
                Quiz.due_date != None,
                Quiz.due_date > now,
                Quiz.due_date <= now + timedelta(hours=13),
            ).all()

            for item in quizzes:
                completed = db.query(QuizAttempt).filter(
                    QuizAttempt.quiz_id == item.id,
                    QuizAttempt.student_id == student.id,
                    QuizAttempt.status.in_([
                        AttemptStatus.submitted,
                        AttemptStatus.timed_out,
                    ]),
                ).first()
                if completed:
                    continue

                if _reminder_stage(item.due_date, now, "12h"):
                    pending_count += 1
                    sent_count += int(
                        _send_item_reminder(student, "quiz", item, "12h", sent, now)
                    )

            # ASSIGNMENT — only 12-hour reminder
            assignments = db.query(Assignment).filter(
                Assignment.domain_id.in_(domain_ids),
                Assignment.is_published == True,
                Assignment.due_date != None,
                Assignment.due_date > now,
                Assignment.due_date <= now + timedelta(hours=13),
            ).all()

            for item in assignments:
                completed = db.query(AssignmentSubmission).filter(
                    AssignmentSubmission.assignment_id == item.id,
                    AssignmentSubmission.student_id == student.id,
                ).first()
                if completed:
                    continue

                if _reminder_stage(item.due_date, now, "12h"):
                    pending_count += 1
                    sent_count += int(
                        _send_item_reminder(
                            student, "assignment", item, "12h", sent, now
                        )
                    )

            # PROJECT — 20-day, 10-day, and 12-hour reminders
            projects = db.query(Project).filter(
                Project.domain_id.in_(domain_ids),
                Project.is_published == True,
                Project.due_date != None,
                Project.due_date > now,
                Project.due_date <= now + timedelta(days=20, hours=1),
            ).all()

            for item in projects:
                completed = db.query(ProjectSubmission).filter(
                    ProjectSubmission.project_id == item.id,
                    ProjectSubmission.student_id == student.id,
                ).first()
                if completed:
                    continue

                for stage in ("20d", "10d", "12h"):
                    if _reminder_stage(item.due_date, now, stage):
                        pending_count += 1
                        sent_count += int(
                            _send_item_reminder(
                                student, "project", item, stage, sent, now
                            )
                        )

        _save_sent(sent)
        result = {
            "status": "completed",
            "pending_items_checked": pending_count,
            "emails_sent": sent_count,
        }
        logger.info("Deadline reminders completed: %s", result)
        return result

    finally:
        if close_db:
            db.close()
