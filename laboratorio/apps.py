from django.apps import AppConfig


class LaboratorioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'laboratorio'
    verbose_name = 'Laboratorio Clínico'
    
    def ready(self):
        """
        Inicialización del módulo de laboratorio.
        
        PILAR 2 & 3: Carga signals para:
        - Historial automático de resultados (ISO 15189)
        - Sistema de permisos de privacidad (NOM-024)
        """
        # Importar signals (esto los registra automáticamente)
        try:
            import laboratorio.signals
            # Usar logger en lugar de print para evitar problemas de encoding
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Signals de laboratorio cargados correctamente")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error cargando signals de laboratorio: {str(e)}")

