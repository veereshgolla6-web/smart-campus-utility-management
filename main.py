from datetime import datetime
from models import User
from storage import read_csv, append_csv, rewrite_csv

RESOURCE_HEADERS = ["resource_id","name","category","location","status"]
COMPLAINT_HEADERS = ["complaint_id","resource_id","title","description","category","priority","reported_by","status","assigned_to"]
USAGE_HEADERS = ["usage_id","resource_id","used_by","purpose","date","duration"]
USER_HEADERS = ["username","password","role","name"]

CATEGORIES = ("Electrical","Computer/IT","Projector","Furniture","Laboratory Equipment","Other")
PRIORITIES = ("Low","Medium","High","Critical")
STATUSES = ("Pending","Assigned","In Progress","Resolved","Closed")

def pause():
    input("\nPress Enter to continue...")

def login():
    users = read_csv("users.csv", USER_HEADERS)
    print("\n" + "="*60)
    print(" SMART CAMPUS UTILITY MANAGEMENT SYSTEM")
    print("="*60)
    for _ in range(3):
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        for row in users:
            if row["username"] == username and row["password"] == password:
                return User(username, password, row["role"], row["name"])
        print("Invalid username or password.")
    return None

def next_id(prefix, rows, field):
    nums=[]
    for row in rows:
        try:
            if row[field].startswith(prefix):
                nums.append(int(row[field][len(prefix):]))
        except (KeyError, ValueError):
            pass
    return f"{prefix}{max(nums, default=0)+1:03d}"

def choose(title, options):
    while True:
        print("\n"+title)
        for i, option in enumerate(options,1):
            print(f"{i}. {option}")
        try:
            n=int(input("Choose: "))
            if 1 <= n <= len(options):
                return options[n-1]
        except ValueError:
            pass
        print("Invalid choice.")

def list_resources():
    rows=read_csv("resources.csv", RESOURCE_HEADERS)
    print("\n--- RESOURCES ---")
    for r in rows:
        print(f'{r["resource_id"]} | {r["name"]} | {r["category"]} | {r["location"]} | {r["status"]}')
    if not rows: print("No resources found.")

def add_resource():
    rows=read_csv("resources.csv", RESOURCE_HEADERS)
    rid=next_id("R",rows,"resource_id")
    name=input("Resource name: ").strip()
    category=input("Category: ").strip() or "Other"
    location=input("Location: ").strip()
    if not name or not location:
        print("Name and location are required."); return
    append_csv("resources.csv",RESOURCE_HEADERS,
        {"resource_id":rid,"name":name,"category":category,"location":location,"status":"Available"})
    print("Resource added:",rid)

def report_complaint(user):
    resources=read_csv("resources.csv",RESOURCE_HEADERS)
    list_resources()
    rid=input("\nResource ID: ").strip()
    if not any(r["resource_id"]==rid for r in resources):
        print("Resource not found."); return
    rows=read_csv("complaints.csv",COMPLAINT_HEADERS)
    cid=next_id("C",rows,"complaint_id")
    title=input("Complaint title: ").strip()
    description=input("Description: ").strip()
    if not title or not description:
        print("Title and description are required."); return
    category=choose("Category",CATEGORIES)
    priority=choose("Priority",PRIORITIES)
    append_csv("complaints.csv",COMPLAINT_HEADERS,
        {"complaint_id":cid,"resource_id":rid,"title":title,"description":description,
         "category":category,"priority":priority,"reported_by":user.name,
         "status":"Pending","assigned_to":""})
    print("Complaint registered:",cid)

def list_complaints():
    rows=read_csv("complaints.csv",COMPLAINT_HEADERS)
    print("\n--- COMPLAINTS ---")
    for c in rows:
        print(f'{c["complaint_id"]} | {c["resource_id"]} | {c["title"]} | {c["priority"]} | {c["status"]}')
    if not rows: print("No complaints found.")

def update_complaint():
    rows=read_csv("complaints.csv",COMPLAINT_HEADERS)
    list_complaints()
    cid=input("\nComplaint ID: ").strip()
    for c in rows:
        if c["complaint_id"]==cid:
            c["status"]=choose("New status",STATUSES)
            assigned=input("Assigned to (optional): ").strip()
            if assigned: c["assigned_to"]=assigned
            rewrite_csv("complaints.csv",COMPLAINT_HEADERS,rows)
            print("Complaint updated."); return
    print("Complaint not found.")

def record_usage(user):
    resources=read_csv("resources.csv",RESOURCE_HEADERS)
    list_resources()
    rid=input("\nResource ID: ").strip()
    if not any(r["resource_id"]==rid for r in resources):
        print("Resource not found."); return
    rows=read_csv("usage.csv",USAGE_HEADERS)
    uid=next_id("U",rows,"usage_id")
    append_csv("usage.csv",USAGE_HEADERS,
        {"usage_id":uid,"resource_id":rid,"used_by":user.name,
         "purpose":input("Purpose: ").strip(),
         "date":datetime.now().strftime("%Y-%m-%d"),
         "duration":input("Duration: ").strip()})
    print("Usage recorded:",uid)

def dashboard():
    resources=read_csv("resources.csv",RESOURCE_HEADERS)
    complaints=read_csv("complaints.csv",COMPLAINT_HEADERS)
    usage=read_csv("usage.csv",USAGE_HEADERS)
    print("\n--- CAMPUS DASHBOARD ---")
    print("Total resources:",len(resources))
    print("Available:",sum(r["status"]=="Available" for r in resources))
    print("Total complaints:",len(complaints))
    for status in STATUSES:
        print(f"{status}: {sum(c['status']==status for c in complaints)}")
    print("Usage records:",len(usage))

def admin_menu():
    while True:
        print("\n1 Dashboard\n2 Add Resource\n3 List Resources\n4 List Complaints\n5 Update Complaint\n0 Logout")
        c=input("Choose: ").strip()
        if c=="1": dashboard(); pause()
        elif c=="2": add_resource(); pause()
        elif c=="3": list_resources(); pause()
        elif c=="4": list_complaints(); pause()
        elif c=="5": update_complaint(); pause()
        elif c=="0": break
        else: print("Invalid choice.")

def faculty_menu(user):
    while True:
        print("\n1 View Resources\n2 Report Complaint\n3 Record Usage\n4 View Complaints\n0 Logout")
        c=input("Choose: ").strip()
        if c=="1": list_resources(); pause()
        elif c=="2": report_complaint(user); pause()
        elif c=="3": record_usage(user); pause()
        elif c=="4": list_complaints(); pause()
        elif c=="0": break
        else: print("Invalid choice.")

def main():
    user=login()
    if not user:
        print("Access denied."); return
    print(f"\nWelcome, {user.name}!")
    if user.role=="Admin": admin_menu()
    else: faculty_menu(user)

if __name__=="__main__":
    main()
