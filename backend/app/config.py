from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "QODEKRAFT Learning Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str

    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Admin
    ADMIN_EMAIL: str = "admin@qodekraft.com"
    ADMIN_DEFAULT_PASSWORD: str

    # CORS
    ALLOWED_ORIGINS: str = "https://qodekraft-learning-platform.vercel.app,http://localhost:5173,http://localhost:3000"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # Media
    MEDIA_ROOT: str = "../media"
    MAX_UPLOAD_SIZE_MB: int = 500

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@qodekraft.com"
    SMTP_FROM_NAME: str = "QODEKRAFT Platform"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False

    # Rate limiting
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_PERIOD_SECONDS: int = 900

    # Cleanup
    CLEANUP_JOB_HOUR: int = 2
    CLEANUP_JOB_MINUTE: int = 0

    # Deadline reminder email
    REMINDER_JOB_HOUR: int = 9
    REMINDER_JOB_MINUTE: int = 0
    REMINDER_HOURS_BEFORE: int = 12

    # Frontend URL
    FRONTEND_URL: str = "https://qodekraft-learning-platform.vercel.app"

    # Google Sheets — student details
    GOOGLE_SPREADSHEET_ID: str = ""
    GOOGLE_SHEET_WORKSHEET: str = "Sheet1"
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "./google-service-account.json"


    @property
    def media_recordings_path(self) -> str:
        return os.path.join(self.MEDIA_ROOT, "recordings")

    @property
    def media_thumbnails_path(self) -> str:
        return os.path.join(self.MEDIA_ROOT, "thumbnails")

    @property
    def media_assignments_path(self) -> str:
        return os.path.join(self.MEDIA_ROOT, "assignments")

    @property
    def media_projects_path(self) -> str:
        return os.path.join(self.MEDIA_ROOT, "projects")

    @property
    def media_quizzes_path(self) -> str:
        return os.path.join(self.MEDIA_ROOT, "quizzes")

    @property
    def media_resources_path(self) -> str:
        return os.path.join(self.MEDIA_ROOT, "resources")

    @property
    def media_profiles_path(self) -> str:
        return os.path.join(self.MEDIA_ROOT, "profiles")

    @property
    def media_domains_path(self) -> str:
        return os.path.join(self.MEDIA_ROOT, "domains")

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()

