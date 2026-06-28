"""
PRISLAB V5.0 - MIXINS DE SEGURIDAD BLINDADA
============================================
Fecha: 1 de Febrero de 2026
Objetivo: Segregación estricta por roles a nivel backend

FILOSOFÍA:
"No confíes solo en ocultar botones HTML."
La seguridad debe estar en el backend, no solo en el frontend.

MEJORAS IMPLEMENTADAS:
✅ Mixins de acceso por rol (Médico, Laboratorio, Farmacia, etc.)
✅ Redirección inteligente o 403 Forbidden
✅ Logging de intentos de acceso no autorizados
✅ Mensajes de error personalizados
✅ Compatible con LoginRequiredMixin
✅ Verificación de grupos Y permisos
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
import logging

logger = logging.getLogger('security')


# ==============================================================================
# MIXIN BASE: VERIFICACIÓN DE GRUPO
# ==============================================================================

class GroupRequiredMixin(LoginRequiredMixin):
    """
    Mixin base que verifica si el usuario pertenece a un grupo específico.
    
    Atributos requeridos:
        required_group (str): Nombre del grupo requerido
        
    Atributos opcionales:
        redirect_url (str): URL de redirección si no tiene acceso
        raise_exception (bool): Si True, lanza 403. Si False, redirige.
        permission_denied_message (str): Mensaje personalizado
    """
    required_group = None
    redirect_url = None
    raise_exception = False
    permission_denied_message = "No tienes permiso para acceder a esta área."
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar autenticación primero
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Superuser tiene acceso a todo
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar grupo
        if not self.has_required_group(request.user):
            return self.handle_no_group_permission(request)
        
        return super().dispatch(request, *args, **kwargs)
    
    def has_required_group(self, user):
        """Verifica si el usuario pertenece al grupo requerido."""
        if not self.required_group:
            raise ValueError("required_group no está definido en el Mixin")
        
        return user.groups.filter(name=self.required_group).exists()
    
    def handle_no_group_permission(self, request):
        """Maneja el caso cuando el usuario no tiene el grupo requerido."""
        # Logging de seguridad
        logger.warning(
            f"Acceso denegado: Usuario '{request.user.username}' "
            f"intentó acceder a {request.path} sin el grupo '{self.required_group}'"
        )
        
        if self.raise_exception:
            # Lanzar 403 Forbidden
            raise PermissionDenied(self.permission_denied_message)
        else:
            # Redirigir con mensaje
            messages.error(request, self.permission_denied_message)
            
            if self.redirect_url:
                return redirect(self.redirect_url)
            else:
                # Redirigir al dashboard del usuario
                return redirect(self.get_user_dashboard_url(request.user))
    
    def get_user_dashboard_url(self, user):
        """Obtiene la URL del dashboard apropiado para el usuario."""
        # Importar aquí para evitar imports circulares
        from core.views.general import get_redirect_url_by_role
        return get_redirect_url_by_role(user)


# ==============================================================================
# MIXINS ESPECÍFICOS POR ROL
# ==============================================================================

class MedicoRequiredMixin(GroupRequiredMixin):
    """
    Mixin para vistas que requieren que el usuario sea médico.
    
    Uso:
        class NuevaConsulta(MedicoRequiredMixin, View):
            pass
    """
    required_group = 'MEDICOS'
    permission_denied_message = (
        "Esta área es exclusiva para personal médico. "
        "Si crees que esto es un error, contacta al administrador."
    )
    redirect_url = None  # Redirigir al dashboard del usuario


class LaboratorioRequiredMixin(GroupRequiredMixin):
    """
    Mixin para vistas que requieren que el usuario sea químico/laboratorista.
    
    Uso:
        class CapturarResultados(LaboratorioRequiredMixin, View):
            pass
    """
    required_group = 'LABORATORIO'
    permission_denied_message = (
        "Esta área es exclusiva para personal de laboratorio. "
        "Si crees que esto es un error, contacta al administrador."
    )


class FarmaciaRequiredMixin(GroupRequiredMixin):
    """
    Mixin para vistas que requieren que el usuario sea farmacéutico.
    
    Uso:
        class VentaFarmacia(FarmaciaRequiredMixin, View):
            pass
    """
    required_group = 'FARMACIA'
    permission_denied_message = (
        "Esta área es exclusiva para personal de farmacia. "
        "Si crees que esto es un error, contacta al administrador."
    )


class RecepcionRequiredMixin(GroupRequiredMixin):
    """
    Mixin para vistas que requieren que el usuario sea recepcionista.
    
    Uso:
        class RegistrarPaciente(RecepcionRequiredMixin, View):
            pass
    """
    required_group = 'RECEPCION'
    permission_denied_message = (
        "Esta área es exclusiva para personal de recepción. "
        "Si crees que esto es un error, contacta al administrador."
    )


class EnfermeriaRequiredMixin(GroupRequiredMixin):
    """
    Mixin para vistas que requieren que el usuario sea enfermero/a.
    
    Uso:
        class TomaSignosVitales(EnfermeriaRequiredMixin, View):
            pass
    """
    required_group = 'ENFERMERIA'
    permission_denied_message = (
        "Esta área es exclusiva para personal de enfermería. "
        "Si crees que esto es un error, contacta al administrador."
    )


class GerenciaRequiredMixin(GroupRequiredMixin):
    """
    Mixin para vistas que requieren que el usuario sea gerente/director.
    
    Uso:
        class ReportesFinancieros(GerenciaRequiredMixin, View):
            pass
    """
    required_group = 'GERENCIA'
    permission_denied_message = (
        "Esta área es exclusiva para gerencia. "
        "Si crees que esto es un error, contacta al administrador."
    )


# ==============================================================================
# MIXINS MULTI-ROL (OR LOGIC)
# ==============================================================================

class MultiGroupRequiredMixin(LoginRequiredMixin):
    """
    Mixin que permite acceso si el usuario pertenece a CUALQUIERA de los grupos.
    
    Atributos requeridos:
        required_groups (list): Lista de nombres de grupos permitidos
        
    Uso:
        class VerPacientes(MultiGroupRequiredMixin, View):
            required_groups = ['MEDICOS', 'ENFERMERIA', 'RECEPCION']
    """
    required_groups = []
    permission_denied_message = "No tienes permiso para acceder a esta área."
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Superuser tiene acceso
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar si pertenece a alguno de los grupos
        if not self.has_any_required_group(request.user):
            logger.warning(
                f"Acceso denegado: Usuario '{request.user.username}' "
                f"intentó acceder a {request.path} sin los grupos {self.required_groups}"
            )
            messages.error(request, self.permission_denied_message)
            return redirect('dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def has_any_required_group(self, user):
        """Verifica si el usuario pertenece a alguno de los grupos."""
        if not self.required_groups:
            raise ValueError("required_groups no está definido en el Mixin")
        
        return user.groups.filter(name__in=self.required_groups).exists()


# ==============================================================================
# MIXINS AVANZADOS (PERMISOS + GRUPOS)
# ==============================================================================

class MedicoConPermisosEspecialesMixin(MedicoRequiredMixin):
    """
    Mixin que requiere ser médico Y tener permisos específicos.
    
    Atributos requeridos:
        required_permissions (list): Lista de permisos necesarios
        
    Uso:
        class PrescribirControlados(MedicoConPermisosEspecialesMixin, View):
            required_permissions = ['consultorio.prescribir_controlados']
    """
    required_permissions = []
    
    def dispatch(self, request, *args, **kwargs):
        # Primero verificar que sea médico
        response = super().dispatch(request, *args, **kwargs)
        
        # Si no pasó la verificación de médico, retornar respuesta
        if response.status_code != 200:
            return response
        
        # Verificar permisos adicionales
        if not self.has_required_permissions(request.user):
            logger.warning(
                f"Acceso denegado: Usuario '{request.user.username}' "
                f"no tiene los permisos {self.required_permissions}"
            )
            messages.error(
                request,
                "No tienes los permisos necesarios para realizar esta acción."
            )
            return redirect('medico')
        
        return response
    
    def has_required_permissions(self, user):
        """Verifica si el usuario tiene todos los permisos requeridos."""
        if not self.required_permissions:
            return True
        
        return all(user.has_perm(perm) for perm in self.required_permissions)


# ==============================================================================
# MIXIN DE EMPRESA (MULTI-TENANT)
# ==============================================================================

class EmpresaRequiredMixin(LoginRequiredMixin):
    """
    Mixin que verifica que el usuario tenga una empresa asignada.
    
    Útil para sistemas multi-tenant.
    
    Uso:
        class ConfiguracionEmpresa(EmpresaRequiredMixin, View):
            pass
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Verificar que tenga empresa
        if not hasattr(request.user, 'empresa') or not request.user.empresa:
            messages.error(
                request,
                "Tu cuenta no está asociada a ninguna empresa. Contacta al administrador."
            )
            logger.error(
                f"Usuario '{request.user.username}' sin empresa intentó acceder a {request.path}"
            )
            return redirect('dashboard')
        
        return super().dispatch(request, *args, **kwargs)


# ==============================================================================
# MIXIN DE MÓDULO ACTIVO (FEATURE TOGGLE)
# ==============================================================================

class ModuloActivoMixin(LoginRequiredMixin):
    """
    Mixin que verifica que un módulo específico esté activo para la empresa.
    
    Atributos requeridos:
        required_module (str): Nombre del atributo del módulo en ConfiguracionModulos
        
    Uso:
        class CrearCampana(ModuloActivoMixin, View):
            required_module = 'modulo_marketing'
    """
    required_module = None
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Verificar módulo activo
        if not self.is_module_active(request.user):
            messages.warning(
                request,
                f"El módulo solicitado no está activo para tu empresa. "
                f"Contacta a ventas para activarlo."
            )
            logger.info(
                f"Usuario '{request.user.username}' intentó acceder a módulo "
                f"'{self.required_module}' que está desactivado"
            )
            return redirect('dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def is_module_active(self, user):
        """Verifica si el módulo está activo."""
        if not self.required_module:
            raise ValueError("required_module no está definido en el Mixin")
        
        if not hasattr(user, 'empresa') or not user.empresa:
            return False
        
        config = user.empresa.configuracion_modulos
        return getattr(config, self.required_module, False)


# ==============================================================================
# DECORADOR DE FUNCIÓN (ALTERNATIVA A MIXINS)
# ==============================================================================

from functools import wraps

def grupo_requerido(*grupos):
    """
    Decorador para vistas basadas en funciones.
    
    Uso:
        @grupo_requerido('MEDICOS')
        def nueva_consulta(request):
            pass
        
        @grupo_requerido('MEDICOS', 'ENFERMERIA')
        def ver_paciente(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Superuser tiene acceso
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Verificar grupos
            if not request.user.groups.filter(name__in=grupos).exists():
                logger.warning(
                    f"Acceso denegado: Usuario '{request.user.username}' "
                    f"intentó acceder a {request.path} sin los grupos {grupos}"
                )
                messages.error(
                    request,
                    "No tienes permiso para acceder a esta área."
                )
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# ==============================================================================
# EJEMPLOS DE USO
# ==============================================================================

"""
EJEMPLO 1: Vista de Consulta (Solo Médicos)
────────────────────────────────────────────

from core.mixins import MedicoRequiredMixin
from django.views.generic import CreateView

class NuevaConsulta(MedicoRequiredMixin, CreateView):
    model = Consulta
    template_name = 'consultorio/nueva_consulta.html'
    fields = ['paciente', 'motivo', 'diagnostico']
    
    # Si un químico intenta acceder, será redirigido a su dashboard


EJEMPLO 2: Vista de Laboratorio (Solo Laboratoristas)
──────────────────────────────────────────────────────

from core.mixins import LaboratorioRequiredMixin
from django.views.generic import UpdateView

class CapturarResultados(LaboratorioRequiredMixin, UpdateView):
    model = OrdenDeServicio
    template_name = 'laboratorio/capturar_resultados.html'
    
    # Si un médico intenta acceder, será redirigido


EJEMPLO 3: Vista Multi-Rol (Médicos O Enfermería)
──────────────────────────────────────────────────

from core.mixins import MultiGroupRequiredMixin
from django.views.generic import DetailView

class VerExpediente(MultiGroupRequiredMixin, DetailView):
    model = Paciente
    required_groups = ['MEDICOS', 'ENFERMERIA', 'RECEPCION']
    template_name = 'pacientes/expediente.html'
    
    # Cualquiera de estos 3 grupos puede acceder


EJEMPLO 4: Vista con Permisos Especiales
─────────────────────────────────────────

from core.mixins import MedicoConPermisosEspecialesMixin
from django.views.generic import CreateView

class PrescribirControlados(MedicoConPermisosEspecialesMixin, CreateView):
    model = Receta
    required_permissions = ['consultorio.prescribir_controlados']
    
    # Solo médicos con permiso especial


EJEMPLO 5: Vista de Función con Decorador
──────────────────────────────────────────

from core.mixins import grupo_requerido

@grupo_requerido('MEDICOS')
def nueva_consulta(request):
    # Lógica de la vista
    return render(request, 'nueva_consulta.html')


EJEMPLO 6: Combinar Mixins
───────────────────────────

from core.mixins import MedicoRequiredMixin, EmpresaRequiredMixin, ModuloActivoMixin

class CrearConsultaConIA(MedicoRequiredMixin, EmpresaRequiredMixin, ModuloActivoMixin, CreateView):
    required_module = 'modulo_ia'
    
    # Requiere: Ser médico + Tener empresa + Módulo IA activo
"""
