"""
Custom middleware to ensure CORS headers are always set for API requests
This works alongside django-cors-headers to ensure headers are set even if the main middleware fails
"""
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class EnhancedCorsMiddleware(MiddlewareMixin):
    """
    Enhanced CORS middleware that ensures headers are always set for API requests
    This is a fallback in case django-cors-headers doesn't set headers properly
    """
    def process_response(self, request, response):
        # Only process API requests
        if not request.path.startswith('/api/'):
            return response
        
        # Get origin from request
        origin = request.META.get('HTTP_ORIGIN', '')
        if not origin:
            return response
        
        # Check if origin is allowed
        allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        allow_all = getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False)
        
        # Set CORS headers if origin is allowed or if we allow all origins
        should_allow = allow_all or origin in allowed_origins
        
        if should_allow:
            # Only set if not already set by django-cors-headers
            if 'Access-Control-Allow-Origin' not in response:
                if allow_all:
                    response['Access-Control-Allow-Origin'] = origin
                elif origin in allowed_origins:
                    response['Access-Control-Allow-Origin'] = origin
            
            # Set credentials header
            if getattr(settings, 'CORS_ALLOW_CREDENTIALS', False):
                response['Access-Control-Allow-Credentials'] = 'true'
            
            # Handle preflight OPTIONS requests
            if request.method == 'OPTIONS':
                allowed_methods = getattr(settings, 'CORS_ALLOW_METHODS', ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
                allowed_headers = getattr(settings, 'CORS_ALLOW_HEADERS', ['content-type', 'authorization', 'x-csrftoken'])
                
                if 'Access-Control-Allow-Methods' not in response:
                    response['Access-Control-Allow-Methods'] = ', '.join(allowed_methods)
                if 'Access-Control-Allow-Headers' not in response:
                    response['Access-Control-Allow-Headers'] = ', '.join(allowed_headers)
                response['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return response

