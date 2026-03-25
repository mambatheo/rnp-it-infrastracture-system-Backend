import base64
from celery import shared_task
from .reports import (
    generate_excel_all,            generate_excel_by_type,
    generate_pdf_all,              generate_pdf_by_type,
    generate_stock_excel_all,      generate_stock_excel_by_type,
    generate_stock_pdf_all,        generate_stock_pdf_by_type,
    generate_unit_excel_all,       generate_unit_excel_by_unit,
    generate_unit_pdf_all,         generate_unit_pdf_by_unit,
    generate_region_excel_all,     generate_region_excel_by_region,
    generate_region_pdf_all,       generate_region_pdf_by_region,
    generate_dpu_excel_all,        generate_dpu_excel_by_dpu,
    generate_dpu_pdf_all,          generate_dpu_pdf_by_dpu,
)


def _buf_to_b64(buf):
    """BytesIO → base64 string (JSON-serialisable for Celery result backend)."""
    return base64.b64encode(buf.read()).decode("utf-8")


# ── Equipment ─────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_excel_all(self):
    try:
        return _buf_to_b64(generate_excel_all())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_excel_by_type(self, equipment_type):
    try:
        return _buf_to_b64(generate_excel_by_type(equipment_type))
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_pdf_all(self):
    try:
        return _buf_to_b64(generate_pdf_all())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_pdf_by_type(self, equipment_type):
    try:
        return _buf_to_b64(generate_pdf_by_type(equipment_type))
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Stock ─────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_excel_all(self):
    try:
        return _buf_to_b64(generate_stock_excel_all())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_excel_by_type(self, equipment_type):
    try:
        return _buf_to_b64(generate_stock_excel_by_type(equipment_type))
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_pdf_all(self):
    try:
        return _buf_to_b64(generate_stock_pdf_all())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_pdf_by_type(self, equipment_type):
    try:
        return _buf_to_b64(generate_stock_pdf_by_type(equipment_type))
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Units ─────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_excel_all(self):
    try:
        return _buf_to_b64(generate_unit_excel_all())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_excel_by_unit(self, unit_id):
    try:
        return _buf_to_b64(generate_unit_excel_by_unit(unit_id))
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_pdf_all(self):
    try:
        return _buf_to_b64(generate_unit_pdf_all())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_pdf_by_unit(self, unit_id):
    try:
        return _buf_to_b64(generate_unit_pdf_by_unit(unit_id))
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Regions ───────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_excel_all(self):
    try:
        return _buf_to_b64(generate_region_excel_all())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_excel_by_region(self, region_id):
    try:
        return _buf_to_b64(generate_region_excel_by_region(region_id))
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_pdf_all(self):
    try:
        return _buf_to_b64(generate_region_pdf_all())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_pdf_by_region(self, region_id):
    try:
        return _buf_to_b64(generate_region_pdf_by_region(region_id))
    except Exception as exc:
        raise self.retry(exc=exc)


# ── DPUs ──────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_excel_all(self):
    try:
        return _buf_to_b64(generate_dpu_excel_all())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_excel_by_dpu(self, dpu_id):
    try:
        return _buf_to_b64(generate_dpu_excel_by_dpu(dpu_id))
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_pdf_all(self):
    try:
        return _buf_to_b64(generate_dpu_pdf_all())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_pdf_by_dpu(self, dpu_id):
    try:
        return _buf_to_b64(generate_dpu_pdf_by_dpu(dpu_id))
    except Exception as exc:
        raise self.retry(exc=exc)