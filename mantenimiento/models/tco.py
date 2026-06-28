"""
CMMS V8.0 — Tco
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid
import hashlib
import logging



from .gemelo import ExpedienteEquipo
from .gemelo import ExpedienteEquipo

# =============================================================================
# SUBSISTEMA D — TCO Y WAR ROOM
# =============================================================================

class RegistroTCO(models.Model):
    """
    Registro mensual de Costo Total de Propiedad por equipo.
    Generado por management command mensual (o Celery).
    Alimenta el panel del War Room del Director.
    """
    empresa      = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="registros_tco",
    )
    expediente   = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.PROTECT,
        related_name="registros_tco",
    )
    periodo_mes  = models.PositiveSmallIntegerField(verbose_name="Mes")
    periodo_anio = models.PositiveSmallIntegerField(verbose_name="Año")

    # Métricas del período
    costo_refacciones   = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name="Costo en Refacciones ($)",
    )
    horas_inactividad   = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="Horas de Inactividad",
    )
    pruebas_procesadas  = models.PositiveIntegerField(
        default=0, verbose_name="Pruebas procesadas en el período",
    )
    tickets_abiertos    = models.PositiveSmallIntegerField(default=0)
    tickets_resueltos   = models.PositiveSmallIntegerField(default=0)
    tiempo_resolucion_promedio_min = models.PositiveIntegerField(default=0)

    # Métrica calculada
    costo_por_prueba    = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        verbose_name="Costo por Prueba ($)",
        help_text="costo_refacciones / pruebas_procesadas",
    )

    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro TCO"
        verbose_name_plural = "Registros TCO"
        unique_together = [('empresa', 'expediente', 'periodo_mes', 'periodo_anio')]
        ordering = ['-periodo_anio', '-periodo_mes']

    def __str__(self):
        return (f"TCO {self.expediente.equipo} — "
                f"{self.periodo_mes:02d}/{self.periodo_anio}")

    def calcular_costo_por_prueba(self):
        if self.pruebas_procesadas > 0:
            self.costo_por_prueba = self.costo_refacciones / self.pruebas_procesadas
        else:
            self.costo_por_prueba = 0
        self.save(update_fields=['costo_por_prueba'])


