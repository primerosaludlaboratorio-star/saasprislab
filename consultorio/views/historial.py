"""
Vistas de historial: historial clínico del paciente, dashboard del consultorio,
detalle de consulta.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.contrib import messages

from core.models import (
    Paciente, CitaMedica, ConsultaMedica, SignosVitales,
    HistoriaClinica, CertificadoMedico,
)
from core.utils.empresa_request import empresa_efectiva_request

logger = logging.getLogger('consultorio')


# ==============================================================================
# HISTORIAL Y REPORTES
# ==============================================================================

@login_required
def historial_clinico_paciente(request, paciente_id):
    """
    Vista completa del historial clínico de un paciente.
    Muestra todas sus consultas, signos vitales, recetas y certificados.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    
    # Historial de consultas médicas
    consultas = ConsultaMedica.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).select_related('medico', 'cita').order_by('-fecha_consulta')
    
    # Historial de signos vitales (últimos 20)
    signos_vitales = SignosVitales.objects.filter(
        paciente=paciente
    ).order_by('-fecha_registro')[:20]
    
    # Certificados médicos
    certificados = CertificadoMedico.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).order_by('-fecha_certificado')
    
    # Historia clínica
    try:
        historia_clinica = paciente.historia_clinica
    except HistoriaClinica.DoesNotExist:
        historia_clinica = None
    
    return render(request, 'consultorio/historial_clinico_paciente.html', {
        'paciente': paciente,
        'consultas': consultas,
        'signos_vitales': signos_vitales,
        'certificados': certificados,
        'historia_clinica': historia_clinica,
    })


@login_required
def dashboard_consultorio(request):
    """
    Dashboard principal del consultorio.
    Muestra resumen del día, estadísticas recientes y accesos rápidos.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    
    hoy = timezone.localdate()
    
    # Citas de hoy
    citas_hoy = CitaMedica.objects.filter(
        empresa=empresa,
        fecha_cita=hoy
    )
    
    # Estadísticas del día
    stats_dia = {
        'total_citas': citas_hoy.count(),
        'pendientes': citas_hoy.filter(estado='PENDIENTE').count(),
        'en_sala': citas_hoy.filter(estado='EN_SALA').count(),
        'en_curso': citas_hoy.filter(estado='EN_CURSO').count(),
        'completadas': citas_hoy.filter(estado='COMPLETADA').count(),
        'canceladas': citas_hoy.filter(estado='CANCELADA').count(),
    }
    
    # Consultas de esta semana
    inicio_semana = hoy - timezone.timedelta(days=hoy.weekday())
    consultas_semana = ConsultaMedica.objects.filter(
        empresa=empresa,
        fecha_consulta__date__gte=inicio_semana,
        estado='FINALIZADA'
    ).count()
    
    # Últimas 5 consultas finalizadas
    ultimas_consultas = ConsultaMedica.objects.filter(
        empresa=empresa,
        estado='FINALIZADA'
    ).select_related('paciente', 'medico').order_by('-fecha_consulta')[:5]
    
    # Citas próximas de hoy (pendientes)
    citas_proximas = citas_hoy.filter(
        estado='PENDIENTE'
    ).select_related('paciente', 'medico').order_by('hora_cita')[:10]
    
    # Total de pacientes activos
    total_pacientes = Paciente.objects.filter(
        empresa=empresa,
        activo=True
    ).count()
    
    return render(request, 'consultorio/dashboard_consultorio.html', {
        'hoy': hoy,
        'stats_dia': stats_dia,
        'consultas_semana': consultas_semana,
        'ultimas_consultas': ultimas_consultas,
        'citas_proximas': citas_proximas,
        'total_pacientes': total_pacientes,
    })


@login_required
def ver_consulta_detalle(request, consulta_id):
    """
    Vista de detalle de una consulta médica específica.
    Muestra SOAP completo, signos vitales, receta y certificados.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    
    consulta = get_object_or_404(
        ConsultaMedica.objects.select_related(
            'paciente', 'medico', 'cita', 'signos_vitales', 'receta'
        ),
        id=consulta_id,
        empresa=empresa
    )
    
    # Certificados vinculados a esta consulta
    certificados = CertificadoMedico.objects.filter(
        consulta=consulta
    ).order_by('-fecha_certificado')
    
    return render(request, 'consultorio/ver_consulta_detalle.html', {
        'consulta': consulta,
        'paciente': consulta.paciente,
        'certificados': certificados,
    })
