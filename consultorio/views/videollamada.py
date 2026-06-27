"""
Vistas de videollamada / telemedicina.
"""
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import CitaMedica, Paciente
from core.utils.empresa_request import empresa_efectiva_request

from ._helpers import _empresa_explicita_usuario, _resolver_medico_usuario

logger = logging.getLogger('consultorio')


# ==============================================================================
# VIDEOLLAMADA SEGURA (TELEMEDICINA)
# ==============================================================================

@login_required
def videollamada_segura(request):
    """
    Vista de telemedicina con videollamada segura.
    Muestra sala virtual, consultas del día y notas.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.localdate()
    medico_actual = _resolver_medico_usuario(request, empresa)

    citas_qs = CitaMedica.objects.filter(
        empresa=empresa,
        fecha_cita=hoy,
    ).select_related('paciente', 'medico').order_by('hora_cita')
    if medico_actual:
        citas_qs = citas_qs.filter(medico=medico_actual)

    virtual_q = (
        Q(motivo__icontains='virtual') |
        Q(motivo__icontains='tele') |
        Q(motivo__icontains='video') |
        Q(notas_paciente__icontains='virtual') |
        Q(notas_paciente__icontains='video') |
        Q(notas_recepcion__icontains='virtual') |
        Q(notas_recepcion__icontains='video')
    )
    candidatas = citas_qs.filter(virtual_q)
    if not candidatas.exists():
        candidatas = citas_qs.filter(estado__in=['PENDIENTE', 'CONFIRMADA', 'EN_SALA', 'EN_CURSO'])

    estado_css = {
        'PENDIENTE': 'secondary',
        'CONFIRMADA': 'primary',
        'EN_SALA': 'info',
        'EN_CURSO': 'warning',
        'COMPLETADA': 'success',
        'CANCELADA': 'danger',
        'NO_ASISTIO': 'dark',
    }
    sala_path = reverse('consultorio:videollamada_segura')
    consultas_virtuales = []
    for cita in candidatas[:20]:
        token = signing.dumps(
            {
                'empresa': empresa.id,
                'cita': cita.id,
                'paciente': cita.paciente_id,
                'medico': cita.medico_id,
            },
            salt='consultorio-videollamada',
        )
        consultas_virtuales.append({
            'cita': cita,
            'paciente': cita.paciente,
            'hora_cita': cita.hora_cita,
            'estado_class': estado_css.get(cita.estado, 'secondary'),
            'estado_display': cita.get_estado_display(),
            'sala_url': request.build_absolute_uri(f'{sala_path}?sala={token}'),
        })

    sala_activa = None
    sala_token = request.GET.get('sala')
    if sala_token:
        try:
            datos_sala = signing.loads(
                sala_token,
                salt='consultorio-videollamada',
                max_age=8 * 60 * 60,
            )
            if datos_sala.get('empresa') == empresa.id:
                paciente = Paciente.objects.filter(
                    id=datos_sala.get('paciente'),
                    empresa=empresa,
                ).first()
                sala_activa = {
                    'token': sala_token,
                    'paciente': paciente,
                    'cita_id': datos_sala.get('cita'),
                }
        except signing.BadSignature:
            messages.warning(request, 'La liga de la sala no es valida o ya expiro.')

    return render(request, 'consultorio/videollamada_segura.html', {
        'consultas_virtuales': consultas_virtuales,
        'sala_activa': sala_activa,
        'sala_actual_url': request.build_absolute_uri() if sala_activa else '',
    })


@login_required
@require_http_methods(["POST"])
def api_crear_sala_videollamada(request):
    """Crea una liga firmada de sala virtual para un paciente validado del tenant."""
    empresa = _empresa_explicita_usuario(request)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Sin empresa'}, status=403)

    try:
        data = json.loads(request.body or '{}') if request.body else request.POST
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON invalido'}, status=400)

    paciente_id = data.get('paciente_id')
    cita_id = data.get('cita_id')
    paciente = Paciente.objects.filter(id=paciente_id, empresa=empresa, activo=True).first()
    if not paciente:
        return JsonResponse({'ok': False, 'error': 'Paciente invalido'}, status=400)

    cita = None
    if cita_id:
        cita = CitaMedica.objects.filter(id=cita_id, empresa=empresa, paciente=paciente).first()

    token = signing.dumps(
        {
            'empresa': empresa.id,
            'paciente': paciente.id,
            'cita': cita.id if cita else None,
            'usuario': request.user.id,
            'emitida': timezone.now().isoformat(),
        },
        salt='consultorio-videollamada',
    )
    sala_url = request.build_absolute_uri(f"{reverse('consultorio:videollamada_segura')}?sala={token}")
    return JsonResponse({
        'ok': True,
        'sala_url': sala_url,
        'paciente': paciente.nombre_completo,
        'cita_id': cita.id if cita else None,
    })
