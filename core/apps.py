from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        """Registrar signals cuando la app está lista."""
        from core.django_template_context_patch import apply_if_needed

        apply_if_needed()

        import core.signals  # Importar signals para activar los decoradores

        # ── PRISLAB V5.4: Activar reorganización departamental del Admin ─────
        # Reemplazamos la CLASE de admin.site (no la instancia) para que todos
        # los modelos ya registrados con @admin.register sigan funcionando,
        # pero el menú lateral quede ordenado por Departamento Operativo.
        try:
            from django.contrib import admin
            from config.admin_site import PrislabAdminSite
            admin.site.__class__ = PrislabAdminSite
        except (ImportError, AttributeError):
            pass  # Nunca bloquear el arranque

        # Verificación de entorno al arranque (solo en producción)
        try:
            from production_env_check import verificar_y_loguear
            verificar_y_loguear()
        except ImportError:
            pass  # Módulo de verificación no disponible en este entorno