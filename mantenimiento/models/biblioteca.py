"""
CMMS V8.0 — Biblioteca
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

# =============================================================================
# SUBSISTEMA A — BIBLIOTECA TÉCNICA
# =============================================================================

class ProtocoloEquipo(models.Model):
    """
    Protocolo de operación para un equipo específico.
    Se construye mediante el Wizard de Carga Visual del Director.
    """
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="protocolos_equipo", verbose_name="Empresa",
        null=True, blank=True,
        help_text="Null = protocolo global PRISLAB (plantilla para todos los tenants).",
    )
    equipo = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.CASCADE,
        related_name="protocolos", verbose_name="Equipo",
        null=True, blank=True,
        help_text="Null = protocolo aplica a todos los equipos del mismo modelo.",
    )
    modelo_equipo = models.CharField(
        max_length=200, blank=True,
        help_text="Si equipo=None, aplica a todos los equipos con este modelo.",
    )
    tipo_protocolo = models.CharField(
        max_length=25, choices=TIPO_PROTOCOLO_CHOICES,
        verbose_name="Tipo de Protocolo",
    )
    nombre       = models.CharField(max_length=250, verbose_name="Nombre del Protocolo")
    descripcion  = models.TextField(blank=True, verbose_name="Descripción")
    version      = models.CharField(max_length=20, default="1.0", verbose_name="Versión")
    activo       = models.BooleanField(default=True)
    nivel_requerido = models.CharField(
        max_length=20, choices=NIVEL_AUTORIZACION_CHOICES, default='TODOS',
        verbose_name="Nivel mínimo para ejecutar",
    )
    aplica_a_perfil = models.CharField(
        max_length=20, choices=NIVEL_AUTORIZACION_CHOICES, default='TODOS',
        verbose_name="Perfil al que aplica el BLOQUEO",
        help_text="Usuarios en este perfil o inferior serán bloqueados si no "
                  "completan este protocolo antes de acceder a la Worklist.",
    )
    bloquea_worklist = models.BooleanField(
        default=False, verbose_name="Bloquea Worklist si no se completa",
        help_text="Activo = Worklist bloqueada hasta completar este checklist hoy.",
    )
    periodicidad_dias = models.PositiveIntegerField(
        default=1, verbose_name="Periodicidad (días)",
        help_text="1=diario, 7=semanal, 30=mensual. 0=sin periodicidad.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Protocolo de Equipo"
        verbose_name_plural = "Protocolos de Equipos"
        ordering = ['equipo__equipo__nombre', 'tipo_protocolo', 'nombre']

    def __str__(self):
        equipo_str = str(self.equipo) if self.equipo else self.modelo_equipo or "Global"
        return f"[{self.get_tipo_protocolo_display()}] {self.nombre} — {equipo_str}"


class PasoProtocolo(models.Model):
    """
    Paso individual dentro de un ProtocoloEquipo.
    Construido desde el Wizard visual.
    """
    protocolo      = models.ForeignKey(
        ProtocoloEquipo, on_delete=models.CASCADE,
        related_name="pasos", verbose_name="Protocolo",
    )
    orden          = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")
    titulo         = models.CharField(max_length=250, verbose_name="Título del Paso")
    instruccion    = models.TextField(verbose_name="Instrucción Detallada")
    tipo_validacion= models.CharField(
        max_length=15, choices=TIPO_VALIDACION_PASO_CHOICES, default='CHECKBOX',
        verbose_name="Tipo de Validación",
    )
    valor_esperado = models.CharField(
        max_length=100, blank=True,
        help_text="Ej: '36-38°C', '>500 rpm'. Si el usuario registra otro valor, se genera alerta.",
    )
    imagen         = models.ImageField(
        upload_to="mantenimiento/pasos/", blank=True, null=True,
        verbose_name="Imagen / Captura del Manual",
    )
    video_url      = models.URLField(blank=True, null=True, verbose_name="URL de video (YouTube/Drive)")
    es_critico     = models.BooleanField(
        default=False, verbose_name="Es Crítico",
        help_text="Si falla, bloquea la ejecución del protocolo.",
    )
    tiempo_estimado_seg = models.PositiveIntegerField(
        default=30, verbose_name="Tiempo estimado (segundos)",
    )
    nota_seguridad = models.CharField(
        max_length=500, blank=True, verbose_name="Nota de Seguridad",
        help_text="EPP requerido, riesgo eléctrico, etc.",
    )

    class Meta:
        verbose_name = "Paso de Protocolo"
        verbose_name_plural = "Pasos de Protocolo"
        ordering = ['protocolo', 'orden']
        unique_together = [('protocolo', 'orden')]

    def __str__(self):
        return f"Paso {self.orden}: {self.titulo}"


class ArbolDiagnostico(models.Model):
    """
    Árbol de decisión para diagnóstico y resolución de fallas.
    Construido desde el Wizard visual del Director.
    """
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="arboles_diagnostico", null=True, blank=True,
    )
    expediente = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.CASCADE,
        related_name="arboles_diagnostico", verbose_name="Equipo",
        null=True, blank=True,
        help_text="Null = árbol genérico aplicable a cualquier equipo.",
    )
    falla_descripcion = models.CharField(
        max_length=300, verbose_name="Falla / Síntoma",
        help_text="Ej: 'Alarma E-023', 'CVs de QC elevados', 'No aspira muestra'",
    )
    falla_codigo      = models.CharField(
        max_length=50, blank=True, verbose_name="Código de Error (si aplica)",
    )
    activo    = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True,
        related_name="arboles_creados",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Árbol de Diagnóstico"
        verbose_name_plural = "Árboles de Diagnóstico"
        ordering = ['falla_descripcion']

    def __str__(self):
        return f"Diag: {self.falla_descripcion}"

    def get_nodo_raiz(self):
        return self.nodos.filter(padre__isnull=True).first()


class ProcedimientoReparacion(models.Model):
    """
    Procedimiento paso a paso para una reparación o intervención técnica.
    Referenciado desde NodoDiagnostico cuando se llega a una acción concreta.
    """
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="procedimientos_reparacion", null=True, blank=True,
    )
    expediente = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="procedimientos",
    )
    titulo          = models.CharField(max_length=300, verbose_name="Título")
    tipo_componente = models.CharField(
        max_length=20, choices=TIPO_COMPONENTE_CHOICES, default='OTRO',
        verbose_name="Componente a Intervenir",
    )
    descripcion_tecnica = models.TextField(blank=True, verbose_name="Descripción Técnica")
    nivel_requerido     = models.CharField(
        max_length=20, choices=NIVEL_AUTORIZACION_CHOICES, default='QUIMICO',
        verbose_name="Nivel mínimo para ejecutar",
    )
    tiempo_estimado_min = models.PositiveIntegerField(
        default=30, verbose_name="Tiempo estimado (minutos)",
    )
    requiere_paro_equipo = models.BooleanField(
        default=True, verbose_name="Requiere paro del equipo",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Procedimiento de Reparación"
        verbose_name_plural = "Procedimientos de Reparación"
        ordering = ['titulo']

    def __str__(self):
        return self.titulo


class PasoReparacion(models.Model):
    """Paso individual dentro de un ProcedimientoReparacion."""
    procedimiento = models.ForeignKey(
        ProcedimientoReparacion, on_delete=models.CASCADE,
        related_name="pasos",
    )
    orden       = models.PositiveSmallIntegerField(default=1)
    instruccion = models.TextField(verbose_name="Instrucción")
    imagen      = models.ImageField(
        upload_to="mantenimiento/reparacion/", blank=True, null=True,
    )
    video_url   = models.URLField(blank=True, null=True)
    nota_seguridad = models.CharField(max_length=500, blank=True)

    # ── Ajuste 1: Refacción requerida — multi-silo GenericFK ──────────────
    silo_refaccion = models.CharField(
        max_length=15, choices=SILO_ORIGEN_CHOICES, blank=True, null=True,
        verbose_name="Silo de la Refacción",
    )
    refaccion_content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Tipo de Catálogo",
        help_text="Catálogo del silo: CatalogoReactivoLab, CatalogoInsumoConsultorio o CatalogoInsumoGeneral",
    )
    refaccion_object_id = models.PositiveIntegerField(null=True, blank=True)
    refaccion_item      = GenericForeignKey('refaccion_content_type', 'refaccion_object_id')
    cantidad_refaccion  = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        verbose_name="Cantidad requerida",
    )
    unidad_refaccion    = models.CharField(max_length=20, blank=True, verbose_name="Unidad")

    class Meta:
        verbose_name = "Paso de Reparación"
        verbose_name_plural = "Pasos de Reparación"
        ordering = ['procedimiento', 'orden']
        unique_together = [('procedimiento', 'orden')]

    def __str__(self):
        return f"Paso {self.orden}: {self.instruccion[:60]}"


class NodoDiagnostico(models.Model):
    """
    Nodo dentro de un ArbolDiagnostico.
    Estructura de árbol con FK a sí mismo (padre/hijo).
    """
    arbol    = models.ForeignKey(
        ArbolDiagnostico, on_delete=models.CASCADE, related_name="nodos",
    )
    padre    = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name="hijos", verbose_name="Nodo Padre",
    )
    tipo_nodo  = models.CharField(
        max_length=15, choices=TIPO_NODO_CHOICES, default='PREGUNTA',
    )
    texto      = models.TextField(
        verbose_name="Pregunta / Instrucción / Descripción",
    )
    condicion_de_padre = models.CharField(
        max_length=200, blank=True,
        help_text="Respuesta del nodo padre que lleva aquí. Ej: 'Sí', 'No', 'Error persiste'",
    )
    nivel_requerido = models.CharField(
        max_length=20, choices=NIVEL_AUTORIZACION_CHOICES, default='TODOS',
    )
    lleva_a_procedimiento = models.ForeignKey(
        ProcedimientoReparacion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="nodos_referencia",
        verbose_name="Procedimiento a ejecutar",
    )
    nivel_escalamiento = models.CharField(
        max_length=20, choices=NIVEL_ESCALAMIENTO_CHOICES, blank=True,
        help_text="Solo para nodos tipo ESCALAMIENTO.",
    )
    imagen  = models.ImageField(upload_to="mantenimiento/nodos/", blank=True, null=True)
    orden   = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Nodo de Diagnóstico"
        verbose_name_plural = "Nodos de Diagnóstico"
        ordering = ['arbol', 'padre', 'orden']

    def __str__(self):
        return f"[{self.get_tipo_nodo_display()}] {self.texto[:80]}"

    def get_hijos_ordenados(self):
        return self.hijos.all().order_by('orden')


