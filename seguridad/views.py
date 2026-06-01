"""
Vistas del módulo de Seguridad
Incluye: 2FA, Gestión de Sesiones, Auditoría
"""

import csv
import json
import logging
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import logout
from django.db.models import Q, Count
from user_agents import parse

from core.decorators import role_required
from core.models import ForenseAcceso, Usuario

from .models import (
    DispositivoTOTP, DispositivoSMS, CodigoBackup2FA,
    SesionActiva, LogAccionSensible, AlertaPanico
)


# ============================================================================
# AUTENTICACIÓN DE DOS FACTORES (2FA)
# ============================================================================

@login_required
def configuracion_2fa(request):
    """
    Vista principal de configuración de 2FA.
    Muestra los dispositivos activos y permite activar/desactivar 2FA.
    """
    dispositivos_totp = DispositivoTOTP.objects.filter(usuario=request.user)
    dispositivos_sms = DispositivoSMS.objects.filter(usuario=request.user)
    codigos_backup = CodigoBackup2FA.objects.filter(usuario=request.user, usado=False)
    
    # Verificar si el usuario tiene 2FA activo
    tiene_2fa_activo = dispositivos_totp.filter(activo=True).exists() or \
                       dispositivos_sms.filter(activo=True).exists()
    
    context = {
        'dispositivos_totp': dispositivos_totp,
        'dispositivos_sms': dispositivos_sms,
        'codigos_backup': codigos_backup,
        'tiene_2fa_activo': tiene_2fa_activo,
        'total_codigos_backup': codigos_backup.count(),
    }
    
    # Registrar acceso a configuración de seguridad
    LogAccionSensible.registrar(
        usuario=request.user,
        accion=LogAccionSensible.ACCION_ACCESO_ADMINISTRACION,
        descripcion="Accedió a configuración de 2FA",
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
        ruta_url=request.path,
        metodo_http=request.method
    )
    
    return render(request, 'seguridad/2fa/configuracion.html', context)


@login_required
def activar_totp(request):
    """
    Inicia el proceso de activación de TOTP (Google Authenticator).
    Genera la llave secreta y muestra el código QR.
    """
    # Verificar si ya tiene un dispositivo TOTP activo
    if DispositivoTOTP.objects.filter(usuario=request.user, activo=True).exists():
        messages.warning(request, "Ya tienes un dispositivo TOTP activo. Desactívalo primero.")
        return redirect('seguridad:configuracion_2fa')
    
    # Crear nuevo dispositivo TOTP
    dispositivo = DispositivoTOTP.objects.create(
        usuario=request.user,
        nombre="Google Authenticator"
    )
    dispositivo.generar_llave_secreta()
    
    # Generar código QR
    qr_code = dispositivo.generar_qr_code()
    
    context = {
        'dispositivo': dispositivo,
        'qr_code': qr_code,
        'llave_secreta': dispositivo.llave_secreta,
    }
    
    return render(request, 'seguridad/2fa/activar_totp.html', context)


@login_required
@require_POST
def confirmar_totp(request, dispositivo_id):
    """
    Confirma la activación de TOTP verificando un código ingresado.
    """
    dispositivo = get_object_or_404(DispositivoTOTP, id=dispositivo_id, usuario=request.user)
    
    codigo = request.POST.get('codigo', '').strip()
    
    if not codigo:
        messages.error(request, "Debes ingresar un código de verificación.")
        return redirect('seguridad:activar_totp')
    
    if dispositivo.confirmar_dispositivo(codigo):
        # Generar códigos de respaldo automáticamente
        generar_codigos_backup(request.user)
        
        messages.success(request, "✓ Autenticación de dos factores activada exitosamente!")
        
        # Registrar activación
        LogAccionSensible.registrar(
            usuario=request.user,
            accion=LogAccionSensible.ACCION_2FA_ACTIVADO,
            descripcion="Activó autenticación de dos factores (TOTP)",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            severidad=LogAccionSensible.SEVERIDAD_WARNING
        )
        
        return redirect('seguridad:mostrar_codigos_backup')
    else:
        messages.error(request, "✗ Código incorrecto. Inténtalo de nuevo.")
        return redirect('seguridad:activar_totp')


@login_required
@require_POST
def desactivar_totp(request, dispositivo_id):
    """
    Desactiva un dispositivo TOTP.
    """
    dispositivo = get_object_or_404(DispositivoTOTP, id=dispositivo_id, usuario=request.user)
    
    # Requerir contraseña para desactivar
    password = request.POST.get('password', '')
    if not request.user.check_password(password):
        messages.error(request, "Contraseña incorrecta.")
        return redirect('seguridad:configuracion_2fa')
    
    dispositivo.activo = False
    dispositivo.save()
    
    messages.success(request, "Autenticación de dos factores desactivada.")
    
    # Registrar desactivación
    LogAccionSensible.registrar(
        usuario=request.user,
        accion=LogAccionSensible.ACCION_2FA_DESACTIVADO,
        descripcion="Desactivó autenticación de dos factores (TOTP)",
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
        severidad=LogAccionSensible.SEVERIDAD_CRITICAL
    )
    
    return redirect('seguridad:configuracion_2fa')


@login_required
def mostrar_codigos_backup(request):
    """
    Muestra los códigos de respaldo después de activar 2FA.
    IMPORTANTE: Solo se muestran una vez.
    """
    codigos = CodigoBackup2FA.objects.filter(usuario=request.user, usado=False)
    
    context = {
        'codigos': codigos,
    }
    
    return render(request, 'seguridad/2fa/codigos_backup.html', context)


@login_required
@require_POST
def regenerar_codigos_backup(request):
    """
    Regenera los códigos de respaldo.
    Los códigos anteriores se marcan como usados.
    """
    # Marcar códigos anteriores como usados
    CodigoBackup2FA.objects.filter(usuario=request.user, usado=False).update(usado=True)
    
    # Generar nuevos códigos
    generar_codigos_backup(request.user)
    
    messages.success(request, "Códigos de respaldo regenerados exitosamente.")
    
    return redirect('seguridad:mostrar_codigos_backup')


def generar_codigos_backup(usuario, cantidad=10):
    """
    Función helper para generar códigos de respaldo.
    """
    for i in range(cantidad):
        codigo = CodigoBackup2FA.generar_codigo()
        CodigoBackup2FA.objects.create(
            usuario=usuario,
            codigo=codigo
        )


def verificar_2fa_login(request, usuario):
    """
    Verifica el código 2FA durante el login.
    Retorna True si el código es válido o si el usuario no tiene 2FA activo.
    """
    # Si el usuario no tiene 2FA activo, retornar True
    if not DispositivoTOTP.objects.filter(usuario=usuario, activo=True).exists():
        return True
    
    # Obtener código del formulario
    codigo = request.POST.get('codigo_2fa', '').strip()
    
    if not codigo:
        return False
    
    # Verificar código TOTP
    dispositivos_totp = DispositivoTOTP.objects.filter(usuario=usuario, activo=True)
    for dispositivo in dispositivos_totp:
        if dispositivo.verificar_codigo(codigo):
            return True
    
    # Verificar código de backup
    codigos_backup = CodigoBackup2FA.objects.filter(usuario=usuario, usado=False)
    for codigo_backup in codigos_backup:
        if codigo_backup.verificar(codigo):
            return True
    
    return False


# ============================================================================
# GESTIÓN DE SESIONES ACTIVAS
# ============================================================================

@login_required
def sesiones_activas(request):
    """
    Muestra todas las sesiones activas del usuario.
    """
    sesiones = SesionActiva.objects.filter(
        usuario=request.user,
        activa=True
    ).order_by('-fecha_ultima_actividad')
    
    # Sesión actual
    session_key_actual = request.session.session_key
    
    context = {
        'sesiones': sesiones,
        'session_key_actual': session_key_actual,
        'total_sesiones': sesiones.count(),
    }
    
    return render(request, 'seguridad/sesiones/lista.html', context)


@login_required
@require_POST
def cerrar_sesion_remota(request, sesion_id):
    """
    Cierra una sesión específica de forma remota.
    """
    sesion = get_object_or_404(SesionActiva, id=sesion_id, usuario=request.user)
    
    # No permitir cerrar la sesión actual desde aquí
    if sesion.session_key == request.session.session_key:
        messages.error(request, "No puedes cerrar tu sesión actual desde aquí. Usa 'Cerrar Sesión'.")
        return redirect('seguridad:sesiones_activas')
    
    sesion.cerrar_sesion()
    
    # Eliminar la sesión de Django también
    try:
        from django.contrib.sessions.models import Session
        Session.objects.filter(session_key=sesion.session_key).delete()
    except Exception as e:
        logger = logging.getLogger('seguridad')
        logger.warning(f'No se pudo eliminar sesión de Django: {str(e)}')
    
    messages.success(request, f"Sesión cerrada: {sesion.dispositivo_tipo} - {sesion.ip_address}")
    
    # Registrar cierre de sesión remota
    LogAccionSensible.registrar(
        usuario=request.user,
        accion=LogAccionSensible.ACCION_LOGOUT,
        descripcion=f"Cerró sesión remota: {sesion.dispositivo_tipo} - {sesion.ip_address}",
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
        severidad=LogAccionSensible.SEVERIDAD_WARNING
    )
    
    return redirect('seguridad:sesiones_activas')


@login_required
@require_POST
def cerrar_todas_las_sesiones(request):
    """
    Cierra todas las sesiones excepto la actual.
    """
    session_key_actual = request.session.session_key
    
    sesiones = SesionActiva.objects.filter(
        usuario=request.user,
        activa=True
    ).exclude(session_key=session_key_actual)
    
    cantidad = sesiones.count()
    
    for sesion in sesiones:
        sesion.cerrar_sesion()
    
    messages.success(request, f"Se cerraron {cantidad} sesión(es) activa(s).")
    
    # Registrar cierre masivo
    LogAccionSensible.registrar(
        usuario=request.user,
        accion=LogAccionSensible.ACCION_LOGOUT,
        descripcion=f"Cerró {cantidad} sesiones activas",
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
        severidad=LogAccionSensible.SEVERIDAD_CRITICAL
    )
    
    return redirect('seguridad:sesiones_activas')


def registrar_sesion_activa(request):
    """
    Registra una nueva sesión activa cuando el usuario hace login.
    """
    if not request.user.is_authenticated:
        return
    
    session_key = request.session.session_key
    if not session_key:
        return
    
    # Verificar si ya existe
    if SesionActiva.objects.filter(session_key=session_key).exists():
        return
    
    # Parsear user agent
    user_agent_string = request.META.get('HTTP_USER_AGENT', '')
    user_agent = parse(user_agent_string)
    
    # Crear sesión activa
    SesionActiva.objects.create(
        usuario=request.user,
        session_key=session_key,
        user_agent=user_agent_string,
        dispositivo_tipo=user_agent.get_device(),
        navegador=user_agent.get_browser(),
        sistema_operativo=user_agent.get_os(),
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
    )


# ============================================================================
# DASHBOARD DE AUDITORÍA
# ============================================================================

@login_required
def dashboard_auditoria(request):
    """
    Dashboard de auditoría de seguridad.
    Solo accesible para administradores.
    """
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('dashboard')
    
    # Estadísticas generales
    hoy = timezone.now().date()
    hace_7_dias = hoy - timedelta(days=7)
    hace_30_dias = hoy - timedelta(days=30)
    
    # Logs recientes
    logs_recientes = LogAccionSensible.objects.select_related('usuario').order_by('-fecha_hora')[:50]
    
    # Estadísticas por acción
    stats_por_accion = LogAccionSensible.objects.values('accion').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Logs críticos recientes
    logs_criticos = LogAccionSensible.objects.filter(
        severidad=LogAccionSensible.SEVERIDAD_CRITICAL,
        fecha_hora__date__gte=hace_7_dias
    ).select_related('usuario').order_by('-fecha_hora')[:20]
    
    # Intentos fallidos de login (últimas 24h)
    hace_24h = timezone.now() - timedelta(hours=24)
    intentos_fallidos = LogAccionSensible.objects.filter(
        accion=LogAccionSensible.ACCION_LOGIN_FALLIDO,
        fecha_hora__gte=hace_24h
    ).values('ip_address').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Sesiones sospechosas
    sesiones_sospechosas = SesionActiva.objects.filter(
        es_sospechosa=True,
        activa=True
    ).select_related('usuario')
    
    context = {
        'logs_recientes': logs_recientes,
        'stats_por_accion': stats_por_accion,
        'logs_criticos': logs_criticos,
        'intentos_fallidos': intentos_fallidos,
        'sesiones_sospechosas': sesiones_sospechosas,
        'total_logs_7dias': LogAccionSensible.objects.filter(fecha_hora__date__gte=hace_7_dias).count(),
        'total_logs_30dias': LogAccionSensible.objects.filter(fecha_hora__date__gte=hace_30_dias).count(),
    }
    
    return render(request, 'seguridad/auditoria/dashboard.html', context)


@login_required
def logs_auditoria(request):
    """
    Lista completa de logs con filtros.
    """
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('dashboard')
    
    logs = LogAccionSensible.objects.select_related('usuario').order_by('-fecha_hora')
    
    # Filtros
    accion = request.GET.get('accion')
    severidad = request.GET.get('severidad')
    usuario_id = request.GET.get('usuario')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if accion:
        logs = logs.filter(accion=accion)
    
    if severidad:
        logs = logs.filter(severidad=severidad)
    
    if usuario_id:
        logs = logs.filter(usuario_id=usuario_id)
    
    if fecha_desde:
        logs = logs.filter(fecha_hora__date__gte=fecha_desde)
    
    if fecha_hasta:
        logs = logs.filter(fecha_hora__date__lte=fecha_hasta)
    
    # Paginación (100 por página)
    from django.core.paginator import Paginator
    paginator = Paginator(logs, 100)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'accion_choices': LogAccionSensible.ACCION_CHOICES,
        'severidad_choices': LogAccionSensible.SEVERIDAD_CHOICES,
        'filtros_aplicados': any([accion, severidad, usuario_id, fecha_desde, fecha_hasta]),
    }
    
    return render(request, 'seguridad/auditoria/logs.html', context)


# ============================================================================
# API ENDPOINTS (AJAX)
# ============================================================================

@login_required
def api_verificar_codigo_2fa(request):
    """
    API para verificar un código 2FA en tiempo real.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    codigo = request.POST.get('codigo', '').strip()
    
    if not codigo:
        return JsonResponse({'valido': False, 'mensaje': 'Código vacío'})
    
    # Verificar TOTP
    dispositivos = DispositivoTOTP.objects.filter(usuario=request.user, activo=True)
    for dispositivo in dispositivos:
        if dispositivo.verificar_codigo(codigo):
            return JsonResponse({'valido': True, 'mensaje': 'Código correcto'})
    
    return JsonResponse({'valido': False, 'mensaje': 'Código incorrecto'})


@login_required
def api_estadisticas_seguridad(request):
    """
    API que retorna estadísticas de seguridad para dashboards.
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    hoy = timezone.now().date()
    hace_7_dias = hoy - timedelta(days=7)
    
    data = {
        'total_usuarios_2fa': DispositivoTOTP.objects.filter(activo=True).values('usuario').distinct().count(),
        'sesiones_activas': SesionActiva.objects.filter(activa=True).count(),
        'sesiones_sospechosas': SesionActiva.objects.filter(activa=True, es_sospechosa=True).count(),
        'logs_criticos_7dias': LogAccionSensible.objects.filter(
            severidad=LogAccionSensible.SEVERIDAD_CRITICAL,
            fecha_hora__date__gte=hace_7_dias
        ).count(),
        'intentos_fallidos_24h': LogAccionSensible.objects.filter(
            accion=LogAccionSensible.ACCION_LOGIN_FALLIDO,
            fecha_hora__gte=timezone.now() - timedelta(hours=24)
        ).count(),
    }
    
    return JsonResponse(data)


# =============================================================================
# BOTÓN DE PÁNICO — deduplicación 30s por canal (Telegram / Push)
# =============================================================================

@login_required
@require_http_methods(['POST'])
def panic_button(request):
    """
    Registra AlertaPanico y notifica por Telegram/Push con rate-limit 30s por canal y usuario.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Sin empresa asignada'}, status=403)

    ubicacion = (request.POST.get('ubicacion') or request.META.get('REMOTE_ADDR') or '')[:255]
    alerta = AlertaPanico.objects.create(
        empresa=empresa,
        usuario=request.user,
        ubicacion=ubicacion or None,
        estado=AlertaPanico.ESTADO_PENDIENTE,
    )

    base_key = f"panic:emp{empresa.id}:u{request.user.id}"
    tg_key = f"{base_key}:telegram"
    push_key = f"{base_key}:push"

    telegram_ok = False
    push_ok = False

    if not cache.get(tg_key):
        from core.services.telegram_outbound import send_telegram_message

        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        chat_id = getattr(settings, 'TELEGRAM_PANIC_CHAT_ID', None) or getattr(
            settings, 'TELEGRAM_CISO_CHAT_ID', None
        )
        if token and chat_id:
            msg = (
                f"🚨 PÁNICO PRISLAB\nEmpresa: {empresa.nombre}\n"
                f"Usuario: {request.user.get_username()}\nAlerta ID: {alerta.id}"
            )
            telegram_ok = send_telegram_message(token, chat_id, msg)
        cache.set(tg_key, 1, 30)

    if not cache.get(push_key):
        try:
            from core.push_service import enviar_notificacion_push
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = (
                User.objects.filter(empresa=empresa, is_staff=True)
                .prefetch_related('push_subscriptions')
            )
            for admin in admins:
                for sub in admin.push_subscriptions.filter(activa=True):
                    if enviar_notificacion_push(
                        sub,
                        'Alerta de pánico',
                        f'{request.user.get_username()} activó el botón de pánico.',
                        '/',
                    ):
                        push_ok = True
        except Exception:
            pass
        cache.set(push_key, 1, 30)

    if telegram_ok:
        alerta.telegram_enviado = True
        alerta.save(update_fields=['telegram_enviado'])

    return JsonResponse(
        {
            'ok': True,
            'alerta_id': alerta.id,
            'telegram_notificado': telegram_ok,
            'push_notificado': push_ok,
        }
    )


# ============================================================================
# RASTRO FORENSE POR PACIENTE (COFEPRIS / Punto 12)
# ============================================================================

def _parse_fecha(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
def rastro_paciente(request):
    """
    Consulta rápida: accesos forenses por paciente_id (empresa del usuario).
    Rango de fechas obligatorio acotado a máximo 90 días.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')

    paciente_raw = (request.GET.get('paciente_id') or '').strip()
    fecha_desde_s = (request.GET.get('fecha_desde') or '').strip()
    fecha_hasta_s = (request.GET.get('fecha_hasta') or '').strip()

    hoy = timezone.localdate()
    fecha_hasta = _parse_fecha(fecha_hasta_s) or hoy
    fecha_desde = _parse_fecha(fecha_desde_s) or (fecha_hasta - timedelta(days=29))

    if fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    if (fecha_hasta - fecha_desde).days > 90:
        messages.error(request, 'El rango entre fechas no puede superar 90 días.')
        fecha_desde = fecha_hasta - timedelta(days=90)

    rows = []
    total_hits = 0
    usuarios_map: dict[int, str] = {}

    if paciente_raw:
        try:
            pid = int(paciente_raw)
        except ValueError:
            messages.error(request, 'paciente_id debe ser un número entero.')
            pid = None
        if pid is not None:
            qs = (
                ForenseAcceso.objects.filter(
                    empresa=empresa,
                    paciente_id=pid,
                    created_at__date__gte=fecha_desde,
                    created_at__date__lte=fecha_hasta,
                )
                .order_by('-created_at')
            )
            total_hits = qs.count()
            rows = list(qs[:5000])
            uids = {r.usuario_id for r in rows if r.usuario_id}
            for u in Usuario.objects.filter(pk__in=uids).only('id', 'username', 'first_name', 'last_name'):
                usuarios_map[u.pk] = (u.get_full_name() or u.username or str(u.pk))

    if request.GET.get('format') == 'csv' and paciente_raw:
        try:
            pid = int(paciente_raw)
        except ValueError:
            return HttpResponse('paciente_id inválido', status=400)
        qs = (
            ForenseAcceso.objects.filter(
                empresa=empresa,
                paciente_id=pid,
                created_at__date__gte=fecha_desde,
                created_at__date__lte=fecha_hasta,
            )
            .order_by('-created_at')[:5000]
        )
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="rastro_paciente_{pid}.csv"'
        w = csv.writer(resp)
        w.writerow(
            ['created_at', 'accion', 'es_publico', 'usuario_id', 'orden_id', 'ip_address', 'token_prefix', 'metadata']
        )
        for r in qs:
            w.writerow(
                [
                    timezone.localtime(r.created_at).isoformat(),
                    r.accion,
                    r.es_publico,
                    r.usuario_id or '',
                    r.orden_id or '',
                    r.ip_address or '',
                    r.token_prefix or '',
                    json.dumps(r.metadata, ensure_ascii=False) if r.metadata else '',
                ]
            )
        return resp

    for display in rows:
        display.usuario_label = (
            'Público'
            if display.es_publico
            else (usuarios_map.get(display.usuario_id) if display.usuario_id else '—')
        )
        display.metadata_json = json.dumps(display.metadata, ensure_ascii=False) if display.metadata else ''

    return render(
        request,
        'seguridad/rastro_paciente.html',
        {
            'paciente_id': paciente_raw,
            'fecha_desde': fecha_desde.isoformat(),
            'fecha_hasta': fecha_hasta.isoformat(),
            'rows': rows,
            'total_hits': total_hits,
            'accion_choices': ForenseAcceso.ACCION_CHOICES,
        },
    )
