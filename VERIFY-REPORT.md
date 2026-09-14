# QODEKRAFT Verification Report

This project contains the LMS modules currently used by QODEKRAFT: authentication, students, domains, recordings, assignments, quizzes, projects, announcements, reports, progress and settings.

The retired code-execution module has been removed from the application, backend routes, database models, Docker configuration and documentation.

The frontend includes PWA installation metadata and the QODEKRAFT install control in the top search bar.

Recommended verification after extraction:

```powershell
docker compose down
docker compose build --no-cache backend frontend
docker compose up -d

docker compose ps
```

Then open `http://localhost:3000` and test Admin Assignments and Student Assignments.
