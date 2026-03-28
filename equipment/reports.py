import io
import os
import re
import struct
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q

import xlsxwriter

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
from .models import Equipment, EquipmentCategory, EquipmentStatus, Stock, Unit, Region, DPU, Department, Directorate
from dotenv import load_dotenv

load_dotenv()

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


# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

SYSTEM_NAME     = os.getenv("SYSTEM_NAME")
LOGO_PATH       = os.path.join(settings.BASE_DIR, "static", "images", "rnp_logo.png")
REPORT_PASSWORD = os.getenv("EXCEL_REPORT_PASSWORD")


def get_equipment_types():
    return (
        Equipment.objects
        .filter(equipment_type__isnull=False)
        .values_list("equipment_type__name", flat=True)
        .distinct()
        .order_by("equipment_type__name")
    )


# ─────────────────────────────────────────
# SHEET NAME SANITISER
# ─────────────────────────────────────────

def _safe_sheet_name(name):
    return re.sub(r'[/\\?*\[\]:]', '-', str(name))[:31]


# ─────────────────────────────────────────
# COLOURS
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
# FIELDS & WIDTHS
# ─────────────────────────────────────────

BASIC_FIELDS = [
    "S/N", "Brand", "Model", "Serial Number", "Marking Code",
    "Location", "Status", "Age",
]
COL_WIDTHS_CM = [
    1.3*cm, 2.0*cm, 4.5*cm, 4.5*cm, 4.5*cm, 7.0*cm, 3.0*cm, 3.0*cm,
]
_CM_TO_XL = 1 / 0.1828
BASIC_COL_WIDTHS_XL = [round(w / cm * _CM_TO_XL, 1) for w in COL_WIDTHS_CM]
PAGE_CONTENT_WIDTH  = 27.7 * cm
_FIELD_WIDTH        = dict(zip(BASIC_FIELDS, COL_WIDTHS_CM))

UNIT_FIELDS = ["S/N", "Brand", "Serial Number", "Marking Code", "Location", "Status", "Age"]
UNIT_COL_WIDTHS_CM = [1.2*cm, 4.5*cm, 4.5*cm, 5.0*cm, 4.0*cm, 4.0*cm, 2.5*cm]
UNIT_COL_WIDTHS_XL = [round(w / cm * _CM_TO_XL, 1) for w in UNIT_COL_WIDTHS_CM]
_UNIT_FIELD_WIDTH  = dict(zip(UNIT_FIELDS, UNIT_COL_WIDTHS_CM))

STOCK_FIELDS = [
    "S/N", "Serial Number", "Marking Code",
    "Brand", "Model", "Status", "Condition", "Date Added",
]
STOCK_COL_WIDTHS_CM = [1.2*cm, 4.0*cm, 4.0*cm, 3.0*cm, 3.0*cm, 3.0*cm, 3.0*cm, 3.5*cm]
_STOCK_FIELD_WIDTH  = dict(zip(STOCK_FIELDS, STOCK_COL_WIDTHS_CM))

_TYPE_ORDER = [
    "Desktop", "Laptop", "Server", "Printer", "Network Device", "Projector",
    "TV Screen", "Decoder", "Telephone", "External Storage", "Peripheral", "UPS",
]
_TYPE_LABELS = {
    "Desktop":          "DESKTOPS",
    "Laptop":           "LAPTOPS",
    "Server":           "SERVERS",
    "Printer":          "PRINTERS & SCANNERS",
    "Network Device":   "NETWORK / ACCESS POINTS",
    "Projector":        "PROJECTORS",
    "TV Screen":        "TV SCREENS",
    "Decoder":          "DECODERS",
    "Telephone":        "TELEPHONES",
    "External Storage": "EXTERNAL STORAGE",
    "Peripheral":       "PERIPHERALS",
    "UPS":              "UPS / BATTERIES",
}


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _filter_empty_cols(headers, rows, widths=None):
    """Filter out columns that are entirely empty. Optimized with early termination."""
    if not rows:
        return headers, rows, widths
    
    n_cols = len(headers)
    # Track which columns have non-empty values
    has_data = [False] * n_cols
    cols_remaining = n_cols
    
    for row in rows:
        for i in range(n_cols):
            if not has_data[i] and str(row[i]).strip() not in ("—", "-", ""):
                has_data[i] = True
                cols_remaining -= 1
                if cols_remaining == 0:
                    # All columns have data, return early
                    return headers, rows, widths
    
    keep      = [i for i in range(n_cols) if has_data[i]]
    f_headers = [headers[i] for i in keep]
    f_rows    = [[row[i] for i in keep] for row in rows]
    f_widths  = [widths[i] for i in keep] if widths else None
    return f_headers, f_rows, f_widths


def _scale_to_page(widths, page_width=PAGE_CONTENT_WIDTH):
    total = sum(widths) if widths else 0
    if not total:
        return widths
    factor = page_width / total
    return [w * factor for w in widths]


def _build_location_from_dict(obj):
    if obj["office__name"]:
        return obj["office__name"]
    if obj["department__name"]:
        return obj["department__name"]
    if obj["directorate__name"]:
        return obj["directorate__name"]
    if obj["unit__name"]:
        return obj["unit__name"]
    if obj["dpu__name"]:
        parts = [obj["dpu__name"]]
        if obj["dpu__dpu_office__name"]:
            parts.append(obj["dpu__dpu_office__name"])
        return ", ".join(parts)
    if obj["region__name"]:
        parts = [obj["region__name"]]
        if obj["region__region_office__name"]:
            parts.append(obj["region__region_office__name"])
        return ", ".join(parts)
    return "—"


def _age_from_date(deployment_date, today=None):
    if not deployment_date:
        return "—"
    if today is None:
        today = timezone.now().date()
    total_days       = (today - deployment_date).days
    years, remainder = divmod(total_days, 365)
    months, days     = divmod(remainder, 30)
    parts = []
    if years:  parts.append(f"{years}y")
    if months: parts.append(f"{months}m")
    if days or not parts: parts.append(f"{days}d")
    return " ".join(parts)


# ─────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────

def get_summary():
    qs = (
        Equipment.objects
        .filter(equipment_type__isnull=False)
        .values("equipment_type__name")
        .annotate(
            total        = Count("id"),
            active       = Count("id", filter=Q(status__name__iexact="Active")),
            inactive     = Count("id", filter=Q(status__name__iexact="Inactive")),
            under_repair = Count("id", filter=Q(status__name__iexact="Under Repair")),
            retired      = Count("id", filter=Q(status__name__iexact="Retired")),
            damaged      = Count("id", filter=Q(status__name__iexact="Damaged")),
            new          = Count("id", filter=Q(status__name__iexact="New")),
        )
        .order_by("equipment_type__name")
    )
    summary     = {}
    grand_total = 0
    for row in qs:
        eq_type = row["equipment_type__name"]
        if not eq_type:
            continue
        summary[eq_type] = {k: row[k] for k in
            ["total","active","inactive","under_repair","retired","damaged","new"]}
        grand_total += row["total"]
    summary["__grand_total__"] = grand_total
    return summary


def _equipment_values_qs(equipment_type=None, extra_filter=None):
    qs = (
        Equipment.objects
        .filter(equipment_type__isnull=False)
        .values(
            "equipment_type__name",
            "brand__name", "model", "serial_number", "marking_code",
            "status__name", "deployment_date",
            "office__name", "department__name", "directorate__name", "unit__name",
            "region__name", "region__region_office__name",
            "dpu__name",    "dpu__dpu_office__name",
        )
        .order_by()
    )
    if equipment_type:
        qs = qs.filter(equipment_type__name=equipment_type)
    if extra_filter:
        qs = qs.filter(**extra_filter)
    return qs


def get_basic_rows(equipment_type=None, extra_filter=None):
    qs    = _equipment_values_qs(equipment_type=equipment_type, extra_filter=extra_filter)
    today = timezone.now().date()
    rows  = []
    for sn, obj in enumerate(qs.iterator(chunk_size=2000), start=1):
        rows.append([
            str(sn),
            obj["brand__name"]   or "—",
            obj["model"]         or "—",
            obj["serial_number"] or "—",
            obj["marking_code"]  or "—",
            _build_location_from_dict(obj),
            obj["status__name"]  or "—",
            _age_from_date(obj["deployment_date"], today),
        ])
    return rows


def get_all_basic_rows_grouped():
    """Fetch all equipment in ONE query and group by equipment_type.
    Returns dict: {equipment_type: [[row1], [row2], ...]}
    """
    qs    = _equipment_values_qs()
    today = timezone.now().date()
    
    grouped = {}
    counters = {}
    
    for obj in qs.iterator(chunk_size=2000):
        eq_type = obj["equipment_type__name"]
        if eq_type not in grouped:
            grouped[eq_type] = []
            counters[eq_type] = 0
        
        counters[eq_type] += 1
        grouped[eq_type].append([
            str(counters[eq_type]),
            obj["brand__name"]   or "—",
            obj["model"]         or "—",
            obj["serial_number"] or "—",
            obj["marking_code"]  or "—",
            _build_location_from_dict(obj),
            obj["status__name"]  or "—",
            _age_from_date(obj["deployment_date"], today),
        ])
    
    return grouped


def _unit_device_rows_fast(extra_filter, equipment_type):
    qs = (
        Equipment.objects
        .filter(equipment_type__name=equipment_type, **extra_filter)
        .values(
            "brand__name", "serial_number", "marking_code", "status__name", "deployment_date",
            "office__name", "department__name", "directorate__name", "unit__name",
            "region__name", "region__region_office__name",
            "dpu__name",    "dpu__dpu_office__name",
        )
        .order_by("brand__name", "serial_number")
    )
    rows = []
    for sn, obj in enumerate(qs.iterator(chunk_size=2000), start=1):
        rows.append([
            str(sn),
            obj["brand__name"]   or "—",
            obj["serial_number"] or "—",
            obj["marking_code"]  or "—",
            _build_location_from_dict(obj),
            obj["status__name"]  or "—",
            _age_from_date(obj["deployment_date"]),
        ])
    return rows


# ─────────────────────────────────────────
# XLSXWRITER FORMAT FACTORY
# ─────────────────────────────────────────

def _make_formats(wb):
    f = {}
    f["header"] = wb.add_format({
        "bold": True, "font_name": "Tahoma", "font_size": 11,
        "font_color": "#FFFFFF", "bg_color": DARK_BLUE,
        "align": "center", "valign": "vcenter", "text_wrap": True,
        "border": 1, "border_color": "#FFFFFF",
    })
    f["data"] = wb.add_format({
        "font_name": "Tahoma", "font_size": 11,
        "bg_color": WHITE, "align": "center", "valign": "vcenter",
        "border": 1, "border_color": "#CCCCCC",
    })
    f["data_alt"] = wb.add_format({
        "font_name": "Tahoma", "font_size": 11,
        "bg_color": ALT_ROW, "align": "center", "valign": "vcenter",
        "border": 1, "border_color": "#CCCCCC",
    })
    f["grand"] = wb.add_format({
        "bold": True, "font_name": "Tahoma", "font_size": 12,
        "font_color": "#FFFFFF", "bg_color": ACCENT,
        "align": "center", "valign": "vcenter",
    })
    f["sys_name"] = wb.add_format({
        "bold": True, "font_name": "Tahoma", "font_size": 14,
        "font_color": DARK_BLUE, "align": "right", "valign": "vcenter",
    })
    f["report_title"] = wb.add_format({
        "font_name": "Tahoma", "font_size": 12,
        "font_color": ACCENT, "align": "right", "valign": "vcenter",
    })
    f["date_line"] = wb.add_format({
        "italic": True, "font_name": "Tahoma", "font_size": 10,
        "font_color": "#666666", "align": "right", "valign": "vcenter",
    })
    f["banner"] = wb.add_format({
        "bold": True, "font_name": "Tahoma", "font_size": 13,
        "font_color": "#FFFFFF", "bg_color": BANNER_BG,
        "align": "center", "valign": "vcenter",
    })
    f["section"] = wb.add_format({
        "bold": True, "font_name": "Tahoma", "font_size": 12,
        "font_color": "#FFFFFF", "bg_color": SECTION_BG,
        "align": "center", "valign": "vcenter",
    })
    return f


# ─────────────────────────────────────────
# XLSXWRITER HEADER BLOCK
# ─────────────────────────────────────────

def _png_size(path):
    """
    Return PNG (width, height) in pixels, or None if unreadable.
    """
    try:
        with open(path, "rb") as f:
            sig = f.read(8)
            if sig != b"\x89PNG\r\n\x1a\n":
                return None
            f.read(4)  # chunk length (IHDR is first)
            chunk_type = f.read(4)
            if chunk_type != b"IHDR":
                return None
            width, height = struct.unpack(">II", f.read(8))
            return width, height
    except Exception:
        return None


def _xl_logo_options():
    """
    Keep logo inside a predictable box so it cannot overlap table content.

    XlsxWriter renders images at 96 DPI on screen.  High-res PNGs (e.g. 300 DPI
    source files) can have very large pixel dimensions, so even a small scale
    factor produces a huge rendered image.  We therefore target a fixed *on-screen*
    size of 64×64 px and use object_position=3 (don't move or size with cells)
    to prevent the image from pushing rows around.
    """
    TARGET_PX = 64          # desired rendered size in screen-pixels (≈ 96 DPI)
    DEFAULT_SCALE = 0.07    # safe fallback when image dimensions are unknown

    size = _png_size(LOGO_PATH)
    if not size:
        return {
            "x_scale": DEFAULT_SCALE, "y_scale": DEFAULT_SCALE,
            "x_offset": 4, "y_offset": 4,
            "object_position": 3,
        }

    width, height = size
    if width <= 0 or height <= 0:
        return {
            "x_scale": DEFAULT_SCALE, "y_scale": DEFAULT_SCALE,
            "x_offset": 4, "y_offset": 4,
            "object_position": 3,
        }

    scale = min(TARGET_PX / width, TARGET_PX / height, 1.0)
    return {
        "x_scale": scale, "y_scale": scale,
        "x_offset": 4, "y_offset": 4,
        "object_position": 3,
    }


def _xl_write_header(ws, fmt, report_title, n_cols):
    ws.set_row(0, 80)
    ws.set_row(1, 22)
    ws.set_row(2, 18)
    ws.set_row(3, 6)
    if os.path.exists(LOGO_PATH):
        ws.insert_image(0, 0, LOGO_PATH, _xl_logo_options())
    title_col = max(1, n_cols // 2)
    ws.merge_range(0, title_col, 0, n_cols - 1, SYSTEM_NAME,     fmt["sys_name"])
    ws.merge_range(1, title_col, 1, n_cols - 1, report_title,    fmt["report_title"])
    ws.merge_range(2, title_col, 2, n_cols - 1,
        f"Generated: {timezone.now().strftime('%d %B %Y')}", fmt["date_line"])
    return 4


# ─────────────────────────────────────────
# WORKBOOK FACTORY
# ─────────────────────────────────────────

def _new_workbook():
    output = io.BytesIO()
    wb     = xlsxwriter.Workbook(output, {
        "in_memory":       True,
        "constant_memory": False,
        "strings_to_urls": False,
    })
    fmt = _make_formats(wb)
    return output, wb, fmt


def _close_workbook(wb, output):
    wb.close()
    output.seek(0)
    return output


# ─────────────────────────────────────────
# XLSXWRITER SHEET WRITERS  (unchanged)
# ─────────────────────────────────────────

def _write_equipment_sheet(wb, fmt, sheet_title, equipment_type=None, extra_filter=None, rows=None):
    """Write equipment sheet. If rows is provided, use it; otherwise fetch from DB."""
    if rows is None:
        rows = get_basic_rows(equipment_type=equipment_type, extra_filter=extra_filter)
    headers, rows, col_widths_xl = _filter_empty_cols(
        BASIC_FIELDS, rows, widths=BASIC_COL_WIDTHS_XL,
    )
    n_cols = len(headers)
    ws     = wb.add_worksheet(_safe_sheet_name(sheet_title))
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    ws.hide_gridlines(2)
    ws.protect(REPORT_PASSWORD)

    row = _xl_write_header(ws, fmt, f"Equipment Report — {sheet_title}", n_cols)
    for col_idx, w in enumerate(col_widths_xl or [15] * n_cols):
        ws.set_column(col_idx, col_idx, w)

    ws.set_row(row, 20)
    for col_idx, h in enumerate(headers):
        ws.write(row, col_idx, h, fmt["header"])
    row += 1

    if not rows:
        ws.write(row, 0, "No data available", fmt["data"])
    else:
        for i, data_row in enumerate(rows):
            f = fmt["data_alt"] if i % 2 == 0 else fmt["data"]
            ws.set_row(row, 16)
            for col_idx, val in enumerate(data_row):
                ws.write(row, col_idx, val, f)
            row += 1


def _write_stock_sheet(wb, fmt, sheet_title, equipment_type=None):
    qs = (
        Stock.objects
        .filter(equipment__equipment_type__isnull=False)
        .values(
            "equipment__serial_number", "equipment__marking_code",
            "equipment__brand__name",   "equipment__model",
            "equipment__status__name",  "condition", "date_added",
        )
        .order_by("equipment__model")
    )
    if equipment_type:
        qs = qs.filter(equipment__equipment_type__name=equipment_type)

    rows = []
    for sn, s in enumerate(qs.iterator(chunk_size=2000), start=1):
        rows.append([
            str(sn),
            s["equipment__serial_number"] or "—",
            s["equipment__marking_code"]  or "—",
            s["equipment__brand__name"]   or "—",
            s["equipment__model"]         or "—",
            s["equipment__status__name"]  or "—",
            s["condition"]                or "—",
            str(s["date_added"])          or "—",
        ])

    stock_widths_xl = [round(w / cm * _CM_TO_XL, 1) for w in STOCK_COL_WIDTHS_CM]
    headers, rows, col_widths_xl = _filter_empty_cols(
        STOCK_FIELDS, rows, widths=stock_widths_xl,
    )
    n_cols = len(headers)
    ws     = wb.add_worksheet(_safe_sheet_name(sheet_title))
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    ws.hide_gridlines(2)
    ws.protect(REPORT_PASSWORD)

    row = _xl_write_header(ws, fmt, f"Stock Report — {sheet_title}", n_cols)
    for col_idx, w in enumerate(col_widths_xl or [15] * n_cols):
        ws.set_column(col_idx, col_idx, w)

    ws.set_row(row, 20)
    for col_idx, h in enumerate(headers):
        ws.write(row, col_idx, h, fmt["header"])
    row += 1

    if not rows:
        ws.write(row, 0, "No stock items available", fmt["data"])
    else:
        for i, data_row in enumerate(rows):
            f = fmt["data_alt"] if i % 2 == 0 else fmt["data"]
            ws.set_row(row, 16)
            for col_idx, val in enumerate(data_row):
                ws.write(row, col_idx, val, f)
            row += 1


def _write_unit_sheet(wb, fmt, unit_name, extra_filter):
    n_cols = len(UNIT_FIELDS)
    ws     = wb.add_worksheet(_safe_sheet_name(unit_name))
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    ws.hide_gridlines(2)
    ws.protect(REPORT_PASSWORD)

    for col_idx, w in enumerate(UNIT_COL_WIDTHS_XL):
        ws.set_column(col_idx, col_idx, w)

    ws.set_row(0, 30)
    ws.set_row(1, 10)
    ws.merge_range(0, 0, 1, n_cols - 1, unit_name.upper(), fmt["banner"])

    row         = 2
    section_num = 0

    for eq_type in _TYPE_ORDER:
        rows = _unit_device_rows_fast(extra_filter, eq_type)
        if not rows:
            continue

        unit_widths_cm = [_UNIT_FIELD_WIDTH[h] for h in UNIT_FIELDS]
        headers_f, rows_f, _ = _filter_empty_cols(UNIT_FIELDS, rows, widths=unit_widths_cm)
        n_cols_section = len(headers_f)

        section_num += 1
        label = f"{section_num}. {_TYPE_LABELS.get(eq_type, eq_type.upper())}"

        ws.set_row(row, 18)
        ws.merge_range(row, 0, row, n_cols_section - 1, label, fmt["section"])
        row += 1

        ws.set_row(row, 18)
        for col_idx, h in enumerate(headers_f):
            ws.write(row, col_idx, h, fmt["header"])
        row += 1

        for i, data_row in enumerate(rows_f):
            f = fmt["data_alt"] if i % 2 == 0 else fmt["data"]
            ws.set_row(row, 15)
            for col_idx, val in enumerate(data_row):
                ws.write(row, col_idx, val, f)
            row += 1

        row += 1  # spacer


def _write_summary_sheet(wb, fmt, title, col_a_label, rows_data, grand_total):
    ws = wb.add_worksheet("Summary")
    ws.set_landscape()
    ws.hide_gridlines(2)
    ws.protect(REPORT_PASSWORD)
    ws.set_column(0, 0, 30)
    ws.set_column(1, 1, 15)
    ws.set_column(2, 2, 10)

    row = _xl_write_header(ws, fmt, title, 3)
    ws.set_row(row, 22)
    ws.write(row, 0, col_a_label, fmt["header"])
    ws.write(row, 1, "Count",     fmt["header"])
    ws.write(row, 2, "",          fmt["header"])
    row += 1

    for i, (label, count) in enumerate(rows_data):
        f = fmt["data_alt"] if i % 2 == 0 else fmt["data"]
        ws.set_row(row, 18)
        ws.write(row, 0, label, f)
        ws.write(row, 1, count, f)
        ws.write(row, 2, "",   f)
        row += 1

    ws.set_row(row, 22)
    ws.write(row, 0, "TOTAL",     fmt["grand"])
    ws.write(row, 1, grand_total, fmt["grand"])
    ws.write(row, 2, "",          fmt["grand"])


def _write_equipment_summary_sheet(wb, fmt, summary):
    ws = wb.add_worksheet("Summary")
    ws.set_landscape()
    ws.hide_gridlines(2)
    ws.protect(REPORT_PASSWORD)
    col_widths = [28, 8, 8, 10, 14, 10, 10, 8]
    for i, w in enumerate(col_widths):
        ws.set_column(i, i, w)

    row = _xl_write_header(ws, fmt, "Equipment Summary Report", 8)
    headers = ["Equipment Type","Total","Active","Inactive","Under Repair","Retired","Damaged","New"]
    ws.set_row(row, 22)
    for col_idx, h in enumerate(headers):
        ws.write(row, col_idx, h, fmt["header"])
    row += 1

    for i, (eq_type, stats) in enumerate(summary.items()):
        if eq_type == "__grand_total__":
            continue
        f = fmt["data_alt"] if i % 2 == 0 else fmt["data"]
        ws.set_row(row, 18)
        for col_idx, val in enumerate([
            eq_type,
            stats["total"],   stats["active"],   stats["inactive"],
            stats["under_repair"], stats["retired"], stats["damaged"], stats["new"],
        ]):
            ws.write(row, col_idx, val, f)
        row += 1

    ws.set_row(row, 22)
    ws.write(row, 0, "GRAND TOTAL",              fmt["grand"])
    ws.write(row, 1, summary["__grand_total__"], fmt["grand"])
    for col_idx in range(2, 8):
        ws.write(row, col_idx, "", fmt["grand"])


# ═══════════════════════════════════════════════════════════════════
#  PDF STYLES  — font size 11 throughout, tight padding
# ═══════════════════════════════════════════════════════════════════

_PDF_STYLES = getSampleStyleSheet()

# ── table cell styles ──────────────────────────────────────────────
_CELL_STYLE = ParagraphStyle(
    "CellNormal",
    fontName=_PDF_FONT, fontSize=11,
    leading=13, wordWrap="LTR", alignment=1,
)
_HEADER_CELL_STYLE = ParagraphStyle(
    "CellHeader",
    fontName=_PDF_FONT_BOLD, fontSize=11,
    leading=13, wordWrap="LTR",
    textColor=colors.white, alignment=1,
)

# ── header block styles ────────────────────────────────────────────
_STYLE_PDF_SYSTEM = ParagraphStyle(
    "PDFSystemName", parent=_PDF_STYLES["Normal"],
    fontSize=11, fontName=_PDF_FONT_BOLD,
    textColor=PDF_DARK, alignment=0,          
    spaceBefore=2, spaceAfter=0,
)
_STYLE_PDF_REPORT = ParagraphStyle(
    "PDFReportTitle", parent=_PDF_STYLES["Normal"],
    fontSize=11, fontName=_PDF_FONT,
    textColor=colors.HexColor("#444444"), alignment=0,
    spaceBefore=1, spaceAfter=0,
)

# ── section / heading styles ───────────────────────────────────────
_STYLE_PDF_HEADING = ParagraphStyle(
    "PDFHeading", parent=_PDF_STYLES["Heading2"],
    textColor=PDF_DARK, fontName=_PDF_FONT_BOLD,
    fontSize=11, spaceBefore=4, spaceAfter=2,
)
_STYLE_PDF_SMALL = ParagraphStyle(
    "PDFSmall", parent=_PDF_STYLES["Normal"],
    fontSize=9, fontName=_PDF_FONT, textColor=colors.grey,
)
_STYLE_SEC_HEAD = ParagraphStyle(
    "PDFSecHead", parent=_PDF_STYLES["Normal"],
    fontSize=11, fontName=_PDF_FONT_BOLD, textColor=colors.white,
    backColor=colors.HexColor("#2E4DA0"),
    spaceAfter=0, spaceBefore=4, leftIndent=4,
)
_STYLE_UNIT_HEAD = ParagraphStyle(
    "PDFUnitHead", parent=_PDF_STYLES["Heading1"],
    textColor=colors.HexColor("#003580"), fontSize=11, fontName=_PDF_FONT_BOLD,
)
_STYLE_REGION_HEAD = ParagraphStyle(
    "PDFRegionHead", parent=_PDF_STYLES["Heading1"],
    textColor=colors.HexColor("#003580"), fontSize=11, fontName=_PDF_FONT_BOLD,
)
_STYLE_DPU_HEAD = ParagraphStyle(
    "PDFDPUHead", parent=_PDF_STYLES["Heading1"],
    textColor=colors.HexColor("#003580"), fontSize=11, fontName=_PDF_FONT_BOLD,
)

# ── base table style ───────────────────────────────────────────────
TABLE_STYLE = TableStyle([
    ("BACKGROUND",    (0, 0),  (-1, 0),  PDF_DARK),
    ("TEXTCOLOR",     (0, 0),  (-1, 0),  colors.white),
    ("FONTNAME",      (0, 0),  (-1, 0),  _PDF_FONT_BOLD),
    ("FONTNAME",      (0, 1),  (-1, -1), _PDF_FONT),
    ("FONTSIZE",      (0, 0),  (-1, -1), 11),
    ("ALIGN",         (0, 0),  (-1, -1), "CENTER"),
    ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS",(0, 1),  (-1, -1), [colors.white, PDF_ALT]),
    ("GRID",          (0, 0),  (-1, -1), 0.4, PDF_GREY),
    # ── tighter row height & padding ──────────────────────────────
    ("ROWHEIGHT",     (0, 0),  (-1, -1), 16),
    ("TOPPADDING",    (0, 0),  (-1, -1), 2),
    ("BOTTOMPADDING", (0, 0),  (-1, -1), 2),
    ("LEFTPADDING",   (0, 0),  (-1, -1), 3),
    ("RIGHTPADDING",  (0, 0),  (-1, -1), 3),
])


# ─────────────────────────────────────────
# PDF HELPERS
# ─────────────────────────────────────────

# Creating many Paragraph objects is extremely expensive in ReportLab.
# To keep PDF generation fast, we keep body cells as plain strings and
# truncate very long values (mostly "Location") to prevent pathological layouts.
_PDF_MAX_CELL_CHARS = 60

def _pdf_cell_text(val, max_chars=_PDF_MAX_CELL_CHARS):
    s = "—" if val is None else str(val)
    s = s.strip() or "—"
    if max_chars and len(s) > max_chars:
        return s[: max_chars - 1] + "…"
    return s

def _wrap_rows(header_row, data_rows):
    """Wrap header with Paragraph; keep data rows as strings for speed."""
    wrapped_header = [Paragraph(str(h), _HEADER_CELL_STYLE) for h in header_row]
    wrapped_data   = [[_pdf_cell_text(c) for c in row] for row in data_rows]
    return wrapped_header, wrapped_data


def _pdf_tables_chunked(headers, rows, col_widths, *, chunk_size=200):
    """
    Build one or more Tables from rows, split into smaller chunks.
    This avoids very slow layout when a single table has many rows.
    """
    if not rows:
        return []
    out = []
    for start in range(0, len(rows), chunk_size):
        chunk = rows[start:start + chunk_size]
        w_header, w_data = _wrap_rows(headers, chunk)
        t = Table([w_header] + w_data, repeatRows=1, hAlign="LEFT",
                  colWidths=_scale_to_page(col_widths))
        t.setStyle(TABLE_STYLE)
        out.append(t)
        out.append(Spacer(1, 0.25 * cm))
    return out



def _make_footer_canvas(report_title):
  
    from reportlab.pdfgen import canvas as _canvas_mod

    generated_str = f"Generated: {timezone.now().strftime('%d %B %Y at %H:%M')}"

    def _draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(_PDF_FONT, 8)
        canvas.setFillColor(colors.grey)
        # Bottom-right: x = page width − right margin, y = bottom margin / 2
        x = doc.pagesize[0] - doc.rightMargin
        y = doc.bottomMargin * 0.5
        canvas.drawRightString(x, y, generated_str)
        canvas.restoreState()

    return _draw_footer


def _pdf_header(report_title):
   
    # ── left cell: logo (if present) + system name below it ──────
    left_items = []
    if os.path.exists(LOGO_PATH):
        left_items.append(RLImage(LOGO_PATH, width=1.8*cm, height=1.8*cm))
        left_items.append(Spacer(1, 0.1*cm))
    left_items.append(Paragraph(SYSTEM_NAME or "", _STYLE_PDF_SYSTEM))

    # ── right cell: report title ──────────────────────────────────
    _STYLE_REPORT_RIGHT = ParagraphStyle(
        "PDFReportRight", parent=_PDF_STYLES["Normal"],
        fontSize=11, fontName=_PDF_FONT_BOLD,
        textColor=PDF_ACCENT, alignment=1,   # centred
    )
    right_items = [Paragraph(report_title, _STYLE_REPORT_RIGHT)]

    header_table = Table(
        [[left_items, right_items]],
        colWidths=[4*cm, PAGE_CONTENT_WIDTH - 4*cm],
        hAlign="LEFT",
    )
    header_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",        (0, 0), (0, 0),   "LEFT"),
        ("ALIGN",        (1, 0), (1, 0),   "CENTER"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    return header_table


# ─────────────────────────────────────────
# PDF SUMMARY TABLE
# ─────────────────────────────────────────

def _pdf_summary_table(summary):
    headers = ["Equipment Type","Total","Active","Inactive","Under Repair","Retired","Damaged","New"]
    data    = [headers]
    for eq_type, stats in summary.items():
        if eq_type == "__grand_total__":
            continue
        data.append([
            eq_type,
            stats["total"],   stats["active"],   stats["inactive"],
            stats["under_repair"], stats["retired"], stats["damaged"], stats["new"],
        ])
    data.append(["GRAND TOTAL", summary["__grand_total__"], "", "", "", "", "", ""])
    w_header, w_data = _wrap_rows(data[0], data[1:])
    t = Table([w_header] + w_data, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  PDF_DARK),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0),  (-1, 0),  _PDF_FONT_BOLD),
        ("FONTNAME",      (0, 1),  (-1, -1), _PDF_FONT),
        ("FONTSIZE",      (0, 0),  (-1, -1), 11),
        ("ALIGN",         (0, 0),  (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [colors.white, PDF_ALT]),
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


def _pdf_equipment_section(equipment_type, rows=None):
    """Generate PDF section for equipment type. If rows provided, use it; otherwise fetch from DB."""
    elements = [
        HRFlowable(width="100%", thickness=1, color=PDF_GREY),
        Spacer(1, 0.2*cm),
        Paragraph(equipment_type, _STYLE_PDF_HEADING),
    ]
    if rows is None:
        rows = get_basic_rows(equipment_type=equipment_type)
    if not rows:
        elements.append(Paragraph("No data available.", _STYLE_PDF_SMALL))
        elements.append(Spacer(1, 0.3*cm))
        return elements
    headers, rows, col_widths = _filter_empty_cols(
        BASIC_FIELDS, rows, widths=[_FIELD_WIDTH[h] for h in BASIC_FIELDS],
    )
    # Chunk large tables to keep ReportLab layout fast.
    elements.extend(_pdf_tables_chunked(headers, rows, col_widths, chunk_size=200))
    return elements


# ─────────────────────────────────────────
# BUILD PDF  — now wires up the footer callback
# ─────────────────────────────────────────

def _build_pdf(elements, report_title=""):
    output   = io.BytesIO()
    footer_cb = _make_footer_canvas(report_title)
    doc = SimpleDocTemplate(
        output, pagesize=landscape(A4),
        rightMargin=1*cm, leftMargin=1*cm,
        # ── reduced top / bottom margins ──────────────────────────
        topMargin=0.2*cm, bottomMargin=0.2*cm,
    )
    doc.build(elements, onFirstPage=footer_cb, onLaterPages=footer_cb)
    output.seek(0)
    return output


# ─────────────────────────────────────────
# PDF UNIT / REGION / DPU SECTION
# ─────────────────────────────────────────

def _pdf_unit_section(eq_type, section_num, rows):
    """Build one equipment-type section from pre-fetched rows (no DB call)."""
    if not rows:
        return []
    label = f"{section_num}. {_TYPE_LABELS.get(eq_type, eq_type.upper())}"
    unit_widths = [_UNIT_FIELD_WIDTH[h] for h in UNIT_FIELDS]
    headers_f, rows_f, col_widths_f = _filter_empty_cols(UNIT_FIELDS, rows, widths=unit_widths)
    elements = [Paragraph(label, _STYLE_SEC_HEAD)]
    elements.extend(_pdf_tables_chunked(headers_f, rows_f, col_widths_f, chunk_size=200))
    return elements


# ─────────────────────────────────────────
# BATCHED LOCATION DATA HELPERS
# ─────────────────────────────────────────

def _fetch_unit_rows_grouped(unit_qs):
    """
    Fetch all equipment for a set of units in ONE query.
    Returns: dict { unit_id: { eq_type: [[row], ...] } }
    """
    ids = list(unit_qs.values_list("id", flat=True))
    if not ids:
        return {}
    qs = (
        Equipment.objects
        .filter(unit_id__in=ids, equipment_type__isnull=False)
        .values(
            "unit_id", "equipment_type__name",
            "brand__name", "serial_number", "marking_code",
            "status__name", "deployment_date",
            "office__name", "department__name", "directorate__name", "unit__name",
            "region__name", "region__region_office__name",
            "dpu__name",    "dpu__dpu_office__name",
        )
        .order_by("unit_id", "equipment_type__name", "brand__name", "serial_number")
    )
    grouped = {}   # { unit_id: { eq_type: [rows] } }
    counters = {}  # { (unit_id, eq_type): int }
    for obj in qs.iterator(chunk_size=2000):
        uid    = str(obj["unit_id"])
        etype  = obj["equipment_type__name"]
        key    = (uid, etype)
        if uid not in grouped:
            grouped[uid] = {}
        if etype not in grouped[uid]:
            grouped[uid][etype] = []
        counters[key] = counters.get(key, 0) + 1
        grouped[uid][etype].append([
            str(counters[key]),
            obj["brand__name"]   or "—",
            obj["serial_number"] or "—",
            obj["marking_code"]  or "—",
            _build_location_from_dict(obj),
            obj["status__name"]  or "—",
            _age_from_date(obj["deployment_date"]),
        ])
    return grouped


def _fetch_region_rows_grouped(region_qs):
    """
    Fetch all equipment for a set of regions in ONE query.
    Returns: dict { region_id: { eq_type: [[row], ...] } }
    """
    ids = list(region_qs.values_list("id", flat=True))
    if not ids:
        return {}
    qs = (
        Equipment.objects
        .filter(region_id__in=ids, equipment_type__isnull=False)
        .values(
            "region_id", "equipment_type__name",
            "brand__name", "serial_number", "marking_code",
            "status__name", "deployment_date",
            "office__name", "department__name", "directorate__name", "unit__name",
            "region__name", "region__region_office__name",
            "dpu__name",    "dpu__dpu_office__name",
        )
        .order_by("region_id", "equipment_type__name", "brand__name", "serial_number")
    )
    grouped = {}
    counters = {}
    for obj in qs.iterator(chunk_size=2000):
        rid   = str(obj["region_id"])
        etype = obj["equipment_type__name"]
        key   = (rid, etype)
        if rid not in grouped:
            grouped[rid] = {}
        if etype not in grouped[rid]:
            grouped[rid][etype] = []
        counters[key] = counters.get(key, 0) + 1
        grouped[rid][etype].append([
            str(counters[key]),
            obj["brand__name"]   or "—",
            obj["serial_number"] or "—",
            obj["marking_code"]  or "—",
            _build_location_from_dict(obj),
            obj["status__name"]  or "—",
            _age_from_date(obj["deployment_date"]),
        ])
    return grouped


def _fetch_dpu_rows_grouped(dpu_qs):
    """
    Fetch all equipment for a set of DPUs in ONE query.
    Returns: dict { dpu_id: { eq_type: [[row], ...] } }
    """
    ids = list(dpu_qs.values_list("id", flat=True))
    if not ids:
        return {}
    qs = (
        Equipment.objects
        .filter(dpu_id__in=ids, equipment_type__isnull=False)
        .values(
            "dpu_id", "equipment_type__name",
            "brand__name", "serial_number", "marking_code",
            "status__name", "deployment_date",
            "office__name", "department__name", "directorate__name", "unit__name",
            "region__name", "region__region_office__name",
            "dpu__name",    "dpu__dpu_office__name",
        )
        .order_by("dpu_id", "equipment_type__name", "brand__name", "serial_number")
    )
    grouped = {}
    counters = {}
    for obj in qs.iterator(chunk_size=2000):
        did   = str(obj["dpu_id"])
        etype = obj["equipment_type__name"]
        key   = (did, etype)
        if did not in grouped:
            grouped[did] = {}
        if etype not in grouped[did]:
            grouped[did][etype] = []
        counters[key] = counters.get(key, 0) + 1
        grouped[did][etype].append([
            str(counters[key]),
            obj["brand__name"]   or "—",
            obj["serial_number"] or "—",
            obj["marking_code"]  or "—",
            _build_location_from_dict(obj),
            obj["status__name"]  or "—",
            _age_from_date(obj["deployment_date"]),
        ])
    return grouped


# ═════════════════════════════════════════════════════════════════
#  EXCEL — EQUIPMENT
# ═════════════════════════════════════════════════════════════════

def generate_excel_all():
    """Generate Excel report for all equipment types using a single batched query."""
    output, wb, fmt = _new_workbook()
    summary  = get_summary()
    
    # Fetch all data in ONE query, grouped by equipment type
    all_rows_grouped = get_all_basic_rows_grouped()
    eq_types = sorted(all_rows_grouped.keys())
    
    _write_equipment_summary_sheet(wb, fmt, summary)
    for eq_type in eq_types:
        _write_equipment_sheet(wb, fmt, eq_type, rows=all_rows_grouped.get(eq_type, []))
    return _close_workbook(wb, output)


def generate_excel_by_type(equipment_type):
    output, wb, fmt = _new_workbook()
    _write_equipment_sheet(wb, fmt, equipment_type, equipment_type=equipment_type)
    return _close_workbook(wb, output)


# ═════════════════════════════════════════════════════════════════
#  PDF — EQUIPMENT
# ═════════════════════════════════════════════════════════════════

def generate_pdf_all():
    """Generate PDF report for all equipment types using a single batched query."""
    title    = "Full Equipment Report"
    elements = [
        _pdf_header(title),
        Spacer(1, 0.2*cm),
        HRFlowable(width="100%", thickness=2, color=PDF_ACCENT),
        Spacer(1, 0.3*cm),
        Paragraph("Summary", _STYLE_PDF_HEADING),
        Spacer(1, 0.1*cm),
        _pdf_summary_table(get_summary()),
        Spacer(1, 0.5*cm),
    ]
    
    # Fetch all data in ONE query, grouped by equipment type
    all_rows_grouped = get_all_basic_rows_grouped()
    for eq_type in sorted(all_rows_grouped.keys()):
        elements.extend(_pdf_equipment_section(eq_type, rows=all_rows_grouped[eq_type]))
    
    return _build_pdf(elements, title)


def generate_pdf_by_type(equipment_type):
    title    = f"{equipment_type} Report"
    elements = [
        _pdf_header(title),
        Spacer(1, 0.2*cm),
        HRFlowable(width="100%", thickness=2, color=PDF_ACCENT),
        Spacer(1, 0.3*cm),
    ]
    elements.extend(_pdf_equipment_section(equipment_type))
    return _build_pdf(elements, title)


# ═════════════════════════════════════════════════════════════════
#  EXCEL — STOCK
# ═════════════════════════════════════════════════════════════════

def generate_stock_excel_all():
    output, wb, fmt = _new_workbook()
    type_counts = dict(
        Stock.objects
        .filter(equipment__equipment_type__isnull=False)
        .values("equipment__equipment_type__name")
        .annotate(count=Count("id"))
        .order_by("equipment__equipment_type__name")
        .values_list("equipment__equipment_type__name", "count")
    )
    types_in_stock = list(type_counts.keys())
    _write_summary_sheet(
        wb, fmt, "Stock Summary", "Equipment Type",
        list(type_counts.items()), sum(type_counts.values()),
    )
    for eq_type in types_in_stock:
        _write_stock_sheet(wb, fmt, eq_type, equipment_type=eq_type)
    return _close_workbook(wb, output)


def generate_stock_excel_by_type(equipment_type):
    output, wb, fmt = _new_workbook()
    _write_stock_sheet(wb, fmt, equipment_type, equipment_type=equipment_type)
    return _close_workbook(wb, output)


# ═════════════════════════════════════════════════════════════════
#  PDF — STOCK
# ═════════════════════════════════════════════════════════════════

def _pdf_stock_section(equipment_type):
    elements = [
        HRFlowable(width="100%", thickness=1, color=PDF_GREY),
        Spacer(1, 0.2*cm),
        Paragraph(equipment_type, _STYLE_PDF_HEADING),
    ]
    qs = (
        Stock.objects
        .filter(equipment__equipment_type__name=equipment_type)
        .values(
            "equipment__serial_number", "equipment__marking_code",
            "equipment__brand__name",   "equipment__model",
            "equipment__status__name",  "condition", "date_added",
        )
        .order_by("equipment__model")
    )
    rows = []
    for sn, s in enumerate(qs.iterator(chunk_size=2000), start=1):
        rows.append([
            str(sn),
            s["equipment__serial_number"] or "—",
            s["equipment__marking_code"]  or "—",
            s["equipment__brand__name"]   or "—",
            s["equipment__model"]         or "—",
            s["equipment__status__name"]  or "—",
            s["condition"]                or "—",
            str(s["date_added"])          or "—",
        ])
    if not rows:
        elements.append(Paragraph("No stock items available.", _STYLE_PDF_SMALL))
        elements.append(Spacer(1, 0.3*cm))
        return elements
    stock_widths = [_STOCK_FIELD_WIDTH[h] for h in STOCK_FIELDS]
    headers, rows, col_widths = _filter_empty_cols(STOCK_FIELDS, rows, widths=stock_widths)
    elements.extend(_pdf_tables_chunked(headers, rows, col_widths, chunk_size=200))
    return elements


def generate_stock_pdf_all():
    type_counts = dict(
        Stock.objects
        .filter(equipment__equipment_type__isnull=False)
        .values("equipment__equipment_type__name")
        .annotate(count=Count("id"))
        .order_by("equipment__equipment_type__name")
        .values_list("equipment__equipment_type__name", "count")
    )
    types_in_stock = list(type_counts.keys())
    total_stock    = sum(type_counts.values())

    summary_data = [["Equipment Type", "Items in Stock"]]
    for eq_type in types_in_stock:
        summary_data.append([eq_type, type_counts[eq_type]])
    summary_data.append(["TOTAL", total_stock])

    sw_header, sw_data = _wrap_rows(summary_data[0], summary_data[1:])
    summary_tbl = Table([sw_header] + sw_data, repeatRows=1, hAlign="LEFT")
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  PDF_DARK),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0),  (-1, 0),  _PDF_FONT_BOLD),
        ("FONTNAME",      (0, 1),  (-1, -1), _PDF_FONT),
        ("FONTSIZE",      (0, 0),  (-1, -1), 11),
        ("ALIGN",         (0, 0),  (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [colors.white, PDF_ALT]),
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
    title    = "Full Stock Report"
    elements = [
        _pdf_header(title),
        Spacer(1, 0.2*cm),
        HRFlowable(width="100%", thickness=2, color=PDF_ACCENT),
        Spacer(1, 0.3*cm),
        Paragraph("Summary", _STYLE_PDF_HEADING),
        Spacer(1, 0.1*cm),
        summary_tbl,
        Spacer(1, 0.5*cm),
    ]
    for eq_type in types_in_stock:
        elements.extend(_pdf_stock_section(eq_type))
    return _build_pdf(elements, title)


def generate_stock_pdf_by_type(equipment_type):
    title    = f"{equipment_type} Stock Report"
    elements = [
        _pdf_header(title),
        Spacer(1, 0.2*cm),
        HRFlowable(width="100%", thickness=2, color=PDF_ACCENT),
        Spacer(1, 0.3*cm),
    ]
    elements.extend(_pdf_stock_section(equipment_type))
    return _build_pdf(elements, title)


# ═════════════════════════════════════════════════════════════════
#  EXCEL — UNITS
# ═════════════════════════════════════════════════════════════════

def generate_unit_excel_all():
    output, wb, fmt = _new_workbook()
    unit_counts = dict(
        Equipment.objects.filter(unit__isnull=False)
        .values("unit__name").annotate(count=Count("id"))
        .order_by("unit__name").values_list("unit__name", "count")
    )
    units = Unit.objects.order_by("name")
    _write_summary_sheet(
        wb, fmt, "Equipment by Organisational Unit", "Unit",
        [(u.name, unit_counts.get(u.name, 0)) for u in units if unit_counts.get(u.name, 0) > 0],
        sum(unit_counts.values()),
    )
    for unit in units:
        if unit_counts.get(unit.name, 0):
            _write_unit_sheet(wb, fmt, unit.name, {"unit": unit})
    return _close_workbook(wb, output)


def generate_unit_excel_by_unit(unit_id):
    unit = Unit.objects.get(pk=unit_id)
    output, wb, fmt = _new_workbook()
    _write_unit_sheet(wb, fmt, unit.name, {"unit": unit})
    return _close_workbook(wb, output)


# ═════════════════════════════════════════════════════════════════
#  PDF — UNITS
# ═════════════════════════════════════════════════════════════════

def _pdf_unit_block(unit, type_rows):
    """Build PDF block for one unit using pre-fetched type_rows dict."""
    if not type_rows:
        return []
    elements = [
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#003580")),
        Spacer(1, 0.1*cm),
        Paragraph(unit.name.upper(), _STYLE_UNIT_HEAD),
        Spacer(1, 0.1*cm),
    ]
    sec_num = 0
    for eq_type in _TYPE_ORDER:
        rows = type_rows.get(eq_type, [])
        if rows:
            sec_num += 1
            elements.extend(_pdf_unit_section(eq_type, sec_num, rows))
    elements.append(Spacer(1, 0.4*cm))
    return elements


def generate_unit_pdf_all():
    """Generate PDF for all units — ONE query for all equipment, zero per-unit queries."""
    title    = "Equipment Report by Organisational Unit"
    units    = list(Unit.objects.order_by("name"))
    all_data = _fetch_unit_rows_grouped(Unit.objects.all())
    elements = [_pdf_header(title), Spacer(1, 0.3*cm)]
    for unit in units:
        type_rows = all_data.get(str(unit.id), {})
        elements.extend(_pdf_unit_block(unit, type_rows))
    return _build_pdf(elements, title)


def generate_unit_pdf_by_unit(unit_id):
    unit     = Unit.objects.get(pk=unit_id)
    all_data = _fetch_unit_rows_grouped(Unit.objects.filter(pk=unit_id))
    type_rows = all_data.get(str(unit.id), {})
    title    = f"{unit.name.upper()} — Equipment Report"
    elements = [_pdf_header(title), Spacer(1, 0.3*cm)]
    elements.extend(_pdf_unit_block(unit, type_rows))
    return _build_pdf(elements, title)


# ═════════════════════════════════════════════════════════════════
#  EXCEL — REGIONS
# ═════════════════════════════════════════════════════════════════

def generate_region_excel_all():
    output, wb, fmt = _new_workbook()
    region_counts = dict(
        Equipment.objects.filter(region__isnull=False)
        .values("region__name").annotate(count=Count("id"))
        .order_by("region__name").values_list("region__name", "count")
    )
    regions = Region.objects.order_by("name")
    _write_summary_sheet(
        wb, fmt, "Equipment by Region", "Region",
        [(r.name, region_counts.get(r.name, 0)) for r in regions if region_counts.get(r.name, 0) > 0],
        sum(region_counts.values()),
    )
    for region in regions:
        if region_counts.get(region.name, 0):
            _write_unit_sheet(wb, fmt, region.name, {"region": region})
    return _close_workbook(wb, output)


def generate_region_excel_by_region(region_id):
    region = Region.objects.get(pk=region_id)
    output, wb, fmt = _new_workbook()
    _write_unit_sheet(wb, fmt, region.name, {"region": region})
    return _close_workbook(wb, output)


# ═════════════════════════════════════════════════════════════════
#  PDF — REGIONS
# ═════════════════════════════════════════════════════════════════

def _pdf_region_block(region, type_rows):
    """Build PDF block for one region using pre-fetched type_rows dict."""
    if not type_rows:
        return []
    elements = [
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#003580")),
        Spacer(1, 0.1*cm),
        Paragraph(region.name.upper(), _STYLE_REGION_HEAD),
        Spacer(1, 0.1*cm),
    ]
    sec_num = 0
    for eq_type in _TYPE_ORDER:
        rows = type_rows.get(eq_type, [])
        if rows:
            sec_num += 1
            elements.extend(_pdf_unit_section(eq_type, sec_num, rows))
    elements.append(Spacer(1, 0.4*cm))
    return elements


def generate_region_pdf_all():
    """Generate PDF for all regions — ONE query for all equipment, zero per-region queries."""
    title   = "Equipment Report by Region"
    regions = list(Region.objects.order_by("name"))
    all_data = _fetch_region_rows_grouped(Region.objects.all())
    elements = [_pdf_header(title), Spacer(1, 0.3*cm)]
    for region in regions:
        type_rows = all_data.get(str(region.id), {})
        elements.extend(_pdf_region_block(region, type_rows))
    return _build_pdf(elements, title)


def generate_region_pdf_by_region(region_id):
    region   = Region.objects.get(pk=region_id)
    all_data = _fetch_region_rows_grouped(Region.objects.filter(pk=region_id))
    type_rows = all_data.get(str(region.id), {})
    title    = f"{region.name.upper()} — Equipment Report"
    elements = [_pdf_header(title), Spacer(1, 0.3*cm)]
    elements.extend(_pdf_region_block(region, type_rows))
    return _build_pdf(elements, title)


# ═════════════════════════════════════════════════════════════════
#  EXCEL — DPUs
# ═════════════════════════════════════════════════════════════════

def generate_dpu_excel_all():
    output, wb, fmt = _new_workbook()
    dpu_counts = dict(
        Equipment.objects.filter(dpu__isnull=False)
        .values("dpu__name").annotate(count=Count("id"))
        .order_by("dpu__name").values_list("dpu__name", "count")
    )
    dpus = DPU.objects.order_by("name")
    _write_summary_sheet(
        wb, fmt, "Equipment by DPU", "DPU",
        [(d.name, dpu_counts.get(d.name, 0)) for d in dpus if dpu_counts.get(d.name, 0) > 0],
        sum(dpu_counts.values()),
    )
    for dpu in dpus:
        if dpu_counts.get(dpu.name, 0):
            _write_unit_sheet(wb, fmt, dpu.name, {"dpu": dpu})
    return _close_workbook(wb, output)


def generate_dpu_excel_by_dpu(dpu_id):
    dpu = DPU.objects.get(pk=dpu_id)
    output, wb, fmt = _new_workbook()
    _write_unit_sheet(wb, fmt, dpu.name, {"dpu": dpu})
    return _close_workbook(wb, output)


# ═════════════════════════════════════════════════════════════════
#  PDF — DPUs
# ═════════════════════════════════════════════════════════════════

def _pdf_dpu_block(dpu, type_rows):
    """Build PDF block for one DPU using pre-fetched type_rows dict."""
    if not type_rows:
        return []
    elements = [
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#003580")),
        Spacer(1, 0.1*cm),
        Paragraph(dpu.name.upper(), _STYLE_DPU_HEAD),
        Spacer(1, 0.1*cm),
    ]
    sec_num = 0
    for eq_type in _TYPE_ORDER:
        rows = type_rows.get(eq_type, [])
        if rows:
            sec_num += 1
            elements.extend(_pdf_unit_section(eq_type, sec_num, rows))
    elements.append(Spacer(1, 0.4*cm))
    return elements


def generate_dpu_pdf_all():
    """Generate PDF for all DPUs — ONE query for all equipment, zero per-DPU queries."""
    title   = "Equipment Report by DPU"
    dpus    = list(DPU.objects.order_by("name"))
    all_data = _fetch_dpu_rows_grouped(DPU.objects.all())
    elements = [_pdf_header(title), Spacer(1, 0.3*cm)]
    for dpu in dpus:
        type_rows = all_data.get(str(dpu.id), {})
        elements.extend(_pdf_dpu_block(dpu, type_rows))
    return _build_pdf(elements, title)


def generate_dpu_pdf_by_dpu(dpu_id):
    dpu      = DPU.objects.get(pk=dpu_id)
    all_data = _fetch_dpu_rows_grouped(DPU.objects.filter(pk=dpu_id))
    type_rows = all_data.get(str(dpu.id), {})
    title    = f"{dpu.name.upper()} — Equipment Report"
    elements = [_pdf_header(title), Spacer(1, 0.3*cm)]
    elements.extend(_pdf_dpu_block(dpu, type_rows))
    return _build_pdf(elements, title)