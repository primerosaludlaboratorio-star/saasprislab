"""
Sistema de Notificaciones — PRISLAB v5
Gestión de NotificacionSistema: listar, leer, marcar como leída, crear desde API.
"""
import json
import logging
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone

from core.models import NotificacionSistema

logger = logging.getLogger('core')


def _json_no_store(payload, status=200):
    response = JsonResponse(payload, status=status)
    response['Cache-Control'] = 'no-store, private, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
def lista_notificaciones(request):
    """Página principal del centro de notificaciones."""
    empresa = getattr(request.user, 'empresa', None)
    qs = NotificacionSistema.objects.filter(
        empresa=empresa
    ).filter(
        Q(destinatario=request.user) | Q(destinatario__isnull=True)
    ).select_related('remitente').order_by('-creada')

    tipo    = request.GET.get('tipo', '')
    modulo  = request.GET.get('modulo', '')
    solo_no_leidas = request.GET.get('no_leidas') == '1'

    if tipo:
        qs = qs.filter(tipo=tipo)
    if modulo:
        qs = qs.filter(modulo=modulo)
    if solo_no_leidas:
        qs = qs.filter(leida=False)

    paginator = Paginator(qs, 25)
    page      = paginator.get_page(request.GET.get('page'))
    total_no_leidas = NotificacionSistema.objects.filter(
        empresa=empresa,
        leida=False
    ).filter(
        Q(destinatario=request.user) | Q(destinatario__isnull=True)
    ).count()

    return render(request, 'core/notificaciones/lista.html', {
        'notificaciones':   page,
        'total_no_leidas':  total_no_leidas,
        'tipos':            NotificacionSistema.TIPO_CHOICES,
        'modulos':          NotificacionSistema.MODULO_CHOICES,
    })


@login_required
def api_notificaciones_badge(request):
    """
    Endpoint JSON para el contador de la campana en el navbar.
    Llamado periódicamente por JS (polling simple).
    """
    empresa = getattr(request.user, 'empresa', None)
    count = NotificacionSistema.objects.filter(
        empresa=empresa,
        leida=False,
    ).filter(
        Q(destinatario=request.user) | Q(destinatario__isnull=True)
    ).count()

    recientes = NotificacionSistema.objects.filter(
        empresa=empresa,
    ).filter(
        Q(destinatario=request.user) | Q(destinatario__isnull=True)
    ).order_by('-creada')[:5].values('id', 'tipo', 'titulo', 'mensaje', 'enlace', 'leida', 'creada')

    return _json_no_store({
        'no_leidas': count,
        'recientes': [
            {
                'id':      n['id'],
                'tipo':    n['tipo'],
                'titulo':  n['titulo'],
                'mensaje': n['mensaje'][:100],
                'enlace':  n['enlace'],
                'leida':   n['leida'],
                'creada':  n['creada'].strftime('%d/%m/%Y %H:%M'),
            }
            for n in recientes
        ],
    })


@login_required
@require_POST
def marcar_leida(request, notificacion_id):
    """Marca una notificación como leída."""
    empresa = getattr(request.user, 'empresa', None)
    notif = get_object_or_404(
        NotificacionSistema,
        pk=notificacion_id,
        empresa=empresa,
    )
    # Solo el destinatario (o si es global) puede marcarla
    if notif.destinatario and notif.destinatario != request.user:
        return _json_no_store({'ok': False, 'error': 'Sin permisos'}, status=403)

    notif.marcar_leida()
    return _json_no_store({'ok': True})


@login_required
@require_POST
def marcar_todas_leidas(request):
    """Marca todas las notificaciones del usuario como leídas."""
    empresa = getattr(request.user, 'empresa', None)
    ahora = timezone.now()
    count = NotificacionSistema.objects.filter(
        empresa=empresa,
        leida=False,
    ).filter(
        Q(destinatario=request.user) | Q(destinatario__isnull=True)
    ).update(leida=True, fecha_lectura=ahora)

    return _json_no_store({'ok': True, 'marcadas': count})


# ── Alias para compatibilidad con rutas legacy ────────────────────────────────
marcar_notificacion_leida = marcar_leida
api_notificaciones_no_leidas = api_notificaciones_badge


@login_required
def configurar_notificaciones(request):
    """Página de preferencias de notificaciones del usuario."""
    empresa = getattr(request.user, 'empresa', None)
    if request.method == 'POST':
        # Por ahora guardamos preferencias simples via sesión
        prefs = {
            'email':   request.POST.get('email_activo') == '1',
            'browser': request.POST.get('browser_activo') == '1',
            'tipos':   request.POST.getlist('tipos'),
        }
        request.session['notif_prefs'] = prefs
        messages.success(request, 'Preferencias de notificaciones guardadas.')
        return redirect('notificaciones_lista')

    prefs = request.session.get('notif_prefs', {'email': True, 'browser': True, 'tipos': []})
    total = NotificacionSistema.objects.filter(empresa=empresa).filter(
        Q(destinatario=request.user) | Q(destinatario__isnull=True)
    ).count()

    return render(request, 'core/notificaciones/configurar.html', {
        'prefs':    prefs,
        'tipos':    NotificacionSistema.TIPO_CHOICES,
        'modulos':  NotificacionSistema.MODULO_CHOICES,
        'total':    total,
    })


@login_required
def ejecutar_verificaciones(request):
    """
    Dispara verificaciones manuales del sistema y genera notificaciones
    para alertas críticas (stocks bajos, resultados pendientes, etc.).
    Solo accesible por staff/directores.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return _json_no_store({'ok': False, 'error': 'Sin permisos'}, status=403)

    empresa = getattr(request.user, 'empresa', None)
    generadas = 0

    try:
        # 2. Verificar órdenes de laboratorio pendientes > 48h
        from core.models import OrdenDeServicio
        from django.utils import timezone
        hace_48h = timezone.now() - timezone.timedelta(hours=48)
        ordenes_tardias = OrdenDeServicio.objects.filter(
            empresa=empresa,
            estado__in=['PAGADA', 'EN_PROCESO'],
            creado__lte=hace_48h,
        ).count()

        if ordenes_tardias > 0:
            NotificacionSistema.crear(
                empresa=empresa,
                titulo=f'{ordenes_tardias} órdenes sin resultado (>48h)',
                mensaje=f'Hay {ordenes_tardias} órdenes de laboratorio con más de 48 horas sin resultado.',
                tipo='ALERTA',
                modulo='LABORATORIO',
                enlace='/laboratorio/lista-trabajo/',
                remitente=request.user,
            )
            generadas += 1

        return _json_no_store({'ok': True, 'generadas': generadas, 'mensaje': f'{generadas} verificaciones ejecutadas'})
    except Exception as exc:
        logger.error("Error en ejecutar_verificaciones: %s", exc)
        return _json_no_store({'ok': False, 'error': str(exc)}, status=500)


@login_required
def api_crear_notificacion(request):
    """
    Crea una notificación vía POST (uso interno / integraciones).
    Solo accesible por staff o directores.
    """
    if not (request.user.is_staff or getattr(request.user, 'rol', '') in ('DIRECTOR', 'ADMIN')):
        return _json_no_store({'ok': False, 'error': 'Sin permisos'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _json_no_store({'ok': False, 'error': 'JSON inválido'}, status=400)

    empresa = getattr(request.user, 'empresa', None)
    notif = NotificacionSistema.crear(
        empresa=empresa,
        titulo=data.get('titulo', 'Sin título')[:200],
        mensaje=data.get('mensaje', ''),
        tipo=data.get('tipo', 'INFO'),
        modulo=data.get('modulo', 'GENERAL'),
        enlace=data.get('enlace', ''),
        remitente=request.user,
        objeto_tipo=data.get('objeto_tipo', ''),
        objeto_id=data.get('objeto_id', ''),
    )
    return _json_no_store({'ok': True, 'id': notif.pk})
