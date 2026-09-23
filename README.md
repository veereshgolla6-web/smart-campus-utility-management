# Smart Campus Utility Management System - Version 11

A Python/Tkinter campus utility management system for resources, maintenance, complaints, usage, reports, analytics, alerts, backups, audit history, administration, and dashboard monitoring.

## Version 19 — Advanced Resource Management
- Resource capacity
- Department ownership
- Resource condition
- Resource assignment
- Resource notes
- Advanced resource search by category, department, location and condition
- Editable resource details
- Capacity validation
- Expanded resource records retained in reports and analytics

## Version 18 — Advanced User & Role Management
- User search and filtering
- Active/Inactive account status
- Admin password reset for selected users
- Last-login tracking
- Inactive accounts cannot log in
- Admin-only user controls
- User status and password actions recorded in the audit trail
- Existing role-based access controls retained

## Version 17 — System Notifications & Notification Center
- Dedicated Notifications tab
- Automatic out-of-service resource notifications
- Overdue and upcoming maintenance notifications
- Invalid maintenance-date notifications
- High/Critical unresolved complaint notifications
- Read/unread notification state
- Mark All as Read control
- Notification history stored in CSV
- Duplicate notification prevention

## Version 16 — User Profile & Session Controls
- My Profile panel
- Display-name update with validation
- Session start information
- Profile changes recorded in the audit trail
- Logout confirmation dialog
- Explicit LOGOUT audit event

## Version 15 — User Experience & Security Upgrade
- Password visibility toggle on login
- Five-attempt login protection per application session
- Session start information in the dashboard header
- Stronger password policy for password changes
- Clearer security and confirmation messages
- Existing role-based Admin/Faculty controls retained

## Version 14 — Advanced Search, Filters & Date-Range Reporting
- From/to date filtering with validation
- Resource filtering
- Status filtering
- Complaint priority filtering
- Combined filters across resources, complaints and usage
- Clear Filters control
- Filtered report counts
- Filtered CSV exports and dashboard summary

## Version 13 — Smart Reports & Export Center
- Dedicated Smart Reports & Export Center
- One-click export of resource, complaint, usage, maintenance and open-complaint reports
- Dashboard summary export with resolution rate and live totals
- CSV exports stored in the reports folder
- Report center record counts and refresh control
- Report exports recorded in the audit trail

## Version 12 — Advanced Visual Analytics
- Native Tkinter charts with no external dependencies
- Resource utilization/status chart
- Complaint priority chart
- Resource usage ranking chart
- Maintenance summary and upcoming maintenance count
- Complaint resolution-rate metric
- Responsive chart redraw after window resizing

## Version 11 — Professional Dashboard
- Dedicated Dashboard tab
- Six KPI cards: Resources, Available, In Use, Complaints, Open Complaints, Alerts
- Resource status summary
- Recent activity panel based on audit history
- Alert count combining maintenance, unavailable resources, and unresolved high/critical complaints
- One-click dashboard refresh
- Existing Admin Center, password management, backup/restore, and audit trail retained

## Demo accounts
- Admin: admin / admin123
- Faculty: faculty / faculty123

## Run
    python app.py

## Data
Operational data is stored in `data/`. Backups are stored in `backups/`. Audit history is stored in `data/audit.csv`.

## Python concepts demonstrated
Decision making, loops, strings, lists, tuples, dictionaries, functions, file handling, exception handling, CSV persistence, dataclasses/OOP, Tkinter GUI, backup/restore, audit logging, user security, analytics, and dashboard design.
