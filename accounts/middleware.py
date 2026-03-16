from django.http import JsonResponse

class ForcePasswordChangeMiddleware:
    EXEMPT_PATHS = [
        '/accounts/auth/login/',
        '/accounts/auth/logout/',
        '/accounts/auth/refresh/',
        '/accounts/users/change_password/',
         '/admin/',
         '/admin',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if (
            request.user.is_authenticated and getattr(request.user, 'is_first_login', False)
            and request.path not in self.EXEMPT_PATHS
        ):
            return JsonResponse({
                'error': 'password_change_required',
                'message': 'You must change your password before continuing'
            }, status=403)

        return self.get_response(request)