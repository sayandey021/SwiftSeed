@echo off
title SwiftSeed Build System
color 0A

echo Checking dependencies...
python -c "import sys" >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

python scripts\build_system.py
pause
