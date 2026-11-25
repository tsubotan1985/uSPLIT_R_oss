@echo off
title microSPLIT-R
cd /d "%~dp0"

echo ========================================
echo   microSPLIT-R - MiniPIX TPX 3ch Controller
echo ========================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Run "python -m venv venv" first, then install requirements.
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated.

echo.
echo Starting microSPLIT-R...
echo.

python src\main.py

echo.
echo microSPLIT-R has been stopped.
deactivate
pause
