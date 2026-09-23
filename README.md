# Smart Campus Utility Management System - Version 9

A Python/Tkinter-based campus utility management system for tracking resources, maintenance, complaints, usage, users, reports, analytics, alerts, backups, and audit history.

## Version 9 features
- Admin-only Backup and Restore controls
- Timestamped backup sets stored under `backups/`
- Restore from a selectable backup set
- Audit Trail tab
- Audit logging for login, user creation, resource creation/status changes, maintenance updates, complaints, usage, release actions, backup and restore operations
- Automatic audit log refresh
- Restore confirmation before replacing current data
- Stronger input validation for maintenance dates
- Existing Version 8 resource workflow and availability controls retained

## Version 8 features
- Resource usage automatically changes the resource to In Use
- Only Available resources can be selected for new usage
- Release Resource returns resources to Available
- Maintenance date validation
- Automatic refresh of alerts and analytics after operational changes
- Safer handling of older/missing CSV fields

## Version 7 features
- Alerts dashboard
- Overdue maintenance alerts
- Upcoming maintenance alerts for the next 7 days
- Invalid maintenance date detection
- Out-of-service resource alerts
- High and Critical unresolved complaint alerts

## Version 6 features
- Resource maintenance scheduling
- Last and next maintenance tracking
- Maintenance controls for Admin users
- Maintenance metrics in Reports and Analytics

## Demo accounts
- Admin: admin / admin123
- Faculty: faculty / faculty123

## Run
    python app.py

## Data and backup
Operational data is stored in `data/`. Admin-created backup sets are stored in `backups/`. Audit history is stored in `data/audit.csv`.

## Python concepts demonstrated
Decision making, loops, strings, lists, tuples, dictionaries, functions, file handling, exception handling, CSV persistence, dataclasses/OOP, Tkinter GUI, backup/restore, audit logging, and modular design.
