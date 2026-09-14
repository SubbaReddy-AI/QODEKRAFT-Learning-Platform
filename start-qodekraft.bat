@echo off
cd /d "%~dp0"
echo Starting QODEKRAFT Learning Platform...
docker compose up --build -d
if errorlevel 1 pause & exit /b 1
echo.
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000/docs
echo Network:  http://%COMPUTERNAME%:3000
pause
