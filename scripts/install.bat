@echo off
REM PodKnow Installation Script for Windows
REM Supports both pip and uv package managers

setlocal enabledelayedexpansion

REM Configuration
set PYTHON_VERSION=3.13
set VENV_NAME=podknow-env
set PROJECT_NAME=podknow

REM Colors (limited support in Windows)
set INFO=[INFO]
set SUCCESS=[SUCCESS]
set WARNING=[WARNING]
set ERROR=[ERROR]

echo %INFO% Starting PodKnow installation for Windows...

REM Function to check if command exists
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo %ERROR% Python not found in PATH
    echo %INFO% Please install Python 3.13 from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo %INFO% Found Python version: %PYTHON_VER%

REM Extract major.minor version
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VER%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if not "%MAJOR%.%MINOR%"=="3.13" (
    echo %ERROR% Python 3.13 is required, but found Python %PYTHON_VER%
    echo %INFO% Please install Python 3.13 from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo %SUCCESS% Python 3.13 confirmed

REM Check for uv package manager
where uv >nul 2>nul
if %errorlevel% equ 0 (
    set USE_UV=1
    echo %INFO% Found uv package manager - using uv for faster installation
) else (
    set USE_UV=0
    echo %INFO% Using pip package manager
)

REM Create virtual environment
echo %INFO% Creating virtual environment...
if %USE_UV%==1 (
    uv venv %VENV_NAME% --python python
) else (
    python -m venv %VENV_NAME%
)

if %errorlevel% neq 0 (
    echo %ERROR% Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
echo %INFO% Activating virtual environment...
call %VENV_NAME%\Scripts\activate.bat

REM Upgrade pip if using pip
if %USE_UV%==0 (
    echo %INFO% Upgrading pip...
    python -m pip install --upgrade pip setuptools wheel
)

REM Install PodKnow
echo %INFO% Installing PodKnow and dependencies...
if %USE_UV%==1 (
    uv pip install -e ".[standard,dev]"
) else (
    pip install -e ".[standard,dev]"
)

if %errorlevel% neq 0 (
    echo %ERROR% Installation failed
    pause
    exit /b 1
)

REM Verify installation
echo %INFO% Verifying installation...
where podknow >nul 2>nul
if %errorlevel% neq 0 (
    echo %ERROR% PodKnow CLI not found in PATH
    pause
    exit /b 1
)

echo %SUCCESS% PodKnow CLI is available
podknow --version

REM Test basic functionality
podknow --help >nul 2>nul
if %errorlevel% neq 0 (
    echo %ERROR% PodKnow CLI test failed
    pause
    exit /b 1
)

echo %SUCCESS% PodKnow installation completed successfully!
echo.
echo %INFO% To activate the environment in future sessions, run:
echo   %VENV_NAME%\Scripts\activate.bat
echo.
echo %INFO% To get started, run:
echo   podknow --help
echo.
pause