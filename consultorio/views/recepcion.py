"""
Vistas de recepción: tablero, check-in y agendamiento de citas.
"""
from datetime import timedelta
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db import transaction
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from core.models import Paciente, Medico, CitaMedica
from core.services.audit_service import registrar_auditoria
from core.utils.empresa_request import empresa_efectiva_request
from core.utils.sucursal_helpers import get_request_sucursal

from ._helpers import _int_or_none, _resolver_medico_usuario

logger = logging.getLogger('consultorio')


# ==============================================================================
# PASO 1: RECEPCIÓN (AGENDAMIENTO Y CHECK-IN)
# ==============================================================================

@login_required
def tablero_recepcion(request):
    """
    Dashboard de recepción con vista de citas del día.
    Botón Check-In para cambiar estado a EN_SALA.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    hoy = timezone.localdate()
    
    # Filtrar citas del día
    citas = CitaMedica.objects.filter(
        empresa=empresa,
        fecha_cita=hoy
    ).select_related('paciente', 'medico').order_by('hora_cita')
    
    # Estadísticas del día
    stats = {
        'total': citas.count(),
        'pendientes': citas.filter(estado='PENDIENTE').count(),
        'en_sala': citas.filter(estado='EN_SALA').count(),
        'en_curso': citas.filter(estado='EN_CURSO').count(),
        'completadas': citas.filter(estado='COMPLETADA').count(),
    }
    
    return render(request, 'consultorio/tablero_recepcion.html', {
        'hoy': hoy,
        'citas': citas,
        'stats': stats,
    })


@login_required
@require_http_methods(["POST"])
def check_in_cita(request, cita_id):
    """Marca una cita como EN_SALA (Check-In)."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)
    
    cita.estado = 'EN_SALA'
    cita.save(update_fields=['estado'])
    
    messages.success(request, f'Check-In realizado para {cita.paciente.nombre_completo}')
    return redirect('consultorio:tablero_recepcion')


@login_required
def agendar_cita(request):
    """
    Formulario para agendar nueva cita.
    Soporta dos flujos:
    - Desde recepción: se selecciona paciente + médico
    - Desde la agenda del médico: el médico agenda para sí mismo
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    
    if request.method == 'POST':
        try:
            paciente_id = request.POST.get('paciente_id')
            paciente_nombre = request.POST.get('paciente_nombre', '').strip()
            medico_id = request.POST.get('medico_id')
            fecha_cita = request.POST.get('fecha_cita')
            hora_cita_str = request.POST.get('hora_cita', '').strip()
            motivo = request.POST.get('motivo', '')
            duracion = _int_or_none(request.POST.get('duracion') or request.POST.get('duracion_estimada')) or 30
            
            def _rerender_form(error_msg):
                messages.error(request, error_msg)
                pacientes_qs = Paciente.objects.filter(empresa=empresa, activo=True).order_by('nombres', 'apellido_paterno')
                medicos_qs = Medico.objects.filter(empresa=empresa) if empresa else Medico.objects.none()
                hoy_form = timezone.localdate()
                return render(request, 'consultorio/agendar_cita.html', {
                    'pacientes': pacientes_qs,
                    'medicos': medicos_qs,
                    'fecha_min': hoy_form.isoformat(),
                    'fecha_max': (hoy_form + timedelta(days=365)).isoformat(),
                    'form_data': {
                        'paciente_id': paciente_id or '',
                        'paciente_nombre': paciente_nombre or '',
                        'medico_id': medico_id or '',
                        'fecha_cita': fecha_cita or '',
                        'hora_cita': hora_cita_str or '',
                        'motivo': motivo or '',
                        'duracion': duracion,
                    },
                })

            if not paciente_id or not paciente_id.strip():
                return _rerender_form('Debe seleccionar un paciente.')
            if not hora_cita_str:
                return _rerender_form('Debe indicar la hora de la cita.')
            from datetime import datetime as dt_parse
            try:
                hora_cita = dt_parse.strptime(hora_cita_str, '%H:%M').time()
            except ValueError:
                try:
                    hora_cita = dt_parse.strptime(hora_cita_str, '%H:%M:%S').time()
                except ValueError:
                    return _rerender_form('Hora de cita inválida. Use formato HH:MM o HH:MM:SS.')
            
            if not fecha_cita:
                return _rerender_form('Debe indicar la fecha de la cita.')
            try:
                from datetime import datetime as dt_parse
                fecha_cita_parsed = dt_parse.strptime(fecha_cita.strip(), '%Y-%m-%d').date()
            except (ValueError, AttributeError):
                return _rerender_form('Fecha de cita inválida. Use formato AAAA-MM-DD.')
            hoy = timezone.localdate()
            if fecha_cita_parsed < hoy:
                return _rerender_form('No se pueden agendar citas en fechas pasadas.')
            if (fecha_cita_parsed - hoy).days > 365:
                return _rerender_form('La fecha de la cita no puede ser mayor a un año.')
            fecha_cita = fecha_cita_parsed
            
            paciente_pk = _int_or_none(paciente_id)
            if paciente_pk is None:
                return _rerender_form('Paciente inválido.')
            paciente = get_object_or_404(Paciente, id=paciente_pk, empresa=empresa)
            
            # Buscar médico: por ID explícito (filtrado por empresa) o por el usuario actual
            medico_obj = None
            if medico_id:
                medico_pk = _int_or_none(medico_id)
                if medico_pk is not None:
                    medico_obj = Medico.objects.filter(id=medico_pk, empresa=empresa).first()

            medico_obj = _resolver_medico_usuario(
                request,
                empresa,
                medico_preferido=medico_obj,
                autocrear=True,
            )
            
            cita = CitaMedica.objects.create(
                empresa=empresa,
                sucursal=get_request_sucursal(request),
                paciente=paciente,
                medico=medico_obj,
                fecha_cita=fecha_cita,
                hora_cita=hora_cita,
                duracion_estimada=duracion,
                motivo=motivo,
                creado_por=request.user,
            )
            # CICLO 15: Auditoría forense - creación de cita
            registrar_auditoria(
                accion='CREATE',
                modelo='CitaMedica',
                objeto_id=str(cita.id),
                datos_nuevos={
                    'paciente_id': cita.paciente_id,
                    'medico_id': cita.medico_id,
                    'fecha_cita': str(cita.fecha_cita),
                    'hora_cita': str(cita.hora_cita),
                    'motivo': (cita.motivo or '')[:200],
                },
                request=request,
            )
            messages.success(request, f'Cita agendada para {paciente.nombre_completo} el {fecha_cita} a las {hora_cita}')
            
            # Redirigir dependiendo de origen
            referer = request.META.get('HTTP_REFERER', '')
            if 'agenda' in referer:
                return redirect('consultorio:agenda_medico')
            return redirect('consultorio:tablero_recepcion')
            
        except Paciente.DoesNotExist:
            messages.error(request, 'Paciente no encontrado')
        except (DatabaseError, ValidationError) as e:
            messages.error(request, f'Error al agendar cita: {str(e)}')
    
    # GET: Mostrar formulario
    pacientes = Paciente.objects.filter(empresa=empresa, activo=True).order_by('nombres', 'apellido_paterno')
    medicos = Medico.objects.filter(empresa=empresa) if empresa else Medico.objects.none()
    hoy = timezone.localdate()
    
    return render(request, 'consultorio/agendar_cita.html', {
        'pacientes': pacientes,
        'medicos': medicos,
        'fecha_min': hoy.isoformat(),
        'fecha_max': (hoy + timedelta(days=365)).isoformat(),
    })
