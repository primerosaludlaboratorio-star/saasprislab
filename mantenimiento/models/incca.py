"""
CMMS V8.0 — Incca
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
# SUBSISTEMA G — INTERFACES LIS: InCCA (CSV Folder Drop)
# =============================================================================


class InCCAInterfaceConfig(models.Model):
    """Configuración de conectividad InCCA por carpetas (CSV bidireccional)."""

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="incca_configs",
        verbose_name="Empresa",
    )
    expediente = models.OneToOneField(
        ExpedienteEquipo,
        on_delete=models.CASCADE,
        related_name="incca_config",
        verbose_name="Equipo (Expediente)",
    )

    habilitado = models.BooleanField(default=False, verbose_name="Habilitado")

    # InCCA Registry defaults:
    # INPUTFILTER (*.csv) / INPUTPATH (input) / OUTPUTPATH (output) / OUTPUTPREFIX (hostq_)
    input_path = models.CharField(max_length=500, blank=True, default="input", verbose_name="Carpeta INPUT")
    output_path = models.CharField(max_length=500, blank=True, default="output", verbose_name="Carpeta OUTPUT")
    input_filter = models.CharField(max_length=100, blank=True, default="*.csv", verbose_name="Filtro INPUT")
    output_prefix = models.CharField(max_length=100, blank=True, default="hostq_", verbose_name="Prefijo OUTPUT")
    dont_delete_input = models.BooleanField(default=True, verbose_name="No borrar INPUT")

    # Operación
    poll_interval_sec = models.PositiveIntegerField(default=60, verbose_name="Intervalo de polling (seg)")
    last_inputdate_seen = models.DateTimeField(null=True, blank=True, verbose_name="Último INPUTDATE observado")
    last_output_scan = models.DateTimeField(null=True, blank=True, verbose_name="Último escaneo OUTPUT")

    # Trazabilidad
    creado_por = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incca_configs_creadas",
        verbose_name="Creado por",
    )
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Config InCCA (CSV)"
        verbose_name_plural = "Configs InCCA (CSV)"
        indexes = [
            models.Index(fields=["empresa", "habilitado"]),
        ]

    def __str__(self):
        return f"InCCA: {self.expediente.equipo} [{self.empresa}]"


class InCCAFileEvent(models.Model):
    """Bitácora de archivos procesados para idempotencia y auditoría forense."""

    DIRECTION_CHOICES = [
        ("IN", "Input (LIS→InCCA)"),
        ("OUT", "Output (InCCA→LIS)"),
    ]
    STATUS_CHOICES = [
        ("DETECTADO", "Detectado"),
        ("PROCESADO", "Procesado"),
        ("ERROR", "Error"),
        ("IGNORADO", "Ignorado"),
    ]

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="incca_file_events",
        verbose_name="Empresa",
    )
    config = models.ForeignKey(
        InCCAInterfaceConfig,
        on_delete=models.CASCADE,
        related_name="file_events",
        verbose_name="Config",
    )

    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES, default="OUT")
    filename = models.CharField(max_length=260, verbose_name="Archivo")
    full_path = models.CharField(max_length=800, blank=True, default="", verbose_name="Ruta completa")
    file_mtime = models.DateTimeField(null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)

    sha256 = models.CharField(max_length=64, blank=True, default="", db_index=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="DETECTADO")
    error = models.TextField(blank=True, default="")
    raw_preview = models.TextField(blank=True, default="")

    detected_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Evento InCCA (archivo)"
        verbose_name_plural = "Eventos InCCA (archivos)"
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["empresa", "direction", "status", "-detected_at"]),
            models.Index(fields=["config", "direction", "filename"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["config", "direction", "filename", "sha256"],
                name="mantenimiento_incca_fileevent_config_dir_file_hash_uniq",
            )
        ]

    def __str__(self):
        return f"{self.get_direction_display()} {self.filename} ({self.status})"

    @staticmethod
    def compute_sha256_bytes(b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()


class InCCAOutputRowStaging(models.Model):
    """Staging de filas de salida InCCA (CSV) aún no mapeadas 1:1 a Orden/Estudio."""

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="incca_output_rows",
        verbose_name="Empresa",
    )
    file_event = models.ForeignKey(
        InCCAFileEvent,
        on_delete=models.CASCADE,
        related_name="rows",
        verbose_name="Archivo",
    )

    row_index = models.PositiveIntegerField(default=0)
    process_number = models.CharField(max_length=80, blank=True, default="")
    order_number = models.CharField(max_length=80, blank=True, default="", db_index=True)
    method_name = models.CharField(max_length=200, blank=True, default="")
    pid = models.CharField(max_length=120, blank=True, default="")
    report = models.TextField(blank=True, default="")
    raw_fields_json = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fila InCCA (staging)"
        verbose_name_plural = "Filas InCCA (staging)"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["empresa", "order_number", "-created_at"]),
        ]

    def __str__(self):
        return f"InCCA row order={self.order_number} method={self.method_name}"
