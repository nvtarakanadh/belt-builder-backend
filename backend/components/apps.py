from django.apps import AppConfig
from django.db.models.signals import post_save


class ComponentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'components'

    def ready(self):
        from .signals import handle_component_post_save

