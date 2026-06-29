"""
Servicio de Cálculo de KPIs — Panel Ejecutivo
Calcula métricas operacionales en tiempo real o desde snapshots en caché.
"""

from decimal import Decimal
from datetime import timedelta, date
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import Coalesce

from core.models import (
    Empresa, Sucursal, Venta, OrdenDeServicio, MovimientoCaja,
    CuentaPorCobrar, AuditLog, KPI_Snapshot, KPI_MetaAnual,
    Paciente, Producto
)


class KPIService:
    """
    Servicio centralizado para cálculos de KPIs.
    Soporta caché via KPI_Snapshot + cálculos on-demand.
    """

    def __init__(self, empresa: Empresa, sucursal: Sucursal = None):
        self.empresa = empresa
        self.sucursal = sucursal

    def _get_filters(self):
        """Retorna filtros Q para empresa/sucursal actual."""
        filters = Q(empresa=self.empresa)
        if self.sucursal:
            filters &= Q(sucursal=self.sucursal)
        return filters

    # ── Ingresos ─────────────────────────────────────────────────────────────

    def ingresos_hoy(self) -> Decimal:
        """Total de ventas (facturadas) de hoy."""
        today = timezone.now().date()
        result = Venta.objects.filter(
            *self._get_filters(),
            fecha__date=today,
            estado='COMPLETADA'
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal(0), output_field=DecimalField())
        )
        return result['total']

    def ingresos_por_periodo(self, dias: int = 30) -> dict:
        """Ingresos de los últimos N días (por día)."""
        desde = timezone.now().date() - timedelta(days=dias)
        ventas = Venta.objects.filter(
            *self._get_filters(),
            fecha__date__gte=desde,
            estado='COMPLETADA'
        ).extra(
            select={'fecha_grupo': 'DATE(fecha)'}
        ).values('fecha_grupo').annotate(
            total=Coalesce(Sum('total'), Decimal(0), output_field=DecimalField())
        ).order_by('fecha_grupo')

        return {str(v['fecha_grupo']): float(v['total']) for v in ventas}

    def ingresos_por_modulo(self, fecha_desde=None, fecha_hasta=None) -> dict:
        """Desglose de ingresos por módulo (Lab, Consultorio, Farmacia)."""
        fecha_desde = fecha_desde or (timezone.now().date() - timedelta(days=30))
        fecha_hasta = fecha_hasta or timezone.now().date()

        # Órdenes de Lab (OrdenDeServicio)
        ingresos_lab = OrdenDeServicio.objects.filter(
            *self._get_filters(),
            fecha_creacion__date__range=(fecha_desde, fecha_hasta),
            estado__in=['COMPLETADA', 'ENTREGADA'],
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal(0), output_field=DecimalField())
        )['total']

        # Ventas por módulo (consultorio, farmacia)
        # Nota: Este es un ejemplo simplificado; en producción habría campos
        # específicos en Venta para indicar módulo
        ingresos_farmacia = Venta.objects.filter(
            *self._get_filters(),
            fecha__date__range=(fecha_desde, fecha_hasta),
            estado='COMPLETADA',
            # Filtro simplificado: asume paciente existe
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal(0), output_field=DecimalField())
        )['total']

        return {
            'lab': float(ingresos_lab),
            'farmacia': float(ingresos_farmacia),
            'consultorio': 0.0,  # Placeholder
        }

    # ── Órdenes ──────────────────────────────────────────────────────────────

    def ordenes_capturadas_hoy(self) -> int:
        """Órdenes creadas hoy."""
        today = timezone.now().date()
        return OrdenDeServicio.objects.filter(
            *self._get_filters(),
            fecha_creacion__date=today
        ).count()

    def ordenes_completadas_hoy(self) -> int:
        """Órdenes completadas hoy."""
        today = timezone.now().date()
        return OrdenDeServicio.objects.filter(
            *self._get_filters(),
            fecha_creacion__date=today,
            estado__in=['COMPLETADA', 'ENTREGADA']
        ).count()

    def tasa_cumplimiento_hoy(self) -> Decimal:
        """(Órdenes completadas / capturadas) * 100."""
        capturadas = self.ordenes_capturadas_hoy()
        if capturadas == 0:
            return Decimal(0)
        completadas = self.ordenes_completadas_hoy()
        return Decimal(completadas) / Decimal(capturadas) * 100

    # ── Caja ──────────────────────────────────────────────────────────────────

    def movimientos_caja_hoy(self) -> dict:
        """Ingresos y egresos de caja hoy."""
        today = timezone.now().date()
        ingresos = MovimientoCaja.objects.filter(
            *self._get_filters(),
            id__date=today,  # Approx; ideally fecha_movimiento field
            tipo_movimiento='INGRESO'
        ).aggregate(
            total=Coalesce(Sum('monto'), Decimal(0), output_field=DecimalField())
        )['total']

        egresos = MovimientoCaja.objects.filter(
            *self._get_filters(),
            id__date=today,
            tipo_movimiento='EGRESO'
        ).aggregate(
            total=Coalesce(Sum('monto'), Decimal(0), output_field=DecimalField())
        )['total']

        return {
            'ingresos': float(ingresos),
            'egresos': float(egresos),
            'saldo': float(ingresos - egresos),
        }

    # ── Finanzas ──────────────────────────────────────────────────────────────

    def cuentas_por_cobrar(self) -> Decimal:
        """Monto total de CxC pendiente."""
        result = CuentaPorCobrar.objects.filter(
            *self._get_filters(),
        ).aggregate(
            total=Coalesce(Sum('monto_pendiente'), Decimal(0), output_field=DecimalField())
        )
        return result['total']

    # ── Operacional ───────────────────────────────────────────────────────────

    def pacientes_nuevos_hoy(self) -> int:
        """Pacientes registrados hoy."""
        today = timezone.now().date()
        return Paciente.objects.filter(
            *self._get_filters(),
            fecha_registro__date=today
        ).count()

    def pacientes_atendidos_hoy(self) -> int:
        """Pacientes con órdenes/ventas hoy."""
        today = timezone.now().date()
        pacientes_ids = set()

        # Órdenes
        pacientes_ids.update(
            OrdenDeServicio.objects.filter(
                *self._get_filters(),
                fecha_creacion__date=today
            ).values_list('paciente_id', flat=True)
        )

        # Ventas
        pacientes_ids.update(
            Venta.objects.filter(
                *self._get_filters(),
                fecha__date=today
            ).values_list('paciente_id', flat=True)
        )

        return len(pacientes_ids)

    # ── Auditoría ─────────────────────────────────────────────────────────────

    def cambios_registrados_hoy(self) -> int:
        """Operaciones en AuditLog hoy."""
        today = timezone.now().date()
        return AuditLog.objects.filter(
            *self._get_filters(),
            fecha_cierta__date=today
        ).count()

    # ── Dashboard Completo ────────────────────────────────────────────────────

    def dashboard_hoy(self) -> dict:
        """Retorna todos los KPIs para el dashboard de hoy."""
        return {
            'empresa': self.empresa.nombre,
            'sucursal': self.sucursal.nombre if self.sucursal else 'Global',
            'fecha': timezone.now().date().isoformat(),

            # Ingresos
            'ingresos_hoy': float(self.ingresos_hoy()),
            'ingresos_por_modulo': self.ingresos_por_modulo(),

            # Órdenes
            'ordenes_capturadas': self.ordenes_capturadas_hoy(),
            'ordenes_completadas': self.ordenes_completadas_hoy(),
            'tasa_cumplimiento': float(self.tasa_cumplimiento_hoy()),

            # Caja
            'caja': self.movimientos_caja_hoy(),

            # Finanzas
            'cuentas_por_cobrar': float(self.cuentas_por_cobrar()),

            # Operacional
            'pacientes_nuevos': self.pacientes_nuevos_hoy(),
            'pacientes_atendidos': self.pacientes_atendidos_hoy(),

            # Auditoría
            'cambios_registrados': self.cambios_registrados_hoy(),
        }

    def generar_snapshot_hoy(self) -> KPI_Snapshot:
        """Genera y guarda snapshot de KPIs para hoy."""
        hoy = timezone.now().date()

        # Calcular todos los KPIs
        ingresos_total = self.ingresos_hoy()
        ingresos_modulo = self.ingresos_por_modulo()
        ordenes_capturadas = self.ordenes_capturadas_hoy()
        ordenes_completadas = self.ordenes_completadas_hoy()
        caja = self.movimientos_caja_hoy()

        snapshot, created = KPI_Snapshot.objects.update_or_create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            fecha=hoy,
            defaults={
                'ingresos_total': ingresos_total,
                'ingresos_lab': Decimal(str(ingresos_modulo['lab'])),
                'ingresos_consultorio': Decimal(str(ingresos_modulo.get('consultorio', 0))),
                'ingresos_farmacia': Decimal(str(ingresos_modulo['farmacia'])),
                'ordenes_capturadas': ordenes_capturadas,
                'ordenes_completadas': ordenes_completadas,
                'tasa_cumplimiento': self.tasa_cumplimiento_hoy(),
                'movimientos_ingreso': Decimal(str(caja['ingresos'])),
                'movimientos_egreso': Decimal(str(caja['egresos'])),
                'saldo_caja': Decimal(str(caja['saldo'])),
                'cuentas_por_cobrar': self.cuentas_por_cobrar(),
                'pacientes_nuevos': self.pacientes_nuevos_hoy(),
                'pacientes_atendidos': self.pacientes_atendidos_hoy(),
                'cambios_registrados': self.cambios_registrados_hoy(),
            }
        )
        return snapshot
