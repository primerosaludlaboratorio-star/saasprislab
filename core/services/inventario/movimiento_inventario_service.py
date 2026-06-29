"""
Servicio de dominio: entradas Kardex (compra, mercancía, ajustes por lote).
transaction.atomic vive aquí; las vistas solo parsean HTTP y devuelven JSON.
"""
import logging
import uuid as uuid_module
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import Sum
from django.utils.dateparse import parse_date

from core.models import AjusteInventario, Lote, Producto
from core.utils.trazabilidad import registrar_trazabilidad

logger_core = logging.getLogger('core')


class MovimientoInventarioService:
    """Operaciones atómicas sobre lotes y MovimientoInventario (farmacia Kardex)."""

    @staticmethod
    def _json_result(http_status: int, body: Dict[str, Any]) -> Dict[str, Any]:
        return {'http_status': http_status, 'body': body}

    @classmethod
    def entrada_mercancia_directa(cls, request, empresa, data: dict) -> Dict[str, Any]:
        """
        Ingreso rápido al almacén (producto + opcional lote + ENTRADA_COMPRA Kardex).
        `data` es el dict ya parseado (JSON o POST).
        """
        codigo = (data.get('codigo') or '').strip()
        nombre = (data.get('nombre') or '').strip()
        factura = (data.get('factura') or '').strip()
        lote_num = (data.get('lote') or '').strip()
        caducidad_str = (data.get('caducidad') or '').strip()
        try:
            cantidad = int(data.get('cantidad', 0) or 0)
        except (TypeError, ValueError):
            cantidad = 0
        costo_unitario = Decimal(str(data.get('costo_unitario', 0) or 0))
        precio_venta = Decimal(str(data.get('precio_venta', 0) or 0))
        categoria = data.get('categoria', 'GENERICO')
        es_controlado = data.get('es_controlado', False)

        if not nombre or cantidad <= 0:
            return cls._json_result(400, {
                'status': 'error',
                'mensaje': 'Faltan datos requeridos: nombre y cantidad son obligatorios',
            })
        if costo_unitario <= 0:
            return cls._json_result(400, {
                'status': 'error',
                'mensaje': 'El costo unitario debe ser mayor a cero',
            })

        fecha_caducidad = parse_date(caducidad_str) if caducidad_str else None

        try:
            with transaction.atomic():
                producto = None
                if codigo:
                    producto = Producto.objects.filter(
                        empresa=empresa,
                        codigo_barras=codigo,
                    ).first()

                if not producto:
                    if not codigo:
                        codigo = f"PRIS-{uuid_module.uuid4().hex[:8].upper()}"
                    producto = Producto.objects.create(
                        empresa=empresa,
                        codigo_barras=codigo,
                        nombre=nombre,
                        categoria=categoria,
                        es_antibiotico=es_controlado,
                        precio_compra=costo_unitario,
                        precio_publico=precio_venta if precio_venta > 0 else costo_unitario * Decimal('1.5'),
                        stock=0,
                    )
                else:
                    datos_antes = {
                        'precio_publico': str(producto.precio_publico) if producto.precio_publico else None,
                        'precio_compra': str(producto.precio_compra) if producto.precio_compra else None,
                    }
                    if nombre and producto.nombre != nombre:
                        producto.nombre = nombre
                    if precio_venta > 0:
                        producto.precio_publico = precio_venta
                    producto.precio_compra = costo_unitario
                    producto.save()
                    if (
                        datos_antes.get('precio_publico') != str(producto.precio_publico)
                        or datos_antes.get('precio_compra') != str(producto.precio_compra)
                    ):
                        from core.services.audit_service import registrar_auditoria
                        registrar_auditoria(
                            accion='UPDATE',
                            modelo='Producto',
                            objeto_id=str(producto.id),
                            datos_anteriores=datos_antes,
                            datos_nuevos={
                                'precio_publico': str(producto.precio_publico),
                                'precio_compra': str(producto.precio_compra),
                                'nombre': producto.nombre,
                            },
                            request=request,
                        )

                lote_obj = None
                if lote_num and fecha_caducidad:
                    lote_obj, _ = Lote.objects.get_or_create(
                        producto=producto,
                        numero_lote=lote_num,
                        defaults={
                            'fecha_caducidad': fecha_caducidad,
                            'cantidad': 0,
                            'costo_adquisicion': costo_unitario,
                        },
                    )

                try:
                    from farmacia.models import MovimientoInventario
                    MovimientoInventario.objects.create(
                        empresa=empresa,
                        producto=producto,
                        lote=lote_obj,
                        tipo_movimiento='ENTRADA_COMPRA',
                        cantidad=cantidad,
                        costo_unitario=costo_unitario,
                        observaciones=f'Entrada de mercancía - Lote: {lote_num or "S/L"}',
                        usuario_responsable=request.user,
                    )
                except Exception:
                    logging.getLogger(__name__).exception("Error inesperado en entrada_mercancia_directa (movimiento_inventario_service.py)")
                    producto.stock = (producto.stock or 0) + cantidad
                    producto.save()

                try:
                    registrar_trazabilidad(
                        usuario=request.user,
                        accion='ENTRADA_MERCANCIA',
                        modelo=producto,
                        detalles=f'Ingreso: {cantidad} pz, Lote: {lote_num or "N/A"}, Factura: {factura or "N/A"}',
                    )
                except Exception:
                    logging.getLogger(__name__).exception("Error inesperado en entrada_mercancia_directa (movimiento_inventario_service.py)")
                    pass

                producto.refresh_from_db()
                logger_core.info(
                    'Entrada de mercancía registrada: Producto=%s, Cantidad=%s, Lote=%s',
                    producto.nombre,
                    cantidad,
                    lote_num or 'N/A',
                )
                return cls._json_result(200, {
                    'status': 'success',
                    'mensaje': (
                        f'Ingreso registrado: {cantidad} piezas de {producto.nombre}. '
                        f'Stock actual: {producto.stock}'
                    ),
                    'producto_id': producto.id,
                    'stock_actual': producto.stock,
                })
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en entrada_mercancia_directa (movimiento_inventario_service.py)")
            logger_core.error('Error al registrar entrada de mercancía: %s', str(e), exc_info=True)
            return cls._json_result(500, {
                'status': 'error',
                'mensaje': f'Error al registrar ingreso: {str(e)}',
            })

    @classmethod
    def registrar_compra_a_proveedor(cls, request, empresa, data: dict) -> Dict[str, Any]:
        """Registro de compra multi-ítem con Kardex ENTRADA_COMPRA."""
        proveedor_id = data.get('proveedor_id')
        fecha_compra = data.get('fecha_compra')
        folio_factura = (data.get('folio_factura') or '').strip()
        productos_data = data.get('productos', [])

        if not proveedor_id or not fecha_compra or not productos_data:
            return cls._json_result(400, {
                'status': 'error',
                'mensaje': 'Faltan datos requeridos: proveedor, fecha o productos',
            })

        from farmacia.models import MovimientoInventario, Proveedor as FarmProveedor

        try:
            proveedor = FarmProveedor.objects.get(id=proveedor_id, empresa=empresa)
        except FarmProveedor.DoesNotExist:
            return cls._json_result(404, {'status': 'error', 'mensaje': 'Proveedor no encontrado'})

        try:
            with transaction.atomic():
                total_compra = Decimal('0.00')
                movimientos_creados = 0
                observaciones_compra = (data.get('observaciones') or '').strip()

                for item in productos_data:
                    producto_id = item.get('producto_id')
                    cantidad = int(item.get('cantidad', 0))
                    costo_unitario = Decimal(str(item.get('costo_unitario', 0)))
                    numero_lote = (item.get('numero_lote') or '').strip()
                    fecha_caducidad_str = item.get('fecha_caducidad') or None

                    if not producto_id or cantidad <= 0 or costo_unitario <= 0:
                        continue

                    try:
                        producto = Producto.objects.select_for_update().get(
                            id=producto_id,
                            empresa=empresa,
                        )
                    except Producto.DoesNotExist:
                        return cls._json_result(404, {'status': 'error', 'mensaje': 'Producto no encontrado'})
                    subtotal = Decimal(cantidad) * costo_unitario

                    lote_obj = None
                    if numero_lote:
                        fecha_cad = parse_date(fecha_caducidad_str) if fecha_caducidad_str else None
                        lote_obj, _ = Lote.objects.get_or_create(
                            producto=producto,
                            numero_lote=numero_lote,
                            defaults={
                                'fecha_caducidad': fecha_cad,
                                'cantidad': 0,
                                'costo_adquisicion': costo_unitario,
                            },
                        )

                    obs = f'Compra a {proveedor.razon_social or proveedor.nombre_comercial}'
                    if folio_factura:
                        obs += f' | Factura: {folio_factura}'
                    if observaciones_compra:
                        obs += f' | {observaciones_compra}'

                    MovimientoInventario.objects.create(
                        empresa=empresa,
                        producto=producto,
                        lote=lote_obj,
                        tipo_movimiento='ENTRADA_COMPRA',
                        cantidad=cantidad,
                        costo_unitario=costo_unitario,
                        proveedor=proveedor,
                        documento_referencia=folio_factura or '',
                        observaciones=obs,
                        usuario_responsable=request.user,
                    )

                    total_compra += subtotal
                    movimientos_creados += 1

                logger_core.info(
                    'Compra registrada via Kardex: %s productos, Proveedor=%s, Total=%s',
                    movimientos_creados,
                    proveedor.razon_social,
                    total_compra,
                )
                return cls._json_result(200, {
                    'status': 'success',
                    'mensaje': (
                        f'Compra registrada ({movimientos_creados} productos). '
                        f'Total: ${total_compra:,.2f}'
                    ),
                    'total': str(total_compra),
                })
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en registrar_compra_a_proveedor (movimiento_inventario_service.py)")
            logger_core.error('Error al registrar compra: %s', str(e), exc_info=True)
            return cls._json_result(500, {
                'status': 'error',
                'mensaje': f'Error al registrar compra: {str(e)}',
            })

    @classmethod
    def aplicar_ajuste_por_lote(
        cls,
        request,
        empresa,
        *,
        lote_id: Optional[str],
        cantidad: int,
        tipo: str,
        observacion: str,
    ) -> Dict[str, Any]:
        """Ajuste BAJA/ALTA sobre un lote + Kardex + recalculo stock producto."""
        if not lote_id:
            return cls._json_result(400, {'status': 'error', 'mensaje': 'Lote requerido'})

        try:
            with transaction.atomic():
                try:
                    lote = Lote.objects.select_for_update().get(
                        id=lote_id,
                        producto__empresa=empresa,
                    )
                except Lote.DoesNotExist:
                    return cls._json_result(404, {'status': 'error', 'mensaje': 'Lote no encontrado'})

                if tipo == 'BAJA' and cantidad > lote.cantidad:
                    return cls._json_result(400, {
                        'status': 'error',
                        'mensaje': 'Cantidad mayor al stock del lote',
                    })

                ajuste = AjusteInventario.objects.create(
                    empresa=empresa,
                    producto=lote.producto,
                    lote=lote,
                    tipo_movimiento=tipo,
                    cantidad=cantidad,
                    observacion=observacion,
                    usuario=request.user,
                )

                if tipo == 'BAJA':
                    lote.cantidad -= cantidad
                else:
                    lote.cantidad += cantidad
                lote.save(update_fields=['cantidad'])

                producto = lote.producto
                producto.stock = producto.lotes.aggregate(t=Sum('cantidad'))['t'] or 0
                producto.save(update_fields=['stock'])

                from farmacia.models import MovimientoInventario, MotivoAjuste

                tipo_mov = 'SALIDA_AJUSTE' if tipo == 'BAJA' else 'ENTRADA_AJUSTE'
                motivo_obj = MotivoAjuste.objects.filter(empresa=empresa, activo=True).first()
                if motivo_obj is None:
                    motivo_obj = MotivoAjuste.objects.create(
                        empresa=empresa,
                        codigo='AJUSTE_GENERAL',
                        descripcion='Ajuste general de inventario',
                        es_responsabilidad_empleado=False,
                        requiere_evidencia_fotografica=False,
                        requiere_autorizacion_gerente=False,
                        activo=True,
                    )
                from core.utils.sucursal_helpers import get_user_primary_sucursal
                MovimientoInventario.objects.create(
                    empresa=empresa,
                    sucursal=get_user_primary_sucursal(request.user),
                    producto=producto,
                    lote=lote,
                    tipo_movimiento=tipo_mov,
                    cantidad=cantidad,
                    costo_unitario=producto.precio_compra or 0,
                    ajuste=ajuste,
                    motivo_ajuste=motivo_obj,
                    usuario_responsable=request.user,
                    observaciones=observacion,
                )

            try:
                from core.services.audit_service import registrar_auditoria
                registrar_auditoria(
                    accion='UPDATE',
                    modelo='AjusteInventario',
                    objeto_id=str(ajuste.id),
                    datos_nuevos={'tipo': tipo, 'cantidad': cantidad, 'producto': producto.nombre},
                    request=request,
                )
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en aplicar_ajuste_por_lote (movimiento_inventario_service.py)")
                pass

            return cls._json_result(200, {'status': 'success'})
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en aplicar_ajuste_por_lote (movimiento_inventario_service.py)")
            return cls._json_result(500, {'status': 'error', 'mensaje': str(e)})