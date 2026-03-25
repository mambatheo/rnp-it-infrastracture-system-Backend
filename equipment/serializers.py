from rest_framework import serializers

from .models import (
    RegionOffice, Region, DPUOffice, DPU, Station,
    Unit, Directorate, Department, Office,
    EquipmentCategory, EquipmentStatus, Brand,
    Equipment, Stock, Deployment, Lending,
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
    directorate_name = serializers.CharField(source="directorate.name",     read_only=True)
    unit_name        = serializers.CharField(source="directorate.unit.name", read_only=True)

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

    equipment_type_name = serializers.CharField(source="equipment_type.name", read_only=True)

    brand_name       = serializers.CharField(source="brand.name",       read_only=True)
    status_name      = serializers.CharField(source="status.name",      read_only=True)
    region_name      = serializers.CharField(source="region.name",      read_only=True)
    dpu_name         = serializers.CharField(source="dpu.name",         read_only=True)
    station_name     = serializers.CharField(source="station.name",     read_only=True)
    unit_name        = serializers.CharField(source="unit.name",        read_only=True)
    directorate_name = serializers.CharField(source="directorate.name", read_only=True)
    department_name  = serializers.CharField(source="department.name",  read_only=True)
    office_name      = serializers.CharField(source="office.name",      read_only=True)

    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    age_since_deployed = serializers.ReadOnlyField()
    is_in_stock        = serializers.ReadOnlyField()

    class Meta:
        model            = Equipment
        fields           = "__all__"
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
            "storage_location",
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

    # Audit label
    issued_by_name = serializers.SerializerMethodField()

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
            # Dates & notes
            "issued_date", "comments",
            # Audit
            "issued_by", "issued_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_issued_by_name(self, obj) -> str | None:
        return obj.issued_by.get_full_name() if obj.issued_by else None
    
class LendingSerializer(serializers.ModelSerializer):

    equipment_name         = serializers.CharField(source="equipment.name",           read_only=True)
    equipment_serial       = serializers.CharField(source="equipment.serial_number",  read_only=True)
    equipment_type         = serializers.CharField(source="equipment.equipment_type.name", read_only=True)
    equipment_marking_code = serializers.CharField(source="equipment.marking_code",   read_only=True)
    equipment_brand        = serializers.CharField(source="equipment.brand.name",     read_only=True)

    issued_by_name           = serializers.SerializerMethodField()
    return_confirmed_by_name = serializers.SerializerMethodField()

    class Meta:
        model  = Lending
        fields = [
            "id", "equipment", "equipment_name", "equipment_serial", "equipment_type",
            "equipment_brand", "equipment_marking_code",   
            "status",
            # Borrower
            "borrower_name", "phone_number", "purpose",
            # Dates
            "issued_date", "returned_date",
            # Return details
            "returned_by", "condition_on_return", "return_comments",
            # Audit
            "issued_by",           "issued_by_name",
            "return_confirmed_by", "return_confirmed_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]





    def get_issued_by_name(self, obj) -> str | None:
        return obj.issued_by.get_full_name() if obj.issued_by else None

    def get_return_confirmed_by_name(self, obj) -> str | None:
        return obj.return_confirmed_by.get_full_name() if obj.return_confirmed_by else None

    def validate(self, data):
        instance = getattr(self, "instance", None)

        status        = data.get("status",        getattr(instance, "status",        None))
        returned_date = data.get("returned_date", getattr(instance, "returned_date", None))
        issued_date   = data.get("issued_date",   getattr(instance, "issued_date",   None))

        errors = {}

        if returned_date and issued_date and returned_date < issued_date:
            errors["returned_date"] = "Return date cannot be before the issue date."

        if status == Lending.LendingStatus.RETURNED and not returned_date:
            errors["returned_date"] = "A return date is required when status is 'Returned'."

        if errors:
            raise serializers.ValidationError(errors)

        return data