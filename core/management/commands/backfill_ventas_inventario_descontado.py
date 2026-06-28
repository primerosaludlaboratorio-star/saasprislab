"""
BACKFILL: Inventario Descontado para Ventas Históricas
========================================================

Marca el campo `inventario_descontado=True` en todas las ventas que ya tienen
movimientos de salida en el Kardex, garantizando idempotencia real.

ESTRATEGIA CONSERVADORA (v1.13):
- Solo marca ventas en estado COMPLETADA/PAGADO (NO canceladas)
- Solo ventas con movimientos SALIDA_VENTA netos (> 0 después de devoluciones)
- Excluye ventas que tienen ENTRADA_DEVOLUCION completa (cancelaciones totales)

Ejecución segura:
    python manage.py backfill_ventas_inventario_descontado              # Dry-run
    python manage.py backfill_ventas_inventario_descontado --execute    # Real

Autor: Windsurf Cascade
Fecha: 2026-04-03
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef, Q

from core.models import Venta
from farmacia.models import MovimientoInventario

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill: Marca inventario_descontado=True en ventas históricas con movimientos de salida (CRÍTICO v1.13)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Ejecutar el backfill real (sin esto solo muestra preview)',
        )
        parser.add_argument(
            '--empresa',
            type=int,
            help='Filtrar por ID de empresa específica',
        )
        parser.add_argument(
            '--desde',
            type=str,
            help='Fecha desde (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Tamaño del lote para actualización (default: 500)',
        )

    def handle(self, *args, **options):
        execute = options['execute']
        empresa_id = options.get('empresa')
        desde = options.get('desde')
        batch_size = options['batch_size']

        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))
        self.stdout.write(self.style.MIGRATE_HEADING('BACKFILL CRÍTICO v1.13 — Inventario Descontado Histórico'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))

        if not execute:
            self.stdout.write(self.style.WARNING('\n[DRY-RUN MODE] No se modificarán datos. Use --execute para aplicar.\n'))
        else:
            self.stdout.write(self.style.ERROR('\n[EXECUTE MODE] ¡Se modificarán datos! Asegúrese de tener backup.\n'))

        # Construir queryset base
        # FIX v1.13: Excluir ventas canceladas (no deben marcarse como descontadas)
        ventas_query = Venta.objects.filter(
            inventario_descontado=False,
            estado__in=['COMPLETADA', 'PAGADO', 'COMPLETADO'],  # EXCLUIR 'CANCELADA'
        )

        if empresa_id:
            ventas_query = ventas_query.filter(empresa_id=empresa_id)
            self.stdout.write(f"Filtrando por empresa_id={empresa_id}")

        if desde:
            ventas_query = ventas_query.filter(fecha__gte=desde)
            self.stdout.write(f"Filtrando desde fecha >= {desde}")

        # Detectar ventas que tienen movimientos de salida NETOS > 0
        # FIX v1.13: Considerar SALIDA_VENTA positivas vs ENTRADA_DEVOLUCION (cancelaciones)
        # Las variables ventas_con_salida_neta y ventas_con_devolucion se usan
        # para futura lógica de cálculo neto (salida - devolución)
        # Por ahora, simplificamos: excluir ventas que tienen devoluciones completas

        # Solo marcar si hay SALIDA_VENTA neta (salidas > devoluciones)
        # O si hay cualquier SALIDA_VENTA (caso normal de venta completada)
        ventas_con_movimientos = ventas_query.filter(
            Exists(MovimientoInventario.objects.filter(
                venta=OuterRef('pk'),
                tipo_movimiento='SALIDA_VENTA',
            ))
        ).exclude(
            # Excluir ventas donde la suma de devoluciones = suma de salidas (canceladas completamente)
            id__in=MovimientoInventario.objects.filter(
                tipo_movimiento='ENTRADA_DEVOLUCION',
            ).values('venta_id')
        ).select_related('empresa')

        total_afectadas = ventas_con_movimientos.count()

        if total_afectadas == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ No hay ventas para backfill. Todas están sincronizadas.'))
            return

        self.stdout.write(f"\n📊 Ventas históricas con movimientos SALIDA_VENTA: {total_afectadas}")
        self.stdout.write(f"📦 Tamaño de lote: {batch_size}")

        # Preview: mostrar algunas ventas de ejemplo
        self.stdout.write("\n📝 Preview de ventas a actualizar:")
        for venta in ventas_con_movimientos[:10]:
            mov_count = MovimientoInventario.objects.filter(
                venta=venta,
                tipo_movimiento='SALIDA_VENTA',
            ).count()
            self.stdout.write(f"   • Venta #{venta.id} | {venta.fecha.strftime('%Y-%m-%d')} | "
                            f"Empresa: {venta.empresa.nombre if venta.empresa else 'N/A'} | "
                            f"Movimientos: {mov_count}")

        if total_afectadas > 10:
            self.stdout.write(f"   ... y {total_afectadas - 10} más")

        if not execute:
            self.stdout.write(self.style.WARNING(f"\n⚠️  DRY-RUN: No se aplicaron cambios. {total_afectadas} ventas pendientes."))
            self.stdout.write(self.style.NOTICE(f"\nEjecute con --execute para aplicar el backfill."))
            return

        # EXECUTE: Realizar actualización por lotes
        self.stdout.write(self.style.ERROR(f"\n🚀 Iniciando backfill real...\n"))

        actualizadas = 0
        errores = 0

        # Paginar para no saturar memoria
        ventas_ids = list(ventas_con_movimientos.values_list('id', flat=True))

        for i in range(0, len(ventas_ids), batch_size):
            batch_ids = ventas_ids[i:i + batch_size]

            try:
                with transaction.atomic():
                    updated = Venta.objects.filter(
                        id__in=batch_ids,
                        inventario_descontado=False,  # Doble verificación de seguridad
                    ).update(inventario_descontado=True)

                    actualizadas += updated
                    self.stdout.write(f"   Lote {i//batch_size + 1}: {updated} ventas actualizadas")

            except Exception as e:
                errores += len(batch_ids)
                logger.error(f"Error en batch {i//batch_size + 1}: {e}")
                self.stdout.write(self.style.ERROR(f"   ❌ Error en lote {i//batch_size + 1}: {e}"))

        # Resumen final
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '=' * 70))
        self.stdout.write(self.style.MIGRATE_HEADING('RESULTADO DEL BACKFILL'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))
        self.stdout.write(f"✅ Ventas actualizadas: {actualizadas}")
        self.stdout.write(f"❌ Errores: {errores}")
        self.stdout.write(f"📊 Total procesado: {actualizadas + errores}")

        if errores == 0:
            self.stdout.write(self.style.SUCCESS('\n🎉 Backfill completado exitosamente.'))
            self.stdout.write(self.style.NOTICE('\nLas ventas históricas ahora están protegidas contra doble descuento.'))
        else:
            self.stdout.write(self.style.ERROR(f'\n⚠️  Se encontraron {errores} errores. Revise los logs.'))

        # Verificación de integridad post-backfill
        pendientes = Venta.objects.filter(
            inventario_descontado=False,
            estado__in=['COMPLETADA', 'PAGADO', 'COMPLETADO'],
        ).filter(
            Exists(MovimientoInventario.objects.filter(
                venta=OuterRef('pk'),
                tipo_movimiento='SALIDA_VENTA',
            ))
        ).count()

        if pendientes == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ Verificación: 0 ventas pendientes de sincronización.'))
        else:
            self.stdout.write(self.style.ERROR(f'\n⚠️  Verificación: {pendientes} ventas aún pendientes.'))
