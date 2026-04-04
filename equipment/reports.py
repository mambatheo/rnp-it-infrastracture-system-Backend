"""
reports.py — 100 M-row-safe report generation
  • Raw SQL + fetchmany()  — no ORM .all() / .filter()
  • PyExcelerate            — constant-memory Excel, ~500 K rows/sec
  • ReportLab (chunked)    — PDF, 40 rows per table block
  • All generators write to disk (output_path) and return row_count
  • Summary columns are DYNAMIC — fetched from equipment_equipmentstatus,
    never hardcoded.
"""
import io
import os
import re
import struct
from datetime import date

from django.conf import settings
from django.db import connection
from django.utils import timezone

from pyexcelerate import Workbook as PxWorkbook

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, Image as RLImage,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from dotenv import load_dotenv

load_dotenv()

# ── Font setup ──────────────────────────────────────────────────────
_FONTS_DIR = os.getenv("PDF_FONT_DIR", "./static/fonts")
try:
    pdfmetrics.registerFont(TTFont("Tahoma",      os.path.join(_FONTS_DIR, "tahoma.ttf")))
    pdfmetrics.registerFont(TTFont("Tahoma-Bold", os.path.join(_FONTS_DIR, "tahomabd.ttf")))
    _PDF_FONT      = "Tahoma"
    _PDF_FONT_BOLD = "Tahoma-Bold"
except Exception as e:
    print(f"[WARN] Tahoma font not loaded ({e}), falling back to Helvetica")
    _PDF_FONT      = "Helvetica"
    _PDF_FONT_BOLD = "Helvetica-Bold"

# ── Config ──────────────────────────────────────────────────────────
SYSTEM_NAME      = os.getenv("SYSTEM_NAME")
LOGO_PATH        = os.path.join(settings.BASE_DIR, "static", "images", "rnp_logo.png")
SHEET_ROW_LIMIT  = 900_000    # Excel row limit per sheet (hard cap 1,048,576)
SQL_CHUNK        = 2_000      # fetchmany() chunk size
PDF_TABLE_CHUNK  = 40         # rows per ReportLab table block

# ── Colors ──────────────────────────────────────────────────────────
DARK_BLUE  = "#1F4E79"
ALT_ROW    = "#EBF3FB"
WHITE      = "#FFFFFF"
ACCENT     = "#2E75B6"
BANNER_BG  = "#003580"
SECTION_BG = "#2E4DA0"
PDF_DARK   = colors.HexColor("#1F4E79")
PDF_ALT    = colors.HexColor("#EBF3FB")
PDF_ACCENT = colors.HexColor("#2E75B6")
PDF_GREY   = colors.HexColor("#CCCCCC")

# ── Column definitions ─────────────────────────────────────────────
PAGE_CONTENT_WIDTH = 27.7 * cm
BASIC_FIELDS       = ["S/N","Brand","Model","Serial Number","Marking Code","Location","Status","Age"]
COL_WIDTHS_CM      = [1.3*cm,2.0*cm,4.5*cm,4.5*cm,4.5*cm,7.0*cm,3.0*cm,3.0*cm]
UNIT_FIELDS        = ["S/N","Brand","Serial Number","Marking Code","Location","Status","Age"]
UNIT_COL_WIDTHS_CM = [1.2*cm,4.5*cm,4.5*cm,5.0*cm,4.0*cm,4.0*cm,2.5*cm]
STOCK_FIELDS       = ["S/N","Serial Number","Marking Code","Brand","Model","Status","Condition","Date Added"]
STOCK_COL_WIDTHS_CM= [1.2*cm,4.0*cm,4.0*cm,3.0*cm,3.0*cm,3.0*cm,3.0*cm,3.5*cm]

EQ_XL_HDR    = ["S/N","Brand","Model","Serial Number","Marking Code","Location","Status","Age","Type"]
STOCK_XL_HDR = ["S/N","Serial Number","Marking Code","Brand","Model","Status","Condition","Date Added"]
UNIT_XL_HDR  = ["S/N","Brand","Serial Number","Marking Code","Location","Status","Age","Type"]

_TYPE_ORDER = ["Desktop","Laptop","Server","Printer","Network Device","Projector",
               "TV Screen","Decoder","Telephone","External Storage","Peripheral","UPS"]
_TYPE_LABELS = {
    "Desktop":"DESKTOPS","Laptop":"LAPTOPS","Server":"SERVERS",
    "Printer":"PRINTERS & SCANNERS","Network Device":"NETWORK / ACCESS POINTS",
    "Projector":"PROJECTORS","TV Screen":"TV SCREENS","Decoder":"DECODERS",
    "Telephone":"TELEPHONES","External Storage":"EXTERNAL STORAGE",
    "Peripheral":"PERIPHERALS","UPS":"UPS / BATTERIES",
}


# ════════════════════════════════════════════════════════════════════
#  PURE HELPERS
# ════════════════════════════════════════════════════════════════════

def _safe_sheet_name(name):
    return re.sub(r'[/\\?*\[\]:]', '-', str(name))[:31]


def _age_from_date(deployment_date, today=None):
    if not deployment_date:
        return "—"
    if today is None:
        today = timezone.now().date()
    if isinstance(deployment_date, str):
        try:
            from datetime import date as _date
            deployment_date = _date.fromisoformat(deployment_date[:10])
        except ValueError:
            return "—"
    total_days = (today - deployment_date).days
    years, rem = divmod(total_days, 365)
    months, days = divmod(rem, 30)
    parts = []
    if years:  parts.append(f"{years}y")
    if months: parts.append(f"{months}m")
    if days or not parts: parts.append(f"{days}d")
    return " ".join(parts)


def _build_location_sql(row):
    if row.get("office_name"):        return row["office_name"]
    if row.get("department_name"):    return row["department_name"]
    if row.get("directorate_name"):   return row["directorate_name"]
    if row.get("unit_name"):          return row["unit_name"]
    if row.get("dpu_name"):
        parts = [row["dpu_name"]]
        if row.get("dpu_office_name"): parts.append(row["dpu_office_name"])
        return ", ".join(parts)
    if row.get("region_name"):
        parts = [row["region_name"]]
        if row.get("region_office_name"): parts.append(row["region_office_name"])
        return ", ".join(parts)
    return "—"


def _scale_to_page(widths, page_width=PAGE_CONTENT_WIDTH):
    total = sum(widths) if widths else 0
    return [w * page_width / total for w in widths] if total else widths


def _ensure_dir(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def _png_size(path):
    try:
        with open(path, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n": return None
            f.read(4); chunk_type = f.read(4)
            if chunk_type != b"IHDR": return None
            w, h = struct.unpack(">II", f.read(8))
            return w, h
    except Exception:
        return None


def get_equipment_types():
    with connection.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT cat.name
            FROM equipment e
            JOIN equipment_equipmentcategory cat ON cat.id = e.equipment_type_id
            WHERE cat.name IS NOT NULL ORDER BY cat.name
        """)
        return [r[0] for r in cur.fetchall()]


# ════════════════════════════════════════════════════════════════════
#  RAW SQL STREAMERS  (generators — yield one dict per row)
# ════════════════════════════════════════════════════════════════════

_EQ_SELECT = """
    SELECT
        e.id, e.name, e.serial_number, e.marking_code, e.model,
        e.deployment_date,
        cat.name  AS equipment_type_name,
        b.name    AS brand_name,
        s.name    AS status_name,
        r.name    AS region_name,
        ro.name   AS region_office_name,
        d.name    AS dpu_name,
        dpo.name  AS dpu_office_name,
        st.name   AS station_name,
        u.name    AS unit_name,
        dir.name  AS directorate_name,
        dep.name  AS department_name,
        o.name    AS office_name
    FROM equipment e
    LEFT JOIN equipment_equipmentcategory cat ON cat.id  = e.equipment_type_id
    LEFT JOIN equipment_brand             b   ON b.id    = e.brand_id
    LEFT JOIN equipment_equipmentstatus   s   ON s.id    = e.status_id
    LEFT JOIN equipment_region            r   ON r.id    = e.region_id
    LEFT JOIN equipment_regionoffice      ro  ON ro.id   = r.region_office_id
    LEFT JOIN equipment_dpu               d   ON d.id    = e.dpu_id
    LEFT JOIN equipment_dpuoffice         dpo ON dpo.id  = d.dpu_office_id
    LEFT JOIN equipment_station           st  ON st.id   = e.station_id
    LEFT JOIN equipment_unit              u   ON u.id    = e.unit_id
    LEFT JOIN equipment_directorate       dir ON dir.id  = e.directorate_id
    LEFT JOIN equipment_department        dep ON dep.id  = e.department_id
    LEFT JOIN equipment_office            o   ON o.id    = e.office_id"""


def _stream_sql(sql, params=(), chunk_size=SQL_CHUNK):
    with connection.cursor() as cur:
        cur.execute(sql, list(params))
        cols = [c[0] for c in cur.description]
        while True:
            rows = cur.fetchmany(chunk_size)
            if not rows:
                break
            for row in rows:
                yield dict(zip(cols, row))


def stream_equipment_rows(filters=None, chunk_size=SQL_CHUNK):
    filters = filters or {}
    clauses, params = [], []
    if filters.get("equipment_type"):
        clauses.append("cat.name = %s"); params.append(filters["equipment_type"])
    if filters.get("region_id"):
        clauses.append("e.region_id = %s"); params.append(filters["region_id"])
    if filters.get("dpu_id"):
        clauses.append("e.dpu_id = %s"); params.append(filters["dpu_id"])
    if filters.get("status_id"):
        clauses.append("e.status_id = %s"); params.append(filters["status_id"])
    if filters.get("unit_id"):
        clauses.append("e.unit_id = %s"); params.append(filters["unit_id"])
    if filters.get("training_school_id"):
        clauses.append("e.training_school_id = %s"); params.append(filters["training_school_id"])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    yield from _stream_sql(f"{_EQ_SELECT} {where} ORDER BY cat.name, e.id", params, chunk_size)


def stream_location_rows(location_field, location_id, eq_type=None, chunk_size=SQL_CHUNK):
    clauses = [f"e.{location_field} = %s"]
    params  = [location_id]
    if eq_type:
        clauses.append("cat.name = %s"); params.append(eq_type)
    where = "WHERE " + " AND ".join(clauses)
    yield from _stream_sql(f"{_EQ_SELECT} {where} ORDER BY cat.name, e.id", params, chunk_size)


def stream_stock_rows(filters=None, chunk_size=SQL_CHUNK):
    filters = filters or {}
    clauses, params = [], []
    if filters.get("equipment_type"):
        clauses.append("cat.name = %s"); params.append(filters["equipment_type"])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT sk.id, e.serial_number, e.marking_code,
               b.name AS brand_name, e.model,
               s.name AS status_name, sk.condition, sk.date_added,
               cat.name AS equipment_type_name
        FROM stock sk
        JOIN equipment                        e   ON e.id   = sk.equipment_id
        LEFT JOIN equipment_equipmentcategory cat ON cat.id = e.equipment_type_id
        LEFT JOIN equipment_brand             b   ON b.id   = e.brand_id
        LEFT JOIN equipment_equipmentstatus   s   ON s.id   = e.status_id
        {where} ORDER BY cat.name, e.model"""
    yield from _stream_sql(sql, params, chunk_size)


# ════════════════════════════════════════════════════════════════════
#  AGGREGATE SQL HELPERS
# ════════════════════════════════════════════════════════════════════

def get_all_statuses() -> list:
    """
    Fetch every real status name from equipment_equipmentstatus.
    Never hardcoded — always reflects what is actually in the database.
    Returns e.g. ['Active', 'Damaged', 'Faulty', 'New', 'Retired', 'Under Repair']
    """
    with connection.cursor() as cur:
        cur.execute(
            "SELECT name FROM equipment_equipmentstatus ORDER BY name"
        )
        return [row[0] for row in cur.fetchall()]


def get_summary_sql() -> list:
    """
    Returns per-equipment-type counts broken down by REAL statuses from the DB.
    Columns are never hardcoded — they are built from equipment_equipmentstatus.

    Result format:
    [
      {
        'eq_type': 'Desktop',
        'total':   1200,
        'Active':  900,
        'Faulty':  150,
        'New':     100,
        ...  (one key per real status name)
      },
      ...
    ]
    """
    # Step 1 — get real status names from DB (not hardcoded)
    statuses = get_all_statuses()

    # Step 2 — fetch raw counts grouped by (equipment_type, status_name)
    sql = """
        SELECT
            cat.name  AS eq_type,
            s.name    AS status_name,
            COUNT(*)  AS cnt
        FROM equipment e
        JOIN  equipment_equipmentcategory cat ON cat.id = e.equipment_type_id
        LEFT JOIN equipment_equipmentstatus   s   ON s.id  = e.status_id
        GROUP BY cat.name, s.name
        ORDER BY cat.name, s.name
    """

    # Step 3 — pivot in Python: one dict per equipment type
    pivot: dict = {}
    with connection.cursor() as cur:
        cur.execute(sql)
        for eq_type, status_name, cnt in cur.fetchall():
            if eq_type not in pivot:
                pivot[eq_type] = {'eq_type': eq_type, 'total': 0}
                # Initialise every real status to 0
                for st in statuses:
                    pivot[eq_type][st] = 0
            pivot[eq_type]['total']                  += cnt
            pivot[eq_type][status_name or 'Unknown'] += cnt

    return list(pivot.values())


def get_stock_summary_sql():
    sql = """
        SELECT cat.name AS eq_type, COUNT(*) AS total
        FROM stock sk
        JOIN equipment e ON e.id = sk.equipment_id
        JOIN equipment_equipmentcategory cat ON cat.id = e.equipment_type_id
        GROUP BY cat.name ORDER BY cat.name"""
    return list(_stream_sql(sql, chunk_size=10_000))


def _location_names_with_equipment(location_field, location_table):
    """Return [(id, name)] for locations that have at least one equipment record."""
    sql = f"""
        SELECT DISTINCT loc.id, loc.name
        FROM {location_table} loc
        WHERE EXISTS (SELECT 1 FROM equipment e WHERE e.{location_field} = loc.id)
        ORDER BY loc.name"""
    with connection.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def _location_name(location_table, location_id):
    with connection.cursor() as cur:
        cur.execute(f"SELECT name FROM {location_table} WHERE id = %s", [location_id])
        row = cur.fetchone()
    return row[0] if row else str(location_id)


# ════════════════════════════════════════════════════════════════════
#  PYEXCELERATE EXCEL GENERATORS
#  Every function: writes output_path to disk, returns row_count (int)
# ════════════════════════════════════════════════════════════════════

def _px_flush_sheet(wb, sheet_name, buf):
    if len(buf) > 1:
        wb.new_sheet(_safe_sheet_name(sheet_name), data=buf)


def _stream_to_sheets(wb, stream, headers, row_builder, sheet_prefix="Data"):
    """
    Stream rows into PyExcelerate, splitting a new sheet every SHEET_ROW_LIMIT rows.
    row_builder(sn, row) → list of cell values.
    Returns total row_count.
    """
    buf       = [headers]
    sheet_num = 1
    row_count = 0
    for sn, row in enumerate(stream, start=1):
        buf.append(row_builder(sn, row))
        row_count += 1
        if len(buf) - 1 >= SHEET_ROW_LIMIT:
            _px_flush_sheet(wb, f"{sheet_prefix}_{sheet_num}", buf)
            buf = [headers]
            sheet_num += 1
    _px_flush_sheet(wb, f"{sheet_prefix}_{sheet_num}", buf)
    return row_count


def _eq_row_builder(today):
    def _build(sn, row):
        return [
            sn,
            str(row.get("brand_name") or "—"),
            str(row.get("model") or "—"),
            str(row.get("serial_number") or "—"),
            str(row.get("marking_code") or "—"),
            _build_location_sql(row),
            str(row.get("status_name") or "—"),
            str(_age_from_date(row.get("deployment_date"), today)),
            str(row.get("equipment_type_name") or "—"),
        ]
    return _build


# ── Equipment Excel ─────────────────────────────────────────────────

def generate_excel_all(output_path: str, filters: dict = None) -> int:
    filters = filters or {}
    _ensure_dir(output_path)
    wb    = PxWorkbook()
    today = date.today()

    # ── Summary sheet — dynamic columns from real DB statuses ────────────────
    summary = get_summary_sql()

    # Discover status column names: all keys except 'eq_type' and 'total'
    status_cols = (
        [k for k in summary[0].keys() if k not in ('eq_type', 'total')]
        if summary else []
    )

    sum_headers = ['Equipment Type', 'Total'] + status_cols
    sum_data    = [sum_headers]

    for row in summary:
        sum_data.append(
            [row['eq_type'], row['total']] +
            [row.get(st, 0) for st in status_cols]
        )

    # Grand total row
    grand = sum(r['total'] for r in summary)
    sum_data.append(
        ['GRAND TOTAL', grand] +
        [sum(r.get(st, 0) for r in summary) for st in status_cols]
    )
    wb.new_sheet('Summary', data=sum_data)

    # ── Data sheets — stream all rows sorted by type ──────────────────────────
    current_type = None
    sheet_num    = 1
    buf          = [EQ_XL_HDR]
    row_count    = 0
    build        = _eq_row_builder(today)

    for row in stream_equipment_rows(filters):
        eq_type = row.get("equipment_type_name") or "Unknown"

        # Type boundary → flush previous buffer into its own sheet
        if eq_type != current_type:
            if current_type is not None and len(buf) > 1:
                _px_flush_sheet(wb, f"{current_type}_{sheet_num}", buf)
            current_type = eq_type
            sheet_num    = 1
            buf          = [EQ_XL_HDR]

        buf.append(build(len(buf), row))   # len(buf)-based S/N within type
        row_count += 1
        if len(buf) - 1 >= SHEET_ROW_LIMIT:
            _px_flush_sheet(wb, f"{current_type}_{sheet_num}", buf)
            buf = [EQ_XL_HDR]
            sheet_num += 1

    if current_type and len(buf) > 1:
        _px_flush_sheet(wb, f"{current_type}_{sheet_num}", buf)

    wb.save(output_path)
    return row_count


def generate_excel_by_type(equipment_type: str, output_path: str, filters: dict = None) -> int:
    filters = dict(filters or {}); filters["equipment_type"] = equipment_type
    _ensure_dir(output_path)
    wb    = PxWorkbook()
    today = date.today()
    build = _eq_row_builder(today)
    rc    = _stream_to_sheets(wb, stream_equipment_rows(filters), EQ_XL_HDR, build,
                               sheet_prefix=_safe_sheet_name(equipment_type))
    wb.save(output_path)
    return rc


# ── Stock Excel ─────────────────────────────────────────────────────

def _stock_row_builder(sn, row):
    return [sn, str(row.get("serial_number") or "—"), str(row.get("marking_code") or "—"),
            str(row.get("brand_name") or "—"), str(row.get("model") or "—"),
            str(row.get("status_name") or "—"), str(row.get("condition") or "—"),
            str(row.get("date_added") or "—")]


def generate_stock_excel_all(output_path: str, filters: dict = None) -> int:
    filters = filters or {}
    _ensure_dir(output_path)
    wb      = PxWorkbook()
    summary = get_stock_summary_sql()
    grand   = sum(r["total"] for r in summary)
    sum_data = [["Equipment Type", "Items in Stock"]] + \
               [[r["eq_type"], r["total"]] for r in summary] + \
               [["TOTAL", grand]]
    wb.new_sheet("Summary", data=sum_data)
    rc = _stream_to_sheets(wb, stream_stock_rows(filters), STOCK_XL_HDR,
                           _stock_row_builder, sheet_prefix="Stock")
    wb.save(output_path)
    return rc


def generate_stock_excel_by_type(equipment_type: str, output_path: str, filters: dict = None) -> int:
    filters = dict(filters or {}); filters["equipment_type"] = equipment_type
    _ensure_dir(output_path)
    wb = PxWorkbook()
    rc = _stream_to_sheets(wb, stream_stock_rows(filters), STOCK_XL_HDR,
                           _stock_row_builder, sheet_prefix=_safe_sheet_name(equipment_type))
    wb.save(output_path)
    return rc


# ── Location Excel (Unit / Region / DPU / TrainingSchool) ──────────

def _unit_row_builder(today):
    def _build(sn, row):
        return [sn, str(row.get("brand_name") or "—"),
                str(row.get("serial_number") or "—"), str(row.get("marking_code") or "—"),
                _build_location_sql(row), str(row.get("status_name") or "—"),
                str(_age_from_date(row.get("deployment_date"), today)),
                str(row.get("equipment_type_name") or "—")]
    return _build


def _generate_location_excel_all(location_field, location_table, summary_label, output_path):
    _ensure_dir(output_path)
    wb    = PxWorkbook()
    today = date.today()
    build = _unit_row_builder(today)
    locs  = _location_names_with_equipment(location_field, location_table)
    row_count = 0
    for loc_id, loc_name in locs:
        stream = stream_location_rows(location_field, loc_id)
        rc = _stream_to_sheets(wb, stream, UNIT_XL_HDR, build,
                               sheet_prefix=_safe_sheet_name(loc_name))
        row_count += rc
    wb.save(output_path)
    return row_count


def _generate_location_excel_single(location_field, location_table, location_id, output_path):
    _ensure_dir(output_path)
    wb    = PxWorkbook()
    today = date.today()
    build = _unit_row_builder(today)
    name  = _location_name(location_table, location_id)
    rc    = _stream_to_sheets(wb, stream_location_rows(location_field, location_id),
                              UNIT_XL_HDR, build, sheet_prefix=_safe_sheet_name(name))
    wb.save(output_path)
    return rc


def generate_unit_excel_all(output_path: str, filters: dict = None) -> int:
    return _generate_location_excel_all("unit_id", "equipment_unit", "Unit", output_path)

def generate_unit_excel_by_unit(unit_id: str, output_path: str, filters: dict = None) -> int:
    return _generate_location_excel_single("unit_id", "equipment_unit", unit_id, output_path)

def generate_region_excel_all(output_path: str, filters: dict = None) -> int:
    return _generate_location_excel_all("region_id", "equipment_region", "Region", output_path)

def generate_region_excel_by_region(region_id: str, output_path: str, filters: dict = None) -> int:
    return _generate_location_excel_single("region_id", "equipment_region", region_id, output_path)

def generate_dpu_excel_all(output_path: str, filters: dict = None) -> int:
    return _generate_location_excel_all("dpu_id", "equipment_dpu", "DPU", output_path)

def generate_dpu_excel_by_dpu(dpu_id: str, output_path: str, filters: dict = None) -> int:
    return _generate_location_excel_single("dpu_id", "equipment_dpu", dpu_id, output_path)

def generate_trainingschool_excel_all(output_path: str, filters: dict = None) -> int:
    return _generate_location_excel_all("training_school_id", "equipment_trainingschool",
                                        "Training School", output_path)

def generate_trainingschool_excel_by_school(trainingschool_id: str, output_path: str, filters: dict = None) -> int:
    return _generate_location_excel_single("training_school_id", "equipment_trainingschool",
                                           trainingschool_id, output_path)


# ════════════════════════════════════════════════════════════════════
#  PDF INFRASTRUCTURE  (ReportLab — kept intact, adapted to disk output)
# ════════════════════════════════════════════════════════════════════

_PDF_STYLES = getSampleStyleSheet()
_CELL_STYLE = ParagraphStyle("CellNormal", fontName=_PDF_FONT, fontSize=11,
    leading=13, wordWrap="LTR", alignment=1)
_HEADER_CELL_STYLE = ParagraphStyle("CellHeader", fontName=_PDF_FONT_BOLD, fontSize=11,
    leading=13, wordWrap="LTR", textColor=colors.white, alignment=1)
_STYLE_PDF_SYSTEM  = ParagraphStyle("PDFSystemName", parent=_PDF_STYLES["Normal"],
    fontSize=11, fontName=_PDF_FONT_BOLD, textColor=PDF_DARK, alignment=0)
_STYLE_PDF_HEADING = ParagraphStyle("PDFHeading", parent=_PDF_STYLES["Heading2"],
    textColor=PDF_DARK, fontName=_PDF_FONT_BOLD, fontSize=11, spaceBefore=4, spaceAfter=2)
_STYLE_PDF_SMALL   = ParagraphStyle("PDFSmall", parent=_PDF_STYLES["Normal"],
    fontSize=9, fontName=_PDF_FONT, textColor=colors.grey)
_STYLE_SEC_HEAD    = ParagraphStyle("PDFSecHead", parent=_PDF_STYLES["Normal"],
    fontSize=11, fontName=_PDF_FONT_BOLD, textColor=colors.white,
    backColor=colors.HexColor("#2E4DA0"), spaceAfter=0, spaceBefore=4, leftIndent=4)
_STYLE_LOC_HEAD    = ParagraphStyle("PDFLocHead", parent=_PDF_STYLES["Heading1"],
    textColor=colors.HexColor("#003580"), fontSize=11, fontName=_PDF_FONT_BOLD)

TABLE_STYLE = TableStyle([
    ("BACKGROUND",    (0,0),(-1,0),  PDF_DARK),
    ("TEXTCOLOR",     (0,0),(-1,0),  colors.white),
    ("FONTNAME",      (0,0),(-1,0),  _PDF_FONT_BOLD),
    ("FONTNAME",      (0,1),(-1,-1), _PDF_FONT),
    ("FONTSIZE",      (0,0),(-1,-1), 7),
    ("ALIGN",         (0,0),(-1,-1), "CENTER"),
    ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, PDF_ALT]),
    ("GRID",          (0,0),(-1,-1), 0.25, PDF_GREY),
    ("ROWHEIGHT",     (0,0),(-1,-1), 14),
    ("TOPPADDING",    (0,0),(-1,-1), 2),
    ("BOTTOMPADDING", (0,0),(-1,-1), 2),
    ("LEFTPADDING",   (0,0),(-1,-1), 3),
    ("RIGHTPADDING",  (0,0),(-1,-1), 3),
])


def _pdf_cell(val, max_c=60):
    s = "—" if val is None else str(val).strip() or "—"
    return s[:max_c-1]+"…" if len(s) > max_c else s


def _wrap_rows(header_row, data_rows):
    w_hdr  = [Paragraph(str(h), _HEADER_CELL_STYLE) for h in header_row]
    w_data = [[_pdf_cell(c) for c in row] for row in data_rows]
    return w_hdr, w_data


def _scale_cols(widths):
    return _scale_to_page(widths)


def _make_footer_canvas(report_title):
    gen_str = f"Generated: {timezone.now().strftime('%d %B %Y at %H:%M')}"
    def _draw(canvas, doc):
        canvas.saveState()
        canvas.setFont(_PDF_FONT, 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(doc.pagesize[0]-doc.rightMargin, doc.bottomMargin*0.5, gen_str)
        canvas.restoreState()
    return _draw


def _pdf_header_block(report_title):
    left_items = []
    if os.path.exists(LOGO_PATH):
        left_items.append(RLImage(LOGO_PATH, width=1.8*cm, height=1.8*cm))
        left_items.append(Spacer(1, 0.1*cm))
    left_items.append(Paragraph(SYSTEM_NAME or "", _STYLE_PDF_SYSTEM))
    _STYLE_RIGHT = ParagraphStyle("PDFReportRight", parent=_PDF_STYLES["Normal"],
        fontSize=11, fontName=_PDF_FONT_BOLD, textColor=PDF_ACCENT, alignment=1)
    right_items = [Paragraph(report_title, _STYLE_RIGHT)]
    hdr = Table([[left_items, right_items]],
                colWidths=[4*cm, PAGE_CONTENT_WIDTH-4*cm], hAlign="LEFT")
    hdr.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    return hdr


def _build_pdf(elements, report_title, output_path):
    _ensure_dir(output_path)
    footer_cb = _make_footer_canvas(report_title)
    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4),
                            rightMargin=1*cm, leftMargin=1*cm,
                            topMargin=0.2*cm, bottomMargin=0.2*cm)
    doc.build(elements, onFirstPage=footer_cb, onLaterPages=footer_cb)


def _pdf_tables_from_stream(stream, headers, col_widths, table_chunk=PDF_TABLE_CHUNK):
    """
    Stream rows and yield Table flowables in chunks.
    Never loads all rows into memory at once.
    Returns (elements_list, row_count).
    """
    elements  = []
    batch     = []
    row_count = 0
    scaled_w  = _scale_cols(col_widths)
    for row in stream:
        batch.append(row)
        row_count += 1
        if len(batch) >= table_chunk:
            w_hdr, w_data = _wrap_rows(headers, batch)
            t = Table([w_hdr]+w_data, repeatRows=1, hAlign="LEFT", colWidths=scaled_w)
            t.setStyle(TABLE_STYLE)
            elements.extend([t, Spacer(1, 0.2*cm)])
            batch = []
    if batch:
        w_hdr, w_data = _wrap_rows(headers, batch)
        t = Table([w_hdr]+w_data, repeatRows=1, hAlign="LEFT", colWidths=scaled_w)
        t.setStyle(TABLE_STYLE)
        elements.extend([t, Spacer(1, 0.2*cm)])
    return elements, row_count


def _pdf_summary_table_from_sql(summary: list) -> object:
    """
    Build a ReportLab summary Table from get_summary_sql() output.
    Columns are built DYNAMICALLY from whatever statuses exist in the data —
    never hardcoded. Automatically adapts when statuses are added or renamed.
    """
    if not summary:
        return Paragraph("No equipment data available.", _STYLE_PDF_SMALL)

    # Discover status columns dynamically from first row
    # (all keys except 'eq_type' and 'total')
    status_cols = [k for k in summary[0].keys() if k not in ('eq_type', 'total')]

    headers = ['Equipment Type', 'Total'] + status_cols
    data    = [headers]

    for row in summary:
        data.append(
            [row['eq_type'], row['total']] +
            [row.get(st, 0) for st in status_cols]
        )

    # Grand total row
    grand_total = sum(r['total'] for r in summary)
    data.append(
        ['GRAND TOTAL', grand_total] +
        [sum(r.get(st, 0) for r in summary) for st in status_cols]
    )

    w_hdr, w_data = _wrap_rows(data[0], data[1:])
    t = Table([w_hdr] + w_data, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  PDF_DARK),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0),  (-1, 0),  _PDF_FONT_BOLD),
        ("FONTNAME",      (0, 1),  (-1, -1), _PDF_FONT),
        ("FONTSIZE",      (0, 0),  (-1, -1), 9),
        ("ALIGN",         (0, 0),  (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [colors.white, PDF_ALT]),
        # Grand total row — accent background
        ("BACKGROUND",    (0, -1), (-1, -1), PDF_ACCENT),
        ("TEXTCOLOR",     (0, -1), (-1, -1), colors.white),
        ("FONTNAME",      (0, -1), (-1, -1), _PDF_FONT_BOLD),
        ("GRID",          (0, 0),  (-1, -1), 0.5, PDF_GREY),
        ("ROWHEIGHT",     (0, 0),  (-1, -1), 16),
        ("TOPPADDING",    (0, 0),  (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 2),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0),  (-1, -1), 3),
    ]))
    return t


# ════════════════════════════════════════════════════════════════════
#  PDF GENERATORS
#  All write to output_path (disk), return row_count (int)
#  NOTE: for 100M-row "all" reports, PDF shows summary only.
#        Per-type and per-location PDFs include full row data.
# ════════════════════════════════════════════════════════════════════

_EQ_PDF_HEADERS = ["S/N","Brand","Model","Serial","Marking","Location","Status","Age"]
_EQ_PDF_WIDTHS  = [1.0*cm,2.5*cm,4.0*cm,4.0*cm,4.0*cm,5.5*cm,2.5*cm,2.5*cm]
_STOCK_PDF_HDR  = ["S/N","Serial","Marking","Brand","Model","Status","Condition","Added"]
_STOCK_PDF_W    = [1.0*cm,3.5*cm,3.5*cm,3.0*cm,3.0*cm,2.5*cm,2.5*cm,2.5*cm]
_UNIT_PDF_HDR   = ["S/N","Brand","Serial","Marking","Location","Status","Age","Type"]
_UNIT_PDF_W     = [1.0*cm,3.0*cm,3.5*cm,3.5*cm,4.0*cm,2.5*cm,2.5*cm,3.0*cm]


def _eq_stream_to_pdf_rows(stream):
    today = date.today()
    for sn, row in enumerate(stream, start=1):
        yield [sn, row.get("brand_name") or "—", row.get("model") or "—",
               row.get("serial_number") or "—", row.get("marking_code") or "—",
               _build_location_sql(row), row.get("status_name") or "—",
               _age_from_date(row.get("deployment_date"), today)]


def _stock_stream_to_pdf_rows(stream):
    for sn, row in enumerate(stream, start=1):
        yield [sn, row.get("serial_number") or "—", row.get("marking_code") or "—",
               row.get("brand_name") or "—", row.get("model") or "—",
               row.get("status_name") or "—", row.get("condition") or "—",
               str(row.get("date_added") or "—")]


def _unit_stream_to_pdf_rows(stream):
    today = date.today()
    for sn, row in enumerate(stream, start=1):
        yield [sn, row.get("brand_name") or "—", row.get("serial_number") or "—",
               row.get("marking_code") or "—", _build_location_sql(row),
               row.get("status_name") or "—",
               _age_from_date(row.get("deployment_date"), today),
               row.get("equipment_type_name") or "—"]


# ── Equipment PDF ────────────────────────────────────────────────────

def generate_pdf_all(output_path: str, filters: dict = None) -> int:
    """Summary-only PDF for full equipment dataset (100M rows → no raw data in PDF)."""
    filters  = filters or {}
    title    = "Full Equipment Report"
    summary  = get_summary_sql()
    elements = [
        _pdf_header_block(title), Spacer(1, 0.2*cm),
        HRFlowable(width="100%", thickness=2, color=PDF_ACCENT), Spacer(1, 0.3*cm),
        Paragraph("Summary by Equipment Type", _STYLE_PDF_HEADING), Spacer(1, 0.1*cm),
        _pdf_summary_table_from_sql(summary), Spacer(1, 0.5*cm),
        Paragraph(
            "For full row-level data, use the Excel report or request a per-type PDF.",
            _STYLE_PDF_SMALL
        ),
    ]
    _build_pdf(elements, title, output_path)
    return sum(r["total"] for r in summary)


def generate_pdf_by_type(equipment_type: str, output_path: str, filters: dict = None) -> int:
    filters = dict(filters or {}); filters["equipment_type"] = equipment_type
    title   = f"{equipment_type} Equipment Report"
    elements = [
        _pdf_header_block(title), Spacer(1, 0.2*cm),
        HRFlowable(width="100%", thickness=2, color=PDF_ACCENT), Spacer(1, 0.3*cm),
        Paragraph(equipment_type, _STYLE_PDF_HEADING),
    ]
    pdf_rows    = _eq_stream_to_pdf_rows(stream_equipment_rows(filters))
    tbl_els, rc = _pdf_tables_from_stream(pdf_rows, _EQ_PDF_HEADERS, _EQ_PDF_WIDTHS)
    elements.extend(tbl_els if rc > 0 else [Paragraph("No data available.", _STYLE_PDF_SMALL)])
    _build_pdf(elements, title, output_path)
    return rc


# ── Stock PDF ────────────────────────────────────────────────────────

def generate_stock_pdf_all(output_path: str, filters: dict = None) -> int:
    """Summary + full stock rows (stock is typically much smaller than equipment)."""
    filters = filters or {}
    title   = "Full Stock Report"
    summary = get_stock_summary_sql()
    grand   = sum(r["total"] for r in summary)
    sum_hdr  = ["Equipment Type", "In Stock"]
    sum_rows = [[r["eq_type"], r["total"]] for r in summary] + [["TOTAL", grand]]
    w_hdr, w_data = _wrap_rows(sum_hdr, sum_rows)
    sum_tbl = Table([w_hdr] + w_data, repeatRows=1, hAlign="LEFT")
    sum_tbl.setStyle(TABLE_STYLE)
    elements = [
        _pdf_header_block(title), Spacer(1, 0.2*cm),
        HRFlowable(width="100%", thickness=2, color=PDF_ACCENT), Spacer(1, 0.3*cm),
        Paragraph("Summary", _STYLE_PDF_HEADING), sum_tbl, Spacer(1, 0.4*cm),
        HRFlowable(width="100%", thickness=1, color=PDF_GREY), Spacer(1, 0.2*cm),
        Paragraph("Stock Items", _STYLE_PDF_HEADING),
    ]
    pdf_rows    = _stock_stream_to_pdf_rows(stream_stock_rows(filters))
    tbl_els, rc = _pdf_tables_from_stream(pdf_rows, _STOCK_PDF_HDR, _STOCK_PDF_W)
    elements.extend(tbl_els)
    _build_pdf(elements, title, output_path)
    return rc


def generate_stock_pdf_by_type(equipment_type: str, output_path: str, filters: dict = None) -> int:
    filters = dict(filters or {}); filters["equipment_type"] = equipment_type
    title   = f"{equipment_type} Stock Report"
    elements = [
        _pdf_header_block(title), Spacer(1, 0.2*cm),
        HRFlowable(width="100%", thickness=2, color=PDF_ACCENT), Spacer(1, 0.3*cm),
        Paragraph(equipment_type, _STYLE_PDF_HEADING),
    ]
    pdf_rows    = _stock_stream_to_pdf_rows(stream_stock_rows(filters))
    tbl_els, rc = _pdf_tables_from_stream(pdf_rows, _STOCK_PDF_HDR, _STOCK_PDF_W)
    elements.extend(tbl_els if rc > 0 else [Paragraph("No stock items.", _STYLE_PDF_SMALL)])
    _build_pdf(elements, title, output_path)
    return rc


# ── Location PDF  ─────────────────────────────────────

def _generate_location_pdf(location_field, location_table, location_id, location_name_str,
                            output_path, all_locations=False):
    title    = f"Equipment Report — {location_name_str}"
    elements = [
        _pdf_header_block(title), Spacer(1, 0.2*cm),
        HRFlowable(width="100%", thickness=2, color=PDF_ACCENT), Spacer(1, 0.3*cm),
    ]
    row_count = 0
    if all_locations:
        locs = _location_names_with_equipment(location_field, location_table)
        for loc_id, loc_name in locs:
            elements += [
                HRFlowable(width="100%", thickness=2, color=colors.HexColor("#003580")),
                Spacer(1, 0.1*cm),
                Paragraph(loc_name.upper(), _STYLE_LOC_HEAD),
                Spacer(1, 0.1*cm),
            ]
            pdf_rows    = _unit_stream_to_pdf_rows(stream_location_rows(location_field, loc_id))
            tbl_els, rc = _pdf_tables_from_stream(pdf_rows, _UNIT_PDF_HDR, _UNIT_PDF_W)
            elements.extend(tbl_els)
            row_count += rc
    else:
        elements += [Paragraph(location_name_str.upper(), _STYLE_LOC_HEAD), Spacer(1, 0.1*cm)]
        pdf_rows    = _unit_stream_to_pdf_rows(stream_location_rows(location_field, location_id))
        tbl_els, rc = _pdf_tables_from_stream(pdf_rows, _UNIT_PDF_HDR, _UNIT_PDF_W)
        elements.extend(tbl_els)
        row_count += rc
    _build_pdf(elements, title, output_path)
    return row_count


def generate_unit_pdf_all(output_path: str, filters: dict = None) -> int:
    return _generate_location_pdf("unit_id", "equipment_unit", None, "All Units",
                                  output_path, all_locations=True)

def generate_unit_pdf_by_unit(unit_id: str, output_path: str, filters: dict = None) -> int:
    name = _location_name("equipment_unit", unit_id)
    return _generate_location_pdf("unit_id", "equipment_unit", unit_id, name, output_path)

def generate_region_pdf_all(output_path: str, filters: dict = None) -> int:
    return _generate_location_pdf("region_id", "equipment_region", None, "All Regions",
                                  output_path, all_locations=True)

def generate_region_pdf_by_region(region_id: str, output_path: str, filters: dict = None) -> int:
    name = _location_name("equipment_region", region_id)
    return _generate_location_pdf("region_id", "equipment_region", region_id, name, output_path)

def generate_dpu_pdf_all(output_path: str, filters: dict = None) -> int:
    return _generate_location_pdf("dpu_id", "equipment_dpu", None, "All DPUs",
                                  output_path, all_locations=True)

def generate_dpu_pdf_by_dpu(dpu_id: str, output_path: str, filters: dict = None) -> int:
    name = _location_name("equipment_dpu", dpu_id)
    return _generate_location_pdf("dpu_id", "equipment_dpu", dpu_id, name, output_path)

def generate_trainingschool_pdf_all(output_path: str, filters: dict = None) -> int:
    return _generate_location_pdf("training_school_id", "equipment_trainingschool",
                                  None, "All Training Schools", output_path, all_locations=True)

def generate_trainingschool_pdf_by_school(trainingschool_id: str, output_path: str, filters: dict = None) -> int:
    name = _location_name("equipment_trainingschool", trainingschool_id)
    return _generate_location_pdf("training_school_id", "equipment_trainingschool",
                                  trainingschool_id, name, output_path)