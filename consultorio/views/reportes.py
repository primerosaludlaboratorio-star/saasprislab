"""
Vistas de reportes y funciones de soporte: analisis_patrones, api_generar_analisis_patron,
campanas_marketing, encuestas_satisfaccion, seguimiento_tratamiento, reportes_productividad,
historial_signos_vitales, agenda_medico, vademecum_lista, triaje_pre_cita, lista_espera,
api_agregar_lista_espera, crear_paciente_express, configuracion_medico,
api_plantillas_especialidad (ver api_consulta.py), archivos_paciente (ver api_consulta.py).
"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum, Q
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from core.models import (
    Paciente, CitaMedica, ConsultaMedica, SignosVitales,
)
from core.services.audit_service import registrar_auditoria
from core.utils.trazabilidad import registrar_trazabilidad
from core.utils.trazabilidad import serializar_modelo
from core.utils.empresa_request import empresa_efectiva_request

from ._helpers import _int_or_none, _dec_or_none

logger = logging.getLogger('consultorio')


# ==============================================================================
# ANÁLISIS DE PATRONES CON IA
# ==============================================================================

@login_required
def analisis_patrones(request):
    """Vista para generar análisis de patrones de consulta con IA (datos ANÓNIMOS)."""
    from consultorio.models import AnalisisPatron

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    analisis_previos = AnalisisPatron.objects.filter(
        empresa=empresa
    ).order_by('-fecha_generacion')[:10]

    return render(request, 'consultorio/analisis_patrones.html', {
        'analisis_previos': analisis_previos,
        'tipo_choices': AnalisisPatron.TIPO_CHOICES,
    })


@login_required
@require_http_methods(['POST'])
def api_generar_analisis_patron(request):
    """Genera un análisis de patrones usando IA sobre datos ANONIMIZADOS."""
    from consultorio.models import AnalisisPatron

    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
        tipo = data.get('tipo', 'DIAGNOSTICO')
        try:
            dias = int(data.get('dias', 90))
        except (TypeError, ValueError):
            dias = 90

        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)

        hoy = timezone.localdate()
        desde = hoy - timedelta(days=dias)

        consultas = ConsultaMedica.objects.filter(
            empresa=empresa,
            fecha_consulta__date__gte=desde,
            estado='FINALIZADA'
        )

        total = consultas.count()

        if total == 0:
            return JsonResponse({'ok': False, 'error': 'No hay consultas en el periodo seleccionado'}, status=400)

        datos_anonimos = {'total_consultas': total}

        if tipo == 'DIAGNOSTICO':
            diagnosticos = consultas.values('diagnostico_principal').annotate(
                cantidad=Count('id')
            ).order_by('-cantidad')[:20]
            datos_anonimos['top_diagnosticos'] = list(diagnosticos)

        elif tipo == 'CONVERSION':
            con_receta = consultas.filter(receta__isnull=False).count()
            datos_anonimos['tasa_recetas'] = round((con_receta / total) * 100, 1) if total > 0 else 0
            datos_anonimos['con_receta'] = con_receta

        elif tipo == 'PRODUCTIVIDAD':
            por_dia = consultas.extra(
                select={'dia': 'DATE(fecha_consulta)'}
            ).values('dia').annotate(cantidad=Count('id')).order_by('dia')
            datos_anonimos['consultas_por_dia'] = list(por_dia)
            datos_anonimos['promedio_diario'] = round(total / max(dias, 1), 1)

        elif tipo == 'FINANCIERO':
            ingresos = consultas.filter(pagada=True).aggregate(
                total=Sum('precio_consulta')
            )['total'] or 0
            datos_anonimos['ingresos_periodo'] = float(ingresos)
            datos_anonimos['ticket_promedio'] = round(float(ingresos) / total, 2) if total > 0 else 0

        analisis_ia = ""
        recomendaciones = ""

        try:
            from core.utils.gemini_client import generate_content

            prompt_ia = f"""
Eres un consultor de gestión clínica. Analiza estos datos ANÓNIMOS de un consultorio médico
y genera insights prácticos y recomendaciones de mejora.

TIPO DE ANÁLISIS: {tipo}
PERÍODO: Últimos {dias} días
DATOS: {json.dumps(datos_anonimos, default=str, ensure_ascii=False)}

Genera:
1. INSIGHTS: 3-5 observaciones clave sobre los patrones
2. RECOMENDACIONES: 3-5 acciones específicas para mejorar
3. Si es CONVERSION: Estrategias para mejorar la conversión de servicios

Responde en español, de forma directa y práctica. Sin formato JSON.
"""
            texto = generate_content(prompt_ia, max_tokens=1200).strip()

            if 'RECOMENDACIONES' in texto.upper():
                analisis_ia = texto[:texto.upper().find('RECOMENDACIONES')]
                recomendaciones = texto[texto.upper().find('RECOMENDACIONES'):]
            else:
                analisis_ia = texto

        except (ImportError, AttributeError, ValueError, RuntimeError) as e:
            logger.warning("IA no disponible para analisis de patrones: %s", e)

        analisis = AnalisisPatron.objects.create(
            empresa=empresa,
            tipo=tipo,
            periodo_inicio=desde,
            periodo_fin=hoy,
            total_consultas=total,
            datos_json=datos_anonimos,
            analisis_ia=analisis_ia,
            recomendaciones=recomendaciones,
            generado_por=request.user,
        )

        return JsonResponse({
            'ok': True,
            'analisis_id': analisis.id,
            'datos': datos_anonimos,
            'analisis_ia': analisis_ia,
            'recomendaciones': recomendaciones,
            'mensaje': 'Analisis generado exitosamente'
        })

    except (DatabaseError, ValidationError, ValueError, TypeError) as e:
        logger.error("Error generando analisis: %s", e)
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ==============================================================================
# LISTA DE ESPERA
# ==============================================================================

@login_required
def lista_espera(request):
    """Vista de la lista de espera del consultorio."""
    from consultorio.models import ListaEspera

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    espera = ListaEspera.objects.filter(
        empresa=empresa, activo=True, atendido=False
    ).select_related('paciente', 'medico').order_by('prioridad', 'fecha_registro')

    return render(request, 'consultorio/lista_espera.html', {
        'lista_espera': espera,
    })


@login_required
@require_http_methods(['POST'])
def api_agregar_lista_espera(request):
    """Agrega un paciente a la lista de espera."""
    from consultorio.models import ListaEspera

    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)

        paciente_id = data.get('paciente_id')
        if paciente_id is None or paciente_id == '':
            return JsonResponse({'ok': False, 'error': 'paciente_id es requerido'}, status=400)

        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

        espera = ListaEspera.objects.create(
            empresa=empresa,
            paciente=paciente,
            medico=request.user if data.get('medico_especifico') else None,
            motivo=data.get('motivo', ''),
            fecha_preferida=data.get('fecha_preferida') or None,
            hora_preferida=data.get('hora_preferida') or None,
            prioridad=int(data.get('prioridad') or 5) if str(data.get('prioridad', '')).isdigit() else 5,
        )

        return JsonResponse({
            'ok': True,
            'espera_id': espera.id,
            'mensaje': f'{paciente.nombre_completo} agregado a lista de espera'
        })

    except (DatabaseError, ValidationError, ValueError, TypeError) as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ==============================================================================
# VADEMÉCUM (Vista de Lista)
# ==============================================================================

@login_required
def vademecum_lista(request):
    """Vista del Vademécum integrado."""
    from consultorio.models import Vademecum

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    medicamentos = Vademecum.objects.filter(activo=True).filter(
        Q(empresa=empresa) | Q(empresa__isnull=True)
    ).order_by('nombre_generico')

    grupos_terapeuticos = (
        medicamentos.exclude(grupo_terapeutico='')
        .values_list('grupo_terapeutico', flat=True)
        .distinct()
        .order_by('grupo_terapeutico')
    )

    return render(request, 'consultorio/vademecum.html', {
        'medicamentos': medicamentos,
        'grupos_terapeuticos': list(grupos_terapeuticos),
    })


# ==============================================================================
# HISTORIAL DE SIGNOS VITALES
# ==============================================================================

@login_required
def historial_signos_vitales(request, paciente_id):
    """Vista de historial de signos vitales del paciente con gráficas de tendencias."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    signos_vitales = SignosVitales.objects.filter(
        paciente=paciente
    ).order_by('-fecha_registro')[:50]

    return render(request, 'consultorio/historial_signos_vitales.html', {
        'paciente': paciente,
        'signos_vitales': signos_vitales,
    })


# ==============================================================================
# AGENDA DEL MÉDICO
# ==============================================================================

@login_required
def agenda_medico(request):
    """Vista de la agenda del médico con switch ON/OFF."""
    from consultorio.models import ConfiguracionMedico

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    config, _ = ConfiguracionMedico.objects.get_or_create(
        medico=request.user, defaults={'empresa': empresa}
    )

    fecha_str = request.GET.get('fecha')
    if fecha_str:
        try:
            fecha_actual = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            fecha_actual = timezone.localdate()
    else:
        fecha_actual = timezone.localdate()

    fecha_anterior = fecha_actual - timedelta(days=1)
    fecha_siguiente = fecha_actual + timedelta(days=1)

    citas_qs = CitaMedica.objects.filter(empresa=empresa, fecha_cita=fecha_actual)
    medico_vinculado = None
    if hasattr(request.user, 'medico_profile') and getattr(request.user.medico_profile, 'empresa_id', None) == empresa.id:
        medico_vinculado = request.user.medico_profile
    if medico_vinculado and not request.user.is_superuser:
        citas_qs = citas_qs.filter(medico=medico_vinculado)
    citas = citas_qs.select_related('paciente', 'medico').order_by('hora_cita')

    stats = {
        'total': citas.count(),
        'pendientes': citas.filter(estado='PENDIENTE').count(),
        'en_curso': citas.filter(estado='EN_CURSO').count(),
        'completadas': citas.filter(estado='COMPLETADA').count(),
    }

    return render(request, 'consultorio/agenda_medico.html', {
        'config': config,
        'citas': citas,
        'stats': stats,
        'fecha_actual': fecha_actual,
        'fecha_anterior': fecha_anterior,
        'fecha_siguiente': fecha_siguiente,
    })


# ==============================================================================
# TRIAJE DIGITAL PRE-CITA
# ==============================================================================

@login_required
def triaje_pre_cita(request):
    """Vista de triaje digital pre-cita."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    from consultorio.models import AgendaCita, ConfiguracionMedico

    hoy = timezone.localdate()
    medicos_con_triaje = list(
        ConfiguracionMedico.objects.filter(
            empresa=empresa, triaje_precita_activo=True,
        ).values_list('medico_id', flat=True)
    )

    citas_pendientes_qs = AgendaCita.objects.none()
    if medicos_con_triaje:
        citas_pendientes_qs = (
            AgendaCita.objects.filter(
                empresa=empresa,
                medico_id__in=medicos_con_triaje,
                fecha__gte=hoy,
                estatus=AgendaCita.ESTATUS_PROGRAMADA,
            )
            .select_related('paciente', 'medico')
            .order_by('fecha', 'hora')[:50]
        )

    triajes_pendientes = [
        SimpleNamespace(
            paciente=cita.paciente,
            cita=SimpleNamespace(fecha_cita=cita.fecha, hora_cita=cita.hora),
            fecha_envio=cita.fecha_creacion,
            canal='WHATSAPP',
            get_canal_display='WhatsApp',
        )
        for cita in citas_pendientes_qs
    ]

    consultas_recientes = (
        ConsultaMedica.objects.filter(
            empresa=empresa,
            estado='FINALIZADA',
            fecha_consulta__gte=timezone.now() - timedelta(days=30),
        )
        .select_related('paciente')
        .order_by('-fecha_consulta')[:50]
    )
    triajes_completados = [
        SimpleNamespace(
            paciente=consulta.paciente,
            motivo_consulta=consulta.motivo_consulta,
            sintomas_principales=consulta.padecimiento_actual,
            nivel_urgencia='ALTA' if consulta.tipo_consulta == 'URGENCIA' else 'NORMAL',
            fecha_respuesta=consulta.fecha_consulta,
        )
        for consulta in consultas_recientes
    ]
    total_enviados = len(triajes_pendientes) + len(triajes_completados)
    total_completados = len(triajes_completados)
    stats = {
        'enviados': total_enviados,
        'completados': total_completados,
        'pendientes': len(triajes_pendientes),
        'tasa_respuesta': round((total_completados / total_enviados) * 100, 1) if total_enviados else 0,
    }

    return render(request, 'consultorio/triaje_pre_cita.html', {
        'triajes_pendientes': triajes_pendientes,
        'triajes_completados': triajes_completados,
        'stats': stats,
    })


# ==============================================================================
# CAMPAÑAS DE MARKETING MÉDICO
# ==============================================================================

@login_required
def campanas_marketing(request):
    """Vista de campañas de marketing médico."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    from marketing.models import CampanaMarketing, MarketingTrackingHit

    campanas_qs = (
        CampanaMarketing.objects
        .filter(empresa=empresa)
        .select_related('sucursal', 'creado_por')
        .order_by('-fecha_creacion')[:50]
    )
    total_campanas = CampanaMarketing.objects.filter(empresa=empresa).count()
    total_pacientes = Paciente.objects.filter(empresa=empresa, activo=True).count()
    tracking_hits = MarketingTrackingHit.objects.filter(empresa=empresa).count()
    base_alcance = max(total_pacientes * max(total_campanas, 1), 1)

    primera_campana = (
        CampanaMarketing.objects
        .filter(empresa=empresa)
        .order_by('fecha_creacion')
        .values_list('fecha_creacion', flat=True)
        .first()
    )
    citas_generadas = 0
    if primera_campana:
        citas_generadas = CitaMedica.objects.filter(
            empresa=empresa, fecha_cita__gte=primera_campana.date(),
        ).count()

    canal_map = {
        'email': 'EMAIL', 'sms': 'SMS', 'whatsapp': 'WHATSAPP', 'push': 'PUSH',
    }
    campanas = []
    for campana in campanas_qs:
        segmento = campana.segmento or 'TODOS'
        campanas.append({
            'id': campana.id,
            'nombre': campana.nombre or segmento.replace('_', ' ').title(),
            'descripcion': campana.mensaje_whatsapp,
            'get_tipo_display': segmento.replace('_', ' ').title(),
            'canal': canal_map.get(campana.canal_comunicacion, 'WHATSAPP'),
            'total_destinatarios': total_pacientes,
            'estado': 'ENVIADA' if campana.activa else 'BORRADOR',
            'fecha_envio': campana.fecha_creacion,
        })

    stats = {
        'total_enviadas': total_campanas,
        'total_pacientes': total_pacientes,
        'tasa_apertura': min(round((tracking_hits / base_alcance) * 100), 100),
        'citas_generadas': citas_generadas,
    }

    return render(request, 'consultorio/campanas_marketing.html', {
        'campanas': campanas,
        'stats': stats,
    })


# ==============================================================================
# ENCUESTAS DE SATISFACCIÓN (NPS)
# ==============================================================================

@login_required
def encuestas_satisfaccion(request):
    """Dashboard de encuestas de satisfacción NPS."""
    from consultorio.models import EncuestaSatisfaccion
    from django.db.models import Avg

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    encuestas = EncuestaSatisfaccion.objects.filter(empresa=empresa, respondida=True)
    total_respondidas = encuestas.count()

    if total_respondidas > 0:
        promotores = encuestas.filter(puntuacion_nps__gte=9).count()
        detractores = encuestas.filter(puntuacion_nps__lte=6).count()
        pasivos = total_respondidas - promotores - detractores
        pct_promotores = round((promotores / total_respondidas) * 100)
        pct_detractores = round((detractores / total_respondidas) * 100)
        pct_pasivos = round((pasivos / total_respondidas) * 100)
        nps_score = pct_promotores - pct_detractores
    else:
        pct_promotores = pct_detractores = pct_pasivos = 0
        nps_score = 0

    promedios = encuestas.aggregate(
        atencion_medico=Avg('atencion_medico'),
        tiempo_espera=Avg('tiempo_espera'),
        instalaciones=Avg('instalaciones'),
        explicacion=Avg('explicacion_tratamiento'),
    )
    for k, v in promedios.items():
        if v is not None:
            promedios[k] = round(v, 1)

    total_enviadas = EncuestaSatisfaccion.objects.filter(empresa=empresa, enviada=True).count()
    tasa = round((total_respondidas / total_enviadas) * 100) if total_enviadas > 0 else 0

    stats = {
        'total_enviadas': total_enviadas,
        'respondidas': total_respondidas,
        'tasa_respuesta': tasa,
        'promedio_estrellas': promedios.get('atencion_medico') or 0,
    }

    encuestas_recientes = encuestas.select_related('paciente').order_by('-fecha_respuesta')[:15]

    return render(request, 'consultorio/encuestas_satisfaccion.html', {
        'nps_score': nps_score,
        'pct_promotores': pct_promotores,
        'pct_detractores': pct_detractores,
        'pct_pasivos': pct_pasivos,
        'promedios': promedios,
        'stats': stats,
        'encuestas_recientes': encuestas_recientes,
    })


# ==============================================================================
# SEGUIMIENTO DE TRATAMIENTO
# ==============================================================================

@login_required
def seguimiento_tratamiento(request):
    """Vista de seguimientos de tratamiento activos."""
    from consultorio.models import SeguimientoTratamiento

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.now()

    base_qs = SeguimientoTratamiento.objects.filter(
        empresa=empresa, activo=True
    ).select_related('paciente', 'consulta')

    seguimientos_medicacion = base_qs.filter(tipo='MEDICACION').order_by('fecha_programada')
    seguimientos_citas = base_qs.filter(tipo='PROXIMA_CITA').order_by('fecha_programada')
    seguimientos_estudios = base_qs.filter(tipo='ESTUDIOS').order_by('fecha_programada')

    stats = {
        'activos': base_qs.count(),
        'enviados_hoy': base_qs.filter(enviado=True, fecha_envio__date=hoy.date()).count(),
        'pendientes_envio': base_qs.filter(enviado=False, fecha_programada__lte=hoy).count(),
        'pacientes_en_seguimiento': base_qs.values('paciente').distinct().count(),
    }

    return render(request, 'consultorio/seguimiento_tratamiento.html', {
        'seguimientos_medicacion': seguimientos_medicacion,
        'seguimientos_citas': seguimientos_citas,
        'seguimientos_estudios': seguimientos_estudios,
        'stats': stats,
    })


# ==============================================================================
# REPORTES DE PRODUCTIVIDAD
# ==============================================================================

@login_required
def reportes_productividad(request):
    """Dashboard de reportes de productividad del consultorio."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    try:
        dias = int(request.GET.get('periodo', 30))
    except (ValueError, TypeError):
        dias = 30
    hoy = timezone.localdate()
    desde = hoy - timedelta(days=dias)

    consultas = ConsultaMedica.objects.filter(
        empresa=empresa, fecha_consulta__date__gte=desde, estado='FINALIZADA',
    )

    total = consultas.count()
    ingresos = consultas.filter(pagada=True).aggregate(total=Sum('precio_consulta'))['total'] or 0

    citas_periodo = CitaMedica.objects.filter(empresa=empresa, fecha_cita__gte=desde)
    canceladas = citas_periodo.filter(estado='CANCELADA').count()
    total_citas = citas_periodo.count()

    kpis = {
        'total_consultas': total,
        'pacientes_nuevos': consultas.filter(tipo_consulta='PRIMERA_VEZ').count(),
        'pacientes_subsecuentes': consultas.filter(tipo_consulta='SUBSECUENTE').count(),
        'tasa_cancelacion': round((canceladas / total_citas) * 100, 1) if total_citas > 0 else 0,
        'ingresos_totales': float(ingresos),
        'ticket_promedio': round(float(ingresos) / total, 0) if total > 0 else 0,
    }

    datos_charts = {}

    por_dia = consultas.extra(
        select={'dia': 'DATE(fecha_consulta)'}
    ).values('dia').annotate(
        cantidad=Count('id'),
        ingresos_dia=Sum('precio_consulta')
    ).order_by('dia')

    datos_charts['consultas_por_dia'] = {
        'fechas': [str(d['dia']) for d in por_dia],
        'cantidad': [d['cantidad'] for d in por_dia],
        'ingresos': [float(d['ingresos_dia'] or 0) for d in por_dia],
    }

    top_dx = consultas.exclude(
        diagnostico_principal__isnull=True
    ).exclude(diagnostico_principal='').values('diagnostico_principal').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')[:8]

    datos_charts['top_diagnosticos'] = {
        'labels': [d['diagnostico_principal'][:30] for d in top_dx],
        'data': [d['cantidad'] for d in top_dx],
    }

    from django.db.models.functions import TruncMonth

    cancelaciones_por_mes = dict(
        citas_periodo.filter(estado='CANCELADA')
        .annotate(mes_dt=TruncMonth('fecha_cita'))
        .values('mes_dt')
        .annotate(total=Count('id'))
        .values_list('mes_dt', 'total')
    )
    resumen_mensual = []
    for row in (
        consultas.annotate(mes_dt=TruncMonth('fecha_consulta'))
        .values('mes_dt')
        .annotate(
            consultas=Count('id'),
            nuevos=Count('id', filter=Q(tipo_consulta='PRIMERA_VEZ')),
            subsecuentes=Count('id', filter=Q(tipo_consulta='SUBSECUENTE')),
            ingresos=Sum('precio_consulta'),
        )
        .order_by('-mes_dt')[:12]
    ):
        consultas_mes = row['consultas'] or 0
        ingresos_mes = float(row['ingresos'] or 0)
        resumen_mensual.append({
            'mes': row['mes_dt'].strftime('%m/%Y') if row['mes_dt'] else '',
            'consultas': consultas_mes,
            'nuevos': row['nuevos'] or 0,
            'subsecuentes': row['subsecuentes'] or 0,
            'cancelaciones': cancelaciones_por_mes.get(row['mes_dt'], 0),
            'ingresos': ingresos_mes,
            'ticket_promedio': round(ingresos_mes / consultas_mes, 2) if consultas_mes else 0,
        })

    return render(request, 'consultorio/reportes_productividad.html', {
        'kpis': kpis,
        'datos_charts': json.dumps(datos_charts, default=str),
        'resumen_mensual': resumen_mensual,
    })


# ==============================================================================
# CONFIGURACIÓN DEL MÉDICO
# ==============================================================================

@login_required
def configuracion_medico(request):
    """Vista para que el médico configure su 'isla independiente'."""
    from consultorio.models import ConfiguracionMedico

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    config, created = ConfiguracionMedico.objects.get_or_create(
        medico=request.user, defaults={'empresa': empresa}
    )

    if request.method == 'POST':
        try:
            config.agenda_activa = request.POST.get('agenda_activa') == 'on'
            duracion_val = _int_or_none(request.POST.get('duracion_consulta_default', 30))
            config.duracion_consulta_default = duracion_val if duracion_val is not None else 30
            config.horario_inicio = request.POST.get('horario_inicio', '08:00')
            config.horario_fin = request.POST.get('horario_fin', '20:00')
            config.reserva_online_activa = request.POST.get('reserva_online_activa') == 'on'

            dias = request.POST.getlist('dias_atencion')
            config.dias_atencion = [d for d in (_int_or_none(x) for x in dias) if d is not None and 0 <= d <= 6]

            config.modo_cobro = request.POST.get('modo_cobro', 'RECEPCION')
            precio = _dec_or_none(request.POST.get('precio_consulta_default', '0'))
            config.precio_consulta_default = precio if precio is not None else Decimal('0')

            config.marketing_propio = request.POST.get('marketing_propio') == 'on'
            config.especialidad_principal = request.POST.get('especialidad_principal', 'Medico General')
            config.subespecialidad = request.POST.get('subespecialidad', '')
            config.whatsapp_confirmaciones = request.POST.get('whatsapp_confirmaciones') == 'on'
            config.telefono_whatsapp = request.POST.get('telefono_whatsapp', '')
            config.triaje_precita_activo = request.POST.get('triaje_precita_activo') == 'on'

            config.save()
            messages.success(request, 'Configuracion guardada exitosamente')
            return redirect('consultorio:configuracion_medico')

        except (DatabaseError, ValidationError) as e:
            messages.error(request, f'Error al guardar: {str(e)}')

    return render(request, 'consultorio/configuracion_medico.html', {
        'config': config,
    })


# ==============================================================================
# REGISTRO RÁPIDO DE PACIENTES (DESDE DASHBOARD)
# ==============================================================================

@login_required
def crear_paciente_express(request):
    """
    Vista Express: Crea un paciente nuevo.
    Acepta POST con JSON (flujo nuevo) o POST con form-data (flujo legacy).
    """
    if request.method != 'POST':
        return redirect('consultorio:dashboard_consultorio')

    is_json = request.content_type and 'json' in request.content_type
    try:
        empresa = empresa_efectiva_request(request)
        if not empresa:
            messages.error(request, 'Usuario no tiene empresa asignada.')
            return redirect('home')

        if is_json:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
            nombres = (data.get('nombres') or '').strip().upper()
            apellido_paterno = (data.get('apellido_paterno') or '').strip().upper()
            apellido_materno = (data.get('apellido_materno') or '').strip().upper()
            nombre_completo = (data.get('nombre_completo') or '').strip().upper()
            fecha_nacimiento = data.get('fecha_nacimiento') or None
            sexo = data.get('sexo') or None
            telefono = (data.get('telefono') or '').strip()
            email = (data.get('email') or '').strip()
        else:
            nombres = request.POST.get('nombres', '').strip().upper()
            apellido_paterno = request.POST.get('apellido_paterno', '').strip().upper()
            apellido_materno = request.POST.get('apellido_materno', '').strip().upper()
            nombre_completo = ''
            fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
            sexo = request.POST.get('sexo') or None
            telefono = request.POST.get('telefono', '').strip()
            email = request.POST.get('email', '').strip()

        if not nombre_completo and (nombres or apellido_paterno):
            partes = [p for p in [nombres, apellido_paterno, apellido_materno] if p]
            nombre_completo = ' '.join(partes)

        if not nombre_completo and not nombres:
            if is_json:
                return JsonResponse({'ok': False, 'error': 'El nombre es obligatorio'}, status=400)
            messages.error(request, 'El nombre es obligatorio')
            return redirect('consultorio:dashboard_consultorio')

        paciente = Paciente.objects.create(
            empresa=empresa,
            nombres=nombres,
            apellido_paterno=apellido_paterno,
            apellido_materno=apellido_materno,
            nombre_completo=nombre_completo,
            fecha_nacimiento=fecha_nacimiento,
            sexo=sexo,
            telefono=telefono,
            email=email,
            activo=True
        )

        registrar_trazabilidad(
            tipo_operacion='REGISTRO',
            modulo='CONSULTORIO',
            referencia_id=paciente.id,
            referencia_tipo='Paciente',
            accion='CREAR',
            descripcion=f'Registro rapido: {paciente.nombre_completo}',
            usuario=request.user,
            empresa=empresa,
            datos_anteriores={},
            datos_nuevos=serializar_modelo(paciente)
        )
        registrar_auditoria(
            accion='CREATE',
            modelo='Paciente',
            objeto_id=str(paciente.id),
            datos_nuevos={
                'nombre_completo': paciente.nombre_completo,
                'telefono': paciente.telefono or '',
                'sexo': paciente.sexo or '',
            },
            request=request,
        )

        if is_json:
            return JsonResponse({
                'ok': True,
                'uuid': str(paciente.uuid),
                'id': paciente.id,
                'nombre_completo': paciente.nombre_completo,
                'mensaje': f'Paciente {paciente.nombre_completo} registrado'
            })

        messages.success(request, f"Paciente {paciente.nombre_completo} registrado correctamente.")
        if paciente.uuid:
            return redirect('consultorio:nueva_consulta_paciente', paciente_uuid=paciente.uuid)
        return redirect('consultorio:nueva_consulta')

    except (DatabaseError, ValidationError, ValueError, TypeError) as e:
        logger.error("Error en crear_paciente_express: %s", e, exc_info=True)
        if is_json:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
        messages.error(request, f"Error al registrar paciente: {e}")
        return redirect('consultorio:dashboard_consultorio')
