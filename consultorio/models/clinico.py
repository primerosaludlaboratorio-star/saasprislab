"""
DEPRECATED: Este archivo sera eliminado en version 2.0
Usar modelos de core en su lugar.
"""

import warnings
warnings.warn(
    f"{__name__} is deprecated. Use core models instead.",
    DeprecationWarning,
    stacklevel=2
)

"""
Modelos clínicos: somatometría, notas médicas y análisis de patrones.
"""
from django.conf import settings
from django.db import models

from .legacy import ConsultaMedica


class Somatometria(models.Model):
    consulta = models.OneToOneField(ConsultaMedica, on_delete=models.CASCADE, related_name="somatometria")

    peso = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    talla = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="En metros o cm (definir estándar).")
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    presion_arterial = models.CharField(max_length=20, null=True, blank=True, help_text="Ej: 120/80")
    sato2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Somatometría"
        verbose_name_plural = "Somatometrías"
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"Somatometría ({self.consulta_id})"


class NotaMedica(models.Model):
    """Nota médica / historia clínica (placeholder inicial)."""
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="notas_medicas")
    sucursal = models.ForeignKey("core.Sucursal", on_delete=models.SET_NULL, null=True, blank=True, related_name="notas_medicas")
    paciente = models.ForeignKey("core.Paciente", on_delete=models.PROTECT, related_name="notas_medicas")
    medico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="notas_medicas")

    titulo = models.CharField(max_length=200, default="Nota médica")
    contenido = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nota Médica"
        verbose_name_plural = "Notas Médicas"
        ordering = ["-fecha_creacion"]


class AnalisisPatron(models.Model):
    """
    Análisis de patrones de consulta con IA (CONFIDENCIAL Y ANÓNIMO).
    Los datos se anonimizan: no se vinculan a pacientes individuales.
    Solo contiene métricas agregadas y insights para mejora continua.
    """
    TIPO_CHOICES = [
        ('DIAGNOSTICO', 'Patrones de Diagnóstico'),
        ('TRATAMIENTO', 'Eficacia de Tratamientos'),
        ('CONVERSION', 'Conversión de Servicios (Cirugías, Procedimientos)'),
        ('RETENCION', 'Retención de Pacientes'),
        ('PRODUCTIVIDAD', 'Productividad del Consultorio'),
        ('FINANCIERO', 'Análisis Financiero Anónimo'),
    ]

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    periodo_inicio = models.DateField(verbose_name="Inicio del período")
    periodo_fin = models.DateField(verbose_name="Fin del período")

    # Datos ANONIMIZADOS (no vinculan pacientes)
    total_consultas = models.IntegerField(default=0)
    datos_json = models.JSONField(
        default=dict,
        verbose_name="Datos anónimos del análisis",
        help_text="Estructura JSON con métricas agregadas"
    )

    # Resultado IA
    analisis_ia = models.TextField(
        blank=True,
        verbose_name="Análisis generado por IA",
        help_text="Insights y patrones detectados"
    )
    recomendaciones = models.TextField(
        blank=True,
        verbose_name="Recomendaciones de mejora"
    )

    # Control
    confidencial = models.BooleanField(
        default=True,
        verbose_name="Datos confidenciales",
        help_text="Siempre True: los datos son anónimos y confidenciales"
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='analisis_patrones_generados'
    )

    class Meta:
        verbose_name = "Análisis de Patrón"
        verbose_name_plural = "Análisis de Patrones"
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f"{self.get_tipo_display()} ({self.periodo_inicio} - {self.periodo_fin})"
