from datetime import date, timedelta

from .auth import hash_password
from .database import Database


def seed_database(db: Database) -> None:
    existing = db.fetch_one("SELECT COUNT(*) c FROM users")
    if existing and existing["c"]:
        return

    users = [
        ("admin", "admin123", "Admin", "System Administrator"),
        ("doctor", "doctor123", "Doctor", "Dr. Aanya Mehta"),
        ("nurse", "nurse123", "Nurse", "Nurse Kavya Rao"),
        ("reception", "reception123", "Receptionist", "Rohan Kapoor"),
        ("lab", "lab123", "Laboratory Staff", "Leena Nair"),
        ("pharmacy", "pharmacy123", "Pharmacist", "Sameer Shah"),
        ("accounts", "accounts123", "Accountant", "Priya Menon"),
    ]
    db.executemany(
        "INSERT INTO users(username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
        [(u, hash_password(p), r, n) for u, p, r, n in users],
    )

    patients = [
        ("PAT-20260001", "Arjun Sharma", 42, "Male", "B+", "MG Road, Bengaluru", "9876543210", "Neha Sharma", "Star Health Policy SH-991", "Penicillin", "Hypertension"),
        ("PAT-20260002", "Meera Iyer", 33, "Female", "O+", "Indiranagar, Bengaluru", "9988776655", "Ravi Iyer", "Corporate Insurance", "None", "Asthma"),
        ("PAT-20260003", "Kabir Khan", 58, "Male", "A-", "Whitefield, Bengaluru", "9123456780", "Sara Khan", "Self Pay", "Sulfa drugs", "Diabetes"),
        ("PAT-20260004", "Anika Rao", 27, "Female", "AB+", "Jayanagar, Bengaluru", "9012345678", "Vikram Rao", "Apollo Munich", "Latex", "None"),
    ]
    db.executemany(
        """
        INSERT INTO patients(patient_uid, name, age, gender, blood_group, address, phone, emergency_contact,
        insurance_details, allergies, existing_diseases) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        patients,
    )

    doctors = [
        ("DOC-1001", "Dr. Aanya Mehta", "Cardiology", "9000011111", "aanya@hospital.local", "Mon-Fri 09:00-16:00", 900, 225000),
        ("DOC-1002", "Dr. Vikram Sethi", "Orthopedics", "9000022222", "vikram@hospital.local", "Mon-Sat 10:00-18:00", 800, 205000),
        ("DOC-1003", "Dr. Farah Ali", "Neurology", "9000033333", "farah@hospital.local", "Tue-Sun 08:00-15:00", 1100, 245000),
        ("DOC-1004", "Dr. Rishi Nair", "Radiology", "9000044444", "rishi@hospital.local", "Mon-Fri 12:00-20:00", 700, 180000),
    ]
    db.executemany(
        """
        INSERT INTO doctors(doctor_uid, name, specialization, phone, email, duty_schedule, consultation_fee, salary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        doctors,
    )

    staff = [
        ("STF-2001", "Kavya Rao", "Nurse", "ICU", "8111111111", 52000, "Morning"),
        ("STF-2002", "Leena Nair", "Laboratory Staff", "Pathology", "8222222222", 48000, "Day"),
        ("STF-2003", "Rohan Kapoor", "Receptionist", "Front Desk", "8333333333", 36000, "Day"),
        ("STF-2004", "Mohan Das", "Security", "Operations", "8444444444", 30000, "Night"),
        ("STF-2005", "Sita Joseph", "Cleaner", "Housekeeping", "8555555555", 26000, "Morning"),
    ]
    db.executemany(
        "INSERT INTO staff(staff_uid, name, role, department, phone, salary, shift) VALUES (?, ?, ?, ?, ?, ?, ?)",
        staff,
    )

    today = date.today()
    appointments = [
        ("APT-5001", 1, 1, str(today), "09:30", "Chest pain review", "Booked", 1),
        ("APT-5002", 2, 3, str(today), "10:00", "Migraine follow-up", "Booked", 2),
        ("APT-5003", 3, 2, str(today + timedelta(days=1)), "11:30", "Knee pain", "Booked", 1),
    ]
    db.executemany(
        """
        INSERT INTO appointments(appointment_uid, patient_id, doctor_id, appointment_date, appointment_time, reason, status, token_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        appointments,
    )

    ward_specs = [
        ("Normal Ward", "Normal", 1, 500),
        ("Semi-Luxury Wing", "Semi-Luxury", 2, 200),
        ("Premium Wing", "Premium", 3, 100),
        ("Ultra Luxury Suites", "Ultra Luxury", 4, 10),
    ]
    db.executemany("INSERT INTO wards(name, bed_type, floor, capacity) VALUES (?, ?, ?, ?)", ward_specs)
    bed_rows = []
    counters = [(1, "N", 500), (2, "S", 200), (3, "P", 100), (4, "U", 10)]
    for ward_id, prefix, count in counters:
        for number in range(1, count + 1):
            room = f"{prefix}{((number - 1) // 4) + 1:03d}"
            bed = f"{number:03d}"
            is_icu = 1 if prefix in {"P", "U"} and number <= 20 else 0
            bed_rows.append((f"BED-{prefix}-{bed}", ward_id, room, bed, "Available", "Clean", "Operational", is_icu))
    db.executemany(
        """
        INSERT INTO beds(bed_uid, ward_id, room_number, bed_number, status, cleaning_status, maintenance_status, is_icu)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        bed_rows,
    )
    db.execute("UPDATE beds SET status='Occupied', current_patient_id=1 WHERE id=1")
    db.execute("INSERT INTO admissions(admission_uid, patient_id, bed_id, reason) VALUES (?, ?, ?, ?)", ("ADM-9001", 1, 1, "Cardiac observation"))

    db.executemany(
        "INSERT INTO suppliers(name, phone, email, address) VALUES (?, ?, ?, ?)",
        [
            ("MediSupply India", "8666666666", "sales@medisupply.local", "Peenya Industrial Area"),
            ("LifeCare Pharma", "8777777777", "orders@lifecare.local", "Electronic City"),
        ],
    )
    inventory = [
        ("MED-PARA-500", "Paracetamol 500mg", "Medicine", 2400, "tablet", 200, str(today + timedelta(days=550)), 1, 0.80, str(today)),
        ("MED-AMOX-250", "Amoxicillin 250mg", "Medicine", 900, "capsule", 150, str(today + timedelta(days=320)), 1, 2.40, str(today)),
        ("EQP-GLOVE-N", "Nitrile Gloves", "Surgical Equipment", 12000, "piece", 2000, str(today + timedelta(days=900)), 2, 0.55, str(today)),
        ("OXY-CYL-47L", "Oxygen Cylinder 47L", "Oxygen", 36, "cylinder", 10, None, 2, 6200, str(today)),
        ("MASK-N95", "N95 Mask", "Consumable", 450, "piece", 500, str(today + timedelta(days=200)), 2, 18, str(today)),
    ]
    db.executemany(
        """
        INSERT INTO inventory(sku, name, category, quantity, unit, low_stock_threshold, expiry_date, supplier_id, purchase_price, last_purchase_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        inventory,
    )

    db.execute(
        """
        INSERT INTO lab_reports(report_uid, patient_id, technician_staff_id, test_type, sample_date, status, findings, image_reference)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("LAB-7001", 1, 2, "Blood Test", str(today), "Completed", "Hemoglobin 13.4 g/dL; WBC normal.", "CBC scan reference"),
    )
    db.execute(
        """
        INSERT INTO surgeries(surgery_uid, patient_id, surgeon_doctor_id, operation_theatre, scheduled_at, procedure_name, estimated_cost, status, recovery_room)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("SUR-3001", 3, 2, "OT-2", f"{today + timedelta(days=3)} 09:00", "Arthroscopic knee repair", 145000, "Scheduled", "RR-4"),
    )
    bill_id = db.execute(
        """
        INSERT INTO bills(bill_uid, patient_id, category, subtotal, tax_rate, discount, insurance_covered, total, paid, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("BILL-8001", 1, "OPD Consultation", 900, 18, 0, 0, 1062, 1062, "Paid"),
    )
    db.execute(
        "INSERT INTO bill_items(bill_id, description, quantity, unit_price, line_total) VALUES (?, ?, ?, ?, ?)",
        (bill_id, "Cardiology consultation", 1, 900, 900),
    )
    db.execute(
        "INSERT INTO notifications(title, message, target_role) VALUES (?, ?, ?)",
        ("Low stock alert", "N95 Mask stock is below threshold.", "Pharmacist"),
    )
