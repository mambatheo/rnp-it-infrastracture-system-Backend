from datetime import timedelta

from django.contrib.auth import authenticate
from django.utils import timezone

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from drf_spectacular.utils import extend_schema

from .models import User
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserUpdateSerializer,
    LoginSerializer, AdminSetPasswordSerializer, ChangePasswordSerializer,
)


# ─────────────────────────────────────────
# USER MANAGEMENT
# ─────────────────────────────────────────

@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    queryset           = User.objects.all()
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.ADMIN or user.is_superuser:
            return User.objects.all().order_by("created_at")
        return User.objects.filter(id=user.id).order_by("created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegistrationSerializer
        if self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @extend_schema(tags=["Users"])
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({"status": "User activated."})

    @extend_schema(tags=["Users"])
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({"status": "User deactivated."})

    @extend_schema(tags=["Users"])
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def reset_password(self, request, pk=None):
        user = self.get_object()
        serializer = AdminSetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response({"status": "Password reset successfully."})

    @extend_schema(tags=["Users"])
    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": "Password changed successfully."})
    



# ─────────────────────────────────────────
# AUTH  (login / refresh / logout)
# ─────────────────────────────────────────

@extend_schema(tags=["Auth"])
class AuthViewSet(viewsets.ViewSet):

    # ── Login ─────────────────────────────────────────────────────────────────

    @action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email    = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ── Lock check ───────────────────────────────────────────────────────
        if user_obj.is_locked:
            if user_obj.locked_until and user_obj.locked_until > timezone.now():
                return Response(
                    {"error": f"Account is locked until {user_obj.locked_until}."},
                    status=status.HTTP_423_LOCKED,
                )
            # Lock period expired — reset automatically
            user_obj.is_locked             = False
            user_obj.failed_login_attempts = 0
            user_obj.locked_until          = None
            user_obj.save()

        # ── Authenticate ──────────────────────────────────────────────────────
        user = authenticate(request, username=email, password=password)

        if user is None:
            user_obj.failed_login_attempts += 1
            if user_obj.failed_login_attempts >= 3:
                user_obj.is_locked    = True
                user_obj.locked_until = timezone.now() + timedelta(minutes=30)
                user_obj.save()
                return Response(
                    {"error": "Account locked due to too many failed attempts. Try again in 30 minutes."},
                    status=status.HTTP_423_LOCKED,
                )
            user_obj.save()
            return Response(
                {"error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"error": "Account is not active. Contact your administrator."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Success — reset counter and issue tokens ───────────────────────
        user.failed_login_attempts = 0
        user.save()

        refresh = RefreshToken.for_user(user)

        # Admins and superusers are exempt from the forced password-change flow
        is_first_login = False if (user.role == User.ADMIN or user.is_superuser) else user.is_first_login

        # Build user data; normalise role for superusers/staff who may have no role set
        user_data = UserSerializer(user).data
        if not user_data.get('role') and (user.is_superuser or user.is_staff):
            user_data['role'] = User.ADMIN

        return Response({
            "access":         str(refresh.access_token),
            "refresh":        str(refresh),
            "is_first_login": is_first_login,
            "user":           user_data,
        })

    # ── Refresh ───────────────────────────────────────────────────────────────

    @extend_schema(exclude=True)                     
    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def refresh(self, request):
        user    = request.user
        refresh = RefreshToken.for_user(user)
        is_first_login = False if (user.role == User.ADMIN or user.is_superuser) else user.is_first_login
        return Response({
            "access":         str(refresh.access_token),
            "refresh":        str(refresh),
            "is_first_login": is_first_login,
            "user":           UserSerializer(user).data,
        })

    # ── Logout ────────────────────────────────────────────────────────────────

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        refresh_token = request.data.get("refresh")   

        if not refresh_token:
            return Response(
                {"error": "Refresh token is required to logout."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {"error": "Token is invalid or already blacklisted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"message": "Logged out successfully."})
