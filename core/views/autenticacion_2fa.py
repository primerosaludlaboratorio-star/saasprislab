"""
core/views/autenticacion_2fa.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2FA integrado con seguridad.DispositivoTOTP (ya en DB).
Incluye: setup, verificación en login, desactivación,
bypass de IP interna, código maestro de emergencia CISO.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import logging
import hashlib

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('core.2fa')

ROLES_2FA_OBLIGATORIO = {'ADMIN', 'DIRECTOR'}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_client_ip(request) -> str:
    """
    REMOTE_ADDR es la IP que Nginx ve directamente (no falsificable por
    el cliente) y es la fuente de verdad para decisiones de seguridad.
    Nunca usar X-Forwarded-For aquí: es un header controlado por el
    cliente y permitiría spoofear una IP interna para saltar el 2FA.
    """
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def _ip_exenta_2fa(request) -> bool:
    """Bypass para desarrollo local y redes internas configuradas."""
    ip = _get_client_ip(request)
    bypass_ips = {'127.0.0.1', 'localhost', '::1'}
    bypass_ips.update(getattr(settings, 'IPS_INTERNAS_2FA_BYPASS', []))
    if ip in bypass_ips:
        return True
    # Bypass para subredes /24 internas (192.168.x.x, 10.x.x.x)
    if ip.startswith('192.168.') or ip.startswith('10.'):
        return True
    return False


def _2fa_obligatorio_por_rol(usuario) -> bool:
    from core.services.feature_flags import flag_activo
    if not flag_activo('2FA_OBLIGATORIO_ACTIVO', getattr(usuario, 'empresa', None)):
        return False
    rol = getattr(usuario, 'rol', '')
    return rol in ROLES_2FA_OBLIGATORIO


def _2fa_activo_para_usuario(usuario) -> bool:
    """True si el usuario tiene al menos un DispositivoTOTP activo y confirmado."""
    try:
        return usuario.dispositivos_totp.filter(activo=True, confirmado=True).exists()
    except Exception:
        return False


def _verificar_codigo_maestro(codigo: str) -> bool:
    """Código de emergencia para el CISO (PRISLAB_MASTER_RECOVERY_CODE en settings)."""
    master = getattr(settings, 'PRISLAB_MASTER_RECOVERY_CODE', '')
    if not master or not codigo:
        return False
    return hashlib.sha256(codigo.encode()).hexdigest() == hashlib.sha256(master.encode()).hexdigest()


def _notificar_ciso_uso_codigo_maestro(usuario, request):
    """Alerta al CISO cuando se usa el código de emergencia."""
    try:
        ip = _get_client_ip(request)
        mensaje = (
            f"⚠️ ALERTA CISO: Código maestro 2FA usado\n"
            f"Usuario: {usuario.username}\n"
            f"IP: {ip}\n"
            f"Hora: {timezone.now().isoformat()}"
        )
        _notificar_telegram(mensaje)
        logger.critical(f'[2FA] Código maestro usado — user={usuario.username} ip={ip}')
    except Exception as exc:
        logger.error(f'[2FA] No se pudo notificar CISO: {exc}')


def _notificar_telegram(mensaje: str):
    from core.services.telegram_outbound import send_telegram_message

    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or None
    chat_id = getattr(settings, 'TELEGRAM_CISO_CHAT_ID', '') or None
    send_telegram_message(token, chat_id, mensaje)


def notificar_alerta_ciso_expedientes(usuario_id: int, count: int, ventana_minutos: int = 60):
    """Llamado por el middleware NOM-024 cuando hay >10 accesos/hora."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        usuario = User.objects.get(pk=usuario_id)
        mensaje = (
            f"🚨 ALERTA NOM-024: Acceso masivo a expedientes\n"
            f"Usuario: {usuario.username}\n"
            f"Accesos: {count} en {ventana_minutos} min\n"
            f"Hora: {timezone.now().isoformat()}"
        )
        _notificar_telegram(mensaje)
        # Email al CISO si está configurado
        ciso_email = getattr(settings, 'CISO_EMAIL', '')
        if ciso_email:
            from django.core.mail import send_mail
            try:
                send_mail(
                    subject='[PRISLAB] ALERTA NOM-024: Acceso masivo',
                    message=mensaje,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[ciso_email],
                    fail_silently=True,
                )
            except Exception:
                pass
    except Exception as exc:
        logger.error(f'[2FA] notificar_alerta_ciso_expedientes error: {exc}')


# ─── Vistas ───────────────────────────────────────────────────────────────────

@login_required
def setup_2fa(request):
    """
    Configura un nuevo DispositivoTOTP para el usuario.
    Delega a seguridad.views.activar_totp usando redirect.
    """
    return redirect('seguridad:activar_totp')


def verificar_2fa(request):
    """
    Verifica el código TOTP durante el login.
    El usuario ya está autenticado parcialmente (en sesión pendiente).
    """
    usuario_id = request.session.get('_2fa_user_id')
    backend = request.session.get('_2fa_backend')

    if not usuario_id:
        return redirect('login')

    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        usuario = User.objects.get(pk=usuario_id)
    except User.DoesNotExist:
        return redirect('login')

    # Bypass para IP interna / localhost
    if _ip_exenta_2fa(request):
        login(request, usuario, backend=backend)
        request.session.pop('_2fa_user_id', None)
        request.session.pop('_2fa_backend', None)
        return redirect('home')

    cache_key = f'2fa_intentos_{usuario.pk}'
    intentos = cache.get(cache_key, 0)
    if intentos >= 5:
        logger.warning(
            'Bloqueo temporal 2FA por exceso de intentos: usuario=%s id=%s',
            usuario.username, usuario.pk,
        )
        return render(request, 'core/2fa/verificar.html', {
            'error': 'Demasiados intentos fallidos. Espera 15 minutos antes de volver a intentar.',
        })

    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()

        # Intentar con código maestro de emergencia
        if _verificar_codigo_maestro(codigo):
            cache.delete(cache_key)
            _notificar_ciso_uso_codigo_maestro(usuario, request)
            login(request, usuario, backend=backend)
            request.session.pop('_2fa_user_id', None)
            request.session.pop('_2fa_backend', None)
            return redirect('home')

        # Intentar con código de respaldo
        from seguridad.models import CodigoBackup2FA
        for codigo_backup in CodigoBackup2FA.objects.filter(usuario=usuario, usado=False):
            if codigo_backup.verificar(codigo):
                cache.delete(cache_key)
                login(request, usuario, backend=backend)
                request.session.pop('_2fa_user_id', None)
                request.session.pop('_2fa_backend', None)
                return redirect('home')

        # Intentar con DispositivoTOTP activo
        dispositivos = usuario.dispositivos_totp.filter(activo=True, confirmado=True)
        for dispositivo in dispositivos:
            if dispositivo.verificar_codigo(codigo):
                cache.delete(cache_key)
                from seguridad.models import LogAccionSensible
                try:
                    LogAccionSensible.registrar(
                        usuario=usuario,
                        accion=LogAccionSensible.ACCION_LOGIN,
                        descripcion=f'Login 2FA exitoso — dispositivo: {dispositivo.nombre}',
                        ip_address=_get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        ruta_url=request.path,
                        metodo_http=request.method,
                    )
                except Exception:
                    pass
                login(request, usuario, backend=backend)
                request.session.pop('_2fa_user_id', None)
                request.session.pop('_2fa_backend', None)
                return redirect('home')

        cache.set(cache_key, intentos + 1, timeout=900)  # 15 minutos
        return render(request, 'core/2fa/verificar.html', {
            'error': 'Código incorrecto. Verifica tu app de autenticación.',
        })

    return render(request, 'core/2fa/verificar.html', {})


@login_required
@require_http_methods(['POST'])
def desactivar_2fa(request):
    """Desactiva todos los dispositivos TOTP del usuario."""
    usuario = request.user
    rol = getattr(usuario, 'rol', '')
    if rol in ROLES_2FA_OBLIGATORIO and _2fa_obligatorio_por_rol(usuario):
        return JsonResponse({'error': 'Tu rol requiere 2FA activo. No puedes desactivarlo.'}, status=403)

    try:
        usuario.dispositivos_totp.filter(activo=True).update(activo=False)
        from seguridad.models import LogAccionSensible
        LogAccionSensible.registrar(
            usuario=usuario,
            accion=LogAccionSensible.ACCION_2FA_DESACTIVADO,
            descripcion='Usuario desactivó 2FA',
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            ruta_url=request.path,
            metodo_http='POST',
        )
        return JsonResponse({'ok': True, 'mensaje': '2FA desactivado correctamente.'})
    except Exception as exc:
        logger.error(f'[2FA] Error desactivando 2FA: {exc}')
        return JsonResponse({'error': str(exc)}, status=500)
