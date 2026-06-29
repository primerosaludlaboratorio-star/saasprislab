"""
Vistas clínicas: lista de trabajo médico, consulta sin cita, SOAP, simplificada, con paciente.
"""
import logging
import uuid as uuid_lib
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from core.decorators import role_required
from core.models import (
    Paciente, Medico, CitaMedica, SignosVitales, ConsultaMedica,
    HistoriaClinica, HistorialCambiosConsulta, Receta, RecetaItem,
    Producto, CertificadoMedico, OrdenDeServicio, DetalleOrden,
)
from core.lims_cart import resolve_lims_cart_ids, aplicar_precio_convenio
from core.services.audit_service import registrar_auditoria
from core.utils.trazabilidad import registrar_trazabilidad
from core.utils.empresa_request import empresa_efectiva_request
from core.utils.sucursal_helpers import get_request_sucursal

from ._helpers import (
    _int_or_none, _dec_or_none, _int_in_range, _dec_in_range,
    _resolver_medico_usuario,
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
# PASO 3: CONSULTORIO (VISTA MAESTRA ADAPTATIVA)
# ==============================================================================

@login_required
def lista_trabajo_medico(request):
    """
    Lista de pacientes listos para consulta.
    Solo muestra citas con signos vitales capturados O todas si el médico no tiene enfermera.
    NO muestra pacientes del laboratorio, solo los que tienen CITA MÉDICA.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    hoy = timezone.localdate()
    
    # Obtener médico actual (lista de trabajo puede ser por médico o todas)
    medico_actual = _resolver_medico_usuario(request, empresa)
    
    # Permitir filtrar por fecha (opcional)
    fecha_filtro = request.GET.get('fecha', None)
    if fecha_filtro:
        try:
            from datetime import datetime
            fecha = datetime.strptime(fecha_filtro, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            fecha = hoy
    else:
        fecha = hoy
    
    # Citas del día seleccionado en sala de espera o en curso (del médico actual si hay)
    # NO incluye pacientes del laboratorio (solo citas médicas)
    citas_qs = CitaMedica.objects.filter(
        empresa=empresa,
        fecha_cita=fecha,
        estado__in=['EN_SALA', 'EN_CURSO']
    )
    if medico_actual:
        citas_qs = citas_qs.filter(medico=medico_actual)
    citas = citas_qs.select_related('paciente', 'medico', 'signos_vitales').order_by('hora_cita')
    
    # También mostrar consultas en curso del día sin cita previa (del médico actual si hay)
    consultas_sin_cita_qs = ConsultaMedica.objects.filter(
        empresa=empresa,
        fecha_consulta__date=fecha,
        cita__isnull=True
    )
    if medico_actual:
        consultas_sin_cita_qs = consultas_sin_cita_qs.filter(medico=medico_actual)
    consultas_sin_cita = consultas_sin_cita_qs.select_related('paciente', 'medico').order_by('-fecha_consulta')
    
    return render(request, 'consultorio/lista_trabajo_medico.html', {
        'citas': citas,
        'consultas_sin_cita': consultas_sin_cita,
        'hoy': hoy,
        'fecha_filtro': fecha,
        'medico_actual': medico_actual,
    })


@login_required
def consulta_sin_cita(request):
    """
    Vista para crear una consulta sin cita previa (Walk-in).
    Permite seleccionar un paciente existente o crear uno nuevo,
    y crea automáticamente una CitaMedica express.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    if request.method == 'POST':
        try:
            paciente_id = request.POST.get('paciente_id')
            motivo = request.POST.get('motivo', 'Consulta sin cita previa')
            
            # Obtener paciente
            paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
            
            # Obtener médico (el usuario actual si es médico, o crear uno genérico) — scope por empresa
            medico = _resolver_medico_usuario(request, empresa, autocrear=True)
            
            # Crear cita express
            with transaction.atomic():
                cita = CitaMedica.objects.create(
                    empresa=empresa,
                    sucursal=get_request_sucursal(request),
                    paciente=paciente,
                    medico=medico,
                    fecha_cita=timezone.localdate(),
                    hora_cita=timezone.localtime().time(),
                    duracion_estimada=30,
                    motivo=motivo,
                    estado='EN_CURSO'  # Directamente en curso
                )
                
                messages.success(request, f'Consulta creada para {paciente.nombre_completo}')
                return redirect('consultorio:nueva_consulta_soap', cita_id=cita.id)
                
        except (DatabaseError, ValidationError) as e:
            messages.error(request, f'Error al crear consulta: {str(e)}')
    
    # GET: Mostrar formulario
    # Obtener pacientes recientes para búsqueda rápida
    pacientes_recientes = Paciente.objects.filter(
        empresa=empresa
    ).order_by('-fecha_registro')[:20]
    
    return render(request, 'consultorio/consulta_sin_cita.html', {
        'pacientes_recientes': pacientes_recientes,
    })


@login_required
@role_required('MEDICO', 'ADMIN')
def nueva_consulta_soap(request, cita_id):
    """
    VISTA MAESTRA CON LÓGICA HÍBRIDA ADAPTATIVA.
    
    Al abrir una cita:
    - Caso A: Ya tiene SignosVitales → Los muestra como read-only o disabled
    - Caso B: No tiene SignosVitales → Muestra formulario editable dentro de la misma página
    
    Si es primera vez:
    - Muestra formulario de Historia Clínica (AHF/APNP/APP/AGO) en pestaña
    
    Si ya existe:
    - Muestra antecedentes colapsados para referencia rápida
    
    Formato SOAP completo con campos amplios.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)
    
    # Verificar si ya existe SignosVitales para esta cita
    signos_vitales = SignosVitales.objects.filter(cita=cita).first()
    signos_vitales_existen = signos_vitales is not None
    
    # Verificar si el paciente tiene Historia Clínica
    try:
        historia_clinica = cita.paciente.historia_clinica
    except HistoriaClinica.DoesNotExist:
        historia_clinica = None
    
    # Buscar o crear consulta
    consulta = ConsultaMedica.objects.filter(cita=cita).first()
    if not consulta:
        consulta = ConsultaMedica(
            empresa=empresa,
            sucursal=get_request_sucursal(request),
            paciente=cita.paciente,
            medico=cita.medico,
            cita=cita,
            historia_clinica=historia_clinica,
        )
    
    # POST: Guardar consulta y opcionalmente signos vitales e historia clínica
    if request.method == 'POST':
        # CICLO 6: Protección contra doble envío (bloqueo por cita mientras se procesa)
        _lock_key = '_soap_post_lock'
        if request.session.get(_lock_key) == cita_id:
            messages.warning(request, 'El formulario ya está siendo guardado. No envíe de nuevo.')
            return redirect('consultorio:nueva_consulta_soap', cita_id=cita.id)
        request.session[_lock_key] = cita_id
        try:
            with transaction.atomic():
                # ========== GUARDAR SIGNOS VITALES (si no existen) ==========
                # Guardar si capturar_signos=1 o si hay datos de signos (ej. formulario SOAP con captura rápida)
                tiene_datos_signos = any(request.POST.get(k) for k in (
                    'presion_arterial', 'pa_sistolica', 'frecuencia_cardiaca', 'peso', 'temperatura', 'talla'
                ))
                if not signos_vitales_existen and (request.POST.get('capturar_signos') == '1' or tiene_datos_signos):
                    signos_vitales = SignosVitales(
                        paciente=cita.paciente,
                        empresa=empresa,
                        cita=cita,
                        registrado_por=request.user
                    )
                    # Aceptar pa_sistolica/pa_diastolica o presion_arterial "120/80" (CICLO 6: rangos)
                    signos_vitales.presion_arterial_sistolica = _int_in_range(
                        request.POST.get('pa_sistolica'), _SV_PA_SIS_MIN, _SV_PA_SIS_MAX)
                    signos_vitales.presion_arterial_diastolica = _int_in_range(
                        request.POST.get('pa_diastolica'), _SV_PA_DIA_MIN, _SV_PA_DIA_MAX)
                    if (signos_vitales.presion_arterial_sistolica is None or signos_vitales.presion_arterial_diastolica is None) and request.POST.get('presion_arterial'):
                        parts = request.POST.get('presion_arterial', '').strip().replace(',', '.').split('/')
                        if len(parts) >= 2:
                            signos_vitales.presion_arterial_sistolica = _int_in_range(
                                parts[0].strip(), _SV_PA_SIS_MIN, _SV_PA_SIS_MAX)
                            signos_vitales.presion_arterial_diastolica = _int_in_range(
                                parts[1].strip(), _SV_PA_DIA_MIN, _SV_PA_DIA_MAX)
                        elif len(parts) == 1:
                            signos_vitales.presion_arterial_sistolica = _int_in_range(
                                parts[0].strip(), _SV_PA_SIS_MIN, _SV_PA_SIS_MAX)
                    signos_vitales.frecuencia_cardiaca = _int_in_range(
                        request.POST.get('frecuencia_cardiaca'), _SV_FC_MIN, _SV_FC_MAX)
                    signos_vitales.frecuencia_respiratoria = _int_in_range(
                        request.POST.get('frecuencia_respiratoria'), _SV_FR_MIN, _SV_FR_MAX)
                    signos_vitales.temperatura = _dec_in_range(
                        request.POST.get('temperatura'), _SV_TEMP_MIN, _SV_TEMP_MAX)
                    signos_vitales.peso = _dec_in_range(request.POST.get('peso'), _SV_PESO_MIN, _SV_PESO_MAX)
                    signos_vitales.talla = _dec_in_range(request.POST.get('talla'), _SV_TALLA_MIN, _SV_TALLA_MAX)
                    if request.POST.get('perimetro_abdominal'):
                        signos_vitales.perimetro_abdominal = _dec_or_none(request.POST.get('perimetro_abdominal'))
                    if request.POST.get('saturacion_oxigeno'):
                        signos_vitales.saturacion_oxigeno = _int_in_range(
                            request.POST.get('saturacion_oxigeno'), _SV_SPO2_MIN, _SV_SPO2_MAX)
                    if request.POST.get('glucosa_capilar'):
                        signos_vitales.glucosa_capilar = _dec_in_range(
                            request.POST.get('glucosa_capilar'), _SV_GLUC_MIN, _SV_GLUC_MAX)
                    
                    signos_vitales.observaciones = request.POST.get('observaciones_signos', '')
                    signos_vitales.save()
                
                # ========== GUARDAR HISTORIA CLÍNICA (si no existe) ==========
                if not historia_clinica and request.POST.get('crear_historia') == '1':
                    historia_clinica = HistoriaClinica(
                        empresa=empresa,
                        paciente=cita.paciente,
                        creado_por=request.user
                    )
                    # AHF
                    historia_clinica.ahf_diabetes = request.POST.get('ahf_diabetes') == 'on'
                    historia_clinica.ahf_hipertension = request.POST.get('ahf_hipertension') == 'on'
                    historia_clinica.ahf_cancer = request.POST.get('ahf_cancer') == 'on'
                    historia_clinica.ahf_cardiopatias = request.POST.get('ahf_cardiopatias') == 'on'
                    historia_clinica.ahf_otros = request.POST.get('ahf_otros', '')
                    
                    # APNP
                    historia_clinica.apnp_tabaquismo = request.POST.get('apnp_tabaquismo', 'NUNCA')
                    historia_clinica.apnp_alcoholismo = request.POST.get('apnp_alcoholismo', 'NUNCA')
                    historia_clinica.apnp_drogas = request.POST.get('apnp_drogas', 'NUNCA')
                    historia_clinica.apnp_actividad_fisica = request.POST.get('apnp_actividad_fisica', 'SEDENTARIO')
                    historia_clinica.apnp_alimentacion = request.POST.get('apnp_alimentacion', '')
                    
                    # APP
                    historia_clinica.app_cirugias_previas = request.POST.get('app_cirugias_previas', '')
                    historia_clinica.app_hospitalizaciones = request.POST.get('app_hospitalizaciones', '')
                    historia_clinica.app_transfusiones = request.POST.get('app_transfusiones', '')
                    historia_clinica.app_alergias = request.POST.get('app_alergias', '')
                    historia_clinica.app_enfermedades_cronicas = request.POST.get('app_enfermedades_cronicas', '')
                    
                    # AGO (si es mujer) — CICLO 6: parse seguro para evitar ValueError
                    if cita.paciente.sexo == 'F':
                        v = _int_or_none(request.POST.get('ago_menarca'))
                        if v is not None:
                            historia_clinica.ago_menarca = v
                        v = _int_or_none(request.POST.get('ago_gestas'))
                        if v is not None:
                            historia_clinica.ago_gestas = v
                        v = _int_or_none(request.POST.get('ago_partos'))
                        if v is not None:
                            historia_clinica.ago_partos = v
                        v = _int_or_none(request.POST.get('ago_cesareas'))
                        if v is not None:
                            historia_clinica.ago_cesareas = v
                        v = _int_or_none(request.POST.get('ago_abortos'))
                        if v is not None:
                            historia_clinica.ago_abortos = v
                        if request.POST.get('ago_fum'):
                            historia_clinica.ago_fum = request.POST.get('ago_fum')
                        historia_clinica.ago_metodo_planificacion = request.POST.get('ago_metodo_planificacion', '')
                    
                    historia_clinica.save()
                
                # ========== GUARDAR CONSULTA MÉDICA (SOAP) ==========
                # VALORES POR DEFECTO: Si el médico no llena campos, usar placeholders
                # para permitir continuar el flujo de trabajo (facilidad para médicos renuentes)
                DEFAULTS_CONSULTA = {
                    'motivo_consulta': 'No especificado - Consulta general',
                    'padecimiento_actual': 'No documentado',
                    'exploracion_fisica': 'Sin hallazgos reportados - Exploración no documentada',
                    'diagnostico_principal': 'Consulta sin diagnóstico documentado',
                    'plan_tratamiento': 'Manejo no documentado - Se recomienda revisar notas adicionales',
                    'diagnostico_cie10': 'Z71.9',  # Código CIE-10 para consulta general no especificada
                }
                
                motivo_consulta = (request.POST.get('motivo_consulta') or '').strip()
                padecimiento_actual = (request.POST.get('padecimiento_actual') or '').strip()
                exploracion_fisica = (request.POST.get('exploracion_fisica') or '').strip()
                diagnostico_principal = (request.POST.get('diagnostico_principal') or '').strip()
                plan_tratamiento = (request.POST.get('plan_tratamiento') or '').strip()
                diagnostico_cie10 = (request.POST.get('diagnostico_cie10', '') or '').strip()[:20]
                
                # Aplicar valores por defecto para campos vacíos
                if not motivo_consulta:
                    motivo_consulta = DEFAULTS_CONSULTA['motivo_consulta']
                if not padecimiento_actual:
                    padecimiento_actual = DEFAULTS_CONSULTA['padecimiento_actual']
                if not exploracion_fisica:
                    exploracion_fisica = DEFAULTS_CONSULTA['exploracion_fisica']
                if not diagnostico_principal:
                    diagnostico_principal = DEFAULTS_CONSULTA['diagnostico_principal']
                if not plan_tratamiento:
                    plan_tratamiento = DEFAULTS_CONSULTA['plan_tratamiento']
                if not diagnostico_cie10:
                    diagnostico_cie10 = DEFAULTS_CONSULTA['diagnostico_cie10']
                    messages.info(request, 'Se asignó código CIE-10 por defecto (Z71.9). Se recomienda actualizar con el diagnóstico correcto.')
                # CICLO 6: Respetar max_length del modelo (diagnostico_principal=500, diagnostico_cie10=20)
                consulta.motivo_consulta = motivo_consulta
                consulta.padecimiento_actual = padecimiento_actual
                consulta.exploracion_fisica = exploracion_fisica
                consulta.diagnostico_principal = (diagnostico_principal or '')[:500]
                consulta.diagnostico_cie10 = diagnostico_cie10[:20] if diagnostico_cie10 else None
                consulta.diagnosticos_secundarios = request.POST.get('diagnosticos_secundarios', '')
                consulta.plan_tratamiento = plan_tratamiento
                consulta.estudios_solicitados = request.POST.get('estudios_solicitados', '')
                consulta.pronostico = request.POST.get('pronostico', 'BUENO')
                
                # CICLO 6: Parse seguro de fecha_proxima_cita (evitar asignar string a DateField)
                if request.POST.get('fecha_proxima_cita'):
                    try:
                        from datetime import datetime as dt_fpc
                        fpc_str = request.POST.get('fecha_proxima_cita', '').strip()
                        fpc = dt_fpc.strptime(fpc_str, '%Y-%m-%d').date()
                        hoy_fpc = timezone.localdate()
                        if fpc < hoy_fpc:
                            messages.warning(request, 'La próxima cita no puede ser en el pasado; no se guardó.')
                        elif (fpc - hoy_fpc).days > 365:
                            messages.warning(request, 'La próxima cita no puede ser mayor a un año; no se guardó.')
                        else:
                            consulta.fecha_proxima_cita = fpc
                    except (ValueError, AttributeError):
                        pass  # Ignorar formato inválido
                
                # Relacionar signos vitales e historia clínica
                if signos_vitales:
                    consulta.signos_vitales = signos_vitales
                if historia_clinica:
                    consulta.historia_clinica = historia_clinica
                
                consulta.tipo_consulta = request.POST.get('tipo_consulta', 'SUBSECUENTE')
                try:
                    consulta.precio_consulta = Decimal(request.POST.get('precio_consulta', '0') or '0')
                except (ValueError, TypeError, InvalidOperation):
                    consulta.precio_consulta = Decimal('0')
                
                # Finalizar si se marca (el botón envía accion=finalizar)
                accion = request.POST.get('accion', '')
                if accion == 'finalizar' or request.POST.get('finalizar') == '1':
                    consulta.estado = 'FINALIZADA'
                    cita.estado = 'COMPLETADA'
                    cita.save(update_fields=['estado'])
                
                # Auditoría forense: registrar cambios SOAP si la consulta ya existía (edición)
                soap_campos = (
                    'motivo_consulta', 'padecimiento_actual', 'exploracion_fisica',
                    'diagnostico_principal', 'diagnostico_cie10', 'diagnosticos_secundarios',
                    'plan_tratamiento', 'estudios_solicitados', 'pronostico',
                )
                if consulta.pk:
                    consulta_refresh = ConsultaMedica.objects.filter(pk=consulta.pk).first()
                    if consulta_refresh:
                        razon_base = f"Edición desde formulario SOAP por {getattr(request.user, 'username', 'sistema')}"
                        for campo in soap_campos:
                            old_val = getattr(consulta_refresh, campo, None)
                            new_val = getattr(consulta, campo, None)
                            if old_val != new_val:
                                # CICLO 6: truncar valores muy largos para historial (TextField sin límite DB)
                                val_ant = (str(old_val) if old_val is not None else '')[:10000]
                                val_nue = (str(new_val) if new_val is not None else '')[:10000]
                                HistorialCambiosConsulta.objects.create(
                                    consulta=consulta,
                                    campo_modificado=campo[:100],
                                    valor_anterior=val_ant,
                                    valor_nuevo=val_nue,
                                    razon_cambio=razon_base[:2000],
                                    usuario_modificador=request.user,
                                    ip_origen=getattr(request, 'META', {}).get('REMOTE_ADDR'),
                                )
                
                es_nueva_consulta = not consulta.pk
                consulta.save()

                registrar_auditoria(
                    accion='CREATE' if es_nueva_consulta else 'UPDATE',
                    modelo='ConsultaMedica',
                    objeto_id=str(consulta.id),
                    datos_nuevos={
                        'cita_id': cita.id,
                        'paciente_id': cita.paciente_id,
                        'diagnostico': (consulta.diagnostico_principal or '')[:200],
                        'estado': consulta.estado,
                    },
                    request=request,
                )
                
                # ========== PROCESAR RECETA MÉDICA (si hay medicamentos) ==========
                medicamento_ids = request.POST.getlist('medicamento_id[]')
                if medicamento_ids and len(medicamento_ids) > 0:
                    import uuid as _uuid
                    # Datos del médico
                    medico_obj = cita.medico
                    folio = f"RX-{cita.id}-{_uuid.uuid4().hex[:6].upper()}"
                    
                    receta = Receta.objects.create(
                        empresa=empresa,
                        paciente=cita.paciente,
                        medico=medico_obj,
                        folio_receta=folio,
                        diagnostico_principal=consulta.diagnostico_principal or 'En proceso',
                        indicaciones=consulta.plan_tratamiento or '',
                        medico_nombre_completo=medico_obj.nombre_completo if medico_obj else request.user.get_full_name(),
                        medico_cedula=medico_obj.cedula_profesional if medico_obj else '',
                        medico_especialidad=medico_obj.especialidad if medico_obj else 'Médico General',
                    )
                    
                    # Agregar items de la receta
                    medicamento_nombres = request.POST.getlist('medicamento_nombre[]')
                    medicamento_dosis = request.POST.getlist('medicamento_dosis[]')
                    medicamento_duracion = request.POST.getlist('medicamento_duracion[]')
                    medicamento_cantidad = request.POST.getlist('medicamento_cantidad[]')
                    
                    for i, med_id in enumerate(medicamento_ids):
                        try:
                            med_producto = None
                            if int(med_id) > 0:
                                med_producto = Producto.objects.filter(id=int(med_id), empresa=empresa).first()
                            
                            nombre = medicamento_nombres[i] if i < len(medicamento_nombres) else ''
                            dosis = medicamento_dosis[i] if i < len(medicamento_dosis) else ''
                            duracion = medicamento_duracion[i] if i < len(medicamento_duracion) else ''
                            try:
                                cant = int((medicamento_cantidad[i] if i < len(medicamento_cantidad) else None) or 1)
                            except (ValueError, TypeError):
                                cant = 1
                            
                            # Componer texto_libre con toda la información de la prescripción (CICLO 6: max 500)
                            partes = [nombre]
                            if dosis:
                                partes.append(f"Dosis: {dosis}")
                            if duracion:
                                partes.append(f"Duración: {duracion}")
                            texto = (' | '.join(partes))[:500]
                            RecetaItem.objects.create(
                                receta=receta,
                                medicamento=med_producto,
                                texto_libre=texto or None,
                                cantidad=max(1, cant),
                            )
                        except (ValueError, TypeError, DatabaseError, ValidationError) as e:
                            logger.error(f"Error agregando medicamento {i}: {e}")
                    
                    # Vincular receta a la consulta
                    consulta.receta = receta
                    consulta.save(update_fields=['receta'])
                    # CICLO 15: Auditoría forense - creación de receta
                    registrar_auditoria(
                        accion='CREATE',
                        modelo='Receta',
                        objeto_id=str(receta.id),
                        datos_nuevos={
                            'folio_receta': receta.folio_receta,
                            'paciente_id': receta.paciente_id,
                            'consulta_id': consulta.id,
                            'items_count': len(medicamento_ids),
                        },
                        request=request,
                    )
                    messages.success(request, f'Receta generada con {len(medicamento_ids)} medicamentos')
                
                # ========== PROCESAR CERTIFICADO MÉDICO (si se solicita) ==========
                if request.POST.get('tipo_certificado') and request.POST.get('motivo_certificado'):
                    try:
                        import uuid as _uuid_cert
                        from datetime import timedelta as _td
                        tipo_form = request.POST.get('tipo_certificado', 'MEDICO')
                        tipo_map_form = {
                            'MEDICO': 'SALUD', 'INCAPACIDAD': 'INCAPACIDAD',
                            'APTITUD': 'APTITUD', 'DEFUNCION': 'DEFUNCION',
                            'NACIMIENTO': 'NACIMIENTO',
                        }
                        tipo_cert_form = tipo_map_form.get(tipo_form, 'OTRO')
                        motivo_cert = request.POST.get('motivo_certificado', '')
                        dias_inc_cert = _int_or_none(request.POST.get('dias_incapacidad', '0')) or 0
                        fecha_ini_cert = timezone.now().date()
                        fecha_fin_cert = fecha_ini_cert + _td(days=dias_inc_cert) if dias_inc_cert else fecha_ini_cert
                        
                        certificado = CertificadoMedico.objects.create(
                            empresa=empresa,
                            paciente=cita.paciente,
                            medico=cita.medico,
                            consulta=consulta,
                            folio_certificado=f"CERT-{cita.id}-{_uuid_cert.uuid4().hex[:6].upper()}",
                            tipo_certificado=tipo_cert_form,
                            diagnostico=consulta.diagnostico_principal or motivo_cert,
                            descripcion=motivo_cert,
                            dias_incapacidad=dias_inc_cert if dias_inc_cert else None,
                            fecha_inicio=fecha_ini_cert,
                            fecha_fin=fecha_fin_cert,
                        )
                        registrar_auditoria(
                            accion='CREATE',
                            modelo='CertificadoMedico',
                            objeto_id=str(certificado.id),
                            datos_nuevos={
                                'folio': certificado.folio_certificado,
                                'tipo': tipo_cert_form,
                                'paciente_id': cita.paciente_id,
                                'cita_id': cita.id,
                            },
                            request=request,
                        )
                        messages.success(request, 'Certificado médico generado')
                    except (DatabaseError, ValidationError) as e:
                        logger.error(f"Error generando certificado: {e}")
                
                # ========== ORDEN DE LABORATORIO (carrito LIMS v7.5) ==========
                estudio_ids = request.POST.getlist('estudio_id[]')
                if estudio_ids:
                    try:
                        from decimal import ROUND_HALF_UP

                        raw_tokens = []
                        for est_id in estudio_ids:
                            if str(est_id).strip().isdigit():
                                raw_tokens.append(int(est_id))
                            else:
                                raw_tokens.append(est_id)
                        lineas = resolve_lims_cart_ids(raw_tokens, empresa=empresa)
                        if lineas:
                            total_orden = Decimal('0.00')
                            for row in lineas:
                                total_orden += aplicar_precio_convenio(
                                    row['precio_base'], row['precio_key'], {}, Decimal('0')
                                )
                            total_orden = total_orden.quantize(
                                Decimal('0.01'), rounding=ROUND_HALF_UP
                            )
                            urgencia_form = request.POST.get('urgencia_estudios', 'NORMAL')
                            tipo_srv = 'URGENCIA' if urgencia_form == 'URGENCIA' else 'RUTINA'

                            orden = OrdenDeServicio.objects.create(
                                empresa=empresa,
                                paciente=cita.paciente,
                                medico_referente=cita.medico,
                                tipo_servicio=tipo_srv,
                                diagnostico=consulta.diagnostico_principal or '',
                                estado='PENDIENTE_PAGO',
                                total=total_orden,
                                responsable_ingreso=request.user,
                            )

                            for row in lineas:
                                precio_momento = aplicar_precio_convenio(
                                    row['precio_base'], row['precio_key'], {}, Decimal('0')
                                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                                desc = (row.get('descripcion_linea') or '')[:300]
                                DetalleOrden.objects.create(
                                    orden=orden,
                                    analito=row['analito'],
                                    perfil_lims=row['perfil_lims'],
                                    paquete_lims=row['paquete_lims'],
                                    descripcion_linea=desc,
                                    precio_momento=precio_momento,
                                )
                            registrar_auditoria(
                                accion='CREATE',
                                modelo='OrdenDeServicio',
                                objeto_id=str(orden.id),
                                datos_nuevos={
                                    'folio_orden': getattr(orden, 'folio_orden', None),
                                    'paciente_id': orden.paciente_id,
                                    'cita_id': cita.id,
                                    'total': str(orden.total),
                                    'lineas_lims': len(lineas),
                                },
                                request=request,
                            )
                            messages.success(
                                request,
                                f'Orden de laboratorio generada con {len(lineas)} línea(s) LIMS',
                            )
                    except (DatabaseError, ValidationError, ValueError, TypeError) as e:
                        logging.getLogger('consultorio').error(
                            "Error generando orden de laboratorio: %s", e, exc_info=True
                        )
                
                messages.success(request, f'Consulta guardada exitosamente')
                
                if request.POST.get('accion') == 'finalizar':
                    return redirect('consultorio:lista_trabajo_medico')
                else:
                    return redirect('consultorio:nueva_consulta_soap', cita_id=cita.id)
                
        except (DatabaseError, ValidationError) as e:
            messages.error(request, f'Error al guardar consulta: {str(e)}')
        finally:
            # Liberar el bloqueo anti-doble-envío siempre (éxito o error)
            request.session.pop(_lock_key, None)

    # GET: Mostrar formulario
    # Consultas previas del paciente para referencia (scope por empresa)
    consultas_previas = ConsultaMedica.objects.filter(
        paciente=cita.paciente,
        empresa=empresa,
        estado='FINALIZADA'
    ).select_related('medico').order_by('-fecha_consulta')[:5]
    
    return render(request, 'consultorio/nueva_consulta_soap.html', {
        'cita': cita,
        'consulta': consulta,
        'signos_vitales': signos_vitales,
        'signos_vitales_existen': signos_vitales_existen,
        'historia_clinica': historia_clinica,
        'consultas_previas': consultas_previas,
    })


@login_required
def nueva_consulta_simplificada(request):
    """
    PASO 1: Pantalla de busqueda de paciente.
    La doctora PRIMERO busca o crea al paciente.
    Al seleccionarlo, redirige a la consulta con UUID en la URL.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    
    pacientes_recientes = Paciente.objects.filter(
        empresa=empresa, activo=True
    ).exclude(uuid__isnull=True).order_by('-id')[:12]
    
    # Fix: asignar UUID a pacientes que no lo tengan
    sin_uuid = Paciente.objects.filter(empresa=empresa, uuid__isnull=True)
    for p in sin_uuid:
        p.uuid = uuid_lib.uuid4()
        p.save(update_fields=['uuid'])
    
    return render(request, 'consultorio/buscar_paciente_consulta.html', {
        'pacientes_recientes': pacientes_recientes,
        'empresa': empresa,
    })


@login_required
def nueva_consulta_con_paciente(request, paciente_uuid):
    """
    PASOS 2-3-4: Consulta medica con paciente ya identificado.
    
    GET  -> Muestra formulario SOAP con encabezado del paciente (readonly).
    POST -> Guarda la consulta vinculada al paciente por UUID.
    
    URL: /consultorio/medico/consulta/nueva/<uuid>/
    REGLA: Si no hay UUID valido, NO se puede continuar.
    """
    # PASO 2: VALIDACION DE IDENTIDAD (multi-tenant: scope by empresa)
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    paciente = get_object_or_404(Paciente, uuid=paciente_uuid, empresa=empresa, activo=True)
    
    # Obtener medico - buscar por FirmaDigital primero, luego cedula_interna
    medico = None
    if hasattr(request.user, 'medico_profile'):
        medico = request.user.medico_profile
    
    if not medico:
        # Buscar por FirmaDigital vinculada al usuario
        try:
            from core.models import FirmaDigital
            firma = FirmaDigital.objects.filter(medico=request.user, activa=True).first()
            if firma and firma.cedula_profesional:
                medico = Medico.objects.filter(
                    cedula_profesional=firma.cedula_profesional, empresa=empresa
                ).first()
        except (DatabaseError, ValidationError, ObjectDoesNotExist):
            pass

    if not medico:
        # Buscar por cedula_interna del usuario — acotado por empresa
        cedula = getattr(request.user, 'cedula_interna', None)
        if cedula:
            medico = Medico.objects.filter(cedula_profesional=cedula, empresa=empresa).first()
    
    if not medico:
        # Último recurso: crear con datos del usuario (scope por empresa)
        nombre = request.user.get_full_name() or request.user.username
        cedula = getattr(request.user, 'cedula_interna', None) or f'USR-{request.user.id}'
        medico, _ = Medico.objects.get_or_create(
            cedula_profesional=cedula,
            empresa=empresa,
            defaults={
                'nombre_completo': nombre,
                'especialidad': 'Medico General',
                'empresa': empresa,
            }
        )
    
    # PASO 4: GUARDADO (POST)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Crear cita (registro administrativo)
                cita = CitaMedica.objects.create(
                    empresa=empresa,
                    sucursal=get_request_sucursal(request),
                    paciente=paciente,
                    medico=medico,
                    fecha_cita=timezone.localdate(),
                    hora_cita=timezone.localtime().time(),
                    duracion_estimada=30,
                    motivo=request.POST.get('motivo', 'Consulta general'),
                    estado='COMPLETADA'
                )
                
                # Crear signos vitales (si se proporcionaron) — modelo: pa_sistolica/pa_diastolica, no presion_arterial
                signos = None
                peso = _dec_or_none(request.POST.get('peso'))
                talla = _dec_or_none(request.POST.get('talla'))
                if peso or talla:
                    pa_raw = (request.POST.get('presion_arterial') or '').strip().replace(',', '.').split('/')
                    pa_sist = _int_or_none(pa_raw[0].strip()) if len(pa_raw) >= 1 else None
                    pa_diast = _int_or_none(pa_raw[1].strip()) if len(pa_raw) >= 2 else None
                    signos = SignosVitales(
                        paciente=paciente,
                        empresa=empresa,
                        cita=cita,
                        registrado_por=request.user,
                        presion_arterial_sistolica=pa_sist or 0,
                        presion_arterial_diastolica=pa_diast or 0,
                        frecuencia_cardiaca=_int_or_none(request.POST.get('frecuencia_cardiaca')) or 0,
                        frecuencia_respiratoria=_int_or_none(request.POST.get('frecuencia_respiratoria')) or 0,
                        temperatura=_dec_or_none(request.POST.get('temperatura')) or Decimal('36.5'),
                        peso=peso or Decimal('0'),
                        talla=talla or Decimal('0'),
                        saturacion_oxigeno=_int_or_none(request.POST.get('saturacion') or request.POST.get('saturacion_oxigeno')),
                    )
                    signos.save()
                
                # Crear consulta medica (SOAP)
                consulta = ConsultaMedica.objects.create(
                    empresa=empresa,
                    sucursal=get_request_sucursal(request),
                    paciente=paciente,
                    medico=medico,
                    cita=cita,
                    signos_vitales=signos,
                    tipo_consulta='SUBSECUENTE' if paciente.consultas.exists() else 'PRIMERA_VEZ',
                    estado='FINALIZADA',
                    motivo_consulta=request.POST.get('motivo', ''),
                    padecimiento_actual=request.POST.get('motivo', ''),
                    exploracion_fisica=request.POST.get('exploracion_fisica', ''),
                    diagnostico_principal=request.POST.get('diagnostico', ''),
                    plan_tratamiento=request.POST.get('tratamiento', ''),
                )
                
                # Crear Receta si hay tratamiento prescrito
                tratamiento_texto = request.POST.get('tratamiento', '').strip()
                if tratamiento_texto:
                    ano = timezone.localtime(timezone.now()).year
                    prefijo_r = f'REC-{empresa.id}-{ano}-'
                    num_r = Receta.objects.filter(empresa=empresa, folio_receta__startswith=prefijo_r).count()
                    folio_receta = f'{prefijo_r}{str(num_r + 1).zfill(5)}'
                    receta = Receta.objects.create(
                        medico=medico,
                        paciente=paciente,
                        empresa=empresa,
                        sucursal=get_request_sucursal(request),
                        folio_receta=folio_receta,
                        diagnostico_principal=request.POST.get('diagnostico', 'Sin diagnóstico') or 'Sin diagnóstico',
                        indicaciones=tratamiento_texto,
                        medico_nombre_completo=medico.nombre_completo if medico else (request.user.get_full_name() or request.user.username),
                        medico_cedula=medico.cedula_profesional if medico else '',
                        medico_especialidad=medico.especialidad if medico else 'Médico General',
                        temperatura=_dec_or_none(request.POST.get('temperatura')),
                        peso=_dec_or_none(request.POST.get('peso')),
                        talla=_dec_or_none(request.POST.get('talla')),
                        frecuencia_cardiaca=_int_or_none(request.POST.get('frecuencia_cardiaca')),
                        saturacion_oxigeno=_int_or_none(request.POST.get('saturacion')),
                    )
                    # Vincular receta a la consulta
                    consulta.receta = receta
                    consulta.save(update_fields=['receta'])

                # Registrar trazabilidad
                registrar_trazabilidad(
                    tipo_operacion='CONSULTA',
                    modulo='CONSULTORIO',
                    referencia_id=consulta.id,
                    referencia_tipo='ConsultaMedica',
                    accion='CREAR',
                    descripcion=f'Consulta {consulta.folio_consulta} - {paciente.nombre_completo}',
                    usuario=request.user,
                    empresa=empresa,
                    datos_anteriores={},
                    datos_nuevos={'folio': consulta.folio_consulta, 'paciente': paciente.nombre_completo}
                )
                
                messages.success(request, f'Consulta {consulta.folio_consulta} guardada correctamente.')
                
                # Si hay tratamiento, ir directo al PDF de receta
                if tratamiento_texto and consulta.receta_id:
                    return redirect('consultorio:pdf_receta_paciente', consulta_id=consulta.id)
                
                return redirect('consultorio:dashboard_consultorio')
                
        except (DatabaseError, ValidationError) as e:
            messages.error(request, f'Error al guardar consulta: {e}')
    
    # PASO 3: MOSTRAR FORMULARIO (GET)
    consultas_previas = paciente.consultas.order_by('-fecha_consulta')[:5]
    
    return render(request, 'consultorio/nueva_consulta_gemelo.html', {
        'paciente': paciente,
        'empresa': empresa,
        'medico': medico,
        'consultas_previas': consultas_previas,
        'paciente_vinculado': True,  # Flag para el template
    })
