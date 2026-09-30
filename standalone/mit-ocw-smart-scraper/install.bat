@echo off
REM MIT OCW Smart Scraper Installation Script for Windows
REM Automates setup process

setlocal ENABLEDELAYEDEXPANSION

echo ==================================
echo MIT OCW Smart Scraper Setup
echo ==================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

echo [OK] Virtual environment created
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip and install dependencies
echo Upgrading pip and installing dependencies...
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [OK] Dependencies installed
echo.

REM Ask about optional features
echo Optional Features:
echo.

set /p install_selenium="Install Selenium for better course discovery? (y/n): "
if /i "%install_selenium%"=="y" (
    echo Installing Selenium...
    pip install selenium webdriver-manager
    echo [OK] Selenium installed
)

echo.
set /p install_whisper="Install Whisper for audio transcription? (y/n): "
if /i "!install_whisper!"=="y" (
    echo.
    echo [WARNING] Whisper requires FFmpeg
    echo Download from: https://www.gyan.dev/ffmpeg/builds/
    echo.
    set /p continue_whisper="Continue with Whisper installation? (y/n): "

    if /i "!continue_whisper!"=="y" (
        echo Installing Whisper...
        pip install openai-whisper

        echo.
        set /p has_gpu="Do you have an NVIDIA GPU? (y/n): "
        if /i "!has_gpu!"=="y" (
            echo Installing PyTorch with CUDA support...
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        ) else (
            echo Installing PyTorch CPU-only...
            pip install torch torchvision torchaudio
        )
        echo [OK] Whisper installed
    ) else (
        set "install_whisper=n"
    )
)

echo.
set /p install_pdf="Install additional PDF tools? (y/n): "
if /i "%install_pdf%"=="y" (
    echo Installing PDF tools...
    pip install PyMuPDF Pillow
    echo [OK] PDF tools installed
)

echo.
set /p install_tests="Install testing tools? (y/n): "
if /i "%install_tests%"=="y" (
    echo Installing testing tools...
    pip install pytest pytest-cov pytest-mock
    echo [OK] Testing tools installed
)

REM Create config file
echo.
echo Creating default config file...
if not exist config.yaml (
    if exist config.example.yaml (
        copy /Y config.example.yaml config.yaml >nul
        echo [OK] Copied config.example.yaml to config.yaml
    ) else (
        echo [WARN] config.example.yaml not found. Creating minimal config.
        (
            echo output:
            echo   base_directory: "MIT_OCW_Courses"
        ) > config.yaml
    )
) else (
    echo [SKIP] Config file already exists
)

REM Create output directory
echo.
echo Creating output directory...
if not exist MIT_OCW_Courses mkdir MIT_OCW_Courses
echo [OK] Output directory created

REM Create activation script
echo.
echo Creating activation script...
(
    echo @echo off
    echo call venv\Scripts\activate.bat
    echo echo Virtual environment activated
    echo echo Run: python smart_scraper.py --help
) > activate.bat
echo [OK] Activation script created

echo.
echo ==================================
echo Installation Complete!
echo ==================================
echo.
echo Next steps:
echo   1. activate.bat
echo   2. python smart_scraper.py --self-test
echo      (check MIT_OCW_Courses\scraper.log for [FAIL]/[WARN])
echo   3. python smart_scraper.py "https://ocw.mit.edu/search/?d=Physics"
echo.
echo Configuration: config.yaml
echo Output: MIT_OCW_Courses\
echo.
echo Press any key to exit...
pause >nul
endlocal
