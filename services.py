from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .auth import CurrentUser, verify_password
from .database import Database
from .utils import generate_pdf_report, timestamp_code


class ValidationError(ValueError):
    pass


class AuthService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def login(self, username: str, password: str) -> CurrentUser:
        row = self.db.fetch_one("SELECT * FROM users WHERE username = ? AND active = 1", (username.strip(),))
        if not row or not verify_password(password, row["password_hash"]):
            raise ValidationError("Invalid username or password.")
        return CurrentUser(row["id"], row["username"], row["role"], row["full_name"])


class AuditService:
    def __init__(self, db: Database, user: CurrentUser | None = None) -> None:
        self.db = db
        self.user = user

    def log(self, action: str, entity: str, entity_id: Any = None, details: str = "") -> None:
        user_id = self.user.id if self.user else None
        self.db.execute(
            "INSERT INTO audit_logs(user_id, action, entity, entity_id, details) VALUES (?, ?, ?, ?, ?)",
            (user_id, action, entity, str(entity_id) if entity_id is not None else None, details),
        )


class HospitalService:
    def __init__(self, db: Database, user: CurrentUser | None = None) -> None:
        self.db = db
        self.audit = AuditService(db, user)

    def dashboard_metrics(self) -> dict[str, Any]:
        patients = self.db.fetch_one("SELECT COUNT(*) c FROM patients")["c"]
        appointments = self.db.fetch_one("SELECT COUNT(*) c FROM appointments WHERE date(appointment_date)=date('now')")["c"]
        revenue = self.db.fetch_one("SELECT COALESCE(SUM(total),0) total FROM bills WHERE date(bill_date)=date('now')")["total"]
        beds = self.db.fetch_one(
            "SELECT COUNT(*) total, SUM(CASE WHEN status='Occupied' THEN 1 ELSE 0 END) occupied FROM beds"
        )
        occupied = beds["occupied"] or 0
        total_beds = beds["total"] or 1
        return {
            "patients": patients,
            "appointments": appointments,
            "revenue": revenue,
            "occupancy": round((occupied / total_beds) * 100, 1),
            "occupied_beds": occupied,
            "total_beds": total_beds,
        }

    def list_rows(self, table: str, search: str = "") -> list:
        allowed = {
            "patients": ("id, patient_uid, name, age, gender, phone, blood_group", "name || patient_uid || phone"),
            "doctors": ("id, doctor_uid, name, specialization, duty_schedule, consultation_fee, attendance_status", "name || specialization"),
            "appointments": (
                "a.id, a.appointment_uid, p.name patient, d.name doctor, a.appointment_date, a.appointment_time, a.status, a.token_number",
                "p.name || d.name || a.status",
            ),
            "lab_reports": ("l.id, l.report_uid, p.name patient, l.test_type, l.sample_date, l.status", "p.name || l.test_type || l.status"),
            "bills": ("b.id, b.bill_uid, p.name patient, b.category, b.total, b.paid, b.status", "p.name || b.category || b.status"),
            "inventory": ("i.id, i.sku, i.name, i.category, i.quantity, i.unit, i.expiry_date", "i.name || i.category || i.sku"),
            "staff": ("id, staff_uid, name, role, department, shift, salary, attendance_status", "name || role || department"),
            "surgeries": ("s.id, s.surgery_uid, p.name patient, d.name surgeon, s.procedure_name, s.scheduled_at, s.status", "p.name || d.name || s.procedure_name"),
            "beds": ("b.id, b.bed_uid, w.name ward, w.bed_type, w.floor, b.room_number, b.status, b.cleaning_status", "b.bed_uid || w.name || b.status"),
        }
        if table not in allowed:
            raise ValidationError(f"Unsupported table: {table}")
        select_cols, search_cols = allowed[table]
        joins = {
            "appointments": "appointments a JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id",
            "lab_reports": "lab_reports l JOIN patients p ON p.id=l.patient_id",
            "bills": "bills b JOIN patients p ON p.id=b.patient_id",
            "inventory": "inventory i LEFT JOIN suppliers s ON s.id=i.supplier_id",
            "surgeries": "surgeries s JOIN patients p ON p.id=s.patient_id JOIN doctors d ON d.id=s.surgeon_doctor_id",
            "beds": "beds b JOIN wards w ON w.id=b.ward_id",
        }
        source = joins.get(table, table)
        params: tuple[Any, ...] = ()
        where = ""
        if search:
            where = f" WHERE lower({search_cols}) LIKE ?"
            params = (f"%{search.lower()}%",)
        return self.db.fetch_all(f"SELECT {select_cols} FROM {source}{where} ORDER BY 1 DESC LIMIT 500", params)

    def create_patient(self, data: dict[str, Any]) -> int:
        if not data.get("name") or not data.get("age") or not data.get("gender"):
            raise ValidationError("Name, age, and gender are required.")
        patient_uid = timestamp_code("PAT")
        record_id = self.db.execute(
            """
            INSERT INTO patients(patient_uid, name, age, gender, blood_group, address, phone, emergency_contact,
            insurance_details, allergies, existing_diseases, photo_path, document_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_uid,
                data["name"].strip(),
                int(data["age"]),
                data["gender"],
                data.get("blood_group"),
                data.get("address"),
                data.get("phone"),
                data.get("emergency_contact"),
                data.get("insurance_details"),
                data.get("allergies"),
                data.get("existing_diseases"),
                data.get("photo_path"),
                data.get("document_path"),
            ),
        )
        self.audit.log("CREATE", "patients", record_id, patient_uid)
        return record_id

    def update_patient(self, patient_id: int, data: dict[str, Any]) -> None:
        self.db.execute(
            """
            UPDATE patients SET name=?, age=?, gender=?, blood_group=?, address=?, phone=?, emergency_contact=?,
            insurance_details=?, allergies=?, existing_diseases=?, photo_path=?, document_path=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                data["name"].strip(),
                int(data["age"]),
                data["gender"],
                data.get("blood_group"),
                data.get("address"),
                data.get("phone"),
                data.get("emergency_contact"),
                data.get("insurance_details"),
                data.get("allergies"),
                data.get("existing_diseases"),
                data.get("photo_path"),
                data.get("document_path"),
                patient_id,
            ),
        )
        self.audit.log("UPDATE", "patients", patient_id)

    def create_doctor(self, data: dict[str, Any]) -> int:
        if not data.get("name") or not data.get("specialization"):
            raise ValidationError("Doctor name and specialization are required.")
        record_id = self.db.execute(
            """
            INSERT INTO doctors(doctor_uid, name, specialization, phone, email, duty_schedule, consultation_fee, salary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp_code("DOC"),
                data["name"],
                data["specialization"],
                data.get("phone"),
                data.get("email"),
                data.get("duty_schedule"),
                float(data.get("consultation_fee") or 0),
                float(data.get("salary") or 0),
            ),
        )
        self.audit.log("CREATE", "doctors", record_id)
        return record_id

    def create_staff(self, data: dict[str, Any]) -> int:
        if not data.get("name") or not data.get("role"):
            raise ValidationError("Employee name and role are required.")
        record_id = self.db.execute(
            "INSERT INTO staff(staff_uid, name, role, department, phone, salary, shift) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                timestamp_code("STF"),
                data["name"],
                data["role"],
                data.get("department"),
                data.get("phone"),
                float(data.get("salary") or 0),
                data.get("shift"),
            ),
        )
        self.audit.log("CREATE", "staff", record_id)
        return record_id

    def create_appointment(self, data: dict[str, Any]) -> int:
        patient_id = int(data["patient_id"])
        doctor_id = int(data["doctor_id"])
        appointment_date = data["appointment_date"]
        appointment_time = data["appointment_time"]
        existing = self.db.fetch_one(
            """
            SELECT id FROM appointments
            WHERE doctor_id=? AND appointment_date=? AND appointment_time=? AND status IN ('Booked','Rescheduled')
            """,
            (doctor_id, appointment_date, appointment_time),
        )
        if existing:
            raise ValidationError("Doctor is already booked for that slot.")
        token = self.db.fetch_one("SELECT COALESCE(MAX(token_number),0)+1 n FROM appointments WHERE appointment_date=?", (appointment_date,))["n"]
        record_id = self.db.execute(
            """
            INSERT INTO appointments(appointment_uid, patient_id, doctor_id, appointment_date, appointment_time, reason, token_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp_code("APT"), patient_id, doctor_id, appointment_date, appointment_time, data.get("reason"), token),
        )
        self.db.execute(
            "INSERT INTO notifications(title, message, target_role) VALUES (?, ?, ?)",
            ("Appointment booked", f"Token {token} booked for {appointment_date} {appointment_time}", "Receptionist"),
        )
        self.audit.log("CREATE", "appointments", record_id)
        return record_id

    def create_lab_report(self, data: dict[str, Any]) -> int:
        record_id = self.db.execute(
            """
            INSERT INTO lab_reports(report_uid, patient_id, technician_staff_id, test_type, sample_date, status, findings, image_reference)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp_code("LAB"),
                int(data["patient_id"]),
                int(data["technician_staff_id"]) if data.get("technician_staff_id") else None,
                data["test_type"],
                data.get("sample_date") or str(date.today()),
                data.get("status") or "Requested",
                data.get("findings"),
                data.get("image_reference"),
            ),
        )
        self.audit.log("CREATE", "lab_reports", record_id)
        return record_id

    def generate_lab_pdf(self, report_id: int) -> str:
        row = self.db.fetch_one(
            "SELECT l.*, p.name patient, p.patient_uid FROM lab_reports l JOIN patients p ON p.id=l.patient_id WHERE l.id=?",
            (report_id,),
        )
        if not row:
            raise ValidationError("Lab report not found.")
        path = generate_pdf_report(
            "Laboratory Report",
            f"{row['patient']} ({row['patient_uid']})",
            [
                ("Report ID", row["report_uid"]),
                ("Test Type", row["test_type"]),
                ("Sample Date", row["sample_date"]),
                ("Status", row["status"]),
                ("Findings", row["findings"] or ""),
                ("Image Reference", row["image_reference"] or ""),
            ],
            "lab_report",
        )
        self.db.execute("UPDATE lab_reports SET report_path=?, status='Completed' WHERE id=?", (str(path), report_id))
        self.audit.log("PDF", "lab_reports", report_id, str(path))
        return str(path)

    def create_bill(self, data: dict[str, Any], items: list[dict[str, Any]]) -> int:
        if not items:
            raise ValidationError("At least one bill item is required.")
        subtotal = sum(float(item["quantity"]) * float(item["unit_price"]) for item in items)
        tax_rate = float(data.get("tax_rate") or 0)
        discount = float(data.get("discount") or 0)
        insurance = float(data.get("insurance_covered") or 0)
        total = max(subtotal + (subtotal * tax_rate / 100) - discount - insurance, 0)
        paid = float(data.get("paid") or 0)
        status = "Paid" if paid >= total else "Partially Paid" if paid > 0 else "Unpaid"
        bill_id = self.db.execute(
            """
            INSERT INTO bills(bill_uid, patient_id, category, subtotal, tax_rate, discount, insurance_covered, total, paid, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp_code("BILL"), int(data["patient_id"]), data["category"], subtotal, tax_rate, discount, insurance, total, paid, status),
        )
        for item in items:
            line_total = float(item["quantity"]) * float(item["unit_price"])
            self.db.execute(
                "INSERT INTO bill_items(bill_id, description, quantity, unit_price, line_total) VALUES (?, ?, ?, ?, ?)",
                (bill_id, item["description"], float(item["quantity"]), float(item["unit_price"]), line_total),
            )
        self.audit.log("CREATE", "bills", bill_id)
        return bill_id

    def generate_bill_pdf(self, bill_id: int) -> str:
        row = self.db.fetch_one(
            "SELECT b.*, p.name patient, p.patient_uid FROM bills b JOIN patients p ON p.id=b.patient_id WHERE b.id=?",
            (bill_id,),
        )
        items = self.db.fetch_all("SELECT description, quantity, unit_price, line_total FROM bill_items WHERE bill_id=?", (bill_id,))
        path = generate_pdf_report(
            "Hospital Invoice",
            f"{row['patient']} ({row['patient_uid']})",
            [
                ("Bill ID", row["bill_uid"]),
                ("Category", row["category"]),
                ("Items", "; ".join(f"{i['description']} x{i['quantity']} = {i['line_total']}" for i in items)),
                ("Subtotal", f"{row['subtotal']:.2f}"),
                ("GST/Tax", f"{row['tax_rate']:.2f}%"),
                ("Discount", f"{row['discount']:.2f}"),
                ("Insurance", f"{row['insurance_covered']:.2f}"),
                ("Total", f"{row['total']:.2f}"),
                ("Paid", f"{row['paid']:.2f}"),
                ("Status", row["status"]),
            ],
            "invoice",
        )
        self.db.execute("UPDATE bills SET pdf_path=? WHERE id=?", (str(path), bill_id))
        self.audit.log("PDF", "bills", bill_id, str(path))
        return str(path)

    def create_inventory_item(self, data: dict[str, Any]) -> int:
        record_id = self.db.execute(
            """
            INSERT INTO inventory(sku, name, category, quantity, unit, low_stock_threshold, expiry_date, purchase_price, last_purchase_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("sku") or timestamp_code("SKU"),
                data["name"],
                data["category"],
                int(data.get("quantity") or 0),
                data.get("unit"),
                int(data.get("low_stock_threshold") or 10),
                data.get("expiry_date"),
                float(data.get("purchase_price") or 0),
                data.get("last_purchase_date") or str(date.today()),
            ),
        )
        self.audit.log("CREATE", "inventory", record_id)
        return record_id

    def admit_patient(self, patient_id: int, bed_id: int, reason: str) -> int:
        bed = self.db.fetch_one("SELECT status FROM beds WHERE id=?", (bed_id,))
        if not bed or bed["status"] != "Available":
            raise ValidationError("Selected bed is not available.")
        admission_id = self.db.execute(
            "INSERT INTO admissions(admission_uid, patient_id, bed_id, reason) VALUES (?, ?, ?, ?)",
            (timestamp_code("ADM"), patient_id, bed_id, reason),
        )
        self.db.execute("UPDATE beds SET status='Occupied', current_patient_id=? WHERE id=?", (patient_id, bed_id))
        self.audit.log("ADMIT", "admissions", admission_id)
        return admission_id

    def discharge_patient(self, admission_id: int, summary: str, follow_up_date: str = "") -> None:
        admission = self.db.fetch_one("SELECT * FROM admissions WHERE id=? AND status='Admitted'", (admission_id,))
        if not admission:
            raise ValidationError("Active admission not found.")
        self.db.execute("INSERT INTO discharges(admission_id, summary, follow_up_date) VALUES (?, ?, ?)", (admission_id, summary, follow_up_date))
        self.db.execute("UPDATE admissions SET status='Discharged' WHERE id=?", (admission_id,))
        self.db.execute("UPDATE beds SET status='Cleaning', current_patient_id=NULL, cleaning_status='Needs Cleaning' WHERE id=?", (admission["bed_id"],))
        self.audit.log("DISCHARGE", "admissions", admission_id)

    def schedule_surgery(self, data: dict[str, Any]) -> int:
        record_id = self.db.execute(
            """
            INSERT INTO surgeries(surgery_uid, patient_id, surgeon_doctor_id, operation_theatre, scheduled_at,
            procedure_name, estimated_cost, recovery_room, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp_code("SUR"),
                int(data["patient_id"]),
                int(data["surgeon_doctor_id"]),
                data["operation_theatre"],
                data["scheduled_at"],
                data["procedure_name"],
                float(data.get("estimated_cost") or 0),
                data.get("recovery_room"),
                data.get("notes"),
            ),
        )
        self.audit.log("CREATE", "surgeries", record_id)
        return record_id

    def generate_salary(self, staff_id: int | None, doctor_id: int | None, month: str, overtime_pay: float, deductions: float) -> int:
        if staff_id:
            person = self.db.fetch_one("SELECT salary FROM staff WHERE id=?", (staff_id,))
        else:
            person = self.db.fetch_one("SELECT salary FROM doctors WHERE id=?", (doctor_id,))
        base = float(person["salary"])
        net = base + overtime_pay - deductions
        record_id = self.db.execute(
            "INSERT INTO salaries(staff_id, doctor_id, month, base_salary, overtime_pay, deductions, net_salary) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (staff_id, doctor_id, month, base, overtime_pay, deductions, net),
        )
        self.audit.log("CREATE", "salaries", record_id)
        return record_id

    def combo_options(self, table: str) -> list[tuple[int, str]]:
        queries = {
            "patients": "SELECT id, patient_uid || ' - ' || name label FROM patients ORDER BY name",
            "doctors": "SELECT id, doctor_uid || ' - ' || name || ' (' || specialization || ')' label FROM doctors ORDER BY name",
            "staff": "SELECT id, staff_uid || ' - ' || name || ' (' || role || ')' label FROM staff ORDER BY name",
            "beds": "SELECT b.id, b.bed_uid || ' - ' || w.name || ' Room ' || b.room_number label FROM beds b JOIN wards w ON w.id=b.ward_id WHERE b.status='Available' ORDER BY b.id",
        }
        return [(row["id"], row["label"]) for row in self.db.fetch_all(queries[table])]
