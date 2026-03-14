from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class ActiveUserJWTAuthentication(JWTAuthentication):
    """Reject requests from deactivated or locked users even if token is still valid."""
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.is_active:
            raise AuthenticationFailed('Account has been deactivated.')
        if user.is_locked:
            raise AuthenticationFailed('Account is locked.')
        return user


class QueryParamJWTAuthentication(ActiveUserJWTAuthentication):
    """
    Extends ActiveUserJWTAuthentication to also accept JWT via ?token= query param.
    Used exclusively by file-download endpoints so the browser can open the URL
    directly (avoiding cross-origin fetch CORS restrictions).
    Falls back to the standard Bearer header if ?token is absent.
    """
    def authenticate(self, request):
        raw_token = request.query_params.get('token')
        if raw_token:
            try:
                validated = self.get_validated_token(raw_token.encode())
                user = self.get_user(validated)
                return (user, validated)
            except Exception:
                pass  # fall through to header-based auth
        return super().authenticate(request)
