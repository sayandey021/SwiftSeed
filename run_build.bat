@echo off
echo ============================================================
echo   SwiftSeed Distribution Builder
echo ============================================================
echo.
echo This will create:
echo 1. Portable Folder (dist/SwiftSeed)
echo 2. Portable ZIP
echo 3. EXE Setup Installer
echo 4. MSIX Package
echo.
python build_distribution.py
echo.
echo Build process finished. Check the dist/ and installer/ folders.
pause
