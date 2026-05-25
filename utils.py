import csv
import logging
import shutil
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .config import BACKUP_DIR, DB_PATH, LOG_DIR, REPORT_DIR


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_DIR / "hospital_erp.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def timestamp_code(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def make_backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    destination = BACKUP_DIR / f"hospital_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"
    shutil.copy2(DB_PATH, destination)
    return destination


def restore_backup(path: str | Path) -> None:
    shutil.copy2(path, DB_PATH)


def choose_upload_file() -> str:
    return filedialog.askopenfilename(
        title="Select file",
        filetypes=[
            ("Supported files", "*.png *.jpg *.jpeg *.pdf *.docx *.xlsx"),
            ("All files", "*.*"),
        ],
    )


def export_rows_to_excel(title: str, columns: list[str], rows: list[tuple]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(columns)
    for row in rows:
        ws.append(list(row))
    wb.save(path)
    return path


def export_rows_to_csv(title: str, columns: list[str], rows: list[tuple]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
    return path


def generate_pdf_report(title: str, subtitle: str, rows: list[tuple[str, str]], filename_prefix: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Paragraph(subtitle, styles["Normal"]), Spacer(1, 18)]
    table = Table([("Field", "Value"), *rows], colWidths=[150, 330])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e2ec")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return path
