
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Equipment, Stock, Deployment


@receiver(post_save, sender=Equipment)
def auto_classify_equipment(sender, instance, created, **kwargs):
   
    if not created:
        return

    if instance.registration_intent == Equipment.RegistrationIntent.STOCK:
        _create_stock(instance)

    elif instance.registration_intent == Equipment.RegistrationIntent.DEPLOYMENT:
        _create_deployment(instance)




def _create_stock(equipment):
    
    Stock.objects.get_or_create(
        equipment=equipment,
        defaults={
            "condition":        Stock.Condition.NEW,
            "date_added":       timezone.now().date(),
            "added_by":         equipment.created_by,
            "storage_location": None,
            "comments": (
                f"Auto-added to stock on registration "
                f"({timezone.now().strftime('%d %b %Y')})"
            ),
        }
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
    return equipment.name   # last resort


def _create_deployment(equipment):
   
    region_office = None
    if equipment.region_id and equipment.region.region_office_id:
        region_office = equipment.region.region_office

    dpu_office = None
    if equipment.dpu_id and equipment.dpu.dpu_office_id:
        dpu_office = equipment.dpu.dpu_office

    Deployment.objects.create(
        equipment             = equipment,
        status                = Deployment.DeploymentStatus.ACTIVE,

        # Recipient — text label resolved from location fields
        issued_to_user        = _resolve_recipient_label(equipment),

        # Mirror all location FKs from the Equipment record
        issued_to_region_office = region_office,
        issued_to_region        = equipment.region,
        issued_to_dpu_office    = dpu_office,
        issued_to_dpu           = equipment.dpu,
        issued_to_station       = equipment.station,
        issued_to_unit          = equipment.unit,
        issued_to_directorate   = equipment.directorate,
        issued_to_department    = equipment.department,
        issued_to_office        = equipment.office,

        # Dates
        issued_date             = equipment.deployment_date or timezone.now().date(),

        # Audit — the IT officer who registered the equipment
        issued_by               = equipment.created_by,

        comments = (
            f"Auto-created on registration "
            f"({timezone.now().strftime('%d %b %Y')})"
        ),
    )