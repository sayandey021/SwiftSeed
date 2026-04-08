@echo off
title SwiftSeed - Test Any Torrent Site
color 0A

:menu
cls
echo ========================================================
echo        SwiftSeed - Test Any Torrent Site
echo ========================================================
echo.
echo Enter a torrent site URL to test if it works with the app.
echo Example: https://1337x.to or https://yts.mx
echo.
echo Type 'exit' to quit.
echo.
set /p url="Enter URL: "

if /i "%url%"=="exit" goto end

echo.
echo Testing %url%...
echo.

python test_site.py "%url%"

echo.
pause
goto menu

:end
echo Goodbye!
