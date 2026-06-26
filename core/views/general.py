"""
Módulo de Vistas Generales.
Incluye: Dashboard médico, funciones auxiliares compartidas.
"""
import json
import logging
import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.views import LoginView
from django.http import HttpResponse, JsonResponse
from django.db import DatabaseError, OperationalError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse

from core.decorators import rate_limit, require_api_token
from core.models import Empresa, Usuario

# Logger específico para errores del frontend
logger_frontend = logging.getLogger('prislab.frontend')
logger_core = logging.getLogger('core')


def home_view(request):
    """
    Vista de inicio que redirecciona según el estado de autenticación.
    Previene bucles de redirección infinitos.
    """
    if request.user.is_authenticated:
        try:
            return redirect(get_redirect_url_by_role(request.user))
        except (DatabaseError, OperationalError) as exc:
            logger_core.warning(
                "home_view: DB/OperationalError al resolver redireccion de entrada: %s",
                exc,
                exc_info=True,
            )
            from django.contrib import messages
            messages.warning(
                request,
                "El sistema está resolviendo una sobrecarga temporal. Vuelve a iniciar sesión."
            )
            return redirect('login')
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en home_view (general.py)")
            logger_core.error(
                "home_view: error inesperado al resolver redireccion de entrada: %s",
                exc,
                exc_info=True,
            )
            from django.contrib import messages
            messages.warning(
                request,
                "No se pudo resolver tu sesión actual. Vuelve a iniciar sesión."
            )
            return redirect('login')
    else:
        return redirect('login')


@login_required
def dashboard_medico(request):
    """Dashboard médico (consultorio) - Escritorio digital del doctor."""
    from consultorio.models import ConsultaMedica
    from core.models import OrdenDeServicio, PreOrdenLaboratorio
    from django.utils import timezone
    from datetime import timedelta
    
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    # Obtener consultas recientes del médico (últimas 10)
    consultas_recientes = ConsultaMedica.objects.filter(
        empresa=empresa,
        medico=request.user
    ).select_related('paciente').order_by('-fecha_creacion')[:10]
    
    # Obtener recetas recientes del médico (últimas 10)
    from core.models import Receta
    recetas_recientes = Receta.objects.filter(
        empresa=empresa,
        medico_nombre_completo__icontains=request.user.get_full_name() or request.user.username
    ).select_related('paciente').order_by('-fecha_emision')[:10]
    
    # Obtener pre-órdenes que el médico generó y que ya fueron cobradas/terminadas
    preordenes_del_medico = PreOrdenLaboratorio.objects.filter(
        empresa=empresa,
        medico_solicitante=request.user,
        estado='COBRADA'
    ).select_related('paciente', 'orden_vinculada')[:5]
    
    # Obtener resultados disponibles (órdenes terminadas de pre-órdenes del médico)
    resultados_disponibles = []
    for preorden in preordenes_del_medico:
        if preorden.orden_vinculada:
            orden = preorden.orden_vinculada
            if orden.estado in ['RESULTADOS_LISTOS', 'ENTREGADO']:
                from core.lims_cart import detalle_orden_etiqueta
                estudios = ", ".join(
                    [detalle_orden_etiqueta(d) for d in orden.detalles.select_related(
                        'analito', 'perfil_lims', 'paquete_lims'
                    ).all()[:3]]
                )
                resultados_disponibles.append({
                    'orden_id': orden.id,
                    'paciente_nombre': preorden.paciente.nombre_completo,
                    'estudios': estudios,
                    'fecha': timezone.localtime(orden.fecha_creacion).strftime('%d/%m/%Y')
                })
    
    return render(request, 'core/dashboard_medico.html', {
        'consultas_recientes': consultas_recientes,
        'recetas_recientes': recetas_recientes,
        'resultados_disponibles': resultados_disponibles[:5],  # Máximo 5 notificaciones
    })

def crear_admin_rescate(request):
    """
    DESHABILITADO (BLINDAJE R104) - Riesgo de seguridad critico.
    Solo disponible en desarrollo local.
    """
    from django.conf import settings as _s
    if not _s.DEBUG:
        return HttpResponse("BLOQUEADO: Esta funcion esta deshabilitada en produccion.", status=403)

    username = os.environ.get('DEV_ADMIN_USER', 'admin')
    email = os.environ.get('DEV_ADMIN_EMAIL', 'admin@prislab.com')
    password = os.environ.get('DEV_ADMIN_PASSWORD', 'admin123')
    try:
        usuario = Usuario.objects.get(username=username)
        usuario.set_password(password)
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.is_active = True
        if not usuario.email:
            usuario.email = email
        usuario.save()
        mensaje = f"LISTO: Usuario '{username}' restaurado (SOLO DESARROLLO)"
    except Usuario.DoesNotExist:
        usuario = Usuario.objects.create_superuser(
            username=username, email=email, password=password
        )
        mensaje = f"LISTO: Usuario '{username}' creado (SOLO DESARROLLO)"
    return HttpResponse(mensaje)


def ingreso_magico(request):
    """
    DESHABILITADO (BLINDAJE R104) - Bypass de autenticacion eliminado.
    Solo disponible en desarrollo local.
    """
    from django.conf import settings as _s
    if not _s.DEBUG:
        return HttpResponse("BLOQUEADO: Ingreso magico deshabilitado en produccion.", status=403)

    password = os.environ.get('DEV_ADMIN_PASSWORD', 'admin123')
    if not password:
        return HttpResponse("BLOQUEADO: Configure DEV_ADMIN_PASSWORD en desarrollo.", status=403)
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=os.environ.get('DEV_ADMIN_USER', 'admin'),
        defaults={
            'email': os.environ.get('DEV_ADMIN_EMAIL', 'admin@prislab.com'),
            'is_staff': True,
            'is_superuser': True,
            'is_active': True
        }
    )
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.save()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('/')

# Nota: Funciones de búsqueda de pacientes movidas a core/views/pacientes.py

# ==============================================================================
# SISTEMA DE AUDITORÍA: Captura de Errores del Frontend
# ==============================================================================
@csrf_exempt
@require_http_methods(["POST"])
@rate_limit('frontend_log', limit=120, window_seconds=60)
@require_api_token('PRISLAB_FRONTEND_LOG_TOKEN')
def log_frontend_error(request):
    """
    Vista para recibir errores del frontend (JavaScript) y registrarlos en el log.
    Silenciosa: Si falla, no debe detener la operación principal.
    """
    try:
        # Intentar parsear el JSON
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        
        # Extraer información del error
        error_message = data.get('message', 'Error desconocido')
        error_source = data.get('source', 'Desconocido')
        error_line = data.get('line', 'N/A')
        error_col = data.get('col', 'N/A')
        error_stack = data.get('stack', 'N/A')
        error_url = data.get('url', request.build_absolute_uri())
        user_agent = request.META.get('HTTP_USER_AGENT', 'N/A')
        
        # Información del usuario (si está autenticado)
        user_info = 'Anónimo'
        if request.user.is_authenticated:
            user_info = f"{request.user.username} (ID: {request.user.id})"
        
        # Construir mensaje de log detallado
        log_message = (
            f"ERROR FRONTEND - Usuario: {user_info} | "
            f"URL: {error_url} | "
            f"Origen: {error_source}:{error_line}:{error_col} | "
            f"Mensaje: {error_message} | "
            f"Stack: {error_stack[:500]} | "  # Limitar stack a 500 caracteres
            f"User-Agent: {user_agent[:200]}"
        )
        
        # Registrar en el log (SILENCIOSO: Si falla, no debe afectar la respuesta)
        try:
            logger_frontend.error(log_message)
        except Exception as log_error:
            logging.getLogger(__name__).exception("Error inesperado en log_frontend_error (general.py)")
            logging.getLogger('prislab.frontend').error(
                'Fallback tras fallo de logger_frontend.error: %s',
                log_error,
                exc_info=True,
            )
        
        return JsonResponse({'status': 'success', 'mensaje': 'Error registrado'})
    
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en log_frontend_error (general.py)")
        # Si TODO falla, devolver respuesta exitosa para no bloquear el frontend
        try:
            logger_frontend.error(f"Error al procesar log_frontend_error: {str(e)}")
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en log_frontend_error (general.py)")
            pass  # Silencioso incluso en el fallback
        return JsonResponse({'status': 'error', 'mensaje': 'Error al procesar'}, status=500)


def get_redirect_url_by_role(user):
    """
    Redirección inteligente según el rol del usuario y grupos de Django.
    
    MEJORAS BLOQUE 3:
    - Considera tanto el campo 'rol' como los grupos de Django
    - Prioriza grupos sobre roles para mayor flexibilidad
    - Fallback robusto en caso de error
    
    Orden de prioridad:
    1. Grupos de Django (MEDICOS, LABORATORIO, FARMACIA, etc.)
    2. Campo 'rol' del modelo Usuario
    3. Superusuario -> Dashboard general
    4. Fallback -> /home/
    """
    try:
        # ==============================================================================
        # 1. VERIFICAR GRUPOS DE DJANGO (PRIORIDAD)
        # ==============================================================================
        
        # GERENCIA_OPERATIVA -> Dashboard General (Nancy, Gabriela)
        # DEBE ir primero: tienen acceso a TODAS las areas pero su
        # dashboard de inicio es el principal, no el de un area especifica
        if user.groups.filter(name='GERENCIA_OPERATIVA').exists():
            return reverse('dashboard')
        
        # Medicos -> Dashboard de Consultorio
        if user.groups.filter(name='MEDICOS').exists():
            return reverse('medico')
        
        # Laboratorio (Quimicos) -> Lista de Trabajo
        if user.groups.filter(name='LABORATORIO').exists():
            return reverse('lista_trabajo_lab')
        
        # Farmacia -> Punto de Venta
        if user.groups.filter(name='FARMACIA').exists():
            return reverse('pdv_farmacia')
        
        # Recepcion -> Dashboard del modulo de recepcion (PWA unificado)
        if user.groups.filter(name='RECEPCION').exists():
            return reverse('recepcion:dashboard_recepcion')
        
        # Enfermeria -> Recepcion
        if user.groups.filter(name='ENFERMERIA').exists():
            return reverse('recepcion_lab')
        
        # Gerencia -> Dashboard General
        if user.groups.filter(name='GERENCIA').exists():
            return reverse('dashboard')
        
        # ==============================================================================
        # 2. VERIFICAR CAMPO 'ROL' (FALLBACK)
        # ==============================================================================
        rol = getattr(user, 'rol', None)
        
        if rol:
            # Normalizar a mayúsculas para evitar problemas de case
            rol_upper = rol.upper().strip()
            # Mapeo de roles a dashboards (incluye variantes usadas en BD)
            role_redirects = {
                'ADMIN': reverse('dashboard'),
                'ADMINISTRADOR': reverse('dashboard'),   # variante: jonathan
                'MEDICO': reverse('medico'),
                'DOCTOR': reverse('medico'),             # alias común
                'DIRECTOR': reverse('dashboard_director'),
                'QUIMICO': reverse('lista_trabajo_lab'),
                'LABORATORIO': reverse('lista_trabajo_lab'),  # variante: gabriela
                'RECEPCION': reverse('recepcion:dashboard_recepcion'),
                'CAJERO': reverse('pdv_farmacia'),
                'FARMACIA': reverse('pdv_farmacia'),     # variante: nancy
                'GERENTE': reverse('dashboard'),
                'ENFERMERIA': reverse('recepcion_lab'),
            }
            
            if rol_upper in role_redirects:
                return role_redirects[rol_upper]
        
        # ==============================================================================
        # 3. SUPERUSUARIO o STAFF
        # ==============================================================================
        if user.is_superuser or user.is_staff:
            return reverse('dashboard')
        
        # ==============================================================================
        # 4. FALLBACK SEGURO (evitar loop /home/ -> /home/)
        # ==============================================================================
        # Redirigir a un dashboard real, NO a /home/
        return reverse('dashboard')
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en get_redirect_url_by_role (general.py)")
        logger_core.error(f"Error en get_redirect_url_by_role: {str(e)}")
        # Fallback seguro: dashboard siempre existe
        return reverse('dashboard') if user.is_authenticated else '/login/'


class CustomLoginView(LoginView):
    """
    Vista de login personalizada con redirección inteligente.
    """
    template_name = 'core/login.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                return redirect(get_redirect_url_by_role(request.user))
            except (DatabaseError, OperationalError) as exc:
                logger_core.warning(
                    "CustomLoginView.dispatch: DB/OperationalError al resolver redireccion: %s",
                    exc,
                    exc_info=True,
                )
                from django.contrib import messages
                messages.warning(
                    request,
                    "Tu sesión anterior encontró una sobrecarga temporal. Inicia sesión nuevamente."
                )
                return redirect('login')
            except Exception as exc:
                logging.getLogger(__name__).exception("Error inesperado en dispatch (general.py)")
                logger_core.error(
                    "CustomLoginView.dispatch: error inesperado al resolver redireccion: %s",
                    exc,
                    exc_info=True,
                )
                from django.contrib import messages
                messages.warning(
                    request,
                    "No se pudo resolver tu sesión actual. Inicia sesión nuevamente."
                )
                return redirect('login')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        usuario = form.get_user()

        # ── 2FA: Si el usuario tiene 2FA activo, NO hacer login todavía ───────
        from core.views.autenticacion_2fa import (
            _2fa_activo_para_usuario, _2fa_obligatorio_por_rol, _ip_exenta_2fa
        )
        requiere_2fa = _2fa_activo_para_usuario(usuario) or _2fa_obligatorio_por_rol(usuario)
        if requiere_2fa and not _ip_exenta_2fa(self.request):
            self.request.session['_2fa_user_id'] = usuario.pk
            self.request.session['_2fa_intentos'] = 0
            backend = getattr(usuario, 'backend', 'django.contrib.auth.backends.ModelBackend')
            self.request.session['_2fa_backend'] = backend
            return redirect('verificar_2fa')

        response = super().form_valid(form)

        # Auditoría de login exitoso
        try:
            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='CREATE',
                modelo='SesionUsuario',
                objeto_id=str(self.request.user.id),
                datos_nuevos={
                    'evento': 'LOGIN',
                    'username': self.request.user.username,
                    'rol': getattr(self.request.user, 'rol', ''),
                    '2fa': False,
                },
                request=self.request,
            )
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en form_valid (general.py)")
            pass
        return response

    def form_invalid(self, form):
        """Registra intentos fallidos de login para auditoría y War Room."""
        username_intentado = self.request.POST.get('username', '')
        # REMOTE_ADDR: IP real vista por Nginx, no falsificable — alimenta War Room.
        ip = self.request.META.get('REMOTE_ADDR', '0.0.0.0')
        try:
            from seguridad.models import LogAccionSensible
            LogAccionSensible.objects.create(
                accion=LogAccionSensible.ACCION_LOGIN_FALLIDO,
                descripcion=f'Intento fallido de login para usuario: {username_intentado}',
                ip_address=ip,
            )
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en form_invalid (general.py)")
            pass
        return super().form_invalid(form)

    def get_success_url(self):
        user = self.request.user
        return get_redirect_url_by_role(user)


@login_required
def logout_view(request):
    """
    Vista de logout personalizada con auditoría.
    """
    try:
        from core.services.audit_service import registrar_auditoria
        registrar_auditoria(
            accion='DELETE',
            modelo='SesionUsuario',
            objeto_id=str(request.user.id),
            datos_nuevos={
                'evento': 'LOGOUT',
                'username': request.user.username,
            },
            request=request,
        )
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en logout_view (general.py)")
        pass
    logout(request)
    response = redirect('login')
    response['Cache-Control'] = 'no-store, private, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def service_worker_view(request):
    """Serve sw.js from root path so the ServiceWorker scope covers the entire site."""
    import os
    from django.conf import settings
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = 'self.addEventListener("fetch", function(e){});'
    response = HttpResponse(content, content_type='application/javascript')
    response['Cache-Control'] = 'no-store, private, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


# ── Páginas de error elegantes (handler404 / handler500 / handler403) ────────

def error_404(request, exception=None):
    """Página 404 — Recurso no encontrado."""
    return render(request, 'errors/404.html', status=404)


def error_500(request):
    """Página 500 — Error interno del servidor."""
    return render(request, 'errors/500.html', status=500)


def error_403(request, exception=None):
    """Página 403 — Acceso denegado."""
    return render(request, 'errors/403.html', status=403)