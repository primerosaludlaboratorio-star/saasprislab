"""
CMMS V8.0 — Tickets
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

from .gemelo import ExpedienteEquipo
from .biblioteca import ProtocoloEquipo, PasoProtocolo, NodoDiagnostico, ProcedimientoReparacion, PasoReparacion
from .ejecucion import EjecucionProtocolo

class TicketMantenimientoCMMS(models.Model):
    """
    Ticket central del CMMS.
    Creado automáticamente desde: checklist, árbol diagnóstico,
    alerta QC (Westgard), o manualmente por el Director.
    """
    TIPO_ORIGEN_CHOICES = [
        ('CHECKLIST',    'Detectado en Checklist Diario'),
        ('DIAGNOSTICO',  'Diagnóstico por Árbol de Decisión'),
        ('QC_TRIGGERED', 'Disparado por Falla en QC (Westgard)'),
        ('MANUAL',       'Creado Manualmente'),
        ('PREVENTIVO',   'Mantenimiento Preventivo Programado'),
    ]

    empresa       = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="tickets_cmms",
    )
    expediente    = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.PROTECT,
        related_name="tickets", null=True, blank=True,
    )
    tipo_origen   = models.CharField(
        max_length=15, choices=TIPO_ORIGEN_CHOICES, default='MANUAL',
    )
    titulo        = models.CharField(max_length=300, verbose_name="Título / Síntoma")
    descripcion   = models.TextField(blank=True, verbose_name="Descripción Detallada")
    estado        = models.CharField(
        max_length=15, choices=ESTADO_TICKET_CHOICES, default='ABIERTO',
    )
    nivel_escalamiento_actual = models.CharField(
        max_length=20, choices=NIVEL_ESCALAMIENTO_CHOICES,
        default='QUIMICO', verbose_name="Nivel de Escalamiento Actual",
    )
    autorizado_por_director = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets_autorizados_director",
        verbose_name="Director que autorizó escalamiento externo",
        help_text="Requerido solo si nivel_escalamiento = PROVEEDOR.",
    )

    # Vínculos a ejecuciones
    ejecucion_protocolo    = models.ForeignKey(
        EjecucionProtocolo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets_generados",
    )
    nodo_diagnostico_final = models.ForeignKey(
        NodoDiagnostico, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets_generados",
        verbose_name="Nodo final del árbol de diagnóstico",
    )

    creado_por    = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="tickets_cmms_creados", null=True, blank=True,
    )
    asignado_a    = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets_cmms_asignados",
    )
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre   = models.DateTimeField(null=True, blank=True)
    tiempo_resolucion_min = models.PositiveIntegerField(
        default=0, verbose_name="Tiempo de resolución (minutos)",
    )
    resolucion_descripcion = models.TextField(
        blank=True, verbose_name="Descripción de la Resolución",
    )

    class Meta:
        verbose_name = "Ticket de Mantenimiento (CMMS)"
        verbose_name_plural = "Tickets de Mantenimiento (CMMS)"
        ordering = ['-fecha_apertura']
        indexes = [
            models.Index(fields=['empresa', '-fecha_apertura']),
            models.Index(fields=['expediente', 'estado']),
        ]

    def __str__(self):
        return f"Ticket #{self.pk} — {self.titulo[:80]} [{self.get_estado_display()}]"

    def clean(self):
        # Regla de Autonomía: escalar a proveedor requiere firma de Director
        if self.nivel_escalamiento_actual == 'PROVEEDOR' and not self.autorizado_por_director_id:
            raise ValidationError(
                "No se puede escalar a Proveedor Externo sin autorización del Director."
            )

    def cerrar(self, descripcion_resolucion=""):
        self.estado = 'CERRADO'
        self.fecha_cierre = timezone.now()
        delta = self.fecha_cierre - self.fecha_apertura
        self.tiempo_resolucion_min = int(delta.total_seconds() / 60)
        self.resolucion_descripcion = descripcion_resolucion
        self.save(update_fields=[
            'estado', 'fecha_cierre',
            'tiempo_resolucion_min', 'resolucion_descripcion',
        ])


class SalidaRefaccionMantenimiento(models.Model):
    """
    ── Ajuste 1: MULTI-SILO via GenericForeignKey ──
    Descuento de refacción/insumo de CUALQUIER silo de inventario
    al ejecutar un mantenimiento.

    content_type puede apuntar a:
      - inventario.LoteReactivoLab      → Silo Lab
      - inventario.LoteInsumoConsultorio → Silo Consultorio
      - inventario.LoteInsumoGeneral    → Silo Generales

    La señal post_save descuenta automáticamente el stock del lote correcto.
    """
    empresa      = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="salidas_refaccion_mantenimiento",
    )
    ticket       = models.ForeignKey(
        TicketMantenimientoCMMS, on_delete=models.PROTECT,
        related_name="salidas_refaccion",
    )
    silo_origen  = models.CharField(
        max_length=15, choices=SILO_ORIGEN_CHOICES,
        verbose_name="Silo de Inventario",
    )

    # GenericFK al lote del silo correspondiente
    lote_content_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT,
        verbose_name="Tipo de Lote",
    )
    lote_object_id    = models.PositiveIntegerField(verbose_name="ID del Lote")
    lote              = GenericForeignKey('lote_content_type', 'lote_object_id')

    cantidad_usada    = models.DecimalField(
        max_digits=10, decimal_places=4,
        verbose_name="Cantidad Utilizada",
    )
    unidad            = models.CharField(max_length=20, blank=True)
    paso_reparacion   = models.ForeignKey(
        PasoReparacion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="salidas_registradas",
        verbose_name="Paso de reparación origen",
    )
    registrado_por    = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="salidas_refaccion_registradas",
    )
    fecha             = models.DateTimeField(auto_now_add=True)
    observacion       = models.CharField(max_length=300, blank=True)
    costo_unitario_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name="Costo Unitario Congelado"
    )
    costo_total_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Costo Total Congelado"
    )
    stock_anterior_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        verbose_name="Stock Anterior Congelado"
    )
    stock_resultante_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        verbose_name="Stock Resultante Congelado"
    )

    class Meta:
        verbose_name = "Salida de Refacción (Mantenimiento)"
        verbose_name_plural = "Salidas de Refacciones (Mantenimiento)"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['empresa', '-fecha']),
            models.Index(fields=['ticket']),
        ]

    def __str__(self):
        return (f"Refacción {self.cantidad_usada} [{self.silo_origen}] "
                f"— Ticket #{self.ticket_id}")


