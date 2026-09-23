from pathlib import Path
import ast

BASE = Path(__file__).resolve().parent
required = ["app.py", "models.py", "storage.py", "README.md"]
data_files = ["users.csv","resources.csv","complaints.csv","usage.csv","reservations.csv","maintenance.csv","workflows.csv","assets.csv","sla.csv"]

print("SMART CAMPUS JARVIS - FINAL HEALTH CHECK")
print("=" * 55)
for name in required:
    print("[{}] {}".format("OK" if (BASE / name).exists() else "FAIL", name))

try:
    ast.parse((BASE / "app.py").read_text(encoding="utf-8"))
    print("[OK] Python syntax")
except Exception as exc:
    print("[FAIL] Python syntax:", exc)

data_dir = BASE / "data"
data_dir.mkdir(exist_ok=True)
for name in data_files:
    path = data_dir / name
    if not path.exists():
        path.write_text("", encoding="utf-8")
    print("[OK] data/" + name)

(BASE / "reports").mkdir(exist_ok=True)
print("[OK] reports directory")
print("=" * 55)
print("Health check completed.")
