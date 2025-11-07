# CAD Builder Django Project

# Celery app initialization
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not configured
    pass
