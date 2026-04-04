import base64
import time
from celery import shared_task
from django.core.cache import cache
from .models import DPU, Region, Unit, TrainingSchool
from .reports import (
    generate_excel_all,                generate_excel_by_type,
    generate_pdf_all,                  generate_pdf_by_type,
    generate_stock_excel_all,          generate_stock_excel_by_type,
    generate_stock_pdf_all,            generate_stock_pdf_by_type,
    generate_unit_excel_all,           generate_unit_excel_by_unit,
    generate_unit_pdf_all,             generate_unit_pdf_by_unit,
    generate_trainingschool_excel_all, generate_trainingschool_excel_by_school,
    generate_trainingschool_pdf_all,   generate_trainingschool_pdf_by_school,
    generate_region_excel_all,         generate_region_excel_by_region,
    generate_region_pdf_all,           generate_region_pdf_by_region,
    generate_dpu_excel_all,            generate_dpu_excel_by_dpu,
    generate_dpu_pdf_all,              generate_dpu_pdf_by_dpu,
    get_equipment_types,
)


def _buf_to_b64(buf):
    """BytesIO → base64 string (JSON-serialisable for Celery result backend)."""
    return base64.b64encode(buf.read()).decode("utf-8")


CACHE_30M = 60 * 30
CACHE_15M = 60 * 15


def _cached_task(cache_key, generator_fn, timeout, *args, force=False):
    t0 = time.perf_counter()
    if not force:
        cached = cache.get(cache_key)
        if cached is not None:
            dt = time.perf_counter() - t0
            print(f"[report-cache] HIT {cache_key} ({dt:.3f}s)")
            return cached

    t1 = time.perf_counter()
    buf = generator_fn(*args)
    t2 = time.perf_counter()
    result = _buf_to_b64(buf)
    t3 = time.perf_counter()
    cache.set(cache_key, result, timeout=timeout)
    t4 = time.perf_counter()
    print(
        f"[report-cache] MISS {cache_key} "
        f"gen={(t2 - t1):.3f}s b64={(t3 - t2):.3f}s set={(t4 - t3):.3f}s total={(t4 - t0):.3f}s"
    )
    return result


# ── Equipment ─────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:xlsx:equipment:all", generate_excel_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_excel_by_type(self, equipment_type):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:xlsx:equipment:{equipment_type.lower()}"
        result = _cached_task(key, generate_excel_by_type, CACHE_30M, equipment_type)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:pdf:equipment:all", generate_pdf_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_pdf_by_type(self, equipment_type):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:pdf:equipment:{equipment_type.lower()}"
        result = _cached_task(key, generate_pdf_by_type, CACHE_30M, equipment_type)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Stock ─────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:xlsx:stock:all", generate_stock_excel_all, CACHE_15M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_excel_by_type(self, equipment_type):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:xlsx:stock:{equipment_type.lower()}"
        result = _cached_task(key, generate_stock_excel_by_type, CACHE_15M, equipment_type)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:pdf:stock:all", generate_stock_pdf_all, CACHE_15M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_pdf_by_type(self, equipment_type):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:pdf:stock:{equipment_type.lower()}"
        result = _cached_task(key, generate_stock_pdf_by_type, CACHE_15M, equipment_type)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Units ─────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:xlsx:unit:all", generate_unit_excel_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_excel_by_unit(self, unit_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:xlsx:unit:{unit_id}"
        result = _cached_task(key, generate_unit_excel_by_unit, CACHE_30M, unit_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:pdf:unit:all", generate_unit_pdf_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_pdf_by_unit(self, unit_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:pdf:unit:{unit_id}"
        result = _cached_task(key, generate_unit_pdf_by_unit, CACHE_30M, unit_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Training Schools ──────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_trainingschool_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:xlsx:trainingschool:all", generate_trainingschool_excel_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_trainingschool_excel_by_school(self, trainingschool_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:xlsx:trainingschool:{trainingschool_id}"
        result = _cached_task(key, generate_trainingschool_excel_by_school, CACHE_30M, trainingschool_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_trainingschool_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:pdf:trainingschool:all", generate_trainingschool_pdf_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_trainingschool_pdf_by_school(self, trainingschool_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:pdf:trainingschool:{trainingschool_id}"
        result = _cached_task(key, generate_trainingschool_pdf_by_school, CACHE_30M, trainingschool_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Regions ───────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:xlsx:region:all", generate_region_excel_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_excel_by_region(self, region_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:xlsx:region:{region_id}"
        result = _cached_task(key, generate_region_excel_by_region, CACHE_30M, region_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:pdf:region:all", generate_region_pdf_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_pdf_by_region(self, region_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:pdf:region:{region_id}"
        result = _cached_task(key, generate_region_pdf_by_region, CACHE_30M, region_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


# ── DPUs ──────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:xlsx:dpu:all", generate_dpu_excel_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_excel_by_dpu(self, dpu_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:xlsx:dpu:{dpu_id}"
        result = _cached_task(key, generate_dpu_excel_by_dpu, CACHE_30M, dpu_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        result = _cached_task("report:pdf:dpu:all", generate_dpu_pdf_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_pdf_by_dpu(self, dpu_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key = f"report:pdf:dpu:{dpu_id}"
        result = _cached_task(key, generate_dpu_pdf_by_dpu, CACHE_30M, dpu_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="prewarm")
def prewarm_equipment_reports(self):
    """
    Prewarm only the heavy, shared 'all' equipment reports.
    Per-type reports are generated on demand and then cached.
    """
    try:
        _cached_task("report:pdf:equipment:all", generate_pdf_all, CACHE_30M)
        _cached_task("report:xlsx:equipment:all", generate_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="prewarm")
def prewarm_stock_reports(self):
    """
    Prewarm only the global stock summaries; per-type stock reports are cached on demand.
    """
    try:
        _cached_task("report:pdf:stock:all", generate_stock_pdf_all, CACHE_15M)
        _cached_task("report:xlsx:stock:all", generate_stock_excel_all, CACHE_15M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="prewarm")
def prewarm_unit_reports(self):
    """
    Prewarm only the aggregated unit 'all' reports.
    Per-unit reports are generated and cached when a user requests them.
    """
    try:
        _cached_task("report:pdf:unit:all", generate_unit_pdf_all, CACHE_30M)
        _cached_task("report:xlsx:unit:all", generate_unit_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="prewarm")
def prewarm_region_reports(self):
    """
    Prewarm only the aggregated region 'all' reports.
    Per-region reports are generated and cached on demand.
    """
    try:
        _cached_task("report:pdf:region:all", generate_region_pdf_all, CACHE_30M)
        _cached_task("report:xlsx:region:all", generate_region_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="prewarm")
def prewarm_dpu_reports(self):
    """
    Prewarm only the aggregated DPU 'all' reports.
    Per-DPU reports are generated and cached on demand.
    """
    try:
        _cached_task("report:pdf:dpu:all", generate_dpu_pdf_all, CACHE_30M)
        _cached_task("report:xlsx:dpu:all", generate_dpu_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(queue="prewarm")
def prewarm_all_reports():
    prewarm_equipment_reports.delay()
    prewarm_stock_reports.delay()
    prewarm_unit_reports.delay()
    prewarm_region_reports.delay()
    prewarm_dpu_reports.delay()