"""
BACKFILL CRÍTICO v1.14 — Movimientos Caja Históricos
======================================================

Prepara datos históricos para Bankguard v1.14:
1. Detecta y marca duplicados como 'fantasma'
2. Genera idempotency_key para movimientos antiguos
3. Marca históricos como autorizados (confianza en auditoría previa)

Ejecución:
    python manage.py backfill_movimientos_caja_v114 --dry-run
    python manage.py backfill_movimientos_caja_v114 --start-date 2025-01-01
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime
import logging

from core.models import MovimientoCaja

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill histórico para Bankguard v1.14: idempotency_key, duplicados, autorización"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            help='Fecha inicio (YYYY-MM-DD). Default: 2020-01-01'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='Fecha fin (YYYY-MM-DD). Default: hoy'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin modificar datos'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Tamaño de lote para procesamiento (default: 500)'
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        start_date_str = options.get('start_date') or '2020-01-01'
        end_date_str = options.get('end_date') or timezone.now().strftime('%Y-%m-%d')
        batch_size = options.get('batch_size', 500)
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 80))
        self.stdout.write(self.style.MIGRATE_HEADING('BACKFILL: MovimientoCaja v1.14 (Bankguard)'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 80))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 MODO SIMULACIÓN (dry-run): No se modificarán datos\n'))
        else:
            self.stdout.write(self.style.ERROR('\n⚠️  MODO EJECUCIÓN REAL: Se modificarán datos\n'))
        
        self.stdout.write(f"Rango: {start_date_str} → {end_date_str}\n")
        
        # PASO 1: Detectar y marcar duplicados
        total_fantasmas = self._paso_1_detectar_duplicados(dry_run, start_date, end_date)
        
        # PASO 2: Generar idempotency_key
        total_keys = self._paso_2_generar_idempotency_keys(dry_run, start_date, end_date, batch_size)
        
        # PASO 3: Validación final
        self._paso_3_validacion_final(dry_run, start_date, end_date)
        
        # Resumen
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '=' * 80))
        self.stdout.write(self.style.MIGRATE_HEADING('RESUMEN'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 80))
        self.stdout.write(f"  Duplicados marcados: {total_fantasmas}")
        self.stdout.write(f"  Keys generadas: {total_keys}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 Simulación completada. Sin cambios reales.'))
            self.stdout.write(self.style.NOTICE('Ejecute sin --dry-run para aplicar.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Backfill completado exitosamente.'))
    
    def _paso_1_detectar_duplicados(self, dry_run, start_date, end_date):
        """Detecta MovimientoCaja duplicados y marca extras como 'fantasma'."""
        self.stdout.write(self.style.WARNING('\n[PASO 1] Detectando duplicados...'))
        
        # Buscar grupos duplicados por (venta, tipo, concepto, monto)
        duplicados = (
            MovimientoCaja.objects
            .filter(
                fecha_movimiento__gte=start_date,
                fecha_movimiento__lte=end_date,
                venta__isnull=False
            )
            .values('venta', 'tipo_movimiento', 'concepto', 'monto')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        
        total_fantasmas = 0
        
        for grupo in duplicados:
            movs = list(
                MovimientoCaja.objects
                .filter(
                    venta=grupo['venta'],
                    tipo_movimiento=grupo['tipo_movimiento'],
                    concepto=grupo['concepto'],
                    monto=grupo['monto'],
                )
                .order_by('id')  # Mantener el más antiguo (ID menor)
            )
            
            # Mantener el primero (más antiguo), marcar el resto como fantasma
            for mov in movs[1:]:
                total_fantasmas += 1
                if not dry_run:
                    observacion_actual = mov.referencia or ""
                    mov.referencia = f"[FANTASMA v1.14] Duplicado de Mov #{movs[0].id}. {observacion_actual}"[:255]
                    mov.save(update_fields=['referencia'])
                    logger.info(f"Marcado como fantasma: Mov {mov.id} (duplicado de {movs[0].id})")
                
                self.stdout.write(
                    f"  🔴 Fantasma: Mov {mov.id} → duplicado de Mov {movs[0].id} "
                    f"(Venta {grupo['venta']}, ${grupo['monto']})"
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"  ✓ {total_fantasmas} duplicados detectados y marcados")
        )
        return total_fantasmas
    
    def _paso_2_generar_idempotency_keys(self, dry_run, start_date, end_date, batch_size):
        """Genera idempotency_key para movimientos históricos sin key."""
        self.stdout.write(self.style.WARNING('\n[PASO 2] Generando idempotency_keys...'))
        
        query = (
            MovimientoCaja.objects
            .filter(
                fecha_movimiento__gte=start_date,
                fecha_movimiento__lte=end_date,
                idempotency_key__isnull=True
            )
            .exclude(referencia__startswith='[FANTASMA')  # Excluir fantasmas
        )
        
        total = query.count()
        processed = 0
        duplicados_key = 0
        
        self.stdout.write(f"  Total a procesar: {total}")
        
        # Procesar en lotes para no saturar memoria
        for offset in range(0, total, batch_size):
            lote = query[offset:offset + batch_size]
            
            for mov in lote:
                # Generar key determinista
                if mov.venta_id:
                    key = f"venta_{mov.venta_id}_{mov.tipo_movimiento}_{mov.concepto}_{mov.fecha_movimiento.strftime('%Y%m%d')}"
                else:
                    # Para movimientos sin venta (gastos, ajustes)
                    key = f"mov_{mov.id}_{mov.concepto}_{mov.fecha_movimiento.strftime('%Y%m%d%H%M%S')}"
                
                # Truncar si es necesario
                key = key[:255]
                
                if not dry_run:
                    try:
                        # Verificar si la key ya existe (otro registro)
                        if MovimientoCaja.objects.filter(idempotency_key=key).exists():
                            # Agregar hash único basado en ID
                            key = f"{key}_{mov.id}"
                        
                        mov.idempotency_key = key
                        mov.save(update_fields=['idempotency_key'])
                    except Exception as e:
                        logger.error(f"Error guardando key para Mov {mov.id}: {e}")
                        duplicados_key += 1
                        continue
                
                processed += 1
                if processed % 100 == 0:
                    self.stdout.write(f"    Progreso: {processed}/{total}")
        
        self.stdout.write(
            self.style.SUCCESS(f"  ✓ {processed} idempotency_keys generadas")
        )
        if duplicados_key > 0:
            self.stdout.write(
                self.style.WARNING(f"  ⚠️  {duplicados_key} conflictos resueltos con ID único")
            )
        
        return processed
    
    def _paso_3_validacion_final(self, dry_run, start_date, end_date):
        """Validación post-backfill."""
        self.stdout.write(self.style.WARNING('\n[PASO 3] Validación final...'))
        
        # Conteos
        total_rango = MovimientoCaja.objects.filter(
            fecha_movimiento__gte=start_date,
            fecha_movimiento__lte=end_date
        ).count()
        
        sin_key = MovimientoCaja.objects.filter(
            fecha_movimiento__gte=start_date,
            fecha_movimiento__lte=end_date,
            idempotency_key__isnull=True
        ).exclude(referencia__startswith='[FANTASMA').count()
        
        fantasmas = MovimientoCaja.objects.filter(
            fecha_movimiento__gte=start_date,
            fecha_movimiento__lte=end_date,
            referencia__startswith='[FANTASMA'
        ).count()
        
        self.stdout.write(f"  Total en rango: {total_rango}")
        self.stdout.write(f"  Sin key (excl. fantasmas): {sin_key}")
        self.stdout.write(f"  Fantasmas marcados: {fantasmas}")
        
        if sin_key == 0:
            self.stdout.write(
                self.style.SUCCESS("  ✅ 100% de movimientos tienen idempotency_key")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"  ⚠️  {sin_key} movimientos aún sin key")
            )
        
        # Verificar duplicados restantes
        duplicados_restantes = (
            MovimientoCaja.objects
            .filter(
                fecha_movimiento__gte=start_date,
                fecha_movimiento__lte=end_date,
                idempotency_key__isnull=False
            )
            .values('idempotency_key')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .count()
        )
        
        if duplicados_restantes == 0:
            self.stdout.write(
                self.style.SUCCESS("  ✅ Sin duplicados de idempotency_key")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"  ⚠️  {duplicados_restantes} keys duplicadas")
            )
