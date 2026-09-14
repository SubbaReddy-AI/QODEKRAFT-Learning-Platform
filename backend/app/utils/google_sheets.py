"""Google Sheets integration for student details.

The service-account JSON is read from a local/container-only path configured by
GOOGLE_SERVICE_ACCOUNT_FILE. Passwords and other authentication secrets are
never written to the Sheet.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from app.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
HEADERS = [
    "Student ID",
    "Full Name",
    "Email",
    "Phone",
    "Qualification",
    "Preferred Domain",
    "Status",
    "Registered At",
    "Approved At",
    "Last Login",
]


def _client() -> gspread.Client:
    credentials_path = Path(settings.GOOGLE_SERVICE_ACCOUNT_FILE)
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google service-account JSON not found: {credentials_path}"
        )
    credentials = Credentials.from_service_account_file(
        str(credentials_path), scopes=SCOPES
    )
    return gspread.authorize(credentials)


def _worksheet():
    if not settings.GOOGLE_SPREADSHEET_ID:
        raise ValueError("GOOGLE_SPREADSHEET_ID is not configured")
    client = _client()
    spreadsheet = client.open_by_key(settings.GOOGLE_SPREADSHEET_ID)
    try:
        worksheet = spreadsheet.worksheet(settings.GOOGLE_SHEET_WORKSHEET)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=settings.GOOGLE_SHEET_WORKSHEET, rows=1000, cols=len(HEADERS)
        )
    values = worksheet.get_all_values()
    if not values:
        worksheet.append_row(HEADERS, value_input_option="USER_ENTERED")
    elif values[0][:len(HEADERS)] != HEADERS:
        # Only create the expected header row when the sheet is genuinely empty.
        # Existing user data is never overwritten automatically.
        logger.warning(
            "Google Sheet '%s' has an existing header layout; using it as-is.",
            settings.GOOGLE_SHEET_WORKSHEET,
        )
    return worksheet


def _value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _student_row(student) -> list[str]:
    profile = student.profile
    return [
        _value(student.id),
        _value(profile.full_name if profile else ""),
        _value(student.email),
        _value(student.phone),
        _value(profile.qualification if profile else ""),
        _value(profile.preferred_domain if profile else ""),
        _value(getattr(student.status, "value", student.status)),
        _value(student.created_at),
        _value(profile.approved_at if profile else None),
        _value(student.last_login_at),
    ]


def sync_student_to_google_sheet(student) -> bool:
    """Upsert one student row by Student ID.

    Returns True when the row was written successfully. Errors are raised so
    callers can decide whether to fail or merely log the integration failure.
    """
    worksheet = _worksheet()
    row = _student_row(student)
    values = worksheet.get_all_values()

    id_column = 1
    existing_row = None
    for index, existing in enumerate(values[1:], start=2):
        if existing and existing[0].strip() == row[0]:
            existing_row = index
            break

    if existing_row:
        worksheet.update(
            f"A{existing_row}:{chr(64 + len(row))}{existing_row}",
            [row],
            value_input_option="USER_ENTERED",
        )
    else:
        worksheet.append_row(row, value_input_option="USER_ENTERED")
    return True


def sync_students_to_google_sheet(students) -> dict:
    """Upsert a collection of students and return a summary."""
    synced = 0
    failed = 0
    errors = []
    for student in students:
        try:
            sync_student_to_google_sheet(student)
            synced += 1
        except Exception as exc:  # integration must not destroy DB workflow
            failed += 1
            errors.append(f"student {getattr(student, 'id', '?')}: {exc}")
            logger.exception("Google Sheets sync failed")
    return {"synced": synced, "failed": failed, "errors": errors}
