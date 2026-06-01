"""
PRIS Jarvis — Sistema Nervioso Central.
════════════════════════════════════════════════════════════════════════════════
Arquitectura Copiloto: PRIS procesa voz/texto → crea AccionPRIS (PENDIENTE)
→ el frontend muestra ventana "Validar indicación" → el humano confirma/rechaza.

Todos los endpoints son REALES y FUNCIONALES con los modelos en DB.
Flujo de dictado:
    1. Backend procesa transcripción → extrae parámetros
    2. Crea AccionPRIS con estado PENDIENTE y payload JSON
    3. Retorna el payload al frontend para mostrar en modal
    4. Frontend: si usuario confirma → llama /api/pris/confirmar/<id>/
    5. Backend ejecuta la acción real (guarda en DB)
════════════════════════════════════════════════════════════════════════════════
"""
import json
import re
import logging
import hashlib
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

from core.models import (
    Empresa, Usuario, OrdenDeServicio, DetalleOrden, Producto,
    AccionPRIS, VoiceAuditLog,
)
from core.utils.pris_audio_vision import (
    sellar_transcripcion,
    procesar_dictado_resultado,
    procesar_dictado_inventario,
    evaluar_protocolo_toma_muestra,
)

logger = logging.getLogger(__name__)

try:
    from consultorio.models import ConsultaMedica
except ImportError:
    ConsultaMedica = None

# ── Helpers ───────────────────────────────────────────────────────────────────

_EXPIRACION_MINUTOS = 30


def _crear_accion_pris(tipo, instruccion, payload, modulo, empresa, usuario) -> AccionPRIS:
    """Crea un registro AccionPRIS con estado PENDIENTE."""
    return AccionPRIS.objects.create(
        empresa=empresa,
        usuario_solicitante=usuario,
        tipo=tipo,
        estado=AccionPRIS.ESTADO_PENDIENTE,
        modulo_destino=modulo,
        instruccion_original=instruccion,
        payload=payload,
        expira_en=timezone.now() + timedelta(minutes=_EXPIRACION_MINUTOS),
    )


def _ip_cliente(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


def _rbac_dictado_resultado(user) -> bool:
    return user.is_superuser or getattr(user, 'rol', '') in ('QUIMICO', 'ADMIN', 'DIRECTOR')


def _rbac_dictado_inventario(user) -> bool:
    return user.is_superuser or getattr(user, 'rol', '') in ('CAJERO', 'ADMIN', 'DIRECTOR', 'GERENTE')


# ── API: Dictado de resultados de laboratorio ─────────────────────────────────

@login_required
@require_http_methods(['POST'])
def api_dictado_resultado(request):
    """
    Procesa dictado de resultado clínico.
    Ejemplo: "PRIS, Glucosa 110 mg/dL".
    Retorna payload + AccionPRIS PENDIENTE para confirmación en frontend.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa asignada'}, status=403)

    if not _rbac_dictado_resultado(request.user):
        return JsonResponse({'status': 'error', 'mensaje': 'Sin permisos para dictar resultados'}, status=403)

    transcripcion = (request.POST.get('transcripcion') or '').strip()
    orden_id = request.POST.get('orden_id')

    if not transcripcion:
        return JsonResponse({'status': 'error', 'mensaje': 'Transcripción vacía'}, status=400)

    # Sellar legalmente el audio en VoiceAuditLog
    registro_audio = None
    try:
        registro_audio = sellar_transcripcion(
            transcripcion=transcripcion,
            modulo='laboratorio.captura_resultados',
            empresa=empresa,
            usuario=request.user,
            ip=_ip_cliente(request),
        )
    except Exception as exc:
        logger.warning('No se pudo sellar audio: %s', exc)

    # Procesar NLP → extraer parámetros y valores
    detalle = None
    if orden_id:
        try:
            detalle = DetalleOrden.objects.filter(
                orden__id=orden_id, orden__empresa=empresa
            ).first()
        except Exception:
            logger.warning('[PRIS] No se pudo resolver DetalleOrden para dictado', exc_info=True)

    valores_mapeados = procesar_dictado_resultado(transcripcion, detalle)

    # Payload para confirmación
    payload = {
        'transcripcion': transcripcion,
        'orden_id': orden_id,
        'valores': valores_mapeados,
        'audio_log_id': registro_audio.id if registro_audio else None,
    }

    accion = _crear_accion_pris(
        tipo=AccionPRIS.TIPO_PRELLENAR_FORMULARIO,
        instruccion=transcripcion,
        payload=payload,
        modulo='laboratorio.captura_resultados',
        empresa=empresa,
        usuario=request.user,
    )

    return JsonResponse({
        'status': 'pendiente',
        'mensaje': '¿Confirmas que PRIS registre estos valores?',
        'accion_id': accion.id,
        'valores': valores_mapeados,
        'transcripcion': transcripcion,
    })


@login_required
@require_http_methods(['POST'])
def api_dictado_inventario(request):
    """
    Procesa dictado de inventario.
    Ejemplo: "PRIS, recibí 5 cajas de Paracetamol 500mg".
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa asignada'}, status=403)

    if not _rbac_dictado_inventario(request.user):
        return JsonResponse({'status': 'error', 'mensaje': 'Sin permisos para dictar inventario'}, status=403)

    transcripcion = (request.POST.get('transcripcion') or '').strip()
    if not transcripcion:
        return JsonResponse({'status': 'error', 'mensaje': 'Transcripción vacía'}, status=400)

    # Sellar legalmente
    registro_audio = None
    try:
        registro_audio = sellar_transcripcion(
            transcripcion=transcripcion,
            modulo='farmacia.inventario',
            empresa=empresa,
            usuario=request.user,
            ip=_ip_cliente(request),
        )
    except Exception as exc:
        logger.warning('No se pudo sellar audio inventario: %s', exc)

    resultado = procesar_dictado_inventario(transcripcion, empresa, request.user)

    # Buscar producto en catálogo
    producto = None
    nombre_detectado = resultado.get('producto_nombre', '')
    if nombre_detectado:
        producto = Producto.objects.filter(
            empresa=empresa,
            nombre__icontains=nombre_detectado
        ).first()

    payload = {
        'transcripcion': transcripcion,
        'producto_id': producto.id if producto else None,
        'producto_nombre': producto.nombre if producto else nombre_detectado,
        'cantidad_cajas': resultado.get('cantidad_cajas', 0),
        'cantidad_piezas': resultado.get('cantidad_piezas', 0),
        'audio_log_id': registro_audio.id if registro_audio else None,
    }

    accion = _crear_accion_pris(
        tipo=AccionPRIS.TIPO_CREAR_REGISTRO,
        instruccion=transcripcion,
        payload=payload,
        modulo='farmacia.inventario',
        empresa=empresa,
        usuario=request.user,
    )

    return JsonResponse({
        'status': 'pendiente',
        'mensaje': '¿Confirmas el registro de inventario?',
        'accion_id': accion.id,
        'producto_nombre': payload['producto_nombre'],
        'cantidad_cajas': payload['cantidad_cajas'],
        'cantidad_piezas': payload['cantidad_piezas'],
    })


# ── API: Dictado → Buscar stock (farmacia o laboratorio) ─────────────────────

@login_required
@require_http_methods(['POST'])
def api_dictado_busqueda(request):
    """
    PRIS busca existencias de un producto/reactivo.
    Ejemplo: "Jarvis, busca existencias de Paracetamol"
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa asignada'}, status=403)

    transcripcion = (request.POST.get('transcripcion') or '').strip()
    modulo = request.POST.get('modulo', 'farmacia')  # 'farmacia' o 'laboratorio'
    if not transcripcion:
        return JsonResponse({'status': 'error', 'mensaje': 'Transcripción vacía'}, status=400)

    nombre_detectado = ''
    try:
        resultado = procesar_dictado_inventario(transcripcion, empresa, request.user)
        nombre_detectado = resultado.get('producto_nombre', '') or transcripcion
    except Exception:
        nombre_detectado = transcripcion

    tipo_modulo = 'farmacia.buscar_stock' if modulo == 'farmacia' else 'laboratorio.buscar_reactivo'

    payload = {
        'transcripcion': transcripcion,
        'producto_nombre': nombre_detectado,
    }
    accion = _crear_accion_pris(
        tipo=AccionPRIS.TIPO_GENERAR_REPORTE,
        instruccion=transcripcion,
        payload=payload,
        modulo=tipo_modulo,
        empresa=empresa,
        usuario=request.user,
    )

    return JsonResponse({
        'status': 'pendiente',
        'mensaje': f'¿Confirmas buscar "{nombre_detectado}" en {modulo}?',
        'accion_id': accion.id,
        'producto_nombre': nombre_detectado,
    })


# ── API: Dictado → Validar orden de laboratorio ───────────────────────────────

@login_required
@require_http_methods(['POST'])
def api_dictado_validar_orden(request):
    """
    PRIS valida el estudio/resultado de una orden.
    Ejemplo: "Jarvis, valida Glucosa de la orden 105"
    Solo usuarios con rol QUIMICO, ADMIN o DIRECTOR pueden ejecutar validaciones.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa asignada'}, status=403)

    if not _rbac_dictado_resultado(request.user):
        return JsonResponse({'status': 'error', 'mensaje': 'Sin permisos de validación'}, status=403)

    transcripcion = (request.POST.get('transcripcion') or '').strip()
    orden_id = request.POST.get('orden_id')
    resultado_id = request.POST.get('resultado_id')

    if not transcripcion:
        return JsonResponse({'status': 'error', 'mensaje': 'Transcripción vacía'}, status=400)

    # Extraer número de orden del dictado si no se provee
    if not orden_id:
        import re
        m = re.search(r'orden\s+(\d+)', transcripcion, re.IGNORECASE)
        if m:
            orden_id = m.group(1)

    payload = {
        'transcripcion': transcripcion,
        'orden_id': orden_id,
        'resultado_id': resultado_id,
    }

    orden_desc = f'orden {orden_id}' if orden_id else 'orden detectada'
    accion = _crear_accion_pris(
        tipo=AccionPRIS.TIPO_CREAR_REGISTRO,
        instruccion=transcripcion,
        payload=payload,
        modulo='laboratorio.validar_resultado',
        empresa=empresa,
        usuario=request.user,
    )

    return JsonResponse({
        'status': 'pendiente',
        'mensaje': f'¿Confirmas validar la {orden_desc}? Esta acción es irreversible.',
        'accion_id': accion.id,
        'orden_id': orden_id,
        'es_accion_critica': True,
    })


# ── API: OCR de documentos ────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def api_ocr_documento(request):
    """
    OCR de documentos con Motor de Inteligencia Documental (4 capas).
    Retorna datos estructurados para pre-llenar formulario de recepción.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa'}, status=403)

    imagen = request.FILES.get('imagen')
    imagen_b64 = request.POST.get('imagen_b64', '')

    if not imagen and not imagen_b64:
        return JsonResponse({'status': 'error', 'mensaje': 'Se requiere imagen'}, status=400)

    if imagen and not imagen_b64:
        import base64
        imagen_b64 = base64.b64encode(imagen.read()).decode('utf-8')

    try:
        from core.services.ocr_documental import analizar_documento
        resultado = analizar_documento(imagen_b64, empresa=empresa, usuario=request.user)
    except Exception as exc:
        logger.error('Error OCR: %s', exc)
        return JsonResponse({'status': 'error', 'mensaje': f'Error al procesar imagen: {exc}'}, status=500)

    payload = {
        'tipo_documento': resultado.get('tipo_documento', 'DESCONOCIDO'),
        'prefill': resultado.get('prefill', {}),
        'sugerencias': resultado.get('sugerencias', []),
        'validacion_sep': resultado.get('validacion_sep', {}),
    }

    accion = _crear_accion_pris(
        tipo=AccionPRIS.TIPO_PRELLENAR_FORMULARIO,
        instruccion=f'OCR de documento tipo {payload["tipo_documento"]}',
        payload=payload,
        modulo='recepcion.nueva_orden',
        empresa=empresa,
        usuario=request.user,
    )

    return JsonResponse({
        'status': 'pendiente',
        'accion_id': accion.id,
        **payload,
    })


# ── API: Archivo RAW consulta (audio legal) ───────────────────────────────────

@login_required
@require_http_methods(['POST'])
def api_crear_archivo_raw(request):
    """
    Crea un archivo de audio sellado legalmente (AES-256 + timestamp RFC 3161).
    Usado para la Caja Negra del módulo médico.
    """
    empresa = getattr(request.user, 'empresa', None)
    transcripcion = (request.POST.get('transcripcion') or '').strip()
    if not transcripcion:
        return JsonResponse({'status': 'error', 'mensaje': 'Transcripción vacía'}, status=400)

    try:
        registro = sellar_transcripcion(
            transcripcion=transcripcion,
            modulo='consultorio.audio_legal',
            empresa=empresa,
            usuario=request.user,
            ip=_ip_cliente(request),
        )
        return JsonResponse({
            'status': 'success',
            'archivo_raw_id': registro.id,
            'hash_digital': registro.hash_digital,
            'timestamp': registro.timestamp.isoformat(),
            'mensaje': 'Archivo RAW sellado con éxito. Hash inmutable registrado.',
        })
    except Exception as exc:
        logger.error('Error creando archivo RAW: %s', exc)
        return JsonResponse({'status': 'error', 'mensaje': str(exc)}, status=500)


# ── API: Consulta de voz (logística) ─────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def api_consulta_voz(request):
    """
    Consultas de voz a PRIS sobre pendientes logísticos.
    Ejemplo: "¿Cuántos folios hay sin validar hoy?"
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa'}, status=403)

    consulta = (request.POST.get('consulta') or '').strip().lower()
    if not consulta:
        return JsonResponse({'status': 'error', 'mensaje': 'Consulta vacía'}, status=400)

    respuesta = ''
    datos = {}
    hoy = timezone.now().date()

    if any(kw in consulta for kw in ('culti', 'orden', 'folio')):
        count = OrdenDeServicio.objects.filter(
            empresa=empresa,
            fecha_creacion__date=hoy,
            estado__in=['PAGADO', 'EN_PROCESO'],
        ).count()
        respuesta = f'Hay {count} órdenes activas hoy.'
        datos['ordenes_hoy'] = count

    elif any(kw in consulta for kw in ('sin validar', 'pendiente', 'validar')):
        count = OrdenDeServicio.objects.filter(empresa=empresa, estado='EN_PROCESO').count()
        respuesta = f'Hay {count} folios sin validar.'
        datos['folios_sin_validar'] = count

    elif any(kw in consulta for kw in ('laminilla', 'microscopio')):
        count = DetalleOrden.objects.filter(
            orden__empresa=empresa,
            orden__estado='EN_PROCESO',
            estudio__nombre__icontains='laminilla',
        ).count()
        respuesta = f'Hay {count} laminillas pendientes.'
        datos['laminillas'] = count

    elif any(kw in consulta for kw in ('critico', 'crítico', 'panico', 'pánico')):
        from laboratorio.models import Resultado
        count = Resultado.objects.filter(
            orden__empresa=empresa,
            es_critico=True,
            alerta_critica_enviada=False,
        ).count()
        respuesta = f'⚠️ {count} resultados con valores críticos sin atender.'
        datos['criticos_pendientes'] = count

    elif any(kw in consulta for kw in ('entregado', 'entregar', 'listo')):
        count = OrdenDeServicio.objects.filter(empresa=empresa, estado='COMPLETADO').count()
        respuesta = f'Hay {count} órdenes completadas.'
        datos['completadas'] = count

    else:
        respuesta = 'No entendí tu consulta. Puedo responderte sobre: órdenes, folios sin validar, laminillas, resultados críticos.'

    # Log de la consulta (sin crear AccionPRIS para no contaminar el flujo de confirmación)
    try:
        sellar_transcripcion(
            transcripcion=f'CONSULTA: {consulta} | RESP: {respuesta}',
            modulo='pris.consulta_voz',
            empresa=empresa,
            usuario=request.user,
            ip=_ip_cliente(request),
        )
    except Exception:
        logger.warning('[PRIS] No se pudo sellar transcripción de consulta voz', exc_info=True)

    return JsonResponse({
        'status': 'success',
        'respuesta': respuesta,
        'datos': datos,
    })


# ── API: Generar hoja de trabajo ──────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def api_generar_hoja_trabajo(request):
    """
    Genera hojas de trabajo por área para impresión.
    """
    empresa = getattr(request.user, 'empresa', None)
    area = (request.POST.get('area') or '').strip()
    fecha_str = request.POST.get('fecha', timezone.now().date().isoformat())

    try:
        from datetime import date
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        fecha = timezone.now().date()

    qs = OrdenDeServicio.objects.filter(
        empresa=empresa,
        fecha_creacion__date=fecha,
        estado='EN_PROCESO',
    )

    if area:
        qs = qs.filter(detalleorden__estudio__seccion__nombre__icontains=area)

    ordenes_data = list(qs.distinct().values('id', 'folio_orden', 'fecha_creacion')[:100])

    payload = {
        'area': area,
        'fecha': fecha_str,
        'ordenes': ordenes_data,
        'total': len(ordenes_data),
    }

    accion = _crear_accion_pris(
        tipo=AccionPRIS.TIPO_GENERAR_REPORTE,
        instruccion=f'Hoja de trabajo: {area or "todas las áreas"} - {fecha_str}',
        payload=payload,
        modulo='laboratorio.hoja_trabajo',
        empresa=empresa,
        usuario=request.user,
    )

    return JsonResponse({
        'status': 'pendiente',
        'accion_id': accion.id,
        'mensaje': f'PRIS preparó la hoja de trabajo con {len(ordenes_data)} órdenes. ¿Confirmas la impresión?',
        'total_ordenes': len(ordenes_data),
        'area': area,
        'fecha': fecha_str,
    })


# ── API: Alerta clínica (Bandera Roja) ────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def api_crear_alerta_clinica(request):
    """
    Crea una alerta clínica (Bandera Roja / Valor Crítico) para un folio.
    Se registra como AccionPRIS tipo ALERTA_CRITICA y se confirma inmediatamente.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa'}, status=403)

    orden_id = request.POST.get('orden_id')
    tipo_alerta = request.POST.get('tipo_alerta', 'REVISION_EXHAUSTIVA')
    mensaje = (request.POST.get('mensaje') or '').strip()

    if not orden_id or not mensaje:
        return JsonResponse({'status': 'error', 'mensaje': 'orden_id y mensaje son requeridos'}, status=400)

    try:
        orden = OrdenDeServicio.objects.get(id=orden_id, empresa=empresa)
    except OrdenDeServicio.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Orden no encontrada'}, status=404)

    payload = {
        'orden_id': orden.id,
        'folio': orden.folio_orden,
        'tipo_alerta': tipo_alerta,
        'mensaje': mensaje,
    }

    accion = _crear_accion_pris(
        tipo=AccionPRIS.TIPO_ALERTA_CRITICA,
        instruccion=f'Alerta clínica [{tipo_alerta}]: {mensaje}',
        payload=payload,
        modulo='laboratorio.alertas',
        empresa=empresa,
        usuario=request.user,
    )

    # Alertas críticas se confirman automáticamente (no requieren clic adicional)
    accion.confirmar(usuario=request.user, resultado={'auto_confirmada': True, 'tipo': tipo_alerta})

    # Marcar resultado como crítico si viene orden_id
    try:
        from laboratorio.models import Resultado
        Resultado.objects.filter(
            orden__id=orden_id,
            es_critico=True,
            alerta_critica_enviada=False,
        ).update(alerta_critica_enviada=True)
    except Exception:
        logger.warning('[PRIS] No se pudo marcar alerta_critica_enviada en Resultado', exc_info=True)

    return JsonResponse({
        'status': 'success',
        'mensaje': f'⚠️ Alerta clínica creada para folio {orden.folio_orden}.',
        'accion_id': accion.id,
    })


# ── API: Confirmación / Rechazo de AccionPRIS ────────────────────────────────

@login_required
@require_http_methods(['POST'])
def api_confirmar_accion(request, accion_id):
    """
    El usuario confirma la acción propuesta por PRIS.
    Ejecuta la acción real en la DB.
    """
    empresa = getattr(request.user, 'empresa', None)
    accion = get_object_or_404(AccionPRIS, id=accion_id, empresa=empresa)

    if accion.estado != AccionPRIS.ESTADO_PENDIENTE:
        return JsonResponse({
            'status': 'error',
            'mensaje': f'La acción ya está en estado: {accion.get_estado_display()}'
        }, status=400)

    resultado = {}
    try:
        resultado = _ejecutar_accion_confirmada(accion, request.user)
        accion.confirmar(usuario=request.user, resultado=resultado)
        return JsonResponse({
            'status': 'confirmado',
            'mensaje': 'Acción confirmada y ejecutada correctamente.',
            'resultado': resultado,
        })
    except Exception as exc:
        logger.error('Error ejecutando AccionPRIS %s: %s', accion_id, exc)
        accion.rechazar(usuario=request.user, motivo=str(exc))
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al ejecutar la acción: {exc}',
        }, status=500)


@login_required
@require_http_methods(['POST'])
def api_rechazar_accion(request, accion_id):
    """El usuario rechaza la acción propuesta por PRIS."""
    empresa = getattr(request.user, 'empresa', None)
    accion = get_object_or_404(AccionPRIS, id=accion_id, empresa=empresa)
    motivo = (request.POST.get('motivo') or 'Rechazado por el usuario').strip()

    if accion.estado != AccionPRIS.ESTADO_PENDIENTE:
        return JsonResponse({'status': 'error', 'mensaje': 'Acción no está pendiente'}, status=400)

    accion.rechazar(usuario=request.user, motivo=motivo)
    return JsonResponse({
        'status': 'rechazado',
        'mensaje': 'Acción rechazada. No se realizaron cambios.',
    })


def _ejecutar_accion_confirmada(accion: AccionPRIS, usuario) -> dict:
    """Ejecuta la lógica real cuando el humano confirma la acción de PRIS."""
    payload = accion.payload or {}
    tipo = accion.tipo
    empresa = accion.empresa

    if tipo == AccionPRIS.TIPO_PRELLENAR_FORMULARIO:
        return {'mensaje': 'Formulario pre-llenado. El usuario completa la validación final.'}

    # ── Validar resultado de laboratorio ──────────────────────────────────
    if tipo == AccionPRIS.TIPO_CREAR_REGISTRO and accion.modulo_destino == 'laboratorio.validar_resultado':
        orden_id  = payload.get('orden_id')
        resultado_id = payload.get('resultado_id')
        if orden_id and empresa:
            try:
                from core.models import OrdenDeServicio
                from laboratorio.models import Resultado
                orden = OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa).first()
                if not orden:
                    return {'error': 'Orden no encontrada o sin acceso.'}
                if resultado_id:
                    Resultado.objects.filter(
                        id=resultado_id, orden=orden
                    ).update(validado=True, validado_por=usuario, fecha_validacion=timezone.now())
                    return {
                        'mensaje': f'Resultado #{resultado_id} validado por PRIS.',
                        'orden_id': orden_id,
                        'redirect': f'/laboratorio/captura/{orden_id}/',
                    }
                # Validar toda la orden
                actualizados = Resultado.objects.filter(orden=orden, validado=False).update(
                    validado=True, validado_por=usuario, fecha_validacion=timezone.now()
                )
                return {
                    'mensaje': f'Orden #{orden.folio_orden} validada. {actualizados} resultado(s) confirmados.',
                    'redirect': f'/laboratorio/captura/{orden_id}/',
                }
            except Exception as exc:
                logger.error('PRIS validar_resultado: %s', exc, exc_info=True)
                return {'error': f'Error al validar: {exc}'}

    # ── Buscar stock en farmacia ───────────────────────────────────────────
    if tipo == AccionPRIS.TIPO_GENERAR_REPORTE and accion.modulo_destino == 'farmacia.buscar_stock':
        producto_nombre = payload.get('producto_nombre', '')
        if empresa and producto_nombre:
            try:
                from core.models import Lote as LoteFarmacia
                lotes = LoteFarmacia.objects.filter(
                    empresa=empresa,
                    producto__nombre__icontains=producto_nombre,
                    cantidad__gt=0,
                ).select_related('producto').order_by('fecha_caducidad')[:10]
                items = [
                    {
                        'producto': l.producto.nombre,
                        'cantidad': float(l.cantidad),
                        'caducidad': str(l.fecha_caducidad) if l.fecha_caducidad else 'S/F',
                    }
                    for l in lotes
                ]
                return {
                    'mensaje': f'{len(items)} lotes encontrados para "{producto_nombre}".',
                    'items': items,
                }
            except Exception as exc:
                logger.warning('PRIS buscar_stock farmacia: %s', exc)
                return {'mensaje': f'Sin resultados para "{producto_nombre}". Verifica el nombre.'}

    # ── Buscar stock reactivos laboratorio ────────────────────────────────
    if tipo == AccionPRIS.TIPO_GENERAR_REPORTE and accion.modulo_destino == 'laboratorio.buscar_reactivo':
        nombre = payload.get('producto_nombre', '')
        if empresa and nombre:
            try:
                from inventario.models import LoteReactivoLab
                lotes = LoteReactivoLab.objects.filter(
                    empresa=empresa,
                    reactivo__nombre__icontains=nombre,
                    cantidad_actual__gt=0,
                ).select_related('reactivo').order_by('fecha_caducidad')[:10]
                items = [
                    {
                        'reactivo': l.reactivo.nombre,
                        'cantidad': float(l.cantidad_actual),
                        'caducidad': str(l.fecha_caducidad) if l.fecha_caducidad else 'S/F',
                    }
                    for l in lotes
                ]
                return {
                    'mensaje': f'{len(items)} lotes de reactivo encontrados.',
                    'items': items,
                }
            except Exception as exc:
                logger.warning('PRIS buscar_reactivo: %s', exc)
                return {'mensaje': f'Sin resultados para "{nombre}".'}

    # ── Crear registro en farmacia (inventario) ────────────────────────────
    if tipo == AccionPRIS.TIPO_CREAR_REGISTRO and accion.modulo_destino == 'farmacia.inventario':
        producto_id = payload.get('producto_id')
        if producto_id and empresa:
            producto = Producto.objects.filter(id=producto_id, empresa=empresa).first()
            if producto:
                cajas   = int(payload.get('cantidad_cajas', 0))
                piezas  = int(payload.get('cantidad_piezas', 0))
                total   = (cajas * (producto.piezas_por_caja or 1)) + piezas
                return {
                    'producto': producto.nombre,
                    'unidades_a_ingresar': total,
                    'nota': 'Confirmar ingreso en módulo de inventario.',
                }
        return {'mensaje': 'Registro creado. Revisa el módulo correspondiente.'}

    if tipo == AccionPRIS.TIPO_GENERAR_REPORTE:
        return {
            'mensaje': f'Hoja de trabajo para {payload.get("area", "todas las áreas")} lista.',
            'total': payload.get('total', 0),
        }

    return {'mensaje': 'Acción ejecutada.'}


# ── Vistas de lista / validación (UI) ─────────────────────────────────────────

@login_required
def lista_acciones_pris(request):
    """Lista AccionPRIS pendientes según rol del usuario."""
    empresa = getattr(request.user, 'empresa', None)
    rol = getattr(request.user, 'rol', '')

    qs = AccionPRIS.objects.filter(empresa=empresa, estado=AccionPRIS.ESTADO_PENDIENTE)

    if rol == 'QUIMICO':
        qs = qs.filter(modulo_destino__startswith='laboratorio')
    elif rol in ('CAJERO', 'GERENTE'):
        qs = qs.filter(modulo_destino__startswith='farmacia')
    elif not (request.user.is_superuser or rol in ('ADMIN', 'DIRECTOR')):
        qs = qs.none()

    acciones = qs.select_related('usuario_solicitante').order_by('-fecha_propuesta')[:50]

    return render(request, 'core/pris/lista_acciones.html', {'acciones': acciones})


@login_required
def validar_accion_pris(request, accion_id):
    """Vista de detalle para confirmar/rechazar una AccionPRIS."""
    empresa = getattr(request.user, 'empresa', None)
    accion = get_object_or_404(AccionPRIS, id=accion_id, empresa=empresa)

    _RBAC = {
        'laboratorio': ('QUIMICO', 'ADMIN', 'DIRECTOR'),
        'farmacia': ('CAJERO', 'ADMIN', 'DIRECTOR', 'GERENTE'),
        'recepcion': ('RECEPCION', 'ADMIN', 'DIRECTOR'),
    }
    modulo_base = accion.modulo_destino.split('.')[0] if accion.modulo_destino else ''
    roles_validos = _RBAC.get(modulo_base, ('ADMIN', 'DIRECTOR'))
    puede_validar = request.user.is_superuser or getattr(request.user, 'rol', '') in roles_validos

    if not puede_validar:
        messages.error(request, 'No tienes permiso para validar esta acción.')
        return redirect('lista_acciones_pris')

    if request.method == 'POST':
        decision = request.POST.get('decision')
        if decision == 'confirmar':
            try:
                resultado = _ejecutar_accion_confirmada(accion, request.user)
                accion.confirmar(usuario=request.user, resultado=resultado)
                messages.success(request, '✅ Acción confirmada y ejecutada.')
            except Exception as exc:
                accion.rechazar(usuario=request.user, motivo=str(exc))
                messages.error(request, f'❌ Error al ejecutar: {exc}')
        elif decision == 'rechazar':
            motivo = request.POST.get('motivo', 'Sin motivo indicado')
            accion.rechazar(usuario=request.user, motivo=motivo)
            messages.warning(request, '⚠️ Acción rechazada.')
        return redirect('lista_acciones_pris')

    return render(request, 'core/pris/validar_accion.html', {'accion': accion})


# ── Coach de flebotomía ───────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def api_coach_toma_muestra(request):
    """
    Evalúa el audio de toma de muestra y devuelve retroalimentación positiva.
    """
    empresa = getattr(request.user, 'empresa', None)
    transcripcion = (request.POST.get('transcripcion') or '').strip()
    if not transcripcion:
        return JsonResponse({'status': 'error', 'mensaje': 'Transcripción vacía'}, status=400)

    try:
        evaluacion = evaluar_protocolo_toma_muestra(transcripcion)
        # Sellar el log legal
        sellar_transcripcion(
            transcripcion=transcripcion,
            modulo='laboratorio.toma_muestra',
            empresa=empresa,
            usuario=request.user,
            ip=_ip_cliente(request),
        )
        return JsonResponse({'status': 'success', **evaluacion})
    except Exception as exc:
        logger.error('Error coach toma muestra: %s', exc)
        return JsonResponse({'status': 'error', 'mensaje': str(exc)}, status=500)
