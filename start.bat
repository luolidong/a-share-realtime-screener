@echo off
cd /d "%~dp0"

echo Starting A-share realtime screener...
docker compose up -d
if errorlevel 1 (
  echo.
  echo Start failed. Please make sure Docker Desktop is running.
  pause
  exit /b 1
)

echo.
docker compose ps
echo.
echo Started. Open: http://127.0.0.1:8080
pause
