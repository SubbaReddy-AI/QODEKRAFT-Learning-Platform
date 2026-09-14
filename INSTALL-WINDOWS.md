# QODEKRAFT Installation

1. Install Docker Desktop for Windows and start it.
2. Extract this ZIP.
3. Open the extracted folder.
4. Copy `backend/.env.example` to `backend/.env` if `backend/.env` does not exist.
5. Double-click `start-qodekraft.bat`.
6. Open http://localhost:3000.
7. Backend API documentation: http://localhost:8000/docs.

For another computer on the same Wi-Fi, use the host computer IPv4 address:
`http://YOUR-COMPUTER-IP:3000`

To stop the application, double-click `stop-qodekraft.bat`.
Do not run `docker compose down -v` unless you intentionally want to delete the database volume.
