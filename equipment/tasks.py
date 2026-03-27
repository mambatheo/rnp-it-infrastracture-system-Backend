import base64
from celery import shared_task
from django.core.cache import cache
from .models import DPU, Region, Unit
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
    get_equipment_types,
)


def _buf_to_b64(buf):
    """BytesIO → base64 string (JSON-serialisable for Celery result backend)."""
    return base64.b64encode(buf.read()).decode("utf-8")


CACHE_30M = 60 * 30
CACHE_15M = 60 * 15


def _cached_task(cache_key, generator_fn, timeout, *args, force=False):
    if not force:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    result = _buf_to_b64(generator_fn(*args))
    cache.set(cache_key, result, timeout=timeout)
    return result


# ── Equipment ─────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_excel_all(self):
    try:
        return _cached_task("report:xlsx:equipment:all", generate_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_excel_by_type(self, equipment_type):
    try:
        key = f"report:xlsx:equipment:{equipment_type.lower()}"
        return _cached_task(key, generate_excel_by_type, CACHE_30M, equipment_type)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_pdf_all(self):
    try:
        return _cached_task("report:pdf:equipment:all", generate_pdf_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_pdf_by_type(self, equipment_type):
    try:
        key = f"report:pdf:equipment:{equipment_type.lower()}"
        return _cached_task(key, generate_pdf_by_type, CACHE_30M, equipment_type)
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Stock ─────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_excel_all(self):
    try:
        return _cached_task("report:xlsx:stock:all", generate_stock_excel_all, CACHE_15M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_excel_by_type(self, equipment_type):
    try:
        key = f"report:xlsx:stock:{equipment_type.lower()}"
        return _cached_task(key, generate_stock_excel_by_type, CACHE_15M, equipment_type)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_pdf_all(self):
    try:
        return _cached_task("report:pdf:stock:all", generate_stock_pdf_all, CACHE_15M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_pdf_by_type(self, equipment_type):
    try:
        key = f"report:pdf:stock:{equipment_type.lower()}"
        return _cached_task(key, generate_stock_pdf_by_type, CACHE_15M, equipment_type)
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Units ─────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_excel_all(self):
    try:
        return _cached_task("report:xlsx:unit:all", generate_unit_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_excel_by_unit(self, unit_id):
    try:
        key = f"report:xlsx:unit:{unit_id}"
        return _cached_task(key, generate_unit_excel_by_unit, CACHE_30M, unit_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_pdf_all(self):
    try:
        return _cached_task("report:pdf:unit:all", generate_unit_pdf_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_pdf_by_unit(self, unit_id):
    try:
        key = f"report:pdf:unit:{unit_id}"
        return _cached_task(key, generate_unit_pdf_by_unit, CACHE_30M, unit_id)
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Regions ───────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_excel_all(self):
    try:
        return _cached_task("report:xlsx:region:all", generate_region_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_excel_by_region(self, region_id):
    try:
        key = f"report:xlsx:region:{region_id}"
        return _cached_task(key, generate_region_excel_by_region, CACHE_30M, region_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_pdf_all(self):
    try:
        return _cached_task("report:pdf:region:all", generate_region_pdf_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_pdf_by_region(self, region_id):
    try:
        key = f"report:pdf:region:{region_id}"
        return _cached_task(key, generate_region_pdf_by_region, CACHE_30M, region_id)
    except Exception as exc:
        raise self.retry(exc=exc)


# ── DPUs ──────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_excel_all(self):
    try:
        return _cached_task("report:xlsx:dpu:all", generate_dpu_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_excel_by_dpu(self, dpu_id):
    try:
        key = f"report:xlsx:dpu:{dpu_id}"
        return _cached_task(key, generate_dpu_excel_by_dpu, CACHE_30M, dpu_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_pdf_all(self):
    try:
        return _cached_task("report:pdf:dpu:all", generate_dpu_pdf_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_pdf_by_dpu(self, dpu_id):
    try:
        key = f"report:pdf:dpu:{dpu_id}"
        return _cached_task(key, generate_dpu_pdf_by_dpu, CACHE_30M, dpu_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def prewarm_equipment_reports(self):
    try:
        _cached_task("report:pdf:equipment:all", generate_pdf_all, CACHE_30M, force=True)
        _cached_task("report:xlsx:equipment:all", generate_excel_all, CACHE_30M, force=True)
        for eq_type in get_equipment_types():
            _cached_task(f"report:pdf:equipment:{eq_type.lower()}", generate_pdf_by_type, CACHE_30M, eq_type, force=True)
            _cached_task(f"report:xlsx:equipment:{eq_type.lower()}", generate_excel_by_type, CACHE_30M, eq_type, force=True)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def prewarm_stock_reports(self):
    try:
        _cached_task("report:pdf:stock:all", generate_stock_pdf_all, CACHE_15M, force=True)
        _cached_task("report:xlsx:stock:all", generate_stock_excel_all, CACHE_15M, force=True)
        for eq_type in get_equipment_types():
            _cached_task(f"report:pdf:stock:{eq_type.lower()}", generate_stock_pdf_by_type, CACHE_15M, eq_type, force=True)
            _cached_task(f"report:xlsx:stock:{eq_type.lower()}", generate_stock_excel_by_type, CACHE_15M, eq_type, force=True)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def prewarm_unit_reports(self):
    try:
        _cached_task("report:pdf:unit:all", generate_unit_pdf_all, CACHE_30M, force=True)
        _cached_task("report:xlsx:unit:all", generate_unit_excel_all, CACHE_30M, force=True)
        for unit in Unit.objects.only("id"):
            _cached_task(f"report:pdf:unit:{unit.id}", generate_unit_pdf_by_unit, CACHE_30M, unit.id, force=True)
            _cached_task(f"report:xlsx:unit:{unit.id}", generate_unit_excel_by_unit, CACHE_30M, unit.id, force=True)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def prewarm_region_reports(self):
    try:
        _cached_task("report:pdf:region:all", generate_region_pdf_all, CACHE_30M, force=True)
        _cached_task("report:xlsx:region:all", generate_region_excel_all, CACHE_30M, force=True)
        for region in Region.objects.only("id"):
            _cached_task(f"report:pdf:region:{region.id}", generate_region_pdf_by_region, CACHE_30M, region.id, force=True)
            _cached_task(f"report:xlsx:region:{region.id}", generate_region_excel_by_region, CACHE_30M, region.id, force=True)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def prewarm_dpu_reports(self):
    try:
        _cached_task("report:pdf:dpu:all", generate_dpu_pdf_all, CACHE_30M, force=True)
        _cached_task("report:xlsx:dpu:all", generate_dpu_excel_all, CACHE_30M, force=True)
        for dpu in DPU.objects.only("id"):
            _cached_task(f"report:pdf:dpu:{dpu.id}", generate_dpu_pdf_by_dpu, CACHE_30M, dpu.id, force=True)
            _cached_task(f"report:xlsx:dpu:{dpu.id}", generate_dpu_excel_by_dpu, CACHE_30M, dpu.id, force=True)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def prewarm_all_reports():
    prewarm_equipment_reports.delay()
    prewarm_stock_reports.delay()
    prewarm_unit_reports.delay()
    prewarm_region_reports.delay()
    prewarm_dpu_reports.delay()