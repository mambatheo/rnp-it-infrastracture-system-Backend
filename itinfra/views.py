from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API root endpoint"""
    return JsonResponse({
        'message': 'IT Infrastructure Management System API',
        'version': '1.0.0',
        'endpoints': {
            'authentication': '/api/accounts/',
            'equipment': '/api/equipment/',
            'maintenance': '/api/maintenance/',
            'admin': '/admin/',
        },
        'documentation': 'See API endpoints above for available resources',
    })