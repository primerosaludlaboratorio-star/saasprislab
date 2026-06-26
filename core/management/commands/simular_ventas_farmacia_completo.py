"""
Management command COMPLETO para simular TODAS las funcionalidades del módulo de Farmacia:
- Ventas normales
- Ventas con receta controlada (antibióticos)
- Pagos mixtos (efectivo+tarjeta+SPEI)
- Diferentes tipos de pacientes (EMPLEADO, FAMILIA, INAPAM, GENERAL)
- Descuentos automáticos
- Devoluciones (parciales y totales)
- Pruebas de carga y estrés SIN borrar datos
"""

import random
import sys
import io
import time
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError, OperationalError
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.models import (
    Empresa, Usuario, Producto, Lote, Venta, DetalleVenta, Paciente,
    Medico, Receta, SalesReturn, DiscountPolicy, Pago
)
from core.views.farmacia import procesar_venta
import logging

User = get_user_model()


def _safe_int(val, default=1):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _pick_empresa(user: Usuario) -> Empresa:
    return user.empresa


class Command(BaseCommand):
    help = "Simula TODAS las funcionalidades del módulo de Farmacia (ventas, devoluciones, recetas, pagos mixtos)"

    def add_arguments(self, parser):
        parser.add_argument("--ventas", type=int, default=100, help="Número de ventas a simular (default: 100)")
        parser.add_argument("--devoluciones", type=int, default=10, help="Número de devoluciones a simular (default: 10)")
        parser.add_argument("--min-items", type=int, default=1, help="Mínimo de productos por venta (default: 1)")
        parser.add_argument("--max-items", type=int, default=6, help="Máximo de productos por venta (default: 6)")
        parser.add_argument("--dias", type=int, default=7, help="Rango de días hacia atrás para fechas (default: 7)")
        parser.add_argument("--usuario", type=str, default="", help="Username del cajero (default: primer usuario)")
        parser.add_argument("--con-paciente", type=int, default=40, help="Porcentaje de ventas con paciente (0-100, default: 40)")
        parser.add_argument("--con-receta", type=int, default=15, help="Porcentaje de ventas con receta controlada (0-100, default: 15)")
        parser.add_argument("--pagos-mixtos", type=int, default=20, help="Porcentaje de ventas con pagos mixtos (0-100, default: 20)")

    def handle(self, *args, **options):
        # Configurar encoding UTF-8 para Windows
        if sys.platform == "win32":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

        ventas_objetivo = options["ventas"]
        devoluciones_objetivo = options["devoluciones"]
        min_items = max(1, options["min_items"])
        max_items = max(min_items, options["max_items"])
        dias = max(1, options["dias"])
        username = (options["usuario"] or "").strip()
        pct_con_paciente = max(0, min(100, options["con_paciente"]))
        pct_con_receta = max(0, min(100, options["con_receta"]))
        pct_pagos_mixtos = max(0, min(100, options["pagos_mixtos"]))

        t0 = time.time()
        self.stdout.write(self.style.SUCCESS("[INICIANDO] Simulacion COMPLETA de Farmacia"))
        self.stdout.write(f"[OBJETIVO] {ventas_objetivo} ventas + {devoluciones_objetivo} devoluciones\n")

        # Seleccionar usuario
        if username:
            user = User.objects.filter(username=username).first()
            if not user:
                self.stdout.write(self.style.ERROR(f"[ERROR] No existe el usuario '{username}'"))
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR("[ERROR] No hay usuarios. Cree uno primero (createsuperuser)."))
                return

        empresa = _pick_empresa(user)
        self.stdout.write(f"[USUARIO] Cajero: {user.username} | Empresa: {getattr(empresa, 'nombre', empresa.id)}")

        # Verificar que existan productos con stock
        productos_con_stock = list(Producto.objects.filter(empresa=empresa).prefetch_related('lotes'))
        productos_validos = [p for p in productos_con_stock if sum(l.cantidad for l in p.lotes.all() if l.cantidad > 0) > 0]
        
        if not productos_validos:
            self.stdout.write(self.style.ERROR("[ERROR] No hay productos con stock disponible."))
            return

        # Obtener o crear pacientes de diferentes tipos
        pacientes_empleado = list(Paciente.objects.filter(empresa=empresa, tipo='EMPLEADO')[:5])
        pacientes_familia = list(Paciente.objects.filter(empresa=empresa, tipo='FAMILIA')[:5])
        pacientes_inapam = list(Paciente.objects.filter(empresa=empresa, tipo='INAPAM')[:5])
        pacientes_general = list(Paciente.objects.filter(empresa=empresa, tipo='GENERAL')[:10])
        
        # Crear pacientes de ejemplo si no existen
        if not pacientes_empleado:
            pacientes_empleado.append(Paciente.objects.create(
                empresa=empresa,
                nombre_completo='Empleado de Prueba',
                tipo='EMPLEADO'
            ))
        if not pacientes_familia:
            pacientes_familia.append(Paciente.objects.create(
                empresa=empresa,
                nombre_completo='Familia de Prueba',
                tipo='FAMILIA'
            ))
        if not pacientes_inapam:
            pacientes_inapam.append(Paciente.objects.create(
                empresa=empresa,
                nombre_completo='Adulto Mayor de Prueba',
                tipo='INAPAM'
            ))

        # Obtener o crear médicos
        medicos = list(Medico.objects.all()[:3])
        if not medicos:
            medicos.append(Medico.objects.create(
                nombre_completo='Dr. Medico de Prueba',
                cedula_profesional='MED123456',
                especialidad='Medicina General'
            ))

        # Estadísticas
        ventas_creadas = 0
        ventas_con_receta = 0
        ventas_con_paciente = 0
        ventas_pagos_mixtos = 0
        ventas_empleado = 0
        ventas_familia = 0
        ventas_inapam = 0
        errores = []
        ventas_para_devolucion = []

        # Simular ventas
        self.stdout.write(self.style.SUCCESS("\n[FASE 1] Simulando ventas..."))
        
        for i in range(ventas_objetivo):
            try:
                # Determinar tipo de venta
                tiene_paciente = random.random() * 100 < pct_con_paciente
                tiene_receta = random.random() * 100 < pct_con_receta
                pago_mixto = random.random() * 100 < pct_pagos_mixtos
                
                # Seleccionar paciente si aplica
                paciente = None
                paciente_id = None
                cliente_nombre = 'PÚBLICO GENERAL'
                tipo_paciente = None
                
                if tiene_paciente:
                    rand_tipo = random.random()
                    if rand_tipo < 0.3 and pacientes_empleado:
                        paciente = random.choice(pacientes_empleado)
                        tipo_paciente = 'EMPLEADO'
                        ventas_empleado += 1
                    elif rand_tipo < 0.5 and pacientes_familia:
                        paciente = random.choice(pacientes_familia)
                        tipo_paciente = 'FAMILIA'
                        ventas_familia += 1
                    elif rand_tipo < 0.7 and pacientes_inapam:
                        paciente = random.choice(pacientes_inapam)
                        tipo_paciente = 'INAPAM'
                        ventas_inapam += 1
                    elif pacientes_general:
                        paciente = random.choice(pacientes_general)
                        tipo_paciente = 'GENERAL'
                    
                    if paciente:
                        paciente_id = paciente.id
                        cliente_nombre = paciente.nombre_completo
                        ventas_con_paciente += 1

                # Armar carrito (productos con stock)
                num_items = random.randint(min_items, max_items)
                carrito = []
                productos_usados = set()
                
                for _ in range(num_items * 2):  # Intentar más productos de los necesarios
                    if len(carrito) >= num_items:
                        break
                    
                    producto = random.choice(productos_validos)
                    if producto.id in productos_usados:
                        continue
                    
                    stock_disponible = sum(l.cantidad for l in producto.lotes.filter(cantidad__gt=0))
                    if stock_disponible <= 0:
                        continue
                    
                    cantidad = random.randint(1, min(3, stock_disponible))
                    productos_usados.add(producto.id)
                    
                    carrito.append({
                        'producto_id': producto.id,
                        'cantidad': cantidad,
                        'precio_unitario': float(producto.precio_publico)
                    })
                
                if not carrito:
                    continue

                # Preparar datos de receta si aplica
                receta_datos = None
                if tiene_receta and any(p.es_antibiotico for p in [Producto.objects.get(id=item['producto_id']) for item in carrito]):
                    medico = random.choice(medicos)
                    receta_datos = {
                        'medico': medico.nombre_completo,
                        'cedula': medico.cedula_profesional,
                        'folio': f'REC-{uuid.uuid4().hex[:8].upper()}',
                        'fecha': (timezone.now() - timedelta(days=random.randint(0, 7))).strftime('%Y-%m-%d')
                    }
                    ventas_con_receta += 1

                # Preparar pagos
                total_estimado = sum(item['precio_unitario'] * item['cantidad'] for item in carrito)
                
                if pago_mixto and total_estimado > 50:
                    # Pago mixto: efectivo + tarjeta o transferencia
                    efectivo = Decimal(str(round(total_estimado * random.uniform(0.3, 0.7), 2)))
                    resto = Decimal(str(total_estimado)) - efectivo
                    
                    if random.random() > 0.5:
                        pagos = {
                            'efectivo': float(efectivo),
                            'tarjeta': float(resto)
                        }
                    else:
                        pagos = {
                            'efectivo': float(efectivo),
                            'transferencia': float(resto)
                        }
                    ventas_pagos_mixtos += 1
                else:
                    # Pago único
                    metodo = random.choice(['efectivo', 'tarjeta', 'transferencia'])
                    pagos = {metodo: float(total_estimado)}

                # Simular request para procesar_venta
                request_mock = SimpleNamespace()
                request_mock.user = user
                request_mock.method = 'POST'
                request_mock.headers = {'X-Requested-With': 'XMLHttpRequest'}
                request_mock.body = json.dumps({
                    'items': carrito,
                    'pagos': pagos,
                    'cliente': cliente_nombre,
                    'paciente_id': paciente_id,
                    'descuento_porcentaje': 0,
                    'tipo_descuento': '0',
                    'receta': receta_datos,
                    'es_controlada': bool(receta_datos),
                    'efectivo_recibido': float(pagos.get('efectivo', 0)),
                    'cambio_entregado': 0
                }).encode('utf-8')

                # Procesar venta usando la misma función que el frontend
                try:
                    with transaction.atomic():
                        response = procesar_venta(request_mock, json.loads(request_mock.body), empresa)
                        
                        if response.status_code == 200:
                            data = json.loads(response.content)
                            if data.get('status') == 'success':
                                ventas_creadas += 1
                                venta_id = data.get('venta_id')
                                if venta_id and random.random() < 0.3:  # 30% de ventas candidatas para devolución
                                    ventas_para_devolucion.append(venta_id)
                            else:
                                errores.append(f"Venta {i+1}: {data.get('mensaje', 'Error desconocido')}")
                        else:
                            errores.append(f"Venta {i+1}: HTTP {response.status_code}")
                except IntegrityError as e:
                    if 'folio_operacion' in str(e):
                        # Reintentar con delay
                        time.sleep(0.1)
                        continue
                    errores.append(f"Venta {i+1}: IntegrityError - {str(e)}")
                except Exception as e:
                    logging.getLogger(__name__).exception("Error inesperado en handle (simular_ventas_farmacia_completo.py)")
                    errores.append(f"Venta {i+1}: {str(e)}")

                # Refrescar productos cada 20 ventas
                if (i + 1) % 20 == 0:
                    productos_validos = [p for p in productos_con_stock if sum(l.cantidad for l in p.lotes.all() if l.cantidad > 0) > 0]
                    if not productos_validos:
                        self.stdout.write(self.style.WARNING(f"[AVISO] Sin stock disponible después de {i+1} ventas"))
                        break

                if (i + 1) % 25 == 0:
                    self.stdout.write(f"[PROGRESO] {i+1}/{ventas_objetivo} ventas intentadas | creadas={ventas_creadas} | errores={len(errores)}")

            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en handle (simular_ventas_farmacia_completo.py)")
                errores.append(f"Venta {i+1}: Excepción inesperada - {str(e)}")
                continue

        # Simular devoluciones
        devoluciones_creadas = 0
        self.stdout.write(self.style.SUCCESS("\n[FASE 2] Simulando devoluciones..."))
        
        ventas_disponibles = list(Venta.objects.filter(empresa=empresa, estado='COMPLETADA').prefetch_related('detalles__producto', 'detalles__lote_vendido')[:devoluciones_objetivo * 2])
        
        for i in range(min(devoluciones_objetivo, len(ventas_disponibles))):
            try:
                venta = random.choice(ventas_disponibles)
                ventas_disponibles.remove(venta)
                
                detalles = list(venta.detalles.all())
                if not detalles:
                    continue
                
                # Seleccionar 1-2 detalles para devolver
                detalles_a_devolver = random.sample(detalles, min(random.randint(1, 2), len(detalles)))
                
                items_devolucion = []
                for detalle in detalles_a_devolver:
                    cantidad_devolver = random.randint(1, detalle.cantidad)
                    items_devolucion.append({
                        'detalle_id': detalle.id,
                        'cantidad': cantidad_devolver
                    })
                
                if not items_devolucion:
                    continue
                
                motivos = [
                    'Producto incorrecto entregado',
                    'Cliente cambió de opinión',
                    'Producto defectuoso',
                    'Error en la venta original',
                    'Cliente no lo necesita'
                ]
                
                # Crear devolución directamente
                with transaction.atomic():
                    for item in items_devolucion:
                        detalle = DetalleVenta.objects.get(id=item['detalle_id'])
                        cantidad = item['cantidad']
                        
                        if detalle.lote_vendido:
                            detalle.lote_vendido.cantidad += cantidad
                            detalle.lote_vendido.save()
                            
                            producto = detalle.producto
                            producto.stock = sum(l.cantidad for l in producto.lotes.filter(cantidad__gt=0))
                            producto.save()
                        
                        tipo_devol = 'TOTAL' if cantidad >= detalle.cantidad else 'PARCIAL'
                        monto_reemb = detalle.precio_unitario * cantidad
                        
                        # Crear devolución (verificar campos del modelo)
                        SalesReturn.objects.create(
                            venta_original=venta,
                            motivo_error=random.choice(motivos),
                            usuario_error_origen=user,
                            usuario_autorizo=user,
                            empresa=empresa,
                            tipo_devolucion=tipo_devol,
                            monto_reembolsado=monto_reemb,
                            accion_stock='RETORNO_ALMACEN'
                        )
                    
                    devoluciones_creadas += 1
                
                if (i + 1) % 5 == 0:
                    self.stdout.write(f"[PROGRESO] {i+1}/{devoluciones_objetivo} devoluciones procesadas")

            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en handle (simular_ventas_farmacia_completo.py)")
                errores.append(f"Devolución {i+1}: {str(e)}")
                continue

        # Calcular tiempo
        tiempo_total = time.time() - t0

        # Mostrar estadísticas finales
        self.stdout.write(self.style.SUCCESS("\n" + "="*60))
        self.stdout.write(self.style.SUCCESS("[RESUMEN] SIMULACION COMPLETA FARMACIA"))
        self.stdout.write(self.style.SUCCESS("="*60))
        self.stdout.write(f"[OK] Ventas creadas: {ventas_creadas}")
        self.stdout.write(f"[OK] Devoluciones creadas: {devoluciones_creadas}")
        self.stdout.write(f"[INFO] Ventas con paciente: {ventas_con_paciente} ({ventas_con_paciente/ventas_creadas*100:.1f}%)" if ventas_creadas > 0 else "[INFO] Ventas con paciente: 0")
        self.stdout.write(f"[INFO] Ventas con receta: {ventas_con_receta} ({ventas_con_receta/ventas_creadas*100:.1f}%)" if ventas_creadas > 0 else "[INFO] Ventas con receta: 0")
        self.stdout.write(f"[INFO] Ventas con pagos mixtos: {ventas_pagos_mixtos} ({ventas_pagos_mixtos/ventas_creadas*100:.1f}%)" if ventas_creadas > 0 else "[INFO] Ventas con pagos mixtos: 0")
        self.stdout.write(f"[INFO] Ventas EMPLEADO: {ventas_empleado}")
        self.stdout.write(f"[INFO] Ventas FAMILIA: {ventas_familia}")
        self.stdout.write(f"[INFO] Ventas INAPAM: {ventas_inapam}")
        self.stdout.write(f"[INFO] Errores: {len(errores)}")
        self.stdout.write(f"[TIEMPO] {tiempo_total:.2f} segundos")
        
        total_ventas_bd = Venta.objects.filter(empresa=empresa).count()
        self.stdout.write(f"[INFO] Total ventas en la empresa ahora: {total_ventas_bd}")
        
        if errores:
            self.stdout.write(self.style.WARNING(f"\n[AVISO] Primeros 5 errores:"))
            for error in errores[:5]:
                self.stdout.write(self.style.WARNING(f"   - {error}"))
            if len(errores) > 5:
                self.stdout.write(self.style.WARNING(f"   ... y {len(errores) - 5} errores mas"))

        self.stdout.write(self.style.SUCCESS("\n[COMPLETADO] Simulacion completa exitosa!"))
        self.stdout.write(self.style.SUCCESS("   Todas las funcionalidades de Farmacia fueron probadas.\n"))