import base64

from django.db.models import Count, Exists, OuterRef, Q
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
from celery.result import AsyncResult

from .models import (
    RegionOffice, Region, DPUOffice, DPU, Station,
    Unit, Directorate, Department, Office,
    EquipmentCategory, EquipmentStatus, Brand,
    Equipment, Stock, Deployment, Lending,
)
from .serializers import (
    RegionOfficeSerializer, RegionSerializer,
    DPUOfficeSerializer, DPUSerializer,
    StationSerializer,
    UnitSerializer, DirectorateSerializer, DepartmentSerializer, OfficeSerializer,
    EquipmentCategorySerializer, EquipmentStatusSerializer, BrandSerializer,
    EquipmentSerializer, StockSerializer, DeploymentSerializer, LendingSerializer,
)
from .tasks import (
    task_excel_all,            task_excel_by_type,
    task_pdf_all,              task_pdf_by_type,
    task_stock_excel_all,      task_stock_excel_by_type,
    task_stock_pdf_all,        task_stock_pdf_by_type,
    task_unit_excel_all,       task_unit_excel_by_unit,
    task_unit_pdf_all,         task_unit_pdf_by_unit,
    task_region_excel_all,     task_region_excel_by_region,
    task_region_pdf_all,       task_region_pdf_by_region,
    task_dpu_excel_all,        task_dpu_excel_by_dpu,
    task_dpu_pdf_all,          task_dpu_pdf_by_dpu,
)

# ─────────────────────────────────────────
# PERMISSION HELPERS
# ─────────────────────────────────────────

def _is_privileged(user):
    """Return True for ADMIN / IT_STAFF / superusers — they see everything."""
    return (
        user.is_superuser
        or getattr(user, "role", None) in ("ADMIN", "IT_STAFF")
    )


def _location_q(user):
    """
    Build a Q filter matching equipment assigned to the user's location.
    USER / TECHNICIAN can be assigned to dpu, region, and/or unit.
    """
    q = Q()
    if getattr(user, "dpu_id", None):
        q |= Q(dpu=user.dpu)
    if getattr(user, "region_id", None):
        q |= Q(region=user.region)
    if getattr(user, "unit_id", None):
        q |= Q(unit=user.unit)
    return q


# ─────────────────────────────────────────
# LOCATION VIEWSETS
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
# CLASSIFICATION VIEWSETS
# ─────────────────────────────────────────

@extend_schema(tags=["Equipment Categories"])
class EquipmentCategoryViewSet(viewsets.ModelViewSet):
    queryset           = EquipmentCategory.objects.all()
    serializer_class   = EquipmentCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ["name"]

    def perform_destroy(self, instance):
        from django.db.models.deletion import ProtectedError
        from rest_framework.exceptions import ValidationError
        try:
            instance.delete()
        except ProtectedError as e:
            blocking = ", ".join(str(obj) for obj in list(e.protected_objects)[:10])
            raise ValidationError(
                f"Cannot delete '{instance.name}' because it is still referenced by: {blocking}. "
                "Reassign or delete those records first."
            )


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


# ─────────────────────────────────────────
# EQUIPMENT VIEWSET
# ─────────────────────────────────────────

@extend_schema(tags=["Equipment"])
class EquipmentViewSet(viewsets.ModelViewSet):
    serializer_class   = EquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = {
        "equipment_type__name": ["exact"],
        "status":               ["exact"],
        "registration_intent":  ["exact"],
        "region":               ["exact"],
        "dpu":                  ["exact"],
        "station":              ["exact"],
        "unit":                 ["exact"],
        "directorate":          ["exact"],
        "department":           ["exact"],
        "office":               ["exact"],
        "brand":                ["exact"],
    }

    search_fields = [
        "name", "serial_number", "marking_code",
        "model", "comments",
        "brand__name", "region__name", "dpu__name", "office__name",
    ]

    ordering_fields = ["created_at", "deployment_date", "name"]
    ordering        = ["-created_at"]

    def get_queryset(self):
        qs = Equipment.objects.select_related(
            "equipment_type",
            "brand", "status",
            "region", "dpu", "station",
            "unit", "directorate", "department", "office",
            "created_by", "updated_by",
        ).prefetch_related("stock")

        user = self.request.user
        if _is_privileged(user):
            return qs

        loc_q = _location_q(user)
        if not loc_q:
            return qs.none()
        return qs.filter(loc_q)

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


# ─────────────────────────────────────────
# STOCK VIEWSET
# ─────────────────────────────────────────

@extend_schema(tags=["Stock"])
class StockViewSet(viewsets.ModelViewSet):
    serializer_class   = StockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Removed "condition" — Stock model has no such field
    filterset_fields = ["equipment__equipment_type__name"]

    search_fields = [
        "equipment__name", "equipment__serial_number",
        "equipment__marking_code", "storage_location",
    ]

    ordering_fields = ["date_added", "created_at"]
    ordering        = ["-date_added"]

    def get_queryset(self):
        qs = Stock.objects.select_related(
            "equipment__brand", "equipment__status",
            "equipment__region", "equipment__dpu", "equipment__unit",
            "added_by",
        )

        user = self.request.user
        if _is_privileged(user):
            return qs

        q = Q()
        if getattr(user, "dpu_id", None):
            q |= Q(equipment__dpu=user.dpu)
        if getattr(user, "region_id", None):
            q |= Q(equipment__region=user.region)
        if getattr(user, "unit_id", None):
            q |= Q(equipment__unit=user.unit)
        if not q:
            return qs.none()
        return qs.filter(q)

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


# ─────────────────────────────────────────
# DEPLOYMENT VIEWSET
# ─────────────────────────────────────────

@extend_schema(tags=["Deployments"])
class DeploymentViewSet(viewsets.ModelViewSet):
    serializer_class   = DeploymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Removed returned_date / expected_return_date / condition_on_return
    # — none of those fields exist on Deployment
    filterset_fields = {
        "status":                          ["exact"],
        "equipment":                       ["exact"],
        "equipment__equipment_type__name": ["exact"],
        "issued_to_user":                  ["exact", "icontains"],
        "issued_to_region":                ["exact"],
        "issued_to_dpu":                   ["exact"],
        "issued_to_station":               ["exact"],
        "issued_to_unit":                  ["exact"],
        "issued_to_directorate":           ["exact"],
        "issued_to_department":            ["exact"],
        "issued_to_office":                ["exact"],
        "issued_date":                     ["exact", "gte", "lte"],
    }

    search_fields = [
        "equipment__name", "equipment__serial_number", "equipment__marking_code",
        "issued_to_user",
        "issued_to_region__name", "issued_to_dpu__name",
        "issued_to_unit__name", "issued_to_directorate__name",
        "issued_to_department__name", "issued_to_office__name",
        "comments",
    ]

    ordering_fields = ["issued_date", "created_at"]
    ordering        = ["-issued_date"]

    def get_queryset(self):
        qs = Deployment.objects.select_related(
            "equipment__brand", "equipment__status", "equipment__equipment_type",
            "issued_to_region_office",
            "issued_to_region", "issued_to_dpu_office", "issued_to_dpu",
            "issued_to_station",
            "issued_to_unit", "issued_to_directorate",
            "issued_to_department", "issued_to_office",
            "issued_by",
        )

        user = self.request.user
        if _is_privileged(user):
            return qs

        q = Q()
        if getattr(user, "dpu_id", None):
            q |= Q(issued_to_dpu=user.dpu)
            q |= Q(equipment__dpu=user.dpu)
        if getattr(user, "region_id", None):
            q |= Q(issued_to_region=user.region)
            q |= Q(equipment__region=user.region)
        if getattr(user, "unit_id", None):
            q |= Q(issued_to_unit=user.unit)
            q |= Q(equipment__unit=user.unit)
        if not q:
            return qs.none()
        return qs.filter(q)

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)


# ─────────────────────────────────────────
# LENDING VIEWSET
# ─────────────────────────────────────────

@extend_schema(tags=["Lendings"])
class LendingViewSet(viewsets.ModelViewSet):
    serializer_class   = LendingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = {
        "status":                          ["exact"],
        "equipment":                       ["exact"],
        "equipment__equipment_type__name": ["exact"],
        "condition_on_return":             ["exact"],
        "issued_date":                     ["exact", "gte", "lte"],
        "returned_date":                   ["exact", "gte", "lte"],
    }

    search_fields = [
        "equipment__name", "equipment__serial_number", "equipment__marking_code",
        "borrower_name", "phone_number",
        "purpose", "return_comments",
    ]

    ordering_fields = ["issued_date", "returned_date", "created_at"]
    ordering        = ["-issued_date"]

    def get_queryset(self):
        qs = Lending.objects.select_related(
            "equipment__brand", "equipment__status", "equipment__equipment_type",
            "equipment__region", "equipment__dpu", "equipment__unit",
            "issued_by", "return_confirmed_by",
        )

        user = self.request.user
        if _is_privileged(user):
            return qs

        q = Q()
        if getattr(user, "dpu_id", None):
            q |= Q(equipment__dpu=user.dpu)
        if getattr(user, "region_id", None):
            q |= Q(equipment__region=user.region)
        if getattr(user, "unit_id", None):
            q |= Q(equipment__unit=user.unit)
        if not q:
            return qs.none()
        return qs.filter(q)

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)


# ═════════════════════════════════════════════════════════════════
#  REPORT VIEWS  (async via Celery)
# ═════════════════════════════════════════════════════════════════

def _user_from_token_param(request):
    """Fall-back: authenticate via ?token= query-param (used for direct download links)."""
    token_str = request.query_params.get("token")
    if not token_str:
        return None
    auth = JWTAuthentication()
    try:
        validated = auth.get_validated_token(token_str)
        return auth.get_user(validated)
    except (InvalidToken, TokenError):
        return None


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


XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_CT  = "application/pdf"


def _enqueue(task_fn, *args):
    result = task_fn.delay(*args)
    return Response({"task_id": result.id, "status": "PENDING"}, status=202)


def _poll_or_download(request, task_id, filename, content_type):
    result = AsyncResult(task_id)

    if result.state in ("PENDING", "STARTED", "RETRY"):
        return Response({"task_id": task_id, "status": result.state}, status=202)

    if result.state == "FAILURE":
        return Response(
            {"task_id": task_id, "status": "FAILURE", "detail": str(result.result)},
            status=500,
        )

    raw  = base64.b64decode(result.result)
    resp = HttpResponse(raw, content_type=content_type)
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    result.forget()
    return resp


# ── Equipment reports ─────────────────────────────────────────────────────────

@extend_schema(tags=["Reports"])
class EquipmentExcelReportView(_ReportBaseView):
    def get(self, request, equipment_type=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        slug     = (equipment_type or "all").replace(" ", "_").lower()
        filename = f"equipment_{slug}_{today}.xlsx"

        if task_id:
            return _poll_or_download(request, task_id, filename, XLSX_CT)
        if equipment_type:
            return _enqueue(task_excel_by_type, equipment_type)
        return _enqueue(task_excel_all)


@extend_schema(tags=["Reports"])
class EquipmentPDFReportView(_ReportBaseView):
    def get(self, request, equipment_type=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        slug     = (equipment_type or "all").replace(" ", "_").lower()
        filename = f"equipment_{slug}_{today}.pdf"

        if task_id:
            return _poll_or_download(request, task_id, filename, PDF_CT)
        if equipment_type:
            return _enqueue(task_pdf_by_type, equipment_type)
        return _enqueue(task_pdf_all)


# ── Stock reports ─────────────────────────────────────────────────────────────

@extend_schema(tags=["Reports"])
class StockExcelReportView(_ReportBaseView):
    def get(self, request, equipment_type=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        slug     = (equipment_type or "all").replace(" ", "_").lower()
        filename = f"stock_{slug}_{today}.xlsx"

        if task_id:
            return _poll_or_download(request, task_id, filename, XLSX_CT)
        if equipment_type:
            return _enqueue(task_stock_excel_by_type, equipment_type)
        return _enqueue(task_stock_excel_all)


@extend_schema(tags=["Reports"])
class StockPDFReportView(_ReportBaseView):
    def get(self, request, equipment_type=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        slug     = (equipment_type or "all").replace(" ", "_").lower()
        filename = f"stock_{slug}_{today}.pdf"

        if task_id:
            return _poll_or_download(request, task_id, filename, PDF_CT)
        if equipment_type:
            return _enqueue(task_stock_pdf_by_type, equipment_type)
        return _enqueue(task_stock_pdf_all)


# ── Unit reports ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Reports"])
class UnitExcelReportView(_ReportBaseView):
    def get(self, request, unit_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"unit_{unit_id or 'all'}_{today}.xlsx"

        if task_id:
            return _poll_or_download(request, task_id, filename, XLSX_CT)
        if unit_id:
            return _enqueue(task_unit_excel_by_unit, str(unit_id))
        return _enqueue(task_unit_excel_all)


@extend_schema(tags=["Reports"])
class UnitPDFReportView(_ReportBaseView):
    def get(self, request, unit_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"unit_{unit_id or 'all'}_{today}.pdf"

        if task_id:
            return _poll_or_download(request, task_id, filename, PDF_CT)
        if unit_id:
            return _enqueue(task_unit_pdf_by_unit, str(unit_id))
        return _enqueue(task_unit_pdf_all)


# ── Region reports ────────────────────────────────────────────────────────────

@extend_schema(tags=["Reports"])
class RegionExcelReportView(_ReportBaseView):
    def get(self, request, region_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"region_{region_id or 'all'}_{today}.xlsx"

        if task_id:
            return _poll_or_download(request, task_id, filename, XLSX_CT)
        if region_id:
            return _enqueue(task_region_excel_by_region, str(region_id))
        return _enqueue(task_region_excel_all)


@extend_schema(tags=["Reports"])
class RegionPDFReportView(_ReportBaseView):
    def get(self, request, region_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"region_{region_id or 'all'}_{today}.pdf"

        if task_id:
            return _poll_or_download(request, task_id, filename, PDF_CT)
        if region_id:
            return _enqueue(task_region_pdf_by_region, str(region_id))
        return _enqueue(task_region_pdf_all)


# ── DPU reports ───────────────────────────────────────────────────────────────

@extend_schema(tags=["Reports"])
class DPUExcelReportView(_ReportBaseView):
    def get(self, request, dpu_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"dpu_{dpu_id or 'all'}_{today}.xlsx"

        if task_id:
            return _poll_or_download(request, task_id, filename, XLSX_CT)
        if dpu_id:
            return _enqueue(task_dpu_excel_by_dpu, str(dpu_id))
        return _enqueue(task_dpu_excel_all)


@extend_schema(tags=["Reports"])
class DPUPDFReportView(_ReportBaseView):
    def get(self, request, dpu_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"dpu_{dpu_id or 'all'}_{today}.pdf"

        if task_id:
            return _poll_or_download(request, task_id, filename, PDF_CT)
        if dpu_id:
            return _enqueue(task_dpu_pdf_by_dpu, str(dpu_id))
        return _enqueue(task_dpu_pdf_all)


# ═════════════════════════════════════════════════════════════════
#  REPORT COUNTS  (dashboard aggregations)
# ═════════════════════════════════════════════════════════════════

@extend_schema(tags=["Reports"])
class ReportCountsView(APIView):
  
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # 1. Equipment count per type
        eq_qs = (
            Equipment.objects
            .filter(equipment_type__isnull=False)
            .values("equipment_type__name")
            .annotate(count=Count("id"))
        )
        equipment_counts = {row["equipment_type__name"]: row["count"] for row in eq_qs}

        # 2. Stock count per equipment type
        st_qs = (
            Stock.objects
            .filter(equipment__equipment_type__isnull=False)
            .values("equipment__equipment_type__name")
            .annotate(count=Count("id"))
        )
        stock_counts = {row["equipment__equipment_type__name"]: row["count"] for row in st_qs}

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
        _in_stock      = Stock.objects.filter(equipment=OuterRef("pk"))
        _active_deploy = Deployment.objects.filter(equipment=OuterRef("pk"), status="Active")
        totals = {
            "equipment":          Equipment.objects.count(),
            "stock":              Stock.objects.count(),
            "deployments":        Deployment.objects.count(),
            "active_deployments": Deployment.objects.filter(status="Active").count(),
            "lendings":           Lending.objects.count(),
            "active_lendings":    Lending.objects.filter(status=Lending.LendingStatus.ACTIVE).count(),
            "unassigned":         Equipment.objects.filter(
                                      ~Exists(_in_stock),
                                      ~Exists(_active_deploy),
                                  ).count(),
        }

        return Response({
            "totals":           totals,
            "equipment_counts": equipment_counts,
            "stock_counts":     stock_counts,
            "unit_counts":      unit_counts,
            "region_counts":    region_counts,
            "dpu_counts":       dpu_counts,
        })