"""
Initialize database tables and seed default data.
Run: python -m app.database_init
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import engine, Base
from app.models import *  # noqa - register all models
from app.config import settings


def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")

    # Seed initial data
    from app.database import SessionLocal
    from app.models.user import User, UserRole, UserStatus, UserProfile
    from app.auth.jwt import get_password_hash

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if not admin:
            print(f"Creating default admin: {settings.ADMIN_EMAIL}")
            admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_DEFAULT_PASSWORD),
                role=UserRole.admin,
                status=UserStatus.approved,
                is_active=True,
            )
            db.add(admin)
            db.flush()
            profile = UserProfile(user_id=admin.id, full_name="QODEKRAFT Admin")
            db.add(profile)
            db.commit()
            print(f"✅ Default admin created: {settings.ADMIN_EMAIL}")
        else:
            print(f"ℹ️  Admin already exists: {settings.ADMIN_EMAIL}")
    finally:
        db.close()

    print("✅ Database initialization complete!")


if __name__ == "__main__":
    init_db()
