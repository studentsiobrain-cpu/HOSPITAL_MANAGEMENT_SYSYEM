from pathlib import Path


APP_NAME = "AsterPrime Hospital ERP"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = DATA_DIR / "reports"
BACKUP_DIR = DATA_DIR / "backups"
LOG_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "hospital_erp.sqlite3"

ROLES = (
    "Admin",
    "Doctor",
    "Nurse",
    "Receptionist",
    "Laboratory Staff",
    "Pharmacist",
    "Accountant",
)

ROLE_PERMISSIONS = {
    "Admin": {"*"},
    "Doctor": {"dashboard", "patients", "appointments", "laboratory", "surgeries"},
    "Nurse": {"dashboard", "patients", "appointments", "wards", "inventory"},
    "Receptionist": {"dashboard", "patients", "appointments", "billing", "wards"},
    "Laboratory Staff": {"dashboard", "patients", "laboratory"},
    "Pharmacist": {"dashboard", "inventory", "billing"},
    "Accountant": {"dashboard", "billing", "employees"},
}

THEMES = {
    "light": {
        "bg": "#f5f8fb",
        "panel": "#ffffff",
        "sidebar": "#17324d",
        "sidebar_active": "#1f78b4",
        "text": "#132238",
        "muted": "#607080",
        "accent": "#0f8b8d",
        "danger": "#c0392b",
        "success": "#27823c",
        "border": "#d8e2ec",
    },
    "dark": {
        "bg": "#121820",
        "panel": "#1b2530",
        "sidebar": "#0e1721",
        "sidebar_active": "#146c94",
        "text": "#edf3f8",
        "muted": "#aebccc",
        "accent": "#2aa7a9",
        "danger": "#ff6b6b",
        "success": "#62d26f",
        "border": "#2e3b48",
    },
}


def ensure_directories() -> None:
    for path in (DATA_DIR, UPLOAD_DIR, REPORT_DIR, BACKUP_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
