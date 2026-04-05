import os

from django.conf import settings
from django.core.cache import cache
from django.core import signing
from django.db.models import Count, Exists, OuterRef, Q
from django.http import FileResponse, HttpResponse
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
    Equipment, Stock, Deployment, Lending, TrainingSchool,
)
from .serializers import (
    RegionOfficeSerializer, RegionSerializer,
    DPUOfficeSerializer, DPUSerializer,
    StationSerializer,
    UnitSerializer, DirectorateSerializer, DepartmentSerializer, OfficeSerializer,
    EquipmentCategorySerializer, EquipmentStatusSerializer, BrandSerializer,
    EquipmentSerializer, StockSerializer, DeploymentSerializer, LendingSerializer,
    TrainingSchoolSerializer,
)
from .tasks import (
    task_excel_all,                task_excel_by_type,
    task_pdf_all,                  task_pdf_by_type,
    task_stock_excel_all,          task_stock_excel_by_type,
    task_stock_pdf_all,            task_stock_pdf_by_type,
    task_unit_excel_all,           task_unit_excel_by_unit,
    task_unit_pdf_all,             task_unit_pdf_by_unit,
    task_trainingschool_excel_all, task_trainingschool_excel_by_school,
    task_trainingschool_pdf_all,   task_trainingschool_pdf_by_school,
    task_region_excel_all,         task_region_excel_by_region,
    task_region_pdf_all,           task_region_pdf_by_region,
    task_dpu_excel_all,            task_dpu_excel_by_dpu,
    task_dpu_pdf_all,              task_dpu_pdf_by_dpu,
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


@extend_schema(tags=["Training Schools"])
class TrainingSchoolViewSet(viewsets.ModelViewSet):
    queryset           = TrainingSchool.objects.all()
    serializer_class   = TrainingSchoolSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.SearchFilter]
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
        "training_school":      ["exact"],
        "brand":                ["exact"],
    }

    search_fields = [
        "name", "serial_number", "marking_code",
        "model", "comments",
        "brand__name", "region__name", "dpu__name",
        "office__name", "training_school__name",
    ]

    ordering_fields = ["created_at", "deployment_date", "name"]
    ordering        = ["-created_at"]

    def get_queryset(self):
        qs = Equipment.objects.select_related(
            "equipment_type",
            "brand", "status",
            "region", "dpu", "station",
            "unit", "directorate", "department", "office", "training_school",
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
        "issued_to_trainingschool":        ["exact"],
        "issued_date":                     ["exact", "gte", "lte"],
    }

    search_fields = [
        "equipment__name", "equipment__serial_number", "equipment__marking_code",
        "issued_to_user",
        "issued_to_region__name", "issued_to_dpu__name",
        "issued_to_unit__name", "issued_to_directorate__name",
        "issued_to_department__name", "issued_to_office__name",
        "issued_to_trainingschool__name",
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
            "issued_to_department", "issued_to_office", "issued_to_trainingschool",
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
        if getattr(user, "training_school_id", None):
            q |= Q(issued_to_trainingschool=user.training_school)
            q |= Q(equipment__training_school=user.training_school)
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
            "equipment__region", "equipment__dpu",
            "equipment__unit", "equipment__training_school",
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
        if getattr(user, "training_school_id", None):
            q |= Q(equipment__training_school=user.training_school)
        if not q:
            return qs.none()
        return qs.filter(q)

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)


# ═════════════════════════════════════════════════════════════════
#  REPORT INFRASTRUCTURE
# ═════════════════════════════════════════════════════════════════

XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_CT  = "application/pdf"

REPORTS_DIR = os.path.join(settings.MEDIA_ROOT, "reports")


def _ensure_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _user_from_token_param(request):
    """Authenticate via ?token= query-param (used for direct download links)."""
    token_str = request.query_params.get("token")
    if not token_str:
        return None
    auth = JWTAuthentication()
    try:
        validated = auth.get_validated_token(token_str)
        return auth.get_user(validated)
    except (InvalidToken, TokenError):
        return None


def _user_from_download_token_param(request):
    """Authenticate via signed ?dl_token= query-param."""
    token = request.query_params.get("dl_token")
    if not token:
        return None
    try:
        payload = signing.loads(
            token,
            salt=getattr(settings, "REPORT_DOWNLOAD_TOKEN_SALT", "report-download-v1"),
            max_age=getattr(settings, "REPORT_DOWNLOAD_TOKEN_MAX_AGE_SECONDS", 60 * 60 * 24),
        )
    except Exception:
        return None

    req_task_id = request.query_params.get("task_id")
    if not req_task_id or payload.get("task_id") != req_task_id:
        return None

    uid = payload.get("uid")
    if not uid:
        return None
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.get(id=uid)
    except Exception:
        return None


class _ReportBaseView(APIView):
    """
    Base view for all report endpoints.
    Falls back to token-based auth so reports can be downloaded
    via direct links (e.g. from React using ?dl_token=... or ?token=...).
    """
    authentication_classes = [JWTAuthentication]
    permission_classes      = [permissions.IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        # 1. Try standard JWT auth (headers)
        try:
            super().initial(request, *args, **kwargs)
            if request.user and request.user.is_authenticated:
                return
        except Exception:
            pass

        # 2. Try signed download token (?dl_token=...)
        user = _user_from_download_token_param(request)
        if user and user.is_active:
            request.user = user
            return

        # 3. Try raw JWT in query param (?token=...)
        user = _user_from_token_param(request)
        if user and user.is_active:
            request.user = user
            return

        # 4. Fail
        raise AuthenticationFailed("Valid authentication token required.")


def _enqueue_response(request, task_fn, *args):
    """
    Dispatch a Celery task and return 202 with task_id + signed download token.
    The frontend polls using the task_id until state = SUCCESS, then downloads.
    """
    result   = task_fn.delay(*args)
    task_id  = result.id
    uid      = str(getattr(request.user, "id", "")) or None
    dl_token = signing.dumps(
        {"uid": uid, "task_id": task_id},
        salt=getattr(settings, "REPORT_DOWNLOAD_TOKEN_SALT", "report-download-v1"),
    )
    return Response(
        {"task_id": task_id, "status": "PENDING", "download_token": dl_token},
        status=202,
    )


def _poll_or_download(request, task_id, filename, content_type):
    """
    Poll for task completion or stream the finished file from disk.

    Flow:
      PENDING / STARTED / RETRY / PROGRESS → return 202 with progress info
      FAILURE                               → return 500 with error detail
      SUCCESS                               → stream file from disk as FileResponse
    """
    result = AsyncResult(task_id)

    # ── Still running ─────────────────────────────────────────────────────────
    if result.state in ("PENDING", "STARTED", "RETRY", "PROGRESS"):
        meta     = result.info or {}
        progress = None
        try:
            current = meta.get("current")
            total   = meta.get("total")
            if current is not None and total:
                progress = int(current * 100 / total)
        except Exception:
            pass

        payload = {"task_id": task_id, "status": result.state}
        if progress is not None:
            payload["progress"] = progress
        return Response(payload, status=202)

    # ── Failed ────────────────────────────────────────────────────────────────
    if result.state == "FAILURE":
        return Response(
            {"task_id": task_id, "status": "FAILURE", "detail": str(result.result)},
            status=500,
        )

    # ── Done — stream file from disk ──────────────────────────────────────────   
    file_path = result.result

    if not file_path or not isinstance(file_path, str):
        return Response(
            {
                "task_id": task_id,
                "status": "FAILURE",
                "detail": "Task completed but returned no file path.",
            },
            status=500,
        )

    if not os.path.exists(file_path):
        return Response(
            {
                "task_id": task_id,
                "status": "FAILURE",
                "detail": (
                    "Report file not found on disk. "
                    "It may have been cleaned up. Please regenerate."
                ),
            },
            status=404,
        )

    # FileResponse streams the file in configurable chunks (default 8KB)
    # so RAM usage stays flat regardless of file size (even multi-GB Excel files)
    response = FileResponse(
        open(file_path, "rb"),          # opened in binary mode
        content_type=content_type,
        as_attachment=True,
        filename=filename,
    )

    # Clean up task result from Redis (file stays on disk until daily cleanup)
    result.forget()

    return response


# ═════════════════════════════════════════════════════════════════
#  REPORT VIEWS
# ═════════════════════════════════════════════════════════════════

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
            return _enqueue_response(request, task_excel_by_type, equipment_type)
        return _enqueue_response(request, task_excel_all)


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
            return _enqueue_response(request, task_pdf_by_type, equipment_type)
        return _enqueue_response(request, task_pdf_all)


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
            return _enqueue_response(request, task_stock_excel_by_type, equipment_type)
        return _enqueue_response(request, task_stock_excel_all)


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
            return _enqueue_response(request, task_stock_pdf_by_type, equipment_type)
        return _enqueue_response(request, task_stock_pdf_all)


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
            return _enqueue_response(request, task_unit_excel_by_unit, str(unit_id))
        return _enqueue_response(request, task_unit_excel_all)


@extend_schema(tags=["Reports"])
class UnitPDFReportView(_ReportBaseView):
    def get(self, request, unit_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"unit_{unit_id or 'all'}_{today}.pdf"

        if task_id:
            return _poll_or_download(request, task_id, filename, PDF_CT)
        if unit_id:
            return _enqueue_response(request, task_unit_pdf_by_unit, str(unit_id))
        return _enqueue_response(request, task_unit_pdf_all)


# ── Training School reports ───────────────────────────────────────────────────

@extend_schema(tags=["Reports"])
class TrainingSchoolExcelReportView(_ReportBaseView):
    def get(self, request, trainingschool_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"trainingschool_{trainingschool_id or 'all'}_{today}.xlsx"

        if task_id:
            return _poll_or_download(request, task_id, filename, XLSX_CT)
        if trainingschool_id:
            return _enqueue_response(
                request, task_trainingschool_excel_by_school, str(trainingschool_id)
            )
        return _enqueue_response(request, task_trainingschool_excel_all)


@extend_schema(tags=["Reports"])
class TrainingSchoolPDFReportView(_ReportBaseView):
    def get(self, request, trainingschool_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"trainingschool_{trainingschool_id or 'all'}_{today}.pdf"

        if task_id:
            return _poll_or_download(request, task_id, filename, PDF_CT)
        if trainingschool_id:
            return _enqueue_response(
                request, task_trainingschool_pdf_by_school, str(trainingschool_id)
            )
        return _enqueue_response(request, task_trainingschool_pdf_all)


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
            return _enqueue_response(request, task_region_excel_by_region, str(region_id))
        return _enqueue_response(request, task_region_excel_all)


@extend_schema(tags=["Reports"])
class RegionPDFReportView(_ReportBaseView):
    def get(self, request, region_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"region_{region_id or 'all'}_{today}.pdf"

        if task_id:
            return _poll_or_download(request, task_id, filename, PDF_CT)
        if region_id:
            return _enqueue_response(request, task_region_pdf_by_region, str(region_id))
        return _enqueue_response(request, task_region_pdf_all)


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
            return _enqueue_response(request, task_dpu_excel_by_dpu, str(dpu_id))
        return _enqueue_response(request, task_dpu_excel_all)


@extend_schema(tags=["Reports"])
class DPUPDFReportView(_ReportBaseView):
    def get(self, request, dpu_id=None):
        today    = timezone.now().strftime("%Y%m%d")
        task_id  = request.query_params.get("task_id")
        filename = f"dpu_{dpu_id or 'all'}_{today}.pdf"

        if task_id:
            return _poll_or_download(request, task_id, filename, PDF_CT)
        if dpu_id:
            return _enqueue_response(request, task_dpu_pdf_by_dpu, str(dpu_id))
        return _enqueue_response(request, task_dpu_pdf_all)


# ═════════════════════════════════════════════════════════════════
#  REPORT COUNTS  (dashboard aggregations)
# ═════════════════════════════════════════════════════════════════

@extend_schema(tags=["Reports"])
class ReportCountsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    _CACHE_KEY         = "report_counts_summary"

    _EMPTY_PAYLOAD = {
        "_computing": True,
        "_message": (
            "Counts are being computed in the background. "
            "This usually takes under 10 minutes. Please refresh shortly."
        ),
        "totals": {
            "equipment":          0,
            "stock":              0,
            "deployments":        0,
            "active_deployments": 0,
            "lendings":           0,
            "active_lendings":    0,
            "unassigned":         0,
        },
        "equipment_counts": {},
        "stock_counts":     {},
        "region_counts":    {},
        "dpu_counts":       {},
        "unit_counts":      {},
    }

    def get(self, request):
        cached = cache.get(self._CACHE_KEY)

        if cached is not None:
            return Response(cached, status=200)

        # Cache empty — trigger background computation
        try:
            from .tasks import refresh_report_counts
            refresh_report_counts.apply_async(countdown=2)
        except Exception:
            pass

        return Response(self._EMPTY_PAYLOAD, status=202)