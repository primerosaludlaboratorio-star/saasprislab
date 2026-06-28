"""
CMMS V8.0 — Ejecucion
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
from .biblioteca import ProtocoloEquipo, PasoProtocolo, NodoDiagnostico, ProcedimientoReparacion, PasoReparacion

# =============================================================================
# SUBSISTEMA B — EJECUCIÓN Y TRAZABILIDAD
# =============================================================================

class EjecucionProtocolo(models.Model):
    """
    Instancia de ejecución de un ProtocoloEquipo por un usuario específico.
    Registro forense completo: quién, cuándo, desde qué IP.
    """
    ESTADO_CHOICES = [
        ('EN_PROGRESO', 'En Progreso'),
        ('COMPLETADO',  'Completado'),
        ('ABANDONADO',  'Abandonado'),
        ('BYPASS',      'Completado con Bypass de Supervisor'),
    ]

    protocolo    = models.ForeignKey(
        ProtocoloEquipo, on_delete=models.PROTECT,
        related_name="ejecuciones",
    )
    expediente   = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.PROTECT,
        related_name="ejecuciones",
    )
    empresa      = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="ejecuciones_protocolo",
    )
    ejecutado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="ejecuciones_protocolo",
    )
    fecha_inicio  = models.DateTimeField(auto_now_add=True)
    fecha_fin     = models.DateTimeField(null=True, blank=True)
    estado        = models.CharField(
        max_length=15, choices=ESTADO_CHOICES, default='EN_PROGRESO',
    )
    ip_address    = models.GenericIPAddressField(null=True, blank=True)
    duracion_real_seg = models.PositiveIntegerField(
        default=0, verbose_name="Duración real (segundos)",
    )

    class Meta:
        verbose_name = "Ejecución de Protocolo"
        verbose_name_plural = "Ejecuciones de Protocolos"
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['empresa', '-fecha_inicio']),
            models.Index(fields=['ejecutado_por', '-fecha_inicio']),
            models.Index(fields=['expediente', '-fecha_inicio']),
        ]

    def __str__(self):
        return f"{self.protocolo.nombre} — {self.ejecutado_por} [{self.get_estado_display()}]"

    def completar(self):
        self.fecha_fin = timezone.now()
        delta = self.fecha_fin - self.fecha_inicio
        self.duracion_real_seg = int(delta.total_seconds())
        self.estado = 'COMPLETADO'
        self.save(update_fields=['fecha_fin', 'duracion_real_seg', 'estado'])


class RespuestaPasoProtocolo(models.Model):
    """Respuesta capturada para un PasoProtocolo dentro de una EjecucionProtocolo."""
    ejecucion      = models.ForeignKey(
        EjecucionProtocolo, on_delete=models.CASCADE,
        related_name="respuestas",
    )
    paso           = models.ForeignKey(
        PasoProtocolo, on_delete=models.CASCADE,
        related_name="respuestas",
    )
    validado       = models.BooleanField(default=False)
    respuesta_texto = models.CharField(max_length=500, blank=True)
    respuesta_valor = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True,
    )
    foto           = models.ImageField(
        upload_to="mantenimiento/respuestas/", blank=True, null=True,
    )
    observacion    = models.CharField(max_length=500, blank=True)
    timestamp      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Respuesta de Paso"
        verbose_name_plural = "Respuestas de Pasos"
        unique_together = [('ejecucion', 'paso')]

    def __str__(self):
        return f"Paso {self.paso.orden} — {'✓' if self.validado else '✗'}"


class BypassChecklistAutorizacion(models.Model):
    """
    ── Ajuste 3: BOTÓN DE EMERGENCIA / SUPERVISIÓN DIRECTA ──
    Permite a un experto (supervisor) autorizar que un novato
    omita el checklist completo, registrando quién autorizó.
    El nivel del autorizante debe ser mayor al del ejecutante.
    """
    ejecucion    = models.OneToOneField(
        EjecucionProtocolo, on_delete=models.CASCADE,
        related_name="bypass_autorizacion",
    )
    ejecutado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="bypasses_recibidos", verbose_name="Novato / Ejecutante",
    )
    autorizado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="bypasses_otorgados", verbose_name="Supervisor Autorizante",
    )
    motivo        = models.TextField(
        verbose_name="Motivo de la omisión",
        help_text="Ej: 'Urgencia clínica', 'Paciente crítico en espera'",
    )
    pin_verificado = models.BooleanField(
        default=False, verbose_name="PIN del supervisor verificado",
    )
    fecha         = models.DateTimeField(auto_now_add=True)
    ip_autorizacion = models.GenericIPAddressField(null=True, blank=True)
    pasos_omitidos  = models.PositiveSmallIntegerField(
        default=0, verbose_name="Cantidad de pasos omitidos",
    )

    class Meta:
        verbose_name = "Bypass de Checklist (Supervisión Directa)"
        verbose_name_plural = "Bypasses de Checklists"
        ordering = ['-fecha']

    def __str__(self):
        return (f"Bypass: {self.ejecutado_por} autorizado por "
                f"{self.autorizado_por} [{self.fecha.date()}]")


