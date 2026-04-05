import glob
import os
import time
from datetime import datetime, timedelta

from celery import shared_task, group
from django.conf import settings
from django.core.cache import cache

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

# ── Config ────────────────────────────────────────────────────────────────────

REPORTS_DIR = os.path.join(settings.MEDIA_ROOT, "reports")
CACHE_30M   = 60 * 30
CACHE_15M   = 60 * 15


def _reports_dir() -> str:
    """Ensure the reports directory exists and return its path."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    return REPORTS_DIR


# ── Task deduplication ────────────────────────────────────────────────────────

def _acquire_task_lock(name: str, ttl: int = 600) -> bool:
    """Try to acquire a Redis dedup lock. Returns True if acquired."""
    return cache.add(f"tasklock:{name}", "1", timeout=ttl)


def _release_task_lock(name: str):
    """Release a dedup lock."""
    cache.delete(f"tasklock:{name}")


# ── Core helper ───────────────────────────────────────────────────────────────

def _cached_task(cache_key: str, generator_fn, timeout: int, *args, force: bool = False) -> str:
    """
    Check Redis cache for an existing report file path.
    If cached AND file still exists on disk → return cached path immediately.
    Otherwise → generate the report, write it to disk, cache the path, return it.

    Args:
        cache_key:    Redis key, e.g. "report:xlsx:equipment:all"
        generator_fn: Report function from reports.py
        timeout:      Cache TTL in seconds
        *args:        Extra positional args forwarded to generator_fn
        force:        If True, bypass cache and regenerate

    Returns:
        Absolute file path of the report on disk (str).
    """
    t0 = time.perf_counter()

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if not force:
        cached_path = cache.get(cache_key)
        if cached_path and os.path.exists(cached_path):
            print(
                f"[report-cache] HIT  {cache_key} "
                f"({time.perf_counter() - t0:.3f}s) → {cached_path}"
            )
            return cached_path

        # Stale cache entry — file was deleted (e.g. by cleanup task)
        if cached_path:
            cache.delete(cache_key)

    # ── Cache miss — generate to disk ─────────────────────────────────────────
    # Stable filename derived from cache key — same report always overwrites
    # the previous version instead of accumulating files.
    suffix   = ".xlsx" if "xlsx" in cache_key else ".pdf"
    filename = cache_key.replace(":", "_").replace("/", "_") + suffix
    out_path = os.path.join(_reports_dir(), filename)

    t1 = time.perf_counter()

    generator_fn(*args, output_path=out_path)

    t2 = time.perf_counter()

    cache.set(cache_key, out_path, timeout=timeout)

    print(
        f"[report-cache] MISS {cache_key} "
        f"gen={(t2 - t1):.3f}s total={(t2 - t0):.3f}s → {out_path}"
    )
    return out_path


# ── Equipment tasks ───────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task("report:xlsx:equipment:all", generate_excel_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_excel_by_type(self, equipment_type):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:xlsx:equipment:{equipment_type.lower()}"
        path = _cached_task(key, generate_excel_by_type, CACHE_30M, equipment_type)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task("report:pdf:equipment:all", generate_pdf_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_pdf_by_type(self, equipment_type):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:pdf:equipment:{equipment_type.lower()}"
        path = _cached_task(key, generate_pdf_by_type, CACHE_30M, equipment_type)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Stock tasks ───────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task("report:xlsx:stock:all", generate_stock_excel_all, CACHE_15M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_excel_by_type(self, equipment_type):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:xlsx:stock:{equipment_type.lower()}"
        path = _cached_task(key, generate_stock_excel_by_type, CACHE_15M, equipment_type)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task("report:pdf:stock:all", generate_stock_pdf_all, CACHE_15M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_stock_pdf_by_type(self, equipment_type):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:pdf:stock:{equipment_type.lower()}"
        path = _cached_task(key, generate_stock_pdf_by_type, CACHE_15M, equipment_type)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Unit tasks ────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task("report:xlsx:unit:all", generate_unit_excel_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_excel_by_unit(self, unit_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:xlsx:unit:{unit_id}"
        path = _cached_task(key, generate_unit_excel_by_unit, CACHE_30M, unit_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task("report:pdf:unit:all", generate_unit_pdf_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_unit_pdf_by_unit(self, unit_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:pdf:unit:{unit_id}"
        path = _cached_task(key, generate_unit_pdf_by_unit, CACHE_30M, unit_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Training School tasks ─────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_trainingschool_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task(
            "report:xlsx:trainingschool:all", generate_trainingschool_excel_all, CACHE_30M
        )
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_trainingschool_excel_by_school(self, trainingschool_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:xlsx:trainingschool:{trainingschool_id}"
        path = _cached_task(
            key, generate_trainingschool_excel_by_school, CACHE_30M, trainingschool_id
        )
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_trainingschool_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task(
            "report:pdf:trainingschool:all", generate_trainingschool_pdf_all, CACHE_30M
        )
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_trainingschool_pdf_by_school(self, trainingschool_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:pdf:trainingschool:{trainingschool_id}"
        path = _cached_task(
            key, generate_trainingschool_pdf_by_school, CACHE_30M, trainingschool_id
        )
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Region tasks ──────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task("report:xlsx:region:all", generate_region_excel_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_excel_by_region(self, region_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:xlsx:region:{region_id}"
        path = _cached_task(key, generate_region_excel_by_region, CACHE_30M, region_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task("report:pdf:region:all", generate_region_pdf_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_region_pdf_by_region(self, region_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:pdf:region:{region_id}"
        path = _cached_task(key, generate_region_pdf_by_region, CACHE_30M, region_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


# ── DPU tasks ─────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_excel_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task("report:xlsx:dpu:all", generate_dpu_excel_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_excel_by_dpu(self, dpu_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:xlsx:dpu:{dpu_id}"
        path = _cached_task(key, generate_dpu_excel_by_dpu, CACHE_30M, dpu_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_pdf_all(self):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        path = _cached_task("report:pdf:dpu:all", generate_dpu_pdf_all, CACHE_30M)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def task_dpu_pdf_by_dpu(self, dpu_id):
    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})
        key  = f"report:pdf:dpu:{dpu_id}"
        path = _cached_task(key, generate_dpu_pdf_by_dpu, CACHE_30M, dpu_id)
        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100})
        return path
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Pre-warm tasks ────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="prewarm")
def prewarm_equipment_reports(self):
    """Pre-warm the heavy 'all equipment' reports. Per-type cached on demand."""
    if not _acquire_task_lock("prewarm_equipment", ttl=900):
        return
    try:
        _cached_task("report:pdf:equipment:all",  generate_pdf_all,   CACHE_30M)
        _cached_task("report:xlsx:equipment:all", generate_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        _release_task_lock("prewarm_equipment")


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="prewarm")
def prewarm_stock_reports(self):
    """Pre-warm global stock summaries; per-type stock cached on demand."""
    if not _acquire_task_lock("prewarm_stock", ttl=900):
        return
    try:
        _cached_task("report:pdf:stock:all",  generate_stock_pdf_all,   CACHE_15M)
        _cached_task("report:xlsx:stock:all", generate_stock_excel_all, CACHE_15M)
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        _release_task_lock("prewarm_stock")


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="prewarm")
def prewarm_unit_reports(self):
    """Pre-warm aggregated unit 'all' reports."""
    if not _acquire_task_lock("prewarm_unit", ttl=900):
        return
    try:
        _cached_task("report:pdf:unit:all",  generate_unit_pdf_all,   CACHE_30M)
        _cached_task("report:xlsx:unit:all", generate_unit_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        _release_task_lock("prewarm_unit")


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="prewarm")
def prewarm_region_reports(self):
    """Pre-warm aggregated region 'all' reports."""
    if not _acquire_task_lock("prewarm_region", ttl=900):
        return
    try:
        _cached_task("report:pdf:region:all",  generate_region_pdf_all,   CACHE_30M)
        _cached_task("report:xlsx:region:all", generate_region_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        _release_task_lock("prewarm_region")


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="prewarm")
def prewarm_dpu_reports(self):
    """Pre-warm aggregated DPU 'all' reports."""
    if not _acquire_task_lock("prewarm_dpu", ttl=900):
        return
    try:
        _cached_task("report:pdf:dpu:all",  generate_dpu_pdf_all,   CACHE_30M)
        _cached_task("report:xlsx:dpu:all", generate_dpu_excel_all, CACHE_30M)
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        _release_task_lock("prewarm_dpu")


@shared_task(queue="prewarm")
def prewarm_all_reports():
    """Dispatch all pre-warm sub-tasks in parallel via Celery group."""
    if not _acquire_task_lock("prewarm_all", ttl=120):
        return
    try:
        group(
            prewarm_equipment_reports.si(),
            prewarm_stock_reports.si(),
            prewarm_unit_reports.si(),
            prewarm_region_reports.si(),
            prewarm_dpu_reports.si(),
        ).apply_async()
    finally:
        _release_task_lock("prewarm_all")


# ── Cleanup task ──────────────────────────────────────────────────────────────

@shared_task(queue="prewarm")
def cleanup_old_reports():
    """
    Delete report files older than 24 hours from MEDIA_ROOT/reports/.
    Scheduled daily at 3 AM UTC via CELERY_BEAT_SCHEDULE in settings.py.

    _cached_task() already handles stale Redis entries at read time
    (checks os.path.exists and clears the key), so no extra cache
    invalidation is needed here.
    """
    if not os.path.exists(REPORTS_DIR):
        return

    cutoff  = datetime.now() - timedelta(hours=24)
    deleted = 0

    for filepath in glob.glob(os.path.join(REPORTS_DIR, "*")):
        try:
            if os.path.getmtime(filepath) < cutoff.timestamp():
                os.unlink(filepath)
                deleted += 1
        except Exception as e:
            print(f"[cleanup] Could not delete {filepath}: {e}")

    print(f"[cleanup] Deleted {deleted} old report file(s) from {REPORTS_DIR}")


# ── Report counts pre-computation ─────────────────────────────────────────────

@shared_task(queue="prewarm")
def refresh_report_counts(ignore_lock=False):
    if not ignore_lock and not _acquire_task_lock("refresh_report_counts", ttl=300):
        print("[refresh_report_counts] Task already locked, skipping.")
        return

    try:
        from django.db import connection

        CACHE_KEY = "report_counts_summary"
        CACHE_TTL = 60 * 15

        t0 = time.perf_counter()

        with connection.cursor() as cur:

            # ── Combined simple counts (1 round-trip instead of 6) ────────
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM equipment)                          AS total_eq,
                    (SELECT COUNT(*) FROM stock)                              AS total_stock,
                    (SELECT COUNT(*) FROM deployment)                         AS total_dep,
                    (SELECT COUNT(*) FROM deployment WHERE status = 'Active') AS active_dep,
                    (SELECT COUNT(*) FROM lending)                            AS total_lend,
                    (SELECT COUNT(*) FROM lending   WHERE status = 'Active')  AS active_lend
            """)
            (total_equipment, total_stock, total_deployments,
             active_deployments, total_lendings, active_lendings) = cur.fetchone()

            # ── Unassigned (LEFT JOIN instead of double NOT EXISTS) ───────
            cur.execute("""
                SELECT COUNT(*)
                FROM equipment e
                LEFT JOIN stock s      ON s.equipment_id = e.id
                LEFT JOIN deployment d ON d.equipment_id = e.id
                                      AND d.status = 'Active'
                WHERE s.equipment_id IS NULL
                  AND d.equipment_id IS NULL
            """)
            unassigned = cur.fetchone()[0]

            # ── Breakdowns ────────────────────────────────────────────────
            cur.execute("""
                SELECT cat.name, COUNT(e.id)
                FROM equipment e
                JOIN equipment_category cat ON cat.id = e.equipment_type_id
                GROUP BY cat.name ORDER BY cat.name
            """)
            equipment_counts = {row[0]: row[1] for row in cur.fetchall()}

            cur.execute("""
                SELECT cat.name, COUNT(s.id)
                FROM stock s
                JOIN equipment e ON e.id = s.equipment_id
                JOIN equipment_category cat ON cat.id = e.equipment_type_id
                GROUP BY cat.name ORDER BY cat.name
            """)
            stock_counts = {row[0]: row[1] for row in cur.fetchall()}

            cur.execute("""
                SELECT r.id::text, r.name, COUNT(e.id)
                FROM equipment_region r
                LEFT JOIN equipment e ON e.region_id = r.id
                GROUP BY r.id, r.name ORDER BY r.name
            """)
            region_counts = {
                row[0]: {"name": row[1], "count": row[2]}
                for row in cur.fetchall()
            }

            cur.execute("""
                SELECT d.id::text, d.name, COUNT(e.id)
                FROM equipment_dpu d
                LEFT JOIN equipment e ON e.dpu_id = d.id
                GROUP BY d.id, d.name ORDER BY d.name
            """)
            dpu_counts = {
                row[0]: {"name": row[1], "count": row[2]}
                for row in cur.fetchall()
            }

            cur.execute("""
                SELECT u.id::text, u.name, COUNT(e.id)
                FROM equipment_unit u
                LEFT JOIN equipment e ON e.unit_id = u.id
                GROUP BY u.id, u.name ORDER BY u.name
            """)
            unit_counts = {
                row[0]: {"name": row[1], "count": row[2]}
                for row in cur.fetchall()
            }

        payload = {
            "totals": {
                "equipment":          total_equipment,
                "stock":              total_stock,
                "deployments":        total_deployments,
                "active_deployments": active_deployments,
                "lendings":           total_lendings,
                "active_lendings":    active_lendings,
                "unassigned":         unassigned,
            },
            "equipment_counts": equipment_counts,
            "stock_counts":     stock_counts,
            "region_counts":    region_counts,
            "dpu_counts":       dpu_counts,
            "unit_counts":      unit_counts,
        }

        cache.set(CACHE_KEY, payload, CACHE_TTL)
        elapsed = time.perf_counter() - t0
        print(
            f"[refresh_report_counts] Done in {elapsed:.1f}s. "
            f"equipment={total_equipment:,} stock={total_stock:,}"
        )
        return payload
    finally:
        _release_task_lock("refresh_report_counts")


# ── Deferred regeneration (called by signals) ────────────────────────────────

@shared_task(queue="prewarm")
def deferred_regen_all():
    """
    Single debounced task triggered by signals.
    Replaces the 18-task storm with one coalesced regeneration.
    """
    prewarm_all_reports.delay()
    refresh_report_counts.delay()