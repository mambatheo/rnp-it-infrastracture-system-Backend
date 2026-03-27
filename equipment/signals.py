from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Deployment, Equipment, Stock


def _invalidate_equipment_caches(instance):
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

    if instance.equipment_type:
        type_name = instance.equipment_type.name.lower()
        keys_to_delete += [
            f"report:pdf:equipment:{type_name}",
            f"report:xlsx:equipment:{type_name}",
        ]
    if instance.unit_id:
        keys_to_delete += [f"report:pdf:unit:{instance.unit_id}", f"report:xlsx:unit:{instance.unit_id}"]
    if instance.region_id:
        keys_to_delete += [f"report:pdf:region:{instance.region_id}", f"report:xlsx:region:{instance.region_id}"]
    if instance.dpu_id:
        keys_to_delete += [f"report:pdf:dpu:{instance.dpu_id}", f"report:xlsx:dpu:{instance.dpu_id}"]

    cache.delete_many(keys_to_delete)


def _invalidate_stock_caches(stock_instance):
    keys = [
        "report:pdf:stock:all",
        "report:xlsx:stock:all",
    ]
    equipment = getattr(stock_instance, "equipment", None)
    if equipment and equipment.equipment_type:
        type_name = equipment.equipment_type.name.lower()
        keys += [f"report:pdf:stock:{type_name}", f"report:xlsx:stock:{type_name}"]
    cache.delete_many(keys)


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