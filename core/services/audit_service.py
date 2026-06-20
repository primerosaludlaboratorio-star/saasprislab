"""
PRISLAB R107 - Servicio de Auditoria Global
=============================================
Proporciona funciones utilitarias para registrar acciones criticas
en la tabla AuditLog (Bitacora Forense).

Uso:
    from core.services.audit_service import registrar_auditoria
    registrar_auditoria(
        request=request,
        accion='UPDATE',
        modelo='ResultadoParametro',
        objeto_id='1234',
        datos_anteriores={'valor': '100'},
        datos_nuevos={'valor': '120'},
    )
"""

import hashlib
import json
import logging

logger = logging.getLogger('audit')


def registrar_auditoria(
    accion,
    modelo,
    objeto_id,
    datos_anteriores=None,
    datos_nuevos=None,
    request=None,
    usuario=None,
    empresa=None,
):
    """
    Registra una entrada en el AuditLog.
    
    Args:
        accion: 'CREATE', 'UPDATE', 'DELETE', 'VIEW', 'PRINT'
        modelo: Nombre del modelo Django afectado (str)
        objeto_id: ID del objeto afectado (str o int)
        datos_anteriores: dict con valores previos (opcional)
        datos_nuevos: dict con valores nuevos (opcional)
        request: HttpRequest (para extraer usuario, IP, user-agent)
        usuario: Usuario instance (si no hay request)
        empresa: Empresa instance (si no hay request)
    """
    try:
        from core.models import AuditLog, Empresa, Usuario

        # Extraer datos del request si existe
        _usuario = usuario
        _empresa = empresa
        _ip = None
        _ua = None

        if request:
            if hasattr(request, 'user') and request.user.is_authenticated:
                _usuario = request.user
                _empresa = getattr(request.user, 'empresa', None)
            _ip = _get_client_ip(request)
            _ua = request.META.get('HTTP_USER_AGENT', '')[:255]

        if not _empresa:
            logger.warning(
                "[AUDIT] Sin empresa en request/usuario; no se registra auditoría "
                "(multi-tenant: no se usa fallback a primera empresa)."
            )
            return None

        # Generar hash de verificacion (SHA-256 del contenido)
        hash_data = f"{accion}|{modelo}|{objeto_id}|{json.dumps(datos_anteriores, default=str)}|{json.dumps(datos_nuevos, default=str)}"
        hash_ver = hashlib.sha256(hash_data.encode()).hexdigest()

        log_entry = AuditLog.objects.create(
            empresa=_empresa,
            usuario=_usuario,
            accion=accion,
            modelo_afectado=modelo,
            objeto_id=str(objeto_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip_address=_ip,
            user_agent=_ua,
            hash_verificacion=hash_ver,
        )

        logger.info(
            f"[AUDIT] {accion} {modelo} #{objeto_id} por "
            f"{_usuario.get_full_name() if _usuario else 'SISTEMA'}"
        )
        return log_entry

    except Exception as e:
        logger.error(f"[AUDIT] Error registrando auditoria: {e}")
        return None


def audit_critical_action(
    request,
    action_type,
    model_name,
    object_id,
    changes=None,
    old_data=None,
    new_data=None,
):
    """
    Log a critical action with full forensic detail.
    Wrapper around registrar_auditoria for high-risk actions (delete, price change,
    refund, role change, etc.).

    Args:
        request: HttpRequest (for user, IP, user-agent).
        action_type: One of 'CREATE', 'UPDATE', 'DELETE', 'VIEW', 'PRINT'.
        model_name: Django model name (e.g. 'OrdenDeServicio', 'Producto').
        object_id: ID of the affected object (str or int).
        changes: Optional short description of what changed (stored in datos_nuevos).
        old_data: Optional dict of previous values (stored in datos_anteriores).
        new_data: Optional dict of new values (stored in datos_nuevos).

    Returns:
        AuditLog instance or None.
    """
    datos_anteriores = old_data
    datos_nuevos = new_data or {}
    if changes:
        datos_nuevos = dict(datos_nuevos) if datos_nuevos else {}
        datos_nuevos['_descripcion'] = str(changes)
    return registrar_auditoria(
        accion=action_type,
        modelo=model_name,
        objeto_id=str(object_id),
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos or None,
        request=request,
    )


def _get_client_ip(request):
    """Extrae la IP real del cliente. Usa REMOTE_ADDR (no falsificable) — este valor alimenta la auditoría."""
    return request.META.get('REMOTE_ADDR')
