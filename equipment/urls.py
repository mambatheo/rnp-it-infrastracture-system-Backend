from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    # Location HQs
    RegionOfficeViewSet, DPUOfficeViewSet,
    # Location
    RegionViewSet, DPUViewSet, StationViewSet,
    UnitViewSet, DirectorateViewSet, DepartmentViewSet, OfficeViewSet,
    # Lookups
    EquipmentCategoryViewSet, EquipmentStatusViewSet, BrandViewSet,
    # Equipment / Stock / Deployment / Lendings
    EquipmentViewSet, StockViewSet, DeploymentViewSet, LendingViewSet,
    # Reports
    EquipmentExcelReportView, EquipmentPDFReportView,
    StockExcelReportView, StockPDFReportView,
    UnitExcelReportView, UnitPDFReportView, RegionExcelReportView, RegionPDFReportView, DPUExcelReportView, DPUPDFReportView,
    ReportCountsView,
)

router = DefaultRouter()

# ── Location HQs ──────────────────────────────────────
router.register(r"region-offices",   RegionOfficeViewSet, basename="region-office")
router.register(r"dpu-offices",      DPUOfficeViewSet,    basename="dpu-office")

# ── Location ──────────────────────────────────────────
router.register(r"regions",          RegionViewSet)
router.register(r"dpus",             DPUViewSet)
router.register(r"stations",         StationViewSet)
router.register(r"units",            UnitViewSet)
router.register(r"directorates",     DirectorateViewSet)
router.register(r"departments",      DepartmentViewSet)
router.register(r"offices",          OfficeViewSet)

# ── Lookups ───────────────────────────────────────────
router.register(r"equipment-categories", EquipmentCategoryViewSet)
router.register(r"equipment-statuses",   EquipmentStatusViewSet)
router.register(r"brands",               BrandViewSet)

# ── Equipment / Stock / Deployment / Lending ────────────────────
router.register(r"equipment",   EquipmentViewSet,  basename="equipment")
router.register(r"stock",       StockViewSet,      basename="stock")
router.register(r"deployments", DeploymentViewSet, basename="deployments")
router.register(r"lendings", LendingViewSet,  basename="lendings")

urlpatterns = [
    # ── Aggregated counts — Reports page (replaces ~60 individual calls) ─
    path("reports/counts/",
         ReportCountsView.as_view(), name="report-counts"),

    # ── Reports — Equipment ────────────────────────────
    path("reports/excel/",
         EquipmentExcelReportView.as_view(), name="report-excel-all"),
    path("reports/excel/<str:equipment_type>/",
         EquipmentExcelReportView.as_view(), name="report-excel-type"),
    path("reports/pdf/",
         EquipmentPDFReportView.as_view(),   name="report-pdf-all"),
    path("reports/pdf/<str:equipment_type>/",
         EquipmentPDFReportView.as_view(),   name="report-pdf-type"),

    # ── Reports — Stock ────────────────────────────────
    path("reports/stock/excel/",
         StockExcelReportView.as_view(),     name="report-stock-excel-all"),
    path("reports/stock/excel/<str:equipment_type>/",
         StockExcelReportView.as_view(),     name="report-stock-excel-type"),
    path("reports/stock/pdf/",
         StockPDFReportView.as_view(),       name="report-stock-pdf-all"),
    path("reports/stock/pdf/<str:equipment_type>/",
         StockPDFReportView.as_view(),       name="report-stock-pdf-type"),

    # ── Reports — Unit-based ───────────────────────────
    path("reports/unit/excel/",
         UnitExcelReportView.as_view(),      name="report-unit-excel-all"),
    path("reports/unit/excel/<uuid:unit_id>/",
         UnitExcelReportView.as_view(),      name="report-unit-excel-by-unit"),
    path("reports/unit/pdf/",
         UnitPDFReportView.as_view(),        name="report-unit-pdf-all"),
    path("reports/unit/pdf/<uuid:unit_id>/",
         UnitPDFReportView.as_view(),        name="report-unit-pdf-by-unit"),
    
    # ── Reports — Region-based ───────────────────────────
    path("reports/region/excel/",
         RegionExcelReportView.as_view(),      name="report-region-excel-all"),
    path("reports/region/excel/<uuid:region_id>/",
         RegionExcelReportView.as_view(),      name="report-region-excel-by-region"),
    path("reports/region/pdf/",
         RegionPDFReportView.as_view(),        name="report-region-pdf-all"),
    path("reports/region/pdf/<uuid:region_id>/",
         RegionPDFReportView.as_view(),        name="report-region-pdf-by-region"),
    
    # ── Reports — DPU-based ───────────────────────────
    path("reports/dpu/excel/",
         DPUExcelReportView.as_view(),      name="report-dpu-excel-all"),
    path("reports/dpu/excel/<uuid:dpu_id>/",
         DPUExcelReportView.as_view(),      name="report-dpu-excel-by-dpu"),
    path("reports/dpu/pdf/",
         DPUPDFReportView.as_view(),        name="report-dpu-pdf-all"),
    path("reports/dpu/pdf/<uuid:dpu_id>/",
         DPUPDFReportView.as_view(),        name="report-dpu-pdf-by-dpu"),

    # ── All other routes via router ────────────────────
    path("", include(router.urls)),
]