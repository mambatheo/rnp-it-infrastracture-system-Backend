from django.http import HttpResponse
from django.utils import timezone

from rest_framework import viewsets, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import (
    RegionOffice, Region, DPUOffice, DPU, Station,
    Unit, Directorate, Department, Office,
    EquipmentCategory, EquipmentStatus, Brand,
    Equipment, Stock, Deployment,   
  
   
)
from .serializers import (
    RegionOfficeSerializer, RegionSerializer,
    DPUOfficeSerializer, DPUSerializer,
    StationSerializer,
    UnitSerializer, DirectorateSerializer, DepartmentSerializer, OfficeSerializer,
    EquipmentCategorySerializer, EquipmentStatusSerializer, BrandSerializer,
    EquipmentSerializer, StockSerializer, DeploymentSerializer,
)
from .reports import (
    generate_excel_all, generate_excel_by_type,
    generate_pdf_all,   generate_pdf_by_type,
    generate_stock_excel_all, generate_stock_excel_by_type,
    generate_stock_pdf_all,   generate_stock_pdf_by_type,
    generate_unit_excel_all,  generate_unit_excel_by_unit,
    generate_unit_pdf_all,    generate_unit_pdf_by_unit,
    generate_region_excel_all, generate_region_excel_by_region,
    generate_region_pdf_all,   generate_region_pdf_by_region,
    generate_dpu_excel_all,    generate_dpu_excel_by_dpu,
    generate_dpu_pdf_all,      generate_dpu_pdf_by_dpu,
)


def _user_from_token_param(request):
  
    token_str = request.query_params.get("token")
    if not token_str:
        return None
    auth = JWTAuthentication()
    try:
        validated = auth.get_validated_token(token_str)
        return auth.get_user(validated)
    except (InvalidToken, TokenError):
        return None




@extend_schema(tags=["Region Offices"])
class RegionOfficeViewSet(viewsets.ModelViewSet):
    queryset           = RegionOffice.objects.all()
    serializer_class   = RegionOfficeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ["name"]


@extend_schema(tags=["Regions"])
class RegionViewSet(viewsets.ModelViewSet):
    queryset           = Region.objects.select_related("region_office")
    serializer_class   = RegionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ["region_office"]
    search_fields      = ["name"]


@extend_schema(tags=["DPU Offices"])
class DPUOfficeViewSet(viewsets.ModelViewSet):
    queryset           = DPUOffice.objects.all()
    serializer_class   = DPUOfficeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ["name"]


@extend_schema(tags=["DPUs"])
class DPUViewSet(viewsets.ModelViewSet):
    queryset           = DPU.objects.select_related("region", "dpu_office")
    serializer_class   = DPUSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ["region", "dpu_office"]
    search_fields      = ["name"]


@extend_schema(tags=["Stations"])
class StationViewSet(viewsets.ModelViewSet):
    queryset           = Station.objects.select_related("dpu__region")
    serializer_class   = StationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ["dpu", "dpu__region"]
    search_fields      = ["name"]


@extend_schema(tags=["Units"])
class UnitViewSet(viewsets.ModelViewSet):
    queryset           = Unit.objects.all()
    serializer_class   = UnitSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ["name"]


@extend_schema(tags=["Directorates"])
class DirectorateViewSet(viewsets.ModelViewSet):
    queryset           = Directorate.objects.select_related("unit")
    serializer_class   = DirectorateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ["unit"]
    search_fields      = ["name"]


@extend_schema(tags=["Departments"])
class DepartmentViewSet(viewsets.ModelViewSet):
    queryset           = Department.objects.select_related("directorate__unit")
    serializer_class   = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ["directorate", "directorate__unit"]
    search_fields      = ["name"]


@extend_schema(tags=["Offices"])
class OfficeViewSet(viewsets.ModelViewSet):
    queryset           = Office.objects.select_related("department", "region", "dpu")
    serializer_class   = OfficeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ["department", "region", "dpu"]
    search_fields      = ["name"]


@extend_schema(tags=["Equipment Categories"])
class EquipmentCategoryViewSet(viewsets.ModelViewSet):
    queryset           = EquipmentCategory.objects.all()
    serializer_class   = EquipmentCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ["name"]


@extend_schema(tags=["Equipment Status"])
class EquipmentStatusViewSet(viewsets.ModelViewSet):
    queryset           = EquipmentStatus.objects.all()
    serializer_class   = EquipmentStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ["name"]


@extend_schema(tags=["Brands"])
class BrandViewSet(viewsets.ModelViewSet):
    queryset           = Brand.objects.select_related("category")
    serializer_class   = BrandSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ["category"]
    search_fields      = ["name"]



@extend_schema(tags=["Equipment"])
class EquipmentViewSet(viewsets.ModelViewSet):
    serializer_class   = EquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = {
        "equipment_type":     ["exact"],
        "status":             ["exact"],       
        "registration_intent": ["exact"],
        "region":             ["exact"],
        "dpu":                ["exact"],
        "station":            ["exact"],
        "unit":               ["exact"],
        "directorate":        ["exact"],
        "department":         ["exact"],
        "office":             ["exact"],
        "brand":              ["exact"],
    }

    search_fields = [
        "name", "serial_number", "marking_code",
        "model", "comments",
        "brand__name", "region__name", "dpu__name", "office__name",
    ]

    ordering_fields = ["created_at", "deployment_date", "name"]
    ordering        = ["-created_at"]

    def get_queryset(self):
        return Equipment.objects.select_related(
            "brand", "status",
            "region", "dpu", "station",
            "unit", "directorate", "department", "office",
            "created_by", "updated_by",
        ).prefetch_related("stock")

    def perform_create(self, serializer):
       
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)




@extend_schema(tags=["Stock"])
class StockViewSet(viewsets.ModelViewSet):
    serializer_class   = StockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = ["condition", "equipment__equipment_type"]

    search_fields = [
        "equipment__name", "equipment__serial_number",
        "equipment__marking_code", "storage_location",
    ]

    ordering_fields = ["date_added", "created_at"]
    ordering        = ["-date_added"]

    def get_queryset(self):
        return Stock.objects.select_related(
            "equipment__brand", "equipment__status",
            "added_by",
        )

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)



@extend_schema(tags=["Deployments"])
class DeploymentViewSet(viewsets.ModelViewSet):
    serializer_class   = DeploymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = {
        "status":                    ["exact"],
        "equipment":                 ["exact"],
        "equipment__equipment_type": ["exact"],
        "issued_to_user":            ["exact", "icontains"],
        "issued_to_region":          ["exact"],
        "issued_to_dpu":             ["exact"],
        "issued_to_station":         ["exact"],
        "issued_to_unit":            ["exact"],
        "issued_to_directorate":     ["exact"],
        "issued_to_department":      ["exact"],
        "issued_to_office":          ["exact"],
        "issued_date":               ["exact", "gte", "lte"],
        "returned_date":             ["exact", "gte", "lte"],
        "expected_return_date":      ["exact", "gte", "lte"],
        "condition_on_return":       ["exact"],
    }

    search_fields = [
        "equipment__name", "equipment__serial_number", "equipment__marking_code",
        "issued_to_user",
        "issued_to_region__name", "issued_to_dpu__name",
        "issued_to_unit__name", "issued_to_directorate__name",
        "issued_to_department__name", "issued_to_office__name",
        "purpose", "comments",
    ]

    ordering_fields = ["issued_date", "returned_date", "created_at"]
    ordering        = ["-issued_date"]

    def get_queryset(self):
        return Deployment.objects.select_related(
            "equipment__brand", "equipment__status",
            "issued_to_region_office",
            "issued_to_region", "issued_to_dpu_office", "issued_to_dpu",
            "issued_to_station",
            "issued_to_unit", "issued_to_directorate",
            "issued_to_department", "issued_to_office",
            "issued_by", "return_confirmed_by",
        )

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)



class _ReportBaseView(APIView):
   
    authentication_classes = [JWTAuthentication]
    permission_classes      = [permissions.IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        try:
            super().initial(request, *args, **kwargs)
        except Exception:
            user = _user_from_token_param(request)
            if not user or not user.is_active:
                raise AuthenticationFailed("Valid authentication token required.")
            request.user = user


@extend_schema(tags=["Reports"])
class EquipmentExcelReportView(_ReportBaseView):
    def get(self, request, equipment_type=None):
        today = timezone.now().strftime("%Y%m%d")
        if equipment_type:
            buf      = generate_excel_by_type(equipment_type)
            slug     = equipment_type.replace(" ", "_").lower()
            filename = f"equipment_{slug}_{today}.xlsx"
        else:
            buf      = generate_excel_all()
            filename = f"equipment_all_{today}.xlsx"
        resp = HttpResponse(
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


@extend_schema(tags=["Reports"])
class EquipmentPDFReportView(_ReportBaseView):
    def get(self, request, equipment_type=None):
        today = timezone.now().strftime("%Y%m%d")
        if equipment_type:
            buf      = generate_pdf_by_type(equipment_type)
            slug     = equipment_type.replace(" ", "_").lower()
            filename = f"equipment_{slug}_{today}.pdf"
        else:
            buf      = generate_pdf_all()
            filename = f"equipment_all_{today}.pdf"
        resp = HttpResponse(buf.read(), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


@extend_schema(tags=["Reports"])
class StockExcelReportView(_ReportBaseView):
    def get(self, request, equipment_type=None):
        today = timezone.now().strftime("%Y%m%d")
        if equipment_type:
            buf      = generate_stock_excel_by_type(equipment_type)
            slug     = equipment_type.replace(" ", "_").lower()
            filename = f"stock_{slug}_{today}.xlsx"
        else:
            buf      = generate_stock_excel_all()
            filename = f"stock_all_{today}.xlsx"
        resp = HttpResponse(
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


@extend_schema(tags=["Reports"])
class StockPDFReportView(_ReportBaseView):
    def get(self, request, equipment_type=None):
        today = timezone.now().strftime("%Y%m%d")
        if equipment_type:
            buf      = generate_stock_pdf_by_type(equipment_type)
            slug     = equipment_type.replace(" ", "_").lower()
            filename = f"stock_{slug}_{today}.pdf"
        else:
            buf      = generate_stock_pdf_all()
            filename = f"stock_all_{today}.pdf"
        resp = HttpResponse(buf.read(), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


@extend_schema(tags=["Reports"])
class UnitExcelReportView(_ReportBaseView):
    def get(self, request, unit_id=None):
        today = timezone.now().strftime("%Y%m%d")
        if unit_id:
            try:
                unit = Unit.objects.get(pk=unit_id)
            except Unit.DoesNotExist:
                return Response({"detail": "Unit not found."}, status=404)
            buf      = generate_unit_excel_by_unit(unit_id)
            slug     = unit.name.replace(" ", "_").lower()
            filename = f"unit_{slug}_{today}.xlsx"
        else:
            buf      = generate_unit_excel_all()
            filename = f"units_all_{today}.xlsx"
        resp = HttpResponse(
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


@extend_schema(tags=["Reports"])
class UnitPDFReportView(_ReportBaseView):
    def get(self, request, unit_id=None):
        today = timezone.now().strftime("%Y%m%d")
        if unit_id:
            try:
                unit = Unit.objects.get(pk=unit_id)
            except Unit.DoesNotExist:
                return Response({"detail": "Unit not found."}, status=404)
            buf      = generate_unit_pdf_by_unit(unit_id)
            slug     = unit.name.replace(" ", "_").lower()
            filename = f"unit_{slug}_{today}.pdf"
        else:
            buf      = generate_unit_pdf_all()
            filename = f"units_all_{today}.pdf"
        resp = HttpResponse(buf.read(), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
    
@extend_schema(tags=["Reports"])
class RegionExcelReportView(_ReportBaseView):
    def get(self, request, region_id=None):
        today = timezone.now().strftime("%Y%m%d")
        if region_id:
            try:
                region = Region.objects.get(pk=region_id)
            except Region.DoesNotExist:
                return Response({"detail": "Region not found."}, status=404)
            buf      = generate_region_excel_by_region(region_id)
            slug     = region.name.replace(" ", "_").lower()
            filename = f"region_{slug}_{today}.xlsx"
        else:
            buf      = generate_region_excel_all()
            filename = f"regions_all_{today}.xlsx"
        resp = HttpResponse(buf.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


@extend_schema(tags=["Reports"])
class RegionPDFReportView(_ReportBaseView):
    def get(self, request, region_id=None):
        today = timezone.now().strftime("%Y%m%d")
        if region_id:
            try:
                region = Region.objects.get(pk=region_id)
            except Region.DoesNotExist:
                return Response({"detail": "Region not found."}, status=404)
            buf      = generate_region_pdf_by_region(region_id)
            slug     = region.name.replace(" ", "_").lower()
            filename = f"region_{slug}_{today}.pdf"
        else:
            buf      = generate_region_pdf_all()
            filename = f"regions_all_{today}.pdf"
        resp = HttpResponse(buf.read(), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


# ─────────────────────────────────────────────
# DPU REPORTS
# ─────────────────────────────────────────────

@extend_schema(tags=["Reports"])
class DPUExcelReportView(_ReportBaseView):
    def get(self, request, dpu_id=None):
        today = timezone.now().strftime("%Y%m%d")
        if dpu_id:
            try:
                dpu = DPU.objects.get(pk=dpu_id)
            except DPU.DoesNotExist:
                return Response({"detail": "DPU not found."}, status=404)
            buf      = generate_dpu_excel_by_dpu(dpu_id)
            slug     = dpu.name.replace(" ", "_").lower()
            filename = f"dpu_{slug}_{today}.xlsx"
        else:
            buf      = generate_dpu_excel_all()          
            filename = f"dpus_all_{today}.xlsx"
        resp = HttpResponse(buf.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


@extend_schema(tags=["Reports"])
class DPUPDFReportView(_ReportBaseView):
    def get(self, request, dpu_id=None):
        today = timezone.now().strftime("%Y%m%d")
        if dpu_id:                                       
            try:
                dpu = DPU.objects.get(pk=dpu_id)
            except DPU.DoesNotExist:
                return Response({"detail": "DPU not found."}, status=404)
            buf      = generate_dpu_pdf_by_dpu(dpu_id)
            slug     = dpu.name.replace(" ", "_").lower()
            filename = f"dpu_{slug}_{today}.pdf"
        else:
            buf      = generate_dpu_pdf_all()
            filename = f"dpus_all_{today}.pdf"
        resp = HttpResponse(buf.read(), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


@extend_schema(tags=["Reports"])
class ReportCountsView(APIView):
    """
    Single aggregated endpoint for the Reports page.
    Replaces ~60–80 individual API calls with 1 request.

    GET /api/v1/equipment/reports/counts/
    """
    permission_classes = [permissions.IsAuthenticated]

    EQUIPMENT_TYPES = [
        "Desktop", "Laptop", "Server", "TV Screen", "Projector",
        "Decoder", "Printer", "Network Device", "Telephone",
        "External Storage", "Peripheral", "UPS",
    ]

    def get(self, request):
        from django.db.models import Count

        # 1. Equipment count per type
        eq_qs = (
            Equipment.objects
            .filter(equipment_type__in=self.EQUIPMENT_TYPES)
            .values("equipment_type")
            .annotate(count=Count("id"))
        )
        equipment_counts = {row["equipment_type"]: row["count"] for row in eq_qs}

        # 2. Stock count per equipment type
        st_qs = (
            Stock.objects
            .filter(equipment__equipment_type__in=self.EQUIPMENT_TYPES)
            .values("equipment__equipment_type")
            .annotate(count=Count("id"))
        )
        stock_counts = {row["equipment__equipment_type"]: row["count"] for row in st_qs}

        # 3. Equipment count per Unit (includes units with 0 items)
        unit_qs = (
            Equipment.objects
            .filter(unit__isnull=False)
            .values("unit__id", "unit__name")
            .annotate(count=Count("id"))
        )
        unit_counts = {
            str(row["unit__id"]): {"count": row["count"], "name": row["unit__name"]}
            for row in unit_qs
        }
        for u in Unit.objects.values("id", "name").order_by("name"):
            uid = str(u["id"])
            if uid not in unit_counts:
                unit_counts[uid] = {"count": 0, "name": u["name"]}

        # 4. Equipment count per Region (includes regions with 0 items)
        region_qs = (
            Equipment.objects
            .filter(region__isnull=False)
            .values("region__id", "region__name")
            .annotate(count=Count("id"))
        )
        region_counts = {
            str(row["region__id"]): {"count": row["count"], "name": row["region__name"]}
            for row in region_qs
        }
        for r in Region.objects.values("id", "name").order_by("name"):
            rid = str(r["id"])
            if rid not in region_counts:
                region_counts[rid] = {"count": 0, "name": r["name"]}

        # 5. Equipment count per DPU (includes DPUs with 0 items)
        dpu_qs = (
            Equipment.objects
            .filter(dpu__isnull=False)
            .values("dpu__id", "dpu__name")
            .annotate(count=Count("id"))
        )
        dpu_counts = {
            str(row["dpu__id"]): {"count": row["count"], "name": row["dpu__name"]}
            for row in dpu_qs
        }
        for d in DPU.objects.values("id", "name").order_by("name"):
            did = str(d["id"])
            if did not in dpu_counts:
                dpu_counts[did] = {"count": 0, "name": d["name"]}

        # 6. Grand totals
        totals = {
            "equipment":   Equipment.objects.count(),
            "stock":       Stock.objects.count(),
            "deployments": Deployment.objects.count(),
        }

        return Response({
            "totals":           totals,
            "equipment_counts": equipment_counts,
            "stock_counts":     stock_counts,
            "unit_counts":      unit_counts,
            "region_counts":    region_counts,
            "dpu_counts":       dpu_counts,
        })
