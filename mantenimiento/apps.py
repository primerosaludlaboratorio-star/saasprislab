from django.apps import AppConfig


class MantenimientoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mantenimiento"
    verbose_name = "CMMS — Mantenimiento de Equipos"

    def ready(self):
        import mantenimiento.signals  # noqa: F401
