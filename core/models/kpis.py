"""
KPIs — Panel Ejecutivo (Executive Dashboard)
Modelos para almacenar snapshots de métricas operacionales en tiempo real.
"""

from django.db import models
from django.utils import timezone
from core.models.base import Empresa, Sucursal, AuditoriaModel


class KPI_Snapshot(models.Model):
    """
    Snapshot diario de KPIs para una empresa/sucursal.
    Permite cálculos históricos sin ejecutar queries grandes en runtime.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='kpi_snapshots',
        verbose_name="Empresa"
    )
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='kpi_snapshots',
        verbose_name="Sucursal (global si None)"
    )
    fecha = models.DateField(
        verbose_name="Fecha del Snapshot",
        help_text="Día para el que se calcula el snapshot"
    )

    # Ingresos
    ingresos_total = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        verbose_name="Ingresos Totales",
        help_text="Total de ventas + órdenes completadas"
    )
    ingresos_lab = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        verbose_name="Ingresos Lab"
    )
    ingresos_consultorio = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        verbose_name="Ingresos Consultorio"
    )
    ingresos_farmacia = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        verbose_name="Ingresos Farmacia"
    )

    # Órdenes
    ordenes_capturadas = models.IntegerField(
        default=0,
        verbose_name="Órdenes Capturadas Hoy"
    )
    ordenes_completadas = models.IntegerField(
        default=0,
        verbose_name="Órdenes Completadas Hoy"
    )
    tasa_cumplimiento = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0,
        verbose_name="Tasa Cumplimiento (%)"
    )

    # Caja
    movimientos_ingreso = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        verbose_name="Movimientos de Ingreso"
    )
    movimientos_egreso = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        verbose_name="Movimientos de Egreso"
    )
    saldo_caja = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        verbose_name="Saldo de Caja"
    )

    # Finanzas
    cuentas_por_cobrar = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        verbose_name="CxC Pendiente"
    )
    margen_promedio = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0,
        verbose_name="Margen Promedio (%)"
    )

    # Operacional
    pacientes_nuevos = models.IntegerField(
        default=0,
        verbose_name="Pacientes Nuevos"
    )
    pacientes_atendidos = models.IntegerField(
        default=0,
        verbose_name="Pacientes Atendidos"
    )
    inventario_bajo_stock = models.IntegerField(
        default=0,
        verbose_name="Ítems bajo stock"
    )

    # Auditoría
    cambios_registrados = models.IntegerField(
        default=0,
        verbose_name="Cambios en AuditLog"
    )

    # Metadata
    calculado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Calculado en"
    )

    class Meta:
        app_label = 'core'
        unique_together = ('empresa', 'sucursal', 'fecha')
        verbose_name = "KPI Snapshot"
        verbose_name_plural = "KPI Snapshots"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['empresa', '-fecha']),
            models.Index(fields=['empresa', 'sucursal', '-fecha']),
        ]

    def __str__(self) -> str:
        sucursal_str = f" @ {self.sucursal.codigo_sucursal}" if self.sucursal else " (global)"
        return f"{self.empresa.nombre}{sucursal_str} — {self.fecha}"


class KPI_MetaAnual(models.Model):
    """
    Metas/objetivos anuales por empresa y sucursal.
    Usadas para comparar KPIs reales vs metas en dashboards.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='kpi_metas',
        verbose_name="Empresa"
    )
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='kpi_metas',
        verbose_name="Sucursal (global si None)"
    )
    anio = models.IntegerField(
        verbose_name="Año"
    )

    # Metas
    meta_ingresos = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        verbose_name="Meta de Ingresos Anuales"
    )
    meta_ordenes = models.IntegerField(
        default=0,
        verbose_name="Meta de Órdenes Anuales"
    )
    meta_margen = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0,
        verbose_name="Meta de Margen (%)"
    )

    class Meta:
        app_label = 'core'
        unique_together = ('empresa', 'sucursal', 'anio')
        verbose_name = "Meta Anual"
        verbose_name_plural = "Metas Anuales"

    def __str__(self) -> str:
        sucursal_str = f" @ {self.sucursal.codigo_sucursal}" if self.sucursal else " (global)"
        return f"{self.empresa.nombre}{sucursal_str} — {self.anio}"
