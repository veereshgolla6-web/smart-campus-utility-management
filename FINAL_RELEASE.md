# JARVIS Smart Campus Utility Management System — Final Release

## Release
**Version 50 — FINAL**

## Finalization checklist
- V1–V50 feature roadmap completed
- Tkinter desktop application retained
- CSV data storage retained
- Audit and notification systems retained
- Backup/restore retained
- JARVIS analytics, command and automation retained
- V41–V50 final evolution center added
- Windows launcher added
- Windows installation helper added
- PyInstaller packaging helper added
- Final health-check utility added

## Run from source
1. Install Python 3.10 or newer.
2. Run install.bat.
3. Run run.bat.

## Build a Windows executable
1. Run build_exe.bat.
2. The executable is generated under dist/SmartCampusJARVIS.exe.

## Release verification
Run: python health_check.py

The health checker validates required source files, Python syntax, data-store directories, and report storage.

## Production deployment
- Use a dedicated Windows PC/server for the application.
- Maintain scheduled backups of data and backups directories.
- Create individual user accounts instead of shared credentials.
- Review audit records regularly.
- Test restore procedures before institutional deployment.
