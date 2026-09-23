# Smart Campus Utility Management System - Version 10

A Python/Tkinter-based campus utility management system for campus resources, maintenance, complaints, usage, reports, analytics, alerts, backups, audit history, administration, and user security.

## Version 10 features
- Admin Control Center
- System health/status summary
- Recent user activity dashboard from the audit trail
- User password change workflow
- Current password verification
- Minimum 6-character new password validation
- Admin and Faculty password-change access
- Existing Version 9 backup, restore, and audit features retained

## Version 9 features
- Admin-only Backup and Restore
- Timestamped backup sets
- Restore confirmation
- Audit Trail
- Activity logging for important system operations

## Version 8 features
- Resource usage automatically changes a resource to In Use
- Only Available resources can be selected for new usage
- Release Resource returns resources to Available
- Maintenance date validation
- Automatic refresh of alerts and analytics

## Version 7 features
- Alerts dashboard
- Overdue and upcoming maintenance alerts
- Invalid maintenance date detection
- Out-of-service resource alerts
- High/Critical unresolved complaint alerts

## Demo accounts
- Admin: admin / admin123
- Faculty: faculty / faculty123

## Run
    python app.py

## Data
Operational data is stored in `data/`. Backups are stored in `backups/`. Audit history is stored in `data/audit.csv`.

## Python concepts demonstrated
Decision making, loops, strings, lists, tuples, dictionaries, functions, file handling, exception handling, CSV persistence, dataclasses/OOP, Tkinter GUI, backup/restore, audit logging, user security, and modular design.
