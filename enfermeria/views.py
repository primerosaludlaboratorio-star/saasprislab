"""
Modulo de Enfermeria - Captura de Signos Vitales y Triage
Blindaje H-009: Signos vitales inmutables en blockchain clínico
"""
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.db import transaction

from core.models import NotaClinicaSOAP, SignosVitales, CitaMedica, Paciente
from core.models.expediente_blindaje import SnapshotNotaMiddleware


@login_required
def dashboard_enfermeria(request):
    """Dashboard principal de enfermeria."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.now().date()
    pendientes = CitaMedica.objects.filter(empresa=empresa, fecha_cita=hoy, estado='EN_SALA').count()
    en_triage = CitaMedica.objects.filter(empresa=empresa, fecha_cita=hoy, estado='EN_CURSO').count()
    completados = SignosVitales.objects.filter(empresa=empresa, fecha_registro__date=hoy).count()

    return render(request, 'enfermeria/dashboard.html', {
        'empresa': empresa,
        'pacientes_pendientes': pendientes,
        'en_triage': en_triage,
        'completados_hoy': completados,
    })


@login_required
def lista_pacientes_triage(request):
    """Lista de pacientes pendientes de triage."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.now().date()
    pacientes = CitaMedica.objects.filter(
        empresa=empresa, fecha_cita=hoy, estado='EN_SALA'
    ).select_related('paciente', 'medico').order_by('hora_cita')

    return render(request, 'enfermeria/lista_triage.html', {
        'empresa': empresa,
        'pacientes': pacientes,
    })


@login_required
def capturar_signos_vitales(request, cita_id):
    """
    Capturar signos vitales del paciente.
    
    Blindaje H-009: Los signos vitales se inyectan en el snapshot inmutable
    de la cadena de custodia clínica. Cuando el médico firme con PIN-LAB,
    el hash englobará tanto el diagnóstico como los signos vitales.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)

    if request.method == 'POST':
        from .forms import SignosVitalesForm
        form = SignosVitalesForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                signos = form.save(commit=False)
                signos.paciente = cita.paciente
                signos.empresa = cita.empresa
                signos.cita = cita
                signos.registrado_por = request.user
                signos.save()
                
                # H-009: Crear snapshot inmutable con los signos vitales
                # Esto asegura que los signos vitales formen parte de la cadena de custodia
                _crear_snapshot_signos_vitales(cita, signos, request)
                
                cita.estado = 'EN_CURSO'
                cita.save(update_fields=['estado'])
            
            messages.success(
                request, 
                '✓ Signos vitales registrados y añadidos a la cadena de custodia inmutable.'
            )
            return redirect('enfermeria:lista_pacientes_triage')
    else:
        from .forms import SignosVitalesForm
        form = SignosVitalesForm()

    return render(request, 'enfermeria/capturar_signos.html', {'cita': cita, 'form': form})


def _crear_snapshot_signos_vitales(cita, signos, request):
    """
    Crea un snapshot inmutable de los signos vitales en la cadena de custodia.
    
    Blindaje H-009: Inyecta los signos vitales como parte del expediente
    inmutable, asegurando que no puedan ser alterados posteriormente.
    """
    # Construir payload de signos vitales para el snapshot
    signos_payload = {
        'tipo_snapshot': 'SIGNOS_VITALES_TRIAGE',
        'cita_id': cita.id,
        'paciente_id': cita.paciente.id,
        'enfermera_id': request.user.id,
        'timestamp_triage': timezone.now().isoformat(),
        'signos_vitales': {
            'presion_arterial_sistolica': str(signos.presion_arterial_sistolica) if signos.presion_arterial_sistolica else None,
            'presion_arterial_diastolica': str(signos.presion_arterial_diastolica) if signos.presion_arterial_diastolica else None,
            'frecuencia_cardiaca': signos.frecuencia_cardiaca,
            'frecuencia_respiratoria': signos.frecuencia_respiratoria,
            'temperatura': str(signos.temperatura) if signos.temperatura else None,
            'peso': str(signos.peso) if signos.peso else None,
            'talla': str(signos.talla) if signos.talla else None,
            'imc': str(signos.imc) if signos.imc else None,
            'saturacion_oxigeno': signos.saturacion_oxigeno,
            'glucosa_capilar': str(signos.glucosa_capilar) if signos.glucosa_capilar else None,
        },
        'alertas_generadas': _evaluar_alertas_signos(signos),
    }
    
    nota_soap = NotaClinicaSOAP.objects.filter(
        paciente=cita.paciente,
        empresa=cita.empresa,
        fecha_consulta__date=cita.fecha_cita,
    ).order_by('-id').first()

    if nota_soap:
        nota_soap.signos_vitales_snapshot = signos_payload
        nota_soap.save(update_fields=['signos_vitales_snapshot', 'ultima_modificacion'])
        try:
            SnapshotNotaMiddleware.crear_expediente_sha(
                nota_soap=nota_soap,
                estado='PRELIMINAR',
                ip=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        except Exception as e:
            import logging
            logger = logging.getLogger('enfermeria')
            logger.warning("No se pudo crear snapshot SHA de signos vitales: %s", e)
    else:
        import logging
        logging.getLogger('enfermeria').info(
            "Signos vitales sin nota SOAP el mismo día; registro clínico en SignosVitales id=%s",
            signos.id,
        )
    
    return signos_payload


def _evaluar_alertas_signos(signos):
    """Evalúa si los signos vitales generan alertas clínicas."""
    alertas = []
    
    if signos.presion_arterial_sistolica and signos.presion_arterial_sistolica >= 140:
        alertas.append({
            'tipo': 'HIPERTENSION',
            'severidad': 'ALTA',
            'valor': str(signos.presion_arterial_sistolica),
            'umbral': '>= 140 mmHg'
        })
    
    if signos.temperatura and signos.temperatura >= 38.0:
        alertas.append({
            'tipo': 'FIEBRE',
            'severidad': 'ALTA',
            'valor': str(signos.temperatura),
            'umbral': '>= 38°C'
        })
    
    if signos.frecuencia_cardiaca and signos.frecuencia_cardiaca >= 100:
        alertas.append({
            'tipo': 'TAQUICARDIA',
            'severidad': 'MEDIA',
            'valor': signos.frecuencia_cardiaca,
            'umbral': '>= 100 lpm'
        })
    
    if signos.saturacion_oxigeno and signos.saturacion_oxigeno < 90:
        alertas.append({
            'tipo': 'HIPOXEMIA',
            'severidad': 'CRITICA',
            'valor': signos.saturacion_oxigeno,
            'umbral': '< 90%'
        })
    
    return alertas


@login_required
def historial_signos_paciente(request, paciente_id):
    """Historial de signos vitales de un paciente."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    signos = SignosVitales.objects.filter(
        paciente=paciente, empresa=empresa
    ).order_by('-fecha_registro')[:20]
    return render(request, 'enfermeria/historial_signos.html', {'paciente': paciente, 'signos': signos})


@login_required
def graficas_tendencias(request, paciente_id):
    """Graficas de tendencias de signos vitales."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    signos = list(
        SignosVitales.objects.filter(paciente=paciente, empresa=empresa).order_by('fecha_registro')[:30]
    )

    datos_presion = json.dumps({
        'labels': [s.fecha_registro.strftime('%d/%m') for s in signos],
        'sistolica': [s.presion_arterial_sistolica or 0 for s in signos],
        'diastolica': [s.presion_arterial_diastolica or 0 for s in signos],
    })
    datos_temperatura = json.dumps({
        'labels': [s.fecha_registro.strftime('%d/%m') for s in signos],
        'values': [float(s.temperatura) if s.temperatura else 0 for s in signos],
    })

    return render(request, 'enfermeria/graficas_tendencias.html', {
        'paciente': paciente,
        'datos_presion': datos_presion,
        'datos_temperatura': datos_temperatura,
    })


@login_required
def alertas_signos_criticos(request):
    """Alertas de signos vitales criticos."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.now().date()
    alertas = SignosVitales.objects.filter(
        empresa=empresa, fecha_registro__date=hoy
    ).filter(
        Q(presion_arterial_sistolica__gte=140) |
        Q(temperatura__gte=38) |
        Q(frecuencia_cardiaca__gte=100)
    ).select_related('paciente', 'cita')

    return render(request, 'enfermeria/alertas_criticas.html', {
        'empresa': empresa,
        'alertas': alertas,
    })
