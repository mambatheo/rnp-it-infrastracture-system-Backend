import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class RegionOffice(models.Model):
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    class Meta:
        ordering    = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="unique_regionoffice_name")
        ]

    def __str__(self):
        return self.name


class Region(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name          = models.CharField(max_length=100)
    region_office = models.ForeignKey(
        RegionOffice, on_delete=models.PROTECT,
        blank=True, null=True, related_name="regionhq_office"
    )

    class Meta:
        ordering    = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="unique_region_name")
        ]

    def __str__(self):
        return self.name


class DPUOffice(models.Model):
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  
    name = models.CharField(max_length=100)

    class Meta:
        ordering    = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="unique_dpuoffice_name")
        ]

    def __str__(self):
        return self.name


class DPU(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=100)
    dpu_office = models.ForeignKey(
        DPUOffice, on_delete=models.PROTECT,
        blank=True, null=True, related_name="dpuhq_office"
    )
    region     = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="dpus")

    class Meta:
        ordering    = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "region"], name="unique_dpu_per_region")
        ]

    def __str__(self):
        return f"{self.name} ({self.region})"


class Station(models.Model):
    id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    dpu  = models.ForeignKey(DPU, on_delete=models.PROTECT, related_name="stations")

    class Meta:
        ordering    = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "dpu"], name="unique_station_per_dpu")
        ]

    def __str__(self):
        return f"{self.name} ({self.dpu})"


class Unit(models.Model):
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    class Meta:
        ordering    = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="unique_unit_name")
        ]

    def __str__(self):
        return self.name


class Directorate(models.Model):
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT,
        null=True, blank=True, related_name="directorates"
    )

    class Meta:
        ordering    = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "unit"],
                name="unique_directorate_per_unit",
                condition=models.Q(unit__isnull=False)
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.unit})" if self.unit else self.name


class Department(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=100)
    directorate = models.ForeignKey(
        Directorate, on_delete=models.PROTECT,
        null=True, blank=True, related_name="departments"
    )

    class Meta:
        ordering    = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "directorate"],
                name="unique_department_per_directorate",
                condition=models.Q(directorate__isnull=False)
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.directorate})" if self.directorate else self.name


class Office(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT,
        null=True, blank=True, related_name="offices"
    )
    region     = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="offices")
    dpu        = models.ForeignKey(DPU,    on_delete=models.PROTECT, related_name="offices")

    class Meta:
        ordering    = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "department"],
                name="unique_office_per_department",
                condition=models.Q(department__isnull=False)
            )
        ]

    def clean(self):
        if self.dpu_id and self.region_id:
            if self.dpu.region_id != self.region_id:
                raise ValidationError({
                    "dpu": "The selected DPU does not belong to the selected Region."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.department})" if self.department else self.name


# ─────────────────────────────────────────
# EQUIPMENT CLASSIFICATION
# ─────────────────────────────────────────

class EquipmentCategory(models.Model):
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering         = ["name"]
        db_table         = "equipment_category"
        verbose_name     = _("Equipment Category")
        verbose_name_plural = _("Equipment Categories")

    def __str__(self):
        return self.name


class Brand(models.Model):
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name     = models.CharField(max_length=100)
    category = models.ForeignKey(
        EquipmentCategory, on_delete=models.PROTECT, related_name="brands"
    )

    class Meta:
        ordering    = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "category"], name="unique_brand_per_category"
            )
        ]

    def __str__(self):
        return self.name


class EquipmentStatus(models.Model):
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering  = ["name"]
        db_table  = "equipment_status"
        verbose_name = _("Equipment Status")
        verbose_name_plural = _("Equipment Statuses")

    def __str__(self):
        return self.name


# ─────────────────────────────────────────
# MAIN EQUIPMENT TABLE
# ─────────────────────────────────────────

class Equipment(models.Model):

    

    class RegistrationIntent(models.TextChoices):
        STOCK      = "Stock",      _("Add to Stock (keep in IT store)")
        DEPLOYMENT = "Deployment", _("Deploy Immediately (issue to a unit/person)")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name  = models.CharField(max_length=100)
    equipment_type  = models.ForeignKey(EquipmentCategory, on_delete=models.PROTECT, related_name="equipment_types")
    registration_intent = models.CharField(
        max_length=20,
        choices=RegistrationIntent.choices,
        default=RegistrationIntent.STOCK,
        help_text=(
            "Stock → item is added to the IT store immediately. "
            "Deployment → item is issued to a location/person immediately."
        )
    )

    # ── Location ──────────────────────────────────────────────────────────────

    region      = models.ForeignKey(Region,      on_delete=models.PROTECT, null=True, blank=True, related_name="equipment")
    dpu         = models.ForeignKey(DPU,         on_delete=models.PROTECT, null=True, blank=True, related_name="equipment")
    station     = models.ForeignKey(Station,     on_delete=models.PROTECT, null=True, blank=True, related_name="equipment")
    unit        = models.ForeignKey(Unit,        on_delete=models.PROTECT, null=True, blank=True, related_name="equipment")
    directorate = models.ForeignKey(Directorate, on_delete=models.PROTECT, null=True, blank=True, related_name="equipment")
    department  = models.ForeignKey(Department,  on_delete=models.PROTECT, null=True, blank=True, related_name="equipment")
    office      = models.ForeignKey(Office,      on_delete=models.PROTECT, null=True, blank=True, related_name="equipment")

    # ── Classification ────────────────────────────────────────────────────────

    brand  = models.ForeignKey(Brand,          on_delete=models.PROTECT, null=True, blank=True, related_name="equipment")
    model  = models.CharField(max_length=50,   blank=True, null=True)
    status = models.ForeignKey(EquipmentStatus, on_delete=models.PROTECT, related_name="equipment")

    # ── Identifiers ───────────────────────────────────────────────────────────

    serial_number = models.CharField(
        max_length=50, unique=True, blank=True, null=True,
        validators=[MinLengthValidator(5), MaxLengthValidator(50)]
    )
    marking_code = models.CharField(max_length=50, unique=True, blank=True, null=True)

    # ── Dates ─────────────────────────────────────────────────────────────────

    deployment_date     = models.DateField(blank=True, null=True)  
    warranty_expiration = models.DateField(blank=True, null=True)

    # ── Computer Specs ────────────────────────────────────────────────────────

    CPU              = models.CharField(max_length=50,  blank=True, null=True)
    ram_size         = models.CharField(max_length=10,  blank=True, null=True)
    storage_size     = models.CharField(max_length=10,  blank=True, null=True)
    GPU              = models.CharField(max_length=50,  blank=True, null=True)
    operating_system = models.CharField(max_length=50,  blank=True, null=True)

    # ── Server Specs ──────────────────────────────────────────────────────────

    ram_slots     = models.IntegerField(blank=True, null=True)
    storage_slots = models.IntegerField(blank=True, null=True)
    storage_type  = models.CharField(max_length=100, blank=True, null=True)

    # ── Display ───────────────────────────────────────────────────────────────

    screen_size = models.CharField(max_length=100, blank=True, null=True)

    # ── Device Types ──────────────────────────────────────────────────────────

    printer_type    = models.CharField(max_length=100, blank=True, null=True)
    network_type    = models.CharField(max_length=100, blank=True, null=True)
    telephone_type  = models.CharField(max_length=100, blank=True, null=True)
    exstorage_type  = models.CharField(max_length=100, blank=True, null=True)
    peripheral_type = models.CharField(max_length=100, blank=True, null=True)
    ups             = models.CharField(max_length=100, blank=True, null=True)

    # ── IT Officer's Observation ──────────────────────────────────────────────

    comments = models.TextField(blank=True, null=True)

    # ── Audit ─────────────────────────────────────────────────────────────────

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,         
        related_name="created_equipment",null=True
    )
    updated_by =  models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,        
        related_name="updated_equipment", null=True
    )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def age_since_deployed(self):
        
        if not self.deployment_date:
            return None
        total_days = (timezone.now().date() - self.deployment_date).days
        years, remainder = divmod(total_days, 365)
        months, days    = divmod(remainder, 30)
        parts = []
        if years:  parts.append(f"{years}y")
        if months: parts.append(f"{months}m")
        if days or not parts: parts.append(f"{days}d")
        return " ".join(parts)

    @property
    def is_in_stock(self):
        
        return hasattr(self, "stock")

    # ── Validation ────────────────────────────────────────────────────────────

    def clean(self):
        errors = {}

        # Location hierarchy
        if self.dpu_id and self.region_id:
            if self.dpu.region_id != self.region_id:
                errors["dpu"] = "The selected DPU does not belong to the selected Region."

        if self.station_id and self.dpu_id:
            if self.station.dpu_id != self.dpu_id:
                errors["station"] = "The selected Station does not belong to the selected DPU."

        if self.directorate_id and self.unit_id:
            if self.directorate.unit_id != self.unit_id:
                errors["directorate"] = "The selected Directorate does not belong to the selected Unit."

        if self.department_id and self.directorate_id:
            if self.department.directorate_id != self.directorate_id:
                errors["department"] = "The selected Department does not belong to the selected Directorate."

        if self.office_id:
            office_errors = []
            if self.department_id and self.office.department_id != self.department_id:
                office_errors.append("Office does not belong to the selected Department.")
            if self.dpu_id and self.office.dpu_id != self.dpu_id:
                office_errors.append("Office does not belong to the selected DPU.")
            if self.region_id and self.office.region_id != self.region_id:
                office_errors.append("Office does not belong to the selected Region.")
            if office_errors:
                errors["office"] = " | ".join(office_errors)

        # Date logic
        if self.returned_date and not self.deployment_date:
            errors["deployment_date"] = "Return date requires a deployment date."

        if self.returned_date and self.deployment_date:
            if self.returned_date < self.deployment_date:
                errors["returned_date"] = "Return date cannot be before deployment date."

        # Deployment intent requires at least one location field
        if self.registration_intent == self.RegistrationIntent.DEPLOYMENT:
            location_fields = [
                self.region_id, self.dpu_id, self.station_id,
                self.unit_id, self.directorate_id, self.department_id, self.office_id,
            ]
            if not any(location_fields):
                errors["registration_intent"] = (
                    "Deployment intent requires at least one location field "
                    "(Region, DPU, Station, Unit, Directorate, Department, or Office)."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        db_table         = "equipment"
        ordering         = ["-created_at"]
        verbose_name     = _("Equipment")
        verbose_name_plural = _("Equipment")

    def __str__(self):
        parts = [self.name]
        if self.brand: parts.append(str(self.brand))
        if self.model: parts.append(self.model)
        return " | ".join(parts)


# ─────────────────────────────────────────
# STOCK
# ─────────────────────────────────────────

class Stock(models.Model):
  

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment        = models.OneToOneField(Equipment, on_delete=models.PROTECT, related_name="stock")
    storage_location = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Logistics or IT Tech Support."
    )
    
    date_added       = models.DateField(default=timezone.now, help_text="Date this item was placed into stock.")
    comments         = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="stock_additions"
    )

    class Meta:
        db_table         = "stock"
        ordering         = ["-date_added"]
        verbose_name     = _("Stock Item")
        verbose_name_plural = _("Stock Items")

    def __str__(self):
        return f"[STOCK] {self.equipment} — {self.condition}"


# ─────────────────────────────────────────
# DEPLOYMENT (Permanent assignment to a location/person)
# ─────────────────────────────────────────

class Deployment(models.Model):

    class DeploymentStatus(models.TextChoices):
        ACTIVE = "Active", _("Active — currently deployed")

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="deployments")
    status    = models.CharField(
        max_length=10, choices=DeploymentStatus.choices, default=DeploymentStatus.ACTIVE
    )

    # ── Recipients ────────────────────────────────────────────────────────────

    issued_to_user         = models.CharField(max_length=100, null=True, blank=True, help_text="Individual who received the equipment.")
    issued_to_region_office = models.ForeignKey(RegionOffice, on_delete=models.PROTECT, null=True, blank=True, related_name="deployments")
    issued_to_region       = models.ForeignKey(Region,       on_delete=models.PROTECT, null=True, blank=True, related_name="deployments")
    issued_to_dpu_office   = models.ForeignKey(DPUOffice,    on_delete=models.PROTECT, null=True, blank=True, related_name="deployments")
    issued_to_dpu          = models.ForeignKey(DPU,          on_delete=models.PROTECT, null=True, blank=True, related_name="deployments")
    issued_to_station      = models.ForeignKey(Station,      on_delete=models.PROTECT, null=True, blank=True, related_name="deployments")
    issued_to_unit         = models.ForeignKey(Unit,         on_delete=models.PROTECT, null=True, blank=True, related_name="deployments")
    issued_to_directorate  = models.ForeignKey(Directorate,  on_delete=models.PROTECT, null=True, blank=True, related_name="deployments")
    issued_to_department   = models.ForeignKey(Department,   on_delete=models.PROTECT, null=True, blank=True, related_name="deployments")
    issued_to_office       = models.ForeignKey(Office,       on_delete=models.PROTECT, null=True, blank=True, related_name="deployments")

    # ── Dates ──────────────────────────────────────────────────────────────────

    issued_date = models.DateField(default=timezone.now)
    comments    = models.TextField(blank=True, null=True)

    # ── Audit ──────────────────────────────────────────────────────────────────

    issued_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="issued_deployments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
   
   

    # ── Validation ────────────────────────────────────────────────────────────

    def clean(self):
        errors = {}

        # At least one recipient required
        recipient_fields = [
            self.issued_to_user,
            self.issued_to_office_id,
            self.issued_to_unit_id,
            self.issued_to_department_id,
            self.issued_to_directorate_id,
            self.issued_to_dpu_id,
            self.issued_to_region_id,
            self.issued_to_station_id,
            self.issued_to_region_office_id,
            self.issued_to_dpu_office_id,
        ]
        if not any(recipient_fields):
            errors["issued_to_user"] = (
                "Set at least one recipient: person name, office, unit, department, "
                "directorate, DPU, region, or station."
            )

        if errors:
            raise ValidationError(errors)

    # ── Stock lifecycle (auto-managed) ────────────────────────────────────────

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = self._state.adding

        if is_new:
            # Item leaves stock → remove Stock record
            Stock.objects.filter(equipment=self.equipment).delete()

        super().save(*args, **kwargs)

       

    class Meta:
        db_table         = "deployment"
        ordering         = ["-issued_date"]
        verbose_name     = _("Deployment")
        verbose_name_plural = _("Deployments")

    def __str__(self):
        if self.issued_to_user:
            recipient = self.issued_to_user
        elif self.issued_to_office_id:
            recipient = str(self.issued_to_office)
        elif self.issued_to_unit_id:
            recipient = str(self.issued_to_unit)
        else:
            recipient = "Unknown"
        return f"{self.equipment} → {recipient} ({self.issued_date})"


# ─────────────────────────────────────────
# LENDING (Temporary loan with return tracking)
# ─────────────────────────────────────────

class Lending(models.Model):
    class Condition(models.TextChoices):
        NEW          = "New",          _("New")
        GOOD         = "Good",         _("Good")
        FAIR         = "Fair",         _("Fair")
        POOR         = "Poor",         _("Poor")
        DAMAGED      = "Damaged",      _("Damaged")
        UNDER_REPAIR = "Under Repair", _("Under Repair")

    class LendingStatus(models.TextChoices):
        ACTIVE   = "Active",   _("Active — currently out")
        RETURNED = "Returned", _("Returned to stock")

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="lendings")
    status    = models.CharField(max_length=10, choices=LendingStatus.choices, default=LendingStatus.ACTIVE)
    

    # ── Borrower Info ─────────────────────────────────────────────────────────

    borrower_name = models.CharField(max_length=100, help_text="Person borrowing the equipment.")
    
    
    # ── Special Units ────────────────────────────────────────────────────────
 
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, blank=True, null=True, related_name="unit_borrower")
     
    # ── Territorial Units ─────────────────────────────────────────────────────────
    
    region = models.ForeignKey(Region, on_delete=models.PROTECT, blank=True, null=True, related_name="region_borrower")
    dpu = models.ForeignKey(DPU, on_delete=models.PROTECT, blank=True, null=True, related_name="dpu_borrower")
    station = models.ForeignKey(Station, on_delete=models.PROTECT, blank=True, null=True, related_name="station_borrower")
    
    phone_number  = models.CharField(max_length=20, help_text="Borrower's phone number")
    purpose  = models.TextField(help_text="Reason for borrowing.") 

    # ── Dates ──────────────────────────────────────────────────────────────────

    issued_date   = models.DateField(default=timezone.now)
    returned_date = models.DateField(blank=True, null=True)

    # ── Return Details ───────────────────────────────────────────────────────

    returned_by         = models.CharField(max_length=100, blank=True, null=True)
   
    condition_on_return        = models.CharField(
        max_length=100, choices=Condition.choices, default=Condition.GOOD
    )
    return_comments = models.TextField(blank=True, null=True)

    # ── Audit ──────────────────────────────────────────────────────────────────

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="issued_lendings"
    )
    return_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="confirmed_lending_returns"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Validation ────────────────────────────────────────────────────────────

    def clean(self):
        errors = {}

        if self.returned_date and self.returned_date < self.issued_date:
            errors["returned_date"] = "Return date cannot be before the issue date."

        if self.status == self.LendingStatus.RETURNED and not self.returned_date:
            errors["returned_date"] = "A return date is required when status is 'Returned'."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = self._state.adding

        if is_new:
            # Item leaves stock → remove Stock record
            Stock.objects.filter(equipment=self.equipment).delete()

        super().save(*args, **kwargs)

        # Item returned → recreate Stock record
        if self.status == self.LendingStatus.RETURNED and self.returned_date:
            Stock.objects.get_or_create(
                equipment=self.equipment,
                defaults={
                    "date_added": self.returned_date,
                    "condition":  self.condition_on_return or self.Condition.GOOD,
                    "added_by":   self.return_confirmed_by,
                    "comments":   f"Returned from lending {self.pk}",
                }
            )

    class Meta:
        db_table            = "lending"
        ordering            = ["-issued_date"]
        verbose_name        = _("Lending")
        verbose_name_plural = _("Lendings")

    def __str__(self):
        return f"{self.equipment} → {self.borrower_name} ({self.issued_date})"