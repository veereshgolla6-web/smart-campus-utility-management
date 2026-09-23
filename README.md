# Smart Campus Utility Management System - Version 7

A Python/Tkinter-based campus utility management system for tracking resources, maintenance, complaints, usage, users, reports, analytics, and operational alerts.

## Version 7 features
- Alerts dashboard
- Overdue maintenance alerts
- Upcoming maintenance alerts for the next 7 days
- Invalid maintenance date detection
- Out-of-service resource alerts
- High and Critical unresolved complaint alerts
- Refreshable alert view

## Version 6 features
- Resource maintenance scheduling
- Last and next maintenance tracking
- Maintenance scheduling controls for Admin users
- Maintenance metrics in Reports and Analytics

## Version 5 features
- Analytics dashboard with live resource, complaint, and usage metrics
- Complaint priority and resolution-rate analysis
- Resource usage analysis

## Version 4 features
- Role-aware interface for Admin and Faculty users
- Admin-only user management
- Add campus users with duplicate-username validation
- Resource status workflow: Available, In Use, Maintenance, Out of Service
- Resource search and filtering
- Complaint search, assignment, and status workflow
- Resource usage recording automatically marks an available resource as In Use
- Release Resource workflow returns an in-use resource to Available
- Live dashboard counters
- Reports with resource status, complaint status/priority, usage totals, and resource utilization
- CSV report export
- Local CSV persistence with no external Python packages

## Demo accounts
- Admin: admin / admin123
- Faculty: faculty / faculty123

## Run
    python app.py

## Project structure
smart-campus-utility-management/
├── app.py
├── main.py
├── models.py
├── storage.py
├── data/
│   ├── users.csv
│   ├── resources.csv
│   ├── complaints.csv
│   └── usage.csv
├── reports/
├── requirements.txt
└── README.md

## Python concepts demonstrated
Decision making, loops, strings, lists, tuples, dictionaries, functions, file handling, exception-safe user input handling, CSV persistence, dataclasses/OOP, Tkinter GUI, and modular design.
