@echo off
REM Windows setup script for Telegram Raffle Bot

echo ================================
echo Telegram Raffle Bot Setup
echo ================================
echo.

REM Check Python
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)
echo OK: Python is installed
echo.

REM Create virtual environment
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo OK: Virtual environment created
) else (
    echo OK: Virtual environment already exists
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo OK: Dependencies installed
echo.

REM Create .env file
if not exist ".env" (
    echo Creating .env file...
    copy .env.example .env
    echo OK: .env file created
    echo WARNING: Please edit .env file with your credentials!
) else (
    echo OK: .env file already exists
)
echo.

REM Create logs directory
if not exist "logs" mkdir logs
echo OK: Logs directory created
echo.

echo ================================
echo Setup Complete!
echo ================================
echo.
echo Next steps:
echo 1. Install PostgreSQL from https://www.postgresql.org/download/windows/
echo 2. Install Redis from https://redis.io/download/ or use WSL
echo 3. Edit .env file with your credentials
echo 4. Run: python scripts\init_db.py
echo 5. Run: python app\main.py
echo.
pause
