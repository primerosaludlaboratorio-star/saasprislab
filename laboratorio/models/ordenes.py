"""
⚠️ DEPRECATED: MODELOS LEGACY - ELIMINAR EN VERSIÓN 2.0 ⚠️

ESTE ARCHIVO CONTIENE MODELOS DUPLICADOS Y OBSOLETOS:

❌ laboratorio.models.ordenes.Medico -> USE core.models.Medico  
❌ laboratorio.models.ordenes.Orden -> USE core.models.OrdenDeServicio

MIGRACIÓN REQUERIDA:
1. Usar core.models para todo nuevo desarrollo
2. Migrar datos existentes con comando: python manage.py migrate_legacy_ordenes
3. Eliminar este archivo después de migración

REFERENCIAS ACTUALIZADAS:
- Medico: from core.models import Medico
- Orden: from core.models import OrdenDeServicio
- Paciente: from core.models import Paciente
"""

import warnings
warnings.warn(
    "⚠️ CRÍTICO: laboratorio.models.ordenes está OBSOLETO. "
    "Use core.models (Medico, OrdenDeServicio) inmediatamente. "
    "Este archivo será eliminado en v2.0",
    DeprecationWarning,
    stacklevel=2
)

"""
MÓDULO DE LABORATORIO - Órdenes y médicos (LEGACY - NO USAR)
"""
from django.conf import settings
from django.db import models


class Medico(models.Model):
    """
    Médico solicitante de estudios de laboratorio.
    """
    nombre = models.CharField(
        max_length=200,
        help_text='Nombre completo del médico.',
    )
    especialidad = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text='Especialidad médica (opcional).',
    )
    activo = models.BooleanField(
        default=True,
        help_text='Indica si el médico está activo en el sistema.',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Médico'
        verbose_name_plural = 'Médicos'
        ordering = ['nombre']

    def __str__(self) -> str:
        especialidad_str = f' ({self.especialidad})' if self.especialidad else ''
        return f'{self.nombre}{especialidad_str}'


class Orden(models.Model):
    """
    Orden de laboratorio (solicitud de estudios para un paciente).
    Multi-tenant: siempre filtrar por empresa. Preparada para PRIS.
    """
    ORIGEN_PUBLICO_GENERAL = 'PUBLICO_GENERAL'
    ORIGEN_CONVENIO = 'CONVENIO'
    ORIGEN_SEGURO = 'SEGURO'
    ORIGEN_OTRO = 'OTRO'
    ORIGEN_CHOICES = [
        (ORIGEN_PUBLICO_GENERAL, 'Público General'),
        (ORIGEN_CONVENIO, 'Convenio'),
        (ORIGEN_SEGURO, 'Seguro'),
        (ORIGEN_OTRO, 'Otro'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ordenes_laboratorio',
        help_text='Empresa/tenant dueño de esta orden (multi-tenant SaaS).',
    )
    paciente = models.ForeignKey(
        'core.Paciente',
        on_delete=models.PROTECT,
        related_name='ordenes_laboratorio',
    )
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ordenes_laboratorio_creadas',
        help_text='Usuario que registró la orden (para comisiones / auditoría).',
    )
    medico = models.ForeignKey(
        Medico,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='ordenes',
        help_text='Médico solicitante (opcional).',
    )
    medico_texto = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text='Nombre del médico en texto libre (si no está en el catálogo).',
    )
    origen = models.CharField(
        max_length=20,
        choices=ORIGEN_CHOICES,
        default=ORIGEN_PUBLICO_GENERAL,
        help_text='Origen de la orden (público general, convenio, seguro, etc.).',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado_pago = models.BooleanField(default=False, help_text='Indica si la orden está pagada.')

    # Control de Calidad y Validación
    ESTADO_ANALISIS_PENDIENTE = 'PENDIENTE'
    ESTADO_ANALISIS_EN_PROCESO = 'EN_PROCESO'
    ESTADO_ANALISIS_VALIDADO = 'VALIDADO'
    ESTADO_ANALISIS_CHOICES = [
        (ESTADO_ANALISIS_PENDIENTE, 'Pendiente'),
        (ESTADO_ANALISIS_EN_PROCESO, 'En Proceso'),
        (ESTADO_ANALISIS_VALIDADO, 'Validado'),
    ]
    estado_analisis = models.CharField(
        max_length=20,
        choices=ESTADO_ANALISIS_CHOICES,
        default=ESTADO_ANALISIS_PENDIENTE,
        help_text='Estado del análisis de laboratorio. Solo órdenes VALIDADAS pueden imprimirse.',
    )
    fecha_validacion = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Fecha y hora en que la orden fue validada.',
    )
    usuario_valido = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='ordenes_validadas',
        help_text='Usuario que validó la orden (control de calidad).',
    )

    # Campos para Inteligencia Artificial
    IA_STATUS_PENDIENTE = 'PENDIENTE'
    IA_STATUS_GENERADO = 'GENERADO'
    IA_STATUS_ERROR = 'ERROR'
    IA_STATUS_CHOICES = [
        (IA_STATUS_PENDIENTE, 'Pendiente'),
        (IA_STATUS_GENERADO, 'Generado'),
        (IA_STATUS_ERROR, 'Error'),
    ]
    interpretacion_ia = models.TextField(
        blank=True,
        null=True,
        help_text='Resumen clínico generado por AI basado en los resultados de la orden.',
    )
    ia_status = models.CharField(
        max_length=20,
        choices=IA_STATUS_CHOICES,
        default=IA_STATUS_PENDIENTE,
        help_text='Estado del análisis de inteligencia artificial para esta orden.',
    )

    # ── PRE-MIGRACIÓN MAESTRA: campo de enlace hacia core.OrdenDeServicio ────────
    # Estos campos se activarán en la Migración Unificada.
    # core_orden_id = models.PositiveIntegerField(
    #     null=True, blank=True, db_index=True,
    #     help_text='ID del core.OrdenDeServicio espejo. Activo tras Migración Maestra.',
    # )
    # core_paciente_id = models.PositiveIntegerField(
    #     null=True, blank=True, db_index=True,
    #     help_text='ID del core.Paciente canónico. Activo tras Migración Maestra.',
    # )
    # ─────────────────────────────────────────────────────────────────────────────

    class Meta:
        verbose_name = 'Orden de Laboratorio'
        verbose_name_plural = 'Órdenes de Laboratorio'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['empresa', 'estado_analisis'], name='lab_orden_empresa_estado_idx'),
            models.Index(fields=['empresa', '-fecha_creacion'], name='lab_orden_empresa_fecha_idx'),
            models.Index(fields=['estado_analisis'], name='lab_orden_estado_idx'),
        ]

    def __str__(self) -> str:
        return f'Orden #{self.id} - {self.paciente}'

    @property
    def total(self):
        from decimal import Decimal
        total = Decimal('0')
        for detalle in self.detalles.all():
            total += detalle.subtotal
        return total


class DetalleOrden(models.Model):
    """
    Línea de detalle de una orden (estudios solicitados).
    Congela el precio del estudio al momento de la venta.
    Puede venir de un perfil o ser un estudio individual.
    """
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='detalles',
    )
    estudio = models.ForeignKey(
        'laboratorio.Estudio',
        on_delete=models.PROTECT,
        related_name='detalles_orden',
    )
    perfil = models.ForeignKey(
        'laboratorio.PerfilLaboratorio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='detalles_orden',
        verbose_name="Perfil de Origen",
        help_text="Si este estudio viene de un perfil, se registra aquí para agrupación visual"
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Precio cobrado por este estudio en el momento de la venta.',
    )
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Detalle de Orden'
        verbose_name_plural = 'Detalles de Orden'
        # Evitar duplicados: mismo estudio en la misma orden (importante para perfiles que se solapan)
        unique_together = ('orden', 'estudio')

    def __str__(self) -> str:
        perfil_str = f' ({self.perfil.nombre})' if self.perfil else ''
        return f'{self.estudio.nombre} x{self.cantidad}{perfil_str} (Orden {self.orden_id})'

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad
