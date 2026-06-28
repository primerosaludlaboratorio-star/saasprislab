"""
Seguridad V8.0 — Auth2Fa
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
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from user_agents import parse

from core.decorators import role_required
from core.models import ForenseAcceso, Usuario
from core.utils.empresa_request import get_empresa_usuario

from seguridad.models import (
    DispositivoTOTP, DispositivoSMS, CodigoBackup2FA,
    SesionActiva, LogAccionSensible, AlertaPanico
)


def _usuario_tiene_2fa_activo(usuario) -> bool:
    """Verdad única para saber si el usuario tiene 2FA activo por cualquier canal."""
    return (
        DispositivoTOTP.objects.filter(usuario=usuario, activo=True).exists()
        or DispositivoSMS.objects.filter(usuario=usuario, activo=True).exists()
    )


def _verificar_codigo_2fa_usuario(usuario, codigo: str):
    """
    Verifica un código 2FA y devuelve (valido: bool, tipo: str).

    Tipos posibles:
      - totp
      - backup
      - master_recovery
      - invalid
    """
    codigo = (codigo or '').strip()
    if not codigo:
        return False, 'invalid'

    dispositivos_totp = DispositivoTOTP.objects.filter(usuario=usuario, activo=True)
    for dispositivo in dispositivos_totp:
        if dispositivo.verificar_codigo(codigo):
            return True, 'totp'

    codigos_backup = CodigoBackup2FA.objects.filter(usuario=usuario, usado=False)
    for codigo_backup in codigos_backup:
        if codigo_backup.verificar(codigo):
            return True, 'backup'

    master_code = str(getattr(settings, 'PRISLAB_MASTER_RECOVERY_CODE', '') or '').strip()
    if master_code and codigo == master_code:
        logger = logging.getLogger('seguridad')
        logger.warning(
            'Se utilizó PRISLAB_MASTER_RECOVERY_CODE para usuario=%s id=%s',
            getattr(usuario, 'username', '?'),
            getattr(usuario, 'id', None),
        )
        return True, 'master_recovery'

    return False, 'invalid'

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
    tiene_2fa_activo = _usuario_tiene_2fa_activo(request.user)
    
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
    if not _usuario_tiene_2fa_activo(usuario):
        return True
    
    # Obtener código del formulario
    codigo = request.POST.get('codigo_2fa', '').strip()
    
    if not codigo:
        return False
    
    valido, _tipo = _verificar_codigo_2fa_usuario(usuario, codigo)
    return bool(valido)


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
    except DatabaseError as e:
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
