@echo off
REM Wallpaper watcher - runs in background
REM Close this window, the watcher will continue running

echo Starting Wallpaper Watcher...
echo The watcher will run in the background.
echo You will receive notifications when colors update.
echo.

start "" pythonw "%~dp0wallpaper_watcher.py"

echo Watcher started!
echo.
echo To stop: Open Task Manager and end 'pythonw.exe'
timeout /t 3 >nul
