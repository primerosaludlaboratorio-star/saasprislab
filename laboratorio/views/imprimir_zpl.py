"""
laboratorio/views/imprimir_zpl.py
════════════════════════════════════════════════════════════════════════════════
FASE 7 — Vistas de impresión ZPL y auto-check-in QR

Endpoints:
  POST /api/lab/imprimir-zpl/<orden_id>/     → Imprimir etiqueta tubo
  POST /api/lab/imprimir-zpl/lote/           → Imprimir lote de etiquetas
  GET  /kiosko/check-in/<qr_token>/          → Auto-check-in por QR
  GET  /kiosko/                              → Vista kiosco pública
════════════════════════════════════════════════════════════════════════════════
"""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from laboratorio.services.etiquetas_zpl import (
    zpl_desde_orden_legacy,
    generar_zpl_lote,
    enviar_zpl_tcp,
)

logger = logging.getLogger('laboratorio.zpl.views')

# Host de la impresora Zebra (configurable por env var o ajuste por empresa)
_ZEBRA_HOST_DEFAULT = getattr(settings, 'ZEBRA_PRINTER_HOST', '')
_ZEBRA_PORT_DEFAULT = int(getattr(settings, 'ZEBRA_PRINTER_PORT', 9100))


@login_required
@require_http_methods(['POST'])
def imprimir_etiqueta_zpl(request, orden_id):
    """
    Genera ZPL para una orden y lo envía a la impresora Zebra por TCP.
    Acepta ?preview=1 para retornar el ZPL como texto sin enviar.
    """
    empresa = getattr(request.user, 'empresa', None)
    from core.models import OrdenDeServicio
    try:
        orden = OrdenDeServicio.objects.select_related('paciente', 'empresa').get(
            pk=orden_id, empresa=empresa
        )
    except OrdenDeServicio.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Orden no encontrada'}, status=404)

    zpl = zpl_desde_orden_legacy(orden)

    # Modo preview: retornar ZPL como texto plano
    if request.GET.get('preview'):
        return HttpResponse(zpl, content_type='text/plain')

    # Obtener host de impresora: params del request > empresa > default
    body = {}
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        pass

    zebra_host = (
        body.get('zebra_host') or
        getattr(empresa, 'zebra_printer_host', '') or
        _ZEBRA_HOST_DEFAULT
    )
    zebra_port = int(body.get('zebra_port', _ZEBRA_PORT_DEFAULT))

    if not zebra_host:
        return JsonResponse({
            'ok': False,
            'error': 'IP de impresora Zebra no configurada. '
                     'Configure ZEBRA_PRINTER_HOST en el sistema o pase zebra_host en el body.',
            'zpl_preview': zpl,  # Retornar ZPL para diagnóstico
        }, status=400)

    resultado = enviar_zpl_tcp(zpl, host=zebra_host, port=zebra_port)
    return JsonResponse(resultado, status=200 if resultado['ok'] else 503)


@login_required
@require_http_methods(['POST'])
def imprimir_etiquetas_lote_zpl(request):
    """Imprime múltiples etiquetas ZPL en una sola operación."""
    try:
        body = json.loads(request.body)
        ordenes_ids = body.get('ordenes_ids', [])
        zebra_host = body.get('zebra_host', _ZEBRA_HOST_DEFAULT)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    if not ordenes_ids:
        return JsonResponse({'ok': False, 'error': 'Sin ordenes_ids'}, status=400)

    empresa = getattr(request.user, 'empresa', None)
    from core.models import OrdenDeServicio as _ODS

    ordenes_data = []
    for oid in ordenes_ids[:50]:
        try:
            _o = _ODS.objects.select_related('paciente', 'empresa').get(pk=oid, empresa=empresa)
            ordenes_data.append(_orden_to_dict(_o))
        except Exception:
            pass

    if not ordenes_data:
        return JsonResponse({'ok': False, 'error': 'Ninguna orden válida'}, status=404)

    from laboratorio.services.etiquetas_zpl import generar_zpl_lote
    zpl_lote = generar_zpl_lote(ordenes_data)

    if not zebra_host:
        return JsonResponse({
            'ok': False, 'error': 'Zebra host requerido',
            'zpl_preview': zpl_lote[:500],
        }, status=400)

    resultado = enviar_zpl_tcp(zpl_lote, host=zebra_host)
    resultado['etiquetas'] = len(ordenes_data)
    return JsonResponse(resultado)


def kiosko_check_in_qr(request, qr_token: str):
    """
    Auto-check-in de paciente escaneando QR en kiosco de recepción.
    Vista pública: el QR lleva el folio o UUID de la orden.
    No requiere sesión — el kiosco es de acceso libre.

    Flujo:
    1. Busca OrdenDeServicio por folio_orden (fuente principal)
    2. Marca paciente como LLEGÓ (estado: ESPERANDO_TOMA) con timestamp
    4. Muestra pantalla de bienvenida con instrucciones
    """
    import logging
    from django.utils import timezone
    logger = logging.getLogger('laboratorio.kiosko')

    token_clean = qr_token.strip().upper() if qr_token else ''
    orden_ods = None
    paciente = None
    folio_display = token_clean

    # ── 1. Buscar en OrdenDeServicio ──────────────────────────────────────────
    try:
        from core.models import OrdenDeServicio
        orden_ods = OrdenDeServicio.objects.select_related('paciente', 'empresa').filter(
            folio_orden=token_clean
        ).first()
        if not orden_ods and len(token_clean) > 6:
            # Intentar con la versión en minúsculas
            orden_ods = OrdenDeServicio.objects.select_related('paciente', 'empresa').filter(
                folio_orden__iexact=token_clean
            ).first()
    except Exception as e:
        logger.warning('kiosko_check_in_qr: error buscando OrdenDeServicio: %s', e)

    if orden_ods:
        paciente = orden_ods.paciente
        folio_display = orden_ods.folio_orden or token_clean

        # Marcar check-in: actualizar estado a ESPERANDO_TOMA si está en estado inicial
        try:
            estados_previos_ok = {'PENDIENTE_PAGO', 'PAGADO', 'EN_ESPERA', 'PENDIENTE'}
            if orden_ods.estado in estados_previos_ok or not orden_ods.estado:
                orden_ods.estado = 'EN_PROCESO'
                orden_ods.save(update_fields=['estado'])
                logger.info('kiosko check-in: orden %s marcada EN_PROCESO', folio_display)
        except Exception as e:
            logger.warning('kiosko_check_in_qr: no se pudo actualizar estado: %s', e)

        # Registrar timestamp de llegada en sesión (para notificación a recepción)
        request.session[f'kiosko_checkin_{folio_display}'] = timezone.now().isoformat()

        nombre_paciente = ''
        if paciente:
            nombre_paciente = getattr(paciente, 'nombre_completo', '') or ''

        return render(request, 'laboratorio/kiosko/bienvenida.html', {
            'orden': orden_ods,
            'paciente': paciente,
            'nombre_paciente': nombre_paciente,
            'folio': folio_display,
            'empresa': getattr(orden_ods, 'empresa', None),
            'check_in_time': timezone.now().strftime('%H:%M'),
        })

    # ── 2. No encontrado ──────────────────────────────────────────────────────
    logger.warning('kiosko_check_in_qr: folio no encontrado: %s', token_clean)
    return render(request, 'laboratorio/kiosko/no_encontrado.html', {
        'token': token_clean,
    })


def kiosko_index(request):
    """Vista pública del kiosco de recepción."""
    return render(request, 'laboratorio/kiosko/index.html')


# ─── Helper ───────────────────────────────────────────────────────────────────

def _orden_to_dict(orden) -> dict:
    """Convierte una Orden a dict para generar_zpl_lote."""
    paciente = getattr(orden, 'paciente', None)
    nombre = ''
    nacimiento = ''
    if paciente:
        nombre = (
            getattr(paciente, 'nombre_completo', '') or
            f"{getattr(paciente, 'apellidos', '')} {getattr(paciente, 'nombres', '')}".strip()
        )
        nac = getattr(paciente, 'fecha_nacimiento', None)
        if nac:
            try:
                nacimiento = nac.strftime('%d/%m/%Y')
            except AttributeError:
                nacimiento = str(nac)
    estudios = []
    detalles = getattr(orden, 'detalles', None)
    if detalles is not None:
        for d in detalles.all():
            label = (getattr(d, 'descripcion_linea', '') or '').strip()
            if not label and getattr(d, 'analito', None):
                label = getattr(d.analito, 'nombre', '') or ''
            if not label and getattr(d, 'perfil_lims', None):
                label = getattr(d.perfil_lims, 'nombre', '') or ''
            if not label and getattr(d, 'paquete_lims', None):
                label = getattr(d.paquete_lims, 'nombre', '') or ''
            if label:
                estudios.append(label)
    return {
        'folio': getattr(orden, 'folio_orden', None) or getattr(orden, 'folio', str(orden.pk)),
        'paciente_nombre': nombre,
        'fecha_nacimiento': nacimiento,
        'estudios': estudios,
        'urgente': getattr(orden, 'urgente', False),
        'empresa_nombre': getattr(getattr(orden, 'empresa', None), 'nombre', 'PRISLAB'),
    }
