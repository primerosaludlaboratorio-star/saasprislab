"""
Vistas de certificados médicos: generar y ver.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db import transaction
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.contrib import messages

from core.models import CertificadoMedico, ConsultaMedica, Paciente, CitaMedica
from core.services.audit_service import registrar_auditoria
from core.utils.empresa_request import empresa_efectiva_request

from ._helpers import _int_or_none, _resolver_medico_usuario

logger = logging.getLogger('consultorio')


# ==============================================================================
# CERTIFICADOS MÉDICOS
# ==============================================================================

@login_required
def generar_certificado(request):
    """
    Formulario para generar un certificado médico.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    
    # Pre-cargar paciente y consulta si vienen por GET
    paciente_id = request.GET.get('paciente_id')
    consulta_id = request.GET.get('consulta_id')
    
    paciente = None
    consulta = None
    cita = None
    
    if paciente_id:
        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    if consulta_id:
        consulta = get_object_or_404(ConsultaMedica, id=consulta_id, empresa=empresa)
        if not paciente:
            paciente = consulta.paciente
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Obtener paciente
                paciente_id_post = request.POST.get('paciente_id')
                if paciente_id_post:
                    paciente = get_object_or_404(Paciente, id=paciente_id_post, empresa=empresa)
                
                if not paciente:
                    messages.error(request, 'Debe seleccionar un paciente')
                    return redirect('consultorio:generar_certificado')
                
                # Obtener consulta (opcional)
                consulta_id_post = request.POST.get('consulta_id')
                if consulta_id_post:
                    consulta = ConsultaMedica.objects.filter(
                        id=consulta_id_post, empresa=empresa
                    ).first()
                
                # Tipo de certificado
                tipo_map = {
                    'MEDICO': 'SALUD',
                    'INCAPACIDAD': 'INCAPACIDAD',
                    'APTITUD': 'APTITUD',
                    'DEFUNCION': 'DEFUNCION',
                    'NACIMIENTO': 'NACIMIENTO',
                }
                tipo_form = request.POST.get('tipo_certificado', 'MEDICO')
                tipo = tipo_map.get(tipo_form, 'OTRO')
                
                # Generar folio
                import uuid
                folio = f"CERT-{timezone.now().year}-{uuid.uuid4().hex[:8].upper()}"
                
                # Fechas
                fecha_inicio_str = request.POST.get('fecha_inicio', '')
                fecha_fin_str = request.POST.get('fecha_fin', '')
                from datetime import datetime
                try:
                    fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date() if fecha_inicio_str else timezone.localdate()
                except ValueError:
                    fecha_inicio = timezone.localdate()
                try:
                    fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date() if fecha_fin_str else fecha_inicio
                except ValueError:
                    fecha_fin = fecha_inicio
                
                # Días de incapacidad
                dias_inc = _int_or_none(request.POST.get('dias_incapacidad')) or 0
                
                # Obtener médico
                medico = _resolver_medico_usuario(request, empresa, autocrear=True)
                
                certificado = CertificadoMedico.objects.create(
                    empresa=empresa,
                    paciente=paciente,
                    medico=medico,
                    consulta=consulta,
                    cita=cita,
                    folio_certificado=folio,
                    tipo_certificado=tipo,
                    diagnostico=request.POST.get('diagnostico', '')[:500],
                    descripcion=request.POST.get('descripcion', ''),
                    recomendaciones=request.POST.get('recomendaciones', ''),
                    dias_incapacidad=dias_inc or None,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                )
                
                registrar_auditoria(
                    accion='CREATE',
                    modelo='CertificadoMedico',
                    objeto_id=str(certificado.id),
                    datos_nuevos={
                        'folio': certificado.folio_certificado,
                        'tipo': tipo,
                        'paciente_id': paciente.id,
                    },
                    request=request,
                )
                
                messages.success(request, f'Certificado {folio} generado correctamente')
                return redirect('consultorio:ver_certificado', certificado_id=certificado.id)
                
        except (DatabaseError, ValidationError) as e:
            messages.error(request, f'Error al generar certificado: {str(e)}')
    
    # GET: Mostrar formulario
    pacientes = Paciente.objects.filter(empresa=empresa, activo=True).order_by('nombres', 'apellido_paterno')
    
    return render(request, 'consultorio/generar_certificado.html', {
        'pacientes': pacientes,
        'paciente_preseleccionado': paciente,
        'consulta_preseleccionada': consulta,
    })


@login_required
def ver_certificado(request, certificado_id):
    """Vista de detalle / impresión de un certificado médico."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    
    certificado = get_object_or_404(
        CertificadoMedico.objects.select_related('paciente', 'medico', 'consulta'),
        id=certificado_id,
        empresa=empresa
    )
    
    return render(request, 'consultorio/ver_certificado.html', {
        'certificado': certificado,
        'paciente': certificado.paciente,
        'empresa': empresa,
    })
