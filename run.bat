@echo off
echo ===== Startup-HUB Application Runner =====
echo.

REM Check if virtual environment exists
if exist .venv\Scripts\activate.bat (
    echo Virtual environment found, activating...
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found, creating new one...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing requirements...
    pip install -r requirements.txt
)

echo.
echo Running Startup-HUB application...
echo.

REM Run the application
python -m reflex run

REM Keep the window open on error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error running application. Press any key to exit...
    pause > nul
) 