@echo off
setlocal enabledelayedexpansion

echo ---------------------------------
echo Starting Django REST Framework Server
echo ---------------------------------

REM Step 1: Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Please run setup.bat to initialize the environment.
    goto pause
)

REM Step 2: Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    echo Please double-click setup.bat to fix the issue.
    goto pause
)

REM Step 3: Start Django server
echo [OK] Virtual environment activated.
echo ---------------------------------
echo Starting Django development server on http://127.0.0.1:8000
echo To stop the server, press CTRL+C in this window.
echo If you see errors, double-click setup.bat to fix dependencies.
echo ---------------------------------

python manage.py runserver
if errorlevel 1 (
    echo.
    echo [ERROR] Server failed to start.
    echo Please double-click setup.bat to fix any missing dependencies or configuration issues.
)

:pause
echo.
echo Press any key to exit...
pause >nul
