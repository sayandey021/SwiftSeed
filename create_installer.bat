@echo off
echo Checking for Inno Setup Compiler...
where iscc >nul 2>nul
if %errorlevel% neq 0 (
    echo Inno Setup Compiler (ISCC.exe) not found in PATH.
    echo Please install Inno Setup and make sure it's in your PATH, or open 'installer_script.iss' manually.
    pause
    exit /b
)

echo Compiling installer...
iscc installer_script.iss

if %errorlevel% neq 0 (
    echo Compilation failed!
    pause
    exit /b
)

echo.
echo Installer created successfully in the 'installer' directory!
pause
