@echo off
cd /d "%~dp0"

echo Stopping A-share realtime screener...
docker compose down
if errorlevel 1 (
  echo.
  echo Stop failed. Please check Docker Desktop.
  pause
  exit /b 1
)

echo.
echo Stopped.
pause
