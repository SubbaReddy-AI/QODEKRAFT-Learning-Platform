# QODEKRAFT Learning Platform

Full-stack QODEKRAFT LMS with a responsive web/PWA frontend, FastAPI backend, MySQL, protected recordings, domain-based access, quizzes, assignments, projects, announcements, reports and authentication.

## Stack
- Frontend: React + Vite + Tailwind CSS
- Backend: FastAPI + SQLAlchemy + JWT authentication
- Database: MySQL 8
- Media: local filesystem under `/media`
- Roles: Admin and Student
- PWA: installable QODEKRAFT web app

## Start on Windows

```powershell
docker compose up --build -d
```
Frontend: `https://qodekraft-learning-platform.vercel.app/`
Backend health: `https://qodekraft-learning-platform.onrender.com/api/v1/health`

## Main LMS features
- Admin and student authentication
- Student approval and domain access
- Recorded classes and protected media
- Assignments and submission review
- Quizzes and results
- Projects and submission review
- Announcements
- Progress and reports
- QODEKRAFT PWA installation


## Automatic deadline reminders
QODEKRAFT checks published quizzes, assignments, and projects every day for approved students with active domain access. If an item is still incomplete, reminder emails are sent before the deadline at the configured 7-, 3-, and 1-day stages. Configure SMTP credentials and REMINDER_DAYS_BEFORE in backend/.env.


## Google Sheets student sync

The backend can synchronize student details to the configured Google Sheet.
1. Share the Google Sheet with the service-account email as Editor.
2. Place the newly generated service-account JSON at `backend/google-service-account.json` (never commit it).
3. Set `GOOGLE_SPREADSHEET_ID` and `GOOGLE_SHEET_WORKSHEET=Students` in `backend/.env`.
4. Start the stack with Docker Compose.
5. Student signup automatically upserts the student row. Admin approval/rejection also refreshes the row. The admin endpoint `POST /api/v1/admin/students/sync-to-google-sheets` can synchronize existing students.

The Sheet never receives passwords, password hashes, JWTs, or private keys.

## Reminder rules

- Quiz: one reminder at 12 hours before the deadline.
- Assignment: one reminder at 12 hours before the deadline.
- Project: reminders at 20 days, 10 days, and 12 hours before the deadline.

## Content cleanup

- Keep the latest 45 recordings active per domain.
- Older recordings enter a 15-day retention period before their media/thumbnail is deleted.
- Assignments keep active/reference media for 45 days plus an additional 15 days before media cleanup.
- Student accounts, progress, quiz results, assignment submissions, and project submissions are preserved.
