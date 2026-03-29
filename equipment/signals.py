from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Deployment, Equipment, Stock


# ─── helpers ────────────────────────────────────────────────────────────────

def _invalidate_equipment_caches(instance):
    """Delete stale report cache keys then schedule background regeneration."""
    keys_to_delete = [
        "report:pdf:equipment:all",
        "report:xlsx:equipment:all",
        "report:pdf:unit:all",
        "report:xlsx:unit:all",
        "report:pdf:region:all",
        "report:xlsx:region:all",
        "report:pdf:dpu:all",
        "report:xlsx:dpu:all",
    ]

    type_name  = None
    unit_id    = instance.unit_id
    region_id  = instance.region_id
    dpu_id     = instance.dpu_id

    if instance.equipment_type:
        type_name = instance.equipment_type.name.lower()
        keys_to_delete += [
            f"report:pdf:equipment:{type_name}",
            f"report:xlsx:equipment:{type_name}",
        ]
    if unit_id:
        keys_to_delete += [f"report:pdf:unit:{unit_id}", f"report:xlsx:unit:{unit_id}"]
    if region_id:
        keys_to_delete += [f"report:pdf:region:{region_id}", f"report:xlsx:region:{region_id}"]
    if dpu_id:
        keys_to_delete += [f"report:pdf:dpu:{dpu_id}", f"report:xlsx:dpu:{dpu_id}"]

    cache.delete_many(keys_to_delete)

    # ── kick off background regeneration so the next download is instant ──
    _schedule_equipment_regen(type_name, unit_id, region_id, dpu_id)


def _invalidate_stock_caches(stock_instance):
    """Delete stale stock cache keys then schedule background regeneration."""
    keys = [
        "report:pdf:stock:all",
        "report:xlsx:stock:all",
    ]
    type_name = None
    equipment = getattr(stock_instance, "equipment", None)
    if equipment and equipment.equipment_type:
        type_name = equipment.equipment_type.name.lower()
        keys += [f"report:pdf:stock:{type_name}", f"report:xlsx:stock:{type_name}"]
    cache.delete_many(keys)
    _schedule_stock_regen(type_name)


def _schedule_equipment_regen(type_name, unit_id, region_id, dpu_id):
    """
    Queue background Celery tasks to rebuild only the invalidated reports.
    Import tasks here (not at module level) to avoid circular imports.
    countdown=5 gives Django a moment to finish the DB write before reading.
    """
    try:
        from .tasks import (
            task_excel_all, task_pdf_all,
            task_excel_by_type, task_pdf_by_type,
            task_unit_excel_all, task_unit_pdf_all,
            task_unit_excel_by_unit, task_unit_pdf_by_unit,
            task_region_excel_all, task_region_pdf_all,
            task_region_excel_by_region, task_region_pdf_by_region,
            task_dpu_excel_all, task_dpu_pdf_all,
            task_dpu_excel_by_dpu, task_dpu_pdf_by_dpu,
        )
        DELAY = 5  # seconds — let the DB commit settle first

        # Always regenerate the "all equipment" aggregates
        task_excel_all.apply_async(countdown=DELAY)
        task_pdf_all.apply_async(countdown=DELAY)

        # Per-type report (if this equipment has a type)
        if type_name:
            task_excel_by_type.apply_async(args=[type_name], countdown=DELAY)
            task_pdf_by_type.apply_async(args=[type_name], countdown=DELAY)

        # Per-location aggregates + specific sheets
        if unit_id:
            task_unit_excel_all.apply_async(countdown=DELAY)
            task_unit_pdf_all.apply_async(countdown=DELAY)
            task_unit_excel_by_unit.apply_async(args=[unit_id], countdown=DELAY)
            task_unit_pdf_by_unit.apply_async(args=[unit_id], countdown=DELAY)

        if region_id:
            task_region_excel_all.apply_async(countdown=DELAY)
            task_region_pdf_all.apply_async(countdown=DELAY)
            task_region_excel_by_region.apply_async(args=[region_id], countdown=DELAY)
            task_region_pdf_by_region.apply_async(args=[region_id], countdown=DELAY)

        if dpu_id:
            task_dpu_excel_all.apply_async(countdown=DELAY)
            task_dpu_pdf_all.apply_async(countdown=DELAY)
            task_dpu_excel_by_dpu.apply_async(args=[dpu_id], countdown=DELAY)
            task_dpu_pdf_by_dpu.apply_async(args=[dpu_id], countdown=DELAY)

    except Exception as e:
        # Never crash the request because of background scheduling
        print(f"[signals] background regen scheduling failed: {e}")


def _schedule_stock_regen(type_name):
    """Queue background tasks to rebuild invalidated stock reports."""
    try:
        from .tasks import (
            task_stock_excel_all, task_stock_pdf_all,
            task_stock_excel_by_type, task_stock_pdf_by_type,
        )
        DELAY = 5
        task_stock_excel_all.apply_async(countdown=DELAY)
        task_stock_pdf_all.apply_async(countdown=DELAY)
        if type_name:
            task_stock_excel_by_type.apply_async(args=[type_name], countdown=DELAY)
            task_stock_pdf_by_type.apply_async(args=[type_name], countdown=DELAY)
    except Exception as e:
        print(f"[signals] stock regen scheduling failed: {e}")


# ─── signal receivers ────────────────────────────────────────────────────────

@receiver(post_save, sender=Equipment)
def auto_classify_equipment(sender, instance, created, **kwargs):
    if created:
        if instance.registration_intent == Equipment.RegistrationIntent.STOCK:
            _create_stock(instance)
        elif instance.registration_intent == Equipment.RegistrationIntent.DEPLOYMENT:
            _create_deployment(instance)

    _invalidate_equipment_caches(instance)


@receiver(post_delete, sender=Equipment)
def invalidate_on_equipment_delete(sender, instance, **kwargs):
    _invalidate_equipment_caches(instance)


@receiver(post_save, sender=Stock)
def invalidate_on_stock_save(sender, instance, **kwargs):
    _invalidate_stock_caches(instance)


@receiver(post_delete, sender=Stock)
def invalidate_on_stock_delete(sender, instance, **kwargs):
    _invalidate_stock_caches(instance)


def _create_stock(equipment):
    Stock.objects.get_or_create(
        equipment=equipment,
        defaults={
            "condition": Stock.Condition.NEW,
            "date_added": timezone.now().date(),
            "added_by": equipment.created_by,
            "storage_location": None,
            "comments": f"Auto-added to stock on registration ({timezone.now().strftime('%d %b %Y')})",
        },
    )


def _resolve_recipient_label(equipment):
    candidates = [
        equipment.office,
        equipment.department,
        equipment.directorate,
        equipment.unit,
        equipment.station,
        equipment.dpu,
        equipment.region,
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return equipment.name


def _create_deployment(equipment):
    region_office = None
    if equipment.region_id and equipment.region.region_office_id:
        region_office = equipment.region.region_office

    dpu_office = None
    if equipment.dpu_id and equipment.dpu.dpu_office_id:
        dpu_office = equipment.dpu.dpu_office

    Deployment.objects.create(
        equipment=equipment,
        status=Deployment.DeploymentStatus.ACTIVE,
        issued_to_user=_resolve_recipient_label(equipment),
        issued_to_region_office=region_office,
        issued_to_region=equipment.region,
        issued_to_dpu_office=dpu_office,
        issued_to_dpu=equipment.dpu,
        issued_to_station=equipment.station,
        issued_to_unit=equipment.unit,
        issued_to_directorate=equipment.directorate,
        issued_to_department=equipment.department,
        issued_to_office=equipment.office,
        issued_date=equipment.deployment_date or timezone.now().date(),
        issued_by=equipment.created_by,
        comments=f"Auto-created on registration ({timezone.now().strftime('%d %b %Y')})",
    )