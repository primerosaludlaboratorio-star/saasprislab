from django.apps import AppConfig


class InventarioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventario"
    verbose_name = "Inventario (Silos Federados)"

    def ready(self):
        import inventario.signals  # noqa: F401 — conectar señales FEFO
