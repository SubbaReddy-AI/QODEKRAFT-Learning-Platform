from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from typing import Optional
import json


def log_audit(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
):
    """Create an audit log entry."""
    log = AuditLog(
        user_id=user_id,
        user_email=user_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
    )
    db.add(log)
    db.commit()


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "system",
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
):
    """Create a notification for a user."""
    from app.models.audit import Notification
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(notif)
    db.commit()
    return notif
