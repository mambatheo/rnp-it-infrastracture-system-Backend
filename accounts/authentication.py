from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class ActiveUserJWTAuthentication(JWTAuthentication):

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.is_active:
            raise AuthenticationFailed('Account has been deactivated.')
        if user.is_locked:
            raise AuthenticationFailed('Account is locked.')
        return user


class QueryParamJWTAuthentication(ActiveUserJWTAuthentication):

    def authenticate(self, request):
        raw_token = request.query_params.get('token')
        if raw_token:
            try:
                validated = self.get_validated_token(raw_token.encode())
                user = self.get_user(validated)
                return (user, validated)
            except Exception:
                pass
        return super().authenticate(request)


# ── drf-spectacular: teach it that our custom auth is JWT Bearer ───────────────
try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class ActiveUserJWTAuthenticationExtension(OpenApiAuthenticationExtension):
        target_class = 'accounts.authentication.ActiveUserJWTAuthentication'
        name = 'jwtAuth'

        def get_security_definition(self, auto_schema):
            return {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }

    class QueryParamJWTAuthenticationExtension(OpenApiAuthenticationExtension):
        target_class = 'accounts.authentication.QueryParamJWTAuthentication'
        name = 'queryParamJwtAuth'

        def get_security_definition(self, auto_schema):
            return {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
except ImportError:
    pass  # drf-spectacular not installed — skip silently

