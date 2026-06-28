"""
PORTAL DEL PACIENTE - VISTAS
Sistema público para que los pacientes accedan a su información médica
"""
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from datetime import timedelta

logger = logging.getLogger('pacientes.portal')

from core.models import (
    Paciente, ConsultaMedica, OrdenDeServicio, 
    Receta, CertificadoMedico, EstudioImagen
)
from .portal_models import (
    UsuarioPaciente, SolicitudAccesoPortal, AccesoExpedientePortal
)


# ==============================================================================
# AUTENTICACIÓN DEL PACIENTE
# ==============================================================================

def portal_login(request):
    """
    Login público para pacientes.
    """
    if request.user.is_authenticated and hasattr(request.user, 'paciente'):
        return redirect('pacientes:portal_dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            usuario_portal = UsuarioPaciente.objects.get(email=email, is_active=True)
            if usuario_portal.check_password(password):
                # Login manual (no usa Django auth)
                request.session['paciente_portal_id'] = usuario_portal.id
                usuario_portal.ultimo_acceso = timezone.now()
                usuario_portal.save(update_fields=['ultimo_acceso'])
                
                messages.success(request, f'Bienvenido, {usuario_portal.paciente.nombre_completo}')
                return redirect('pacientes:portal_dashboard')
            else:
                messages.error(request, 'Credenciales incorrectas')
        except UsuarioPaciente.DoesNotExist:
            messages.error(request, 'Credenciales incorrectas')
    
    return render(request, 'pacientes/portal/login.html')


def portal_logout(request):
    """Cerrar sesión del portal del paciente"""
    if 'paciente_portal_id' in request.session:
        del request.session['paciente_portal_id']
    messages.success(request, 'Sesión cerrada correctamente')
    return redirect('pacientes:portal_login')


def solicitar_acceso(request):
    """
    Formulario público para que los pacientes soliciten acceso al portal.
    """
    if request.method == 'POST':
        try:
            solicitud = SolicitudAccesoPortal.objects.create(
                nombre_completo=request.POST.get('nombre_completo'),
                email=request.POST.get('email'),
                telefono=request.POST.get('telefono'),
                fecha_nacimiento=request.POST.get('fecha_nacimiento'),
                numero_identificacion=request.POST.get('numero_identificacion'),
                ip_solicitud=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(
                request, 
                'Tu solicitud ha sido enviada. Te contactaremos en las próximas 24 horas.'
            )
            return redirect('pacientes:portal_login')
            
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en solicitar_acceso (portal_views.py)")
            messages.error(request, f'Error al procesar solicitud: {str(e)}')
    
    return render(request, 'pacientes/portal/solicitar_acceso.html')


# ==============================================================================
# DECORADOR PERSONALIZADO PARA PORTAL
# ==============================================================================

def portal_login_required(view_func):
    """Decorador personalizado para vistas del portal del paciente"""
    def wrapper(request, *args, **kwargs):
        paciente_portal_id = request.session.get('paciente_portal_id')
        if not paciente_portal_id:
            messages.warning(request, 'Por favor inicia sesión')
            return redirect('pacientes:portal_login')
        
        try:
            request.usuario_portal = UsuarioPaciente.objects.select_related('paciente').get(
                id=paciente_portal_id,
                is_active=True
            )
            return view_func(request, *args, **kwargs)
        except UsuarioPaciente.DoesNotExist:
            del request.session['paciente_portal_id']
            messages.error(request, 'Sesión inválida')
            return redirect('pacientes:portal_login')
    
    return wrapper


# ==============================================================================
# DASHBOARD DEL PACIENTE
# ==============================================================================

@portal_login_required
def portal_dashboard(request):
    """
    Dashboard principal del paciente con resumen de su información.
    """
    paciente = request.usuario_portal.paciente
    empresa = paciente.empresa
    
    # Registrar acceso
    AccesoExpedientePortal.objects.create(
        usuario_portal=request.usuario_portal,
        seccion_consultada='dashboard',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )
    
    # Última consulta
    ultima_consulta = ConsultaMedica.objects.filter(
        paciente=paciente,
        empresa=empresa,
        estado='FINALIZADA'
    ).order_by('-fecha_consulta').first()
    
    # Próxima cita (si existe un modelo de citas)
    proxima_cita = None
    
    # Resultados pendientes
    estudios_pendientes = OrdenDeServicio.objects.filter(
        paciente=paciente,
        empresa=empresa,
        estado__in=['REGISTRADA', 'EN_PROCESO']
    ).count()
    
    # Recetas activas (últimos 90 días)
    fecha_limite = timezone.now() - timedelta(days=90)
    recetas_activas = Receta.objects.filter(
        paciente=paciente,
        empresa=empresa,
        fecha_emision__gte=fecha_limite
    ).order_by('-fecha_emision')[:5]
    
    # Estadísticas
    stats = {
        'total_consultas': ConsultaMedica.objects.filter(
            paciente=paciente, empresa=empresa, estado='FINALIZADA'
        ).count(),
        'total_estudios': OrdenDeServicio.objects.filter(
            paciente=paciente, empresa=empresa
        ).count(),
        'estudios_pendientes': estudios_pendientes,
        'recetas_activas': recetas_activas.count(),
    }
    
    return render(request, 'pacientes/portal/dashboard.html', {
        'paciente': paciente,
        'usuario_portal': request.usuario_portal,
        'ultima_consulta': ultima_consulta,
        'proxima_cita': proxima_cita,
        'recetas_activas': recetas_activas,
        'stats': stats,
    })


# ==============================================================================
# MIS CONSULTAS
# ==============================================================================

@portal_login_required
def portal_mis_consultas(request):
    """
    Historial de consultas del paciente.
    """
    paciente = request.usuario_portal.paciente
    
    # Registrar acceso
    AccesoExpedientePortal.objects.create(
        usuario_portal=request.usuario_portal,
        seccion_consultada='consultas',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )
    
    consultas = ConsultaMedica.objects.filter(
        paciente=paciente,
        empresa=paciente.empresa,
        estado='FINALIZADA'
    ).select_related('medico', 'signos_vitales').order_by('-fecha_consulta')
    
    return render(request, 'pacientes/portal/mis_consultas.html', {
        'paciente': paciente,
        'consultas': consultas,
    })


# ==============================================================================
# MIS ESTUDIOS DE LABORATORIO
# ==============================================================================

@portal_login_required
def portal_mis_estudios(request):
    """
    Estudios de laboratorio del paciente.
    """
    paciente = request.usuario_portal.paciente
    
    # Registrar acceso
    AccesoExpedientePortal.objects.create(
        usuario_portal=request.usuario_portal,
        seccion_consultada='laboratorio',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )
    
    ordenes = OrdenDeServicio.objects.filter(
        paciente=paciente,
        empresa=paciente.empresa
    ).select_related('creado_por').prefetch_related(
        'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
    ).order_by('-fecha_creacion')[:100]
    
    return render(request, 'pacientes/portal/mis_estudios.html', {
        'paciente': paciente,
        'ordenes': ordenes,
    })


# ==============================================================================
# MIS RECETAS
# ==============================================================================

@portal_login_required
def portal_mis_recetas(request):
    """
    Recetas médicas del paciente.
    """
    paciente = request.usuario_portal.paciente
    
    # Registrar acceso
    AccesoExpedientePortal.objects.create(
        usuario_portal=request.usuario_portal,
        seccion_consultada='recetas',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )
    
    recetas = Receta.objects.filter(
        paciente=paciente,
        empresa=paciente.empresa
    ).select_related('medico').order_by('-fecha_emision')
    
    return render(request, 'pacientes/portal/mis_recetas.html', {
        'paciente': paciente,
        'recetas': recetas,
    })


# ==============================================================================
# DESCARGAR DOCUMENTOS
# ==============================================================================

@portal_login_required
def portal_descargar_resultado(request, orden_id):
    """
    Descargar PDF de resultados de laboratorio (Portal del Paciente).
    """
    paciente = request.usuario_portal.paciente
    orden = get_object_or_404(
        OrdenDeServicio,
        id=orden_id,
        paciente=paciente,
        estado='ENTREGADO'
    )

    # ── CANDADO FINANCIERO ─────────────────────────────────────────────────
    from core.utils.candado_financiero import (
        tiene_saldo_pendiente, calcular_saldo, respuesta_retenida_html
    )
    if tiene_saldo_pendiente(orden):
        logger.warning(
            "CANDADO portal: descarga bloqueada por saldo — orden %s paciente %s",
            orden_id, paciente.id
        )
        return respuesta_retenida_html(calcular_saldo(orden), folio=orden.folio_orden or str(orden_id))
    # ──────────────────────────────────────────────────────────────────────

    # Registrar descarga
    AccesoExpedientePortal.objects.create(
        usuario_portal=request.usuario_portal,
        seccion_consultada=f'descarga_resultado_{orden.folio_orden or orden.id}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    # Generar PDF directamente usando el motor de reportes, sin cruzar la sesión de staff.
    # La vista imprimir_resultados tiene @login_required para personal; los pacientes del
    # portal usan sesión propia (paciente_portal_id) que no satisface ese decorator.
    try:
        from core.services.motor_reportes_lab import generar_reporte_pdf
        from core.utils.candado_financiero import ReportePdfSaldoPendienteError

        pdf_bytes = generar_reporte_pdf(orden)
        folio = orden.folio_orden or f'ORD-{orden.id}'
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Resultados_{folio}.pdf"'
        return response
    except ReportePdfSaldoPendienteError as e:
        return respuesta_retenida_html(
            e.saldo_pendiente, folio=orden.folio_orden or str(orden_id)
        )
    except Exception as exc:
        logger.error(
            'Portal paciente: error generando PDF para orden %s - %s',
            orden.id, exc, exc_info=True
        )
        return HttpResponse(
            'No se pudo generar el PDF de resultados. Por favor contacte al laboratorio.',
            status=500
        )


# ==============================================================================
# MI PERFIL
# ==============================================================================

@portal_login_required
def portal_mi_perfil(request):
    """
    Perfil del paciente con información personal.
    """
    paciente = request.usuario_portal.paciente
    usuario_portal = request.usuario_portal
    
    if request.method == 'POST':
        # Actualizar configuración
        usuario_portal.notificaciones_email = request.POST.get('notificaciones_email') == 'on'
        usuario_portal.notificaciones_sms = request.POST.get('notificaciones_sms') == 'on'
        usuario_portal.save()
        
        messages.success(request, 'Configuración actualizada')
        return redirect('pacientes:portal_mi_perfil')
    
    return render(request, 'pacientes/portal/mi_perfil.html', {
        'paciente': paciente,
        'usuario_portal': usuario_portal,
    })


# ==============================================================================
# CAMBIAR CONTRASEÑA
# ==============================================================================

@portal_login_required
def portal_cambiar_password(request):
    """
    Cambiar contraseña del portal.
    """
    if request.method == 'POST':
        password_actual = request.POST.get('password_actual')
        password_nueva = request.POST.get('password_nueva')
        password_confirmacion = request.POST.get('password_confirmacion')
        
        usuario_portal = request.usuario_portal
        
        if not usuario_portal.check_password(password_actual):
            messages.error(request, 'Contraseña actual incorrecta')
        elif password_nueva != password_confirmacion:
            messages.error(request, 'Las contraseñas nuevas no coinciden')
        elif len(password_nueva) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres')
        else:
            usuario_portal.set_password(password_nueva)
            usuario_portal.save()
            messages.success(request, 'Contraseña actualizada correctamente')
            return redirect('pacientes:portal_mi_perfil')
    
    return render(request, 'pacientes/portal/cambiar_password.html', {
        'paciente': request.usuario_portal.paciente,
    })