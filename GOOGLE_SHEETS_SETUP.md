# QODEKRAFT Google Sheets setup

The application writes **student details only** to the configured Google Sheet. It never writes passwords, password hashes, JWTs, or private keys.

## Configuration

Google Sheet ID:
`1CjrABpOXK-1aEj16YWyNKHtdnakCL7tscFB9kjqQ8`

Worksheet/tab:
`Sheet1`

Service-account email:
`qodekraft-excel@qodekraft-excel.iam.gserviceaccount.com`

## Credential file

Create a fresh service-account JSON key in Google Cloud and place it locally at:

`backend/google-service-account.json`

This file is ignored by Git and must not be committed or shared. Docker mounts it read-only at `/run/secrets/google-service-account.json`.

## What is written

The first row is initialized with:

- Student ID
- Full Name
- Email
- Phone
- Qualification
- Preferred Domain
- Status
- Registered At
- Approved At
- Last Login

A student signup creates/updates the row. Admin approval/rejection refreshes the same row. Existing students can be synchronized through `POST /api/v1/admin/students/sync-to-google-sheets`.

## Reminder rules

- Quiz: **12 hours before deadline only**.
- Assignment: **12 hours before deadline only**.
- Project: **20 days, 10 days, and 12 hours before deadline**.

The scheduler checks reminder windows hourly and records sent reminders in the existing `media/reminders/sent.json` state file.

## Cleanup rules

- Latest **45 recordings** per domain stay active.
- Older recordings enter the configured **15-day retention** period; then only recording media/thumbnails are deleted.
- Assignments use **45 days + 15 additional days** before assignment reference media cleanup.
- Student accounts and progress are preserved; quiz results, assignment submissions, and project submissions are not automatically deleted.
