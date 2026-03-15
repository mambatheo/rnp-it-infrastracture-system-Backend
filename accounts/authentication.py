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
