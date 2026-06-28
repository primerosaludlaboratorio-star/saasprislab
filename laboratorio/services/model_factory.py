"""
Factory centralizado para acceso a modelos - ELIMINA DEPENDENCIAS LEGACY
⚠️ ESTE FACTORY SOLO RETORNA MODELOS CORE - NO USA LEGACY
"""

from django.apps import apps
import logging
import warnings

logger = logging.getLogger(__name__)

class ModelFactory:
    """Abstracción para acceso a modelos core - ELIMINA LEGACY"""

    @staticmethod
    def get_medico_model():
        """
        Retorna modelo Medico (core.Medico).
        ⚠️ NO USA laboratorio.Medico - ESTÁ OBSOLETO
        """
        try:
            return apps.get_model('core', 'Medico')
        except LookupError:
            raise ImportError(
                "❌ CRÍTICO: core.Medico no encontrado. "
                "Verificar que core esté instalado y migrado. "
                "NO se usará laboratorio.Medico (OBSOLETO)."
            )

    @staticmethod
    def get_orden_model():
        """
        Retorna modelo Orden (core.OrdenDeServicio).
        ⚠️ NO USA laboratorio.Orden - ESTÁ OBSOLETO
        """
        try:
            return apps.get_model('core', 'OrdenDeServicio')
        except LookupError:
            raise ImportError(
                "❌ CRÍTICO: core.OrdenDeServicio no encontrado. "
                "Verificar que core esté instalado y migrado. "
                "NO se usará laboratorio.Orden (OBSOLETO)."
            )

    @staticmethod
    def get_paciente_model():
        """
        Retorna modelo Paciente (core.Paciente).
        """
        try:
            return apps.get_model('core', 'Paciente')
        except LookupError:
            raise ImportError(
                "❌ CRÍTICO: core.Paciente no encontrado. "
                "Verificar que core esté instalado y migrado."
            )

    @staticmethod
    def get_detalle_orden_model():
        """
        Retorna modelo DetalleOrden (core.DetalleOrden).
        """
        try:
            return apps.get_model('core', 'DetalleOrden')
        except LookupError:
            raise ImportError(
                "❌ CRÍTICO: core.DetalleOrden no encontrado. "
                "Verificar que core esté instalado y migrado."
            )
