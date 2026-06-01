"""
core/views/bienestar.py
════════════════════════════════════════════════════════════════════════════════
Módulo Bienestar Staff — NOM-035-STPS-2018
CAJA FUERTE INTERNA: Solo empleados. Sin cruce con datos de pacientes.
AES-256 activado en DiarioEmocionalStaff, SesionCoachingStaff, EvaluacionNOM035.
════════════════════════════════════════════════════════════════════════════════
"""
import json
import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import (
    EvaluacionNOM035,
    DiarioEmocionalStaff,
    SesionCoachingStaff,
    AlertaBurnout,
    ProgramaCapacitacion,
    Empresa,
)

logger = logging.getLogger(__name__)

# ── Cuestionario NOM-035 (55 ítems simplificados en 20 representativos) ───────
CUESTIONARIO_NOM035 = [
    {'id': 1, 'categoria': 'Ambiente', 'texto': 'Mi trabajo me exige atender varias tareas al mismo tiempo'},
    {'id': 2, 'categoria': 'Ambiente', 'texto': 'En mi trabajo debo tomar decisiones difíciles muy rápido'},
    {'id': 3, 'categoria': 'Carga', 'texto': 'Mi trabajo me exige esfuerzo mental'},
    {'id': 4, 'categoria': 'Carga', 'texto': 'Mi trabajo me demanda mucho físicamente'},
    {'id': 5, 'categoria': 'Carga', 'texto': 'Tengo tiempo suficiente para terminar mis tareas'},
    {'id': 6, 'categoria': 'Organizacion', 'texto': 'En mi trabajo me dan instrucciones claras'},
    {'id': 7, 'categoria': 'Organizacion', 'texto': 'Sé exactamente qué se espera de mí'},
    {'id': 8, 'categoria': 'Organizacion', 'texto': 'Mi jefe habla conmigo sobre cómo realizo mi trabajo'},
    {'id': 9, 'categoria': 'Organizacion', 'texto': 'Puedo resolver problemas sin pedir permiso'},
    {'id': 10, 'categoria': 'Relaciones', 'texto': 'En mi trabajo tengo buen trato con mis compañeros'},
    {'id': 11, 'categoria': 'Relaciones', 'texto': 'En mi trabajo se me trata injustamente'},
    {'id': 12, 'categoria': 'Relaciones', 'texto': 'Tengo apoyo de mis compañeros cuando lo necesito'},
    {'id': 13, 'categoria': 'Violencia', 'texto': 'Alguien me ha intimidado o acosado en el trabajo'},
    {'id': 14, 'categoria': 'Violencia', 'texto': 'Algún compañero me ha tratado con hostilidad'},
    {'id': 15, 'categoria': 'Violencia', 'texto': 'Mi jefe me ha humillado o ridiculizado'},
    {'id': 16, 'categoria': 'Bienestar', 'texto': 'Me siento bien con el trabajo que realizo'},
    {'id': 17, 'categoria': 'Bienestar', 'texto': 'Mi trabajo afecta negativamente mi vida personal'},
    {'id': 18, 'categoria': 'Bienestar', 'texto': 'Me preocupa perder mi trabajo'},
    {'id': 19, 'categoria': 'Bienestar', 'texto': 'Siento que mi trabajo tiene un propósito'},
    {'id': 20, 'categoria': 'Bienestar', 'texto': 'Recomendaría este lugar de trabajo a un amigo'},
]

# Ítems con valores invertidos (mayor = mejor bienestar)
ITEMS_INVERSOS = {5, 9, 10, 12, 16, 19, 20}


def _calcular_nivel_riesgo(score: int, total_items: int) -> int:
    """Calcula nivel de riesgo 1-5 basado en score NOM-035."""
    porcentaje = (score / (total_items * 5)) * 100
    if porcentaje <= 20:
        return 1
    elif porcentaje <= 40:
        return 2
    elif porcentaje <= 60:
        return 3
    elif porcentaje <= 80:
        return 4
    return 5


def _verificar_riesgo_burnout(empleado, empresa):
    """Detecta patrones de burnout y crea AlertaBurnout si aplica."""
    from datetime import date
    hace_5_dias = timezone.now().date() - timedelta(days=5)

    entradas_recientes = DiarioEmocionalStaff.objects.filter(
        empleado=empleado,
        fecha__gte=hace_5_dias,
    )

    if entradas_recientes.count() < 3:
        return

    humor_bajo = entradas_recientes.filter(humor_general__lte=2).count()
    estres_alto = entradas_recientes.filter(nivel_estres__gte=8).count()

    if humor_bajo >= 3:
        AlertaBurnout.objects.get_or_create(
            empleado=empleado,
            empresa=empresa,
            tipo='HUMOR_BAJO',
            atendida=False,
            defaults={'nivel_riesgo': 4},
        )

    if estres_alto >= 3:
        AlertaBurnout.objects.get_or_create(
            empleado=empleado,
            empresa=empresa,
            tipo='ESTRES_ALTO',
            atendida=False,
            defaults={'nivel_riesgo': 4},
        )


# ── Vistas ─────────────────────────────────────────────────────────────────────

@login_required
def dashboard_bienestar(request):
    """Dashboard principal del módulo Bienestar Staff."""
    empresa = getattr(request.user, 'empresa', None)
    usuario = request.user

    # Estadísticas personales (sin revelar contenido privado)
    hace_30_dias = timezone.now().date() - timedelta(days=30)
    entradas_mes = DiarioEmocionalStaff.objects.filter(
        empleado=usuario, fecha__gte=hace_30_dias
    ).count()

    humor_promedio = None
    entradas_qs = DiarioEmocionalStaff.objects.filter(empleado=usuario, fecha__gte=hace_30_dias)
    if entradas_qs.exists():
        from django.db.models import Avg
        humor_promedio = round(entradas_qs.aggregate(Avg('humor_general'))['humor_general__avg'] or 0, 1)

    capacitaciones = ProgramaCapacitacion.objects.filter(
        empleado=usuario, empresa=empresa
    ).order_by('-fecha_inicio')[:5]

    sesiones = SesionCoachingStaff.objects.filter(
        empleado=usuario, empresa=empresa
    ).order_by('-fecha_sesion')[:5]

    # Para RRHH/Admin: resumen de alertas pendientes (sin contenido privado)
    alertas_rrhh = None
    if request.user.is_superuser or getattr(request.user, 'rol', '') in ('ADMIN', 'DIRECTOR', 'GERENTE'):
        alertas_rrhh = AlertaBurnout.objects.filter(empresa=empresa, atendida=False).count()

    evaluaciones = EvaluacionNOM035.objects.filter(empleado=usuario).order_by('-fecha')[:3]

    # Últimas 7 entradas del diario para el widget emocional
    ultimas_entradas_diario = DiarioEmocionalStaff.objects.filter(
        empleado=usuario
    ).order_by('-fecha')[:7]

    ctx = {
        'entradas_mes': entradas_mes,
        'humor_promedio': humor_promedio,
        'capacitaciones': capacitaciones,
        'sesiones': sesiones,
        'sesiones_proximas': sesiones,          # alias que usa el template
        'alertas_rrhh': alertas_rrhh,
        'alertas_activas': alertas_rrhh,        # alias que usa el template
        'evaluaciones': evaluaciones,
        'ultimas_entradas_diario': ultimas_entradas_diario,
        'seccion_activa': 'bienestar',
    }
    return render(request, 'core/bienestar/dashboard.html', ctx)


@login_required
def diario_emocional(request):
    """Vista y registro del Diario Emocional privado (AES-256 activado)."""
    empresa = getattr(request.user, 'empresa', None)
    usuario = request.user

    if request.method == 'POST':
        try:
            humor = int(request.POST.get('humor_general', 3))
            estres = int(request.POST.get('nivel_estres', 5))
            contenido = request.POST.get('contenido', '').strip()
            horas = request.POST.get('horas_sueno')
            actividad = request.POST.get('actividad_fisica') == 'on'
            fecha_str = request.POST.get('fecha', timezone.now().date().isoformat())

            from datetime import date
            try:
                fecha = date.fromisoformat(fecha_str)
            except ValueError:
                fecha = timezone.now().date()

            obj, created = DiarioEmocionalStaff.objects.update_or_create(
                empleado=usuario,
                fecha=fecha,
                defaults={
                    'humor_general': max(1, min(5, humor)),
                    'nivel_estres': max(1, min(10, estres)),
                    'contenido': contenido,  # Se cifra automáticamente por EncryptedTextField
                    'horas_sueno': float(horas) if horas else None,
                    'actividad_fisica': actividad,
                },
            )

            # Verificar patrones de burnout
            _verificar_riesgo_burnout(usuario, empresa)

            messages.success(request, '✅ Entrada guardada de forma privada y cifrada.')
            return redirect('diario_emocional')

        except Exception as exc:
            logger.error('Error guardando diario emocional: %s', exc)
            messages.error(request, f'Error al guardar: {exc}')

    # Solo el propio usuario puede ver sus entradas
    entradas = DiarioEmocionalStaff.objects.filter(
        empleado=usuario
    ).order_by('-fecha')[:30]

    return render(request, 'core/bienestar/diario.html', {
        'entradas': entradas,
        'seccion_activa': 'bienestar',
    })


@login_required
def evaluacion_nom035(request):
    """Cuestionario NOM-035 (20 ítems representativos). Respuestas cifradas."""
    empresa = getattr(request.user, 'empresa', None)
    usuario = request.user
    periodo = timezone.now().strftime('%Y-%m')

    # Verificar si ya completó este período
    ya_completo = EvaluacionNOM035.objects.filter(
        empleado=usuario, periodo=periodo, completada=True
    ).exists()

    if request.method == 'POST' and not ya_completo:
        respuestas = {}
        score_total = 0
        for item in CUESTIONARIO_NOM035:
            val = int(request.POST.get(f'item_{item["id"]}', 3))
            val = max(1, min(5, val))
            respuestas[str(item['id'])] = val
            # Ítems inversos: mejor bienestar = respuesta alta → menos riesgo
            if item['id'] in ITEMS_INVERSOS:
                score_total += (6 - val)
            else:
                score_total += val

        nivel = _calcular_nivel_riesgo(score_total, len(CUESTIONARIO_NOM035))

        evaluacion, _ = EvaluacionNOM035.objects.update_or_create(
            empleado=usuario,
            periodo=periodo,
            defaults={
                'respuestas_json': json.dumps(respuestas),  # Cifrado por EncryptedTextField
                'score_total': score_total,
                'nivel_riesgo': nivel,
                'completada': True,
            }
        )

        # Crear alerta si riesgo medio o mayor
        if evaluacion.alerta_requerida:
            AlertaBurnout.objects.get_or_create(
                empleado=usuario,
                empresa=empresa,
                tipo='NOM035_RIESGO',
                atendida=False,
                defaults={'nivel_riesgo': nivel},
            )

        messages.success(request, f'✅ Evaluación NOM-035 completada. Nivel de riesgo: {evaluacion.get_nivel_riesgo_display()}')
        return redirect('dashboard_bienestar')

    evaluaciones_previas = EvaluacionNOM035.objects.filter(
        empleado=usuario
    ).order_by('-fecha')[:6]

    return render(request, 'core/bienestar/evaluacion_nom035.html', {
        'cuestionario': CUESTIONARIO_NOM035,
        'periodo': periodo,
        'ya_completo': ya_completo,
        'evaluaciones_previas': evaluaciones_previas,
        'seccion_activa': 'bienestar',
    })


@login_required
def alertas_rrhh(request):
    """
    Vista de alertas de burnout para RRHH/Admin.
    SOLO muestra: empleado, tipo de alerta, fecha.
    NUNCA muestra contenido del diario ni respuestas de evaluación.
    """
    empresa = getattr(request.user, 'empresa', None)
    rol = getattr(request.user, 'rol', '')

    if not (request.user.is_superuser or rol in ('ADMIN', 'DIRECTOR', 'GERENTE')):
        messages.error(request, 'Acceso restringido a RRHH/Dirección.')
        return redirect('dashboard_bienestar')

    if request.method == 'POST':
        alerta_id = request.POST.get('alerta_id')
        notas = request.POST.get('notas', '').strip()
        if alerta_id:
            try:
                alerta = AlertaBurnout.objects.get(id=alerta_id, empresa=empresa)
                alerta.atendida = True
                alerta.atendida_por = request.user
                alerta.notas_rrhh = notas
                alerta.save()
                messages.success(request, f'✅ Alerta {alerta_id} marcada como atendida.')
            except AlertaBurnout.DoesNotExist:
                messages.error(request, 'Alerta no encontrada.')

    alertas_qs = AlertaBurnout.objects.filter(empresa=empresa).select_related(
        'empleado', 'atendida_por'
    ).order_by('atendida', '-fecha')
    total_pendientes = alertas_qs.filter(atendida=False).count()
    alertas = alertas_qs[:100]

    return render(request, 'core/bienestar/alertas_rrhh.html', {
        'alertas': alertas,
        'total_pendientes': total_pendientes,
        'seccion_activa': 'bienestar',
    })


@login_required
def capacitaciones(request):
    """Registro de capacitaciones del personal."""
    empresa = getattr(request.user, 'empresa', None)
    usuario = request.user

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        fecha_inicio = request.POST.get('fecha_inicio')
        horas = request.POST.get('horas', 1)
        descripcion = request.POST.get('descripcion', '').strip()

        if titulo and fecha_inicio:
            ProgramaCapacitacion.objects.create(
                empleado=usuario,
                empresa=empresa,
                titulo=titulo,
                fecha_inicio=fecha_inicio,
                horas=int(horas),
                descripcion=descripcion,
            )
            messages.success(request, '✅ Capacitación registrada.')
            return redirect('capacitaciones_bienestar')

    mis_caps = ProgramaCapacitacion.objects.filter(
        empleado=usuario, empresa=empresa
    ).order_by('-fecha_inicio')

    return render(request, 'core/bienestar/capacitaciones.html', {
        'capacitaciones': mis_caps,
        'seccion_activa': 'bienestar',
    })
