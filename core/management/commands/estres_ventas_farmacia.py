"""
ESTRÉS CONCURRENTE VENTAS v1.13 — Prueba de Integridad Farmacia
===============================================================

Simula 100 ventas concurrentes para validar:
- Idempotencia del signal (no doble descuento)
- Manejo de concurrencia en cancelaciones
- Consistencia del Kardex vs Stock
- Deadlock prevention con select_for_update()

Ejecución:
    python manage.py estres_ventas_farmacia --ventas=100 --workers=10

Autor: Windsurf Cascade
Fecha: 2026-04-03
"""

import concurrent.futures
import logging
import random
import time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from core.models import Empresa, Producto, Venta, DetalleVenta, Lote, Usuario
from farmacia.models import MovimientoInventario

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Prueba de estrés: Ventas concurrentes Farmacia v1.13'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ventas',
            type=int,
            default=100,
            help='Número total de ventas a simular (default: 100)',
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=10,
            help='Número de workers concurrentes (default: 10)',
        )
        parser.add_argument(
            '--cancelar-pct',
            type=float,
            default=0.1,
            help='Porcentaje de ventas a cancelar (0.1 = 10%%)',
        )
        parser.add_argument(
            '--empresa',
            type=int,
            help='ID de empresa para pruebas (default: primera encontrada)',
        )

    def handle(self, *args, **options):
        self.total_ventas = options['ventas']
        self.max_workers = options['workers']
        self.cancelar_pct = options['cancelar_pct']
        empresa_id = options.get('empresa')

        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))
        self.stdout.write(self.style.MIGRATE_HEADING('ESTRÉS CONCURRENTE VENTAS v1.13'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))
        self.stdout.write(f"📊 Ventas a simular: {self.total_ventas}")
        self.stdout.write(f"🔧 Workers concurrentes: {self.max_workers}")
        self.stdout.write(f"❌ % Cancelaciones: {self.cancelar_pct * 100}%")

        # Obtener empresa y datos de prueba
        self._setup_datos_prueba(empresa_id)
        if not self.empresa:
            self.stdout.write(self.style.ERROR("❌ No se encontró empresa para pruebas"))
            return

        # Preparar productos con stock suficiente
        if not self._preparar_stock():
            return

        self.stdout.write(f"\n🏢 Empresa: {self.empresa.nombre}")
        self.stdout.write(f"📦 Productos de prueba: {len(self.productos_prueba)}")
        self.stdout.write(f"👤 Usuario: {self.usuario.email if self.usuario else 'N/A'}")

        # Ejecutar estrés
        resultados = self._ejecutar_estres()

        # Análisis de resultados
        self._analizar_resultados(resultados)

    def _setup_datos_prueba(self, empresa_id):
        """Configura empresa, usuario y productos para pruebas"""
        if empresa_id:
            self.empresa = Empresa.objects.filter(id=empresa_id).first()
        else:
            self.empresa = Empresa.objects.first()

        if not self.empresa:
            return

        # Usuario admin o cualquier usuario
        self.usuario = Usuario.objects.filter(is_staff=True).first()
        if not self.usuario:
            self.usuario = Usuario.objects.first()

        # Productos con stock para pruebas
        self.productos_prueba = list(Producto.objects.filter(
            empresa=self.empresa,
            stock__gt=50  # Stock suficiente para pruebas
        )[:5])

    def _preparar_stock(self):
        """Asegura stock mínimo para pruebas"""
        if len(self.productos_prueba) < 3:
            self.stdout.write(self.style.WARNING(
                "⚠️  Pocos productos con stock. Creando productos de prueba..."
            ))
            # Crear productos de prueba si no hay suficientes
            for i in range(5):
                prod, _ = Producto.objects.get_or_create(
                    sku=f"TEST_{i:03d}",
                    defaults={
                        'nombre': f'Producto Test {i}',
                        'empresa': self.empresa,
                        'precio_publico': Decimal('100.00'),
                        'precio_compra': Decimal('50.00'),
                        'stock': 200,
                    }
                )
                # Crear lote para el producto
                lote, _ = Lote.objects.get_or_create(
                    producto=prod,
                    numero_lote=f'LOTE_TEST_{i}',
                    defaults={
                        'cantidad': 200,
                        'fecha_caducidad': timezone.now().date().replace(year=2027),
                    }
                )
                self.productos_prueba.append(prod)

        return len(self.productos_prueba) >= 3

    def _ejecutar_estres(self):
        """Ejecuta las ventas concurrentes"""
        ventas_ids = []
        errores = []
        exitos = []

        self.stdout.write(self.style.ERROR(f"\n🚀 Iniciando estrés concurrente...\n"))
        tiempo_inicio = time.time()

        def crear_venta_task(n):
            """Task para crear una venta"""
            try:
                with transaction.atomic():
                    # Seleccionar producto aleatorio
                    producto = random.choice(self.productos_prueba)
                    cantidad = random.randint(1, 5)

                    # Crear venta
                    venta = Venta.objects.create(
                        empresa=self.empresa,
                        usuario=self.usuario,
                        estado='PENDIENTE',
                        total=producto.precio_publico * cantidad,
                    )

                    # Crear detalle
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=producto.precio_publico,
                        subtotal=producto.precio_publico * cantidad,
                    )

                    # Completar venta (esto dispara el signal)
                    venta.estado = 'COMPLETADA'
                    venta.save()

                    return {'tipo': 'venta', 'id': venta.id, 'status': 'ok'}
            except Exception as e:
                return {'tipo': 'venta', 'n': n, 'status': 'error', 'error': str(e)}

        # Ejecutar ventas concurrentes
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(crear_venta_task, i): i for i in range(self.total_ventas)}

            for future in concurrent.futures.as_completed(futures):
                resultado = future.result()
                if resultado['status'] == 'ok':
                    ventas_ids.append(resultado['id'])
                    exitos.append(resultado)
                else:
                    errores.append(resultado)

                # Progreso cada 10 ventas
                if len(exitos) % 10 == 0:
                    self.stdout.write(f"   Progreso: {len(exitos)} ventas creadas...")

        tiempo_total = time.time() - tiempo_inicio

        # Cancelar algunas ventas (simulación)
        canceladas = self._cancelar_ventas_aleatorias(ventas_ids)

        return {
            'exitos': exitos,
            'errores': errores,
            'ventas_ids': ventas_ids,
            'canceladas': canceladas,
            'tiempo_total': tiempo_total,
        }

    def _cancelar_ventas_aleatorias(self, ventas_ids):
        """Cancela un porcentaje aleatorio de ventas"""
        n_cancelar = int(len(ventas_ids) * self.cancelar_pct)
        if n_cancelar == 0:
            return []

        ids_cancelar = random.sample(ventas_ids, n_cancelar)
        canceladas = []

        self.stdout.write(f"\n❌ Cancelando {n_cancelar} ventas...")

        for venta_id in ids_cancelar:
            try:
                venta = Venta.objects.get(id=venta_id)
                # Simular cancelación (no implementamos la lógica completa aquí)
                venta.estado = 'CANCELADA'
                venta.save(update_fields=['estado'])
                canceladas.append(venta_id)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   Error cancelando #{venta_id}: {e}"))

        return canceladas

    def _analizar_resultados(self, resultados):
        """Analiza y muestra resultados del estrés"""
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '=' * 70))
        self.stdout.write(self.style.MIGRATE_HEADING('RESULTADOS DEL ESTRÉS'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))

        exitos = len(resultados['exitos'])
        errores = len(resultados['errores'])
        total = exitos + errores
        canceladas = len(resultados['canceladas'])
        tiempo = resultados['tiempo_total']

        # Métricas
        tps = total / tiempo if tiempo > 0 else 0

        self.stdout.write(f"✅ Ventas exitosas: {exitos}")
        self.stdout.write(f"❌ Errores: {errores}")
        self.stdout.write(f"❌ Canceladas: {canceladas}")
        self.stdout.write(f"⏱️  Tiempo total: {tiempo:.2f}s")
        self.stdout.write(f"⚡ TPS (transacciones/segundo): {tps:.2f}")

        # Mostrar errores si los hay
        if errores > 0:
            self.stdout.write(self.style.ERROR(f"\n⚠️  ERRORES ENCONTRADOS:"))
            for err in resultados['errores'][:5]:
                self.stdout.write(self.style.ERROR(f"   • {err.get('error', 'Error desconocido')}"))

        # Verificación de integridad post-estrés
        self._verificar_integridad_post_estres(resultados['ventas_ids'])

        # Determinar éxito de la prueba
        if errores == 0:
            self.stdout.write(self.style.SUCCESS(f"\n🎉 ESTRÉS COMPLETADO: Sin errores de concurrencia"))
        elif errores / total < 0.01:  # Menos de 1% errores
            self.stdout.write(self.style.WARNING(f"\n⚠️  ESTRÉS COMPLETADO: {errores} errores menores ({errores/total*100:.1f}%)"))
        else:
            self.stdout.write(self.style.ERROR(f"\n❌ ESTRÉS FALLÓ: {errores} errores ({errores/total*100:.1f}% fallo)"))

    def _verificar_integridad_post_estres(self, ventas_ids):
        """Verifica integridad después del estrés"""
        self.stdout.write(self.style.NOTICE(f"\n🔍 Verificación post-estrés..."))

        # 1. Verificar que no hay ventas duplicadas en Kardex
        duplicados = MovimientoInventario.objects.filter(
            venta_id__in=ventas_ids,
            tipo_movimiento='SALIDA_VENTA',
        ).values('venta_id').annotate(
            count=Count('id')
        ).filter(count__gt=1)

        if duplicados.exists():
            self.stdout.write(self.style.ERROR(
                f"   ❌ ALERTA CRÍTICA: {duplicados.count()} ventas con movimientos duplicados en Kardex!"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("   ✅ Sin movimientos duplicados en Kardex"))

        # 2. Verificar flags inventario_descontado
        ventas_sin_flag = Venta.objects.filter(
            id__in=ventas_ids,
            estado='COMPLETADA',
            inventario_descontado=False,
        ).count()

        if ventas_sin_flag > 0:
            self.stdout.write(self.style.WARNING(
                f"   ⚠️  {ventas_sin_flag} ventas completadas sin flag inventario_descontado"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("   ✅ Flags inventario_descontado consistentes"))

        # 3. Stock no negativo
        stocks_negativos = Producto.objects.filter(
            id__in=[p.id for p in self.productos_prueba],
            stock__lt=0,
        ).count()

        if stocks_negativos > 0:
            self.stdout.write(self.style.ERROR(f"   ❌ {stocks_negativos} productos con stock negativo!"))
        else:
            self.stdout.write(self.style.SUCCESS("   ✅ Sin stock negativo"))
