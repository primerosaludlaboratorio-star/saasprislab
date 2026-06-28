from django.apps import AppConfig


class LimsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lims'
    verbose_name = 'LIMS — Laboratorio Clínico'

    def ready(self):
        from lims import signals  # noqa: F401
