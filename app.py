import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import csv
from models import User
from storage import read_csv, append_csv, rewrite_csv

RESOURCE_HEADERS=["resource_id","name","category","location","status","last_maintenance","next_maintenance","capacity","department","condition","assigned_to","notes"]
COMPLAINT_HEADERS=["complaint_id","resource_id","title","description","category","priority","reported_by","status","assigned_to"]
USAGE_HEADERS=["usage_id","resource_id","used_by","purpose","date","duration"]
USER_HEADERS=["username","password","role","name","status","last_login"]
CATEGORIES=("Electrical","Computer/IT","Projector","Furniture","Laboratory Equipment","Other")
PRIORITIES=("Low","Medium","High","Critical")
STATUSES=("Pending","Assigned","In Progress","Resolved","Closed")
RESOURCE_STATUSES=("Available","In Use","Maintenance","Out of Service")
DATA_FILES=("users.csv","resources.csv","complaints.csv","usage.csv","reservations.csv","maintenance.csv")
AUDIT_HEADERS=("timestamp","username","role","action","details")
NOTIFICATION_HEADERS=("timestamp","username","type","title","message","read")

class SmartCampusApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Smart Campus Utility Management System"); self.geometry("1180x720"); self.minsize(1000,620); self.configure(bg="#eef4fb"); self.user=None; self.login_attempts=0; self.session_started=None
        self.style=ttk.Style(self)
        try:self.style.theme_use("clam")
        except tk.TclError:pass
        self.style.configure("Treeview",rowheight=30,font=("Segoe UI",10)); self.style.configure("Treeview.Heading",font=("Segoe UI",10,"bold")); self.style.configure("TNotebook.Tab",padding=(18,10),font=("Segoe UI",10,"bold")); self.show_login()
    def notify(self,kind,title,message):
        append_csv("notifications.csv",NOTIFICATION_HEADERS,{"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"username":self.user.username if self.user else "SYSTEM","type":kind,"title":title,"message":message,"read":"No"})
    def refresh_notifications(self):
        if not hasattr(self,"notification_tree"): return
        for x in self.notification_tree.get_children(): self.notification_tree.delete(x)
        rows=read_csv("notifications.csv",NOTIFICATION_HEADERS)
        for row in reversed(rows):
            if row.get("username") in (self.user.username,"SYSTEM"):
                self.notification_tree.insert("","end",values=tuple(row.get(k,"") for k in NOTIFICATION_HEADERS))
        unread=sum(1 for r in rows if r.get("username") in (self.user.username,"SYSTEM") and r.get("read")!="Yes")
        if hasattr(self,"notification_count"): self.notification_count.set(str(unread))
    def mark_notifications_read(self):
        rows=read_csv("notifications.csv",NOTIFICATION_HEADERS)
        for r in rows:
            if r.get("username") in (self.user.username,"SYSTEM"): r["read"]="Yes"
        rewrite_csv("notifications.csv",NOTIFICATION_HEADERS,rows); self.refresh_notifications()
    def generate_notifications(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS); complaints=read_csv("complaints.csv",COMPLAINT_HEADERS)
        today=datetime.now().date()
        existing=read_csv("notifications.csv",NOTIFICATION_HEADERS)
        existing_keys={(r.get("type"),r.get("message"),r.get("username")) for r in existing}
        def add(kind,title,msg):
            key=(kind,msg,self.user.username)
            if key not in existing_keys:
                self.notify(kind,title,msg); existing_keys.add(key)
        for r in resources:
            nxt=r.get("next_maintenance","").strip()
            if r.get("status")=="Out of Service": add("RESOURCE","Resource Out of Service",f"{r.get('resource_id','')} - {r.get('name','')} is out of service.")
            if nxt:
                try:
                    days=(datetime.strptime(nxt,"%Y-%m-%d").date()-today).days
                    if days<0: add("MAINTENANCE","Overdue Maintenance",f"{r.get('resource_id','')} maintenance is overdue.")
                    elif days<=7: add("MAINTENANCE","Upcoming Maintenance",f"{r.get('resource_id','')} maintenance is due in {days} day(s).")
                except ValueError: add("MAINTENANCE","Invalid Maintenance Date",f"{r.get('resource_id','')} has an invalid maintenance date.")
        for x in complaints:
            if x.get("priority") in ("High","Critical") and x.get("status") not in ("Resolved","Closed"):
                add("COMPLAINT","Priority Complaint",f"{x.get('complaint_id','')} is {x.get('priority','')} priority and unresolved.")
    def audit(self,action,details=""):
        append_csv("audit.csv",AUDIT_HEADERS,{"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"username":self.user.username if self.user else "SYSTEM","role":self.user.role if self.user else "SYSTEM","action":action,"details":details})

    def backup_data(self):
        if self.user.role!="Admin": messagebox.showerror("Access Denied","Only Admin can create backups."); return
        src=Path("data"); src.mkdir(exist_ok=True); stamp=datetime.now().strftime("%Y%m%d_%H%M%S"); dest=Path("backups")/f"backup_{stamp}"; dest.mkdir(parents=True,exist_ok=True)
        for name in DATA_FILES+("audit.csv",):
            p=src/name
            if p.exists(): shutil.copy2(p,dest/name)
        self.audit("BACKUP_CREATED",str(dest)); messagebox.showinfo("Backup Complete",f"Backup created successfully:\\n{dest}")

    def restore_data(self):
        if self.user.role!="Admin": messagebox.showerror("Access Denied","Only Admin can restore data."); return
        root=Path("backups")
        if not root.exists(): messagebox.showwarning("No Backups","No backup folder exists yet."); return
        backups=sorted([p for p in root.iterdir() if p.is_dir()],reverse=True)
        if not backups: messagebox.showwarning("No Backups","No backup sets were found."); return
        win=tk.Toplevel(self); win.title("Restore Backup"); win.geometry("500x250"); win.configure(bg="white")
        tk.Label(win,text="Select backup to restore",font=("Segoe UI",12,"bold"),bg="white",fg="#12395b").pack(pady=20)
        choice=tk.StringVar(value=backups[0].name); ttk.Combobox(win,textvariable=choice,values=[p.name for p in backups],state="readonly").pack(fill="x",padx=35,pady=10)
        def restore():
            selected=root/choice.get()
            if not selected.exists(): return
            if not messagebox.askyesno("Confirm Restore","Restore this backup? Current data will be replaced.",parent=win): return
            src=Path("data"); src.mkdir(exist_ok=True)
            for name in DATA_FILES+("audit.csv",):
                p=selected/name
                if p.exists(): shutil.copy2(p,src/name)
            self.audit("BACKUP_RESTORED",selected.name); win.destroy(); messagebox.showinfo("Restore Complete","Backup restored. The application will return to the login screen."); self.show_login()
        tk.Button(win,text="Restore Selected Backup",command=restore,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=20)

    def build_audit(self):
        bar=tk.Frame(self.audit_tab); bar.pack(fill="x",padx=15,pady=12)
        tk.Button(bar,text="Refresh Audit Log",command=self.refresh_audit,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left")
        self.audit_tree=self.tree(self.audit_tab,AUDIT_HEADERS); self.refresh_audit()

    def refresh_audit(self):
        if not hasattr(self,"audit_tree"): return
        for x in self.audit_tree.get_children(): self.audit_tree.delete(x)
        for row in reversed(read_csv("audit.csv",AUDIT_HEADERS)): self.audit_tree.insert("","end",values=tuple(row.get(k,"") for k in AUDIT_HEADERS))

    def clear(self):
        for w in self.winfo_children():w.destroy()
    def toggle_password(self,entry,button):
        if entry.cget("show"): entry.config(show=""); button.config(text="Hide")
        else: entry.config(show="•"); button.config(text="Show")
    def show_login(self):
        self.clear(); frame=tk.Frame(self,bg="#0b4f8a",width=520,height=720); frame.pack(side="left",fill="both",expand=True); frame.pack_propagate(False)
        tk.Label(frame,text="SMART CAMPUS",font=("Segoe UI",30,"bold"),fg="white",bg="#0b4f8a").pack(pady=(150,5)); tk.Label(frame,text="UTILITY MANAGEMENT",font=("Segoe UI",20),fg="#d9ecff",bg="#0b4f8a").pack(); tk.Label(frame,text="Resource Tracking • Maintenance • Reports",font=("Segoe UI",11),fg="white",bg="#0b4f8a").pack(pady=20)
        card=tk.Frame(self,bg="white"); card.pack(side="right",fill="both",expand=True,padx=70,pady=90); tk.Label(card,text="Welcome Back",font=("Segoe UI",25,"bold"),fg="#12395b",bg="white").pack(pady=(55,5)); tk.Label(card,text="Sign in to continue",font=("Segoe UI",11),fg="#6b7b8c",bg="white").pack(pady=(0,30))
        self.login_user=self.entry(card,"Username"); self.login_pass=self.entry(card,"Password",True); self.login_pass.bind("<Return>",lambda e:self.login()); pwbtn=tk.Button(card,text="Show",command=lambda:self.toggle_password(self.login_pass,pwbtn),bg="white",fg="#0b4f8a",bd=0); pwbtn.place(relx=0.80,rely=0.40); tk.Button(card,text="LOGIN",command=self.login,bg="#0b4f8a",fg="white",font=("Segoe UI",11,"bold"),bd=0,cursor="hand2",width=24,height=2).pack(pady=25); tk.Label(card,text="Demo: admin / admin123   |   faculty / faculty123",font=("Segoe UI",9),fg="#7a8794",bg="white").pack()
    def entry(self,parent,label,password=False):
        tk.Label(parent,text=label,font=("Segoe UI",10,"bold"),fg="#345",bg="white",anchor="w").pack(fill="x",padx=65,pady=(8,3)); e=tk.Entry(parent,font=("Segoe UI",12),show="•" if password else "",relief="solid",bd=1); e.pack(fill="x",padx=65,ipady=9); return e
    def login(self):
        if self.login_attempts>=5:
            messagebox.showerror("Login Locked","Too many failed attempts. Restart the application to try again."); return
        users=read_csv("users.csv",USER_HEADERS); u=self.login_user.get().strip(); p=self.login_pass.get(); row=next((x for x in users if x["username"]==u and x["password"]==p and x.get("status","Active")=="Active"),None)
        if not row:
            self.login_attempts+=1; messagebox.showerror("Login Failed",f"Invalid username or password. Attempts remaining: {max(0,5-self.login_attempts)}"); return
        self.login_attempts=0; self.user=User(u,p,row["role"],row["name"]); self.session_started=datetime.now(); rows=read_csv("users.csv",USER_HEADERS); [r.update({"last_login":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}) for r in rows if r.get("username")==u]; rewrite_csv("users.csv",USER_HEADERS,rows); self.show_dashboard(); self.audit("LOGIN","Successful login")
    def confirm_logout(self):
        if messagebox.askyesno("Confirm Logout","Are you sure you want to logout?"):
            self.audit("LOGOUT","User logged out")
            self.user=None
            self.session_started=None
            self.show_login()

    def user_profile(self):
        win=tk.Toplevel(self); win.title("My Profile"); win.geometry("460x430"); win.configure(bg="white")
        tk.Label(win,text="MY PROFILE",font=("Segoe UI",18,"bold"),fg="#12395b",bg="white").pack(pady=(25,15))
        fields={}
        for label,key,value,editable in (("Username","username",self.user.username,False),("Display Name","name",self.user.name,True),("Role","role",self.user.role,False)):
            tk.Label(win,text=label,bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=35,pady=(10,3))
            e=tk.Entry(win,font=("Segoe UI",11)); e.pack(fill="x",padx=35,ipady=7); e.insert(0,value); fields[key]=e
            if not editable: e.config(state="readonly")
        tk.Label(win,text=f"Session started: {self.session_started.strftime('%Y-%m-%d %H:%M:%S') if self.session_started else 'N/A'}",bg="white",fg="#71859a").pack(pady=18)
        def save():
            name=fields["name"].get().strip()
            if not name: messagebox.showwarning("Required","Display Name cannot be empty.",parent=win); return
            rows=read_csv("users.csv",USER_HEADERS)
            for row in rows:
                if row.get("username")==self.user.username: row["name"]=name
            rewrite_csv("users.csv",USER_HEADERS,rows); old=self.user.name; self.user.name=name
            self.audit("PROFILE_UPDATED",f"Display name changed from {old} to {name}")
            win.destroy(); self.show_dashboard()
        tk.Button(win,text="Save Profile",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack()

    def build_notifications(self,parent):
        bar=tk.Frame(parent,bg="#eef4fb"); bar.pack(fill="x",padx=15,pady=12)
        self.notification_count=tk.StringVar(value="0")
        tk.Button(bar,text="Refresh Notifications",command=lambda:(self.generate_notifications(),self.refresh_notifications()),bg="#0b4f8a",fg="white",bd=0,padx=14,pady=8).pack(side="left")
        tk.Button(bar,text="Mark All as Read",command=self.mark_notifications_read,bg="#376a92",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=8)
        tk.Label(bar,text="Unread:",bg="#eef4fb",fg="#456",font=("Segoe UI",10,"bold")).pack(side="left",padx=(15,5))
        tk.Label(bar,textvariable=self.notification_count,bg="#eef4fb",fg="#c0392b",font=("Segoe UI",12,"bold")).pack(side="left")
        self.notification_tree=self.tree(parent,NOTIFICATION_HEADERS)
        self.generate_notifications(); self.refresh_notifications()

    def show_dashboard(self):
        self.clear(); top=tk.Frame(self,bg="#0b4f8a",height=76); top.pack(fill="x"); tk.Label(top,text="Smart Campus Utility Management",font=("Segoe UI",20,"bold"),fg="white",bg="#0b4f8a").pack(side="left",padx=25,pady=18); tk.Label(top,text=f"{self.user.name}  •  {self.user.role}  •  Login: {self.session_started.strftime("%H:%M") if self.session_started else ""}",font=("Segoe UI",10),fg="white",bg="#0b4f8a").pack(side="right",padx=15); tk.Button(top,text="Logout",command=self.confirm_logout,bg="#083b68",fg="white",bd=0,padx=15,pady=8).pack(side="right"); tk.Button(top,text="My Profile",command=self.user_profile,bg="#376a92",fg="white",bd=0,padx=15,pady=8).pack(side="right",padx=5)
        body=tk.Frame(self,bg="#eef4fb"); body.pack(fill="both",expand=True,padx=20,pady=20); self.build_cards(body); notebook=ttk.Notebook(body); notebook.pack(fill="both",expand=True,pady=(18,0))
        self.home_tab=ttk.Frame(notebook); self.notification_tab=ttk.Frame(notebook); self.resource_tab=ttk.Frame(notebook); self.reservation_tab=ttk.Frame(notebook); self.schedule_tab=ttk.Frame(notebook); self.health_tab=ttk.Frame(notebook); self.maintenance_plan_tab=ttk.Frame(notebook); self.prediction_tab=ttk.Frame(notebook); self.complaint_tab=ttk.Frame(notebook); self.usage_tab=ttk.Frame(notebook); self.report_tab=ttk.Frame(notebook); self.analytics_tab=ttk.Frame(notebook); self.alert_tab=ttk.Frame(notebook); self.audit_tab=ttk.Frame(notebook)
        for tab,text in ((self.home_tab,"Dashboard"),(self.notification_tab,"Notifications"),(self.resource_tab,"Resources"),(self.reservation_tab,"Reservations"),(self.schedule_tab,"Smart Scheduling"),(self.health_tab,"Resource Health"),(self.maintenance_plan_tab,"Maintenance Planning"),(self.prediction_tab,"Predictive Maintenance"),(self.complaint_tab,"Complaints"),(self.usage_tab,"Usage"),(self.report_tab,"Reports"),(self.analytics_tab,"Analytics"),(self.alert_tab,"Alerts"),(self.audit_tab,"Audit")):notebook.add(tab,text=f"  {text}  ")
        if self.user.role=="Admin":
            self.user_tab=ttk.Frame(notebook); notebook.add(self.user_tab,text="  Users  ")
            self.admin_tab=ttk.Frame(notebook); notebook.add(self.admin_tab,text="  Admin Center  ")
            self.build_backup_controls(); self.build_admin_center()
        self.build_professional_dashboard(self.home_tab); self.build_notifications(self.notification_tab); self.build_resources(); self.build_reservations(); self.build_smart_scheduling(); self.build_resource_health(); self.build_maintenance_planning(); self.build_predictive_maintenance(); self.build_complaints(); self.build_usage(); self.build_reports(); self.build_analytics(); self.build_alerts(); self.build_audit()
        if self.user.role=="Admin":self.build_users()
    def build_professional_dashboard(self,parent):
        frame=tk.Frame(parent,bg="#eef4fb"); frame.pack(fill="both",expand=True)
        top=tk.Frame(frame,bg="#eef4fb"); top.pack(fill="x",pady=(0,12))
        self.kpi_vars={}
        for title,key in (("Resources","resources"),("Available","available"),("In Use","inuse"),("Complaints","complaints"),("Open Complaints","open"),("Alerts","alerts")):
            card=tk.Frame(top,bg="white",highlightthickness=1,highlightbackground="#d8e2ee"); card.pack(side="left",fill="x",expand=True,padx=4)
            tk.Label(card,text=title,bg="white",fg="#60758a",font=("Segoe UI",9,"bold")).pack(anchor="w",padx=12,pady=(10,2))
            v=tk.StringVar(value="0"); self.kpi_vars[key]=v
            tk.Label(card,textvariable=v,bg="white",fg="#0b4f8a",font=("Segoe UI",21,"bold")).pack(anchor="w",padx=12,pady=(0,10))
        lower=tk.Frame(frame,bg="#eef4fb"); lower.pack(fill="both",expand=True)
        left=tk.Frame(lower,bg="white",highlightthickness=1,highlightbackground="#d8e2ee"); left.pack(side="left",fill="both",expand=True,padx=(4,8))
        right=tk.Frame(lower,bg="white",highlightthickness=1,highlightbackground="#d8e2ee"); right.pack(side="left",fill="both",expand=True,padx=(8,4))
        tk.Label(left,text="Resource Status",font=("Segoe UI",13,"bold"),fg="#12395b",bg="white").pack(anchor="w",padx=15,pady=12)
        self.status_text=tk.Text(left,font=("Consolas",11),bg="white",fg="#345",bd=0,height=10,padx=15,pady=5); self.status_text.pack(fill="both",expand=True,padx=10,pady=5)
        tk.Label(right,text="Recent Activity",font=("Segoe UI",13,"bold"),fg="#12395b",bg="white").pack(anchor="w",padx=15,pady=12)
        self.activity_text=tk.Text(right,font=("Consolas",10),bg="white",fg="#345",bd=0,height=10,padx=15,pady=5); self.activity_text.pack(fill="both",expand=True,padx=10,pady=5)
        tk.Button(frame,text="↻ Refresh Dashboard",command=self.refresh_professional_dashboard,bg="#0b4f8a",fg="white",bd=0,padx=16,pady=8).pack(anchor="e",pady=10)
        self.refresh_professional_dashboard()

    def refresh_professional_dashboard(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS); complaints=read_csv("complaints.csv",COMPLAINT_HEADERS); audits=read_csv("audit.csv",AUDIT_HEADERS)
        alerts=0; today=datetime.now().date()
        for r in resources:
            nxt=r.get("next_maintenance","").strip()
            if r.get("status")=="Out of Service": alerts+=1
            if nxt:
                try:
                    if (datetime.strptime(nxt,"%Y-%m-%d").date()-today).days<=7: alerts+=1
                except ValueError: alerts+=1
        alerts+=sum(1 for x in complaints if x.get("priority") in ("High","Critical") and x.get("status") not in ("Resolved","Closed"))
        vals={"resources":len(resources),"available":sum(r.get("status")=="Available" for r in resources),"inuse":sum(r.get("status")=="In Use" for r in resources),"complaints":len(complaints),"open":sum(x.get("status") not in ("Resolved","Closed") for x in complaints),"alerts":alerts}
        for k,v in vals.items(): self.kpi_vars[k].set(str(v))
        lines=["AVAILABLE     : "+str(vals["available"]), "IN USE        : "+str(vals["inuse"]), "MAINTENANCE   : "+str(sum(r.get("status")=="Maintenance" for r in resources)), "OUT OF SERVICE: "+str(sum(r.get("status")=="Out of Service" for r in resources))]
        self.status_text.delete("1.0","end"); self.status_text.insert("1.0","\n".join(lines))
        recent=list(reversed(audits[-10:]))
        self.activity_text.delete("1.0","end"); self.activity_text.insert("1.0","\n".join(f"{x.get('timestamp','')} | {x.get('username','')} | {x.get('action','')}" for x in recent) or "No activity recorded.")

    def build_cards(self,parent):
        self.card_vars={}
        for title,file,headers in (("Resources","resources.csv",RESOURCE_HEADERS),("Complaints","complaints.csv",COMPLAINT_HEADERS),("Usage Records","usage.csv",USAGE_HEADERS)):
            f=tk.Frame(parent,bg="white",highlightthickness=1,highlightbackground="#d8e2ee"); f.pack(side="left",fill="x",expand=True,padx=6); v=tk.StringVar(value=str(len(read_csv(file,headers)))); self.card_vars[title]=v; tk.Label(f,text=title,bg="white",fg="#60758a",font=("Segoe UI",10)).pack(anchor="w",padx=18,pady=(15,2)); tk.Label(f,textvariable=v,bg="white",fg="#0b4f8a",font=("Segoe UI",24,"bold")).pack(anchor="w",padx=18,pady=(0,15))
    def refresh_cards(self):
        if hasattr(self,"card_vars"):
            for title,file,headers in (("Resources","resources.csv",RESOURCE_HEADERS),("Complaints","complaints.csv",COMPLAINT_HEADERS),("Usage Records","usage.csv",USAGE_HEADERS)):self.card_vars[title].set(str(len(read_csv(file,headers))))
    def tree(self,parent,columns):
        t=ttk.Treeview(parent,columns=columns,show="headings")
        for c in columns:t.heading(c,text=c.replace("_"," ").title()); t.column(c,width=135,anchor="center")
        t.pack(fill="both",expand=True,padx=15,pady=10); return t
    def build_admin_center(self):
        bar=tk.Frame(self.admin_tab); bar.pack(fill="x",padx=15,pady=12)
        tk.Button(bar,text="Refresh System Health",command=self.refresh_admin_center,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left")
        tk.Button(bar,text="Change My Password",command=self.change_password,bg="#376a92",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        self.admin_text=tk.Text(self.admin_tab,font=("Consolas",11),bg="white",fg="#12395b",bd=0,padx=20,pady=20); self.admin_text.pack(fill="both",expand=True,padx=15,pady=10); self.refresh_admin_center()

    def refresh_admin_center(self):
        users=read_csv("users.csv",USER_HEADERS); resources=read_csv("resources.csv",RESOURCE_HEADERS); complaints=read_csv("complaints.csv",COMPLAINT_HEADERS); usage=read_csv("usage.csv",USAGE_HEADERS); audits=read_csv("audit.csv",AUDIT_HEADERS)
        backup_count=len([p for p in Path("backups").iterdir() if p.is_dir()]) if Path("backups").exists() else 0
        lines=["ADMIN CONTROL CENTER","="*60,"","SYSTEM HEALTH","-"*60,f"Users: {len(users)}",f"Resources: {len(resources)}",f"Complaints: {len(complaints)}",f"Usage records: {len(usage)}",f"Audit entries: {len(audits)}",f"Backups: {backup_count}","","USER ACTIVITY","-"*60]
        for row in reversed(audits[-15:]): lines.append(f"{row.get('timestamp','')} | {row.get('username','')} | {row.get('action','')} | {row.get('details','')}")
        self.admin_text.delete("1.0","end"); self.admin_text.insert("1.0","\n".join(lines))

    def password_valid(self,password):
        return len(password)>=8 and any(x.isupper() for x in password) and any(x.islower() for x in password) and any(x.isdigit() for x in password)

    def change_password(self):
        win=tk.Toplevel(self); win.title("Change Password"); win.geometry("420x330"); win.configure(bg="white"); fields={}
        for label,key in (("Current Password","current"),("New Password","new"),("Confirm New Password","confirm")):
            tk.Label(win,text=label,bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(18,3)); e=tk.Entry(win,show="*",font=("Segoe UI",11)); e.pack(fill="x",padx=30,ipady=7); fields[key]=e
        def save():
            cur=fields["current"].get(); new=fields["new"].get(); confirm=fields["confirm"].get()
            if cur!=self.user.password: messagebox.showerror("Invalid Password","Current password is incorrect.",parent=win); return
            if not self.password_valid(new): messagebox.showwarning("Weak Password","Use at least 8 characters with uppercase, lowercase and a number.",parent=win); return
            if new!=confirm: messagebox.showwarning("Mismatch","New passwords do not match.",parent=win); return
            rows=read_csv("users.csv",USER_HEADERS)
            for row in rows:
                if row.get("username")==self.user.username: row["password"]=new
            rewrite_csv("users.csv",USER_HEADERS,rows); self.user.password=new; self.audit("PASSWORD_CHANGED","User changed own password"); win.destroy(); self.refresh_audit(); self.refresh_admin_center() if self.user.role=="Admin" else None; messagebox.showinfo("Password Updated","Your password was changed successfully.")
        tk.Button(win,text="Update Password",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=25)

    def build_backup_controls(self):
        bar=tk.Frame(self.user_tab); bar.pack(fill="x",padx=15,pady=(0,12))
        tk.Button(bar,text="Create Backup",command=self.backup_data,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left")
        tk.Button(bar,text="Restore Backup",command=self.restore_data,bg="#376a92",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)

    def build_users(self):
        bar=tk.Frame(self.user_tab); bar.pack(fill="x",padx=15,pady=12)
        tk.Button(bar,text="+ Add User",command=self.add_user,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left")
        tk.Button(bar,text="Refresh Users",command=self.refresh_users,bg="#376a92",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        tk.Button(bar,text="Reset Selected Password",command=self.reset_selected_password,bg="#657789",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        tk.Button(bar,text="Toggle Account Status",command=self.toggle_user_status,bg="#8a5a0b",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        self.user_search=tk.StringVar(); tk.Entry(bar,textvariable=self.user_search,width=22).pack(side="right",padx=5)
        tk.Button(bar,text="Search",command=self.refresh_users,bg="#0b4f8a",fg="white",bd=0,padx=10,pady=6).pack(side="right")
        self.user_tree=self.tree(self.user_tab,USER_HEADERS); self.refresh_users()
    def refresh_users(self):
        if not hasattr(self,"user_tree"): return
        for x in self.user_tree.get_children(): self.user_tree.delete(x)
        q=self.user_search.get().strip().lower()
        for row in read_csv("users.csv",USER_HEADERS):
            if q and q not in " ".join(row.get(k,"") for k in USER_HEADERS).lower(): continue
            self.user_tree.insert("","end",values=tuple(row.get(k,"") for k in USER_HEADERS))
    def selected_username(self):
        sel=self.user_tree.selection()
        if not sel: messagebox.showwarning("Select User","Select a user first."); return None
        return self.user_tree.item(sel[0],"values")[0]
    def reset_selected_password(self):
        username=self.selected_username()
        if not username: return
        if username==self.user.username: messagebox.showwarning("Not Allowed","Use Change Password for your own account."); return
        win=tk.Toplevel(self); win.title("Reset User Password"); win.geometry("380x230"); win.configure(bg="white")
        tk.Label(win,text=f"New password for {username}",bg="white",fg="#345").pack(pady=(25,5))
        e=tk.Entry(win,show="*",font=("Segoe UI",11)); e.pack(fill="x",padx=30,ipady=7)
        def save():
            p=e.get()
            if not self.password_valid(p): messagebox.showwarning("Weak Password","Use at least 8 characters with uppercase, lowercase and a number.",parent=win); return
            rows=read_csv("users.csv",USER_HEADERS)
            for r in rows:
                if r.get("username")==username: r["password"]=p
            rewrite_csv("users.csv",USER_HEADERS,rows); self.audit("PASSWORD_RESET",username); win.destroy(); self.refresh_users()
        tk.Button(win,text="Reset Password",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=8).pack(pady=20)
    def toggle_user_status(self):
        username=self.selected_username()
        if not username: return
        if username==self.user.username: messagebox.showwarning("Not Allowed","You cannot deactivate your own account."); return
        rows=read_csv("users.csv",USER_HEADERS); new="Active"
        for r in rows:
            if r.get("username")==username: new="Inactive" if r.get("status","Active")=="Active" else "Active"; r["status"]=new
        rewrite_csv("users.csv",USER_HEADERS,rows); self.audit("USER_STATUS_CHANGED",f"{username} -> {new}"); self.refresh_users()
    def add_user(self):
        win=tk.Toplevel(self); win.title("Add Campus User"); win.geometry("430x390"); win.configure(bg="white"); fields={}
        for label,key in (("Username","username"),("Password","password"),("Display Name","name")):
            tk.Label(win,text=label,bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(16,3)); e=tk.Entry(win,font=("Segoe UI",11),show="*" if key=="password" else ""); e.pack(fill="x",padx=30,ipady=7); fields[key]=e
        tk.Label(win,text="Role",bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(16,3)); role=tk.StringVar(value="Faculty"); ttk.Combobox(win,textvariable=role,values=("Admin","Faculty"),state="readonly").pack(fill="x",padx=30)
        def save():
            rows=read_csv("users.csv",USER_HEADERS); vals={k:e.get().strip() for k,e in fields.items()}
            if not all(vals.values()):messagebox.showwarning("Required","Complete all fields.",parent=win); return
            if any(x["username"].lower()==vals["username"].lower() for x in rows):messagebox.showerror("Duplicate","Username already exists.",parent=win); return
            vals["role"]=role.get(); vals["status"]="Active"; vals["last_login"]=""; append_csv("users.csv",USER_HEADERS,vals); self.audit("USER_CREATED",vals["username"]); win.destroy(); self.refresh_users(); self.refresh_audit()
        tk.Button(win,text="Create User",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=25)
    def draw_bar_chart(self,canvas,title,labels,values):
        canvas.delete("all")
        w=max(canvas.winfo_width(),420); h=max(canvas.winfo_height(),230)
        canvas.create_text(15,15,text=title,anchor="nw",font=("Segoe UI",12,"bold"),fill="#12395b")
        if not values or sum(values)==0:
            canvas.create_text(w/2,h/2,text="No data available",font=("Segoe UI",11),fill="#71859a"); return
        maxv=max(values) or 1; left=45; bottom=h-35; top=50; gap=12
        usable=w-left-20; bw=max(18,(usable-gap*max(1,len(values)-1))/max(1,len(values)))
        for i,(lab,val) in enumerate(zip(labels,values)):
            x=left+i*(bw+gap); bh=(h-top-45)*(val/maxv); y=bottom-bh
            canvas.create_rectangle(x,y,x+bw,bottom,fill="#2f80c0",outline="")
            canvas.create_text(x+bw/2,bottom+8,text=str(lab)[:12],anchor="n",font=("Segoe UI",8),fill="#456")
            canvas.create_text(x+bw/2,y-4,text=str(val),anchor="s",font=("Segoe UI",8,"bold"),fill="#12395b")

    def draw_horizontal_chart(self,canvas,title,labels,values):
        canvas.delete("all")
        w=max(canvas.winfo_width(),420); h=max(canvas.winfo_height(),230)
        canvas.create_text(15,15,text=title,anchor="nw",font=("Segoe UI",12,"bold"),fill="#12395b")
        if not values or sum(values)==0:
            canvas.create_text(w/2,h/2,text="No data available",font=("Segoe UI",11),fill="#71859a"); return
        maxv=max(values) or 1; start=125; barw=w-start-25; row=max(28,(h-65)/len(values))
        for i,(lab,val) in enumerate(zip(labels,values)):
            y=52+i*row; width=barw*(val/maxv)
            canvas.create_text(start-8,y+9,text=str(lab),anchor="e",font=("Segoe UI",9),fill="#456")
            canvas.create_rectangle(start,y,start+barw,y+18,fill="#e4edf6",outline="")
            canvas.create_rectangle(start,y,start+width,y+18,fill="#0b4f8a",outline="")
            canvas.create_text(start+width+5,y+9,text=str(val),anchor="w",font=("Segoe UI",9,"bold"),fill="#12395b")

    def build_analytics(self):
        bar=tk.Frame(self.analytics_tab); bar.pack(fill="x",padx=15,pady=12)
        tk.Button(bar,text="Refresh Analytics",command=self.refresh_analytics,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left")
        self.chart_area=tk.Frame(self.analytics_tab,bg="#eef4fb"); self.chart_area.pack(fill="both",expand=True,padx=10,pady=5)
        self.chart1=tk.Canvas(self.chart_area,bg="white",highlightthickness=1,highlightbackground="#d8e2ee"); self.chart1.pack(side="left",fill="both",expand=True,padx=5,pady=5)
        self.chart2=tk.Canvas(self.chart_area,bg="white",highlightthickness=1,highlightbackground="#d8e2ee"); self.chart2.pack(side="left",fill="both",expand=True,padx=5,pady=5)
        self.chart3=tk.Canvas(self.analytics_tab,bg="white",height=250,highlightthickness=1,highlightbackground="#d8e2ee"); self.chart3.pack(fill="both",expand=False,padx=15,pady=5)
        self.analytics_text=tk.Text(self.analytics_tab,font=("Consolas",10),bg="white",fg="#12395b",bd=0,padx=15,pady=10,height=7)
        self.analytics_text.pack(fill="x",padx=15,pady=5)
        self.refresh_analytics()

    def refresh_analytics(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS); complaints=read_csv("complaints.csv",COMPLAINT_HEADERS); usage=read_csv("usage.csv",USAGE_HEADERS)
        status_labels=list(RESOURCE_STATUSES); status_values=[sum(r.get("status")==s for r in resources) for s in status_labels]
        priority_labels=list(PRIORITIES); priority_values=[sum(x.get("priority")==p for x in complaints) for p in priority_labels]
        counts={}
        for u in usage: counts[u.get("resource_id","Unknown")]=counts.get(u.get("resource_id","Unknown"),0)+1
        usage_items=sorted(counts.items(),key=lambda x:x[1],reverse=True)[:8]
        self.draw_bar_chart(self.chart1,"Resource Utilization",status_labels,status_values)
        self.draw_bar_chart(self.chart2,"Complaint Priority",priority_labels,priority_values)
        self.draw_horizontal_chart(self.chart3,"Resource Usage Records",[x[0] for x in usage_items],[x[1] for x in usage_items])
        resolved=sum(x.get("status") in ("Resolved","Closed") for x in complaints)
        resolution=(resolved/len(complaints)*100) if complaints else 0
        maintenance=sum(r.get("status")=="Maintenance" for r in resources)
        upcoming=0; today=datetime.now().date()
        for r in resources:
            nxt=r.get("next_maintenance","").strip()
            if nxt:
                try:
                    if 0 <= (datetime.strptime(nxt,"%Y-%m-%d").date()-today).days <= 30: upcoming+=1
                except ValueError: pass
        lines=["SMART CAMPUS VISUAL ANALYTICS","="*55,"",f"Total resources: {len(resources)}",f"Maintenance resources: {maintenance}",f"Upcoming maintenance (30 days): {upcoming}",f"Total complaints: {len(complaints)}",f"Resolution rate: {resolution:.1f}%",f"Total usage records: {len(usage)}","", "Charts: Resource utilization | Complaint priority | Resource usage"]
        self.analytics_text.delete("1.0","end"); self.analytics_text.insert("1.0","\\n".join(lines))
        self.chart1.after(100,self._redraw_charts)

    def _redraw_charts(self):
        if hasattr(self,"chart1"):
            resources=read_csv("resources.csv",RESOURCE_HEADERS); complaints=read_csv("complaints.csv",COMPLAINT_HEADERS); usage=read_csv("usage.csv",USAGE_HEADERS)
            self.draw_bar_chart(self.chart1,"Resource Utilization",list(RESOURCE_STATUSES),[sum(r.get("status")==s for r in resources) for s in RESOURCE_STATUSES])
            self.draw_bar_chart(self.chart2,"Complaint Priority",list(PRIORITIES),[sum(x.get("priority")==p for x in complaints) for p in PRIORITIES])
            counts={}
            for u in usage: counts[u.get("resource_id","Unknown")]=counts.get(u.get("resource_id","Unknown"),0)+1
            items=sorted(counts.items(),key=lambda x:x[1],reverse=True)[:8]
            self.draw_horizontal_chart(self.chart3,"Resource Usage Records",[x[0] for x in items],[x[1] for x in items])


        bar=tk.Frame(self.analytics_tab); bar.pack(fill="x",padx=15,pady=12); tk.Button(bar,text="Refresh Analytics",command=self.refresh_analytics,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left"); self.analytics_text=tk.Text(self.analytics_tab,font=("Consolas",11),bg="white",fg="#12395b",bd=0,padx=20,pady=20); self.analytics_text.pack(fill="both",expand=True,padx=15,pady=10); self.refresh_analytics()
    def refresh_analytics(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS); complaints=read_csv("complaints.csv",COMPLAINT_HEADERS); usage=read_csv("usage.csv",USAGE_HEADERS); lines=["SMART CAMPUS ANALYTICS","="*55,"",f"Total resources: {len(resources)}",f"Available: {sum(r.get('status')=='Available' for r in resources)}",f"In Use: {sum(r.get('status')=='In Use' for r in resources)}",f"Maintenance: {sum(r.get('status')=='Maintenance' for r in resources)}",f"Out of Service: {sum(r.get('status')=='Out of Service' for r in resources)}","",f"Total complaints: {len(complaints)}"]
        for p in PRIORITIES:lines.append(f"{p} priority: {sum(x.get('priority')==p for x in complaints)}")
        resolved=sum(x.get("status") in ("Resolved","Closed") for x in complaints)
        if complaints:lines.append(f"Resolution rate: {resolved/len(complaints)*100:.1f}%")
        lines+=["",f"Total usage records: {len(usage)}","","RESOURCE USAGE"]; counts={}
        for u in usage:counts[u.get("resource_id","")]=counts.get(u.get("resource_id",""),0)+1
        for rid,count in sorted(counts.items(),key=lambda x:x[1],reverse=True):lines.append(f"{rid}: {count} usage record(s)")
        self.analytics_text.delete("1.0","end"); self.analytics_text.insert("1.0","\n".join(lines))
    def build_alerts(self):
        bar=tk.Frame(self.alert_tab); bar.pack(fill="x",padx=15,pady=12); tk.Button(bar,text="Refresh Alerts",command=self.refresh_alerts,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left"); self.alert_text=tk.Text(self.alert_tab,font=("Consolas",11),bg="white",fg="#12395b",bd=0,padx=20,pady=20); self.alert_text.pack(fill="both",expand=True,padx=15,pady=10); self.refresh_alerts()
    def refresh_alerts(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS); complaints=read_csv("complaints.csv",COMPLAINT_HEADERS); today=datetime.now().date(); alerts=[]
        for r in resources:
            nxt=r.get("next_maintenance","").strip()
            if nxt:
                try:
                    d=datetime.strptime(nxt,"%Y-%m-%d").date(); days=(d-today).days
                    if days<0:alerts.append(f"OVERDUE MAINTENANCE: {r.get('resource_id')} - {r.get('name')} ({abs(days)} day(s) overdue)")
                    elif days<=7:alerts.append(f"UPCOMING MAINTENANCE: {r.get('resource_id')} - {r.get('name')} in {days} day(s)")
                except ValueError:alerts.append(f"INVALID MAINTENANCE DATE: {r.get('resource_id')} - {r.get('name')}")
            if r.get("status")=="Out of Service":alerts.append(f"RESOURCE UNAVAILABLE: {r.get('resource_id')} - {r.get('name')}")
        for x in complaints:
            if x.get("priority") in ("High","Critical") and x.get("status") not in ("Resolved","Closed"):alerts.append(f"{x.get('priority').upper()} COMPLAINT: {x.get('complaint_id')} - {x.get('title')}")
        self.alert_text.delete("1.0","end"); self.alert_text.insert("1.0","SMART CAMPUS ALERTS\n"+"="*60+"\n\n"+("\n".join("• "+a for a in alerts) if alerts else "No active alerts."))
    def build_resources(self):
        bar=tk.Frame(self.resource_tab); bar.pack(fill="x",padx=15,pady=12)
        tk.Button(bar,text="+ Add Resource",command=self.add_resource,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left")
        tk.Button(bar,text="Advanced Search",command=self.search_resources,bg="#376a92",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        tk.Button(bar,text="Resource Details",command=self.edit_resource_details,bg="#657789",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        tk.Button(bar,text="Availability",command=self.show_resource_availability,bg="#5b7f5b",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        self.resource_search=tk.StringVar(); tk.Entry(bar,textvariable=self.resource_search,width=28).pack(side="right",padx=5)
        tk.Button(bar,text="Search",command=self.refresh_resources,bg="#0b4f8a",fg="white",bd=0,padx=10,pady=6).pack(side="right")
        self.resource_tree=self.tree(self.resource_tab,RESOURCE_HEADERS); self.refresh_resources()
    def refresh_resources(self):
        if not hasattr(self,"resource_tree"): return
        for x in self.resource_tree.get_children(): self.resource_tree.delete(x)
        q=self.resource_search.get().strip().lower()
        for row in read_csv("resources.csv",RESOURCE_HEADERS):
            if q and q not in " ".join(row.get(k,"") for k in RESOURCE_HEADERS).lower(): continue
            self.resource_tree.insert("","end",values=tuple(row.get(k,"") for k in RESOURCE_HEADERS))
    def search_resources(self):
        self.resource_search.set("")
        win=tk.Toplevel(self); win.title("Advanced Resource Search"); win.geometry("430x300"); win.configure(bg="white")
        fields={}
        for label,key in (("Category","category"),("Department","department"),("Location","location"),("Condition","condition")):
            tk.Label(win,text=label,bg="white",fg="#345").pack(anchor="w",padx=30,pady=(14,2))
            e=tk.Entry(win); e.pack(fill="x",padx=30); fields[key]=e
        def apply():
            rows=read_csv("resources.csv",RESOURCE_HEADERS)
            for key,e in fields.items():
                q=e.get().strip().lower()
                if q: rows=[r for r in rows if q in r.get(key,"").lower()]
            for x in self.resource_tree.get_children(): self.resource_tree.delete(x)
            for row in rows:self.resource_tree.insert("","end",values=tuple(row.get(k,"") for k in RESOURCE_HEADERS))
            win.destroy()
        tk.Button(win,text="Apply Search",command=apply,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=8).pack(pady=20)
    def edit_resource_details(self):
        sel=self.resource_tree.selection()
        if not sel: messagebox.showwarning("Select Resource","Select a resource first."); return
        rid=self.resource_tree.item(sel[0],"values")[0]; rows=read_csv("resources.csv",RESOURCE_HEADERS); row=next((r for r in rows if r.get("resource_id")==rid),None)
        if not row:return
        win=tk.Toplevel(self); win.title("Resource Details"); win.geometry("470x650"); win.configure(bg="white"); fields={}
        editable=("name","category","location","capacity","department","condition","assigned_to","notes")
        for key in editable:
            tk.Label(win,text=key.replace("_"," ").title(),bg="white",fg="#345").pack(anchor="w",padx=30,pady=(10,2))
            e=tk.Entry(win); e.pack(fill="x",padx=30); e.insert(0,row.get(key,"")); fields[key]=e
        def save():
            cap=fields["capacity"].get().strip()
            if cap and (not cap.isdigit() or int(cap)<0): messagebox.showwarning("Invalid Capacity","Capacity must be a non-negative number.",parent=win); return
            for r in rows:
                if r.get("resource_id")==rid:
                    for key,e in fields.items(): r[key]=e.get().strip()
            rewrite_csv("resources.csv",RESOURCE_HEADERS,rows); self.audit("RESOURCE_DETAILS_UPDATED",rid); win.destroy(); self.refresh_resources(); self.refresh_professional_dashboard()
        tk.Button(win,text="Save Resource Details",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=20)
    def build_reservations(self):
        bar=tk.Frame(self.reservation_tab,bg="#eef4fb"); bar.pack(fill="x",padx=15,pady=12)
        tk.Button(bar,text="+ New Reservation",command=self.add_reservation,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left")
        tk.Button(bar,text="Refresh",command=self.refresh_reservations,bg="#376a92",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        tk.Button(bar,text="Cancel Selected",command=self.cancel_reservation,bg="#8a4b0b",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        tk.Button(bar,text="Complete Selected",command=self.complete_reservation,bg="#4b7650",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        tk.Button(bar,text="Availability View",command=self.show_resource_availability,bg="#657789",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        self.reservation_search=tk.StringVar()
        tk.Entry(bar,textvariable=self.reservation_search,width=28).pack(side="right",padx=5)
        tk.Button(bar,text="Search",command=self.refresh_reservations,bg="#0b4f8a",fg="white",bd=0,padx=10,pady=6).pack(side="right")
        self.reservation_tree=self.tree(self.reservation_tab,RESERVATION_HEADERS)
        self.reservation_summary=tk.StringVar(value="")
        tk.Label(self.reservation_tab,textvariable=self.reservation_summary,bg="#eef4fb",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=20,pady=(0,4))
        self.refresh_reservations()

    def reservation_overlap(self,a_start,a_end,b_start,b_end):
        return a_start < b_end and b_start < a_end

    def valid_reservation_times(self,date_value,start_value,end_value):
        try:
            date=datetime.strptime(date_value.strip(),"%Y-%m-%d").date()
            start=datetime.strptime(start_value.strip(),"%H:%M").time()
            end=datetime.strptime(end_value.strip(),"%H:%M").time()
            start_dt=datetime.combine(date,start); end_dt=datetime.combine(date,end)
            if end_dt<=start_dt: return None
            return date,start_dt,end_dt
        except ValueError:
            return None

    def find_reservation_conflicts(self,resource_id,date_value,start_value,end_value,ignore_id=""):
        parsed=self.valid_reservation_times(date_value,start_value,end_value)
        if not parsed: return []
        _,start_dt,end_dt=parsed; conflicts=[]
        for r in read_csv("reservations.csv",RESERVATION_HEADERS):
            if r.get("reservation_id")==ignore_id or r.get("resource_id")!=resource_id or r.get("date")!=date_value: continue
            if r.get("status") in ("Cancelled","Completed"): continue
            other=self.valid_reservation_times(r.get("date",""),r.get("start_time",""),r.get("end_time",""))
            if other and self.reservation_overlap(start_dt,end_dt,other[1],other[2]): conflicts.append(r)
        return conflicts

    def next_reservation_id(self):
        rows=read_csv("reservations.csv",RESERVATION_HEADERS)
        nums=[int(r.get("reservation_id","")[1:]) for r in rows if r.get("reservation_id","").startswith("R") and r.get("reservation_id","")[1:].isdigit()]
        return f"R{max(nums,default=0)+1:03d}"

    def refresh_reservations(self):
        if not hasattr(self,"reservation_tree"): return
        for x in self.reservation_tree.get_children(): self.reservation_tree.delete(x)
        q=getattr(self,"reservation_search",tk.StringVar()).get().strip().lower()
        rows=read_csv("reservations.csv",RESERVATION_HEADERS)
        for r in rows:
            if q and q not in " ".join(r.get(k,"") for k in RESERVATION_HEADERS).lower(): continue
            self.reservation_tree.insert("","end",values=tuple(r.get(k,"") for k in RESERVATION_HEADERS))
        self.refresh_reservation_summary()

    def refresh_reservation_summary(self):
        if not hasattr(self,"reservation_summary"): return
        rows=read_csv("reservations.csv",RESERVATION_HEADERS)
        active=sum(r.get("status") in ("Pending","Active") for r in rows)
        today=datetime.now().strftime("%Y-%m-%d")
        today_count=sum(r.get("date")==today and r.get("status") not in ("Cancelled","Completed") for r in rows)
        self.reservation_summary.set(f"Active/Pending: {active}   |   Today's reservations: {today_count}")

    def add_reservation(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS)
        eligible=[r for r in resources if r.get("status")=="Available"]
        if not eligible:
            messagebox.showwarning("No Available Resources","There are no resources currently marked Available."); return
        win=tk.Toplevel(self); win.title("New Resource Reservation"); win.geometry("520x610"); win.configure(bg="white")
        fields={}
        def field(label,key,default=""):
            tk.Label(win,text=label,bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(10,3))
            e=tk.Entry(win,font=("Segoe UI",11)); e.pack(fill="x",padx=30,ipady=6); e.insert(0,default); fields[key]=e
        tk.Label(win,text="RESERVE RESOURCE",font=("Segoe UI",18,"bold"),fg="#12395b",bg="white").pack(pady=(20,8))
        rm=tk.StringVar(); ttk.Combobox(win,textvariable=rm,values=[f"{r.get('resource_id')} - {r.get('name')} ({r.get('location','')})" for r in eligible],state="readonly").pack(fill="x",padx=30,pady=8)
        field("Reserved By","reserved_by",self.user.name)
        field("Department","department","")
        field("Date (YYYY-MM-DD)","date",datetime.now().strftime("%Y-%m-%d"))
        field("Start Time (HH:MM)","start_time","09:00")
        field("End Time (HH:MM)","end_time","10:00")
        field("Purpose","purpose")
        def save():
            selected=rm.get().strip()
            if not selected or not all(fields[k].get().strip() for k in ("reserved_by","date","start_time","end_time","purpose")):
                messagebox.showwarning("Required","Complete the resource, user, date, time and purpose fields.",parent=win); return
            parsed=self.valid_reservation_times(fields["date"].get(),fields["start_time"].get(),fields["end_time"].get())
            if not parsed: messagebox.showwarning("Invalid Date/Time","Use YYYY-MM-DD and HH:MM. End time must be after start time.",parent=win); return
            date_obj,_,_=parsed
            if date_obj < datetime.now().date(): messagebox.showwarning("Invalid Date","Reservation date cannot be in the past.",parent=win); return
            rid=selected.split(" - ",1)[0]
            current=next((r for r in read_csv("resources.csv",RESOURCE_HEADERS) if r.get("resource_id")==rid),None)
            if not current or current.get("status")!="Available": messagebox.showwarning("Unavailable","This resource is no longer available.",parent=win); return
            conflicts=self.find_reservation_conflicts(rid,fields["date"].get().strip(),fields["start_time"].get().strip(),fields["end_time"].get().strip())
            if conflicts:
                c=conflicts[0]
                messagebox.showerror("Schedule Conflict",f"{rid} is already reserved from {c.get('start_time')} to {c.get('end_time')} on {c.get('date')}.",parent=win); return
            row={"reservation_id":self.next_reservation_id(),"resource_id":rid,"reserved_by":fields["reserved_by"].get().strip(),"department":fields["department"].get().strip(),"date":fields["date"].get().strip(),"start_time":fields["start_time"].get().strip(),"end_time":fields["end_time"].get().strip(),"purpose":fields["purpose"].get().strip(),"status":"Pending"}
            append_csv("reservations.csv",RESERVATION_HEADERS,row)
            self.audit("RESERVATION_CREATED",row["reservation_id"]+" | "+rid)
            self.notify("RESERVATION","Reservation Created",f"{rid} reserved for {row['date']} {row['start_time']}-{row['end_time']}.")
            win.destroy(); self.refresh_reservations(); self.refresh_notifications(); self.refresh_audit(); messagebox.showinfo("Reservation Created",f"Reservation {row['reservation_id']} created successfully.")
        tk.Button(win,text="Create Reservation",command=save,bg="#0b4f8a",fg="white",bd=0,padx=22,pady=9).pack(pady=22)

    def cancel_reservation(self):
        sel=self.reservation_tree.selection()
        if not sel: messagebox.showwarning("Select Reservation","Select a reservation first."); return
        rid=self.reservation_tree.item(sel[0],"values")[0]
        rows=read_csv("reservations.csv",RESERVATION_HEADERS); row=next((r for r in rows if r.get("reservation_id")==rid),None)
        if not row or row.get("status") in ("Cancelled","Completed"): return
        if not messagebox.askyesno("Cancel Reservation",f"Cancel {rid}?",parent=self): return
        row["status"]="Cancelled"; rewrite_csv("reservations.csv",RESERVATION_HEADERS,rows)
        self.audit("RESERVATION_CANCELLED",rid); self.notify("RESERVATION","Reservation Cancelled",f"{rid} for resource {row.get('resource_id','')} was cancelled.")
        self.refresh_reservations(); self.refresh_notifications(); self.refresh_audit()

    def complete_reservation(self):
        sel=self.reservation_tree.selection()
        if not sel: messagebox.showwarning("Select Reservation","Select a reservation first."); return
        rid=self.reservation_tree.item(sel[0],"values")[0]
        rows=read_csv("reservations.csv",RESERVATION_HEADERS); row=next((r for r in rows if r.get("reservation_id")==rid),None)
        if not row or row.get("status") in ("Cancelled","Completed"): return
        row["status"]="Completed"; rewrite_csv("reservations.csv",RESERVATION_HEADERS,rows)
        self.audit("RESERVATION_COMPLETED",rid); self.refresh_reservations(); self.refresh_audit()

    def show_resource_availability(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS)
        win=tk.Toplevel(self); win.title("Resource Availability"); win.geometry("980x600"); win.configure(bg="#eef4fb")
        tk.Label(win,text="RESOURCE AVAILABILITY",font=("Segoe UI",18,"bold"),fg="#12395b",bg="#eef4fb").pack(pady=(18,5))
        top=tk.Frame(win,bg="#eef4fb"); top.pack(fill="x",padx=20)
        rm=tk.StringVar()
        ttk.Combobox(top,textvariable=rm,values=[f"{r.get('resource_id')} - {r.get('name')}" for r in resources],state="readonly").pack(side="left",fill="x",expand=True)
        tree=self.tree(win,RESERVATION_HEADERS)
        def load():
            selected=rm.get(); rid=selected.split(" - ",1)[0] if selected else ""
            for x in tree.get_children(): tree.delete(x)
            for r in read_csv("reservations.csv",RESERVATION_HEADERS):
                if r.get("resource_id")==rid and r.get("status") not in ("Cancelled","Completed"): tree.insert("","end",values=tuple(r.get(k,"") for k in RESERVATION_HEADERS))
        tk.Button(top,text="Show Schedule",command=load,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=7).pack(side="left",padx=8)
        if resources:
            rm.set(f"{resources[0].get('resource_id')} - {resources[0].get('name')}"); load()

    def reservation_hours(self,row):
        try:
            start=datetime.strptime(row.get("start_time",""),"%H:%M")
            end=datetime.strptime(row.get("end_time",""),"%H:%M")
            return max(0.0,(end-start).total_seconds()/3600.0)
        except ValueError:
            return 0.0

    def schedule_period(self):
        if not hasattr(self,"schedule_period_var"): return datetime.now().date(),datetime.now().date()
        choice=self.schedule_period_var.get()
        today=datetime.now().date()
        if choice=="Today": return today,today
        return today,today+timedelta(days=6)

    def calculate_utilization(self,start_date,end_date):
        resources=read_csv("resources.csv",RESOURCE_HEADERS)
        reservations=read_csv("reservations.csv",RESERVATION_HEADERS)
        days=max(1,(end_date-start_date).days+1)
        capacity_hours=days*OPERATING_HOURS_PER_DAY
        stats={}
        for r in resources:
            rid=r.get("resource_id","")
            stats[rid]={"resource_id":rid,"name":r.get("name",""),"department":r.get("department",""),"capacity_hours":capacity_hours,"reserved_hours":0.0,"utilization":0.0}
        for row in reservations:
            if row.get("status") in ("Cancelled","Completed"): continue
            try: d=datetime.strptime(row.get("date",""),"%Y-%m-%d").date()
            except ValueError: continue
            if start_date<=d<=end_date and row.get("resource_id") in stats:
                stats[row["resource_id"]]["reserved_hours"]+=self.reservation_hours(row)
        for x in stats.values():
            x["utilization"]=(x["reserved_hours"]/x["capacity_hours"]*100) if x["capacity_hours"] else 0.0
        return list(stats.values())

    def build_smart_scheduling(self):
        bar=tk.Frame(self.schedule_tab,bg="#eef4fb"); bar.pack(fill="x",padx=15,pady=12)
        self.schedule_period_var=tk.StringVar(value="Next 7 Days")
        tk.Label(bar,text="Period:",bg="#eef4fb",fg="#456",font=("Segoe UI",10,"bold")).pack(side="left")
        ttk.Combobox(bar,textvariable=self.schedule_period_var,values=("Today","Next 7 Days"),state="readonly",width=14).pack(side="left",padx=6)
        tk.Button(bar,text="Refresh Utilization",command=self.refresh_smart_scheduling,bg="#0b4f8a",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=5)
        tk.Button(bar,text="Find Available Slot",command=self.find_available_slot,bg="#376a92",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=5)
        tk.Button(bar,text="Conflict Check",command=self.show_schedule_conflicts,bg="#8a5a0b",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=5)
        tk.Button(bar,text="Weekly Calendar",command=self.show_weekly_calendar,bg="#657789",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=5)
        tk.Button(bar,text="Department Usage",command=self.show_department_usage,bg="#5b7f5b",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=5)
        self.schedule_kpi=tk.StringVar(value="")
        tk.Label(bar,textvariable=self.schedule_kpi,bg="#eef4fb",fg="#12395b",font=("Segoe UI",10,"bold")).pack(side="right",padx=8)
        self.util_tree=self.tree(self.schedule_tab,("resource_id","name","department","capacity_hours","reserved_hours","utilization_percent"))
        self.refresh_smart_scheduling()

    def refresh_smart_scheduling(self):
        if not hasattr(self,"util_tree"): return
        start,end=self.schedule_period()
        stats=self.calculate_utilization(start,end)
        for x in self.util_tree.get_children(): self.util_tree.delete(x)
        for x in sorted(stats,key=lambda z:z["utilization"],reverse=True):
            self.util_tree.insert("","end",values=(x["resource_id"],x["name"],x["department"],f"{x['capacity_hours']:.1f}",f"{x['reserved_hours']:.1f}",f"{x['utilization']:.1f}%"))
        total=len(stats); avg=(sum(x["utilization"] for x in stats)/total) if total else 0
        busiest=max(stats,key=lambda z:z["utilization"])["name"] if stats else "None"
        least=min(stats,key=lambda z:z["utilization"])["name"] if stats else "None"
        self.schedule_kpi.set(f"Resources: {total}  |  Average utilization: {avg:.1f}%  |  Most used: {busiest}  |  Least used: {least}")

    def show_weekly_calendar(self):
        start,end=self.schedule_period()
        rows=[r for r in read_csv("reservations.csv",RESERVATION_HEADERS) if r.get("status") not in ("Cancelled","Completed")]
        win=tk.Toplevel(self); win.title("Weekly Resource Calendar"); win.geometry("1100x620"); win.configure(bg="#eef4fb")
        tk.Label(win,text="RESOURCE SCHEDULE CALENDAR",font=("Segoe UI",18,"bold"),fg="#12395b",bg="#eef4fb").pack(pady=(15,3))
        tk.Label(win,text=f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}",fg="#60758a",bg="#eef4fb").pack(pady=(0,10))
        cols=("resource","date","time","reserved_by","department","purpose","status")
        tree=self.tree(win,cols)
        for r in sorted(rows,key=lambda x:(x.get("date",""),x.get("resource_id",""),x.get("start_time",""))):
            try: d=datetime.strptime(r.get("date",""),"%Y-%m-%d").date()
            except ValueError: continue
            if start<=d<=end:
                tree.insert("","end",values=(r.get("resource_id",""),r.get("date",""),f"{r.get('start_time','')} - {r.get('end_time','')}",r.get("reserved_by",""),r.get("department",""),r.get("purpose",""),r.get("status","")))
        if not tree.get_children(): tk.Label(win,text="No reservations in this period.",bg="#eef4fb",fg="#60758a").pack(pady=15)

    def show_department_usage(self):
        start,end=self.schedule_period()
        rows=[r for r in read_csv("reservations.csv",RESERVATION_HEADERS) if r.get("status") not in ("Cancelled","Completed")]
        totals={}
        for r in rows:
            try: d=datetime.strptime(r.get("date",""),"%Y-%m-%d").date()
            except ValueError: continue
            if start<=d<=end:
                dept=r.get("department","").strip() or "Unassigned"
                totals[dept]=totals.get(dept,0.0)+self.reservation_hours(r)
        win=tk.Toplevel(self); win.title("Department Resource Utilization"); win.geometry("650x430"); win.configure(bg="white")
        tk.Label(win,text="DEPARTMENT-WISE RESOURCE USAGE",font=("Segoe UI",16,"bold"),fg="#12395b",bg="white").pack(pady=15)
        tree=self.tree(win,("department","reserved_hours","share_percent"))
        total=sum(totals.values())
        for dept,hours in sorted(totals.items(),key=lambda x:x[1],reverse=True):
            tree.insert("","end",values=(dept,f"{hours:.1f}",f"{hours/total*100:.1f}%" if total else "0.0%"))
        if not totals: tk.Label(win,text="No department reservation data for this period.",bg="white",fg="#60758a").pack(pady=15)

    def show_schedule_conflicts(self):
        rows=read_csv("reservations.csv",RESERVATION_HEADERS); conflicts=[]
        for i,a in enumerate(rows):
            if a.get("status") in ("Cancelled","Completed"): continue
            for b in rows[i+1:]:
                if b.get("status") in ("Cancelled","Completed") or a.get("resource_id")!=b.get("resource_id") or a.get("date")!=b.get("date"): continue
                pa=self.valid_reservation_times(a.get("date",""),a.get("start_time",""),a.get("end_time","")); pb=self.valid_reservation_times(b.get("date",""),b.get("start_time",""),b.get("end_time",""))
                if pa and pb and self.reservation_overlap(pa[1],pa[2],pb[1],pb[2]):
                    conflicts.append((a,b))
        win=tk.Toplevel(self); win.title("Scheduling Conflicts"); win.geometry("900x420"); win.configure(bg="white")
        tk.Label(win,text="SCHEDULING CONFLICTS",font=("Segoe UI",16,"bold"),fg="#12395b",bg="white").pack(pady=15)
        tree=self.tree(win,("resource_id","date","reservation_1","time_1","reservation_2","time_2"))
        for a,b in conflicts:
            tree.insert("","end",values=(a.get("resource_id",""),a.get("date",""),a.get("reservation_id",""),f"{a.get('start_time')} - {a.get('end_time')}",b.get("reservation_id",""),f"{b.get('start_time')} - {b.get('end_time')}"))
        if not conflicts: tk.Label(win,text="No overlapping active/pending reservations found.",bg="white",fg="#4b7650",font=("Segoe UI",11,"bold")).pack(pady=20)
        self.audit("SCHEDULE_CONFLICT_CHECK",f"{len(conflicts)} conflict(s) found")

    def find_available_slot(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS)
        win=tk.Toplevel(self); win.title("Smart Availability Recommendation"); win.geometry("520x500"); win.configure(bg="white")
        tk.Label(win,text="SMART AVAILABILITY",font=("Segoe UI",18,"bold"),fg="#12395b",bg="white").pack(pady=(22,5))
        tk.Label(win,text="Choose a date and duration; the system finds the first free resource slot.",bg="white",fg="#60758a").pack(pady=(0,18))
        date_e=tk.Entry(win,font=("Segoe UI",11)); date_e.insert(0,datetime.now().strftime("%Y-%m-%d")); date_e.pack(fill="x",padx=35,ipady=7)
        dur_e=tk.Entry(win,font=("Segoe UI",11)); dur_e.insert(0,"1"); dur_e.pack(fill="x",padx=35,ipady=7)
        result=tk.Text(win,font=("Consolas",10),bg="#f7fbff",fg="#12395b",height=12,bd=0,padx=10,pady=10); result.pack(fill="both",expand=True,padx=35,pady=15)
        def find():
            try: date=datetime.strptime(date_e.get().strip(),"%Y-%m-%d").date(); duration=float(dur_e.get().strip())
            except ValueError: messagebox.showwarning("Invalid Input","Enter date as YYYY-MM-DD and duration as a number of hours.",parent=win); return
            if duration<=0 or duration>OPERATING_HOURS_PER_DAY: messagebox.showwarning("Invalid Duration",f"Duration must be between 0 and {OPERATING_HOURS_PER_DAY} hours.",parent=win); return
            results=[]
            for r in resources:
                if r.get("status")!="Available": continue
                rid=r.get("resource_id","")
                bookings=[x for x in read_csv("reservations.csv",RESERVATION_HEADERS) if x.get("resource_id")==rid and x.get("date")==date.strftime("%Y-%m-%d") and x.get("status") not in ("Cancelled","Completed")]
                cursor=9*60
                while cursor+int(duration*60)<=17*60:
                    st=f"{cursor//60:02d}:{cursor%60:02d}"; enm=cursor+int(duration*60); en=f"{enm//60:02d}:{enm%60:02d}"
                    if not self.find_reservation_conflicts(rid,date.strftime("%Y-%m-%d"),st,en): results.append((rid,r.get("name",""),r.get("department",""),st,en)); break
                    cursor+=30
            result.delete("1.0","end")
            if results:
                result.insert("1.0","SMART RECOMMENDATIONS\n\n"+"\n".join(f"{rid} | {name} | {dept or 'Unassigned'} | {st}-{en}" for rid,name,dept,st,en in results))
            else: result.insert("1.0","No free slot found for the requested date and duration.")
        tk.Button(win,text="Find Free Slots",command=find,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=(0,20))

    def maintenance_id(self):
        rows=read_csv("maintenance.csv",MAINTENANCE_HEADERS)
        nums=[int(r.get("maintenance_id","")[1:]) for r in rows if r.get("maintenance_id","").startswith("M") and r.get("maintenance_id","")[1:].isdigit()]
        return f"M{max(nums,default=0)+1:03d}"

    def resource_health_score(self,rid):
        resources=read_csv("resources.csv",RESOURCE_HEADERS); complaints=read_csv("complaints.csv",COMPLAINT_HEADERS); maint=read_csv("maintenance.csv",MAINTENANCE_HEADERS)
        r=next((x for x in resources if x.get("resource_id")==rid),None)
        if not r: return 0,["Resource not found"]
        score=100; reasons=[]
        cond=r.get("condition","Good")
        deductions={"Excellent":0,"Good":0,"Fair":10,"Poor":25,"Critical":40}
        score-=deductions.get(cond,5)
        if cond in ("Poor","Critical"): reasons.append(f"Condition: {cond}")
        open_high=sum(1 for x in complaints if x.get("resource_id")==rid and x.get("priority") in ("High","Critical") and x.get("status") not in ("Resolved","Closed"))
        score-=min(30,open_high*10)
        if open_high: reasons.append(f"{open_high} unresolved high/critical complaint(s)")
        overdue=0; today=datetime.now().date()
        nxt=r.get("next_maintenance","").strip()
        if nxt:
            try:
                overdue=(datetime.strptime(nxt,"%Y-%m-%d").date()<today)
            except ValueError: overdue=True
        if overdue: score-=20; reasons.append("Maintenance overdue/invalid")
        count=sum(1 for x in maint if x.get("resource_id")==rid)
        if count>=5: score-=10; reasons.append("High maintenance frequency")
        elif count>=3: score-=5; reasons.append("Repeated maintenance history")
        return max(0,min(100,score)),reasons

    def build_resource_health(self):
        bar=tk.Frame(self.health_tab,bg="#eef4fb"); bar.pack(fill="x",padx=15,pady=12)
        tk.Button(bar,text="Refresh Health",command=self.refresh_resource_health,bg="#0b4f8a",fg="white",bd=0,padx=14,pady=8).pack(side="left")
        tk.Button(bar,text="+ Maintenance Record",command=self.add_maintenance_record,bg="#376a92",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=6)
        tk.Button(bar,text="Maintenance History",command=self.show_maintenance_history,bg="#657789",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=6)
        tk.Button(bar,text="Health Alerts",command=self.show_health_alerts,bg="#8a5a0b",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=6)
        self.health_tree=self.tree(self.health_tab,("resource_id","name","condition","status","maintenance_count","last_maintenance","next_maintenance","health_score","risk"))
        self.refresh_resource_health()

    def refresh_resource_health(self):
        if not hasattr(self,"health_tree"): return
        rows=read_csv("resources.csv",RESOURCE_HEADERS); maint=read_csv("maintenance.csv",MAINTENANCE_HEADERS)
        for x in self.health_tree.get_children(): self.health_tree.delete(x)
        for r in rows:
            rid=r.get("resource_id",""); score,reasons=self.resource_health_score(rid); count=sum(x.get("resource_id")==rid for x in maint)
            risk="High" if score<50 else "Medium" if score<75 else "Low"
            self.health_tree.insert("","end",values=(rid,r.get("name",""),r.get("condition",""),r.get("status",""),count,r.get("last_maintenance",""),r.get("next_maintenance",""),f"{score}/100",risk))

    def add_maintenance_record(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS)
        if not resources: messagebox.showwarning("No Resources","Add a resource first."); return
        win=tk.Toplevel(self); win.title("Maintenance Record"); win.geometry("500x620"); win.configure(bg="white")
        tk.Label(win,text="MAINTENANCE RECORD",font=("Segoe UI",18,"bold"),fg="#12395b",bg="white").pack(pady=20)
        labels=("Date (YYYY-MM-DD)","Description","Cost","Performed By","Next Due (YYYY-MM-DD)")
        keys=("date","description","cost","performed_by","next_due"); fields={}
        rm=tk.StringVar()
        ttk.Combobox(win,textvariable=rm,values=[f"{r.get('resource_id')} - {r.get('name')}" for r in resources],state="readonly").pack(fill="x",padx=30,pady=8)
        mt=tk.StringVar(value="Preventive"); ttk.Combobox(win,textvariable=mt,values=MAINTENANCE_TYPES,state="readonly").pack(fill="x",padx=30,pady=8)
        for label,key in zip(labels,keys):
            tk.Label(win,text=label,bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(8,3))
            e=tk.Entry(win); e.pack(fill="x",padx=30,ipady=6); fields[key]=e
        fields["date"].insert(0,datetime.now().strftime("%Y-%m-%d")); fields["performed_by"].insert(0,self.user.name)
        def save():
            selected=rm.get(); rid=selected.split(" - ",1)[0] if selected else ""
            d=self.parse_report_date(fields["date"].get()); nxt=fields["next_due"].get().strip()
            if not rid or not d or not fields["description"].get().strip() or not fields["cost"].get().strip(): messagebox.showwarning("Required","Complete resource, date, description and cost.",parent=win); return
            try: cost=float(fields["cost"].get())
            except ValueError: messagebox.showwarning("Invalid Cost","Enter a valid numeric maintenance cost.",parent=win); return
            if cost<0: messagebox.showwarning("Invalid Cost","Cost cannot be negative.",parent=win); return
            if nxt and not self.parse_report_date(nxt): messagebox.showwarning("Invalid Date","Next Due must be YYYY-MM-DD.",parent=win); return
            row={"maintenance_id":self.maintenance_id(),"resource_id":rid,"date":d.strftime("%Y-%m-%d"),"type":mt.get(),"description":fields["description"].get().strip(),"cost":f"{cost:.2f}","performed_by":fields["performed_by"].get().strip(),"next_due":nxt,"status":st.get()}
            append_csv("maintenance.csv",MAINTENANCE_HEADERS,row)
            resources=read_csv("resources.csv",RESOURCE_HEADERS)
            for r in resources:
                if r.get("resource_id")==rid:
                    r["last_maintenance"]=row["date"]
                    if nxt: r["next_maintenance"]=nxt
                    r["status"]="Available" if r.get("status")=="Maintenance" else r.get("status","Available")
            rewrite_csv("resources.csv",RESOURCE_HEADERS,resources)
            self.audit("MAINTENANCE_RECORDED",row["maintenance_id"]+" | "+rid+" | "+row["cost"])
            self.notify("MAINTENANCE","Maintenance Recorded",f"{rid} maintenance recorded on {row['date']}.")
            win.destroy(); self.refresh_resource_health(); self.refresh_resources(); self.refresh_alerts(); self.refresh_analytics(); self.refresh_notifications(); self.refresh_audit()
        tk.Button(win,text="Save Maintenance Record",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=22)

    def show_maintenance_history(self):
        win=tk.Toplevel(self); win.title("Maintenance History"); win.geometry("1050x560"); win.configure(bg="#eef4fb")
        tk.Label(win,text="MAINTENANCE HISTORY & COST",font=("Segoe UI",17,"bold"),fg="#12395b",bg="#eef4fb").pack(pady=15)
        tree=self.tree(win,MAINTENANCE_HEADERS)
        rows=read_csv("maintenance.csv",MAINTENANCE_HEADERS)
        for r in reversed(rows): tree.insert("","end",values=tuple(r.get(k,"") for k in MAINTENANCE_HEADERS))
        total=sum(float(r.get("cost",0) or 0) for r in rows if str(r.get("cost","")).replace(".","",1).isdigit())
        tk.Label(win,text=f"Total recorded maintenance cost: {total:.2f}",bg="#eef4fb",fg="#12395b",font=("Segoe UI",11,"bold")).pack(pady=10)

    def show_health_alerts(self):
        rows=read_csv("resources.csv",RESOURCE_HEADERS); alerts=[]
        for r in rows:
            score,reasons=self.resource_health_score(r.get("resource_id",""))
            if score<75: alerts.append(f"{r.get('resource_id')} - {r.get('name')}: {score}/100 | "+("; ".join(reasons) or "Review resource"))
        win=tk.Toplevel(self); win.title("Resource Health Alerts"); win.geometry("850x430"); win.configure(bg="white")
        tk.Label(win,text="RESOURCE HEALTH ALERTS",font=("Segoe UI",16,"bold"),fg="#12395b",bg="white").pack(pady=15)
        txt=tk.Text(win,font=("Consolas",10),bg="white",fg="#345",bd=0,padx=20,pady=15); txt.pack(fill="both",expand=True,padx=20,pady=10)
        txt.insert("1.0","No elevated health risks detected." if not alerts else "\n".join("• "+x for x in alerts))
        self.audit("HEALTH_ALERT_CHECK",f"{len(alerts)} resource health alert(s)")

    def build_maintenance_planning(self):
        bar=tk.Frame(self.maintenance_plan_tab,bg="#eef4fb"); bar.pack(fill="x",padx=15,pady=12)
        tk.Button(bar,text="Refresh Planning",command=self.refresh_maintenance_planning,bg="#0b4f8a",fg="white",bd=0,padx=14,pady=8).pack(side="left")
        tk.Button(bar,text="+ Plan Maintenance",command=self.add_planned_maintenance,bg="#376a92",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=6)
        tk.Button(bar,text="Cost Analytics",command=self.show_maintenance_cost_analytics,bg="#657789",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=6)
        tk.Button(bar,text="Maintenance Calendar",command=self.show_maintenance_calendar,bg="#8a5a0b",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=6)
        self.plan_tree=self.tree(self.maintenance_plan_tab,("maintenance_id","resource_id","date","type","cost","status","performed_by","next_due"))
        self.refresh_maintenance_planning()

    def refresh_maintenance_planning(self):
        if not hasattr(self,"plan_tree"): return
        for x in self.plan_tree.get_children(): self.plan_tree.delete(x)
        rows=read_csv("maintenance.csv",MAINTENANCE_HEADERS)
        for r in sorted(rows,key=lambda x:x.get("date","")): self.plan_tree.insert("","end",values=tuple(r.get(k,"") for k in ("maintenance_id","resource_id","date","type","cost","status","performed_by","next_due")))

    def add_planned_maintenance(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS)
        win=tk.Toplevel(self); win.title("Plan Maintenance"); win.geometry("520x650"); win.configure(bg="white")
        tk.Label(win,text="PLAN MAINTENANCE",font=("Segoe UI",18,"bold"),fg="#12395b",bg="white").pack(pady=20)
        rm=tk.StringVar()
        ttk.Combobox(win,textvariable=rm,values=[f"{r.get('resource_id')} - {r.get('name')}" for r in resources],state="readonly").pack(fill="x",padx=30,pady=8)
        mt=tk.StringVar(value="Preventive"); ttk.Combobox(win,textvariable=mt,values=MAINTENANCE_TYPES,state="readonly").pack(fill="x",padx=30,pady=8)
        st=tk.StringVar(value="Planned"); ttk.Combobox(win,textvariable=st,values=MAINTENANCE_STATUSES,state="readonly").pack(fill="x",padx=30,pady=8)
        fields={}
        for label,key,default in (("Planned Date (YYYY-MM-DD)","date",datetime.now().strftime("%Y-%m-%d")),("Estimated Cost","cost","0"),("Technician / Assigned To","performed_by",self.user.name),("Description","description",""),("Next Due (YYYY-MM-DD)","next_due","")):
            tk.Label(win,text=label,bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(8,3))
            e=tk.Entry(win); e.pack(fill="x",padx=30,ipady=6); e.insert(0,default); fields[key]=e
        def save():
            selected=rm.get(); rid=selected.split(" - ",1)[0] if selected else ""
            d=self.parse_report_date(fields["date"].get()); nxt=fields["next_due"].get().strip()
            try: cost=float(fields["cost"].get())
            except ValueError: messagebox.showwarning("Invalid Cost","Enter a valid estimated cost.",parent=win); return
            if not rid or not d or cost<0 or (nxt and not self.parse_report_date(nxt)): messagebox.showwarning("Invalid Input","Check resource, planned date, cost and next-due date.",parent=win); return
            row={"maintenance_id":self.maintenance_id(),"resource_id":rid,"date":d.strftime("%Y-%m-%d"),"type":mt.get(),"description":fields["description"].get().strip(),"cost":f"{cost:.2f}","performed_by":fields["performed_by"].get().strip(),"next_due":nxt,"status":st.get()}
            append_csv("maintenance.csv",MAINTENANCE_HEADERS,row)
            self.audit("MAINTENANCE_PLANNED",row["maintenance_id"]+" | "+rid+" | "+row["date"])
            win.destroy(); self.refresh_maintenance_planning(); self.refresh_resource_health(); self.refresh_audit()

        tk.Button(win,text="Save Maintenance Plan",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=22)

    def show_maintenance_cost_analytics(self):
        rows=read_csv("maintenance.csv",MAINTENANCE_HEADERS)
        costs={}
        types={}
        months={}
        for r in rows:
            try: cost=float(r.get("cost","0") or 0)
            except ValueError: cost=0
            rid=r.get("resource_id","Unknown"); costs[rid]=costs.get(rid,0)+cost
            typ=r.get("type","Other"); types[typ]=types.get(typ,0)+cost
            date=self.parse_report_date(r.get("date",""))
            if date:
                key=date.strftime("%Y-%m"); months[key]=months.get(key,0)+cost
        total=sum(costs.values())
        win=tk.Toplevel(self); win.title("Maintenance Cost Analytics"); win.geometry("900x600"); win.configure(bg="#eef4fb")
        tk.Label(win,text="MAINTENANCE COST ANALYTICS",font=("Segoe UI",18,"bold"),fg="#12395b",bg="#eef4fb").pack(pady=15)
        summary=tk.Text(win,font=("Consolas",11),bg="white",fg="#345",bd=0,padx=20,pady=15,height=14); summary.pack(fill="both",expand=True,padx=20,pady=10)
        lines=["TOTAL MAINTENANCE COST",f"{total:.2f}","","RESOURCE-WISE COST"]
        lines += [f"{k}: {v:.2f}" for k,v in sorted(costs.items(),key=lambda x:x[1],reverse=True)]
        lines += ["","TYPE-WISE COST"]+[f"{k}: {v:.2f}" for k,v in sorted(types.items(),key=lambda x:x[1],reverse=True)]
        lines += ["","MONTHLY COST TREND"]+[f"{k}: {v:.2f}" for k,v in sorted(months.items())]
        summary.insert("1.0","\n".join(lines)); self.audit("MAINTENANCE_COST_ANALYTICS",f"Total cost {total:.2f}")

    def show_maintenance_calendar(self):
        rows=read_csv("maintenance.csv",MAINTENANCE_HEADERS); win=tk.Toplevel(self); win.title("Maintenance Calendar"); win.geometry("900x500"); win.configure(bg="#eef4fb")
        tk.Label(win,text="MAINTENANCE CALENDAR",font=("Segoe UI",17,"bold"),fg="#12395b",bg="#eef4fb").pack(pady=15)
        tree=self.tree(win,("date","resource_id","type","status","cost","assigned_to"))
        for r in sorted(rows,key=lambda x:x.get("date","")):
            tree.insert("","end",values=(r.get("date",""),r.get("resource_id",""),r.get("type",""),r.get("status",""),r.get("cost",""),r.get("performed_by","")))
        self.audit("MAINTENANCE_CALENDAR_VIEWED",f"{len(rows)} record(s)")

    def predictive_metrics(self,rid):
        score,reasons=self.resource_health_score(rid)
        maintenance=read_csv("maintenance.csv",MAINTENANCE_HEADERS); complaints=read_csv("complaints.csv",COMPLAINT_HEADERS)
        today=datetime.now().date()
        history=[r for r in maintenance if r.get("resource_id")==rid]
        recent_cut=today-timedelta(days=365)
        recent=[r for r in history if self.parse_report_date(r.get("date","")) and self.parse_report_date(r.get("date",""))>=recent_cut]
        freq=len(recent)
        costs=[]
        for r in history:
            try: costs.append(float(r.get("cost","0") or 0))
            except ValueError: pass
        avg_cost=sum(costs)/len(costs) if costs else 0
        overdue_days=0
        resources=read_csv("resources.csv",RESOURCE_HEADERS); resource=next((r for r in resources if r.get("resource_id")==rid),{})
        nxt=resource.get("next_maintenance","").strip()
        if nxt:
            try: overdue_days=max(0,(today-datetime.strptime(nxt,"%Y-%m-%d").date()).days)
            except ValueError: overdue_days=30
        high=sum(1 for c in complaints if c.get("resource_id")==rid and c.get("priority") in ("High","Critical") and c.get("status") not in ("Resolved","Closed"))
        risk_score=(100-score)+(freq*4)+(high*8)+(min(30,overdue_days))
        risk="Critical" if risk_score>=80 else "High" if risk_score>=50 else "Medium" if risk_score>=25 else "Low"
        if risk in ("Critical","High") or overdue_days>0: recommendation="Schedule preventive maintenance immediately"
        elif freq>=3: recommendation="Shorten maintenance interval and inspect resource"
        elif avg_cost>0: recommendation="Continue preventive monitoring and track maintenance cost"
        else: recommendation="Establish a preventive maintenance baseline"
        return score,risk,freq,len(history),avg_cost,overdue_days,recommendation

    def build_predictive_maintenance(self):
        bar=tk.Frame(self.prediction_tab,bg="#eef4fb"); bar.pack(fill="x",padx=15,pady=12)
        tk.Button(bar,text="Refresh Predictions",command=self.refresh_predictive_maintenance,bg="#0b4f8a",fg="white",bd=0,padx=14,pady=8).pack(side="left")
        tk.Button(bar,text="Generate Alerts",command=self.generate_predictive_alerts,bg="#8a5a0b",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=6)
        tk.Button(bar,text="Risk Analysis",command=self.show_predictive_risk_analysis,bg="#657789",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=6)
        tk.Button(bar,text="Maintenance Recommendations",command=self.show_maintenance_recommendations,bg="#376a92",fg="white",bd=0,padx=14,pady=8).pack(side="left",padx=6)
        self.prediction_tree=self.tree(self.prediction_tab,("resource_id","health_score","risk_level","failure_frequency","maintenance_count","avg_cost","overdue_days","recommendation"))
        self.refresh_predictive_maintenance()

    def refresh_predictive_maintenance(self):
        if not hasattr(self,"prediction_tree"): return
        for x in self.prediction_tree.get_children(): self.prediction_tree.delete(x)
        for r in read_csv("resources.csv",RESOURCE_HEADERS):
            m=self.predictive_metrics(r.get("resource_id",""))
            self.prediction_tree.insert("","end",values=(r.get("resource_id",""),f"{m[0]}/100",m[1],m[2],m[3],f"{m[4]:.2f}",m[5],m[6]))

    def generate_predictive_alerts(self):
        alerts=0
        for r in read_csv("resources.csv",RESOURCE_HEADERS):
            rid=r.get("resource_id",""); m=self.predictive_metrics(rid)
            if m[1] in ("High","Critical"):
                self.notify("PREDICTIVE","Predictive Maintenance Risk",f"{rid} has {m[1]} failure risk. Recommendation: {m[6]}")
                alerts+=1
        self.audit("PREDICTIVE_ALERTS_GENERATED",f"{alerts} alert(s)")
        self.refresh_notifications()
        messagebox.showinfo("Predictive Alerts",f"{alerts} predictive maintenance alert(s) generated.")

    def show_predictive_risk_analysis(self):
        rows=[]
        for r in read_csv("resources.csv",RESOURCE_HEADERS):
            m=self.predictive_metrics(r.get("resource_id",""))
            rows.append((r.get("resource_id",""),r.get("name",""),m[0],m[1],m[2],m[3],m[4],m[5]))
        rows.sort(key=lambda x:({"Critical":0,"High":1,"Medium":2,"Low":3}[x[3]],-x[2]))
        win=tk.Toplevel(self); win.title("Predictive Risk Analysis"); win.geometry("980x520"); win.configure(bg="#eef4fb")
        tk.Label(win,text="PREDICTIVE FAILURE RISK ANALYSIS",font=("Segoe UI",17,"bold"),fg="#12395b",bg="#eef4fb").pack(pady=15)
        tree=self.tree(win,("resource_id","name","health","risk","failure_frequency","maintenance_count","avg_cost","overdue_days"))
        for row in rows: tree.insert("","end",values=(row[0],row[1],f"{row[2]}/100",row[3],row[4],row[5],f"{row[6]:.2f}",row[7]))
        self.audit("PREDICTIVE_RISK_ANALYSIS","Viewed predictive failure risk analysis")

    def show_maintenance_recommendations(self):
        win=tk.Toplevel(self); win.title("Smart Maintenance Recommendations"); win.geometry("850x480"); win.configure(bg="white")
        tk.Label(win,text="SMART MAINTENANCE RECOMMENDATIONS",font=("Segoe UI",16,"bold"),fg="#12395b",bg="white").pack(pady=15)
        txt=tk.Text(win,font=("Consolas",10),bg="white",fg="#345",bd=0,padx=20,pady=15); txt.pack(fill="both",expand=True,padx=20,pady=10)
        lines=[]
        for r in read_csv("resources.csv",RESOURCE_HEADERS):
            m=self.predictive_metrics(r.get("resource_id",""))
            if m[1]!="Low" or m[5]>0:
                lines.append(f"{r.get('resource_id')} - {r.get('name')}: {m[1]} risk | {m[6]}")
        txt.insert("1.0","No immediate recommendations." if not lines else "\n".join("• "+x for x in lines))
        self.audit("MAINTENANCE_RECOMMENDATIONS","Generated smart maintenance recommendations")

    def build_complaints(self):
        bar=tk.Frame(self.complaint_tab);bar.pack(fill="x",padx=15,pady=12);tk.Button(bar,text="+ New Complaint",command=self.add_complaint,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left");tk.Button(bar,text="Refresh",command=self.refresh_complaints,padx=15,pady=7).pack(side="left",padx=8)
        if self.user.role in ("Admin","Faculty"):tk.Button(bar,text="Update Selected",command=self.update_complaint,bg="#376a92",fg="white",bd=0,padx=12,pady=7).pack(side="left",padx=5)
        tk.Label(bar,text="Search:",font=("Segoe UI",10,"bold")).pack(side="left",padx=(12,4));self.complaint_search=tk.StringVar();tk.Entry(bar,textvariable=self.complaint_search,width=22).pack(side="left",ipady=5);self.complaint_search.trace_add("write",lambda *a:self.refresh_complaints());self.complaint_tree=self.tree(self.complaint_tab,("complaint_id","resource_id","title","category","priority","status","reported_by"));self.refresh_complaints()
    def refresh_complaints(self):
        if not hasattr(self,"complaint_tree"):return
        for x in self.complaint_tree.get_children():self.complaint_tree.delete(x)
        term=getattr(self,"complaint_search",tk.StringVar()).get().lower().strip()
        for c in read_csv("complaints.csv",COMPLAINT_HEADERS):
            if not term or term in " ".join(c.values()).lower():self.complaint_tree.insert("","end",values=tuple(c.get(k,"") for k in ("complaint_id","resource_id","title","category","priority","status","reported_by")))
        self.refresh_cards()
    def update_complaint(self):
        item=self.complaint_tree.selection()
        if not item:messagebox.showwarning("Select Complaint","Select a complaint first.");return
        cid=self.complaint_tree.item(item[0],"values")[0];rows=read_csv("complaints.csv",COMPLAINT_HEADERS);current=next((r for r in rows if r.get("complaint_id")==cid),None)
        if not current:return
        win=tk.Toplevel(self);win.title("Update Complaint");win.geometry("430x300");tk.Label(win,text=f"{cid} - {current['title']}",font=("Segoe UI",11,"bold")).pack(pady=18);status=tk.StringVar(value=current.get("status","Pending"));ttk.Combobox(win,textvariable=status,values=STATUSES,state="readonly").pack(fill="x",padx=30,pady=8);tk.Label(win,text="Assigned To").pack(anchor="w",padx=30);assigned=tk.Entry(win);assigned.insert(0,current.get("assigned_to",""));assigned.pack(fill="x",padx=30,ipady=6)
        def save():
            current["status"]=status.get();current["assigned_to"]=assigned.get().strip();rewrite_csv("complaints.csv",COMPLAINT_HEADERS,rows);self.audit("COMPLAINT_UPDATED",cid);win.destroy();self.refresh_complaints();self.refresh_alerts();self.refresh_analytics();self.refresh_audit()
        tk.Button(win,text="Save Changes",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=8).pack(pady=20)
    def add_complaint(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS)
        if not resources:messagebox.showwarning("No resources","Add a resource first.");return
        win=tk.Toplevel(self);win.title("New Maintenance Complaint");win.geometry("520x560");win.configure(bg="white")
        def field(label):
            tk.Label(win,text=label,bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(12,3));e=tk.Entry(win,font=("Segoe UI",11));e.pack(fill="x",padx=30,ipady=6);return e
        title=field("Complaint Title");desc=field("Description");tk.Label(win,text="Resource",bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(12,3));rm=tk.StringVar();ttk.Combobox(win,textvariable=rm,values=[f'{r.get("resource_id")} - {r.get("name")}' for r in resources],state="readonly").pack(fill="x",padx=30);tk.Label(win,text="Category",bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(12,3));cm=tk.StringVar(value=CATEGORIES[0]);ttk.Combobox(win,textvariable=cm,values=CATEGORIES,state="readonly").pack(fill="x",padx=30);tk.Label(win,text="Priority",bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(12,3));pm=tk.StringVar(value="Medium");ttk.Combobox(win,textvariable=pm,values=PRIORITIES,state="readonly").pack(fill="x",padx=30)
        def save():
            selected=rm.get()
            if not title.get().strip() or not desc.get().strip() or not selected:messagebox.showwarning("Required","Complete all fields.",parent=win);return
            rows=read_csv("complaints.csv",COMPLAINT_HEADERS);nums=[int(r.get("complaint_id","")[1:]) for r in rows if r.get("complaint_id","").startswith("C") and r.get("complaint_id","")[1:].isdigit()];cid=f"C{max(nums,default=0)+1:03d}";rid=selected.split(" - ",1)[0];append_csv("complaints.csv",COMPLAINT_HEADERS,{"complaint_id":cid,"resource_id":rid,"title":title.get().strip(),"description":desc.get().strip(),"category":cm.get(),"priority":pm.get(),"reported_by":self.user.name,"status":"Pending","assigned_to":""});self.audit("COMPLAINT_CREATED",cid);win.destroy();self.refresh_complaints();self.refresh_alerts();self.refresh_analytics();self.refresh_audit()
        tk.Button(win,text="Register Complaint",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=25)
    def build_usage(self):
        bar=tk.Frame(self.usage_tab);bar.pack(fill="x",padx=15,pady=12);tk.Button(bar,text="+ Record Usage",command=self.add_usage,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left");tk.Button(bar,text="Refresh",command=self.refresh_usage,padx=15,pady=7).pack(side="left",padx=8);tk.Button(bar,text="Release Resource",command=self.release_resource,bg="#376a92",fg="white",bd=0,padx=12,pady=7).pack(side="left",padx=5);self.usage_tree=self.tree(self.usage_tab,("usage_id","resource_id","used_by","purpose","date","duration"));self.refresh_usage()
    def refresh_usage(self):
        if not hasattr(self,"usage_tree"):return
        for x in self.usage_tree.get_children():self.usage_tree.delete(x)
        for u in read_csv("usage.csv",USAGE_HEADERS):self.usage_tree.insert("","end",values=tuple(u.get(k,"") for k in USAGE_HEADERS))
        self.refresh_cards()
    def release_resource(self):
        item=self.usage_tree.selection()
        if not item:messagebox.showwarning("Select Usage","Select a usage record first.");return
        rid=self.usage_tree.item(item[0],"values")[1];rows=read_csv("resources.csv",RESOURCE_HEADERS)
        for r in rows:
            if r.get("resource_id")==rid and r.get("status")=="In Use":r["status"]="Available"
        rewrite_csv("resources.csv",RESOURCE_HEADERS,rows);self.audit("RESOURCE_RELEASED",rid);self.refresh_resources();self.refresh_alerts();self.refresh_analytics();self.refresh_audit();messagebox.showinfo("Resource Released",f"{rid} is now Available.")
    def parse_report_date(self,value):
        value=(value or "").strip()
        for fmt in ("%Y-%m-%d","%d-%m-%Y","%d/%m/%Y"):
            try: return datetime.strptime(value,fmt).date()
            except ValueError: pass
        return None

    def build_report_filters(self,parent):
        box=tk.LabelFrame(parent,text="Advanced Filters",bg="white",fg="#12395b",font=("Segoe UI",10,"bold"),padx=10,pady=8)
        box.pack(fill="x",padx=15,pady=(0,8))
        self.report_from=tk.StringVar(); self.report_to=tk.StringVar(); self.report_resource=tk.StringVar(value="All"); self.report_status=tk.StringVar(value="All"); self.report_priority=tk.StringVar(value="All")
        for label,var in (("From (YYYY-MM-DD)",self.report_from),("To (YYYY-MM-DD)",self.report_to)):
            tk.Label(box,text=label,bg="white",fg="#456").pack(side="left",padx=(0,5))
            tk.Entry(box,textvariable=var,width=13).pack(side="left",padx=(0,12))
        tk.Label(box,text="Resource",bg="white",fg="#456").pack(side="left")
        ttk.Combobox(box,textvariable=self.report_resource,values=["All"]+[r.get("resource_id","") for r in read_csv("resources.csv",RESOURCE_HEADERS)],width=14,state="readonly").pack(side="left",padx=(5,12))
        tk.Label(box,text="Status",bg="white",fg="#456").pack(side="left")
        ttk.Combobox(box,textvariable=self.report_status,values=["All"]+list(RESOURCE_STATUSES)+list(STATUSES),width=15,state="readonly").pack(side="left",padx=(5,12))
        tk.Label(box,text="Priority",bg="white",fg="#456").pack(side="left")
        ttk.Combobox(box,textvariable=self.report_priority,values=["All"]+list(PRIORITIES),width=10,state="readonly").pack(side="left",padx=(5,12))
        tk.Button(box,text="Apply Filters",command=self.refresh_report_center,bg="#0b4f8a",fg="white",bd=0,padx=10,pady=5).pack(side="left",padx=4)
        tk.Button(box,text="Clear Filters",command=self.clear_report_filters,bg="#6b7d8f",fg="white",bd=0,padx=10,pady=5).pack(side="left",padx=4)

    def clear_report_filters(self):
        self.report_from.set(""); self.report_to.set(""); self.report_resource.set("All"); self.report_status.set("All"); self.report_priority.set("All")
        self.refresh_report_center()

    def get_filtered_report_data(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS); complaints=read_csv("complaints.csv",COMPLAINT_HEADERS); usage=read_csv("usage.csv",USAGE_HEADERS)
        resource_id=self.report_resource.get() if hasattr(self,"report_resource") else "All"
        status=self.report_status.get() if hasattr(self,"report_status") else "All"
        priority=self.report_priority.get() if hasattr(self,"report_priority") else "All"
        start=self.parse_report_date(self.report_from.get()) if hasattr(self,"report_from") else None
        end=self.parse_report_date(self.report_to.get()) if hasattr(self,"report_to") else None
        if self.report_from.get() and not start: messagebox.showwarning("Invalid Date","Use YYYY-MM-DD for the From date."); return None
        if self.report_to.get() and not end: messagebox.showwarning("Invalid Date","Use YYYY-MM-DD for the To date."); return None
        if start and end and start>end: messagebox.showwarning("Invalid Range","From date must not be after To date."); return None
        if resource_id!="All":
            resources=[r for r in resources if r.get("resource_id")==resource_id]
            complaints=[x for x in complaints if x.get("resource_id")==resource_id]
            usage=[x for x in usage if x.get("resource_id")==resource_id]
        if status!="All":
            resources=[r for r in resources if r.get("status")==status]
            complaints=[x for x in complaints if x.get("status")==status]
        if priority!="All": complaints=[x for x in complaints if x.get("priority")==priority]
        if start or end:
            def in_range(row):
                d=self.parse_report_date(row.get("date",""))
                if not d: return False
                return (not start or d>=start) and (not end or d<=end)
            usage=[x for x in usage if in_range(x)]
            complaints=[x for x in complaints if in_range(x)]
        return resources,complaints,usage

    def export_report_csv(self,filename,headers,rows):
        out=Path("reports"); out.mkdir(exist_ok=True)
        path=out/filename
        with path.open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=headers); writer.writeheader(); writer.writerows(rows)
        return path

    def build_reports(self):
        bar=tk.Frame(self.reports_tab,bg="#eef4fb"); bar.pack(fill="x",padx=15,pady=12)
        tk.Button(bar,text="Export Filtered Reports",command=self.export_all_reports,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left")
        tk.Button(bar,text="Refresh Report Center",command=self.refresh_report_center,bg="#376a92",fg="white",bd=0,padx=15,pady=8).pack(side="left",padx=8)
        self.build_report_filters(self.reports_tab)
        self.report_text=tk.Text(self.reports_tab,font=("Consolas",10),bg="white",fg="#12395b",bd=0,padx=20,pady=15)
        self.report_text.pack(fill="both",expand=True,padx=15,pady=10)
        self.refresh_report_center()

    def refresh_report_center(self):
        data=self.get_filtered_report_data()
        if not data: return
        resources,complaints,usage=data
        maintenance=[r for r in resources if r.get("status")=="Maintenance"]
        open_complaints=[x for x in complaints if x.get("status") not in ("Resolved","Closed")]
        lines=["SMART REPORTS & EXPORT CENTER","="*65,"","ACTIVE FILTERS","-"*65,
               f"Date range: {self.report_from.get() or 'Any'} to {self.report_to.get() or 'Any'}",
               f"Resource: {self.report_resource.get() or 'All'} | Status: {self.report_status.get() or 'All'} | Priority: {self.report_priority.get() or 'All'}",
               "","FILTERED REPORT COUNTS","-"*65,f"Resources: {len(resources)}",f"Complaints: {len(complaints)}",f"Usage records: {len(usage)}",f"Maintenance: {len(maintenance)}",f"Open complaints: {len(open_complaints)}","","Export folder: reports/"]
        self.report_text.delete("1.0","end"); self.report_text.insert("1.0","\n".join(lines))

    def export_all_reports(self):
        data=self.get_filtered_report_data()
        if not data: return
        resources,complaints,usage=data
        maintenance=[r for r in resources if r.get("status")=="Maintenance"]; open_complaints=[x for x in complaints if x.get("status") not in ("Resolved","Closed")]
        for filename,headers,rows in [("resource_report.csv",RESOURCE_HEADERS,resources),("complaint_report.csv",COMPLAINT_HEADERS,complaints),("usage_report.csv",USAGE_HEADERS,usage),("maintenance_report.csv",RESOURCE_HEADERS,maintenance),("open_complaints_report.csv",COMPLAINT_HEADERS,open_complaints)]:
            self.export_report_csv(filename,headers,rows)
        resolved=sum(x.get("status") in ("Resolved","Closed") for x in complaints)
        headers=["report_date","from_date","to_date","resource_filter","status_filter","priority_filter","total_resources","available","in_use","maintenance","out_of_service","total_complaints","open_complaints","resolved_or_closed","resolution_rate_percent","total_usage_records"]
        summary={"report_date":datetime.now().strftime("%Y-%m-%d"),"from_date":self.report_from.get(),"to_date":self.report_to.get(),"resource_filter":self.report_resource.get(),"status_filter":self.report_status.get(),"priority_filter":self.report_priority.get(),"total_resources":len(resources),"available":sum(r.get("status")=="Available" for r in resources),"in_use":sum(r.get("status")=="In Use" for r in resources),"maintenance":len(maintenance),"out_of_service":sum(r.get("status")=="Out of Service" for r in resources),"total_complaints":len(complaints),"open_complaints":len(open_complaints),"resolved_or_closed":resolved,"resolution_rate_percent":f"{resolved/len(complaints)*100:.1f}" if complaints else "0.0","total_usage_records":len(usage)}
        self.export_report_csv("dashboard_summary.csv",headers,[summary])
        self.audit("REPORTS_EXPORTED","Filtered reports exported")
        self.refresh_report_center()
        messagebox.showinfo("Export Complete","Filtered reports were generated successfully in the reports folder.")


