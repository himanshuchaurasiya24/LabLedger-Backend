@echo off
REM Change directory to where manage.py is (adjust if needed)
cd /d %~dp0

REM Activate virtual environment
call .\.venv\Scripts\activate.bat

REM Run the Django development server
python manage.py runserver

REM Keep the window open
pause
