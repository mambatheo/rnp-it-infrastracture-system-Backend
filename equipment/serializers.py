from rest_framework import serializers

from .models import (
    RegionOffice, Region, DPUOffice, DPU, Station,
    Unit, Directorate, Department, Office,
    EquipmentCategory, EquipmentStatus, Brand,
    Equipment, Stock, Deployment,
)




class RegionOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RegionOffice
        fields = ["id", "name"]


class RegionSerializer(serializers.ModelSerializer):
    region_office_name = serializers.CharField(source="region_office.name", read_only=True)

    class Meta:
        model  = Region
        fields = ["id", "name", "region_office", "region_office_name"]


class DPUOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DPUOffice
        fields = ["id", "name"]


class DPUSerializer(serializers.ModelSerializer):
    region_name     = serializers.CharField(source="region.name",     read_only=True)
    dpu_office_name = serializers.CharField(source="dpu_office.name", read_only=True)

    class Meta:
        model  = DPU
        fields = ["id", "name", "region", "region_name", "dpu_office", "dpu_office_name"]


class StationSerializer(serializers.ModelSerializer):
    dpu_name    = serializers.CharField(source="dpu.name",        read_only=True)
    region_name = serializers.CharField(source="dpu.region.name", read_only=True)

    class Meta:
        model  = Station
        fields = ["id", "name", "dpu", "dpu_name", "region_name"]


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Unit
        fields = ["id", "name"]


class DirectorateSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source="unit.name", read_only=True)

    class Meta:
        model  = Directorate
        fields = ["id", "name", "unit", "unit_name"]


class DepartmentSerializer(serializers.ModelSerializer):
    directorate_name = serializers.CharField(source="directorate.name",      read_only=True)
    unit_name        = serializers.CharField(source="directorate.unit.name",  read_only=True)

    class Meta:
        model  = Department
        fields = ["id", "name", "directorate", "directorate_name", "unit_name"]


class OfficeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    region_name     = serializers.CharField(source="region.name",     read_only=True)
    dpu_name        = serializers.CharField(source="dpu.name",        read_only=True)

    class Meta:
        model  = Office
        fields = [
            "id", "name",
            "department", "department_name",
            "region",     "region_name",
            "dpu",        "dpu_name",
        ]




class EquipmentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = EquipmentCategory
        fields = ["id", "name"]


class EquipmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EquipmentStatus
        fields = ["id", "name"]


class BrandSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model  = Brand
        fields = ["id", "name", "category", "category_name"]




class EquipmentSerializer(serializers.ModelSerializer):

    # equipment_type FK → readable name (frontend reads item.equipment_type_name)
    equipment_type_name = serializers.CharField(source="equipment_type.name", read_only=True)

    # FK read-only labels
    brand_name       = serializers.CharField(source="brand.name",       read_only=True)
    status_name      = serializers.CharField(source="status.name",      read_only=True)
    region_name      = serializers.CharField(source="region.name",      read_only=True)
    dpu_name         = serializers.CharField(source="dpu.name",         read_only=True)
    station_name     = serializers.CharField(source="station.name",     read_only=True)
    unit_name        = serializers.CharField(source="unit.name",        read_only=True)
    directorate_name = serializers.CharField(source="directorate.name", read_only=True)
    department_name  = serializers.CharField(source="department.name",  read_only=True)
    office_name      = serializers.CharField(source="office.name",      read_only=True)

    # Audit display
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    # Computed model properties
    age_since_deployed = serializers.ReadOnlyField()
    is_in_stock        = serializers.ReadOnlyField()

    class Meta:
        model  = Equipment
        fields = "__all__"
        # equipment_type_name is extra (not a model field) so we list it explicitly
        # by using __all__ DRF will include all model fields; extra declared fields
        # are always included automatically.
        read_only_fields = ["created_at", "updated_at"]

    def get_created_by_name(self, obj) -> str | None:
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_updated_by_name(self, obj) -> str | None:
        return obj.updated_by.get_full_name() if obj.updated_by else None

    def validate(self, data):
        
        # On updates the intent field cannot be changed.
        if self.instance and "registration_intent" in data:
            if data["registration_intent"] != self.instance.registration_intent:
                raise serializers.ValidationError({
                    "registration_intent": (
                        "Registration intent cannot be changed after the item has been registered."
                    )
                })

        # On creation with Deployment intent, at least one location is required.
        intent = data.get("registration_intent", Equipment.RegistrationIntent.STOCK)
        if intent == Equipment.RegistrationIntent.DEPLOYMENT:
            location_fields = [
                "region", "dpu", "station",
                "unit", "directorate", "department", "office",
            ]
            if not any(data.get(f) for f in location_fields):
                raise serializers.ValidationError({
                    "registration_intent": (
                        "Deployment intent requires at least one location field "
                        "(Region, DPU, Station, Unit, Directorate, Department, or Office)."
                    )
                })

        return data




class StockSerializer(serializers.ModelSerializer):
    equipment_name   = serializers.CharField(source="equipment.name",          read_only=True)
    equipment_serial = serializers.CharField(source="equipment.serial_number", read_only=True)
    added_by_name    = serializers.SerializerMethodField()

    class Meta:
        model  = Stock
        fields = [
            "id", "equipment", "equipment_name", "equipment_serial",
            "condition", "storage_location",
            "date_added", "comments",
            "added_by", "added_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["date_added", "created_at", "updated_at"]

    def get_added_by_name(self, obj) -> str | None:
        return obj.added_by.get_full_name() if obj.added_by else None




class DeploymentSerializer(serializers.ModelSerializer):

    # Equipment labels
    equipment_name   = serializers.CharField(source="equipment.name",                read_only=True)
    equipment_serial = serializers.CharField(source="equipment.serial_number",       read_only=True)
    # equipment_type is now a FK → EquipmentCategory; resolve to the name string
    equipment_type   = serializers.CharField(source="equipment.equipment_type.name", read_only=True)

    # Org-level recipient labels
    issued_to_region_office_name = serializers.CharField(source="issued_to_region_office.name", read_only=True)
    issued_to_region_name        = serializers.CharField(source="issued_to_region.name",        read_only=True)
    issued_to_dpu_office_name    = serializers.CharField(source="issued_to_dpu_office.name",    read_only=True)
    issued_to_dpu_name           = serializers.CharField(source="issued_to_dpu.name",           read_only=True)
    issued_to_station_name       = serializers.CharField(source="issued_to_station.name",       read_only=True)
    issued_to_unit_name          = serializers.CharField(source="issued_to_unit.name",          read_only=True)
    issued_to_directorate_name   = serializers.CharField(source="issued_to_directorate.name",   read_only=True)
    issued_to_department_name    = serializers.CharField(source="issued_to_department.name",    read_only=True)
    issued_to_office_name        = serializers.CharField(source="issued_to_office.name",        read_only=True)

    # Audit labels
    issued_by_name           = serializers.SerializerMethodField()
    return_confirmed_by_name = serializers.SerializerMethodField()

    class Meta:
        model  = Deployment
        fields = [
            "id", "equipment", "equipment_name", "equipment_type", "equipment_serial",
            "status",
            # Recipients
            "issued_to_user",
            "issued_to_region_office", "issued_to_region_office_name",
            "issued_to_region",        "issued_to_region_name",
            "issued_to_dpu_office",    "issued_to_dpu_office_name",
            "issued_to_dpu",           "issued_to_dpu_name",
            "issued_to_station",       "issued_to_station_name",
            "issued_to_unit",          "issued_to_unit_name",
            "issued_to_directorate",   "issued_to_directorate_name",
            "issued_to_department",    "issued_to_department_name",
            "issued_to_office",        "issued_to_office_name",
            # Dates
            "issued_date", "expected_return_date",
            "returned_date", "condition_on_return",
            "purpose", "comments",
            # Audit
            "issued_by",           "issued_by_name",
            "return_confirmed_by", "return_confirmed_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, data):
        instance = getattr(self, "instance", None)

        status          = data.get("status",               getattr(instance, "status",               None))
        returned_date   = data.get("returned_date",        getattr(instance, "returned_date",        None))
        issued_date     = data.get("issued_date",          getattr(instance, "issued_date",          None))
        exp_return_date = data.get("expected_return_date", getattr(instance, "expected_return_date", None))

        errors = {}

        if status == "Returned" and not returned_date:
            errors["returned_date"] = "A return date is required when status is 'Returned'."

        if issued_date and exp_return_date and exp_return_date < issued_date:
            errors["expected_return_date"] = "Expected return date cannot be before the issue date."

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def get_issued_by_name(self, obj) -> str | None:
        return obj.issued_by.get_full_name() if obj.issued_by else None

    def get_return_confirmed_by_name(self, obj) -> str | None:
        return obj.return_confirmed_by.get_full_name() if obj.return_confirmed_by else None