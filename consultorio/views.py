"""
VISTAS DEL MÓDULO DE CONSULTORIO MÉDICO
Sistema Adaptativo Híbrido (NOM-004-SSA3-2012)
Soporta flujo con y sin enfermera
"""
from datetime import date, datetime, timedelta
import json
import logging
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth.decorators import login_required, permission_required
from core.decorators import role_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.http import Http404, JsonResponse
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from core.models import (
    Paciente, OrdenDeServicio, DetalleOrden,
    Empresa, Medico, Usuario, Receta, RecetaItem, Producto,
    CitaMedica, HistoriaClinica, SignosVitales, ConsultaMedica, CertificadoMedico,
    HistorialCambiosConsulta,
)
from core.lims_cart import resolve_lims_cart_ids, aplicar_precio_convenio
from core.utils.trazabilidad import registrar_trazabilidad, serializar_modelo
from core.services.audit_service import registrar_auditoria
from core.utils.empresa_request import empresa_efectiva_request

logger = logging.getLogger('consultorio')


def _empresa_explicita_usuario(request):
    """Empresa del usuario para APIs tenant-sensitive; no usa fallback del middleware."""
    if not getattr(request, 'user', None) or not getattr(request.user, 'is_authenticated', False):
        return None
    if not getattr(request.user, 'empresa_id', None):
        return None
    return empresa_efectiva_request(request)


def _resolver_medico_usuario(request, empresa, *, medico_preferido=None, autocrear=False):
    """
    Resuelve el médico operativo del usuario actual sin caer en el "primer médico"
    de la empresa, para evitar certificados, recetas u órdenes firmadas por la
    persona equivocada.
    """
    if not empresa or not getattr(request, 'user', None) or not request.user.is_authenticated:
        return None

    if medico_preferido and getattr(medico_preferido, 'empresa_id', None) == empresa.id:
        return medico_preferido

    medico_profile = getattr(request.user, 'medico_profile', None)
    if medico_profile and getattr(medico_profile, 'empresa_id', None) == empresa.id:
        return medico_profile

    nombre_usuario = (request.user.get_full_name() or '').strip()
    if nombre_usuario:
        medico = Medico.objects.filter(
            empresa=empresa,
            activo=True,
            nombre_completo__iexact=nombre_usuario,
        ).first()
        if medico:
            return medico

    cedula_usuario = getattr(request.user, 'cedula_interna', None)
    if isinstance(cedula_usuario, str):
        cedula_usuario = cedula_usuario.strip()
    if cedula_usuario:
        medico = Medico.objects.filter(
            empresa=empresa,
            cedula_profesional=cedula_usuario,
        ).first()
        if medico:
            return medico

    if not autocrear:
        return None

    medico, _ = Medico.objects.get_or_create(
        empresa=empresa,
        cedula_profesional=cedula_usuario or f'USR-{request.user.id}',
        defaults={
            'nombre_completo': nombre_usuario or request.user.username,
            'especialidad': 'Médico General',
            'empresa': empresa,
        }
    )
    return medico


# =====================================================================
# HELPERS para conversión segura de POST values
# =====================================================================
def _int_or_none(val):
    """Convierte a int de forma segura. Retorna None si no es posible."""
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def _dec_or_none(val):
    """Convierte a Decimal de forma segura. Retorna None si no es posible."""
    try:
        if val is not None and isinstance(val, str):
            val = val.strip()
        return Decimal(val) if val else None
    except Exception:
        return None


def _int_in_range(val, min_val, max_val):
    """Convierte a int y lo acota a [min_val, max_val]. Retorna None si no es posible."""
    n = _int_or_none(val)
    if n is None:
        return None
    if min_val is not None and n < min_val:
        return None
    if max_val is not None and n > max_val:
        return None
    return n


def _dec_in_range(val, min_val, max_val):
    """Convierte a Decimal y lo acota a [min_val, max_val]. Retorna None si no es posible."""
    d = _dec_or_none(val)
    if d is None:
        return None
    if min_val is not None and d < min_val:
        return None
    if max_val is not None and d > max_val:
        return None
    return d


# Rangos clínicamente razonables para signos vitales (CICLO 6)
_SV_PA_SIS_MIN, _SV_PA_SIS_MAX = 50, 300
_SV_PA_DIA_MIN, _SV_PA_DIA_MAX = 30, 200
_SV_FC_MIN, _SV_FC_MAX = 20, 300
_SV_FR_MIN, _SV_FR_MAX = 5, 60
_SV_TEMP_MIN, _SV_TEMP_MAX = Decimal('32'), Decimal('45')
_SV_PESO_MIN, _SV_PESO_MAX = Decimal('2'), Decimal('500')
_SV_TALLA_MIN, _SV_TALLA_MAX = Decimal('0.3'), Decimal('2.5')
_SV_SPO2_MIN, _SV_SPO2_MAX = 0, 100
_SV_GLUC_MIN, _SV_GLUC_MAX = Decimal('0'), Decimal('600')


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
                sucursal=getattr(request.user, 'sucursal', None),
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
        except Exception as e:
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
                
        except Exception as e:
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
                    sucursal=getattr(request.user, 'sucursal', None),
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
                
        except Exception as e:
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
            sucursal=getattr(request.user, 'sucursal', None),
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
                except Exception:
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
                        except Exception as e:
                            logger = logging.getLogger('consultorio')
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
                        fecha_fin_cert = fecha_ini_cert + timedelta(days=dias_inc_cert) if dias_inc_cert else fecha_ini_cert
                        
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
                    except Exception as e:
                        logger = logging.getLogger('consultorio')
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
                    except Exception as e:
                        logging.getLogger('consultorio').error(
                            "Error generando orden de laboratorio: %s", e, exc_info=True
                        )
                
                messages.success(request, f'Consulta guardada exitosamente')
                
                if request.POST.get('accion') == 'finalizar':
                    return redirect('consultorio:lista_trabajo_medico')
                else:
                    return redirect('consultorio:nueva_consulta_soap', cita_id=cita.id)
                
        except Exception as e:
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


# ==============================================================================
# HISTORIAL Y REPORTES
# ==============================================================================

@login_required
def historial_clinico_paciente(request, paciente_id):
    """
    Historial completo de consultas del paciente.
    Timeline con todas las consultas.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    
    # Historia clínica
    try:
        historia_clinica = paciente.historia_clinica
    except HistoriaClinica.DoesNotExist:
        historia_clinica = None
    
    # Consultas ordenadas por fecha
    consultas = ConsultaMedica.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).select_related('medico', 'signos_vitales', 'receta').order_by('-fecha_consulta')
    
    # Recetas y órdenes de lab del paciente (para historial completo)
    recetas = Receta.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).select_related('medico').order_by('-id')[:30]
    
    ordenes_lab = OrdenDeServicio.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).order_by('-id')[:30]
    
    certificados = CertificadoMedico.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).select_related('medico', 'consulta').order_by('-fecha_emision')[:30]
    
    return render(request, 'consultorio/historial_clinico_paciente.html', {
        'paciente': paciente,
        'historia_clinica': historia_clinica,
        'consultas': consultas,
        'recetas': recetas,
        'ordenes_lab': ordenes_lab,
        'certificados': certificados,
    })


@login_required
def dashboard_consultorio(request):
    """
    Dashboard principal del consultorio con estadísticas.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    hoy = timezone.localdate()
    
    # Citas del día (opcional: filtrar por búsqueda q)
    citas_hoy = CitaMedica.objects.filter(
        empresa=empresa,
        fecha_cita=hoy
    ).select_related('paciente', 'medico').order_by('hora_cita')
    query = (request.GET.get('q') or '').strip()
    if query:
        q_filter = (
            Q(paciente__nombre_completo__icontains=query) |
            Q(paciente__telefono__icontains=query) |
            Q(paciente__nombres__icontains=query) |
            Q(paciente__apellido_paterno__icontains=query)
        )
        if query.isdigit():
            q_filter |= Q(paciente__id=query)
        citas_hoy = citas_hoy.filter(q_filter)
    
    # Estadísticas del mes
    inicio_mes = hoy.replace(day=1)
    stats_mes = {
        'consultas': ConsultaMedica.objects.filter(
            empresa=empresa,
            fecha_consulta__date__gte=inicio_mes,
            estado='FINALIZADA'
        ).count(),
        'ingresos': ConsultaMedica.objects.filter(
            empresa=empresa,
            fecha_consulta__date__gte=inicio_mes,
            estado='FINALIZADA',
            pagada=True
        ).aggregate(total=Sum('precio_consulta'))['total'] or 0,
    }
    
    return render(request, 'consultorio/dashboard_consultorio.html', {
        'hoy': hoy,
        'citas_hoy': citas_hoy,
        'stats_mes': stats_mes,
        'query': query,
    })


# ==============================================================================
# CERTIFICADOS MÉDICOS
# ==============================================================================

@login_required
@permission_required('core.generar_certificado', raise_exception=True)
def generar_certificado(request, consulta_id=None):
    """
    Generar certificado médico (Incapacidad, Aptitud, etc.).
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    consulta = None
    
    if consulta_id:
        consulta = get_object_or_404(ConsultaMedica, id=consulta_id, empresa=empresa)
    
    if request.method == 'POST':
        try:
            paciente_id = request.POST.get('paciente_id')
            medico_id = request.POST.get('medico_id')
            
            paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
            medico = get_object_or_404(Medico, id=medico_id, empresa=empresa)
            
            fecha_inicio_str = request.POST.get('fecha_inicio')
            if not fecha_inicio_str:
                raise ValueError('La fecha de inicio es obligatoria.')
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            
            descripcion = request.POST.get('observaciones', '').strip() or request.POST.get('descripcion', '')
            
            certificado = CertificadoMedico(
                empresa=empresa,
                paciente=paciente,
                medico=medico,
                consulta=consulta,
                tipo_certificado=request.POST.get('tipo_certificado'),
                diagnostico=request.POST.get('diagnostico', ''),
                descripcion=descripcion or 'Certificado médico.',
                fecha_inicio=fecha_inicio,
            )
            
            if request.POST.get('dias_incapacidad'):
                dias_val = _int_or_none(request.POST.get('dias_incapacidad'))
                if dias_val is not None:
                    certificado.dias_incapacidad = dias_val
            
            if request.POST.get('fecha_fin'):
                try:
                    certificado.fecha_fin = datetime.strptime(request.POST.get('fecha_fin'), '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
            
            certificado.save()

            registrar_auditoria(
                accion='CREATE',
                modelo='CertificadoMedico',
                objeto_id=str(certificado.id),
                datos_nuevos={
                    'folio': certificado.folio_certificado,
                    'tipo': certificado.tipo_certificado,
                    'paciente_id': certificado.paciente_id,
                    'medico_id': certificado.medico_id,
                },
                request=request,
            )
            
            messages.success(request, f'Certificado {certificado.folio_certificado} generado exitosamente')
            return redirect('consultorio:ver_certificado', certificado_id=certificado.id)
            
        except Exception as e:
            messages.error(request, f'Error al generar certificado: {str(e)}')
    
    pacientes = Paciente.objects.filter(empresa=empresa, activo=True).order_by('nombres', 'apellido_paterno')
    medicos = Medico.objects.filter(empresa=empresa) if empresa else Medico.objects.none()
    
    return render(request, 'consultorio/generar_certificado.html', {
        'consulta': consulta,
        'pacientes': pacientes,
        'medicos': medicos,
    })


@login_required
def ver_certificado(request, certificado_id):
    """Ver certificado médico generado."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    certificado = get_object_or_404(CertificadoMedico, id=certificado_id, empresa=empresa)
    
    return render(request, 'consultorio/ver_certificado.html', {
        'certificado': certificado,
    })


@login_required
def ver_consulta_detalle(request, consulta_id):
    """
    Ver detalle de una consulta (por ID). Usado desde lista de trabajo cuando la consulta no tiene cita.
    Si la consulta tiene cita, redirige a nueva_consulta_soap para edición.
    Multi-tenant: no usar Empresa.objects.first(); 403/redirect si no hay empresa.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('consultorio:lista_trabajo_medico')
    consulta = get_object_or_404(ConsultaMedica, id=consulta_id, empresa=empresa)
    if consulta.cita_id:
        return redirect('consultorio:nueva_consulta_soap', cita_id=consulta.cita_id)
    return render(request, 'consultorio/ver_consulta_detalle.html', {
        'consulta': consulta,
    })


# ==============================================================================
# NUEVA CONSULTA - FLUJO SIMPLIFICADO
# ==============================================================================

@login_required
def nueva_consulta_simplificada(request):
    """
    PASO 1: Pantalla de busqueda de paciente.
    La doctora PRIMERO busca o crea al paciente.
    Al seleccionarlo, redirige a la consulta con UUID en la URL.
    """
    import uuid as uuid_lib
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
        except Exception:
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
                    sucursal=getattr(request.user, 'sucursal', None),
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
                    sucursal=getattr(request.user, 'sucursal', None),
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
                        sucursal=getattr(request.user, 'sucursal', None),
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
                
        except Exception as e:
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


@login_required
@require_http_methods(["POST"])
def api_crear_consulta_directa(request):
    """
    API para crear consulta con paciente existente.
    Redirige directamente a la consulta SOAP.
    """
    try:
        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'mensaje': 'JSON inválido'}, status=400)
        
        paciente_id = data.get('paciente_id')
        motivo = data.get('motivo', 'Consulta general')
        
        empresa = _empresa_explicita_usuario(request)
        if not empresa:
            return JsonResponse({'ok': False, 'mensaje': 'Usuario sin empresa asignada'}, status=403)
        
        if paciente_id is None or paciente_id == '':
            return JsonResponse({'ok': False, 'mensaje': 'paciente_id es requerido'}, status=400)
        
        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
        
        # Obtener médico (scope por empresa)
        medico = _resolver_medico_usuario(request, empresa, autocrear=True)

        # Crear cita en curso
        with transaction.atomic():
            cita = CitaMedica.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, 'sucursal', None),
                paciente=paciente,
                medico=medico,
                fecha_cita=timezone.localdate(),
                hora_cita=timezone.localtime().time(),
                duracion_estimada=30,
                motivo=motivo,
                estado='EN_CURSO'
            )

            ConsultaMedica.objects.get_or_create(
                cita=cita,
                defaults={
                    'empresa': empresa,
                    'sucursal': getattr(request.user, 'sucursal', None),
                    'paciente': paciente,
                    'medico': medico,
                    'tipo_consulta': 'SUBSECUENTE' if paciente.consultas.exists() else 'PRIMERA_VEZ',
                    'estado': 'EN_CURSO',
                    'motivo_consulta': motivo,
                    'padecimiento_actual': motivo,
                    'diagnostico_principal': 'En proceso',
                    'plan_tratamiento': '',
                }
            )
            
            return JsonResponse({
                'ok': True,
                'mensaje': 'Consulta creada exitosamente',
                'cita_id': cita.id,
                'paciente': paciente.nombre_completo
            })
            
    except Http404:
        return JsonResponse({'ok': False, 'mensaje': 'Paciente no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'mensaje': f'Error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_crear_paciente_y_consulta(request):
    """
    API para crear paciente nuevo + consulta automáticamente.
    Flujo simplificado para médicos sin enfermero.
    """
    try:
        import json
        from datetime import datetime as dt
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'mensaje': 'JSON inválido'}, status=400)
        
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'mensaje': 'Usuario sin empresa asignada'}, status=403)
        
        # Validar datos mínimos
        nombre = data.get('nombre', '').strip()
        apellidos = data.get('apellidos', '').strip()
        fecha_nacimiento = data.get('fecha_nacimiento')
        sexo = data.get('sexo')
        
        if not all([nombre, apellidos, fecha_nacimiento, sexo]):
            return JsonResponse({
                'ok': False,
                'mensaje': 'Faltan datos obligatorios (nombre, apellidos, fecha de nacimiento, sexo)'
            }, status=400)
        
        # Calcular edad (validar formato de fecha)
        try:
            fecha_nac = dt.strptime(fecha_nacimiento, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return JsonResponse({
                'ok': False,
                'mensaje': 'fecha_nacimiento debe tener formato AAAA-MM-DD'
            }, status=400)
        hoy = date.today()
        # CICLO 6: Validar fecha de nacimiento razonable (no futura, no antes de 1900)
        if fecha_nac > hoy:
            return JsonResponse({
                'ok': False,
                'mensaje': 'La fecha de nacimiento no puede ser futura.'
            }, status=400)
        if fecha_nac < date(1900, 1, 1):
            return JsonResponse({
                'ok': False,
                'mensaje': 'La fecha de nacimiento debe ser posterior a 1900.'
            }, status=400)
        edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        
        # Obtener médico (scope por empresa)
        medico = _resolver_medico_usuario(request, empresa, autocrear=True)
        
        # Crear paciente + consulta en una transacción
        with transaction.atomic():
            # Crear paciente (CICLO 6: usar fecha_nac ya validada, no string crudo)
            nombre_completo = f"{nombre} {apellidos}".strip()
            paciente = Paciente.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, 'sucursal', None),
                nombre_completo=nombre_completo,
                fecha_nacimiento=fecha_nac,
                sexo=sexo,
                telefono=data.get('telefono', ''),
                email=data.get('email', ''),
                tipo='GENERAL'  # Corregido: tipo en lugar de tipo_paciente
            )
            
            # Crear consulta inmediatamente
            cita = CitaMedica.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, 'sucursal', None),
                paciente=paciente,
                medico=medico,
                fecha_cita=timezone.localdate(),
                hora_cita=timezone.localtime().time(),
                duracion_estimada=30,
                motivo=data.get('motivo', 'Consulta general'),
                estado='EN_CURSO'
                # Nota: tipo_consulta no existe en CitaMedica, se eliminó
            )

            ConsultaMedica.objects.get_or_create(
                cita=cita,
                defaults={
                    'empresa': empresa,
                    'sucursal': getattr(request.user, 'sucursal', None),
                    'paciente': paciente,
                    'medico': medico,
                    'tipo_consulta': 'PRIMERA_VEZ',
                    'estado': 'EN_CURSO',
                    'motivo_consulta': data.get('motivo', 'Consulta general'),
                    'padecimiento_actual': data.get('motivo', 'Consulta general'),
                    'diagnostico_principal': 'En proceso',
                    'plan_tratamiento': '',
                }
            )
            
            return JsonResponse({
                'ok': True,
                'mensaje': 'Paciente y consulta creados exitosamente',
                'cita_id': cita.id,
                'paciente_id': paciente.id,
                'paciente': paciente.nombre_completo
            })
            
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'mensaje': f'Error al crear paciente: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(['GET'])
def api_buscar_pacientes(request):
    """
    API para buscar pacientes en tiempo real.
    Responde con JSON incluyendo UUID para navegacion.
    """
    termino = request.GET.get('q', '').strip()
    empresa = _empresa_explicita_usuario(request)
    if not empresa:
        return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada', 'pacientes': []}, status=403)
    
    if len(termino) < 2:
        return JsonResponse({'success': True, 'pacientes': []})
    
    import uuid as uuid_lib
    
    # Auto-asignar UUID a pacientes que no lo tengan (para que sean navegables)
    sin_uuid = Paciente.objects.filter(empresa=empresa, activo=True, uuid__isnull=True)
    for p in sin_uuid[:50]:
        p.uuid = uuid_lib.uuid4()
        p.save(update_fields=['uuid'])
    
    pacientes = Paciente.objects.filter(
        empresa=empresa,
        activo=True,
    ).exclude(uuid__isnull=True).filter(
        Q(nombre_completo__icontains=termino) |
        Q(telefono__icontains=termino)
    ).order_by('nombre_completo')[:10]
    
    resultados = [{
        'id': p.id,
        'uuid': str(p.uuid),
        'nombre_completo': p.nombre_completo,
        'edad': p.edad,
        'sexo_display': p.get_sexo_display() if p.sexo else '--',
        'telefono': p.telefono or '',
    } for p in pacientes]
    
    return JsonResponse({'success': True, 'pacientes': resultados})


# ==============================================================================
# API: TRANSCRIPCIÓN INTELIGENTE CON IA
# ==============================================================================

@login_required
@require_http_methods(['POST'])
def api_analizar_transcripcion(request):
    """
    MOTOR IA SOAP INTELIGENTE (Botón Único)
    ========================================
    Analiza la transcripción completa de una consulta y DETECTA AUTOMÁTICAMENTE
    a qué campo SOAP pertenece cada pieza de información.
    
    El médico solo habla una vez → la IA clasifica todo.
    
    Recibe:
    - transcripcion_completa: Texto completo de la consulta
    - cita_id: ID de la cita (opcional, para guardar transcripción)
    
    Retorna:
    - Campos SOAP extraídos y clasificados automáticamente
    - Transcripción guardada como respaldo legal (NOM-004-SSA3-2012)
    """
    try:
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
        transcripcion = data.get('transcripcion_completa', '').strip()
        cita_id = data.get('cita_id')
        
        if not transcripcion:
            return JsonResponse({
                'ok': False,
                'error': 'No se recibio transcripcion'
            }, status=400)
        
        from core.utils.gemini_client import generate_content
        
        # =====================================================
        # PROMPT MAESTRO: CLASIFICACIÓN SOAP INTELIGENTE
        # =====================================================
        prompt = f"""
Eres un asistente médico experto y altamente preciso. Tu tarea es analizar la
transcripción de una consulta médica donde el doctor habla libremente, y
CLASIFICAR AUTOMÁTICAMENTE cada fragmento de información en su campo SOAP correcto.

TRANSCRIPCIÓN COMPLETA DE LA CONSULTA:
---
{transcripcion}
---

REGLAS DE CLASIFICACIÓN (OBLIGATORIAS):
1. motivo_consulta: Lo que el PACIENTE reporta como razón de su visita (síntomas iniciales)
2. padecimiento_actual: Historia del padecimiento actual, evolución de síntomas,
   cuándo empezó, qué ha tomado, cómo ha progresado
3. exploracion_fisica: Lo que el MÉDICO observa, palpa, ausculta (hallazgos objetivos).
   Incluye: "a la exploración se encuentra...", "campos pulmonares...", "abdomen...",
   "faringe...", "se observa...", datos de la exploración clínica
4. diagnostico_principal: El diagnóstico final o presuntivo que el médico da
5. diagnostico_cie10: Código CIE-10 si se menciona (ej: J06.9, E11, K29.7).
   Si el diagnóstico es claro pero no se da código, SUGIERE uno.
6. diagnosticos_secundarios: Otros diagnósticos mencionados
7. plan_tratamiento: Medicamentos prescritos con dosis, frecuencia, duración.
   Incluye indicaciones como: reposo, dieta, hidratación, medidas generales
8. estudios_solicitados: Labs, rayos X, ultrasonidos o cualquier estudio solicitado
9. pronostico: Debe ser uno de: EXCELENTE, BUENO, REGULAR, RESERVADO, MALO
10. medicamentos_detectados: Lista de medicamentos mencionados, cada uno con:
    nombre, dosis, frecuencia, duracion, via (si se menciona)

FORMATO DE RESPUESTA (JSON ESTRICTO):
{{
  "motivo_consulta": "...",
  "padecimiento_actual": "...",
  "exploracion_fisica": "...",
  "diagnostico_principal": "...",
  "diagnostico_cie10": "...",
  "diagnosticos_secundarios": "...",
  "plan_tratamiento": "...",
  "estudios_solicitados": "...",
  "pronostico": "BUENO",
  "medicamentos_detectados": [
    {{
      "nombre": "Paracetamol",
      "dosis": "500mg",
      "frecuencia": "cada 8 horas",
      "duracion": "5 días",
      "via": "oral"
    }}
  ],
  "signos_vitales_detectados": {{
    "temperatura": null,
    "frecuencia_cardiaca": null,
    "presion_arterial": null,
    "peso": null,
    "talla": null,
    "saturacion": null
  }}
}}

REGLAS CRÍTICAS:
- NO inventes información que no esté en la transcripción
- Si un campo no tiene datos, usa "" (string vacío) o null para numéricos
- Sé preciso con los términos médicos
- Conserva los nombres comerciales Y genéricos de los medicamentos
- Si se menciona CIE-10, úsalo; si no, sugiere el más probable
- RESPONDE SOLO CON EL JSON, sin texto adicional ni backticks
"""
        
        try:
            respuesta_texto = generate_content(
                prompt,
                model_name='gemini-2.0-flash',
                temperature=0.2,
                max_tokens=2000,
            ).strip()
        except Exception as ia_error:
            logging.getLogger('consultorio').warning(
                'IA de transcripcion no disponible, usando fallback local: %s',
                ia_error,
            )
            campos_soap = {
                "motivo_consulta": transcripcion[:500],
                "padecimiento_actual": transcripcion,
                "exploracion_fisica": "",
                "diagnostico_principal": "",
                "diagnostico_cie10": "",
                "diagnosticos_secundarios": "",
                "plan_tratamiento": "",
                "estudios_solicitados": "",
                "pronostico": "BUENO",
                "medicamentos_detectados": [],
                "signos_vitales_detectados": {
                    "temperatura": None,
                    "frecuencia_cardiaca": None,
                    "presion_arterial": None,
                    "peso": None,
                    "talla": None,
                    "saturacion": None,
                },
            }
            respuesta_texto = json.dumps(campos_soap)
        
        # Limpiar respuesta si tiene markdown
        if respuesta_texto.startswith('```'):
            respuesta_texto = respuesta_texto.split('```')[1]
            if respuesta_texto.startswith('json'):
                respuesta_texto = respuesta_texto[4:]
            respuesta_texto = respuesta_texto.strip()
        
        # Parsear JSON
        campos_soap = json.loads(respuesta_texto)
        
        # =====================================================
        # GUARDAR TRANSCRIPCIÓN (Respaldo legal NOM-004) — scope por empresa
        # =====================================================
        transcripcion_guardada = False
        if cita_id:
            try:
                cita = CitaMedica.objects.filter(id=cita_id, empresa=empresa).first()
                consulta_tr = ConsultaMedica.objects.filter(cita=cita).first() if cita else None
                if consulta_tr:
                    consulta_tr.transcripcion_completa = transcripcion
                    consulta_tr.save(update_fields=['transcripcion_completa'])
                    transcripcion_guardada = True
            except Exception as e:
                logging.getLogger('consultorio').error(f'Error guardando transcripcion: {e}', exc_info=True)

        return JsonResponse({
            'ok': True,
            'campos_soap': campos_soap,
            'transcripcion_guardada': transcripcion_guardada,
            'mensaje': 'Campos SOAP extraidos y clasificados exitosamente',
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({
            'ok': False,
            'error': f'Error parseando JSON de IA: {str(e)}',
            'respuesta_ia': respuesta_texto if 'respuesta_texto' in locals() else ''
        }, status=500)
        
    except Exception as e:
        logger = logging.getLogger('consultorio')
        logger.error(f"Error en analisis de transcripcion: {e}")
        return JsonResponse({
            'ok': False,
            'error': f'Error procesando transcripcion: {str(e)}'
        }, status=500)


# ==============================================================================
# API: GENERACIÓN INMEDIATA DE RECETA
# ==============================================================================

@login_required
@require_http_methods(['POST'])
def api_generar_receta_inmediata(request):
    """
    Genera una receta INMEDIATAMENTE sin esperar al final de la consulta.
    Más práctico para el flujo de trabajo del médico.
    """
    import uuid as _uuid
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
        cita_id = data.get('cita_id')
        medicamentos = data.get('medicamentos', [])
        
        if cita_id is None or cita_id == '':
            return JsonResponse({'ok': False, 'error': 'cita_id es requerido'}, status=400)
        if not medicamentos:
            return JsonResponse({
                'ok': False,
                'error': 'Debe agregar al menos un medicamento'
            }, status=400)
        
        # Multi-tenant: empresa obligatoria, cita filtrada por empresa
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)
        
        # Obtener médico
        medico = _resolver_medico_usuario(
            request,
            empresa,
            medico_preferido=cita.medico,
            autocrear=True,
        )
        
        # Crear o actualizar consulta
        consulta, created = ConsultaMedica.objects.get_or_create(
            cita=cita,
            defaults={
                'empresa': empresa,
                'medico': medico,
                'paciente': cita.paciente,
                'fecha_consulta': timezone.now(),
                'motivo_consulta': 'En proceso',
                'padecimiento_actual': '',
                'exploracion_fisica': '',
                'diagnostico_principal': 'En proceso',
                'plan_tratamiento': '',
            }
        )
        
        # Crear receta con campos reales del modelo
        with transaction.atomic():
            folio = f"RX-{cita_id}-{_uuid.uuid4().hex[:6].upper()}"
            receta = Receta.objects.create(
                empresa=empresa,
                medico=medico,
                paciente=cita.paciente,
                folio_receta=folio,
                diagnostico_principal=consulta.diagnostico_principal or 'En proceso',
                indicaciones=consulta.plan_tratamiento if hasattr(consulta, 'plan_tratamiento') and consulta.plan_tratamiento else '',
                medico_nombre_completo=medico.nombre_completo if medico else request.user.get_full_name(),
                medico_cedula=medico.cedula_profesional if medico else '',
                medico_especialidad=medico.especialidad if medico else 'Médico General',
            )
            
            # Crear items de receta con campos reales del modelo
            for med in medicamentos:
                nombre = med.get('nombre', '')
                dosis = med.get('dosis', '')
                duracion = med.get('duracion', '')
                try:
                    cant = int(med.get('cantidad', 1) or 1)
                except (ValueError, TypeError):
                    cant = 1
                
                # Buscar producto en catálogo
                med_producto = None
                if nombre:
                    med_producto = Producto.objects.filter(
                        nombre__icontains=nombre, empresa=empresa
                    ).first()
                
                # Componer texto_libre con información completa
                partes = [nombre]
                if dosis:
                    partes.append(f"Dosis: {dosis}")
                if duracion:
                    partes.append(f"Duración: {duracion}")
                texto = ' | '.join(partes)
                
                RecetaItem.objects.create(
                    receta=receta,
                    medicamento=med_producto,
                    texto_libre=texto,
                    cantidad=cant,
                )
            
            # Vincular receta a la consulta
            consulta.receta = receta
            consulta.save(update_fields=['receta'])
        
        url_pdf = request.build_absolute_uri(
            reverse('consultorio:pdf_receta_paciente', args=[consulta.id])
        )
        try:
            url_farmacia = request.build_absolute_uri(
                reverse('pdv_farmacia')
            ) + '?receta_id=' + str(receta.id)
        except Exception:
            url_farmacia = None
        return JsonResponse({
            'ok': True,
            'receta_id': receta.id,
            'url_pdf': url_pdf,
            'url_farmacia': url_farmacia,
            'mensaje': 'Receta generada exitosamente'
        })
        
    except Exception as e:
        logger = logging.getLogger('consultorio')
        logger.error(f"Error generando receta inmediata: {e}", exc_info=True)
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=500)


# ==============================================================================
# API: GENERACIÓN INMEDIATA DE CERTIFICADO
# ==============================================================================

@login_required
@require_http_methods(['POST'])
def api_generar_certificado_inmediato(request):
    """
    Genera un certificado médico INMEDIATAMENTE.
    """
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
        cita_id = data.get('cita_id')
        tipo = data.get('tipo')
        motivo = data.get('motivo') or data.get('diagnostico', '')
        recomendaciones = data.get('recomendaciones', '')
        dias_incapacidad = data.get('dias_incapacidad', 0)
        
        if not motivo:
            return JsonResponse({
                'ok': False,
                'error': 'Debe especificar el motivo o diagnóstico del certificado'
            }, status=400)
        
        if cita_id is None or cita_id == '':
            return JsonResponse({'ok': False, 'error': 'cita_id es requerido'}, status=400)
        
        # Multi-tenant: no fallback a primera empresa; scope estricto por usuario
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)

        # Obtener médico (filtrado por empresa)
        medico = _resolver_medico_usuario(
            request,
            empresa,
            medico_preferido=cita.medico,
            autocrear=True,
        )
        
        # Crear o actualizar consulta
        consulta, created = ConsultaMedica.objects.get_or_create(
            cita=cita,
            defaults={
                'empresa': empresa,
                'medico': medico,
                'paciente': cita.paciente,
                'fecha_consulta': timezone.now(),
                'motivo_consulta': motivo,
                'padecimiento_actual': '',
                'exploracion_fisica': '',
                'diagnostico_principal': motivo,
                'plan_tratamiento': '',
            }
        )
        
        # Crear certificado (sin fallback a primera empresa; ya validado empresa arriba)
        import uuid as _uuid
        empresa_cert = empresa
        fecha_inicio = timezone.now().date()
        dias_inc = _int_or_none(dias_incapacidad) or 0
        fecha_fin = fecha_inicio + timedelta(days=dias_inc) if dias_inc else fecha_inicio
        
        # Mapear tipo del template a TIPO_CHOICES del modelo
        tipo_map = {
            'MEDICO': 'SALUD',
            'INCAPACIDAD': 'INCAPACIDAD',
            'APTITUD': 'APTITUD',
            'DEFUNCION': 'DEFUNCION',
            'NACIMIENTO': 'NACIMIENTO',
        }
        tipo_cert = tipo_map.get(tipo, 'OTRO')
        folio_cert = f"CERT-{cita_id}-{_uuid.uuid4().hex[:6].upper()}"
        
        descripcion_texto = f"{motivo}. {recomendaciones}".strip() if recomendaciones else motivo
        certificado = CertificadoMedico.objects.create(
            empresa=empresa_cert,
            consulta=consulta,
            medico=medico,
            paciente=cita.paciente,
            folio_certificado=folio_cert,
            tipo_certificado=tipo_cert,
            diagnostico=consulta.diagnostico_principal if hasattr(consulta, 'diagnostico_principal') and consulta.diagnostico_principal else motivo,
            descripcion=descripcion_texto,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            dias_incapacidad=dias_inc if dias_inc else None,
        )
        
        registrar_auditoria(
            accion='CREATE',
            modelo='CertificadoMedico',
            objeto_id=str(certificado.id),
            datos_nuevos={
                'folio': certificado.folio_certificado,
                'tipo': tipo_cert,
                'paciente_id': cita.paciente_id,
                'cita_id': cita.id,
            },
            request=request,
        )

        url_ver = request.build_absolute_uri(
            reverse('consultorio:ver_certificado', args=[certificado.id])
        )
        return JsonResponse({
            'ok': True,
            'certificado_id': certificado.id,
            'url_ver': url_ver,
            'url_pdf': url_ver,
            'mensaje': '✅ Certificado generado exitosamente'
        })
        
    except Exception as e:
        logger = logging.getLogger('consultorio')
        logger.error(f"Error generando certificado: {e}")
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=500)


# ==============================================================================
# API: GENERACIÓN INMEDIATA DE ORDEN DE LABORATORIO
# ==============================================================================

@login_required
@require_http_methods(['POST'])
def api_generar_orden_laboratorio_inmediata(request):
    """
    Genera una orden de laboratorio INMEDIATAMENTE.
    """
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
        cita_id = data.get('cita_id')
        estudios = data.get('estudios', [])
        urgencia = data.get('urgencia', 'NORMAL')
        
        if cita_id is None or cita_id == '':
            return JsonResponse({'ok': False, 'error': 'cita_id es requerido'}, status=400)
        if not estudios:
            return JsonResponse({
                'ok': False,
                'error': 'Debe seleccionar al menos un estudio'
            }, status=400)
        
        # Multi-tenant: empresa obligatoria, cita filtrada por empresa
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)
        
        # Obtener médico: de la cita (si tiene empresa) o del usuario/crear con empresa
        medico = _resolver_medico_usuario(
            request,
            empresa,
            medico_preferido=cita.medico,
            autocrear=True,
        )
        
        from decimal import ROUND_HALF_UP

        tipo_srv = 'URGENCIA' if urgencia == 'URGENCIA' else 'RUTINA'

        raw_ids = []
        for item in estudios:
            if isinstance(item, dict):
                eid = item.get('id')
                if eid is not None:
                    raw_ids.append(eid)
            else:
                raw_ids.append(item)

        lineas = resolve_lims_cart_ids(list(raw_ids), empresa=empresa)
        if not lineas:
            return JsonResponse({
                'ok': False,
                'error': 'No se resolvió ningún ítem del catálogo LIMS (analito/perfil/paquete)',
            }, status=400)

        with transaction.atomic():
            total_orden = Decimal('0.00')
            for row in lineas:
                total_orden += aplicar_precio_convenio(
                    row['precio_base'], row['precio_key'], {}, Decimal('0')
                )
            total_orden = total_orden.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            orden = OrdenDeServicio.objects.create(
                empresa=empresa,
                paciente=cita.paciente,
                medico_referente=medico,
                tipo_servicio=tipo_srv,
                diagnostico=f'Orden generada en consulta (Cita #{cita.id})',
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
        
        return JsonResponse({
            'ok': True,
            'orden_id': orden.id,
            'url_detalle': reverse('imprimir_ticket_lab', args=[orden.id]),
            'mensaje': '✅ Orden de laboratorio generada exitosamente'
        })
        
    except Exception as e:
        logger = logging.getLogger('consultorio')
        logger.error(f"Error generando orden: {e}")
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=500)


# ==============================================================================
# ARCHIVOS ADJUNTOS (Rx, Tomografías, Documentos externos)
# ==============================================================================

@login_required
def archivos_paciente(request, paciente_id):
    """
    Vista de archivos adjuntos de un paciente.
    Permite subir y ver radiografías, tomografías, documentos de otros lugares.
    """
    from consultorio.models import ArchivoAdjuntoConsulta
    
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    
    archivos = ArchivoAdjuntoConsulta.objects.filter(
        paciente=paciente, empresa=empresa
    ).order_by('-fecha_subida')
    
    # Agrupar por tipo
    tipos_archivo = {}
    for archivo in archivos:
        tipo = archivo.get_tipo_display()
        if tipo not in tipos_archivo:
            tipos_archivo[tipo] = []
        tipos_archivo[tipo].append(archivo)
    
    return render(request, 'consultorio/archivos_paciente.html', {
        'paciente': paciente,
        'archivos': archivos,
        'tipos_archivo': tipos_archivo,
        'tipo_choices': ArchivoAdjuntoConsulta.TIPO_CHOICES,
    })


@login_required
@require_http_methods(['POST'])
def api_subir_archivo(request):
    """
    API para subir archivos adjuntos (radiografías, tomografías, etc.).
    Acepta multipart/form-data.
    """
    from consultorio.models import ArchivoAdjuntoConsulta
    
    try:
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        paciente_id = request.POST.get('paciente_id')
        consulta_id = request.POST.get('consulta_id')
        tipo = request.POST.get('tipo', 'DOCUMENTO')
        titulo = request.POST.get('titulo', 'Sin título')
        descripcion = request.POST.get('descripcion', '')
        origen = request.POST.get('origen', '')
        fecha_documento = request.POST.get('fecha_documento')
        
        if not paciente_id:
            return JsonResponse({'ok': False, 'error': 'paciente_id es requerido'}, status=400)
        if 'archivo' not in request.FILES:
            return JsonResponse({
                'ok': False,
                'error': 'No se recibio archivo'
            }, status=400)
        
        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
        
        consulta = None
        if consulta_id:
            consulta = ConsultaMedica.objects.filter(id=consulta_id, empresa=empresa).first()
            if consulta and consulta.paciente_id != paciente.id:
                return JsonResponse({
                    'ok': False,
                    'error': 'La consulta seleccionada no corresponde al paciente indicado'
                }, status=400)
        
        archivo = ArchivoAdjuntoConsulta.objects.create(
            empresa=empresa,
            paciente=paciente,
            consulta=consulta,
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion,
            archivo=request.FILES['archivo'],
            origen=origen,
            fecha_documento=fecha_documento if fecha_documento else None,
            subido_por=request.user,
        )
        
        return JsonResponse({
            'ok': True,
            'archivo_id': archivo.id,
            'titulo': archivo.titulo,
            'tipo': archivo.get_tipo_display(),
            'mensaje': f'Archivo "{titulo}" subido exitosamente'
        })
        
    except Exception as e:
        logger = logging.getLogger('consultorio')
        logger.error(f"Error subiendo archivo: {e}")
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['POST'])
def api_eliminar_archivo(request, archivo_id):
    """Eliminar archivo adjunto."""
    from consultorio.models import ArchivoAdjuntoConsulta
    
    try:
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
        archivo = get_object_or_404(ArchivoAdjuntoConsulta, id=archivo_id, empresa=empresa)
        nombre = archivo.titulo
        archivo.delete()
        
        return JsonResponse({
            'ok': True,
            'mensaje': f'Archivo "{nombre}" eliminado'
        })
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=500)


# ==============================================================================
# VADEMÉCUM (Búsqueda de medicamentos en tiempo real)
# ==============================================================================

@login_required
@require_http_methods(['GET'])
def api_buscar_vademecum(request):
    """
    API para buscar medicamentos en el Vademécum integrado.
    Retorna dosis, contraindicaciones e interacciones.
    """
    from consultorio.models import Vademecum
    
    termino = request.GET.get('q', '').strip()
    
    if len(termino) < 2:
        return JsonResponse([], safe=False)
    
    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    # Buscar en vademécum global + de la empresa
    medicamentos = Vademecum.objects.filter(
        activo=True
    ).filter(
        Q(empresa=empresa) | Q(empresa__isnull=True)
    ).filter(
        Q(nombre_generico__icontains=termino) |
        Q(nombre_comercial__icontains=termino) |
        Q(principio_activo__icontains=termino) |
        Q(grupo_terapeutico__icontains=termino)
    ).order_by('nombre_generico')[:15]
    
    resultados = [{
        'id': m.id,
        'nombre_generico': m.nombre_generico,
        'nombre_comercial': m.nombre_comercial,
        'principio_activo': m.principio_activo,
        'presentacion': m.presentacion,
        'concentracion': m.concentracion,
        'via': m.get_via_administracion_display(),
        'dosis_adulto': m.dosis_adulto,
        'dosis_pediatrica': m.dosis_pediatrica,
        'dosis_maxima': m.dosis_maxima,
        'contraindicaciones': m.contraindicaciones,
        'efectos_adversos': m.efectos_adversos,
        'interacciones': m.interacciones,
        'embarazo': m.get_embarazo_categoria_display() if m.embarazo_categoria else '',
        'requiere_receta': m.requiere_receta,
        'controlado': m.controlado,
        'en_farmacia': m.producto_farmacia_id is not None,
    } for m in medicamentos]
    
    return JsonResponse(resultados, safe=False)


# ==============================================================================
# SIGNOS VITALES: API DE TENDENCIAS (Charts)
# ==============================================================================

@login_required
@require_http_methods(['GET'])
def api_signos_vitales_tendencia(request, paciente_id):
    """
    Retorna historial de signos vitales para gráficas de tendencias.
    Datos: peso, presión, glucosa, temperatura, IMC a lo largo del tiempo.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    
    # Últimos 20 registros de signos vitales
    signos = SignosVitales.objects.filter(
        paciente=paciente
    ).order_by('fecha_registro')[:20]
    
    datos = {
        'fechas': [],
        'peso': [],
        'imc': [],
        'pa_sistolica': [],
        'pa_diastolica': [],
        'temperatura': [],
        'glucosa': [],
        'fc': [],
        'spo2': [],
    }
    
    for s in signos:
        datos['fechas'].append(s.fecha_registro.strftime('%d/%m/%Y'))
        datos['peso'].append(float(s.peso) if s.peso else None)
        datos['imc'].append(float(s.imc) if s.imc else None)
        datos['pa_sistolica'].append(s.presion_arterial_sistolica)
        datos['pa_diastolica'].append(s.presion_arterial_diastolica)
        datos['temperatura'].append(float(s.temperatura) if s.temperatura else None)
        datos['glucosa'].append(float(s.glucosa_capilar) if s.glucosa_capilar else None)
        datos['fc'].append(s.frecuencia_cardiaca)
        datos['spo2'].append(s.saturacion_oxigeno)
    
    return JsonResponse({
        'ok': True,
        'paciente': paciente.nombre_completo,
        'total_registros': len(signos),
        'datos': datos,
    })


# ==============================================================================
# CONFIGURACIÓN DEL MÉDICO (Isla Independiente)
# ==============================================================================

@login_required
def configuracion_medico(request):
    """
    Vista para que el médico configure su "isla independiente":
    - Agenda ON/OFF
    - Modo de cobro
    - Marketing propio
    - Horarios de atención
    """
    from consultorio.models import ConfiguracionMedico
    
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    # Obtener o crear configuración
    config, created = ConfiguracionMedico.objects.get_or_create(
        medico=request.user,
        defaults={'empresa': empresa}
    )
    
    if request.method == 'POST':
        try:
            # Agenda — CICLO 6: parse seguro para evitar ValueError
            config.agenda_activa = request.POST.get('agenda_activa') == 'on'
            duracion_val = _int_or_none(request.POST.get('duracion_consulta_default', 30))
            config.duracion_consulta_default = duracion_val if duracion_val is not None else 30
            config.horario_inicio = request.POST.get('horario_inicio', '08:00')
            config.horario_fin = request.POST.get('horario_fin', '20:00')
            config.reserva_online_activa = request.POST.get('reserva_online_activa') == 'on'
            
            # Días de atención (solo valores numéricos válidos 0-6)
            dias = request.POST.getlist('dias_atencion')
            config.dias_atencion = [d for d in (_int_or_none(x) for x in dias) if d is not None and 0 <= d <= 6]
            
            # Cobros — CICLO 6: parse seguro para Decimal
            config.modo_cobro = request.POST.get('modo_cobro', 'RECEPCION')
            precio = _dec_or_none(request.POST.get('precio_consulta_default', '0'))
            config.precio_consulta_default = precio if precio is not None else Decimal('0')
            
            # Marketing
            config.marketing_propio = request.POST.get('marketing_propio') == 'on'
            
            # Especialidad
            config.especialidad_principal = request.POST.get('especialidad_principal', 'Medico General')
            config.subespecialidad = request.POST.get('subespecialidad', '')
            
            # WhatsApp
            config.whatsapp_confirmaciones = request.POST.get('whatsapp_confirmaciones') == 'on'
            config.telefono_whatsapp = request.POST.get('telefono_whatsapp', '')
            
            # Triaje pre-cita
            config.triaje_precita_activo = request.POST.get('triaje_precita_activo') == 'on'
            
            config.save()
            messages.success(request, 'Configuracion guardada exitosamente')
            return redirect('consultorio:configuracion_medico')
            
        except Exception as e:
            messages.error(request, f'Error al guardar: {str(e)}')
    
    return render(request, 'consultorio/configuracion_medico.html', {
        'config': config,
    })


# ==============================================================================
# PLANTILLAS POR ESPECIALIDAD
# ==============================================================================

@login_required
@require_http_methods(['GET'])
def api_plantillas_especialidad(request):
    """
    Retorna plantillas de notas clínicas filtradas por especialidad del médico.
    """
    from core.models import PlantillaNotaClinica
    from consultorio.models import ConfiguracionMedico
    
    empresa = _empresa_explicita_usuario(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    # Obtener especialidad del médico
    try:
        config = ConfiguracionMedico.objects.get(medico=request.user)
        especialidad = config.especialidad_principal
    except ConfiguracionMedico.DoesNotExist:
        especialidad = ''
    
    # Filtrar plantillas: públicas + propias + de la especialidad
    plantillas = PlantillaNotaClinica.objects.filter(
        empresa=empresa,
        activa=True
    ).filter(
        Q(es_publica=True) |
        Q(creado_por=request.user) |
        Q(especialidad__icontains=especialidad) |
        Q(especialidad='')
    ).order_by('-veces_usada', 'nombre')[:20]
    
    resultados = [{
        'id': p.id,
        'nombre': p.nombre,
        'descripcion': p.descripcion,
        'especialidad': p.especialidad,
        'subjetivo': p.subjetivo,
        'objetivo': p.objetivo,
        'analisis': p.analisis,
        'plan': p.plan,
        'veces_usada': p.veces_usada,
    } for p in plantillas]
    
    return JsonResponse(resultados, safe=False)


@login_required
@require_http_methods(['POST'])
def api_usar_plantilla(request, plantilla_id):
    """Incrementa contador de uso y retorna datos de la plantilla."""
    from core.models import PlantillaNotaClinica
    
    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
    plantilla = get_object_or_404(PlantillaNotaClinica, id=plantilla_id, empresa=empresa)
    plantilla.veces_usada += 1
    plantilla.save(update_fields=['veces_usada'])
    
    return JsonResponse({
        'ok': True,
        'subjetivo': plantilla.subjetivo,
        'objetivo': plantilla.objetivo,
        'analisis': plantilla.analisis,
        'plan': plantilla.plan,
    })


# ==============================================================================
# ANÁLISIS DE PATRONES CON IA (Confidencial / Anónimo)
# ==============================================================================

@login_required
def analisis_patrones(request):
    """
    Vista para generar análisis de patrones de consulta con IA.
    Los datos son ANÓNIMOS: no se vinculan a pacientes individuales.
    """
    from consultorio.models import AnalisisPatron
    
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    # Obtener análisis previos
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
    """
    Genera un análisis de patrones usando IA sobre datos ANONIMIZADOS.
    """
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
        
        # Obtener datos ANONIMIZADOS (solo métricas, no datos de pacientes)
        consultas = ConsultaMedica.objects.filter(
            empresa=empresa,
            fecha_consulta__date__gte=desde,
            estado='FINALIZADA'
        )
        
        total = consultas.count()
        
        if total == 0:
            return JsonResponse({
                'ok': False,
                'error': 'No hay consultas en el periodo seleccionado'
            }, status=400)
        
        # Agregar métricas según tipo
        datos_anonimos = {'total_consultas': total}
        
        if tipo == 'DIAGNOSTICO':
            # Top diagnósticos (sin datos de pacientes)
            diagnosticos = consultas.values('diagnostico_principal').annotate(
                cantidad=Count('id')
            ).order_by('-cantidad')[:20]
            datos_anonimos['top_diagnosticos'] = list(diagnosticos)
        
        elif tipo == 'CONVERSION':
            # Tasa de conversión: consultas que generaron receta/orden lab/cirugía
            con_receta = consultas.filter(receta__isnull=False).count()
            datos_anonimos['tasa_recetas'] = round((con_receta / total) * 100, 1) if total > 0 else 0
            datos_anonimos['con_receta'] = con_receta
        
        elif tipo == 'PRODUCTIVIDAD':
            # Métricas de productividad
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
        
        # Generar insights con IA (si está disponible)
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
   (cómo el médico puede comunicar mejor el valor de sus procedimientos)

Responde en español, de forma directa y práctica. Sin formato JSON.
"""
            texto = generate_content(prompt_ia, max_tokens=1200).strip()

            # Separar insights y recomendaciones
            if 'RECOMENDACIONES' in texto.upper():
                analisis_ia = texto[:texto.upper().find('RECOMENDACIONES')]
                recomendaciones = texto[texto.upper().find('RECOMENDACIONES'):]
            else:
                analisis_ia = texto
                    
        except Exception as e:
            logger = logging.getLogger('consultorio')
            logger.warning(f"IA no disponible para analisis de patrones: {e}")
        
        # Guardar análisis
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
        
    except Exception as e:
        logger = logging.getLogger('consultorio')
        logger.error(f"Error generando analisis: {e}")
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=500)


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
        empresa=empresa,
        activo=True,
        atendido=False
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
        
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=500)


# ==============================================================================
# VADEMÉCUM (Vista de Lista)
# ==============================================================================

@login_required
def vademecum_lista(request):
    """
    Vista del Vademécum integrado: base de datos de medicamentos
    con dosis, contraindicaciones e interacciones.
    """
    from consultorio.models import Vademecum

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    medicamentos = Vademecum.objects.filter(
        activo=True
    ).filter(
        Q(empresa=empresa) | Q(empresa__isnull=True)
    ).order_by('nombre_generico')

    # Obtener grupos terapéuticos únicos para el filtro
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
# HISTORIAL DE SIGNOS VITALES (Tendencias con Gráficas)
# ==============================================================================

@login_required
def historial_signos_vitales(request, paciente_id):
    """
    Vista de historial de signos vitales del paciente con gráficas de tendencias.
    Peso, presión arterial, temperatura, glucosa, FC, SpO2.
    """
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
# AGENDA DEL MÉDICO (con switch ON/OFF)
# ==============================================================================

@login_required
def agenda_medico(request):
    """
    Vista de la agenda del médico.
    Si agenda_activa=False, muestra modo "orden de llegada".
    Navegación por fecha con día anterior/siguiente.
    """
    from consultorio.models import ConfiguracionMedico

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    # Obtener configuración del médico
    config, _ = ConfiguracionMedico.objects.get_or_create(
        medico=request.user,
        defaults={'empresa': empresa}
    )

    # Fecha seleccionada (o hoy)
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

    # Obtener citas del día
    citas_qs = CitaMedica.objects.filter(
        empresa=empresa,
        fecha_cita=fecha_actual
    )
    # Si el usuario está vinculado a un médico de la empresa, mostrar solo su agenda
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
    """
    Vista de triaje digital pre-cita: formularios enviados
    automáticamente a los pacientes antes de la consulta.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    from consultorio.models import AgendaCita, ConfiguracionMedico

    hoy = timezone.localdate()
    medicos_con_triaje = list(
        ConfiguracionMedico.objects.filter(
            empresa=empresa,
            triaje_precita_activo=True,
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
    """
    Vista de campañas de marketing médico: emails, SMS, WhatsApp.
    Permite crear, programar y ver historial de campañas.
    """
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
            empresa=empresa,
            fecha_cita__gte=primera_campana.date(),
        ).count()

    canal_map = {
        'email': 'EMAIL',
        'sms': 'SMS',
        'whatsapp': 'WHATSAPP',
        'push': 'PUSH',
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
    """
    Dashboard de encuestas de satisfacción NPS.
    Muestra score general, dimensiones de calidad y respuestas recientes.
    """
    from consultorio.models import EncuestaSatisfaccion
    from django.db.models import Avg

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    encuestas = EncuestaSatisfaccion.objects.filter(
        empresa=empresa, respondida=True
    )
    total_respondidas = encuestas.count()

    # Calcular NPS
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

    # Promedios por dimensión
    promedios = encuestas.aggregate(
        atencion_medico=Avg('atencion_medico'),
        tiempo_espera=Avg('tiempo_espera'),
        instalaciones=Avg('instalaciones'),
        explicacion=Avg('explicacion_tratamiento'),
    )
    # Redondear
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
    """
    Vista de seguimientos de tratamiento activos.
    Agrupa por tipo: medicación, citas, estudios.
    """
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
        'enviados_hoy': base_qs.filter(
            enviado=True, fecha_envio__date=hoy.date()
        ).count(),
        'pendientes_envio': base_qs.filter(
            enviado=False, fecha_programada__lte=hoy
        ).count(),
        'pacientes_en_seguimiento': (
            base_qs.values('paciente').distinct().count()
        ),
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
    """
    Dashboard de reportes de productividad del consultorio.
    KPIs, gráficas de consultas/ingresos, top diagnósticos, etc.
    """
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
        empresa=empresa,
        fecha_consulta__date__gte=desde,
        estado='FINALIZADA',
    )

    total = consultas.count()
    ingresos = consultas.filter(pagada=True).aggregate(
        total=Sum('precio_consulta')
    )['total'] or 0

    # Cancelaciones (aproximar con citas canceladas)
    citas_periodo = CitaMedica.objects.filter(
        empresa=empresa, fecha_cita__gte=desde
    )
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

    # Datos para gráficas (serializar para JavaScript)
    datos_charts = {}

    # Consultas por día
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

    # Top diagnósticos
    top_dx = consultas.exclude(
        diagnostico_principal__isnull=True
    ).exclude(
        diagnostico_principal=''
    ).values('diagnostico_principal').annotate(
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

    from django.core import signing

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
    from django.core import signing

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


# ==============================================================================
# COBRO DE CONSULTA (Control flexible)
# ==============================================================================

@login_required
def cobro_consulta(request):
    """
    FASE 10: Blindaje de Cobros - Consultorio Médico Independiente.
    Caja virtual segregada por médico con soporte para:
    - Cobros mixtos (Efectivo + Tarjeta + Transferencia)
    - Dinero en tránsito (cobrado por recepción)
    - Dashboard privado con acumulados diario/semanal/mensual
    - Reporte de liquidación: "Recepción debe entregarle $X"
    """
    from consultorio.models import (
        ConfiguracionMedico, CajaConsultorio, CobroConsulta, ValeLiquidacion
    )

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.localdate()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    # Obtener configuración del médico
    config, _ = ConfiguracionMedico.objects.get_or_create(
        medico=request.user,
        defaults={'empresa': empresa}
    )

    # Obtener o crear caja del día
    caja_hoy, _ = CajaConsultorio.objects.get_or_create(
        medico=request.user,
        fecha=hoy,
        defaults={'empresa': empresa}
    )

    # Consultas finalizadas hoy sin pagar
    pendientes_cobro = ConsultaMedica.objects.filter(
        empresa=empresa,
        fecha_consulta__date=hoy,
        estado='FINALIZADA',
        pagada=False,
    ).select_related('paciente').order_by('-fecha_consulta')

    # Cobros registrados hoy (desde el modelo CobroConsulta)
    cobros_hoy = CobroConsulta.objects.filter(
        caja=caja_hoy,
        estado='PAGADO',
    ).select_related('consulta', 'paciente').order_by('-fecha_cobro')

    # Vales pendientes de liquidación
    vales_pendientes = ValeLiquidacion.objects.filter(
        medico=request.user,
        estado__in=['PENDIENTE', 'PARCIAL'],
    ).select_related('cobro', 'cobro__consulta', 'cobro__paciente').order_by('-fecha_creacion')

    # === STATS DEL DÍA ===
    agg_hoy = cobros_hoy.aggregate(
        total=Sum('monto_total'),
        efectivo=Sum('monto_efectivo'),
        tarjeta=Sum('monto_tarjeta'),
        transferencia=Sum('monto_transferencia'),
    )
    ingresos_hoy = agg_hoy['total'] or Decimal('0')
    count_hoy = cobros_hoy.count()
    en_transito_hoy = vales_pendientes.aggregate(
        total=Sum('monto_adeudado')
    )['total'] or Decimal('0')
    ya_liquidado = vales_pendientes.aggregate(
        total=Sum('monto_liquidado')
    )['total'] or Decimal('0')

    stats_hoy = {
        'ingresos': float(ingresos_hoy),
        'efectivo': float(agg_hoy['efectivo'] or 0),
        'tarjeta': float(agg_hoy['tarjeta'] or 0),
        'transferencia': float(agg_hoy['transferencia'] or 0),
        'pagadas': count_hoy,
        'pendientes_cobro': pendientes_cobro.count(),
        'ticket_promedio': round(float(ingresos_hoy) / count_hoy, 0) if count_hoy > 0 else 0,
        'en_transito': float(en_transito_hoy - ya_liquidado),
    }

    # === STATS SEMANAL ===
    cobros_semana = CobroConsulta.objects.filter(
        medico=request.user,
        estado='PAGADO',
        fecha_cobro__date__gte=inicio_semana,
        fecha_cobro__date__lte=hoy,
    )
    stats_semana = cobros_semana.aggregate(total=Sum('monto_total'))['total'] or 0

    # === STATS MENSUAL ===
    cobros_mes = CobroConsulta.objects.filter(
        medico=request.user,
        estado='PAGADO',
        fecha_cobro__date__gte=inicio_mes,
        fecha_cobro__date__lte=hoy,
    )
    stats_mes = cobros_mes.aggregate(total=Sum('monto_total'))['total'] or 0

    return render(request, 'consultorio/cobro_consulta.html', {
        'config': config,
        'caja_hoy': caja_hoy,
        'pendientes_cobro': pendientes_cobro,
        'cobros_hoy': cobros_hoy,
        'vales_pendientes': vales_pendientes,
        'stats_hoy': stats_hoy,
        'stats_semana': float(stats_semana),
        'stats_mes': float(stats_mes),
    })


@login_required
@require_http_methods(["POST"])
def api_registrar_cobro(request):
    """
    API para registrar un cobro de consulta con soporte de pago mixto.
    No toca inventario. Solo servicios profesionales.
    """
    from consultorio.models import (
        CajaConsultorio, CobroConsulta, ValeLiquidacion, ConfiguracionMedico
    )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos'}, status=400)

    consulta_id = data.get('consulta_id')
    monto_total = Decimal(str(data.get('monto_total', '0')))
    monto_efectivo = Decimal(str(data.get('monto_efectivo', '0')))
    monto_tarjeta = Decimal(str(data.get('monto_tarjeta', '0')))
    monto_transferencia = Decimal(str(data.get('monto_transferencia', '0')))
    concepto = data.get('concepto', 'CONSULTA')
    cobrado_por = data.get('cobrado_por', 'MEDICO')
    referencia = data.get('referencia_pago', '')
    notas = data.get('notas', '')

    if not consulta_id or monto_total <= 0:
        return JsonResponse({'error': 'Consulta y monto son requeridos'}, status=400)

    # Validar que los montos parciales sumen el total
    suma_parciales = monto_efectivo + monto_tarjeta + monto_transferencia
    if suma_parciales != monto_total:
        return JsonResponse({
            'error': f'Los montos parciales (${suma_parciales}) no coinciden con el total (${monto_total})'
        }, status=400)

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    try:
        consulta = ConsultaMedica.objects.get(id=consulta_id, empresa=empresa)
    except ConsultaMedica.DoesNotExist:
        return JsonResponse({'error': 'Consulta no encontrada'}, status=404)
    hoy = timezone.localdate()

    with transaction.atomic():
        # Idempotencia (K1): bloquear la consulta y rechazar doble cobro
        # (doble clic / reenvío del POST creaba 2 CobroConsulta y duplicaba la caja).
        consulta = ConsultaMedica.objects.select_for_update().get(id=consulta_id, empresa=empresa)
        if getattr(consulta, 'pagada', False):
            return JsonResponse({
                'error': 'Esta consulta ya fue cobrada.',
                'codigo': 'CONSULTA_YA_COBRADA',
            }, status=409)

        # Obtener/crear caja del día
        caja, _ = CajaConsultorio.objects.get_or_create(
            medico=request.user,
            fecha=hoy,
            defaults={'empresa': empresa}
        )

        # Crear el cobro
        cobro = CobroConsulta.objects.create(
            empresa=empresa,
            caja=caja,
            consulta=consulta,
            paciente=consulta.paciente,
            medico=request.user,
            concepto=concepto,
            monto_total=monto_total,
            monto_efectivo=monto_efectivo,
            monto_tarjeta=monto_tarjeta,
            monto_transferencia=monto_transferencia,
            cobrado_por=cobrado_por,
            usuario_cobro=request.user,
            referencia_pago=referencia,
            notas=notas,
            estado='PAGADO',
        )

        # Marcar la consulta como pagada
        consulta.pagada = True
        consulta.precio_consulta = monto_total
        consulta.save(update_fields=['pagada', 'precio_consulta'])

        # Actualizar totales de la caja
        caja.total_efectivo += monto_efectivo
        caja.total_tarjeta += monto_tarjeta
        caja.total_transferencia += monto_transferencia
        caja.consultas_cobradas += 1
        caja.save()

        # Si cobró recepción, crear vale de liquidación
        vale_data = None
        if cobrado_por == 'RECEPCION':
            vale = ValeLiquidacion.objects.create(
                empresa=empresa,
                cobro=cobro,
                medico=request.user,
                monto_adeudado=monto_total,
                estado='PENDIENTE',
            )
            caja.total_en_transito += monto_total
            caja.save(update_fields=['total_en_transito'])
            vale_data = {
                'folio_vale': vale.folio_vale,
                'monto': float(vale.monto_adeudado),
            }

    response_data = {
        'success': True,
        'cobro_id': cobro.id,
        'folio_consulta': consulta.folio_consulta,
        'monto_total': float(monto_total),
        'metodo': cobro.get_metodo_pago_display(),
        'es_mixto': cobro.es_mixto,
    }
    if vale_data:
        response_data['vale'] = vale_data

    return JsonResponse(response_data)


@login_required
@require_http_methods(["POST"])
def api_liquidar_vale(request):
    """
    API para marcar un vale como liquidado (recepción entregó el dinero al médico).
    """
    from consultorio.models import ValeLiquidacion

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos'}, status=400)

    vale_id = data.get('vale_id')
    monto = Decimal(str(data.get('monto', '0')))

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)

    try:
        vale = ValeLiquidacion.objects.get(id=vale_id, medico=request.user, empresa=empresa)
    except ValeLiquidacion.DoesNotExist:
        return JsonResponse({'error': 'Vale no encontrado'}, status=404)

    if vale.estado == 'LIQUIDADO':
        return JsonResponse({'error': 'Este vale ya fue liquidado'}, status=400)

    with transaction.atomic():
        if monto <= 0:
            return JsonResponse({'error': 'El monto debe ser mayor a 0'}, status=400)

        if monto >= vale.saldo_pendiente:
            # Liquidación total
            vale.monto_liquidado = vale.monto_adeudado
            vale.estado = 'LIQUIDADO'
        else:
            # Liquidación parcial
            vale.monto_liquidado += monto
            vale.estado = 'PARCIAL'

        vale.liquidado_por = request.user
        vale.fecha_liquidacion = timezone.now()
        vale.save()

        # Actualizar caja
        caja = vale.cobro.caja
        caja.total_liquidado += monto if monto > 0 else vale.monto_adeudado
        caja.save(update_fields=['total_liquidado'])

    return JsonResponse({
        'success': True,
        'vale_folio': vale.folio_vale,
        'estado': vale.get_estado_display(),
        'saldo_pendiente': float(vale.saldo_pendiente),
    })


@login_required
def reporte_liquidacion(request):
    """
    Reporte de liquidación diaria.
    Muestra: "Recepción debe entregarle $X al médico".
    """
    from consultorio.models import ValeLiquidacion, CobroConsulta, CajaConsultorio

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    hoy = timezone.localdate()

    # Filtro de fecha (permite ver otros días)
    fecha_str = request.GET.get('fecha')
    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha = hoy
    else:
        fecha = hoy

    # Todos los vales pendientes (no solo del día)
    vales_pendientes = ValeLiquidacion.objects.filter(
        medico=request.user,
        estado__in=['PENDIENTE', 'PARCIAL'],
    ).select_related('cobro', 'cobro__consulta', 'cobro__paciente')

    # Cobros del día seleccionado
    cobros_dia = CobroConsulta.objects.filter(
        medico=request.user,
        estado='PAGADO',
        fecha_cobro__date=fecha,
    ).select_related('consulta', 'paciente')

    # Calcular totales
    total_pendiente = sum(v.saldo_pendiente for v in vales_pendientes)
    total_dia = cobros_dia.aggregate(total=Sum('monto_total'))['total'] or 0

    # Historial de cajas recientes
    cajas_recientes = CajaConsultorio.objects.filter(
        medico=request.user,
    ).order_by('-fecha')[:7]

    return render(request, 'consultorio/reporte_liquidacion.html', {
        'fecha': fecha,
        'hoy': hoy,
        'vales_pendientes': vales_pendientes,
        'cobros_dia': cobros_dia,
        'total_pendiente': float(total_pendiente),
        'total_dia': float(total_dia),
        'cajas_recientes': cajas_recientes,
    })


# ==============================================================================
# PRIS SENTINEL: TELEMETRÍA INTELIGENTE Y GESTIÓN DE INCIDENCIAS
# ==============================================================================

@login_required
def sentinel_dashboard(request):
    """
    Dashboard de incidencias para el Director.
    v3: Filtros por namespace, botón 'SOLUCIONAR CON CURSOR', SSH quick-fix,
    y panel de autocuración compatible con Remote SSH.
    Solo accesible por superusuarios, administradores y directores.
    """
    from consultorio.models import IncidenciaSentinel

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    # Verificar permisos (Director / Admin / Superuser)
    is_director = (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Administrador', 'Director', 'Gerente']).exists() or
        getattr(request.user, 'rol', '') in ['ADMIN', 'DIRECTOR', 'GERENTE']
    )
    if not is_director:
        messages.error(request, 'Acceso denegado. Solo directores y administradores.')
        return redirect('consultorio:dashboard_consultorio')

    # Acción POST: limpieza masiva de incidencias resueltas
    if request.method == 'POST' and request.POST.get('accion') == 'limpiar_resueltas':
        # Marcar como SOLUCIONADO todas las incidencias de favicon y URLs ya corregidas
        urls_resueltas = ['/favicon.ico', '/consultorio/api/resultados-disponibles/']
        count_favicon = IncidenciaSentinel.objects.filter(
            empresa=empresa,
            estado='PENDIENTE',
            url_afectada__in=urls_resueltas,
        ).update(estado='SOLUCIONADO', resuelto_por=request.user, fecha_resolucion=timezone.now())

        # Marcar feedbacks de Brizia como solucionados (los issues ya fueron corregidos)
        count_feedback = IncidenciaSentinel.objects.filter(
            empresa=empresa,
            estado='PENDIENTE',
            origen='FEEDBACK',
        ).update(estado='SOLUCIONADO', resuelto_por=request.user, fecha_resolucion=timezone.now())

        total_limpiados = count_favicon + count_feedback
        messages.success(request, f'Sentinel: {total_limpiados} incidencias marcadas como solucionadas.')
        return redirect('consultorio:sentinel_dashboard')

    # Filtros
    estado_filtro = request.GET.get('estado', '')
    severidad_filtro = request.GET.get('severidad', '')
    namespace_filtro = request.GET.get('namespace', '')

    incidencias = IncidenciaSentinel.objects.filter(empresa=empresa)

    if estado_filtro:
        incidencias = incidencias.filter(estado=estado_filtro)
    if severidad_filtro:
        incidencias = incidencias.filter(severidad=severidad_filtro)
    if namespace_filtro:
        incidencias = incidencias.filter(namespace=namespace_filtro)

    incidencias = incidencias.select_related('usuario_reporta', 'resuelto_por').order_by('-fecha_creacion')[:100]

    # Estadísticas
    stats = IncidenciaSentinel.objects.filter(empresa=empresa).aggregate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado='PENDIENTE')),
        en_reparacion=Count('id', filter=Q(estado='EN_REPARACION')),
        solucionados=Count('id', filter=Q(estado='SOLUCIONADO')),
        criticas=Count('id', filter=Q(severidad='CRITICA', estado='PENDIENTE')),
    )

    return render(request, 'consultorio/sentinel_dashboard.html', {
        'incidencias': incidencias,
        'stats': stats,
        'estado_filtro': estado_filtro,
        'severidad_filtro': severidad_filtro,
        'namespace_filtro': namespace_filtro,
    })


@login_required
def sentinel_ssh_guide(request):
    """Guía visual paso a paso para configurar Remote SSH con Cursor."""
    return render(request, 'consultorio/sentinel_ssh_guide.html')


@login_required
def sentinel_detalle(request, incidencia_id):
    """Detalle de una incidencia con traceback completo y análisis IA."""
    from consultorio.models import IncidenciaSentinel

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'message': 'Usuario sin empresa asignada'}, status=403)
    incidencia = get_object_or_404(IncidenciaSentinel, id=incidencia_id, empresa=empresa)
    # Cambiar estado si se solicita
    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado in ['PENDIENTE', 'EN_REPARACION', 'SOLUCIONADO']:
            incidencia.estado = nuevo_estado
            if nuevo_estado == 'SOLUCIONADO':
                incidencia.resuelto_por = request.user
                incidencia.fecha_resolucion = timezone.now()
                incidencia.notas_resolucion = request.POST.get('notas_resolucion', '')
            incidencia.save()
            messages.success(request, f'Estado actualizado a: {incidencia.get_estado_display()}')
            return redirect('consultorio:sentinel_detalle', incidencia_id=incidencia.id)

    # Pasar el contexto de reparación al template para visualización
    repair_ctx = incidencia.contexto_reparacion or {}

    return render(request, 'consultorio/sentinel_detalle.html', {
        'incidencia': incidencia,
        'repair_ctx': repair_ctx,
    })


@login_required
@require_http_methods(["POST"])
def api_sentinel_feedback(request):
    """
    API: Recibe el reporte en lenguaje natural de la doctora.
    Cruza con el ultimo error tecnico para crear un Ticket de Reparacion Maestro.
    """
    logger = logging.getLogger('sentinel')

    try:
        from consultorio.models import IncidenciaSentinel
    except Exception as e:
        logger.error(f"SENTINEL FEEDBACK: No se pudo importar IncidenciaSentinel: {e}")
        return JsonResponse({'status': 'error', 'message': 'Modulo Sentinel no disponible.'}, status=500)

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'message': 'Usuario sin empresa asignada'}, status=403)

    try:
        data = json.loads(request.body)
        descripcion = data.get('descripcion', '').strip()

        if not descripcion:
            return JsonResponse({'status': 'error', 'message': 'Escribe una descripcion del problema.'}, status=400)

        # Buscar la ultima incidencia tecnica (ultimas 2 horas)
        ultima_incidencia = None
        try:
            hace_2h = timezone.now() - timedelta(hours=2)
            ultima_incidencia = IncidenciaSentinel.objects.filter(
                empresa=empresa,
                origen='MIDDLEWARE',
                fecha_creacion__gte=hace_2h,
            ).order_by('-fecha_creacion').first()
        except Exception as e:
            logger.warning(f"SENTINEL FEEDBACK: Error buscando incidencias previas: {e}")

        # URL de donde reporta (truncar a 500 caracteres por seguridad)
        url_reportada = str(data.get('url_actual', request.META.get('HTTP_REFERER', '')))[:500]

        # PASO 1: Crear incidencia RÁPIDO (sin esperar IA)
        contexto_basico = f"Reporte del usuario: {descripcion}"
        incidencia = IncidenciaSentinel.objects.create(
            empresa=empresa,
            origen='FEEDBACK',
            usuario_reporta=request.user,
            url_afectada=url_reportada,
            metodo_http='POST',
            namespace='consultorio',
            codigo_http=0,
            tipo_excepcion='UserFeedback',
            traceback_completo=ultima_incidencia.traceback_completo if ultima_incidencia else '',
            datos_request={'feedback': True},
            tag='#FEEDBACK_CONSULTA',
            descripcion_usuario=descripcion,
            analisis_ia=contexto_basico,
            contexto_cursor=contexto_basico,
            estado='PENDIENTE',
            severidad=data.get('severidad', 'MEDIA'),
        )

        logger.info(f"SENTINEL FEEDBACK OK: Incidencia #{incidencia.id} creada por {request.user.username}")

        # PASO 2: Enriquecer con IA en background (no bloquea al usuario)
        try:
            from consultorio.sentinel_service import cruzar_feedback_con_error
            import threading

            def _enriquecer_con_ia(inc_id, desc, ult_inc):
                try:
                    contexto_maestro = cruzar_feedback_con_error(desc, ult_inc)
                    IncidenciaSentinel.objects.filter(id=inc_id).update(
                        analisis_ia=contexto_maestro,
                        contexto_cursor=contexto_maestro,
                    )
                except Exception as ex:
                    logging.getLogger('sentinel').warning(f"SENTINEL IA background: {ex}")

            threading.Thread(
                target=_enriquecer_con_ia,
                args=(incidencia.id, descripcion, ultima_incidencia),
                daemon=True
            ).start()
        except Exception as e:
            logger.warning(f"SENTINEL FEEDBACK: No se pudo iniciar enriquecimiento IA: {e}")

        return JsonResponse({
            'status': 'success',
            'message': 'Tu reporte fue registrado. El equipo tecnico lo revisara.',
            'incidencia_id': incidencia.id,
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Formato de datos invalido.'}, status=400)
    except Exception as e:
        logger.error(f"SENTINEL FEEDBACK ERROR: {type(e).__name__}: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'Error del servidor: {type(e).__name__}'}, status=500)


@login_required
def api_sentinel_exportar_cursor(request, incidencia_id):
    """
    API: Exporta el contexto técnico de una incidencia en formato
    listo para copiar y pegar en Cursor (Remote SSH compatible).
    v3: Genera prompt optimizado para autocuración con archivo, línea,
    código propuesto e instrucciones SSH para reparación en vivo.
    """
    from consultorio.models import IncidenciaSentinel
    from consultorio.sentinel_service import (
        generar_prompt_cursor_reparacion,
        generar_resumen_ssh_rapido
    )

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'message': 'Usuario sin empresa asignada'}, status=403)
    incidencia = get_object_or_404(IncidenciaSentinel, id=incidencia_id, empresa=empresa)
    # Si tiene contexto_reparacion, usar el generador avanzado
    if incidencia.contexto_reparacion:
        bloque_cursor = generar_prompt_cursor_reparacion(incidencia)
    else:
        # Fallback al formato legacy enriquecido con info SSH
        bloque_cursor = (
            f"@Codebase PRIS SENTINEL - Ticket #{incidencia.id} (REPARACIÓN REMOTA)\n"
            f"{'=' * 60}\n"
            f"MODO: Remote SSH -> Servidor Ubuntu\n"
            f"Severidad: {incidencia.get_severidad_display()}\n"
            f"Modulo: {incidencia.namespace.upper()}\n"
            f"URL: {incidencia.metodo_http} {incidencia.url_afectada}\n"
            f"Excepcion: {incidencia.tipo_excepcion}\n"
            f"Fecha: {incidencia.fecha_creacion.strftime('%Y-%m-%d %H:%M')}\n\n"
        )

        if incidencia.descripcion_usuario:
            bloque_cursor += (
                f"REPORTE DEL USUARIO:\n"
                f"{incidencia.descripcion_usuario}\n\n"
            )

        if incidencia.contexto_cursor:
            bloque_cursor += (
                f"ANALISIS IA:\n"
                f"{incidencia.contexto_cursor}\n\n"
            )

        bloque_cursor += (
            f"TRACEBACK COMPLETO:\n"
            f"{incidencia.traceback_completo}\n\n"
            f"INSTRUCCION: Corrige este error. El servidor está conectado via "
            f"Remote SSH. Ruta del proyecto: /app/. Los cambios se aplican en vivo.\n"
        )

    # Generar resumen SSH rápido
    ssh_rapido = ''
    if incidencia.contexto_reparacion:
        ssh_rapido = generar_resumen_ssh_rapido(incidencia)

    # Marcar como EN_REPARACION
    if incidencia.estado == 'PENDIENTE':
        incidencia.estado = 'EN_REPARACION'
        incidencia.resuelto_por = request.user
        incidencia.save(update_fields=['estado', 'resuelto_por', 'fecha_modificacion'])

    # Incluir datos de reparación para el frontend
    ctx_rep = incidencia.contexto_reparacion or {}

    return JsonResponse({
        'status': 'success',
        'bloque_cursor': bloque_cursor,
        'ssh_rapido': ssh_rapido,
        'incidencia_id': incidencia.id,
        'tiene_reparacion': bool(ctx_rep),
        'reparacion': {
            'archivo': ctx_rep.get('archivo_principal', ''),
            'linea': ctx_rep.get('linea_error', 0),
            'funcion': ctx_rep.get('funcion_afectada', ''),
            'causa': ctx_rep.get('causa_raiz', ''),
            'codigo_original': ctx_rep.get('codigo_original', ''),
            'codigo_propuesto': ctx_rep.get('codigo_propuesto', ''),
            'instrucciones_ssh': ctx_rep.get('instrucciones_ssh', ''),
            'riesgo': ctx_rep.get('riesgo_regresion', ''),
            'tiempo': ctx_rep.get('tiempo_estimado', ''),
            'archivos_relacionados': ctx_rep.get('archivos_relacionados', []),
        } if ctx_rep else {},
    })


@login_required
def api_sentinel_ssh(request, incidencia_id):
    """
    API: Genera comandos SSH rápidos para reparación directa en terminal.
    Compatible con conexiones Remote SSH al servidor Ubuntu de producción.
    """
    from consultorio.models import IncidenciaSentinel
    from consultorio.sentinel_service import generar_resumen_ssh_rapido

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'message': 'Usuario sin empresa asignada'}, status=403)
    incidencia = get_object_or_404(IncidenciaSentinel, id=incidencia_id, empresa=empresa)
    comandos_ssh = generar_resumen_ssh_rapido(incidencia)

    ctx = incidencia.contexto_reparacion or {}

    return JsonResponse({
        'status': 'success',
        'comandos_ssh': comandos_ssh,
        'incidencia_id': incidencia.id,
        'archivo': ctx.get('archivo_principal', ''),
        'linea': ctx.get('linea_error', 0),
        'ruta_contenedor': f"/app/{ctx.get('archivo_principal', '')}",
    })


# ==============================================================================
# REGISTRO RÁPIDO DE PACIENTES (DESDE DASHBOARD)
# ==============================================================================

@login_required
def crear_paciente_express(request):
    """
    Vista Express: Crea un paciente nuevo.
    Acepta POST con JSON (flujo nuevo) o POST con form-data (flujo legacy).
    Retorna JSON con uuid para redirigir a la consulta.
    """
    if request.method != 'POST':
        return redirect('consultorio:dashboard_consultorio')
    
    is_json = request.content_type and 'json' in request.content_type
    try:
        # Obtener empresa del usuario
        empresa = empresa_efectiva_request(request)
        if not empresa:
            messages.error(request, 'Usuario no tiene empresa asignada.')
            return redirect('home')
        
        if is_json:
            import json
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
            # Form-data legacy
            nombres = request.POST.get('nombres', '').strip().upper()
            apellido_paterno = request.POST.get('apellido_paterno', '').strip().upper()
            apellido_materno = request.POST.get('apellido_materno', '').strip().upper()
            nombre_completo = ''
            fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
            sexo = request.POST.get('sexo') or None
            telefono = request.POST.get('telefono', '').strip()
            email = request.POST.get('email', '').strip()
        
        # Construir nombre_completo si no viene pero si los campos separados
        if not nombre_completo and (nombres or apellido_paterno):
            partes = [p for p in [nombres, apellido_paterno, apellido_materno] if p]
            nombre_completo = ' '.join(partes)
        
        if not nombre_completo and not nombres:
            if is_json:
                return JsonResponse({'ok': False, 'error': 'El nombre es obligatorio'}, status=400)
            messages.error(request, 'El nombre es obligatorio')
            return redirect('consultorio:dashboard_consultorio')
        
        # Crear paciente con campos separados
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
            
    except Exception as e:
        import logging
        logging.getLogger('consultorio').error(f"Error en crear_paciente_express: {e}", exc_info=True)
        if is_json:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
        messages.error(request, f"Error al registrar paciente: {e}")
        return redirect('consultorio:dashboard_consultorio')


@login_required
def api_test_github_sentinel(request):
    """
    API de prueba: Verifica la conexion con GitHub y opcionalmente crea un issue de test.
    Solo accesible por superusuarios.
    GET  -> Verificar conexion
    POST -> Crear issue de prueba
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'mensaje': 'Solo superusuarios'}, status=403)
    
    from core.services.github_reporter import test_github_connection, crear_github_issue, GITHUB_TOKEN, GITHUB_REPO
    
    if request.method == 'GET':
        # Solo verificar conexion
        ok, msg = test_github_connection()
        return JsonResponse({
            'status': 'success' if ok else 'error',
            'conexion': ok,
            'mensaje': msg,
            'config': {
                'token_configurado': bool(GITHUB_TOKEN),
                'repo': GITHUB_REPO or 'NO CONFIGURADO',
            }
        })
    
    elif request.method == 'POST':
        # Crear issue de prueba
        ok, msg = test_github_connection()
        if not ok:
            return JsonResponse({'status': 'error', 'mensaje': f'Conexion fallida: {msg}'}, status=500)
        
        resultado = crear_github_issue({
            'tipo_excepcion': 'TestSentinel',
            'traceback_texto': (
                'Traceback (most recent call last):\\n'
                '  File "consultorio/views.py", line 999, in test_view\\n'
                '    raise TestSentinel("Prueba de notificacion")\\n'
                'TestSentinel: Prueba de notificacion de PRIS Sentinel\\n'
                '\\n'
                'NOTA: Este es un issue de PRUEBA generado automaticamente\\n'
                'para verificar que las notificaciones de GitHub funcionan.\\n'
                'Puede cerrar este issue de forma segura.'
            ),
            'path': '/api/sentinel/test-github/',
            'url': '/api/sentinel/test-github/',
            'metodo': 'POST',
            'severidad': 'BAJA',
            'namespace': 'sentinel',
            'codigo_http': 200,
            'user_id': request.user.id,
        })
        
        if resultado:
            return JsonResponse({
                'status': 'success',
                'mensaje': 'Issue de prueba creado exitosamente en GitHub',
                'issue_url': resultado.get('issue_url'),
                'issue_number': resultado.get('issue_number'),
            })
        else:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'No se pudo crear el issue. Puede ser rate limit o deduplicacion.'
            }, status=500)
    
    return JsonResponse({'status': 'error', 'mensaje': 'Metodo no permitido'}, status=405)


# =============================================================================
# API: RESULTADOS DISPONIBLES PARA EL DASHBOARD MÉDICO
# =============================================================================
@login_required
@require_http_methods(['GET'])
def api_resultados_disponibles(request):
    """
    Devuelve las órdenes de laboratorio con resultados listos
    vinculadas a pre-órdenes del médico actual.
    Llamado por el dashboard_medico cada 30 segundos.
    """
    try:
        from core.models import PreOrdenLaboratorio
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'status': 'success', 'resultados': []})

        preordenes = PreOrdenLaboratorio.objects.filter(
            empresa=empresa,
            medico_solicitante=request.user,
            estado='COBRADA'
        ).select_related('paciente', 'orden_vinculada')[:10]

        resultados = []
        for preorden in preordenes:
            if preorden.orden_vinculada:
                orden = preorden.orden_vinculada
                if orden.estado in ['RESULTADOS_LISTOS', 'ENTREGADO']:
                    estudios_names = list(
                        orden.detalles.values_list('estudio__nombre', flat=True)[:3]
                    )
                    resultados.append({
                        'orden_id': orden.id,
                        'paciente_nombre': preorden.paciente.nombre_completo if preorden.paciente else 'N/D',
                        'estudios': ', '.join(estudios_names),
                        'fecha': timezone.localtime(orden.fecha_creacion).strftime('%d/%m/%Y') if orden.fecha_creacion else '',
                    })

        return JsonResponse({'status': 'success', 'resultados': resultados})
    except Exception as e:
        return JsonResponse({'status': 'success', 'resultados': [], 'nota': str(e)})


@login_required
@require_http_methods(['POST'])
def api_resolver_incidencias_sentinel(request):
    """
    API: Marca como SOLUCIONADO todas las incidencias Sentinel
    que correspondan a errores ya corregidos.
    Solo accesible por superusuarios.
    POST /consultorio/api/sentinel/resolver-conocidas/
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'mensaje': 'Solo superusuarios'}, status=403)

    from consultorio.models import IncidenciaSentinel
    ahora = timezone.now()

    # Patrones de errores ya corregidos
    patrones = [
        {'filtro': {'tipo_excepcion__icontains': 'NameError'}, 'nota': 'Fix: timezone import en sentinel.py'},
        {'filtro': {'tipo_excepcion__icontains': 'FieldError', 'url_afectada__icontains': 'entrega-resultados'}, 'nota': 'Fix: bitacora_entrega removido de select_related'},
        {'filtro': {'tipo_excepcion__icontains': 'FieldError', 'url_afectada__icontains': 'medicos'}, 'nota': 'Fix: empresa filter removido de Medico'},
        {'filtro': {'tipo_excepcion__icontains': 'FieldError', 'url_afectada__icontains': 'compras'}, 'nota': 'Fix: activo filter removido de Producto'},
        {'filtro': {'tipo_excepcion__icontains': 'TypeError', 'url_afectada__icontains': 'paciente'}, 'nota': 'Fix: registrar_trazabilidad args corregidos'},
        {'filtro': {'tipo_excepcion__icontains': 'ReferenceError'}, 'nota': 'Fix: funciones JS expuestas a scope global'},
        {'filtro': {'tipo_excepcion': 'UserFeedback'}, 'nota': 'Resuelto: errores reportados ya corregidos'},
        {'filtro': {'tag': '#BUG_FARMACIA', 'url_afectada__icontains': 'pdv'}, 'nota': 'Fix: PDV farmacia corregido'},
    ]

    total = 0
    detalles = []
    for p in patrones:
        qs = IncidenciaSentinel.objects.filter(
            estado__in=['PENDIENTE', 'EN_REPARACION'],
            **p['filtro'],
        )
        count = qs.count()
        if count > 0:
            qs.update(
                estado='SOLUCIONADO',
                notas_resolucion=p['nota'],
                fecha_resolucion=ahora,
            )
            total += count
            detalles.append(f"{count}x {p['nota']}")

    # Resolver por patrones en traceback
    for patron_tb in ['timezone', 'bitacora_entrega', 'activo', 'empresa',
                       'abrirModalReceta', 'validarCamposConsultorio',
                       'enviarErrorAlServidor', 'contenedor-productos']:
        qs_tb = IncidenciaSentinel.objects.filter(
            estado__in=['PENDIENTE', 'EN_REPARACION'],
            traceback_completo__icontains=patron_tb,
        )
        count_tb = qs_tb.count()
        if count_tb > 0:
            qs_tb.update(
                estado='SOLUCIONADO',
                notas_resolucion=f'Fix automatico: error de {patron_tb} resuelto',
                fecha_resolucion=ahora,
            )
            total += count_tb

    pendientes = IncidenciaSentinel.objects.filter(
        estado__in=['PENDIENTE', 'EN_REPARACION']
    ).count()

    logger.info(f'SENTINEL: {total} incidencias marcadas como SOLUCIONADO, {pendientes} pendientes')

    return JsonResponse({
        'status': 'success',
        'resueltas': total,
        'pendientes_restantes': pendientes,
        'detalles': detalles,
    })


@login_required
@require_http_methods(['GET'])
def api_sentinel_listar_feedback(request):
    """
    API: Lista las incidencias con feedback del usuario (descripcion_usuario).
    Solo accesible por superusuarios.
    GET /consultorio/api/sentinel/feedback-lista/
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'mensaje': 'Solo superusuarios'}, status=403)

    from consultorio.models import IncidenciaSentinel

    incidencias = IncidenciaSentinel.objects.filter(
        origen='FEEDBACK',
    ).order_by('-fecha_creacion').values(
        'id', 'descripcion_usuario', 'url_afectada', 'estado',
        'severidad', 'fecha_creacion', 'notas_resolucion',
        'usuario_reporta__username', 'usuario_reporta__first_name',
    )[:50]

    items = []
    for inc in incidencias:
        items.append({
            'id': inc['id'],
            'usuario': inc['usuario_reporta__first_name'] or inc['usuario_reporta__username'] or 'Anon',
            'descripcion': inc['descripcion_usuario'],
            'url': inc['url_afectada'],
            'estado': inc['estado'],
            'severidad': inc['severidad'],
            'fecha': inc['fecha_creacion'].strftime('%Y-%m-%d %H:%M') if inc['fecha_creacion'] else '',
            'notas_resolucion': inc['notas_resolucion'] or '',
        })

    return JsonResponse({'status': 'success', 'feedback': items, 'total': len(items)})
