"""
AUDITAR FARMACIA INTEGRIDAD — Botón de Pánico v1.13
====================================================

Verifica que la integridad entre Kardex y Stock de Productos sea matemática:
    ∑ MovimientosKardex = Stock_Producto

Este comando es el "botón de pánico" para detectar:
- Desfases entre Kardex y stock declarado
- Ventas que no descontaron inventario
- Movimientos huérfanos sin venta asociada
- Productos con stock negativo

AUTOMATIZACIÓN CI/CD:
    python manage.py auditar_farmacia_integridad
    echo $?  # 0 = OK, 1 = ERRORES CRÍTICOS, 2 = WARNINGS

Autor: Windsurf Cascade
Fecha: 2026-04-03
"""

import logging
import sys
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import Sum, F, Q, Count, OuterRef, Subquery
from core.models import Venta, Producto
from farmacia.models import MovimientoInventario, CierreTurnoFarmacia, AperturaCaja

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Auditoría de integridad Farmacia — Verifica ∑Kardex = Stock_Producto (Botón de Pánico v1.13)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=int,
            help='Filtrar por ID de empresa',
        )
        parser.add_argument(
            '--producto',
            type=int,
            help='Auditar producto específico (ID)',
        )
        parser.add_argument(
            '--reparar',
            action='store_true',
            help='Intentar reparar desfases automáticamente (¡cuidado!)',
        )
        parser.add_argument(
            '--alertas',
            action='store_true',
            help='Solo mostrar alertas críticas (omitir OKs)',
        )
        parser.add_argument(
            '--exit-code-warnings',
            action='store_true',
            help='Exit code 2 si solo hay warnings (sin --reparar)',
        )

    def handle(self, *args, **options):
        self.empresa_id = options.get('empresa')
        self.producto_id = options.get('producto')
        self.reparar = options['reparar']
        self.solo_alertas = options['alertas']

        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))
        self.stdout.write(self.style.MIGRATE_HEADING('AUDITORÍA FARMACIA INTEGRIDAD — Botón de Pánico v1.13'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))

        if self.reparar:
            self.stdout.write(self.style.ERROR('\n⚠️  MODO REPARACIÓN ACTIVADO — Se modificarán datos\n'))

        total_errores = 0

        # 1. Verificar integridad Kardex vs Stock
        total_errores += self.auditar_kardex_vs_stock()

        # 2. Verificar ventas sin descuento de inventario
        total_errores += self.auditar_ventas_sin_descuento()

        # 3. Verificar cierres de caja sin apertura activa
        total_errores += self.auditar_cierres_caja()

        # 4. Verificar aperturas sin cierre
        total_errores += self.auditar_aperturas_huerfanas()

        # 5. Verificar productos con stock negativo
        total_errores += self.auditar_stock_negativo()

        # Resumen final
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '=' * 70))
        
        # FIX v1.13: Exit codes para CI/CD
        # 0 = OK, 1 = Errores críticos, 2 = Solo warnings
        exit_code = 0
        total_warnings = self.auditar_cierres_caja() + self.auditar_aperturas_huerfanas()
        
        if total_errores == 0:
            self.stdout.write(self.style.SUCCESS('🎉 INTEGRIDAD VERIFICADA — No se encontraron desfases'))
            if total_warnings > 0 and options.get('exit_code_warnings'):
                exit_code = 2  # Solo warnings
        else:
            self.stdout.write(self.style.ERROR(f'⚠️  SE ENCONTRARON {total_errores} PROBLEMAS DE INTEGRIDAD'))
            if not self.reparar:
                self.stdout.write(self.style.NOTICE('\nEjecute con --reparar para intentar corrección automática.'))
            exit_code = 1  # Errores críticos
        
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))
        
        # FIX v1.13: Exit code para automatización
        if exit_code != 0:
            sys.exit(exit_code)

    def auditar_kardex_vs_stock(self):
        """Verifica que ∑(entradas - salidas) en Kardex = stock del producto"""
        if not self.solo_alertas:
            self.stdout.write(self.style.NOTICE('\n📊 1. Verificando Kardex vs Stock de Productos...'))

        productos_query = Producto.objects.all()
        if self.empresa_id:
            productos_query = productos_query.filter(empresa_id=self.empresa_id)
        if self.producto_id:
            productos_query = productos_query.filter(id=self.producto_id)

        errores = 0
        productos_revisados = 0

        for producto in productos_query.iterator(chunk_size=100):
            productos_revisados += 1

            # Calcular stock teórico desde Kardex
            kardex_sums = MovimientoInventario.objects.filter(
                producto=producto,
            ).aggregate(
                entradas=Sum('cantidad', filter=Q(tipo_movimiento__startswith='ENTRADA')),
                salidas=Sum('cantidad', filter=Q(tipo_movimiento__startswith='SALIDA')),
            )

            entradas = kardex_sums['entradas'] or Decimal('0')
            salidas = kardex_sums['salidas'] or Decimal('0')
            stock_teorico = entradas - salidas
            stock_declarado = producto.stock or Decimal('0')

            diferencia = abs(stock_teorico - stock_declarado)

            if diferencia > Decimal('0.0001'):
                errores += 1
                self.stdout.write(self.style.ERROR(
                    f"   ❌ Producto #{producto.id} ({producto.nombre[:30]}): "
                    f"Stock declarado={stock_declarado}, Stock Kardex={stock_teorico}, "
                    f"Diferencia={diferencia}"
                ))

                if self.reparar:
                    producto.stock = stock_teorico
                    producto.save(update_fields=['stock'])
                    self.stdout.write(self.style.WARNING(f"      → Stock corregido a {stock_teorico}"))

        if not self.solo_alertas:
            self.stdout.write(f"   Productos revisados: {productos_revisados}, Errores: {errores}")

        return errores

    def auditar_ventas_sin_descuento(self):
        """Detecta ventas completadas sin movimientos de salida o sin flag inventario_descontado"""
        if not self.solo_alertas:
            self.stdout.write(self.style.NOTICE('\n📊 2. Verificando Ventas sin Descuento de Inventario...'))

        ventas_query = Venta.objects.filter(
            estado__in=['COMPLETADA', 'PAGADO', 'COMPLETADO'],
        )
        if self.empresa_id:
            ventas_query = ventas_query.filter(empresa_id=self.empresa_id)

        # Ventas completadas SIN movimientos de salida
        ventas_sin_movimiento = ventas_query.exclude(
            id__in=MovimientoInventario.objects.filter(
                tipo_movimiento='SALIDA_VENTA',
            ).values('venta_id')
        )

        count_sin_mov = ventas_sin_movimiento.count()

        # Ventas con movimientos pero sin flag inventario_descontado
        ventas_con_mov_sin_flag = ventas_query.filter(
            inventario_descontado=False,
        ).filter(
            id__in=MovimientoInventario.objects.filter(
                tipo_movimiento='SALIDA_VENTA',
            ).values('venta_id')
        )

        count_sin_flag = ventas_con_mov_sin_flag.count()

        if count_sin_mov > 0:
            self.stdout.write(self.style.ERROR(
                f"   ❌ {count_sin_mov} ventas completadas SIN movimientos de salida en Kardex"
            ))
            for v in ventas_sin_movimiento[:5]:
                self.stdout.write(f"      • Venta #{v.id} | {v.fecha.strftime('%Y-%m-%d')} | ${v.total}")

        if count_sin_flag > 0:
            self.stdout.write(self.style.WARNING(
                f"   ⚠️  {count_sin_flag} ventas con movimientos pero SIN flag inventario_descontado"
            ))
            if self.reparar:
                ventas_con_mov_sin_flag.update(inventario_descontado=True)
                self.stdout.write(self.style.WARNING(f"      → Flags corregidos"))

        if not self.solo_alertas and count_sin_mov == 0 and count_sin_flag == 0:
            self.stdout.write(self.style.SUCCESS("   ✅ Todas las ventas sincronizadas correctamente"))

        return count_sin_mov + count_sin_flag

    def auditar_cierres_caja(self):
        """Verifica que los cierres tengan apertura activa"""
        if not self.solo_alertas:
            self.stdout.write(self.style.NOTICE('\n📊 3. Verificando Cierres de Caja...'))

        cierres_query = CierreTurnoFarmacia.objects.all()
        if self.empresa_id:
            cierres_query = cierres_query.filter(empresa_id=self.empresa_id)

        # Cierres con apertura inactiva (inconsistencia)
        cierres_mal = cierres_query.filter(
            apertura_caja__isnull=False,
            apertura_caja__activa=True,  # Debería ser False si ya hay cierre
        )

        count = cierres_mal.count()

        if count > 0:
            self.stdout.write(self.style.WARNING(
                f"   ⚠️  {count} cierres con apertura aún marcada como activa"
            ))
            if self.reparar:
                for cierre in cierres_mal:
                    cierre.apertura_caja.cerrar_caja()
                self.stdout.write(self.style.WARNING(f"      → Aperturas cerradas correctamente"))
        elif not self.solo_alertas:
            self.stdout.write(self.style.SUCCESS("   ✅ Cierres de caja consistentes"))

        return count

    def auditar_aperturas_huerfanas(self):
        """Detecta aperturas antiguas sin cierre (posible olvido)"""
        if not self.solo_alertas:
            self.stdout.write(self.style.NOTICE('\n📊 4. Verificando Aperturas Huérfanas...'))

        from datetime import timedelta
        from django.utils import timezone

        aperturas_query = AperturaCaja.objects.filter(
            activa=True,
            fecha_apertura__lt=timezone.now() - timedelta(days=1),
        )
        if self.empresa_id:
            aperturas_query = aperturas_query.filter(empresa_id=self.empresa_id)

        count = aperturas_query.count()

        if count > 0:
            self.stdout.write(self.style.WARNING(
                f"   ⚠️  {count} aperturas antiguas (>24h) sin cerrar"
            ))
            for a in aperturas_query[:5]:
                self.stdout.write(f"      • {a.folio} | {a.fecha_apertura.strftime('%Y-%m-%d %H:%M')} | {a.usuario_responsable}")
        elif not self.solo_alertas:
            self.stdout.write(self.style.SUCCESS("   ✅ No hay aperturas huérfanas"))

        return 0  # Esto es informativo, no es error crítico

    def auditar_stock_negativo(self):
        """Detecta productos con stock negativo (inconsistencia grave)"""
        if not self.solo_alertas:
            self.stdout.write(self.style.NOTICE('\n📊 5. Verificando Stock Negativo...'))

        productos_query = Producto.objects.filter(stock__lt=0)
        if self.empresa_id:
            productos_query = productos_query.filter(empresa_id=self.empresa_id)
        if self.producto_id:
            productos_query = productos_query.filter(id=self.producto_id)

        count = productos_query.count()

        if count > 0:
            self.stdout.write(self.style.ERROR(
                f"   ❌ {count} productos con STOCK NEGATIVO (¡CRÍTICO!)"
            ))
            for p in productos_query[:10]:
                self.stdout.write(self.style.ERROR(
                    f"      • #{p.id} {p.nombre[:30]}: stock={p.stock}"
                ))
        elif not self.solo_alertas:
            self.stdout.write(self.style.SUCCESS("   ✅ No hay stock negativo"))

        return count
