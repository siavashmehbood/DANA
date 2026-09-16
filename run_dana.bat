@echo off
setlocal
cd /d "%~dp0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8003" ^| findstr "LISTENING"') do taskkill /PID %%P /F >nul 2>&1
.venv\Scripts\python.exe manage.py check
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8003 --noreload
