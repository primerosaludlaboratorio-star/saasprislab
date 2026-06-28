"""
⚠️ DEPRECATED: MODELOS LEGACY - ELIMINAR EN VERSIÓN 2.0 ⚠️

ESTE ARCHIVO CONTIENE MODELOS OBSOLETOS:

❌ consultorio.models.legacy.ConsultaMedica -> USE core.models.ConsultaMedica

MIGRACIÓN REQUERIDA:
1. Usar core.models.ConsultaMedica para todo nuevo desarrollo
2. Migrar datos existentes con comando: python manage.py migrate_legacy_consultas
3. Eliminar este archivo después de migración

REFERENCIAS ACTUALIZADAS:
- ConsultaMedica: from core.models import ConsultaMedica
- AgendaCita: from consultorio.models.agenda import AgendaCita (ACTIVO)
"""
import warnings
warnings.warn(
    "⚠️ CRÍTICO: consultorio.models.legacy está OBSOLETO. "
    "Use core.models.ConsultaMedica inmediatamente. "
    "Este archivo será eliminado en v2.0",
    DeprecationWarning,
    stacklevel=2
)

from django.conf import settings
from django.db import models

from .agenda import AgendaCita


class ConsultaMedica(models.Model):
    """
    ⚠️ DEPRECATED: MODELO LEGACY - NO USAR PARA NUEVAS FUNCIONALIDADES ⚠️
    
    MODELO ACTIVO: core.models.ConsultaMedica (con campos SOAP completos)
    
    Este modelo se mantiene ÚNICAMENTE para compatibilidad con migraciones existentes.
    Todas las vistas del consultorio YA usan core.ConsultaMedica.
    
    CAMBIOS REQUERIDOS:
    - from core.models import ConsultaMedica
    - Eliminar cualquier referencia a consultorio.models.legacy.ConsultaMedica
    """
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="consultas_medicas")
    sucursal = models.ForeignKey("core.Sucursal", on_delete=models.SET_NULL, null=True, blank=True, related_name="consultas_medicas")

    cita = models.OneToOneField(AgendaCita, on_delete=models.CASCADE, related_name="consulta", null=True, blank=True)
    paciente = models.ForeignKey("core.Paciente", on_delete=models.PROTECT, related_name="consultas_medicas")
    medico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="consultas_realizadas")

    motivo = models.TextField(blank=True, null=True)
    exploracion_fisica = models.TextField(blank=True, null=True)
    diagnostico_cie10 = models.CharField(max_length=30, blank=True, null=True, help_text="Código CIE-10 (ej. E11)")
    diagnostico_texto = models.TextField(blank=True, null=True)
    tratamiento = models.TextField(blank=True, null=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Consulta Médica (LEGACY)"
        verbose_name_plural = "Consultas Médicas (LEGACY)"
        ordering = ["-fecha_creacion"]

    def __str__(self) -> str:
        return f"[LEGACY] Consulta {self.paciente} ({self.fecha_creacion:%Y-%m-%d})"
