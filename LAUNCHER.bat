@echo off
setlocal EnableDelayedExpansion

:: Set window title and colors
title Genesis Grades Dashboard - Launcher
color 0A

echo.
echo ==========================================
echo     GENESIS GRADES DASHBOARD
echo ==========================================
echo.
echo Starting up...
echo.

:: Check if Python is installed
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed!
    echo.
    echo Please install Python 3.7 or newer from:
    echo https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During installation, check the box that says
    echo    "Add Python to PATH" or "Add Python to environment variables"
    echo.
    echo After installing Python, run this launcher again.
    echo.
    pause
    exit /b 1
)
echo Python found!

:: Check if we're in the right directory
echo [2/4] Checking project files...
if not exist "main.py" (
    echo.
    echo ERROR: main.py not found!
    echo Make sure you extracted all files and are running this from the correct folder.
    echo.
    pause
    exit /b 1
)
if not exist "requirements.txt" (
    echo.
    echo ERROR: requirements.txt not found!
    echo Make sure you extracted all files from the ZIP.
    echo.
    pause
    exit /b 1
)
echo Project files found!

:: Install/update dependencies
echo [3/4] Installing required packages...
echo (This may take a minute on first run)

:: Try multiple installation methods
echo Attempting installation method 1...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo Method 1 failed, trying method 2...
    python -m pip install -r requirements.txt >nul 2>&1
    if errorlevel 1 (
        echo Method 2 failed, trying method 3...
        python -m pip install --user -r requirements.txt >nul 2>&1
        if errorlevel 1 (
            echo.
            echo ERROR: All installation methods failed!
            echo.
            echo Please try running this command manually:
            echo python -m pip install -r requirements.txt
            echo.
            echo If that doesn't work, try:
            echo python -m pip install --user -r requirements.txt
            echo.
            pause
            exit /b 1
        )
    )
)

:: Verify installation by testing import
echo Verifying package installation...
python -c "import requests, bs4, lxml, dotenv, webview" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Packages installed but not accessible. Trying to fix...
    echo.
    echo Force installing packages...
    python -m pip install --force-reinstall -r requirements.txt
    
    :: Test again
    python -c "import requests, bs4, lxml, dotenv, webview" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ERROR: Required packages are still not working!
        echo.
        echo This might be a Python environment issue.
        echo Try these commands manually:
        echo.
        echo python -m pip install --upgrade pip
        echo python -m pip install -r requirements.txt
        echo.
        echo If you're still having issues, you might need to:
        echo 1. Reinstall Python from python.org
        echo 2. Make sure to check "Add Python to PATH"
        echo 3. Restart your computer after installation
        echo.
        pause
        exit /b 1
    )
)
echo Packages installed and verified!

:: Launch the application
echo [4/4] Starting Genesis Grades Dashboard...
echo.
echo Launching dashboard...
echo.
echo  On first run, you'll need to enter your Genesis credentials.
echo    They will be saved securely for future use.
echo.

:: Run the main application
python main.py

:: Handle exit
echo.
echo.
if errorlevel 1 (
    echo Application exited with an error.
    echo Check the messages above for details.
) else (
    echo Application closed normally.
)
echo.
echo Press any key to close this window...
pause >nul