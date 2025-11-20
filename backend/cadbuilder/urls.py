"""
URL configuration for cadbuilder project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from .views import health_check, api_root, csrf_token
from .auth_views import RegisterView, LoginView, LogoutView, CurrentUserView
from .media_views import serve_media_with_cors

urlpatterns = [
    # Root and health check
    path('', api_root, name='api-root'),
    path('health/', health_check, name='health-check'),
    path('api/csrf/', csrf_token, name='csrf-token'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Authentication endpoints
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/user/', CurrentUserView.as_view(), name='current-user'),
    
    # API endpoints
    path('api/', include('components.urls')),
    path('api/', include('projects.urls')),
    path('api/', include('converter.urls')),  # STEP to GLB converter
    
    # Media files with CORS support
    re_path(r'^media/(?P<path>.*)$', serve_media_with_cors, name='media'),
]

# Serve media files in development (fallback if custom view doesn't work)
# The custom view above should handle this, but keep as fallback
if settings.DEBUG:
    # Only add if not already handled by custom view
    pass

