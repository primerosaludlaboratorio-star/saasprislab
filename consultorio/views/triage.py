"""
Vistas de enfermería / triage: lista de triage y captura de signos vitales.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db import transaction
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.contrib import messages

from core.models import CitaMedica, SignosVitales
from core.services.audit_service import registrar_auditoria
from core.utils.empresa_request import empresa_efectiva_request

from ._helpers import (
    _int_in_range, _dec_in_range, _dec_or_none,
    _SV_PA_SIS_MIN, _SV_PA_SIS_MAX,
    _SV_PA_DIA_MIN, _SV_PA_DIA_MAX,
    _SV_FC_MIN, _SV_FC_MAX,
    _SV_FR_MIN, _SV_FR_MAX,
    _SV_TEMP_MIN, _SV_TEMP_MAX,
    _SV_PESO_MIN, _SV_PESO_MAX,
    _SV_TALLA_MIN, _SV_TALLA_MAX,
    _SV_SPO2_MIN, _SV_SPO2_MAX,
    _SV_GLUC_MIN, _SV_GLUC_MAX,
)

logger = logging.getLogger('consultorio')


# ==============================================================================
# PASO 2: ENFERMERÍA (TRIAGE OPCIONAL)
# ==============================================================================

@login_required
def lista_triage(request):
    """
    Lista de pacientes en sala de espera (EN_SALA) para triage.
    Solo accesible por enfermeras.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    hoy = timezone.localdate()
    
    # Citas en sala de espera que aún no tienen signos vitales
    citas = CitaMedica.objects.filter(
        empresa=empresa,
        fecha_cita=hoy,
        estado='EN_SALA',
        signos_vitales__isnull=True  # No tienen signos vitales todavía
    ).select_related('paciente', 'medico').order_by('hora_cita')
    
    return render(request, 'consultorio/lista_triage.html', {
        'citas': citas,
    })


@login_required
def captura_signos_vitales(request, cita_id):
    """
    Formulario de triage para capturar signos vitales.
    Al guardar, marca la cita como LISTO_PARA_CONSULTA.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('consultorio:tablero_recepcion')
    cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)
    
    # Verificar si ya tiene signos vitales (para GET usar instancia vacía si no existe, evita crash en template)
    signos = SignosVitales.objects.filter(cita=cita).first()
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Crear o actualizar signos vitales
                if not signos:
                    signos = SignosVitales(
                        paciente=cita.paciente,
                        empresa=empresa,
                        cita=cita,
                        registrado_por=request.user
                    )
                
                # Capturar valores con rangos clínicamente razonables (CICLO 6)
                signos.presion_arterial_sistolica = _int_in_range(
                    request.POST.get('pa_sistolica'), _SV_PA_SIS_MIN, _SV_PA_SIS_MAX)
                signos.presion_arterial_diastolica = _int_in_range(
                    request.POST.get('pa_diastolica'), _SV_PA_DIA_MIN, _SV_PA_DIA_MAX)
                signos.frecuencia_cardiaca = _int_in_range(
                    request.POST.get('frecuencia_cardiaca'), _SV_FC_MIN, _SV_FC_MAX)
                signos.frecuencia_respiratoria = _int_in_range(
                    request.POST.get('frecuencia_respiratoria'), _SV_FR_MIN, _SV_FR_MAX)
                signos.temperatura = _dec_in_range(
                    request.POST.get('temperatura'), _SV_TEMP_MIN, _SV_TEMP_MAX)
                signos.peso = _dec_in_range(request.POST.get('peso'), _SV_PESO_MIN, _SV_PESO_MAX)
                signos.talla = _dec_in_range(request.POST.get('talla'), _SV_TALLA_MIN, _SV_TALLA_MAX)
                # Opcionales
                if request.POST.get('perimetro_abdominal') is not None:
                    signos.perimetro_abdominal = _dec_or_none(request.POST.get('perimetro_abdominal'))
                if request.POST.get('saturacion_oxigeno') is not None:
                    signos.saturacion_oxigeno = _int_in_range(
                        request.POST.get('saturacion_oxigeno'), _SV_SPO2_MIN, _SV_SPO2_MAX)
                if request.POST.get('glucosa_capilar') is not None:
                    signos.glucosa_capilar = _dec_in_range(
                        request.POST.get('glucosa_capilar'), _SV_GLUC_MIN, _SV_GLUC_MAX)
                
                signos.observaciones = request.POST.get('observaciones', '')
                signos.save()  # El IMC se calcula automáticamente en el save()
                # CICLO 15: Auditoría forense - triage / signos vitales
                registrar_auditoria(
                    accion='CREATE' if not signos.pk else 'UPDATE',
                    modelo='SignosVitales',
                    objeto_id=str(signos.id),
                    datos_nuevos={
                        'cita_id': cita.id,
                        'paciente_id': cita.paciente_id,
                        'pa_sistolica': signos.presion_arterial_sistolica,
                        'pa_diastolica': signos.presion_arterial_diastolica,
                        'temperatura': str(signos.temperatura) if signos.temperatura is not None else None,
                        'peso': str(signos.peso) if signos.peso is not None else None,
                        'talla': str(signos.talla) if signos.talla is not None else None,
                    },
                    request=request,
                )
                # Cambiar estado de la cita a EN_SALA (listo para médico)
                cita.estado = 'EN_SALA'
                cita.save(update_fields=['estado'])
                
                messages.success(request, f'Signos vitales registrados para {cita.paciente.nombre_completo}')
                return redirect('consultorio:lista_triage')
                
        except (DatabaseError, ValidationError) as e:
            messages.error(request, f'Error al guardar signos vitales: {str(e)}')
    
    # Para GET o re-render tras error: asegurar que signos no sea None (template accede a signos.xxx)
    if signos is None:
        signos = SignosVitales(
            paciente=cita.paciente,
            empresa=empresa,
            cita=cita,
            registrado_por=request.user,
        )
    
    return render(request, 'consultorio/captura_signos_vitales.html', {
        'cita': cita,
        'signos': signos,
    })
