from functools import wraps
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Decorator to exempt CSRF for API views
csrf_exempt_api = method_decorator(csrf_exempt, name='dispatch')
