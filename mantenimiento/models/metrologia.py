"""
CMMS V8.0 — Metrologia
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

# =============================================================================
# SUBSISTEMA E — METROLOGÍA: Certificados de Calibración / Calificación IQ/OQ/PQ
# =============================================================================

class CertificadoMetrologia(models.Model):
    """
    Repositorio legal de certificados de calibración, calificación (IQ/OQ/PQ)
    y verificación de equipos de laboratorio.

    ISO 15189 §6.4.3 — Los equipos deben calibrarse o verificarse con intervalos
    definidos. Este modelo garantiza la trazabilidad documental exigida por
    COFEPRIS e ISO 15189 durante auditorías.

    Alertas automáticas: el management command `check_certificados_metrologicos`
    revisa diariamente y dispara NotificacionDiscrepancia al Director 30 días
    antes del vencimiento.
    """
    TIPO_CHOICES = [
        ('CALIBRACION',    'Calibración Metrológica'),
        ('CALIFICACION_IQ','Calificación de Instalación (IQ)'),
        ('CALIFICACION_OQ','Calificación de Operación (OQ)'),
        ('CALIFICACION_PQ','Calificación de Desempeño (PQ)'),
        ('VERIFICACION',   'Verificación Periódica'),
        ('MANTENIMIENTO_PREVENTIVO', 'Mantenimiento Preventivo Certificado'),
    ]
    ESTADO_CHOICES = [
        ('VIGENTE',  'Vigente'),
        ('POR_VENCER','Por Vencer (≤30 días)'),
        ('VENCIDO',  'Vencido'),
        ('RENOVADO', 'Renovado / Sustituido'),
    ]

    empresa    = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="certificados_metrologia", verbose_name="Empresa",
    )
    expediente = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.CASCADE,
        related_name="certificados", verbose_name="Equipo",
    )
    tipo           = models.CharField(max_length=30, choices=TIPO_CHOICES,
                                       verbose_name="Tipo de Certificado")
    numero_certificado = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Número / Folio del Certificado",
    )
    laboratorio_emisor = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Laboratorio / Entidad Emisora",
    )
    fecha_emision  = models.DateField(verbose_name="Fecha de Emisión")
    fecha_vencimiento = models.DateField(verbose_name="Fecha de Vencimiento")
    estado         = models.CharField(max_length=15, choices=ESTADO_CHOICES,
                                       default="VIGENTE", verbose_name="Estado")

    # Documento PDF del certificado
    archivo_pdf    = models.FileField(
        upload_to="metrologia/certificados/",
        blank=True, null=True, verbose_name="Archivo PDF del Certificado",
    )
    observaciones  = models.TextField(blank=True, null=True)

    # Trazabilidad
    registrado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="certificados_registrados", verbose_name="Registrado por",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Flag: ¿ya se envió la alerta de próximo vencimiento?
    alerta_30d_enviada = models.BooleanField(
        default=False,
        verbose_name="Alerta 30 días enviada",
        help_text="Marca automática del cron para evitar alertas duplicadas.",
    )

    class Meta:
        verbose_name = "Certificado de Metrología"
        verbose_name_plural = "Certificados de Metrología"
        ordering = ["fecha_vencimiento"]
        indexes = [
            models.Index(fields=["empresa", "estado", "fecha_vencimiento"]),
            models.Index(fields=["expediente", "tipo"]),
        ]

    def __str__(self):
        return (f"{self.get_tipo_display()} — {self.expediente.equipo} "
                f"| Vence: {self.fecha_vencimiento:%d/%m/%Y}")

    def actualizar_estado(self):
        """Actualiza el campo estado según fecha de vencimiento vs hoy."""
        from datetime import date
        hoy = date.today()
        if self.fecha_vencimiento < hoy:
            self.estado = 'VENCIDO'
        elif (self.fecha_vencimiento - hoy).days <= 30:
            self.estado = 'POR_VENCER'
        else:
            self.estado = 'VIGENTE'
        self.save(update_fields=['estado'])


