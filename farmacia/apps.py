"""
Configuración de la app Farmacia
"""
from django.apps import AppConfig


class FarmaciaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'farmacia'
    verbose_name = 'Farmacia (Gestión de Activos)'
    
    def ready(self):
        """Registrar signals si existen."""
        try:
            import farmacia.signals
        except ImportError:
            pass
