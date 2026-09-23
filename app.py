import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
import shutil
import csv
from models import User
from storage import read_csv, append_csv, rewrite_csv

RESOURCE_HEADERS=["resource_id","name","category","location","status","last_maintenance","next_maintenance"]
COMPLAINT_HEADERS=["complaint_id","resource_id","title","description","category","priority","reported_by","status","assigned_to"]
USAGE_HEADERS=["usage_id","resource_id","used_by","purpose","date","duration"]
USER_HEADERS=["username","password","role","name","status","last_login"]
CATEGORIES=("Electrical","Computer/IT","Projector","Furniture","Laboratory Equipment","Other")
PRIORITIES=("Low","Medium","High","Critical")
STATUSES=("Pending","Assigned","In Progress","Resolved","Closed")
RESOURCE_STATUSES=("Available","In Use","Maintenance","Out of Service")
DATA_FILES=("users.csv","resources.csv","complaints.csv","usage.csv")
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
        self.home_tab=ttk.Frame(notebook); self.notification_tab=ttk.Frame(notebook); self.resource_tab=ttk.Frame(notebook); self.complaint_tab=ttk.Frame(notebook); self.usage_tab=ttk.Frame(notebook); self.report_tab=ttk.Frame(notebook); self.analytics_tab=ttk.Frame(notebook); self.alert_tab=ttk.Frame(notebook); self.audit_tab=ttk.Frame(notebook)
        for tab,text in ((self.home_tab,"Dashboard"),(self.notification_tab,"Notifications"),(self.resource_tab,"Resources"),(self.complaint_tab,"Complaints"),(self.usage_tab,"Usage"),(self.report_tab,"Reports"),(self.analytics_tab,"Analytics"),(self.alert_tab,"Alerts"),(self.audit_tab,"Audit")):notebook.add(tab,text=f"  {text}  ")
        if self.user.role=="Admin":
            self.user_tab=ttk.Frame(notebook); notebook.add(self.user_tab,text="  Users  ")
            self.admin_tab=ttk.Frame(notebook); notebook.add(self.admin_tab,text="  Admin Center  ")
            self.build_backup_controls(); self.build_admin_center()
        self.build_professional_dashboard(self.home_tab); self.build_notifications(self.notification_tab); self.build_resources(); self.build_complaints(); self.build_usage(); self.build_reports(); self.build_analytics(); self.build_alerts(); self.build_audit()
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
        bar=tk.Frame(self.user_tab); bar.pack(fill="x",padx=15,pady=12); tk.Button(bar,text="+ Add User",command=self.add_user,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left"); tk.Button(bar,text="Refresh",command=self.refresh_users,padx=15,pady=7).pack(side="left",padx=8); self.user_tree=self.tree(self.user_tab,("username","role","name")); self.refresh_users()
    def refresh_users(self):
        for x in self.user_tree.get_children():self.user_tree.delete(x)
        for u in read_csv("users.csv",USER_HEADERS):self.user_tree.insert("","end",values=(u["username"],u["role"],u["name"]))
    def add_user(self):
        win=tk.Toplevel(self); win.title("Add Campus User"); win.geometry("430x390"); win.configure(bg="white"); fields={}
        for label,key in (("Username","username"),("Password","password"),("Display Name","name")):
            tk.Label(win,text=label,bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(16,3)); e=tk.Entry(win,font=("Segoe UI",11),show="*" if key=="password" else ""); e.pack(fill="x",padx=30,ipady=7); fields[key]=e
        tk.Label(win,text="Role",bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(16,3)); role=tk.StringVar(value="Faculty"); ttk.Combobox(win,textvariable=role,values=("Admin","Faculty"),state="readonly").pack(fill="x",padx=30)
        def save():
            rows=read_csv("users.csv",USER_HEADERS); vals={k:e.get().strip() for k,e in fields.items()}
            if not all(vals.values()):messagebox.showwarning("Required","Complete all fields.",parent=win); return
            if any(x["username"].lower()==vals["username"].lower() for x in rows):messagebox.showerror("Duplicate","Username already exists.",parent=win); return
            vals["role"]=role.get(); append_csv("users.csv",USER_HEADERS,vals); self.audit("USER_CREATED",vals["username"]); win.destroy(); self.refresh_users(); self.refresh_audit()
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
        if self.user.role=="Admin":tk.Button(bar,text="+ Add Resource",command=self.add_resource,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left")
        tk.Button(bar,text="Refresh",command=self.refresh_resources,padx=15,pady=7).pack(side="left",padx=8)
        if self.user.role=="Admin":
            tk.Button(bar,text="Update Status",command=self.update_resource_status,bg="#376a92",fg="white",bd=0,padx=12,pady=7).pack(side="left",padx=5); tk.Button(bar,text="Maintenance",command=self.update_maintenance,bg="#376a92",fg="white",bd=0,padx=12,pady=7).pack(side="left",padx=5)
        tk.Label(bar,text="Search:",font=("Segoe UI",10,"bold")).pack(side="left",padx=(12,4)); self.resource_search=tk.StringVar(); tk.Entry(bar,textvariable=self.resource_search,width=22).pack(side="left",ipady=5); self.resource_search.trace_add("write",lambda *a:self.refresh_resources()); self.resource_tree=self.tree(self.resource_tab,("resource_id","name","category","location","status","last_maintenance","next_maintenance")); self.refresh_resources()
    def refresh_resources(self):
        if not hasattr(self,"resource_tree"):return
        for x in self.resource_tree.get_children():self.resource_tree.delete(x)
        term=getattr(self,"resource_search",tk.StringVar()).get().lower().strip()
        for r in read_csv("resources.csv",RESOURCE_HEADERS):
            if not term or term in " ".join(r.values()).lower():self.resource_tree.insert("","end",values=tuple(r.get(k,"") for k in RESOURCE_HEADERS))
        self.refresh_cards()
    def update_resource_status(self):
        item=self.resource_tree.selection()
        if not item:messagebox.showwarning("Select Resource","Select a resource first.");return
        rid=self.resource_tree.item(item[0],"values")[0]; rows=read_csv("resources.csv",RESOURCE_HEADERS); current=next((r for r in rows if r.get("resource_id")==rid),None)
        if not current:return
        win=tk.Toplevel(self); win.title("Update Resource Status"); win.geometry("360x220"); status=tk.StringVar(value=current.get("status","Available")); ttk.Combobox(win,textvariable=status,values=RESOURCE_STATUSES,state="readonly").pack(fill="x",padx=35,pady=35)
        def save():
            for r in rows:
                if r.get("resource_id")==rid:r["status"]=status.get()
            rewrite_csv("resources.csv",RESOURCE_HEADERS,rows); self.audit("RESOURCE_STATUS_CHANGED",f"{rid} -> {status.get()}"); win.destroy(); self.refresh_resources(); self.refresh_alerts(); self.refresh_analytics(); self.refresh_audit()
        tk.Button(win,text="Save Status",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=8).pack()
    def add_resource(self):
        win=tk.Toplevel(self); win.title("Add Resource"); win.geometry("430x390"); win.configure(bg="white"); fields=[]
        for label in ("Resource Name","Category","Location"):
            tk.Label(win,text=label,bg="white",fg="#345",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(18,3)); e=tk.Entry(win,font=("Segoe UI",11)); e.pack(fill="x",padx=30,ipady=7); fields.append(e)
        def save():
            rows=read_csv("resources.csv",RESOURCE_HEADERS); nums=[int(r.get("resource_id","")[1:]) for r in rows if r.get("resource_id","").startswith("R") and r.get("resource_id","")[1:].isdigit()]; rid=f"R{max(nums,default=0)+1:03d}"; name,cat,loc=[e.get().strip() for e in fields]
            if not name or not loc:messagebox.showwarning("Required","Enter resource name and location.",parent=win);return
            append_csv("resources.csv",RESOURCE_HEADERS,{"resource_id":rid,"name":name,"category":cat or "Other","location":loc,"status":"Available","last_maintenance":"","next_maintenance":""}); self.audit("RESOURCE_CREATED",rid); win.destroy(); self.refresh_resources(); self.refresh_analytics(); self.refresh_audit()
        tk.Button(win,text="Save Resource",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=25)
    def update_maintenance(self):
        item=self.resource_tree.selection()
        if not item:messagebox.showwarning("Select Resource","Select a resource first.");return
        rid=self.resource_tree.item(item[0],"values")[0]; rows=read_csv("resources.csv",RESOURCE_HEADERS); current=next((x for x in rows if x.get("resource_id")==rid),None)
        if not current:return
        win=tk.Toplevel(self); win.title("Maintenance Schedule"); win.geometry("420x330"); win.configure(bg="white"); tk.Label(win,text=f"Maintenance: {rid}",font=("Segoe UI",13,"bold"),bg="white",fg="#12395b").pack(pady=18)
        tk.Label(win,text="Last Maintenance (YYYY-MM-DD)",bg="white").pack(anchor="w",padx=30,pady=(8,3)); last=tk.Entry(win); last.insert(0,current.get("last_maintenance","")); last.pack(fill="x",padx=30,ipady=6)
        tk.Label(win,text="Next Maintenance (YYYY-MM-DD)",bg="white").pack(anchor="w",padx=30,pady=(14,3)); nxt=tk.Entry(win); nxt.insert(0,current.get("next_maintenance","")); nxt.pack(fill="x",padx=30,ipady=6)
        def save():
            lv=last.get().strip(); nv=nxt.get().strip()
            for label,value in (("Last Maintenance",lv),("Next Maintenance",nv)):
                if value:
                    try:datetime.strptime(value,"%Y-%m-%d")
                    except ValueError:messagebox.showerror("Invalid Date",f"{label} must use YYYY-MM-DD.",parent=win);return
            if lv and nv and nv<lv:messagebox.showerror("Invalid Schedule","Next maintenance cannot be earlier than last maintenance.",parent=win);return
            for x in rows:
                if x.get("resource_id")==rid:x["last_maintenance"]=lv;x["next_maintenance"]=nv
            rewrite_csv("resources.csv",RESOURCE_HEADERS,rows);self.audit("MAINTENANCE_UPDATED",rid);win.destroy();self.refresh_resources();self.refresh_alerts();self.refresh_audit()
        tk.Button(win,text="Save Schedule",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=22)
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


