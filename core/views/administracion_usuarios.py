"""
Administración de Usuarios (Roles y Títulos)
REGLA: Formulario incluye 'Título Profesional' y 'Enfoque' para equipo de élite.
Log de auditoría en cada cambio administrativo para trazabilidad total.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.contrib.auth import get_user_model
import json
from decimal import Decimal

from core.utils.trazabilidad import registrar_trazabilidad
from core.utils.estandares_industriales import auditar_cambio_campo
import logging

Usuario = get_user_model()


def _empresa_tenant_admin(request):
    """Misma resolución que el resto del SaaS (middleware + FK usuario)."""
    return getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)


def _requiere_empresa_o_superuser(request):
    """Admin de tenant debe tener empresa; superusuario puede operar sin tenant explícito."""
    if request.user.is_superuser:
        return True
    if _empresa_tenant_admin(request):
        return True
    return False


@login_required
def gestionar_usuarios(request):
    """
    Vista principal para gestión de usuarios.
    REGLA: Incluir campos de 'Título Profesional' y 'Enfoque'.
    """
    empresa = _empresa_tenant_admin(request)

    # Solo admin puede gestionar usuarios
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('home')

    if not request.user.is_superuser:
        if not empresa:
            from django.contrib import messages
            messages.error(request, 'Usuario sin empresa asignada.')
            return redirect('home')
        usuarios = Usuario.objects.filter(empresa=empresa).select_related('empresa').order_by('username')
    else:
        usuarios = Usuario.objects.select_related('empresa').order_by('empresa__nombre', 'username')
    
    return render(request, 'core/administracion/usuarios.html', {
        'empresa': empresa,
        'usuarios': usuarios
    })


@login_required
@require_http_methods(["GET"])
def api_obtener_usuario(request, usuario_id):
    """
    API para obtener datos de un usuario (para modal de edición).
    """
    empresa = _empresa_tenant_admin(request)

    # Solo admin puede ver datos de usuarios
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Acceso denegado'
        }, status=403)

    if not _requiere_empresa_o_superuser(request):
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Usuario sin empresa asignada.',
        }, status=403)

    try:
        if request.user.is_superuser:
            usuario = get_object_or_404(Usuario, id=usuario_id)
        else:
            usuario = get_object_or_404(Usuario, id=usuario_id, empresa=empresa)
        
        return JsonResponse({
            'status': 'success',
            'usuario': {
                'id': usuario.id,
                'username': usuario.username,
                'first_name': usuario.first_name,
                'last_name': usuario.last_name,
                'email': usuario.email,
                'rol': usuario.rol,
                'titulo_profesional': usuario.titulo_profesional or '',
                'enfoque_profesional': usuario.enfoque_profesional or '',
                'departamento': usuario.departamento or '',
                'cedula_interna': usuario.cedula_interna or '',
                'is_active': usuario.is_active,
                'is_staff': usuario.is_staff,
            }
        })
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_obtener_usuario (administracion_usuarios.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al obtener usuario: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_actualizar_usuario(request, usuario_id):
    """
    API para actualizar datos de un usuario.
    REGLA: Auditoría en cada cambio administrativo.
    """
    empresa = _empresa_tenant_admin(request)

    # Solo admin puede actualizar usuarios
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Acceso denegado'
        }, status=403)

    if not _requiere_empresa_o_superuser(request):
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Usuario sin empresa asignada.',
        }, status=403)

    try:
        if request.user.is_superuser:
            usuario = get_object_or_404(Usuario, id=usuario_id)
        else:
            usuario = get_object_or_404(Usuario, id=usuario_id, empresa=empresa)
        data = json.loads(request.body)

        if not request.user.is_superuser:
            for campo_tenant in ('empresa', 'empresa_id'):
                if campo_tenant in data:
                    return JsonResponse({
                        'status': 'error',
                        'mensaje': 'No está permitido reasignar la empresa del usuario.',
                    }, status=403)

        # Guardar valores anteriores para auditoría
        valores_anteriores = {
            'first_name': usuario.first_name,
            'last_name': usuario.last_name,
            'email': usuario.email,
            'rol': usuario.rol,
            'titulo_profesional': usuario.titulo_profesional,
            'enfoque_profesional': usuario.enfoque_profesional,
            'departamento': usuario.departamento,
            'cedula_interna': usuario.cedula_interna,
            'is_active': usuario.is_active,
            'is_staff': usuario.is_staff,
        }
        
        # Actualizar campos
        if 'first_name' in data:
            usuario.first_name = data['first_name']
        if 'last_name' in data:
            usuario.last_name = data['last_name']
        if 'email' in data:
            usuario.email = data['email']
        if 'rol' in data:
            usuario.rol = data['rol']
        if 'titulo_profesional' in data:
            usuario.titulo_profesional = data['titulo_profesional']
        if 'enfoque_profesional' in data:
            usuario.enfoque_profesional = data['enfoque_profesional']
        if 'departamento' in data:
            usuario.departamento = data['departamento']
        if 'cedula_interna' in data:
            usuario.cedula_interna = data['cedula_interna']
        if 'is_active' in data:
            usuario.is_active = data['is_active']
        if 'is_staff' in data:
            usuario.is_staff = data['is_staff']
        
        usuario.save()
        
        # Registrar auditoría de cambios administrativos
        valores_nuevos = {
            'first_name': usuario.first_name,
            'last_name': usuario.last_name,
            'email': usuario.email,
            'rol': usuario.rol,
            'titulo_profesional': usuario.titulo_profesional,
            'enfoque_profesional': usuario.enfoque_profesional,
            'departamento': usuario.departamento,
            'cedula_interna': usuario.cedula_interna,
            'is_active': usuario.is_active,
            'is_staff': usuario.is_staff,
        }
        
        # Registrar cada campo modificado
        cambios_detectados = []
        for campo, valor_anterior in valores_anteriores.items():
            valor_nuevo = valores_nuevos.get(campo)
            if valor_anterior != valor_nuevo:
                cambios_detectados.append({
                    'campo': campo,
                    'anterior': valor_anterior,
                    'nuevo': valor_nuevo
                })
                
                # Registrar auditoría individual por campo
                auditar_cambio_campo(
                    campo_nombre=campo,
                    valor_anterior=valor_anterior,
                    valor_nuevo=valor_nuevo,
                    modelo_instancia=usuario,
                    request=request,
                    modulo='ADMINISTRACION',
                    accion='UPDATE'
                )
        
        # Registrar trazabilidad general
        registrar_trazabilidad(
            tipo_operacion='USUARIO_MODIFICADO',
            modulo='ADMINISTRACION',
            referencia_id=usuario.id,
            referencia_tipo='Usuario',
            accion='UPDATE',
            descripcion=f'Usuario {usuario.username} modificado por {request.user.username}',
            usuario=request.user,
            empresa=empresa,
            datos_anteriores=valores_anteriores,
            datos_nuevos=valores_nuevos,
            request=request,
        )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Usuario actualizado correctamente',
            'cambios': cambios_detectados
        })
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_actualizar_usuario (administracion_usuarios.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al actualizar usuario: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_actualizar_tarifa(request, estudio_id):
    """
    API para actualizar tarifa de un estudio.
    REGLA: Log de auditoría en cada cambio de tarifa.
    """
    empresa = _empresa_tenant_admin(request)

    # Solo admin puede actualizar tarifas
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Acceso denegado'
        }, status=403)

    # Permitir superuser/staff CON empresa válida - consistencia con LIMS
    if not empresa:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Usuario sin empresa asignada.',
        }, status=403)

    try:
        from laboratorio.models import Estudio as EstudioLaboratorio

        estudio = get_object_or_404(EstudioLaboratorio, id=estudio_id)
        data = json.loads(request.body)

        precio_anterior = estudio.precio_base
        precio_nuevo = Decimal(str(data.get('precio', 0)))

        estudio.precio_base = precio_nuevo
        estudio.save(update_fields=['precio_base'])
        
        # Registrar auditoría de cambio de tarifa
        auditar_cambio_campo(
            campo_nombre='precio',
            valor_anterior=str(precio_anterior),
            valor_nuevo=str(precio_nuevo),
            modelo_instancia=estudio,
            request=request,
            modulo='ADMINISTRACION',
            accion='UPDATE'
        )
        
        registrar_trazabilidad(
            tipo_operacion='TARIFA_MODIFICADA',
            modulo='ADMINISTRACION',
            referencia_id=estudio.id,
            referencia_tipo='Estudio',
            accion='UPDATE',
            descripcion=f'Tarifa de {estudio.nombre} modificada: ${precio_anterior} → ${precio_nuevo}',
            usuario=request.user,
            empresa=empresa,
            datos_anteriores={'precio': str(precio_anterior)},
            datos_nuevos={'precio': str(precio_nuevo)},
            request=request,
        )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Tarifa actualizada correctamente'
        })
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_actualizar_tarifa (administracion_usuarios.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al actualizar tarifa: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_actualizar_permiso(request, perfil_id):
    """
    API para actualizar permiso de un perfil.
    REGLA: Log de auditoría en cada cambio de permiso.
    """
    empresa = _empresa_tenant_admin(request)

    # Solo admin puede actualizar permisos
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Acceso denegado'
        }, status=403)

    # SIN BYPASS SUPERUSER - validar empresa siempre
    if not empresa:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Usuario sin empresa asignada.',
        }, status=403)

    try:
        from core.models.seguridad_perfiles import PermisoModulo
        if request.user.is_superuser:
            permiso = get_object_or_404(PermisoModulo, id=perfil_id)
        else:
            permiso = get_object_or_404(PermisoModulo, id=perfil_id, perfil__empresa=empresa)
        data = json.loads(request.body)
        
        permitido_anterior = permiso.permitido
        permitido_nuevo = data.get('permitido', False)
        
        permiso.permitido = permitido_nuevo
        permiso.save()
        
        # Registrar auditoría de cambio de permiso
        auditar_cambio_campo(
            campo_nombre='permitido',
            valor_anterior=str(permitido_anterior),
            valor_nuevo=str(permitido_nuevo),
            modelo_instancia=permiso,
            request=request,
            modulo='ADMINISTRACION',
            accion='UPDATE'
        )
        
        registrar_trazabilidad(
            tipo_operacion='PERMISO_MODIFICADO',
            modulo='ADMINISTRACION',
            referencia_id=permiso.id,
            referencia_tipo='PermisoModulo',
            accion='UPDATE',
            descripcion=f'Permiso {permiso.modulo} - {permiso.accion} modificado: {permitido_anterior} → {permitido_nuevo}',
            usuario=request.user,
            empresa=empresa,
            datos_anteriores={'permitido': permitido_anterior},
            datos_nuevos={'permitido': permitido_nuevo},
            request=request,
        )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Permiso actualizado correctamente'
        })
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_actualizar_permiso (administracion_usuarios.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al actualizar permiso: {str(e)}'
        }, status=500)