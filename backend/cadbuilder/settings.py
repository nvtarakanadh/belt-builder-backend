"""
Django settings for cadbuilder project.
"""

from pathlib import Path
import os
import sys

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

# Add custom Python packages to path if specified (for local development)
# This is optional and only used if the path exists
custom_packages_path = os.environ.get('CUSTOM_PYTHON_PACKAGES_PATH')
if custom_packages_path and os.path.exists(custom_packages_path) and custom_packages_path not in sys.path:
    sys.path.insert(0, custom_packages_path)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production-!!!')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Parse ALLOWED_HOSTS from environment variable
allowed_hosts_str = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',') if host.strip()]

# Add Railway's default domain if RAILWAY_PUBLIC_DOMAIN is set
if os.environ.get('RAILWAY_PUBLIC_DOMAIN'):
    ALLOWED_HOSTS.append(os.environ.get('RAILWAY_PUBLIC_DOMAIN'))

# Add Railway's service URL if available
if os.environ.get('RAILWAY_STATIC_URL'):
    from urllib.parse import urlparse
    parsed = urlparse(os.environ.get('RAILWAY_STATIC_URL'))
    if parsed.hostname:
        ALLOWED_HOSTS.append(parsed.hostname)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    'components',
    'projects',
    'cad_processing',
    'converter',  # STEP to GLB converter API
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cadbuilder.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cadbuilder.wsgi.application'

# Database
# Support Railway's DATABASE_URL format and PostgreSQL service linking
import dj_database_url

# Railway provides DATABASE_URL when a PostgreSQL service is linked
# Also check for Railway's PostgreSQL service variables
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

# If no DATABASE_URL, check for individual PostgreSQL environment variables (Railway format)
if not DATABASE_URL:
    pg_host = os.environ.get('PGHOST')
    pg_port = os.environ.get('PGPORT')
    pg_user = os.environ.get('PGUSER')
    pg_password = os.environ.get('PGPASSWORD')
    pg_database = os.environ.get('PGDATABASE')
    
    if all([pg_host, pg_port, pg_user, pg_password, pg_database]):
        # Construct DATABASE_URL from Railway PostgreSQL service variables
        DATABASE_URL = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

if DATABASE_URL:
    # Railway/Neon provides DATABASE_URL in format: postgresql://user:pass@host:port/dbname?sslmode=require
    # Parse and configure database from DATABASE_URL
    try:
        db_config = dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,  # Require SSL for Neon and other cloud databases
        )
        DATABASES = {
            'default': db_config
        }
        # Ensure we're using PostgreSQL
        if 'ENGINE' not in db_config or 'postgresql' not in db_config.get('ENGINE', ''):
            # Force PostgreSQL if DATABASE_URL is provided
            db_config['ENGINE'] = 'django.db.backends.postgresql'
            DATABASES['default'] = db_config
        
        # Add SSL configuration for Neon and other cloud databases
        if 'OPTIONS' not in DATABASES['default']:
            DATABASES['default']['OPTIONS'] = {}
        DATABASES['default']['OPTIONS']['sslmode'] = 'require'
        
        print(f"[OK] Database configured from DATABASE_URL: {db_config.get('HOST', 'unknown')}/{db_config.get('NAME', 'unknown')}")
    except Exception as e:
        print(f"[WARNING] Error parsing DATABASE_URL: {e}")
        # Fall back to manual configuration
        DATABASE_URL = None

if not DATABASE_URL:
    if os.environ.get('USE_POSTGRES', 'False') == 'True':
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ.get('DB_NAME', 'cadbuilder'),
                'USER': os.environ.get('DB_USER', 'postgres'),
                'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
                'HOST': os.environ.get('DB_HOST', 'localhost'),
                'PORT': os.environ.get('DB_PORT', '5432'),
                'OPTIONS': {
                    'connect_timeout': 10,
                },
            }
        }
        print(f"[OK] Database configured from individual environment variables: {os.environ.get('DB_HOST', 'localhost')}")
    else:
        # Default to SQLite for easier development
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
        print("[WARNING] Using SQLite database (not recommended for production)")

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (uploaded CAD files)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File storage settings
USE_S3 = os.environ.get('USE_S3', 'False') == 'True'
if USE_S3:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "https://belt-builder.vercel.app",
]

# Add frontend URL from environment if provided
frontend_url = os.environ.get('FRONTEND_URL', 'https://belt-builder.vercel.app')
if frontend_url and frontend_url not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(frontend_url)

# For Railway preview deployments, allow all origins
CORS_ALLOW_ALL_ORIGINS = os.environ.get('RAILWAY_ENVIRONMENT') == 'true' or DEBUG
CORS_ALLOW_CREDENTIALS = True

# CSRF settings - trust the same origins as CORS
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()
if frontend_url and frontend_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(frontend_url)

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Allow unauthenticated access for development
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    # Disable CSRF for API views (handled by DRF)
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

# API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'CAD Builder API',
    'DESCRIPTION': 'API for CAD-based engineering builder platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Celery Configuration (optional)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# CAD File Settings - Supports GLB/GLTF, STEP, STL, OBJ
# STEP files are converted using FreeCAD Docker (deployment-friendly)
CAD_UPLOAD_MAX_SIZE = 100 * 1024 * 1024  # 100 MB
CAD_ALLOWED_EXTENSIONS = ['.glb', '.gltf', '.step', '.stp', '.stl', '.obj']
# Backward compatibility
GLB_UPLOAD_MAX_SIZE = CAD_UPLOAD_MAX_SIZE
GLB_ALLOWED_EXTENSIONS = ['.glb', '.gltf']

# STEP File Conversion Settings - FreeCAD Docker (deployment-friendly)
# Option 1: Use FreeCAD Docker container via HTTP API
FREECAD_DOCKER_URL = os.environ.get('FREECAD_DOCKER_URL', None)  # e.g., 'http://freecad-service:8001'
# Option 2: Use FreeCAD Docker container via subprocess (requires Docker)
FREECAD_DOCKER_IMAGE = os.environ.get('FREECAD_DOCKER_IMAGE', 'freecad-converter:latest')

# CloudConvert API for STEP conversion
# Set CLOUDCONVERT_API_KEY environment variable
CLOUDCONVERT_API_KEY = os.environ.get('CLOUDCONVERT_API_KEY', None)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

