@echo off
setlocal enabledelayedexpansion

echo ---------------------------------
echo Running Django REST Framework setup...
echo ---------------------------------

REM Step 1: Check for Python
echo Step 1: (Internet Required) Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not added to PATH.
    goto pause
) else (
    echo [OK] Python is installed.
)

REM Step 2: Create virtual environment
echo Step 2: Creating virtual environment (venv)...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        goto pause
    )
    echo [OK] Virtual environment 'venv' created.
) else (
    echo [INFO] Virtual environment 'venv' already exists. Skipping creation.
)

REM Step 3: Install dependencies
echo Step 3: Installing dependencies from requirements.txt...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m pip install --upgrade pip >nul
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies. Check if requirements.txt exists and is valid.
        goto pause
    )
    echo [OK] Dependencies installed successfully.
) else (
    echo [ERROR] Could not find venv\Scripts\python.exe. Virtual environment may be corrupted.
    goto pause
)

REM Step 4: Stop existing server on port 8000
echo Step 4: Checking if server is running on port 8000...
set "foundProcess="
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    set "foundProcess=%%a"
)
if defined foundProcess (
    echo [INFO] Server is running on port 8000 (PID: !foundProcess!). Attempting to stop it...
    taskkill /PID !foundProcess! /F >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Failed to stop server process.
    ) else (
        echo [OK] Server stopped.
    )
) else (
    echo [INFO] Server is not running on port 8000. All good.
)

REM Step 5: Run Django migrations
echo Step 5: Running Django makemigrations and migrate...
cd /d "%~dp0"
call venv\Scripts\activate.bat
python manage.py makemigrations
if errorlevel 1 (
    echo [ERROR] makemigrations failed. Check your models and settings.
    goto pause
)
python manage.py migrate
if errorlevel 1 (
    echo [ERROR] migrate failed. Check your database configuration.
    goto pause
)
echo [OK] Database migrations applied.

echo ---------------------------------
echo [SUCCESS] SETUP COMPLETE!
echo You can now run the server by double-clicking 'run_server.bat'.
echo ---------------------------------

:pause
echo.
echo Press any key to exit...
pause >nul
