import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
import shutil
from models import User
from storage import read_csv, append_csv, rewrite_csv

RESOURCE_HEADERS=["resource_id","name","category","location","status","last_maintenance","next_maintenance"]
COMPLAINT_HEADERS=["complaint_id","resource_id","title","description","category","priority","reported_by","status","assigned_to"]
USAGE_HEADERS=["usage_id","resource_id","used_by","purpose","date","duration"]
USER_HEADERS=["username","password","role","name"]
CATEGORIES=("Electrical","Computer/IT","Projector","Furniture","Laboratory Equipment","Other")
PRIORITIES=("Low","Medium","High","Critical")
STATUSES=("Pending","Assigned","In Progress","Resolved","Closed")
RESOURCE_STATUSES=("Available","In Use","Maintenance","Out of Service")
DATA_FILES=("users.csv","resources.csv","complaints.csv","usage.csv")
AUDIT_HEADERS=("timestamp","username","role","action","details")

class SmartCampusApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Smart Campus Utility Management System"); self.geometry("1180x720"); self.minsize(1000,620); self.configure(bg="#eef4fb"); self.user=None
        self.style=ttk.Style(self)
        try:self.style.theme_use("clam")
        except tk.TclError:pass
        self.style.configure("Treeview",rowheight=30,font=("Segoe UI",10)); self.style.configure("Treeview.Heading",font=("Segoe UI",10,"bold")); self.style.configure("TNotebook.Tab",padding=(18,10),font=("Segoe UI",10,"bold")); self.show_login()
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
    def show_login(self):
        self.clear(); frame=tk.Frame(self,bg="#0b4f8a",width=520,height=720); frame.pack(side="left",fill="both",expand=True); frame.pack_propagate(False)
        tk.Label(frame,text="SMART CAMPUS",font=("Segoe UI",30,"bold"),fg="white",bg="#0b4f8a").pack(pady=(150,5)); tk.Label(frame,text="UTILITY MANAGEMENT",font=("Segoe UI",20),fg="#d9ecff",bg="#0b4f8a").pack(); tk.Label(frame,text="Resource Tracking • Maintenance • Reports",font=("Segoe UI",11),fg="white",bg="#0b4f8a").pack(pady=20)
        card=tk.Frame(self,bg="white"); card.pack(side="right",fill="both",expand=True,padx=70,pady=90); tk.Label(card,text="Welcome Back",font=("Segoe UI",25,"bold"),fg="#12395b",bg="white").pack(pady=(55,5)); tk.Label(card,text="Sign in to continue",font=("Segoe UI",11),fg="#6b7b8c",bg="white").pack(pady=(0,30))
        self.login_user=self.entry(card,"Username"); self.login_pass=self.entry(card,"Password",True); self.login_pass.bind("<Return>",lambda e:self.login()); tk.Button(card,text="LOGIN",command=self.login,bg="#0b4f8a",fg="white",font=("Segoe UI",11,"bold"),bd=0,cursor="hand2",width=24,height=2).pack(pady=25); tk.Label(card,text="Demo: admin / admin123   |   faculty / faculty123",font=("Segoe UI",9),fg="#7a8794",bg="white").pack()
    def entry(self,parent,label,password=False):
        tk.Label(parent,text=label,font=("Segoe UI",10,"bold"),fg="#345",bg="white",anchor="w").pack(fill="x",padx=65,pady=(8,3)); e=tk.Entry(parent,font=("Segoe UI",12),show="•" if password else "",relief="solid",bd=1); e.pack(fill="x",padx=65,ipady=9); return e
    def login(self):
        users=read_csv("users.csv",USER_HEADERS); u=self.login_user.get().strip(); p=self.login_pass.get().strip(); row=next((x for x in users if x["username"]==u and x["password"]==p),None)
        if not row:messagebox.showerror("Login Failed","Invalid username or password."); return
        self.user=User(u,p,row["role"],row["name"]); self.show_dashboard(); self.audit("LOGIN","Successful login")
    def show_dashboard(self):
        self.clear(); top=tk.Frame(self,bg="#0b4f8a",height=76); top.pack(fill="x"); tk.Label(top,text="Smart Campus Utility Management",font=("Segoe UI",20,"bold"),fg="white",bg="#0b4f8a").pack(side="left",padx=25,pady=18); tk.Label(top,text=f"{self.user.name}  •  {self.user.role}",font=("Segoe UI",10),fg="white",bg="#0b4f8a").pack(side="right",padx=15); tk.Button(top,text="Logout",command=self.show_login,bg="#083b68",fg="white",bd=0,padx=15,pady=8).pack(side="right")
        body=tk.Frame(self,bg="#eef4fb"); body.pack(fill="both",expand=True,padx=20,pady=20); self.build_cards(body); notebook=ttk.Notebook(body); notebook.pack(fill="both",expand=True,pady=(18,0))
        self.resource_tab=ttk.Frame(notebook); self.complaint_tab=ttk.Frame(notebook); self.usage_tab=ttk.Frame(notebook); self.report_tab=ttk.Frame(notebook); self.analytics_tab=ttk.Frame(notebook); self.alert_tab=ttk.Frame(notebook); self.audit_tab=ttk.Frame(notebook)
        for tab,text in ((self.resource_tab,"Resources"),(self.complaint_tab,"Complaints"),(self.usage_tab,"Usage"),(self.report_tab,"Reports"),(self.analytics_tab,"Analytics"),(self.alert_tab,"Alerts"),(self.audit_tab,"Audit")):notebook.add(tab,text=f"  {text}  ")
        if self.user.role=="Admin":
            self.user_tab=ttk.Frame(notebook); notebook.add(self.user_tab,text="  Users  ")
            self.build_backup_controls()
        self.build_resources(); self.build_complaints(); self.build_usage(); self.build_reports(); self.build_analytics(); self.build_alerts(); self.build_audit()
        if self.user.role=="Admin":self.build_users()
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
    def build_analytics(self):
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
    def build_reports(self):
        bar=tk.Frame(self.report_tab);bar.pack(fill="x",padx=15,pady=12);tk.Button(bar,text="Refresh Summary",command=self.refresh_report_summary,bg="#0b4f8a",fg="white",bd=0,padx=15,pady=8).pack(side="left");tk.Button(bar,text="Export CSV Reports",command=self.export_reports,padx=15,pady=7).pack(side="left",padx=8);self.report_text=tk.Text(self.report_tab,font=("Consolas",11),bg="white",fg="#12395b",bd=0,padx=20,pady=20);self.report_text.pack(fill="both",expand=True,padx=15,pady=10);self.refresh_report_summary()
    def refresh_report_summary(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS);complaints=read_csv("complaints.csv",COMPLAINT_HEADERS);usage=read_csv("usage.csv",USAGE_HEADERS);lines=["SMART CAMPUS UTILITY MANAGEMENT REPORT","="*58,f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}","",f"Total Resources: {len(resources)}"]
        for st in RESOURCE_STATUSES:lines.append(f"{st}: {sum(r.get('status','')==st for r in resources)}")
        lines+=["",f"Total Complaints: {len(complaints)}"]
        for st in STATUSES:lines.append(f"{st}: {sum(c.get('status','')==st for c in complaints)}")
        for p in PRIORITIES:lines.append(f"{p} priority: {sum(c.get('priority','')==p for c in complaints)}")
        lines+=["",f"Usage Records: {len(usage)}",f"Maintenance schedules recorded: {sum(1 for r in resources if r.get('next_maintenance','').strip())}",""]
        for r in resources:lines.append(f"{r.get('resource_id')} - {r.get('name')}: {sum(u.get('resource_id')==r.get('resource_id') for u in usage)} usage record(s)")
        self.report_text.delete("1.0","end");self.report_text.insert("1.0","\n".join(lines))
    def export_reports(self):
        import csv
        out=__import__("pathlib").Path("reports");out.mkdir(exist_ok=True)
        for target,source,headers in (("resource_report.csv","resources.csv",RESOURCE_HEADERS),("complaint_report.csv","complaints.csv",COMPLAINT_HEADERS),("usage_report.csv","usage.csv",USAGE_HEADERS)):
            rows=read_csv(source,headers)
            with(out/target).open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=headers);w.writeheader();w.writerows(rows)
        messagebox.showinfo("Export Complete","Three CSV reports were saved in the reports folder.")
    def add_usage(self):
        resources=read_csv("resources.csv",RESOURCE_HEADERS);available=[r for r in resources if r.get("status","Available")=="Available"]
        if not available:messagebox.showwarning("No Available Resources","All resources are currently in use, under maintenance, or unavailable.");return
        win=tk.Toplevel(self);win.title("Record Resource Usage");win.geometry("450x360");win.configure(bg="white");tk.Label(win,text="Resource",bg="white",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(25,4));rm=tk.StringVar();ttk.Combobox(win,textvariable=rm,values=[f'{r.get("resource_id")} - {r.get("name")}' for r in available],state="readonly").pack(fill="x",padx=30);tk.Label(win,text="Purpose",bg="white",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(15,4));purpose=tk.Entry(win,font=("Segoe UI",11));purpose.pack(fill="x",padx=30,ipady=7);tk.Label(win,text="Duration",bg="white",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=30,pady=(15,4));duration=tk.Entry(win,font=("Segoe UI",11));duration.pack(fill="x",padx=30,ipady=7)
        def save():
            if not rm.get() or not purpose.get().strip():messagebox.showwarning("Required","Complete the fields.",parent=win);return
            rows=read_csv("usage.csv",USAGE_HEADERS);nums=[int(r.get("usage_id","")[1:]) for r in rows if r.get("usage_id","").startswith("U") and r.get("usage_id","")[1:].isdigit()];uid=f"U{max(nums,default=0)+1:03d}";rid=rm.get().split(" - ",1)[0]
            append_csv("usage.csv",USAGE_HEADERS,{"usage_id":uid,"resource_id":rid,"used_by":self.user.name,"purpose":purpose.get().strip(),"date":datetime.now().strftime("%Y-%m-%d"),"duration":duration.get().strip()})
            for r in resources:
                if r.get("resource_id")==rid:r["status"]="In Use"
            rewrite_csv("resources.csv",RESOURCE_HEADERS,resources);self.audit("USAGE_RECORDED",uid);win.destroy();self.refresh_usage();self.refresh_resources();self.refresh_analytics();self.refresh_alerts();self.refresh_audit()
        tk.Button(win,text="Save Usage",command=save,bg="#0b4f8a",fg="white",bd=0,padx=20,pady=9).pack(pady=25)

if __name__=="__main__":SmartCampusApp().mainloop()
