from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from hospital_erp.services import HospitalService
from hospital_erp.utils import export_rows_to_excel, make_backup, restore_backup
from .components import DataTable, FormDialog, MetricCard, selected_combo_id


class BaseModule(ttk.Frame):
    permission = "dashboard"

    def __init__(self, parent, service: HospitalService) -> None:
        super().__init__(parent, padding=18)
        self.service = service

    def header(self, title: str, subtitle: str = "") -> ttk.Frame:
        box = ttk.Frame(self)
        box.pack(fill="x", pady=(0, 12))
        ttk.Label(box, text=title, style="Title.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(box, text=subtitle).pack(anchor="w", pady=(2, 0))
        return box


class DashboardModule(BaseModule):
    permission = "dashboard"

    def __init__(self, parent, service: HospitalService) -> None:
        super().__init__(parent, service)
        self.header("Hospital Structure Dashboard", "Live overview of clinical, occupancy, and finance activity.")
        self.cards = ttk.Frame(self)
        self.cards.pack(fill="x")
        self.chart_area = ttk.Frame(self, style="Panel.TFrame", padding=12)
        self.chart_area.pack(fill="both", expand=True, pady=(16, 0))
        self.refresh()

    def refresh(self) -> None:
        for child in self.cards.winfo_children():
            child.destroy()
        for child in self.chart_area.winfo_children():
            child.destroy()
        metrics = self.service.dashboard_metrics()
        cards = [
            ("Total Patients", str(metrics["patients"]), "Registered patient records"),
            ("Today's Appointments", str(metrics["appointments"]), "OPD and follow-up visits"),
            ("Daily Revenue", f"Rs. {metrics['revenue']:.2f}", "Collected and invoiced today"),
            ("Bed Occupancy", f"{metrics['occupancy']}%", f"{metrics['occupied_beds']} of {metrics['total_beds']} beds"),
        ]
        for idx, (title, value, caption) in enumerate(cards):
            card = MetricCard(self.cards, title, value, caption)
            card.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 10, 0), ipady=6)
            self.cards.columnconfigure(idx, weight=1)

        rows = self.service.db.fetch_all(
            "SELECT w.bed_type, COUNT(*) total, SUM(CASE WHEN b.status='Occupied' THEN 1 ELSE 0 END) occupied "
            "FROM beds b JOIN wards w ON w.id=b.ward_id GROUP BY w.bed_type"
        )
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(121)
        labels = [row["bed_type"] for row in rows]
        occupied = [row["occupied"] or 0 for row in rows]
        totals = [row["total"] for row in rows]
        ax.bar(labels, totals, label="Total", color="#8fb9cf")
        ax.bar(labels, occupied, label="Occupied", color="#0f8b8d")
        ax.set_title("Bed Occupancy")
        ax.tick_params(axis="x", rotation=20)
        ax.legend()

        revenue = self.service.db.fetch_all(
            "SELECT date(bill_date) d, SUM(total) total FROM bills GROUP BY date(bill_date) ORDER BY d LIMIT 7"
        )
        ax2 = fig.add_subplot(122)
        ax2.plot([r["d"] for r in revenue], [r["total"] for r in revenue], marker="o", color="#1f78b4")
        ax2.set_title("Revenue Trend")
        ax2.tick_params(axis="x", rotation=20)
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, self.chart_area)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


class TableModule(BaseModule):
    title = ""
    subtitle = ""
    table_name = ""
    columns: list[str] = []

    def __init__(self, parent, service: HospitalService) -> None:
        super().__init__(parent, service)
        self.header(self.title, self.subtitle)
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 10))
        self.search_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.search_var).pack(side="left", fill="x", expand=True)
        ttk.Button(toolbar, text="Search", command=self.refresh).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Add", style="Accent.TButton", command=self.add_record).pack(side="left")
        ttk.Button(toolbar, text="Export Excel", command=self.export_excel).pack(side="left", padx=6)
        self.table = DataTable(self, self.columns)
        self.table.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self) -> None:
        self.table.set_rows(self.service.list_rows(self.table_name, self.search_var.get()))

    def export_excel(self) -> None:
        path = export_rows_to_excel(self.title, self.columns, self.table.as_rows())
        messagebox.showinfo("Export complete", f"Saved to {path}")

    def add_record(self) -> None:
        messagebox.showinfo("Not available", "This module uses specialized actions.")


class PatientsModule(TableModule):
    permission = "patients"
    title = "Patient Management"
    subtitle = "Registration, demographics, insurance, allergies, and complete clinical history access."
    table_name = "patients"
    columns = ["id", "patient_uid", "name", "age", "gender", "phone", "blood_group"]

    def add_record(self) -> None:
        fields = [
            {"name": "name", "label": "Name"},
            {"name": "age", "label": "Age"},
            {"name": "gender", "label": "Gender", "kind": "combo", "values": ["Male", "Female", "Other"]},
            {"name": "blood_group", "label": "Blood Group", "kind": "combo", "values": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]},
            {"name": "address", "label": "Address", "kind": "text"},
            {"name": "phone", "label": "Phone"},
            {"name": "emergency_contact", "label": "Emergency Contact"},
            {"name": "insurance_details", "label": "Insurance Details", "kind": "text"},
            {"name": "allergies", "label": "Allergies", "kind": "text"},
            {"name": "existing_diseases", "label": "Existing Diseases", "kind": "text"},
            {"name": "photo_path", "label": "Photo Path"},
            {"name": "document_path", "label": "Document Path"},
        ]
        FormDialog(self, "Add Patient", fields, lambda data: (self.service.create_patient(data), self.refresh()))


class DoctorsModule(TableModule):
    permission = "doctors"
    title = "Doctor Management"
    subtitle = "Doctor profiles, specialization, duty schedules, attendance, fees, and salary."
    table_name = "doctors"
    columns = ["id", "doctor_uid", "name", "specialization", "duty_schedule", "consultation_fee", "attendance_status"]

    def add_record(self) -> None:
        fields = [
            {"name": "name", "label": "Doctor Name"},
            {"name": "specialization", "label": "Specialization"},
            {"name": "phone", "label": "Phone"},
            {"name": "email", "label": "Email"},
            {"name": "duty_schedule", "label": "Duty Schedule"},
            {"name": "consultation_fee", "label": "Consultation Fee"},
            {"name": "salary", "label": "Salary"},
        ]
        FormDialog(self, "Add Doctor", fields, lambda data: (self.service.create_doctor(data), self.refresh()))


class AppointmentsModule(TableModule):
    permission = "appointments"
    title = "Appointment Management"
    subtitle = "Booking, availability checks, OPD scheduling, token queues, and reminder-ready notifications."
    table_name = "appointments"
    columns = ["id", "appointment_uid", "patient", "doctor", "appointment_date", "appointment_time", "status", "token_number"]

    def add_record(self) -> None:
        patients = [f"{id_} - {label}" for id_, label in self.service.combo_options("patients")]
        doctors = [f"{id_} - {label}" for id_, label in self.service.combo_options("doctors")]
        fields = [
            {"name": "patient", "label": "Patient", "kind": "combo", "values": patients, "state": "readonly"},
            {"name": "doctor", "label": "Doctor", "kind": "combo", "values": doctors, "state": "readonly"},
            {"name": "appointment_date", "label": "Date (YYYY-MM-DD)"},
            {"name": "appointment_time", "label": "Time (HH:MM)"},
            {"name": "reason", "label": "Reason", "kind": "text"},
        ]

        def submit(data):
            data["patient_id"] = selected_combo_id(data.pop("patient"))
            data["doctor_id"] = selected_combo_id(data.pop("doctor"))
            self.service.create_appointment(data)
            self.refresh()

        FormDialog(self, "Book Appointment", fields, submit)


class LaboratoryModule(TableModule):
    permission = "laboratory"
    title = "Laboratory Management"
    subtitle = "Blood, urine, biochemistry, pathology, X-Ray, CT, MRI, and ultrasound report workflow."
    table_name = "lab_reports"
    columns = ["id", "report_uid", "patient", "test_type", "sample_date", "status"]

    def __init__(self, parent, service):
        super().__init__(parent, service)
        ttk.Button(self, text="Generate PDF For Selected", command=self.pdf_selected).pack(anchor="e", pady=(8, 0))

    def add_record(self) -> None:
        patients = [f"{id_} - {label}" for id_, label in self.service.combo_options("patients")]
        staff = [f"{id_} - {label}" for id_, label in self.service.combo_options("staff")]
        tests = ["Blood Test", "Urine Test", "Biochemistry", "Pathology", "X-Ray", "CT Scan", "MRI", "Ultrasound"]
        fields = [
            {"name": "patient", "label": "Patient", "kind": "combo", "values": patients, "state": "readonly"},
            {"name": "technician", "label": "Technician", "kind": "combo", "values": staff},
            {"name": "test_type", "label": "Test Type", "kind": "combo", "values": tests},
            {"name": "sample_date", "label": "Sample Date (YYYY-MM-DD)"},
            {"name": "status", "label": "Status", "kind": "combo", "values": ["Requested", "Sample Collected", "Processing", "Completed"]},
            {"name": "findings", "label": "Findings", "kind": "text"},
            {"name": "image_reference", "label": "Image / Scan Reference"},
        ]

        def submit(data):
            data["patient_id"] = selected_combo_id(data.pop("patient"))
            data["technician_staff_id"] = selected_combo_id(data.pop("technician")) if data.get("technician") else ""
            self.service.create_lab_report(data)
            self.refresh()

        FormDialog(self, "New Lab Report", fields, submit)

    def pdf_selected(self) -> None:
        report_id = self.table.selected_id()
        if not report_id:
            messagebox.showwarning("Select report", "Choose a lab report first.")
            return
        path = self.service.generate_lab_pdf(report_id)
        self.refresh()
        messagebox.showinfo("PDF generated", f"Saved to {path}")


class BillingModule(TableModule):
    permission = "billing"
    title = "Billing & Finance"
    subtitle = "OPD, surgeries, lab tests, medicines, rooms, ICU, emergency charges, GST, discounts, insurance, and invoices."
    table_name = "bills"
    columns = ["id", "bill_uid", "patient", "category", "total", "paid", "status"]

    def __init__(self, parent, service):
        super().__init__(parent, service)
        ttk.Button(self, text="Generate Invoice PDF", command=self.pdf_selected).pack(anchor="e", pady=(8, 0))

    def add_record(self) -> None:
        patients = [f"{id_} - {label}" for id_, label in self.service.combo_options("patients")]
        fields = [
            {"name": "patient", "label": "Patient", "kind": "combo", "values": patients, "state": "readonly"},
            {"name": "category", "label": "Category", "kind": "combo", "values": ["OPD Consultation", "Surgery", "Lab Test", "Medicine", "Room Charges", "ICU Charges", "Emergency Charges"]},
            {"name": "description", "label": "Item Description"},
            {"name": "quantity", "label": "Quantity", "default": "1"},
            {"name": "unit_price", "label": "Unit Price"},
            {"name": "tax_rate", "label": "GST/Tax %", "default": "18"},
            {"name": "discount", "label": "Discount", "default": "0"},
            {"name": "insurance_covered", "label": "Insurance Covered", "default": "0"},
            {"name": "paid", "label": "Paid Amount", "default": "0"},
        ]

        def submit(data):
            data["patient_id"] = selected_combo_id(data.pop("patient"))
            items = [{"description": data.pop("description"), "quantity": data.pop("quantity"), "unit_price": data.pop("unit_price")}]
            self.service.create_bill(data, items)
            self.refresh()

        FormDialog(self, "Generate Bill", fields, submit)

    def pdf_selected(self) -> None:
        bill_id = self.table.selected_id()
        if not bill_id:
            messagebox.showwarning("Select bill", "Choose a bill first.")
            return
        path = self.service.generate_bill_pdf(bill_id)
        self.refresh()
        messagebox.showinfo("Invoice generated", f"Saved to {path}")


class WardsModule(TableModule):
    permission = "wards"
    title = "Ward & Bed Management"
    subtitle = "Floor-wise, room-wise allocation, ICU status, cleaning, maintenance, admission, and discharge tracking."
    table_name = "beds"
    columns = ["id", "bed_uid", "ward", "bed_type", "floor", "room_number", "status", "cleaning_status"]

    def add_record(self) -> None:
        patients = [f"{id_} - {label}" for id_, label in self.service.combo_options("patients")]
        beds = [f"{id_} - {label}" for id_, label in self.service.combo_options("beds")]
        fields = [
            {"name": "patient", "label": "Patient", "kind": "combo", "values": patients, "state": "readonly"},
            {"name": "bed", "label": "Available Bed", "kind": "combo", "values": beds, "state": "readonly"},
            {"name": "reason", "label": "Admission Reason", "kind": "text"},
        ]

        def submit(data):
            self.service.admit_patient(selected_combo_id(data["patient"]), selected_combo_id(data["bed"]), data["reason"])
            self.refresh()

        FormDialog(self, "Admit Patient", fields, submit)


class InventoryModule(TableModule):
    permission = "inventory"
    title = "Inventory & Pharmacy"
    subtitle = "Medicines, surgical equipment, consumables, oxygen, suppliers, expiry, low-stock, and purchase tracking."
    table_name = "inventory"
    columns = ["id", "sku", "name", "category", "quantity", "unit", "expiry_date"]

    def add_record(self) -> None:
        fields = [
            {"name": "sku", "label": "SKU"},
            {"name": "name", "label": "Item Name"},
            {"name": "category", "label": "Category", "kind": "combo", "values": ["Medicine", "Surgical Equipment", "Gloves", "Masks", "Syringes", "Medical Tools", "Oxygen"]},
            {"name": "quantity", "label": "Quantity"},
            {"name": "unit", "label": "Unit"},
            {"name": "low_stock_threshold", "label": "Low Stock Threshold", "default": "10"},
            {"name": "expiry_date", "label": "Expiry Date (YYYY-MM-DD)"},
            {"name": "purchase_price", "label": "Purchase Price"},
            {"name": "last_purchase_date", "label": "Last Purchase Date (YYYY-MM-DD)"},
        ]
        FormDialog(self, "Add Inventory Item", fields, lambda data: (self.service.create_inventory_item(data), self.refresh()))


class EmployeesModule(TableModule):
    permission = "employees"
    title = "Employee & Salary Management"
    subtitle = "Doctors, nurses, receptionists, lab staff, security, cleaners, attendance, shifts, overtime, and payroll."
    table_name = "staff"
    columns = ["id", "staff_uid", "name", "role", "department", "shift", "salary", "attendance_status"]

    def add_record(self) -> None:
        fields = [
            {"name": "name", "label": "Employee Name"},
            {"name": "role", "label": "Role", "kind": "combo", "values": ["Nurse", "Receptionist", "Laboratory Staff", "Security", "Cleaner", "Pharmacist", "Accountant"]},
            {"name": "department", "label": "Department"},
            {"name": "phone", "label": "Phone"},
            {"name": "salary", "label": "Salary"},
            {"name": "shift", "label": "Shift", "kind": "combo", "values": ["Morning", "Day", "Evening", "Night"]},
        ]
        FormDialog(self, "Add Employee", fields, lambda data: (self.service.create_staff(data), self.refresh()))


class SurgeriesModule(TableModule):
    permission = "surgeries"
    title = "Surgery Management"
    subtitle = "Scheduling, operation theatre allocation, surgeon assignment, cost estimation, billing, and recovery rooms."
    table_name = "surgeries"
    columns = ["id", "surgery_uid", "patient", "surgeon", "procedure_name", "scheduled_at", "status"]

    def add_record(self) -> None:
        patients = [f"{id_} - {label}" for id_, label in self.service.combo_options("patients")]
        doctors = [f"{id_} - {label}" for id_, label in self.service.combo_options("doctors")]
        fields = [
            {"name": "patient", "label": "Patient", "kind": "combo", "values": patients, "state": "readonly"},
            {"name": "surgeon", "label": "Surgeon", "kind": "combo", "values": doctors, "state": "readonly"},
            {"name": "operation_theatre", "label": "Operation Theatre", "kind": "combo", "values": ["OT-1", "OT-2", "OT-3", "OT-4"]},
            {"name": "scheduled_at", "label": "Scheduled At (YYYY-MM-DD HH:MM)"},
            {"name": "procedure_name", "label": "Procedure Name"},
            {"name": "estimated_cost", "label": "Estimated Cost"},
            {"name": "recovery_room", "label": "Recovery Room"},
            {"name": "notes", "label": "Notes", "kind": "text"},
        ]

        def submit(data):
            data["patient_id"] = selected_combo_id(data.pop("patient"))
            data["surgeon_doctor_id"] = selected_combo_id(data.pop("surgeon"))
            self.service.schedule_surgery(data)
            self.refresh()

        FormDialog(self, "Schedule Surgery", fields, submit)


class AdminToolsModule(BaseModule):
    permission = "admin"

    def __init__(self, parent, service):
        super().__init__(parent, service)
        self.header("Administration Tools", "Backup, restore, notifications, audit logs, and operational exports.")
        actions = ttk.Frame(self, style="Panel.TFrame", padding=14)
        actions.pack(fill="x")
        ttk.Button(actions, text="Backup Database", style="Accent.TButton", command=self.backup).pack(side="left")
        ttk.Button(actions, text="Restore Database", command=self.restore).pack(side="left", padx=8)
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, pady=(14, 0))
        self.audit_table = DataTable(tabs, ["id", "user_id", "action", "entity", "entity_id", "details", "created_at"])
        self.note_table = DataTable(tabs, ["id", "title", "message", "channel", "target_role", "status", "created_at"])
        tabs.add(self.audit_table, text="Audit Logs")
        tabs.add(self.note_table, text="Notifications")
        self.refresh()

    def refresh(self) -> None:
        self.audit_table.set_rows(self.service.db.fetch_all("SELECT id, user_id, action, entity, entity_id, details, created_at FROM audit_logs ORDER BY id DESC LIMIT 500"))
        self.note_table.set_rows(self.service.db.fetch_all("SELECT id, title, message, channel, target_role, status, created_at FROM notifications ORDER BY id DESC LIMIT 500"))

    def backup(self) -> None:
        path = make_backup()
        messagebox.showinfo("Backup complete", f"Saved to {path}")

    def restore(self) -> None:
        path = filedialog.askopenfilename(title="Choose SQLite backup", filetypes=[("SQLite", "*.sqlite3 *.db"), ("All files", "*.*")])
        if path and messagebox.askyesno("Restore database", "Restore will replace the active database. Continue?"):
            restore_backup(path)
            messagebox.showinfo("Restore complete", "Restart the application to reload the restored database.")
