"""
CMMS V8.0 — Gemelo
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid
import hashlib
import logging

from .base import (
    SILO_ORIGEN_CHOICES,
    TIPO_EQUIPO_CHOICES,
    NIVEL_AUTORIZACION_CHOICES,
    TIPO_VALIDACION_PASO_CHOICES,
    TIPO_PROTOCOLO_CHOICES,
    TIPO_NODO_CHOICES,
    NIVEL_ESCALAMIENTO_CHOICES,
    TIPO_COMPONENTE_CHOICES,
    ESTADO_TICKET_CHOICES
)

# =============================================================================
# SUBSISTEMA C — GEMELO DIGITAL (Debe ir primero por dependencias)
# =============================================================================

class ExpedienteEquipo(models.Model):
    """
    Gemelo Digital del equipo físico.
    QR único → landing informativa + acceso rápido a protocolos.
    """
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="expedientes_equipo", verbose_name="Empresa",
    )
    equipo = models.ForeignKey(
        "laboratorio.Equipo", on_delete=models.CASCADE,
        related_name="expediente_cmms", verbose_name="Equipo",
    )
    tipo_equipo   = models.CharField(
        max_length=20, choices=TIPO_EQUIPO_CHOICES, default='ANALIZADOR',
        verbose_name="Tipo de Equipo",
    )
    silo_refacciones = models.CharField(
        max_length=15, choices=SILO_ORIGEN_CHOICES, default='LAB',
        verbose_name="Silo de Refacciones por Defecto",
        help_text="Silo de inventario del que se descontarán las refacciones. "
                  "Se puede cambiar manualmente en cada ticket.",
    )

    # Identificación física
    numero_serie     = models.CharField(max_length=120, blank=True, verbose_name="N° de Serie")
    modelo           = models.CharField(max_length=200, blank=True, verbose_name="Modelo")
    fabricante       = models.CharField(max_length=150, blank=True, verbose_name="Fabricante")
    foto_equipo      = models.ImageField(
        upload_to="mantenimiento/equipos/", blank=True, null=True,
        verbose_name="Foto del Equipo",
    )
    manual_pdf       = models.FileField(
        upload_to="mantenimiento/manuales/", blank=True, null=True,
        verbose_name="Manual PDF del Fabricante",
    )

    # Fechas clave
    fecha_instalacion        = models.DateField(null=True, blank=True, verbose_name="Fecha de Instalación")
    garantia_hasta           = models.DateField(null=True, blank=True, verbose_name="Garantía Hasta")
    fecha_ultima_calibracion = models.DateField(null=True, blank=True, verbose_name="Última Calibración")
    proxima_calibracion      = models.DateField(null=True, blank=True, verbose_name="Próxima Calibración")
    proxima_verificacion_prev= models.DateField(null=True, blank=True, verbose_name="Próximo Mant. Preventivo")

    # QR / NFC para acceso físico rápido
    qr_uid  = models.UUIDField(default=uuid.uuid4, unique=True, editable=False,
                               verbose_name="UID del código QR")
    codigo_nfc = models.CharField(max_length=120, blank=True, null=True,
                                  verbose_name="Código NFC (opcional)")

    # Estado operativo
    en_servicio = models.BooleanField(default=True, verbose_name="En Servicio")
    notas       = models.TextField(blank=True, verbose_name="Notas / Observaciones")

    class Meta:
        verbose_name = "Expediente de Equipo"
        verbose_name_plural = "Expedientes de Equipos"
        unique_together = [('empresa', 'equipo')]
        ordering = ['empresa', 'equipo__nombre']

    def __str__(self):
        return f"Expediente: {self.equipo} [{self.empresa}]"

    def get_qr_url(self):
        from django.urls import reverse
        return reverse('mantenimiento:qr_equipo', args=[str(self.qr_uid)])


