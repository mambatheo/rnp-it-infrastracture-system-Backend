from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    RegionOffice, Region, DPU, DPUOffice, Station,
    Unit, Directorate, Department, Office,
    EquipmentCategory, Brand, EquipmentStatus,
    Equipment,
    Stock, Deployment, Lending,
)




class RegionInline(admin.TabularInline):
    model = Region
    extra = 0
    fields = ["name"]
    show_change_link = True


class DPUInline(admin.TabularInline):
    model = DPU
    extra = 0
    fields = ["name"]
    show_change_link = True


class DPUByOfficeInline(admin.TabularInline):
    model = DPU
    extra = 0
    fields = ["name", "region"]
    show_change_link = True


class StationInline(admin.TabularInline):
    model = Station
    extra = 0
    fields = ["name"]
    show_change_link = True


class DirectorateInline(admin.TabularInline):
    model = Directorate
    extra = 0
    fields = ["name"]
    show_change_link = True


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 0
    fields = ["name"]
    show_change_link = True


class OfficeInline(admin.TabularInline):
    model = Office
    extra = 0
    fields = ["name", "region", "dpu"]
    show_change_link = True


class BrandInline(admin.TabularInline):
    model = Brand
    extra = 0
    fields = ["name"]
    show_change_link = True


class DeploymentInline(admin.TabularInline):
    model = Deployment
    extra = 0
    fields = [
        "status",
        "issued_to_user",
        "issued_to_region", "issued_to_dpu", "issued_to_unit",
        "issued_to_directorate", "issued_to_department", "issued_to_office",
        "issued_date", "issued_by",
    ]
    readonly_fields = ["issued_date", "issued_by"]
    show_change_link = True


class LendingInline(admin.TabularInline):
    model = Lending
    extra = 0
    fields = [
        "status", "borrower_name", "phone_number",
        "issued_date", "returned_date", "condition_on_return", "issued_by",
    ]
    readonly_fields = ["issued_date", "issued_by"]
    show_change_link = True


class StockInline(admin.StackedInline):
    model = Stock
    extra = 0
    fields = ["storage_location", "date_added", "comments", "added_by"]
    readonly_fields = ["date_added", "added_by"]
    can_delete = True
    verbose_name = "Current Stock Entry"
    verbose_name_plural = "Current Stock Entry"




@admin.register(RegionOffice)
class RegionOfficeAdmin(admin.ModelAdmin):
    list_display  = ["name"]
    search_fields = ["name"]
    ordering      = ["name"]
    inlines       = [RegionInline]


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display        = ["name", "region_office"]
    list_filter         = ["region_office"]
    search_fields       = ["name", "region_office__name"]
    ordering            = ["name"]
    autocomplete_fields = ["region_office"]
    inlines             = [DPUInline]


@admin.register(DPUOffice)
class DPUOfficeAdmin(admin.ModelAdmin):
    list_display  = ["name"]
    search_fields = ["name"]
    ordering      = ["name"]
    inlines       = [DPUByOfficeInline]


@admin.register(DPU)
class DPUAdmin(admin.ModelAdmin):
    list_display        = ["name", "region", "dpu_office"]
    list_filter         = ["region", "dpu_office"]
    search_fields       = ["name", "region__name", "dpu_office__name"]
    ordering            = ["name"]
    autocomplete_fields = ["region", "dpu_office"]
    inlines             = [StationInline]


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display        = ["name", "dpu", "get_region"]
    list_filter         = ["dpu__region", "dpu"]
    search_fields       = ["name", "dpu__name", "dpu__region__name"]
    ordering            = ["name"]
    autocomplete_fields = ["dpu"]

    @admin.display(description=_("Region"), ordering="dpu__region__name")
    def get_region(self, obj):
        return obj.dpu.region


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display  = ["name"]
    search_fields = ["name"]
    ordering      = ["name"]
    inlines       = [DirectorateInline]


@admin.register(Directorate)
class DirectorateAdmin(admin.ModelAdmin):
    list_display        = ["name", "unit"]
    list_filter         = ["unit"]
    search_fields       = ["name", "unit__name"]
    ordering            = ["name"]
    autocomplete_fields = ["unit"]
    inlines             = [DepartmentInline]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display        = ["name", "directorate", "get_unit"]
    list_filter         = ["directorate__unit", "directorate"]
    search_fields       = ["name", "directorate__name"]
    ordering            = ["name"]
    autocomplete_fields = ["directorate"]
    inlines             = [OfficeInline]

    @admin.display(description=_("Unit"), ordering="directorate__unit__name")
    def get_unit(self, obj):
        return obj.directorate.unit if obj.directorate else "-"


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display        = ["name", "department", "region", "dpu"]
    list_filter         = ["region", "dpu", "department"]
    search_fields       = ["name", "department__name", "region__name", "dpu__name"]
    ordering            = ["name"]
    autocomplete_fields = ["department", "region", "dpu"]




@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display  = ["name"]
    search_fields = ["name"]
    ordering      = ["name"]
    inlines       = [BrandInline]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display        = ["name", "category"]
    list_filter         = ["category"]
    search_fields       = ["name", "category__name"]
    ordering            = ["name"]
    autocomplete_fields = ["category"]


@admin.register(EquipmentStatus)
class EquipmentStatusAdmin(admin.ModelAdmin):
    list_display  = ["name"]
    search_fields = ["name"]
    ordering      = ["name"]




@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):

    list_display = [
        "name", "equipment_type",
        "registration_intent",
        "brand", "model",
        "status", "get_stock_status",
        "region", "dpu", "office",
        "serial_number", "marking_code",
        "deployment_date", "age_since_deployed",
        "created_at",
    ]

    list_filter = [
        "registration_intent",
        "status", "equipment_type",
        "region", "dpu", "unit",
        "brand__category", "brand",
    ]

    search_fields = [
        "name", "serial_number", "marking_code",
        "model", "comments",
        "brand__name", "region__name", "dpu__name",
        "office__name",
    ]

    ordering       = ["-created_at"]
    date_hierarchy = "created_at"

    readonly_fields = [
        "id", "age_since_deployed", "get_stock_status",
        "created_at", "updated_at",
        "created_by", "updated_by",
    ]

    autocomplete_fields = [
        "region", "dpu", "station",
        "unit", "directorate", "department", "office",
        "brand", "status",
    ]

    inlines = [StockInline, DeploymentInline, LendingInline]

    fieldsets = (
        (_("Identity"), {
            "fields": (
                "id", "name", "equipment_type", "status", "get_stock_status",
            )
        }),
        (_("Registration Intent"), {
            "description": (
                " Add to Stock — item goes into the IT store immediately. "
                " Deploy Immediately — item is issued to a location/person right now. "
                "Locked after first save."
            ),
            "fields": ("registration_intent",),
        }),
        (_("Location"), {
            "fields": (
                ("region", "dpu", "station"),
                ("unit", "directorate", "department", "office"),
            )
        }),
        (_("Classification"), {
            "fields": (
                ("brand", "model"),
                ("serial_number", "marking_code"),
            )
        }),
        (_("Dates"), {
            "fields": (
                "warranty_expiration",
                "deployment_date",
                "age_since_deployed",
            )
        }),
        (_("Computer Specs"), {
            "classes": ("collapse",),
            "fields": (
                ("CPU", "GPU"),
                ("ram_size", "storage_size"),
                "operating_system",
            )
        }),
        (_("Server Specs"), {
            "classes": ("collapse",),
            "fields": (
                ("ram_slots", "storage_slots"),
                ("storage_type",),
            )
        }),
        (_("Device Details"), {
            "classes": ("collapse",),
            "fields": (
                "screen_size",
                ("printer_type", "network_type"),
                ("telephone_type", "exstorage_type", "peripheral_type"),
                "ups",
            )
        }),
        (_("Comments"), {
            "classes": ("collapse",),
            "fields": ("comments",)
        }),
        (_("Audit"), {
            "classes": ("collapse",),
            "fields": (
                ("created_at", "created_by"),
                ("updated_at", "updated_by"),
            )
        }),
    )

    @admin.display(description=_("In Stock"), boolean=True)
    def get_stock_status(self, obj):
        return obj.is_in_stock

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:
            readonly.append("registration_intent")
        return readonly

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)



@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):

    list_display = [
        "equipment", "storage_location",
        "date_added", "added_by",
    ]

    search_fields = [
        "equipment__name", "equipment__serial_number",
        "equipment__marking_code", "storage_location",
    ]

    ordering = ["-date_added"]

    readonly_fields = ["date_added", "created_at", "updated_at"]

    autocomplete_fields = ["equipment"]

    fieldsets = (
        (None, {
            "fields": (
                "equipment", "storage_location",
                "date_added", "comments",
            )
        }),
        (_("Audit"), {
            "classes": ("collapse",),
            "fields": (
                ("created_at", "updated_at"),
                "added_by",
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.added_by = request.user
        super().save_model(request, obj, form, change)




@admin.register(Deployment)
class DeploymentAdmin(admin.ModelAdmin):

    list_display = [
        "equipment", "status",
        "issued_to_user",
        "issued_to_region", "issued_to_dpu", "issued_to_unit",
        "issued_to_directorate", "issued_to_department", "issued_to_office",
        "issued_date", "issued_by",
    ]

    list_filter = [
        "status",
        "issued_to_region", "issued_to_dpu",
        "issued_to_unit", "issued_to_directorate",
        "issued_to_department", "issued_to_office",
    ]

    search_fields = [
        "equipment__name", "equipment__serial_number",
        "equipment__marking_code",
        "issued_to_user",
        "issued_to_region__name", "issued_to_dpu__name",
        "issued_to_unit__name", "issued_to_directorate__name",
        "issued_to_department__name", "issued_to_office__name",
        "comments",
    ]

    ordering       = ["-issued_date"]
    date_hierarchy = "issued_date"

    readonly_fields = ["id", "created_at", "updated_at"]

    autocomplete_fields = [
        "equipment",
        "issued_to_region", "issued_to_dpu", "issued_to_unit",
        "issued_to_directorate", "issued_to_department", "issued_to_office",
    ]

    fieldsets = (
        (_("Equipment"), {
            "fields": ("id", "equipment", "status")
        }),
        (_("Recipients"), {
            "description": "Fill the individual recipient and/or any organisational level the item was issued to.",
            "fields": (
                "issued_to_user",
                ("issued_to_region_office", "issued_to_region"),
                ("issued_to_dpu_office",    "issued_to_dpu"),
                "issued_to_station",
                ("issued_to_unit", "issued_to_directorate"),
                ("issued_to_department", "issued_to_office"),
                "purpose",
            )
        }),
        (_("Dates"), {
            "fields": (
                "issued_date",
            )
        }),
        (_("Comments"), {
            "classes": ("collapse",),
            "fields": ("comments",)
        }),
        (_("Audit"), {
            "classes": ("collapse",),
            "fields": (
                "issued_by",
                ("created_at", "updated_at"),
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.issued_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Lending)
class LendingAdmin(admin.ModelAdmin):

    list_display = [
        "equipment", "status",
        "borrower_name", "phone_number",
        "issued_date", "returned_date",
        "condition_on_return", "issued_by",
    ]

    list_filter = [
        "status", "condition_on_return",
    ]

    search_fields = [
        "equipment__name", "equipment__serial_number",
        "equipment__marking_code",
        "borrower_name", "phone_number",
        "purpose", "return_comments",
    ]

    ordering       = ["-issued_date"]
    date_hierarchy = "issued_date"

    readonly_fields = ["id", "created_at", "updated_at"]

    autocomplete_fields = ["equipment"]

    fieldsets = (
        (_("Equipment"), {
            "fields": ("id", "equipment", "status")
        }),
        (_("Borrower"), {
            "fields": (
                ("borrower_name", "phone_number"),
                "purpose",
            )
        }),
        (_("Dates"), {
            "fields": (
                ("issued_date", "returned_date"),
            )
        }),
        (_("Return Details"), {
            "fields": (
                ("returned_by", "condition_on_return"),
                "return_comments",
            )
        }),
        (_("Audit"), {
            "classes": ("collapse",),
            "fields": (
                ("issued_by", "return_confirmed_by"),
                ("created_at", "updated_at"),
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.issued_by = request.user
        super().save_model(request, obj, form, change)