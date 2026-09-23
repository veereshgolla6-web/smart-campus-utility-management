@echo off
title Smart Campus - EXE Builder
cd /d "%~dp0"
py -m pip install pyinstaller
if errorlevel 1 python -m pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name SmartCampusJARVIS app.py
if errorlevel 1 python -m PyInstaller --noconfirm --clean --onefile --windowed --name SmartCampusJARVIS app.py
echo Build finished. Check the dist folder.
pause
