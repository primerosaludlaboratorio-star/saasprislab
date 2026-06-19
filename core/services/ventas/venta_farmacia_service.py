"""
Servicio de dominio PDV Farmacia (v8.5 Fase 2): búsqueda de catálogo y cobro atómico.
transaction.atomic vive en ejecutar_venta_pdv; las vistas solo delegan.
"""
import json
import logging
import time as time_module
import uuid as uuid_module
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.models import (
    AuditLog,
    DetalleVenta,
    DetalleVentaLote,
    Lote,
    Medico,
    MetaVenta,
    Paciente,
    Pago,
    Producto,
    Receta,
    SalesReturn,
    Venta,
)
from core.utils.trazabilidad import registrar_trazabilidad

logger = logging.getLogger("core.farmacia")
logger_core = logging.getLogger("core")


def _int_or_none(value):
    """Convierte un valor a int si es posible; de lo contrario None."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class VentaFarmaciaService:
    """Cobro PDV, Kardex PEPS y búsqueda de catálogo por empresa (sin lógica en la vista)."""

    @staticmethod
    def buscar_productos_pdv(empresa, termino):
        """
        Catálogo ultraligero para tipeo en vivo (<200 ms objetivo sin middleware).
        Sin lotes ni FEFO: el stock mostrado es el campo `Producto.stock`.
        La validación real (lotes, caducidad, PEPS) ocurre en /farmacia/api/lotes-producto/<id>/
        al agregar al carrito (intentarAgregar).
        """
        from django.db.models import Q

        termino = (termino or "").strip()
        if len(termino) < 2:
            return []

        productos = (
            Producto.objects_all.filter(empresa=empresa)
            .filter(
                Q(codigo_barras__icontains=termino)
                | Q(nombre__icontains=termino)
                | Q(sustancia_activa__icontains=termino)
                | Q(marca_laboratorio__icontains=termino)
            )
            .only(
                "id",
                "nombre",
                "sustancia_activa",
                "codigo_barras",
                "precio_publico",
                "precio_compra",
                "stock",
                "iva_porcentaje",
                "es_antibiotico",
                "requiere_receta",
                "categoria",
                "empresa_id",
            )
            .order_by("-id")[:40]
        )

        resultados = []
        for p in productos:
            precio_venta = float(p.precio_publico) if p.precio_publico else 0
            costo = float(p.precio_compra) if p.precio_compra else 0
            stock_total = int(p.stock) if p.stock else 0
            alerta_precio_bajo = precio_venta > 0 and costo > 0 and precio_venta < costo

            resultados.append(
                {
                    "id": p.id,
                    "nombre_comercial": p.nombre,
                    "sustancia_activa": p.sustancia_activa or "",
                    "codigo_barras": p.codigo_barras or "",
                    "precio_base": precio_venta,
                    "precio_venta": precio_venta,
                    "precio_compra": costo,
                    "costo_lote": costo,
                    "stock": stock_total,
                    "stock_total": stock_total,
                    "proxima_caducidad": None,
                    "dias_restantes_fefo": None,
                    "numero_lote_proximo": None,
                    "iva_pct": float(p.iva_porcentaje) if p.iva_porcentaje else 0,
                    "es_controlado": bool(p.es_antibiotico),
                    "es_antibiotico": bool(p.es_antibiotico),
                    "requiere_receta": bool(
                        getattr(p, "requiere_receta", False) or p.es_antibiotico
                    ),
                    "categoria": p.categoria or "",
                    # Fallback si falla api/lotes-producto: no bloquear por caducidad ficticia
                    "dias_restantes": 999,
                    "lote_id": None,
                    "sin_stock_vigente": False,
                    "alerta_precio_bajo": alerta_precio_bajo,
                }
            )
        return resultados

    @staticmethod
    def ejecutar_venta_pdv(request, data, empresa):
        """
        Procesa una venta completa: crea Venta, DetalleVenta, Pago y actualiza stock.
        Maneja folios únicos, lotes PEPS y recetas controladas.
    
        Entrada:
            - request: HttpRequest (con usuario autenticado)
            - data: dict (datos JSON de la venta)
            - empresa: Empresa (empresa del usuario)
    
        Salida:
            - JsonResponse: {
                'status': 'success' | 'error',
                'mensaje': str,
                'folio': str,
                'venta_id': int,
                'sello': str
            }
            - Siempre devuelve JSON, incluso en caso de error
    
        Excepciones:
            - Exception: Cualquier error se captura y devuelve como JSON con logging
    
        Validaciones:
            - Stock disponible antes de vender
            - Receta requerida para antibióticos
            - Cortesía requiere motivo y autorizador
    
        Auditoría:
            - Registra inicio de cobro en log
            - Registra fallos en log con detalles completos
        """
        try:
            with transaction.atomic():
                usuario = request.user
            
                # 1. Obtener paciente si existe
                paciente = None
                paciente_nombre = data.get('cliente', 'PÚBLICO GENERAL')
                if data.get('paciente_id'):
                    try:
                        paciente = Paciente.objects.get(id=data['paciente_id'], empresa=empresa)
                        paciente_nombre = paciente.nombre_completo
                    except Paciente.DoesNotExist:
                        pass
            
                # 2. Calcular totales (CICLO 14: normalizar a 2 decimales y validar rango para evitar crash por overflow)
                from decimal import ROUND_HALF_UP, InvalidOperation
                MAX_MONTO = Decimal('99999999.99')
                def _moneto(s, default=0):
                    try:
                        d = Decimal(str(s))
                    except (InvalidOperation, TypeError):
                        return Decimal(str(default))
                    return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                subtotal = _moneto(data.get('subtotal', 0))
                iva_total = _moneto(data.get('iva_total', 0))
                redondeo = _moneto(data.get('redondeo', 0))
                total_final = _moneto(data.get('total_final', 0))
                descuento_aplicado = _moneto(data.get('descuento_aplicado', 0))
                porcentaje_descuento = _moneto(data.get('descuento_porcentaje', 0))
                total_original = _moneto(data.get('total_original', total_final))  # Valor original para estadísticas
                if any(x > MAX_MONTO or x < -MAX_MONTO for x in (subtotal, iva_total, total_final, descuento_aplicado, porcentaje_descuento, total_original)):
                    return JsonResponse({'status': 'error', 'mensaje': 'Algún importe excede el rango permitido (máx. 99,999,999.99)'}, status=400)
            
                # Campos de Cortesía / Beca (APOYO SOCIAL)
                es_cortesia = data.get('es_cortesia', False)
                motivo_cortesia = data.get('motivo_cortesia', '')
                autorizado_por_cortesia = data.get('autorizado_por_cortesia', '')
            
                # Si es cortesía, forzar total a 0
                if es_cortesia:
                    if not motivo_cortesia or not autorizado_por_cortesia:
                        return JsonResponse({'status': 'error', 'mensaje': 'Cortesía requiere motivo y autorizador'}, status=400)
                    total_final = Decimal('0.00')
                    subtotal = Decimal('0.00')
                    iva_total = Decimal('0.00')
                    redondeo = Decimal('0.00')
            
                # 3. Generar folio único
                max_intentos = 10
                folio_generado = None
                for intento in range(max_intentos):
                    timestamp = time_module.strftime('%Y%m%d%H%M%S')
                    random_suffix = uuid_module.uuid4().hex[:4].upper()
                    folio_candidato = f"VTA-{timestamp}-{random_suffix}"
                
                    if not Venta.objects.filter(folio_operacion=folio_candidato).exists():
                        folio_generado = folio_candidato
                        break
            
                if not folio_generado:
                    # Fallback: usar UUID completo
                    folio_generado = f"VTA-{uuid_module.uuid4().hex[:16].upper()}"
            
                # 4. Receta: vincular existente (receta_id desde consultorio) o crear si es controlado
                receta = None
                receta_id = data.get('receta_id')
                if receta_id:
                    try:
                        receta = Receta.objects.filter(id=receta_id, empresa=empresa).first()
                    except (ValueError, TypeError):
                        receta = None
                if receta is None and data.get('es_controlada'):
                    medico_nombre = data.get('medico_nombre', '')
                    medico_cedula = data.get('medico_cedula', '')
                    receta_fecha = data.get('receta_fecha', '')
                
                    if medico_nombre and medico_cedula:
                        max_dias_receta = int(getattr(empresa, "farmacia_dias_max_antiguedad_receta", 30))
                        # Buscar o crear médico
                        medico, _ = Medico.objects.get_or_create(
                            cedula_profesional=medico_cedula,
                            defaults={'nombre_completo': medico_nombre}
                        )
                    
                        # Crear receta
                        if receta_fecha:
                            try:
                                fecha_receta = datetime.strptime(receta_fecha, '%Y-%m-%d').date()
                                dias_receta = (date.today() - fecha_receta).days
                                if dias_receta > max_dias_receta:
                                    return JsonResponse({
                                        'status': 'error',
                                        'mensaje': (
                                            f'La receta tiene {dias_receta} días de antigüedad '
                                            f'(máximo permitido: {max_dias_receta} días). '
                                            'No puede ser aceptada para dispensación según normativa COFEPRIS.'
                                        )
                                    }, status=400)
                            except (ValueError, TypeError):
                                fecha_receta = timezone.now().date()
                        else:
                            fecha_receta = timezone.now().date()
                    
                        folio_receta = f"REC-{time_module.strftime('%Y%m%d%H%M%S')}-{uuid_module.uuid4().hex[:4].upper()}"
                        receta = Receta.objects.create(
                            medico=medico,
                            empresa=empresa,
                            folio_receta=folio_receta,
                            fecha_emision=fecha_receta,
                            numero_receta_externo=data.get('numero_receta_externo', '') or None,
                            informacion_adicional=data.get('informacion_adicional', '') or None,
                        )
            
                # 4.5. Verificar cupón de marketing (si existe)
                cupon_marketing = None
                campana_marketing = None
                codigo_cupon = (data.get('codigo_cupon') or '').strip()
                cupon_idempotency_key = None

                if codigo_cupon:
                    cupon_idempotency_key = (
                        (request.META.get('HTTP_IDEMPOTENCY_KEY') or data.get('idempotency_key') or '')
                        .strip()
                    )
                    if len(cupon_idempotency_key) < 8:
                        return JsonResponse(
                            {
                                'status': 'error',
                                'mensaje': (
                                    'Idempotency-Key (header HTTP o campo idempotency_key) es obligatorio '
                                    'para ventas con cupón (mínimo 8 caracteres).'
                                ),
                            },
                            status=400,
                        )
                    try:
                        from marketing.models import CuponMarketing, CuponUso

                        prev_uso = (
                            CuponUso.objects.filter(idempotency_key=cupon_idempotency_key[:128])
                            .select_related('venta')
                            .first()
                        )
                        if prev_uso and prev_uso.venta_id:
                            v = prev_uso.venta
                            return JsonResponse(
                                {
                                    'status': 'success',
                                    'reintento': True,
                                    'mensaje': 'Venta idempotente (cupón ya registrado con esta clave).',
                                    'folio': v.folio_operacion,
                                    'venta_id': v.id,
                                    'sello': getattr(v, 'sello_digital', '') or '',
                                }
                            )

                        cupon_marketing = CuponMarketing.objects.filter(
                            codigo=codigo_cupon,
                            empresa=empresa,
                        ).first()

                        if cupon_marketing:
                            if descuento_aplicado == 0 and cupon_marketing.porcentaje_descuento > 0:
                                descuento_cupon = (subtotal * cupon_marketing.porcentaje_descuento) / 100
                                descuento_aplicado = descuento_cupon
                                porcentaje_descuento = cupon_marketing.porcentaje_descuento
                                total_final = subtotal - descuento_aplicado + iva_total + redondeo

                            campana_marketing = (
                                cupon_marketing.campana_marketing
                                if hasattr(cupon_marketing, 'campana_marketing')
                                else None
                            )
                    except ImportError:
                        pass
            
                # 5. Crear Venta (solo campos existentes en core.models.Venta; cupon/campaña si se agregan al modelo)
                venta_kw = dict(
                    empresa=empresa,
                    usuario=usuario,
                    folio_operacion=folio_generado,
                    subtotal=subtotal,
                    impuestos_iva=iva_total,
                    redondeo=redondeo,
                    total=total_final,
                    descuento_aplicado=descuento_aplicado,
                    porcentaje_descuento=porcentaje_descuento,
                    paciente=paciente,
                    paciente_nombre=paciente_nombre,
                    receta=receta,
                    estado='COMPLETADA',
                    efectivo_recibido=_moneto(data.get('efectivo_recibido', 0)),
                    cambio_entregado=_moneto(data.get('cambio_entregado', 0)),
                    es_cortesia=es_cortesia,
                    motivo_cortesia=motivo_cortesia or None,
                    autorizado_por_cortesia=autorizado_por_cortesia or None,
                    total_original=(total_original if es_cortesia else None),
                )
                if hasattr(Venta, 'cupon_marketing') and cupon_marketing is not None:
                    venta_kw['cupon_marketing'] = cupon_marketing
                if hasattr(Venta, 'campana_marketing') and campana_marketing is not None:
                    venta_kw['campana_marketing'] = campana_marketing
                venta = Venta.objects.create(**venta_kw)

                if cupon_marketing and cupon_idempotency_key:
                    try:
                        from marketing.models import CuponUso

                        CuponUso.objects.create(
                            empresa=empresa,
                            cupon=cupon_marketing,
                            paciente=paciente,
                            orden=None,
                            venta=venta,
                            idempotency_key=cupon_idempotency_key[:128],
                        )
                    except IntegrityError:
                        existed = CuponUso.objects.filter(
                            idempotency_key=cupon_idempotency_key[:128]
                        ).first()
                        if existed and existed.venta_id == venta.id:
                            pass
                        else:
                            raise ValueError(
                                'No se pudo registrar el uso del cupón (idempotencia o cupón ya aplicado).'
                            )
            
                # 5b. Auditoría de descuento aplicado (override / autorización)
                if descuento_aplicado and descuento_aplicado > 0:
                    try:
                        from core.services.audit_service import registrar_auditoria
                        registrar_auditoria(
                            accion='CREATE',
                            modelo='Venta',
                            objeto_id=str(venta.id),
                            datos_nuevos={
                                'descuento_aplicado': str(descuento_aplicado),
                                'porcentaje_descuento': str(porcentaje_descuento),
                                'folio': folio_generado,
                                'total': str(total_final),
                                'subtotal': str(subtotal),
                                'autorizado_por': request.user.get_full_name(),
                            },
                            request=request,
                        )
                    except Exception:
                        pass
            
                # 6. ALGORITMO PEPS/FIFO MEJORADO: Crear DetalleVenta y actualizar stock multi-lote
                items = data.get('items', [])
                lotes_afectados = []  # Para auditoría detallada
                _hoy = date.today()  # Fecha de hoy para filtrar lotes caducados

                # ── SPRINT 1.3 / 2.5: Validación pre-loop — bloquear controlados sin receta ──────
                # Fuente autoritativa: requiere_receta (Sprint 2) + es_antibiotico (legacy)
                for _chk in items:
                    _pid = _chk.get('producto_id') or _chk.get('id')
                    _prod_chk = Producto.objects.filter(id=_pid, empresa=empresa).only(
                        'nombre', 'requiere_receta', 'es_antibiotico'
                    ).first()
                    if _prod_chk and _prod_chk.necesita_receta() and not receta:
                        return JsonResponse({
                            'status': 'error',
                            'mensaje': (
                                f'"{_prod_chk.nombre}" requiere receta médica. '
                                'Capture los datos del médico prescritor antes de continuar.'
                            )
                        }, status=400)

                for item_data in items:
                    producto_id = item_data.get('producto_id') or item_data.get('id')
                    get_object_or_404(Producto, id=producto_id, empresa=empresa)
                    # ACAYUCAN v7.5: serializar ventas concurrentes por producto (junto con lotes bloqueados)
                    producto = Producto.objects.select_for_update().get(pk=producto_id, empresa=empresa)
                
                    cantidad = int(item_data.get('cantidad', 1))
                    cantidad_restante = cantidad  # Cantidad que aún falta descontar
                    precio_unitario = _moneto(item_data.get('precio_unitario', 0))
                    subtotal_item = _moneto(item_data.get('subtotal', precio_unitario * cantidad))
                    iva_item = _moneto(item_data.get('iva_item', 0))
                
                    # ALGORITMO PEPS: Obtener lotes ordenados por fecha_caducidad (más antiguo primero)
                    # select_for_update() evita que dos ventas simultáneas desconten el mismo lote y sobredesen stock
                    # SPRINT 1.1: fecha_caducidad__gte=_hoy → bloquear lotes caducados en PEPS
                    lotes_disponibles = producto.lotes.filter(
                        empresa=empresa,
                        cantidad__gt=0,
                        fecha_caducidad__gte=_hoy,  # NO vender lotes caducados (ISO 15189 + COFEPRIS)
                    ).select_for_update().order_by('fecha_caducidad', 'fecha_registro')
                
                    # Si se especificó un lote específico, usarlo primero
                    lote_id = item_data.get('lote_id')
                    if lote_id:
                        try:
                            lote_especifico = Lote.objects.select_for_update().get(
                                id=lote_id, producto=producto, empresa=empresa, cantidad__gt=0
                            )
                            # Reordenar: poner el lote especificado primero
                            lotes_list = list(lotes_disponibles)
                            if lote_especifico in lotes_list:
                                lotes_list.remove(lote_especifico)
                                lotes_list.insert(0, lote_especifico)
                            lotes_disponibles = lotes_list
                        except Lote.DoesNotExist:
                            pass
                
                    # ALGORITMO PEPS MULTI-LOTE: Iterar sobre lotes hasta cubrir la cantidad solicitada
                    lotes_usados_en_item = []
                    lote_principal = None  # Lote que se asignará al DetalleVenta (el primero usado)
                
                    for lote in lotes_disponibles:
                        if cantidad_restante <= 0:
                            break
                    
                        cantidad_a_descontar = min(cantidad_restante, lote.cantidad)
                    
                        # Guardar el primer lote como principal para el DetalleVenta
                        if not lote_principal:
                            lote_principal = lote
                    
                        # ==============================================================================
                        # PILAR FORENSE: CREAR MOVIMIENTO EN KARDEX (NO MODIFICAR STOCK DIRECTAMENTE)
                        # ==============================================================================
                        from farmacia.models import MovimientoInventario
                    
                        # Crear MovimientoInventario en lugar de modificar lote.cantidad directamente
                        # El método save() del MovimientoInventario actualizará automáticamente el stock
                        movimiento = MovimientoInventario(
                            empresa=empresa,
                            sucursal=getattr(request.user, 'sucursal', None),
                            producto=producto,
                            lote=lote,
                            tipo_movimiento='SALIDA_VENTA',
                            cantidad=cantidad_a_descontar,
                            costo_unitario=lote.costo_adquisicion if hasattr(lote, 'costo_adquisicion') else producto.precio_compra or Decimal('0'),
                            usuario_responsable=request.user,
                            venta=venta,
                            observaciones=f"Venta POS - Folio: {folio_generado}",
                            documento_referencia=folio_generado
                        )
                        movimiento.save()  # ← El save() actualiza lote.cantidad automáticamente
                    
                        # NOTA: Ya NO hacemos lote.cantidad -= cantidad_a_descontar
                        # El MovimientoInventario.save() se encarga de eso (Pilar Forense)

                    
                        # Registrar para auditoría detallada
                        # Refrescar el lote para obtener la cantidad actualizada después del movimiento
                        lote.refresh_from_db()
                        lotes_usados_en_item.append({
                            'lote_id': lote.id,
                            'numero_lote': lote.numero_lote,
                            'cantidad_descontada': cantidad_a_descontar,
                            'cantidad_restante_lote': lote.cantidad,  # ← Ya actualizada por el Kardex
                            'fecha_caducidad': lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None
                        })
                    
                        cantidad_restante -= cantidad_a_descontar
                
                    # Si no hay suficiente stock, lanzar error
                    if cantidad_restante > 0:
                        raise ValueError(f'Stock insuficiente para {producto.nombre}. Faltan {cantidad_restante} unidades.')
                
                    # DetalleVenta: lote_vendido = primer lote (compatibilidad); trazabilidad completa en DetalleVentaLote
                    costo_momento = producto.precio_compra if producto.precio_compra is not None else Decimal('0')
                    detalle_row = DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        lote_vendido=lote_principal,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                        iva_aplicado=iva_item,
                        subtotal=subtotal_item,
                        costo_unitario_momento=costo_momento,
                    )
                    for uso in lotes_usados_en_item:
                        DetalleVentaLote.objects.create(
                            detalle_venta=detalle_row,
                            lote_id=uso['lote_id'],
                            cantidad_extraida=int(uso['cantidad_descontada']),
                        )
                
                    # Agregar a lista de lotes afectados para auditoría
                    lotes_afectados.append({
                        'producto_id': producto.id,
                        'producto_nombre': producto.nombre,
                        'cantidad_total': cantidad,
                        'lotes': lotes_usados_en_item  # Detalle completo de todos los lotes usados
                    })
            
                # 7. Crear Pagos (Soporte Cobro Mixto) — compatible con dict y lista
                pagos_data = data.get('pagos', {})
                if isinstance(pagos_data, list):
                    pagos_dict = {'efectivo': Decimal('0'), 'tarjeta': Decimal('0'), 'transferencia': Decimal('0')}
                    for p in pagos_data:
                        met = str(p.get('metodo', '')).upper()
                        mnt = _moneto(p.get('monto', 0))
                        if met in ('EFECTIVO', 'CASH'):
                            pagos_dict['efectivo'] += mnt
                        elif met in ('TARJETA', 'CARD', 'TC'):
                            pagos_dict['tarjeta'] += mnt
                        elif met in ('TRANSFERENCIA', 'SPEI', 'TRANSFER'):
                            pagos_dict['transferencia'] += mnt
                        else:
                            pagos_dict['efectivo'] += mnt
                    pagos_data = pagos_dict
                monto_efectivo = _moneto(pagos_data.get('efectivo', 0))
                monto_tarjeta = _moneto(pagos_data.get('tarjeta', 0))
                monto_transferencia = _moneto(pagos_data.get('transferencia', 0))
                if monto_efectivo > MAX_MONTO or monto_tarjeta > MAX_MONTO or monto_transferencia > MAX_MONTO:
                    return JsonResponse({'status': 'error', 'mensaje': 'Algún monto de pago excede el rango permitido.'}, status=400)
                # Validación servidor: montos de pago no pueden ser negativos
                if monto_efectivo < 0 or monto_tarjeta < 0 or monto_transferencia < 0:
                    return JsonResponse({
                        'status': 'error',
                        'mensaje': 'Los montos de pago no pueden ser negativos.'
                    }, status=400)
            
                # Determinar metodo principal para el registro
                metodos_usados = []
                if monto_efectivo > 0:
                    metodos_usados.append('EFECTIVO')
                if monto_tarjeta > 0:
                    metodos_usados.append('TARJETA')
                if monto_transferencia > 0:
                    metodos_usados.append('SPEI')
            
                # Crear un registro de Pago unificado con desglose multimodal
                # Esto facilita la auditoria y el corte de caja
                monto_total_pagos = monto_efectivo + monto_tarjeta + monto_transferencia
                # Validar que la suma de medios de pago coincida con el total (tolerancia 0.01 por redondeo)
                if not es_cortesia and abs(monto_total_pagos - total_final) > Decimal('0.01'):
                    return JsonResponse({
                        'status': 'error',
                        'mensaje': f'La suma de pagos (${monto_total_pagos}) no coincide con el total (${total_final}). Ajuste los montos.'
                    }, status=400)
                if monto_total_pagos > 0 or es_cortesia:
                    metodo_principal = metodos_usados[0] if len(metodos_usados) == 1 else 'EFECTIVO'
                    Pago.objects.create(
                        venta=venta,
                        metodo=metodo_principal,
                        monto=monto_total_pagos if not es_cortesia else Decimal('0.00'),
                        monto_efectivo=monto_efectivo,
                        monto_tarjeta=monto_tarjeta,
                        monto_transferencia=monto_transferencia,
                        referencia_pago=data.get('referencia_pago', '') or ''
                    )
            
                # 8. Generar sello digital (simplificado)
                sello_digital = f"{folio_generado}|{venta.id}|{timezone.now().isoformat()}"
                venta.sello_digital = sello_digital
                venta.save()

                # Hito 16 Fase 2: borrador CFDI (misma transacción que la venta)
                if not es_cortesia and total_final > 0:
                    from contabilidad.services.cfdi_borrador_auto import (
                        crear_borrador_cfdi_desde_venta_farmacia,
                    )

                    crear_borrador_cfdi_desde_venta_farmacia(venta, usuario)
            
                # 9. ACTUALIZAR META DE VENTA (Impacto en Metas)
                sucursal_venta = getattr(request.user, 'sucursal', None)
                fecha_actual = timezone.now().date()
            
                if sucursal_venta:
                    # Obtener o crear MetaVenta para la sucursal y fecha actual
                    nombre_sucursal = sucursal_venta.nombre if hasattr(sucursal_venta, 'nombre') else str(sucursal_venta)
                    meta_venta, creada = MetaVenta.objects.get_or_create(
                        empresa=empresa,
                        fecha=fecha_actual,
                        sucursal=nombre_sucursal,
                        defaults={
                            'monto_objetivo': Decimal('50000.00'),  # Valor por defecto, puede configurarse después
                            'creado_por': request.user
                        }
                    )
                    # Nota: El acumulado de ventas se calcula dinámicamente en el dashboard
                    # comparando MetaVenta.monto_objetivo con Venta.objects.filter(...).aggregate(Sum('total'))
            
                # 10. REGISTRAR EN AUDITLOG CON DETALLE DE LOTES AFECTADOS
                from core.models import AuditLog
                AuditLog.objects.create(
                    empresa=empresa,
                    usuario=request.user,
                    accion=AuditLog.ACCION_CREATE,
                    modelo_afectado='Venta',
                    objeto_id=str(venta.id),
                    datos_anteriores=None,
                    datos_nuevos={
                        'folio': folio_generado,
                        'total': str(total_final),
                        'paciente': paciente_nombre,
                        'items_count': len(items),
                        'lotes_afectados': lotes_afectados,  # Detalle completo de lotes
                        'sucursal': sucursal_venta.nombre if sucursal_venta and hasattr(sucursal_venta, 'nombre') else str(sucursal_venta) if sucursal_venta else None
                    },
                    sucursal=sucursal_venta,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
            
                # Registrar trazabilidad
                registrar_trazabilidad(
                    tipo_operacion='VENTA',
                    modulo='FARMACIA',
                    referencia_id=venta.id,
                    referencia_tipo='Venta',
                    accion='CREAR',
                    descripcion=f'Venta procesada con algoritmo PEPS. Lotes afectados: {len(lotes_afectados)}',
                    usuario=request.user,
                    empresa=empresa,
                    sucursal=sucursal_venta,
                    datos_nuevos={
                        'folio': folio_generado,
                        'total': str(total_final),
                        'lotes_detalle': lotes_afectados
                    },
                    request=request
                )
            
                # 11. REGISTRAR ANTIBIÓTICOS EN LIBRO COFEPRIS (auto-trazabilidad)
                try:
                    from farmacia.models import RegistroAntibiotico
                    paciente_obj = None
                    paciente_id = data.get('paciente_id')
                    if paciente_id:
                        paciente_obj = Paciente.objects.filter(pk=paciente_id, empresa=empresa).first()

                    for detalle in DetalleVenta.objects.filter(venta=venta).select_related('producto').prefetch_related(
                        'lotes_extraidos__lote'
                    ):
                        prod = detalle.producto
                        if not (getattr(prod, 'es_antibiotico', False) or getattr(prod, 'es_controlado', False)):
                            continue
                        sucursal_actual = getattr(request.user, 'sucursal', None)
                        if not sucursal_actual:
                            logger.warning(
                                '[Farmacia-COFEPRIS] Usuario %s sin sucursal — registro omitido para %s',
                                request.user,
                                prod,
                            )
                            continue
                        pares_lote_cant = [
                            (x.lote, x.cantidad_extraida) for x in detalle.lotes_extraidos.all()
                        ]
                        if not pares_lote_cant and detalle.lote_vendido_id:
                            pares_lote_cant = [(detalle.lote_vendido, detalle.cantidad)]
                        for lt, qty in pares_lote_cant:
                            if lt is None:
                                continue
                            RegistroAntibiotico.objects.get_or_create(
                                venta=venta,
                                producto=prod,
                                lote_vendido=lt,
                                defaults={
                                    'empresa': empresa,
                                    'sucursal': sucursal_actual,
                                    'paciente': paciente_obj,
                                    'paciente_nombre': paciente_nombre or '',
                                    'medico_nombre': data.get('nombre_medico', '') or '',
                                    'medico_cedula': data.get('cedula_medico', '') or '',
                                    'cantidad_vendida': qty,
                                    'fecha_venta': timezone.now(),
                                    'usuario_vendedor': request.user,
                                },
                            )
                except Exception as _abx_exc:
                    logger.error(f'[Farmacia-COFEPRIS] Error auto-registro antibiótico: {_abx_exc}', exc_info=True)

                return JsonResponse({
                    'status': 'success',
                    'mensaje': 'Venta procesada exitosamente',
                    'folio': folio_generado,
                    'venta_id': venta.id,
                    'sello': sello_digital
                })
            
        except ValueError as e:
            # CICLO 14: Stock insuficiente u otra validación — devolver 400 en lugar de 500
            msg = str(e)
            if 'Stock insuficiente' in msg or 'insuficiente' in msg.lower():
                return JsonResponse({'status': 'error', 'mensaje': msg}, status=400)
            import traceback
            error_detail = traceback.format_exc()
            return JsonResponse({'status': 'error', 'mensaje': msg, 'detalle': error_detail[:500]}, status=400)
        except Exception as e:
            from django.core.exceptions import ValidationError
            if isinstance(e, ValidationError):
                return JsonResponse({'status': 'error', 'mensaje': str(e.messages[0]) if e.messages else str(e)}, status=400)
            import traceback
            error_detail = traceback.format_exc()
            try:
                monto_intentado = float(data.get('total_final', 0)) if isinstance(data, dict) else 0.0
            except (TypeError, ValueError):
                monto_intentado = 0.0
            usuario_log = getattr(request, 'user', None)
            empresa_nombre = getattr(empresa, 'nombre', 'N/A') if empresa else 'N/A'

            # BITÁCORA DE TRANSACCIÓN CRÍTICA: Fallo en cobro
            try:
                logger_core.error(
                    f"FALLO EN COBRO (FARMACIA) - "
                    f"Usuario: {getattr(usuario_log, 'username', '?')} (ID: {getattr(usuario_log, 'id', '?')}) - "
                    f"Monto intentado: ${monto_intentado:.2f} - "
                    f"Error: {str(e)} - "
                    f"Tipo: {type(e).__name__} - "
                    f"Traceback: {error_detail[:500]} - "
                    f"Empresa: {empresa_nombre}"
                )
            except Exception as log_error:
                # Silencioso: Si el logging falla, no debe detener la operación
                pass
        
            return JsonResponse({
                'status': 'error',
                'mensaje': f'Error al procesar la venta: {str(e)}',
                'detalle': error_detail
            }, status=500)

    @staticmethod
    def registrar_devolucion_resultado(request, empresa, data: dict):
        """POST devolución: SalesReturn + auditoría. Retorna {http_status, body}."""
        if not empresa:
            return {'http_status': 403, 'body': {'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}}
        venta_id = data.get('venta_id')
        if not venta_id:
            return {'http_status': 400, 'body': {'status': 'error', 'mensaje': 'venta_id requerido'}}
        try:
            monto = Decimal(str(data.get('monto_reembolsado') or data.get('monto', 0)))
        except (InvalidOperation, TypeError, ValueError):
            monto = Decimal('0')
        tipo = data.get('tipo_devolucion') or data.get('tipo', 'TOTAL')
        motivo = data.get('motivo_error') or data.get('motivo', '')
        accion_stock = data.get('accion_stock') or 'RETORNO_ALMACEN'
        try:
            venta = Venta.objects.get(id=venta_id, empresa=empresa)
        except Venta.DoesNotExist:
            return {'http_status': 404, 'body': {'status': 'error', 'mensaje': 'Venta no encontrada'}}
        if monto <= 0:
            return {'http_status': 400, 'body': {'status': 'error', 'mensaje': 'El monto debe ser mayor a cero'}}
        if monto > venta.total:
            return {
                'http_status': 400,
                'body': {
                    'status': 'error',
                    'mensaje': f'Monto excede el total de la venta (${venta.total})',
                },
            }
        productos = data.get('productos') or []
        if isinstance(productos, str):
            try:
                productos = json.loads(productos)
            except (json.JSONDecodeError, TypeError):
                productos = []
        detalle_ids_venta = set(venta.detalles.values_list('id', flat=True))
        productos_validados = []
        for p in productos:
            detalle_id = _int_or_none(p.get('detalle_id')) or _int_or_none(p.get('id'))
            if detalle_id and detalle_id in detalle_ids_venta:
                productos_validados.append({
                    'detalle_id': detalle_id,
                    'cantidad': p.get('cantidad', 1),
                    'motivo': p.get('motivo', '') or motivo,
                })
        observaciones = data.get('observaciones', '')
        if productos_validados:
            observaciones_json = json.dumps({'productos_devueltos': productos_validados}, ensure_ascii=False)
            observaciones = f"{observaciones}\n\nDetalle de productos:\n{observaciones_json}".strip()
        try:
            from core.services.audit_service import registrar_auditoria
            with transaction.atomic():
                devolucion = SalesReturn.objects.create(
                    empresa=empresa,
                    venta_original=venta,
                    tipo_devolucion=tipo,
                    monto_reembolsado=monto,
                    motivo_error=motivo,
                    usuario_error_origen=request.user,
                    usuario_autorizo=request.user,
                    accion_stock=accion_stock,
                    observaciones=observaciones or None,
                )
                registrar_auditoria(
                    accion='CREATE',
                    modelo='SalesReturn',
                    objeto_id=str(devolucion.id),
                    datos_nuevos={
                        'venta_id': venta.id,
                        'folio_venta': getattr(venta, 'folio', None) or str(venta.id),
                        'tipo_devolucion': tipo,
                        'monto_reembolsado': str(monto),
                        'motivo': motivo,
                        'autorizado_por': request.user.get_full_name(),
                    },
                    request=request,
                )
        except Exception as e:
            return {'http_status': 400, 'body': {'status': 'error', 'mensaje': str(e)}}
        return {'http_status': 200, 'body': {'status': 'success'}}

    @staticmethod
    def cancelar_venta_resultado(request, empresa, venta_id: int):
        """Cancelación + reversión Kardex. Retorna {http_status, body}."""
        if not empresa:
            return {'http_status': 403, 'body': {'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}}
        try:
            venta = Venta.objects.select_related('empresa').prefetch_related(
                'detalles__lote_vendido', 'detalles__producto'
            ).get(id=venta_id, empresa=empresa)
        except Venta.DoesNotExist:
            return {'http_status': 404, 'body': {'status': 'error', 'mensaje': 'Venta no encontrada'}}
        if venta.estado == 'CANCELADA':
            return {'http_status': 400, 'body': {'status': 'error', 'mensaje': 'La venta ya está cancelada'}}
        estado_anterior = venta.estado

        try:
            from farmacia.models import MovimientoInventario
            from core.services.audit_service import registrar_auditoria

            with transaction.atomic():
                venta_bloqueada = Venta.objects.select_for_update().get(pk=venta.pk)
                if venta_bloqueada.estado == 'CANCELADA':
                    return {'http_status': 400, 'body': {'status': 'error', 'mensaje': 'La venta ya está cancelada'}}

                venta_bloqueada.estado = 'CANCELADA'
                venta_bloqueada.save(update_fields=['estado'])

                movimientos_originales = MovimientoInventario.objects.select_for_update().filter(
                    venta=venta_bloqueada,
                    tipo_movimiento='SALIDA_VENTA',
                ).select_related('producto', 'lote')
                for mov in movimientos_originales:
                    if not mov.lote or not mov.producto or not mov.cantidad:
                        continue
                    MovimientoInventario.objects.create(
                        empresa=empresa,
                        sucursal=getattr(request.user, 'sucursal', None),
                        producto=mov.producto,
                        lote=mov.lote,
                        tipo_movimiento='ENTRADA_DEVOLUCION',
                        cantidad=mov.cantidad,
                        costo_unitario=mov.costo_unitario or 0,
                        venta=venta,
                        usuario_responsable=request.user,
                        observaciones=f'Reversión automática por cancelación de venta #{venta_id}',
                    )

            try:
                registrar_auditoria(
                    accion='UPDATE',
                    modelo='Venta',
                    objeto_id=str(venta.id),
                    datos_anteriores={'estado': estado_anterior},
                    datos_nuevos={'estado': 'CANCELADA', 'cancelado_por': request.user.get_full_name()},
                    request=request,
                )
            except Exception:
                pass

            return {
                'http_status': 200,
                'body': {
                    'status': 'success',
                    'mensaje': f'Venta #{venta_id} cancelada y stock revertido correctamente',
                    'folio': getattr(venta, 'folio_operacion', str(venta_id)),
                },
            }
        except Exception as e:
            return {'http_status': 400, 'body': {'status': 'error', 'mensaje': str(e)}}


def ejecutar_venta_pdv(request, data, empresa):
    """Compatibilidad con imports existentes (management commands, tests)."""
    return VentaFarmaciaService.ejecutar_venta_pdv(request, data, empresa)
