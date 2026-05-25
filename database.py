import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

from .config import DB_PATH, ensure_directories


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    full_name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    staff_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_uid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK(age >= 0),
    gender TEXT NOT NULL,
    blood_group TEXT,
    address TEXT,
    phone TEXT,
    emergency_contact TEXT,
    insurance_details TEXT,
    allergies TEXT,
    existing_diseases TEXT,
    photo_path TEXT,
    document_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_uid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    specialization TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    duty_schedule TEXT,
    attendance_status TEXT DEFAULT 'Present',
    consultation_fee REAL NOT NULL DEFAULT 0,
    salary REAL NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_uid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    department TEXT,
    phone TEXT,
    salary REAL NOT NULL DEFAULT 0,
    shift TEXT,
    attendance_status TEXT DEFAULT 'Present',
    overtime_hours REAL NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_uid TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    appointment_time TEXT NOT NULL,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'Booked',
    token_number INTEGER,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES patients(id),
    FOREIGN KEY(doctor_id) REFERENCES doctors(id)
);

CREATE TABLE IF NOT EXISTS wards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    bed_type TEXT NOT NULL,
    floor INTEGER NOT NULL,
    capacity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS beds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bed_uid TEXT NOT NULL UNIQUE,
    ward_id INTEGER NOT NULL,
    room_number TEXT NOT NULL,
    bed_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Available',
    cleaning_status TEXT NOT NULL DEFAULT 'Clean',
    maintenance_status TEXT NOT NULL DEFAULT 'Operational',
    is_icu INTEGER NOT NULL DEFAULT 0,
    current_patient_id INTEGER,
    FOREIGN KEY(ward_id) REFERENCES wards(id),
    FOREIGN KEY(current_patient_id) REFERENCES patients(id)
);

CREATE TABLE IF NOT EXISTS admissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_uid TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL,
    bed_id INTEGER NOT NULL,
    admitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'Admitted',
    FOREIGN KEY(patient_id) REFERENCES patients(id),
    FOREIGN KEY(bed_id) REFERENCES beds(id)
);

CREATE TABLE IF NOT EXISTS discharges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_id INTEGER NOT NULL,
    discharged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    summary TEXT,
    follow_up_date TEXT,
    FOREIGN KEY(admission_id) REFERENCES admissions(id)
);

CREATE TABLE IF NOT EXISTS lab_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_uid TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL,
    technician_staff_id INTEGER,
    test_type TEXT NOT NULL,
    sample_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Requested',
    findings TEXT,
    report_path TEXT,
    image_reference TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES patients(id),
    FOREIGN KEY(technician_staff_id) REFERENCES staff(id)
);

CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_uid TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL,
    bill_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    category TEXT NOT NULL,
    subtotal REAL NOT NULL DEFAULT 0,
    tax_rate REAL NOT NULL DEFAULT 0,
    discount REAL NOT NULL DEFAULT 0,
    insurance_covered REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    paid REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Unpaid',
    pdf_path TEXT,
    FOREIGN KEY(patient_id) REFERENCES patients(id)
);

CREATE TABLE IF NOT EXISTS bill_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL DEFAULT 0,
    line_total REAL NOT NULL DEFAULT 0,
    FOREIGN KEY(bill_id) REFERENCES bills(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    unit TEXT,
    low_stock_threshold INTEGER NOT NULL DEFAULT 10,
    expiry_date TEXT,
    supplier_id INTEGER,
    purchase_price REAL NOT NULL DEFAULT 0,
    last_purchase_date TEXT,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS salaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER,
    doctor_id INTEGER,
    month TEXT NOT NULL,
    base_salary REAL NOT NULL,
    overtime_pay REAL NOT NULL DEFAULT 0,
    deductions REAL NOT NULL DEFAULT 0,
    net_salary REAL NOT NULL,
    paid_on TEXT,
    status TEXT NOT NULL DEFAULT 'Generated',
    FOREIGN KEY(staff_id) REFERENCES staff(id),
    FOREIGN KEY(doctor_id) REFERENCES doctors(id)
);

CREATE TABLE IF NOT EXISTS surgeries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    surgery_uid TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL,
    surgeon_doctor_id INTEGER NOT NULL,
    operation_theatre TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    procedure_name TEXT NOT NULL,
    estimated_cost REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Scheduled',
    recovery_room TEXT,
    notes TEXT,
    FOREIGN KEY(patient_id) REFERENCES patients(id),
    FOREIGN KEY(surgeon_doctor_id) REFERENCES doctors(id)
);

CREATE TABLE IF NOT EXISTS clinical_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    record_type TEXT NOT NULL,
    title TEXT NOT NULL,
    details TEXT,
    record_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    reference_path TEXT,
    FOREIGN KEY(patient_id) REFERENCES patients(id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'In-App',
    target_role TEXT,
    status TEXT NOT NULL DEFAULT 'Unread',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""


class Database:
    def __init__(self, path: Path = DB_PATH) -> None:
        ensure_directories()
        self.path = path
        self.logger = logging.getLogger(__name__)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def session(self) -> Iterable[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            self.logger.exception("Database transaction failed")
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.session() as conn:
            conn.executescript(SCHEMA)

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.session() as conn:
            return conn.execute(query, params).fetchall()

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self.session() as conn:
            return conn.execute(query, params).fetchone()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        with self.session() as conn:
            cur = conn.execute(query, params)
            return int(cur.lastrowid)

    def executemany(self, query: str, rows: Iterable[tuple[Any, ...]]) -> None:
        with self.session() as conn:
            conn.executemany(query, rows)
