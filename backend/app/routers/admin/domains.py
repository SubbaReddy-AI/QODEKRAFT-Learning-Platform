from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.domain import Domain
from app.auth.dependencies import get_current_admin
from app.models.user import User
from app.utils.file_handler import save_upload_file
from app.utils.audit import log_audit
from app.config import settings

router = APIRouter(prefix="/admin/domains", tags=["Admin - Domains"])


@router.get("")
async def list_domains(
    search: Optional[str] = Query(None),
    active_only: bool = Query(False),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Domain)
    if search:
        query = query.filter(Domain.name.ilike(f"%{search}%"))
    if active_only:
        query = query.filter(Domain.is_active == True)
    domains = query.all()
    return [_format_domain(d) for d in domains]


@router.post("", status_code=201)
async def create_domain(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    duration_weeks: Optional[int] = Form(None),
    max_active_recordings: int = Form(45),
    recording_retention_days: int = Form(15),
    image: Optional[UploadFile] = File(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    # Unique name check
    if db.query(Domain).filter(Domain.name == name).first():
        raise HTTPException(status_code=400, detail="Domain name already exists")

    slug = name.lower().replace(" ", "-").replace("_", "-")
    image_path = image_name = None

    if image:
        image_path, image_name, _, _ = await save_upload_file(
            image, settings.media_domains_path,
            allowed_extensions=["jpg", "jpeg", "png", "webp", "svg"],
        )

    domain = Domain(
        name=name,
        slug=slug,
        description=description,
        duration_weeks=duration_weeks,
        max_active_recordings=max_active_recordings,
        recording_retention_days=recording_retention_days,
        image_path=image_path,
        image_name=image_name,
        created_by=admin.id,
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    log_audit(db, "create_domain", admin.id, admin.email, "domain", domain.id)
    return _format_domain(domain)


@router.get("/{domain_id}")
async def get_domain(
    domain_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    domain = _get_domain_or_404(domain_id, db)
    return _format_domain(domain)


@router.put("/{domain_id}")
async def update_domain(
    domain_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    duration_weeks: Optional[int] = Form(None),
    max_active_recordings: Optional[int] = Form(None),
    recording_retention_days: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    domain = _get_domain_or_404(domain_id, db)

    if name: domain.name = name; domain.slug = name.lower().replace(" ", "-")
    if description is not None: domain.description = description
    if duration_weeks is not None: domain.duration_weeks = duration_weeks
    if max_active_recordings is not None: domain.max_active_recordings = max_active_recordings
    if recording_retention_days is not None: domain.recording_retention_days = recording_retention_days

    if image:
        image_path, image_name, _, _ = await save_upload_file(
            image, settings.media_domains_path,
            allowed_extensions=["jpg", "jpeg", "png", "webp", "svg"],
        )
        domain.image_path = image_path
        domain.image_name = image_name

    db.commit()
    log_audit(db, "update_domain", admin.id, admin.email, "domain", domain_id)
    return _format_domain(domain)


@router.patch("/{domain_id}/toggle-active")
async def toggle_domain_active(
    domain_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    domain = _get_domain_or_404(domain_id, db)
    domain.is_active = not domain.is_active
    db.commit()
    log_audit(db, "toggle_domain_active", admin.id, admin.email, "domain", domain_id,
              details={"is_active": domain.is_active})
    return {"message": f"Domain {'activated' if domain.is_active else 'deactivated'}", "is_active": domain.is_active}


@router.delete("/{domain_id}")
async def delete_domain(
    domain_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a domain — requires admin confirmation from frontend."""
    domain = _get_domain_or_404(domain_id, db)
    log_audit(db, "delete_domain", admin.id, admin.email, "domain", domain_id,
              details={"domain_name": domain.name})
    db.delete(domain)
    db.commit()
    return {"message": "Domain deleted successfully"}


def _get_domain_or_404(domain_id: int, db: Session) -> Domain:
    d = db.query(Domain).filter(Domain.id == domain_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Domain not found")
    return d


def _format_domain(d: Domain) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "slug": d.slug,
        "description": d.description,
        "duration_weeks": d.duration_weeks,
        "is_active": d.is_active,
        "max_active_recordings": d.max_active_recordings,
        "recording_retention_days": d.recording_retention_days,
        "image_name": d.image_name,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }
