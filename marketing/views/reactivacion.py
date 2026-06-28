from __future__ import annotations

import logging
from datetime import timedelta
from urllib.error import URLError

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import OrdenDeServicio, Paciente
from core.utils.whatsapp_sender import generar_enlace_whatsapp

logger = logging.getLogger('marketing.reactivacion')


# Palabras clave por segmento para buscar en estudios.
_PALABRAS_CLAVE = {
    'diabeticos': ['glucosa', 'hba1c', 'hemoglobina glucosilada', 'diabetes', 'curva de glucosa'],
    'hipertensos': ['electrolitos', 'sodio', 'potasio', 'creatinina', 'urea', 'hipertension'],
    'renales': ['creatinina', 'urea', 'depuracion', 'aclaramiento', 'renal'],
    'cardiaco': ['troponina', 'ck-mb', 'bnp', 'dhl', 'cardiaco'],
    'todos': [],
}


@login_required
@require_http_methods(["GET"])
def api_detectar_pacientes_inactivos(request):
    """
    PRIS Marketing IA — Detecta pacientes crónicos que no han tenido
    actividad en los últimos N meses (default: 6).
    Segmentos soportados: diabeticos, hipertensos, renales, cardiaco, todos.

    Retorna lista de pacientes con teléfono, último estudio y enlace WhatsApp pre-generado.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Sin empresa'}, status=400)

    try:
        meses = int(request.GET.get('meses', 6))
        if meses < 1 or meses > 36:
            raise ValueError("meses fuera de rango")
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'meses debe ser un entero entre 1 y 36'}, status=400)

    segmento = request.GET.get('segmento', 'diabeticos').lower()
    claves = _PALABRAS_CLAVE.get(segmento, _PALABRAS_CLAVE['diabeticos'])

    try:
        fecha_corte = timezone.now() - timedelta(days=meses * 30)

        if claves:
            from core.models import DetalleOrden
            from django.db.models import Q

            q = Q()
            for c in claves:
                q |= Q(analito__nombre__icontains=c)
            pacientes_ids_cronicos = (
                DetalleOrden.objects.filter(
                    q,
                    orden__empresa=empresa,
                ).values_list('orden__paciente_id', flat=True).distinct()
            )
        else:
            pacientes_ids_cronicos = Paciente.objects.filter(
                empresa=empresa, activo=True
            ).values_list('id', flat=True)

        pacientes_con_actividad_reciente = (
            OrdenDeServicio.objects.filter(
                empresa=empresa,
                paciente_id__in=pacientes_ids_cronicos,
                fecha_creacion__gte=fecha_corte,
            ).values_list('paciente_id', flat=True).distinct()
        )

        pacientes_inactivos = (
            Paciente.objects.filter(
                id__in=pacientes_ids_cronicos,
                empresa=empresa,
                activo=True,
            ).exclude(
                id__in=pacientes_con_actividad_reciente,
            ).select_related()
            .order_by('nombre_completo')[:100]
        )

        resultado = []
        empresa_nombre = getattr(empresa, 'nombre', 'PRISLAB')
        for p in pacientes_inactivos:
            whatsapp = None
            if p.telefono:
                nombre_corto = (p.nombre_completo or '').split()[0] if p.nombre_completo else 'Paciente'
                msg = (
                    f"Hola {nombre_corto} 👋\n\n"
                    f"En *{empresa_nombre}* nos importa tu salud. "
                    f"Han pasado algunos meses desde tu última visita y queremos invitarte "
                    f"a programar tu chequeo de control. 🧬\n\n"
                    f"¿Te gustaría agendar una cita? Escríbenos y con gusto te atendemos. "
                    f"¡Primero tu salud! 💙"
                )
                try:
                    whatsapp = generar_enlace_whatsapp(p.telefono, msg)
                except (ValueError, URLError) as exc:
                    logger.warning('No se pudo generar enlace WhatsApp para paciente %s: %s', p.id, exc)

            resultado.append({
                'id': p.id,
                'nombre': p.nombre_completo or '',
                'telefono': p.telefono or '',
                'fecha_nacimiento': p.fecha_nacimiento.isoformat() if p.fecha_nacimiento else None,
                'whatsapp': whatsapp,
            })

        return JsonResponse({
            'ok': True,
            'segmento': segmento,
            'meses_inactivo': meses,
            'total': len(resultado),
            'pacientes': resultado,
        })

    except (DatabaseError, ValidationError) as e:
        logger.error('api_detectar_pacientes_inactivos: %s', e, exc_info=True)
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
