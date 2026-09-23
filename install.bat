@echo off
title Smart Campus - Installation
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -m pip install --upgrade pip) else (python -m pip install --upgrade pip)
echo Installation complete. Run run.bat to start.
pause
