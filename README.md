# Hospital ERP / HMS Desktop Application

A modular Python 3 desktop Hospital Management Software built with Tkinter, ttk, SQLite, Pillow, ReportLab, and matplotlib.

## Features

- Secure login with SHA-256 salted password hashing
- Role-based access control for Admin, Doctor, Nurse, Receptionist, Laboratory Staff, Pharmacist, and Accountant
- Patient management with generated patient IDs, documents, allergies, history, appointments, prescriptions, billing, and lab reports
- Doctor, appointment, laboratory, billing, ward/bed, inventory/pharmacy, employee/payroll, surgery, and analytics modules
- SQLite database with normalized tables and a repository/service style architecture
- PDF invoice and lab report export using ReportLab
- Excel export using openpyxl
- Integrated matplotlib dashboard charts
- Light/dark professional ttk themes
- Audit logs, notifications, backup, restore, validation, and application logging
- Dummy seed data for immediate testing

## Project Structure

```text
HOSPITAL/
  main.py
  requirements.txt
  README.md
  hospital_erp/
    __init__.py
    app.py
    auth.py
    config.py
    database.py
    seed.py
    services.py
    utils.py
    ui/
      __init__.py
      components.py
      modules.py
      styles.py
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Default users:

| Role | Username | Password |
| --- | --- | --- |
| Admin | admin | admin123 |
| Doctor | doctor | doctor123 |
| Nurse | nurse | nurse123 |
| Receptionist | reception | reception123 |
| Laboratory Staff | lab | lab123 |
| Pharmacist | pharmacy | pharmacy123 |
| Accountant | accounts | accounts123 |

## Database

The app creates `data/hospital_erp.sqlite3` automatically on first run and seeds it with realistic sample data.

Core entities:

- `users` authenticate staff and enforce roles.
- `patients` stores demographic, medical, insurance, and document metadata.
- `doctors` and `staff` manage provider and employee profiles.
- `appointments` connects patients and doctors.
- `wards`, `beds`, `admissions`, and `discharges` model bed occupancy.
- `lab_reports`, `bills`, `bill_items`, `inventory`, `salaries`, and `surgeries` cover clinical, finance, stock, payroll, and operation theatre workflows.
- `notifications` and `audit_logs` provide operational traceability.

## ER Diagram Explanation

`patients` is the clinical hub. Appointments, admissions, bills, lab reports, and surgeries reference a patient. Doctors are linked to appointments and surgeries. Beds belong to wards and can be assigned through admissions. Bills are parent records with line items in `bill_items`. Staff can be attached to users and salaries. Inventory items reference suppliers. Audit logs reference the user who performed each action.

The schema is normalized enough to migrate later: SQLite access is isolated in `hospital_erp/database.py` and business operations live in `hospital_erp/services.py`.

## Notes

This is a full desktop HMS foundation designed for extension. SMS and email reminder hooks are represented by notification records and clean service methods so real providers can be added without changing UI code.
