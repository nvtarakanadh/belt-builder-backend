"""
Custom view for serving media files with CORS headers
"""
from django.views.static import serve
from django.conf import settings
from django.http import HttpResponse, Http404
import os


def serve_media_with_cors(request, path):
    """
    Serve media files with CORS headers enabled
    This ensures GLB files and other media can be loaded from the frontend
    """
    # Get origin from request
    origin = request.META.get('HTTP_ORIGIN', '')
    
    # Check if origin is allowed
    allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
    allow_all = getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False)
    
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        response = HttpResponse()
        should_allow = allow_all or origin in allowed_origins
        if should_allow and origin:
            if allow_all:
                response['Access-Control-Allow-Origin'] = origin
            elif origin in allowed_origins:
                response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Range'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'
        return response
    
    # Serve the file using Django's static file serving
    try:
        response = serve(request, path, document_root=settings.MEDIA_ROOT)
    except Http404:
        raise
    
    # Add CORS headers if origin is allowed
    should_allow = allow_all or origin in allowed_origins
    
    if should_allow and origin:
        if allow_all:
            response['Access-Control-Allow-Origin'] = origin
        elif origin in allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
        
        # Set credentials header
        if getattr(settings, 'CORS_ALLOW_CREDENTIALS', False):
            response['Access-Control-Allow-Credentials'] = 'true'
        
        # Allow all methods for media files
        response['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
        response['Access-Control-Expose-Headers'] = 'Content-Type, Content-Length, Content-Range, Accept-Ranges'
    
    return response

