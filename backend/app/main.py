"""
QODEKRAFT Learning Platform — FastAPI Backend
Main application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.config import settings
from app.database import engine, Base
from app.utils.file_handler import ensure_media_dirs

# Import all models to register them with SQLAlchemy
from app.models import *  # noqa: F401,F403

# Import routers
from app.routers.auth import router as auth_router
from app.routers.admin.students import router as admin_students_router
from app.routers.admin.domains import router as admin_domains_router
from app.routers.admin.recordings import router as admin_recordings_router
from app.routers.admin.quizzes import router as admin_quizzes_router
from app.routers.admin.assignments import router as admin_assignments_router

from app.routers.admin.settings import (
    router as admin_settings_router,
    audit_router,
    cleanup_router,
    dashboard_router as admin_dashboard_router,
)

from app.routers.student.recordings import router as student_recordings_router

from app.routers.student.quizzes import (
    quiz_router as student_quizzes_router,
    assignment_router as student_assignments_router,
)

from app.routers.student.content import router as student_content_router

from app.routers.admin.projects import router as admin_projects_router
from app.routers.admin.announcements import router as admin_announcements_router

from app.routers.student.progress import (
    router as student_progress_router,
    dashboard_router as student_dashboard_router,
)


# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("qodekraft")


# ------------------------------------------------------------
# Application Lifespan
# ------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""

    logger.info("Starting QODEKRAFT Learning Platform Backend...")

    # Ensure media directories exist
    try:
        ensure_media_dirs()
        logger.info("Media directories verified")
    except Exception:
        logger.exception("Failed to create media directories")
        raise

    # Create all database tables BEFORE checking/updating columns.
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified")
    except Exception:
        logger.exception("Database table creation failed")
        raise

    # Add quiz due_date column if the quizzes table exists
    # and the column is missing.
    try:
        with engine.begin() as connection:
            quiz_columns = connection.execute(
                text("SHOW COLUMNS FROM quizzes LIKE 'due_date'")
            ).fetchall()

            if not quiz_columns:
                connection.execute(
                    text(
                        "ALTER TABLE quizzes "
                        "ADD COLUMN due_date DATETIME NULL"
                    )
                )

        logger.info("Quiz due_date column verified")

    except Exception:
        logger.exception("Failed to verify quiz due_date column")
        raise

    # Seed default admin and data
    try:
        await _seed_initial_data()
        logger.info("Initial data verified")
    except Exception:
        logger.exception("Initial data setup failed")
        raise

    # Start background cleanup scheduler
    try:
        from app.tasks.cleanup import setup_scheduler

        setup_scheduler(app)
        logger.info("Background cleanup scheduler started")
    except Exception:
        logger.exception("Failed to start cleanup scheduler")
        raise

    yield

    logger.info("QODEKRAFT Backend shutting down...")


# ------------------------------------------------------------
# Seed Initial Data
# ------------------------------------------------------------

async def _seed_initial_data():
    """Create default admin if it does not already exist."""

    from app.database import SessionLocal
    from app.models.user import (
        User,
        UserRole,
        UserStatus,
        UserProfile,
    )
    from app.auth.jwt import get_password_hash

    db = SessionLocal()

    try:
        admin = (
            db.query(User)
            .filter(User.email == settings.ADMIN_EMAIL)
            .first()
        )

        if not admin:
            logger.info(
                "Creating default admin: %s",
                settings.ADMIN_EMAIL,
            )

            admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(
                    settings.ADMIN_DEFAULT_PASSWORD
                ),
                role=UserRole.admin,
                status=UserStatus.approved,
                is_active=True,
            )

            db.add(admin)
            db.flush()

            profile = UserProfile(
                user_id=admin.id,
                full_name="QODEKRAFT Admin",
            )

            db.add(profile)
            db.commit()

            logger.info("Default admin created")

        else:
            logger.info(
                "Default admin already exists: %s",
                settings.ADMIN_EMAIL,
            )

    except Exception:
        db.rollback()
        logger.exception("Failed to seed initial data")
        raise

    finally:
        db.close()


# ------------------------------------------------------------
# Create FastAPI Application
# ------------------------------------------------------------

app = FastAPI(
    title="QODEKRAFT Learning Platform API",
    description=(
        "Private online learning platform with RBAC, "
        "protected video streaming, and comprehensive LMS features."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# Routers
# ------------------------------------------------------------

app.include_router(auth_router, prefix="/api/v1")

app.include_router(
    admin_students_router,
    prefix="/api/v1",
)

app.include_router(
    admin_domains_router,
    prefix="/api/v1",
)

app.include_router(
    admin_recordings_router,
    prefix="/api/v1",
)

app.include_router(
    admin_quizzes_router,
    prefix="/api/v1",
)

app.include_router(
    admin_assignments_router,
    prefix="/api/v1",
)

app.include_router(
    admin_settings_router,
    prefix="/api/v1",
)

app.include_router(
    audit_router,
    prefix="/api/v1",
)

app.include_router(
    cleanup_router,
    prefix="/api/v1",
)

app.include_router(
    admin_dashboard_router,
    prefix="/api/v1",
)

app.include_router(
    student_recordings_router,
    prefix="/api/v1",
)

app.include_router(
    student_quizzes_router,
    prefix="/api/v1",
)

app.include_router(
    student_assignments_router,
    prefix="/api/v1",
)

app.include_router(
    student_progress_router,
    prefix="/api/v1",
)

app.include_router(
    student_dashboard_router,
    prefix="/api/v1",
)

app.include_router(
    student_content_router,
    prefix="/api/v1",
)

app.include_router(
    admin_projects_router,
    prefix="/api/v1",
)

app.include_router(
    admin_announcements_router,
    prefix="/api/v1",
)


# ------------------------------------------------------------
# Health Check
# ------------------------------------------------------------

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
    }


# ------------------------------------------------------------
# Root
# ------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "message": "QODEKRAFT Learning Platform API",
        "docs": "/docs",
    }