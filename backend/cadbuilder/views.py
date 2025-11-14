"""
Root view for health checks and API info
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'CAD Builder API',
        'version': '1.0.0'
    })


@require_http_methods(["GET"])
def api_root(request):
    """API root endpoint with links to available endpoints"""
    return JsonResponse({
        'message': 'CAD Builder API',
        'version': '1.0.0',
        'endpoints': {
            'components': '/api/components/',
            'projects': '/api/projects/',
            'api_docs': '/api/docs/',
            'admin': '/admin/',
        }
    })


@ensure_csrf_cookie
@require_http_methods(["GET"])
def csrf_token(request):
    """Get CSRF token for API requests"""
    token = get_token(request)
    return JsonResponse({'csrfToken': token})

