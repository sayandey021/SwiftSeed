@echo off
title SwiftSeed Build System
color 0A

:MENU
cls
echo ========================================================================
echo                    SwiftSeed Build System
echo ========================================================================
echo.
echo  Select build operation:
echo.
echo   [1] Build Portable Version Only (Folder + ZIP)
echo   [2] Build Windows Installer Only (Requires existing Portable build)
echo   [3] Build EVERYTHING (Portable + Installer)
echo   [4] Build MSIX Package for Microsoft Store
echo   [5] Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto BUILD_PORTABLE
if "%choice%"=="2" goto BUILD_INSTALLER
if "%choice%"=="3" goto BUILD_ALL
if "%choice%"=="4" goto BUILD_MSIX
if "%choice%"=="5" exit
echo.
echo Invalid choice. Please try again.
timeout /t 2 >nul
goto MENU

:BUILD_PORTABLE
call :FUNC_BUILD_PORTABLE
if %errorlevel% neq 0 goto ERROR
goto END

:BUILD_INSTALLER
call :FUNC_BUILD_INSTALLER
if %errorlevel% neq 0 goto ERROR
goto END

:BUILD_ALL
call :FUNC_BUILD_PORTABLE
if %errorlevel% neq 0 goto ERROR
call :FUNC_BUILD_INSTALLER
if %errorlevel% neq 0 goto ERROR
goto END

:BUILD_MSIX
call :FUNC_BUILD_MSIX
if %errorlevel% neq 0 goto ERROR
goto END


:FUNC_BUILD_PORTABLE
echo.
echo ========================================================================
echo  Building Portable Application...
echo ========================================================================
python build_complete.py
if %errorlevel% neq 0 (
    echo.
    echo  BUILD FAILED!
    echo  The portable build encountered an error.
    exit /b 1
)
exit /b 0

:FUNC_BUILD_INSTALLER
if not exist "dist\SwiftSeed\SwiftSeed.exe" (
    echo.
    echo  ERROR: Portable build not found at dist\SwiftSeed\SwiftSeed.exe
    echo  You must build the portable version before creating an installer.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo  Creating Windows Installer...
echo ========================================================================
set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "%ISCC_PATH%" (
    "%ISCC_PATH%" installer_script.iss
    if %errorlevel% neq 0 (
        echo   ✗ Installer build failed
        exit /b 1
    ) else (
        echo   ✓ Installer created successfully!
    )
) else (
    echo   ! Inno Setup not found at: %ISCC_PATH%
    echo   ! Installer creation skipped
    echo.
    echo   To create installer manually:
    echo   1. Install Inno Setup 6 from https://jrsoftware.org/isdl.php
    echo   2. Run: "%ISCC_PATH%" installer_script.iss
)
exit /b 0



:FUNC_BUILD_MSIX
echo.
echo ========================================================================
echo  Building MSIX Package for Microsoft Store...
echo ========================================================================

REM Check if portable build exists
if not exist "dist\SwiftSeed\SwiftSeed.exe" (
    echo.
    echo  ERROR: Portable build not found at dist\SwiftSeed\SwiftSeed.exe
    echo  You must build the portable version first.
    echo.
    pause
    exit /b 1
)

REM Check for Windows SDK
set "SDK_BASE=C:\Program Files (x86)\Windows Kits\10\bin"
set "MAKEAPPX_EXE="
set "SIGNTOOL_EXE="

REM Try to find the latest SDK version
for /d %%i in ("%SDK_BASE%\10.0.*") do (
    if exist "%%i\x64\MakeAppx.exe" (
        set "MAKEAPPX_EXE=%%i\x64\MakeAppx.exe"
        set "SIGNTOOL_EXE=%%i\x64\SignTool.exe"
    )
)

if not exist "%MAKEAPPX_EXE%" (
    echo.
    echo  ERROR: Windows SDK not found!
    echo  MakeAppx.exe is required to create MSIX packages.
    echo.
    echo  Please install Windows SDK from:
    echo  https://developer.microsoft.com/windows/downloads/windows-sdk/
    echo.
    echo  Required components:
    echo  - App Certification Kit
    echo  - Windows App SDK
    echo.
    pause
    exit /b 1
)

echo      Found Windows SDK tools
echo    - MakeAppx: %MAKEAPPX_EXE%

REM Create package directory structure
set "PKG_ROOT=msix_package"
set "PKG_ASSETS=%PKG_ROOT%\Assets"

echo    Cleaning package directory...
if exist "%PKG_ROOT%" rd /s /q "%PKG_ROOT%"
mkdir "%PKG_ROOT%"
mkdir "%PKG_ASSETS%"

echo    Copying application files...
xcopy /E /I /Y /Q "dist\SwiftSeed\*" "%PKG_ROOT%\" >nul
if %errorlevel% neq 0 (
    echo   ✗ Failed to copy application files
    exit /b 1
)

echo    Copying manifest...
if not exist "..\store\AppxManifest_TEMPLATE.xml" (
    echo   ✗ AppxManifest_TEMPLATE.xml not found in store folder
    exit /b 1
)
copy /Y "..\store\AppxManifest_TEMPLATE.xml" "%PKG_ROOT%\AppxManifest.xml" >nul

echo    Updating executable icon...
if exist "rcedit.exe" (
    "rcedit.exe" "%PKG_ROOT%\SwiftSeed.exe" --set-icon "src\assets\icon.ico"
)

echo    Preparing logo assets...
REM Use PowerShell script to create properly sized MSIX assets from icon.ico
powershell -ExecutionPolicy Bypass -File "create_msix_assets.ps1" -IconPath "src\assets\icon.ico" -OutputDir "%PKG_ASSETS%"
if %errorlevel% neq 0 (
    echo   ✗ Failed to create MSIX assets
    exit /b 1
)

echo    Creating MSIX package...
if not exist "installer" mkdir "installer"
set "OUTPUT_MSIX=installer\SwiftSeed.msix"
"%MAKEAPPX_EXE%" pack /d "%PKG_ROOT%" /p "%OUTPUT_MSIX%" /l /o >nul 2>&1
if %errorlevel% neq 0 (
    echo   ✗ MSIX package creation failed!
    echo.
    echo   Running with detailed output for debugging:
    "%MAKEAPPX_EXE%" pack /d "%PKG_ROOT%" /p "%OUTPUT_MSIX%" /l
    echo.
    pause
    exit /b 1
)

echo.
echo  ========================================================================
echo   ✓ MSIX PACKAGE CREATED SUCCESSFULLY!
echo  ========================================================================
echo.
echo   Package: %OUTPUT_MSIX%
echo   Size: 
for %%A in ("%OUTPUT_MSIX%") do echo   %%~zA bytes
echo.
echo  IMPORTANT NOTES:
echo  ════════════════════════════════════════════════════════════════════════
echo.
echo  Before Microsoft Store Submission:
echo  1. Update AppxManifest.xml with Publisher ID from Partner Center
echo  2. Update Identity Name with your reserved app name
echo  3. Increment Version number for each submission
echo.
echo  Testing the Package:
echo    Enable Developer Mode in Windows Settings
echo    Run: Add-AppxPackage -Path "%OUTPUT_MSIX%"
echo    Test app functionality
echo    Run: Get-AppxPackage SwiftSeed* ^| Remove-AppxPackage (to uninstall)
echo.
echo  Validation (RECOMMENDED):
echo    Run Windows App Certification Kit (WACK) before submission
echo    Find WACK at: 
echo    "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe"
echo.
echo  For Store Submission:
echo    NO need to sign the package (Microsoft signs it)
echo    Upload the UNSIGNED .msix file to Partner Center
echo    See ..\store\PACKAGE_AND_CERTIFICATE_GUIDE.md for details
echo.
pause
exit /b 0



:ERROR
echo.
echo ========================================================================
echo  BUILD PROCESS STOPPED DUE TO ERROR
echo ========================================================================
pause
goto MENU

:END
echo.
echo ========================================================================
echo                         OPERATION COMPLETE
echo ========================================================================
echo.
pause
goto MENU
