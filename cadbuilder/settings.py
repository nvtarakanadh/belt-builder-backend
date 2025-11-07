"""
Django settings for cadbuilder project.
"""

from pathlib import Path
import os

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
# Support Railway's DATABASE_URL format
import dj_database_url

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Railway provides DATABASE_URL in format: postgresql://user:pass@host:port/dbname
    # Parse and configure database from DATABASE_URL
    db_config = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
    DATABASES = {
        'default': db_config
    }
    # Ensure we're using PostgreSQL
    if 'ENGINE' not in db_config or 'postgresql' not in db_config.get('ENGINE', ''):
        # Force PostgreSQL if DATABASE_URL is provided
        db_config['ENGINE'] = 'django.db.backends.postgresql'
        DATABASES['default'] = db_config
elif os.environ.get('USE_POSTGRES', 'False') == 'True':
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
else:
    # Default to SQLite for easier development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

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

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Allow unauthenticated access for development
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Empty for development - no authentication required
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

# GLB/GLTF File Settings - Only GLB/GLTF files are accepted (direct upload, no conversion)
GLB_UPLOAD_MAX_SIZE = 100 * 1024 * 1024  # 100 MB
GLB_ALLOWED_EXTENSIONS = ['.glb', '.gltf']
# Backward compatibility
CAD_UPLOAD_MAX_SIZE = GLB_UPLOAD_MAX_SIZE
CAD_ALLOWED_EXTENSIONS = GLB_ALLOWED_EXTENSIONS

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

