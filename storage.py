import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
DATA_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

def read_csv(filename, headers):
    path = DATA_DIR / filename
    if not path.exists():
        path.write_text(",".join(headers) + "\n", encoding="utf-8")
    try:
        with path.open("r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except (OSError, csv.Error) as exc:
        print("File error:", exc)
        return []

def append_csv(filename, headers, row):
    path = DATA_DIR / filename
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=headers).writeheader()
    try:
        with path.open("a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=headers).writerow(row)
    except (OSError, csv.Error) as exc:
        print("File error:", exc)

def rewrite_csv(filename, headers, rows):
    path = DATA_DIR / filename
    try:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, csv.Error) as exc:
        print("File error:", exc)
