"""
PRISLAB V5.0 - DECORADORES DE SEGURIDAD Y LÓGICA DE NEGOCIO
===========================================================
Fecha: 1 de Febrero de 2026
Objetivo: Decoradores reutilizables para control de acceso y validaciones

FILOSOFÍA:
- Separación de responsabilidades (no meter lógica en vistas)
- Reutilización de código
- Mensajes de error claros para el usuario
"""

from functools import wraps
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger('decorators')


# ==============================================================================
# DECORADOR: VERIFICACIÓN DE PAGO PARA IMPRESIÓN DE RESULTADOS
# ==============================================================================

def check_payment_status(view_func):
    """
    Decorador que verifica si una orden de laboratorio está pagada antes de permitir
    imprimir resultados o generar PDFs.
    
    LÓGICA DE NEGOCIO:
    - Si la orden NO está pagada: Bloquea y muestra error
    - Si la orden SÍ está pagada: Permite continuar
    
    Uso:
        @login_required
        @check_payment_status
        def imprimir_resultados(request, orden_id):
            # Esta vista solo se ejecuta si la orden está pagada
            ...
    
    Args:
        view_func: Función de vista a decorar
    
    Returns:
        Función decorada con validación de pago
    """
    @wraps(view_func)
    def wrapper(request, orden_id, *args, **kwargs):
        from core.models import OrdenDeServicio
        
        try:
            # Intentar obtener la orden
            orden = OrdenDeServicio.objects.select_related('paciente', 'empresa').get(
                id=orden_id,
                empresa=getattr(request.user, 'empresa', None)
            )
            
            # VALIDACIÓN CRÍTICA: ¿Está pagada?
            if not orden.estado_pago:
                logger.warning(
                    f"Intento de acceso a resultados sin pago. "
                    f"Usuario: {request.user.username}, Orden: {orden_id}"
                )
                
                # Si es AJAX (JsonResponse)
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'mensaje': '❌ ORDEN NO PAGADA',
                        'detalle': 'No se pueden imprimir resultados de órdenes no pagadas. '
                                   'Dirígete a Caja para procesar el pago primero.',
                        'orden_id': orden_id,
                        'folio': orden.folio_orden or f'ORD-{orden_id}',
                        'monto_total': str(orden.total),
                        'redirect_url': f'/laboratorio/recepcion/?orden_pendiente={orden_id}'
                    }, status=403)
                
                # Si es request normal (HTML)
                return render(request, 'core/error.html', {
                    'titulo': '❌ ORDEN NO PAGADA',
                    'mensaje': 'No se pueden imprimir resultados de órdenes no pagadas.',
                    'detalle': f'Orden #{orden.folio_orden or orden_id} - Total: ${orden.total}',
                    'accion': 'Procesa el pago en Caja primero',
                    'redirect_url': f'/laboratorio/recepcion/?orden_pendiente={orden_id}',
                    'redirect_text': 'Ir a Caja'
                }, status=403)
            
            # Si llegó aquí, la orden SÍ está pagada
            # Adjuntar la orden al request para evitar re-queries en la vista
            request.orden_validada = orden
            
            # Ejecutar la vista original
            return view_func(request, orden_id, *args, **kwargs)
        
        except OrdenDeServicio.DoesNotExist:
            logger.error(f"Orden no encontrada: {orden_id}. Usuario: {request.user.username}")
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'mensaje': 'Orden no encontrada',
                    'orden_id': orden_id
                }, status=404)
            
            return render(request, 'core/error.html', {
                'titulo': '❌ Orden No Encontrada',
                'mensaje': f'La orden #{orden_id} no existe o no pertenece a tu empresa.',
                'detalle': 'Verifica el folio e intenta nuevamente.'
            }, status=404)
        
        except Exception as e:
            logger.error(
                f"Error en decorador check_payment_status. "
                f"Usuario: {request.user.username}, Orden: {orden_id}, Error: {str(e)}",
                exc_info=True
            )
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'mensaje': 'Error al validar el estado de pago',
                    'detalle': str(e)
                }, status=500)
            
            return render(request, 'core/error.html', {
                'titulo': '❌ Error del Sistema',
                'mensaje': 'Ocurrió un error al validar el estado de pago.',
                'detalle': str(e) if request.user.is_staff else 'Contacta al administrador.'
            }, status=500)
    
    return wrapper


# ==============================================================================
# DECORADOR: VERIFICACIÓN DE RESULTADOS VALIDADOS
# ==============================================================================

def check_results_validated(view_func):
    """
    Decorador que verifica si los resultados de una orden están validados antes
    de permitir la impresión o entrega.
    
    LÓGICA DE NEGOCIO (ISO 15189):
    - Solo resultados VALIDADOS pueden imprimirse
    - Previene entrega de resultados preliminares
    
    Uso:
        @login_required
        @check_payment_status  # Primero verificar pago
        @check_results_validated  # Luego verificar validación
        def imprimir_resultados(request, orden_id):
            ...
    """
    @wraps(view_func)
    def wrapper(request, orden_id, *args, **kwargs):
        from core.models import OrdenDeServicio
        
        try:
            # Si el decorador anterior ya cargó la orden, usarla
            if hasattr(request, 'orden_validada'):
                orden = request.orden_validada
            else:
                orden = OrdenDeServicio.objects.get(id=orden_id, empresa=getattr(request.user, 'empresa', None))
            
            # VALIDACIÓN CRÍTICA: ¿Están validados los resultados?
            if orden.estado != 'VALIDADO':
                logger.warning(
                    f"Intento de imprimir resultados sin validar. "
                    f"Usuario: {request.user.username}, Orden: {orden_id}, Estado: {orden.estado}"
                )
                
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'mensaje': '❌ RESULTADOS NO VALIDADOS',
                        'detalle': 'Los resultados deben ser validados por el Químico antes de imprimirse.',
                        'estado_actual': orden.estado,
                        'orden_id': orden_id
                    }, status=403)
                
                return render(request, 'core/error.html', {
                    'titulo': '❌ RESULTADOS NO VALIDADOS',
                    'mensaje': 'Los resultados deben ser validados antes de imprimirse.',
                    'detalle': f'Estado actual: {orden.get_estado_display()}',
                    'accion': 'Solicita al Químico que valide los resultados primero.',
                    'redirect_url': f'/laboratorio/captura/{orden_id}/',
                    'redirect_text': 'Ir a Captura de Resultados'
                }, status=403)
            
            # Adjuntar orden al request
            request.orden_validada = orden
            
            # Ejecutar vista original
            return view_func(request, orden_id, *args, **kwargs)
        
        except Exception as e:
            logger.error(f"Error en check_results_validated: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Error al validar el estado de resultados'
            }, status=500)
    
    return wrapper


# ==============================================================================
# DECORADOR: VERIFICACIÓN DE MÓDULO ACTIVO
# ==============================================================================

def module_required(module_name):
    """
    Decorador que verifica si un módulo está activo para la empresa del usuario.
    
    LÓGICA DE NEGOCIO (SaaS Multi-Tenant):
    - Solo empresas con el módulo activado pueden acceder
    - Previene acceso a funcionalidades no contratadas
    
    Uso:
        @login_required
        @module_required('modulo_laboratorio')
        def dashboard_lab(request):
            ...
    
    Args:
        module_name: Nombre del campo en ConfiguracionModulos (ej: 'modulo_laboratorio')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                empresa = getattr(request.user, 'empresa', None)
                
                if not empresa:
                    logger.error(f"Usuario {request.user.username} sin empresa asignada")
                    return HttpResponseForbidden("Usuario sin empresa asignada.")
                
                config = empresa.configuracion_modulos
                modulo_activo = getattr(config, module_name, False)
                
                if not modulo_activo:
                    logger.warning(
                        f"Acceso denegado a módulo desactivado. "
                        f"Usuario: {request.user.username}, Módulo: {module_name}"
                    )
                    
                    return render(request, 'core/error.html', {
                        'titulo': '🔒 MÓDULO NO DISPONIBLE',
                        'mensaje': 'Este módulo no está activado para tu empresa.',
                        'detalle': f'Módulo: {module_name.replace("modulo_", "").title()}',
                        'accion': 'Contacta al administrador para activar esta funcionalidad.',
                        'redirect_url': '/',
                        'redirect_text': 'Volver al Inicio'
                    }, status=403)
                
                # Módulo activo, continuar
                return view_func(request, *args, **kwargs)
            
            except Exception as e:
                logger.error(f"Error en module_required: {str(e)}", exc_info=True)
                return HttpResponseForbidden("Error al validar el módulo.")
        
        return wrapper
    return decorator


# ==============================================================================
# DECORADOR: VERIFICACIÓN DE ROL DE USUARIO
# ==============================================================================

def role_required(*allowed_roles):
    """
    Decorador que restringe acceso a vistas según el rol del usuario.

    Permite acceso a superusers y is_staff siempre.
    Los roles se comparan en mayúsculas contra usuario.rol.

    Uso:
        @login_required
        @role_required('MEDICO', 'ADMIN')
        def nueva_consulta_soap(request, cita_id):
            ...

    Args:
        *allowed_roles: Roles permitidos (ej: 'MEDICO', 'QUIMICO', 'ADMIN', 'CAJERO', 'RECEPCION')
    """
    allowed_upper = {r.upper() for r in allowed_roles}

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.is_staff:
                return view_func(request, *args, **kwargs)

            user_rol = (getattr(user, 'rol', '') or '').upper().strip()
            if user_rol in allowed_upper:
                return view_func(request, *args, **kwargs)

            has_group = user.groups.filter(name__in=allowed_upper).exists()
            if has_group:
                return view_func(request, *args, **kwargs)

            logger.warning(
                f"Acceso denegado por rol. Usuario: {user.username}, "
                f"Rol: {user_rol}, Requeridos: {allowed_upper}"
            )

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'mensaje': 'No tiene permisos para acceder a esta función.'
                }, status=403)

            return HttpResponseForbidden(
                "No tiene permisos para acceder a esta función. "
                "Contacte al administrador."
            )

        return wrapper
    return decorator
