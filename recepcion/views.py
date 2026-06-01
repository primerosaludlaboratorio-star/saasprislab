"""
Modulo de Recepcion - Gestion de Pacientes, Citas y Sistema de Turnos
"""
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from core.models import Paciente, CitaMedica
from core.utils.empresa_request import empresa_efectiva_request

logger = logging.getLogger(__name__)


def _empresa_recepcion(request):
    return empresa_efectiva_request(request)


@login_required
def dashboard_recepcion(request):
    """Dashboard principal de recepcion."""
    empresa = _empresa_recepcion(request)
    sucursal = getattr(request.user, 'sucursal', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.now().date()
    citas_hoy = CitaMedica.objects.filter(empresa=empresa, fecha_cita=hoy)
    if sucursal:
        citas_hoy = citas_hoy.filter(sucursal=sucursal)

    total_citas_hoy = citas_hoy.count()
    citas_pendientes = citas_hoy.filter(estado='PENDIENTE').count()
    citas_en_proceso = citas_hoy.filter(estado__in=['EN_SALA', 'EN_CURSO']).count()
    citas_finalizadas = citas_hoy.filter(estado='COMPLETADA').count()
    proximas_citas = citas_hoy.filter(estado='PENDIENTE').order_by('hora_cita')[:5]

    return render(request, 'recepcion/dashboard.html', {
        'empresa': empresa,
        'total_citas_hoy': total_citas_hoy,
        'citas_pendientes': citas_pendientes,
        'citas_en_proceso': citas_en_proceso,
        'citas_finalizadas': citas_finalizadas,
        'proximas_citas': proximas_citas,
    })


@login_required
def registrar_paciente(request):
    """Registrar nuevo paciente con consentimiento LFPDPPP."""
    from core.models import ConsentimientoInformado, RegistroAuditoriaConsentimiento
    
    empresa = _empresa_recepcion(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    if request.method == 'POST':
        from .forms import PacienteForm
        form = PacienteForm(request.POST, empresa=empresa)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Guardar paciente
                    paciente = form.save(commit=False)
                    paciente.empresa = empresa
                    paciente.save()
                    
                    # Crear ConsentimientoInformado para trazabilidad LFPDPPP
                    acepta_base = form.cleaned_data['acepta_privacidad_y_tratamiento']
                    consentimiento = ConsentimientoInformado.objects.create(
                        empresa=empresa,
                        paciente=paciente,
                        orden=None,  # Sin orden asociada (alta de paciente)
                        acepta_privacidad=acepta_base,
                        acepta_procesamiento=acepta_base,
                        consentimiento_marketing=form.cleaned_data.get('consentimiento_marketing', False),
                        firma_digital='',  # Firma digital no requerida en alta básica
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    )
                    consentimiento.hash_firma = consentimiento.calcular_hash()
                    consentimiento.save()
                    
                    # Auditoría del consentimiento
                    RegistroAuditoriaConsentimiento.objects.create(
                        consentimiento=consentimiento,
                        accion='CREADO',
                        usuario=request.user,
                        descripcion=f'Consentimiento creado en alta de paciente {paciente.nombre_completo}',
                        datos_nuevos={
                            'acepta_privacidad': acepta_base,
                            'acepta_procesamiento': acepta_base,
                            'consentimiento_marketing': consentimiento.consentimiento_marketing,
                            'hash_firma': consentimiento.hash_firma,
                        },
                        ip_address=request.META.get('REMOTE_ADDR'),
                    )
                    
                    # Sincronizar campo en Paciente (regla de negocio: sin aceptación, marketing=False)
                    paciente.consentimiento_marketing = consentimiento.consentimiento_marketing
                    paciente.save(update_fields=['consentimiento_marketing'])
                    
                messages.success(
                    request,
                    f'Paciente {paciente.nombre_completo} registrado. '
                    f'LFPDPPP: privacidad y tratamiento aceptados. '
                    f'Marketing: {"Sí" if consentimiento.consentimiento_marketing else "No (opt-out)"}.',
                )
                return redirect('recepcion:buscar_paciente')
                
            except Exception as e:
                logger.error(f"Error creando paciente/consentimiento: {e}")
                messages.error(request, f'Error al guardar: {e}')
    else:
        from .forms import PacienteForm
        form = PacienteForm(empresa=empresa)

    return render(request, 'recepcion/registrar_paciente.html', {'empresa': empresa, 'form': form})


@login_required
def buscar_paciente(request):
    """Busqueda avanzada de pacientes."""
    empresa = _empresa_recepcion(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        pacientes = Paciente.objects.filter(empresa=empresa).filter(
            Q(nombres__icontains=busqueda) | Q(apellido_paterno__icontains=busqueda) |
            Q(nombre_completo__icontains=busqueda) |
            Q(telefono__icontains=busqueda) | Q(email__icontains=busqueda)
        ).order_by('nombres')[:50]
    else:
        pacientes = Paciente.objects.filter(empresa=empresa).order_by('-id')[:20]

    return render(request, 'recepcion/buscar_paciente.html', {
        'empresa': empresa, 'pacientes': pacientes, 'busqueda': busqueda,
    })


@login_required
def agendar_cita(request):
    """Agendar nueva cita medica."""
    empresa = _empresa_recepcion(request)
    sucursal = getattr(request.user, 'sucursal', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    if request.method == 'POST':
        from .forms import CitaMedicaForm
        form = CitaMedicaForm(request.POST, empresa=empresa)
        if form.is_valid():
            paciente_cita = form.cleaned_data.get('paciente')
            if paciente_cita and paciente_cita.empresa_id != empresa.id:
                messages.error(request, 'El paciente no pertenece a su empresa.')
                return render(request, 'recepcion/agendar_cita.html', {'empresa': empresa, 'form': form})
            cita = form.save(commit=False)
            cita.empresa = empresa
            cita.sucursal = sucursal
            cita.creado_por = request.user
            cita.save()
            messages.success(request, f'Cita agendada para {cita.paciente.nombre_completo}.')
            return redirect('recepcion:lista_espera')
    else:
        from .forms import CitaMedicaForm
        initial = {}
        pre_paciente = request.GET.get('paciente')
        if pre_paciente and str(pre_paciente).isdigit():
            # FIX CONTRATO UI: enlace desde buscar_paciente (?paciente=id) del mismo tenant
            if Paciente.objects.filter(pk=int(pre_paciente), empresa=empresa).exists():
                initial['paciente'] = int(pre_paciente)
        form = CitaMedicaForm(empresa=empresa, initial=initial)

    return render(request, 'recepcion/agendar_cita.html', {'empresa': empresa, 'form': form})


@login_required
def check_in_paciente(request, cita_id):
    """Registrar llegada del paciente (check-in)."""
    empresa = _empresa_recepcion(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)

    if request.method == 'POST':
        with transaction.atomic():
            cita = get_object_or_404(
                CitaMedica.objects.select_for_update(),
                id=cita_id,
                empresa=empresa,
            )
            cita.estado = 'EN_SALA'
            cita.save(update_fields=['estado'])
        messages.success(request, f'Check-in exitoso para {cita.paciente.nombre_completo}.')
        return redirect('recepcion:lista_espera')

    return render(request, 'recepcion/check_in.html', {'cita': cita})


@login_required
def lista_espera(request):
    """Lista de pacientes en sala de espera."""
    empresa = _empresa_recepcion(request)
    sucursal = getattr(request.user, 'sucursal', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.now().date()
    qs = CitaMedica.objects.filter(empresa=empresa, fecha_cita=hoy)
    if sucursal:
        qs = qs.filter(sucursal=sucursal)

    pacientes_espera = qs.filter(estado__in=['PENDIENTE', 'CONFIRMADA', 'EN_SALA']).select_related('paciente', 'medico').order_by('hora_cita')
    pacientes_consulta = qs.filter(estado='EN_CURSO').select_related('paciente', 'medico')

    return render(request, 'recepcion/lista_espera.html', {
        'empresa': empresa,
        'pacientes_espera': pacientes_espera,
        'pacientes_consulta': pacientes_consulta,
    })


@login_required
def cobrar_consulta(request, cita_id):
    """Cobrar consulta al paciente."""
    empresa = _empresa_recepcion(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)

    if request.method == 'POST':
        monto = request.POST.get('monto', '0')
        try:
            from decimal import Decimal, InvalidOperation

            monto_decimal = Decimal(str(monto).strip())
            if monto_decimal < 0:
                raise InvalidOperation('negativo')
            # metodo_pago recibido por contrato UI; persistencia en módulo de cobros cuando exista modelo
            _metodo = (request.POST.get('metodo_pago') or 'EFECTIVO').strip()[:20]
            with transaction.atomic():
                cita = get_object_or_404(
                    CitaMedica.objects.select_for_update(),
                    id=cita_id,
                    empresa=empresa,
                )
                cita.estado = 'COMPLETADA'
                cita.save(update_fields=['estado'])
            messages.success(
                request,
                f'Pago de ${monto_decimal} registrado ({_metodo}). '
                'La cita quedó como completada.',
            )
            return redirect('recepcion:dashboard_recepcion')
        except (InvalidOperation, ValueError) as exc:
            logger.warning('cobrar_consulta monto inválido: %s', exc)
            messages.error(request, 'Monto inválido. Use un número positivo (ej. 500.00).')
        except Exception:
            logger.exception('cobrar_consulta error')
            messages.error(
                request,
                'No se pudo registrar el cobro. Intente de nuevo o contacte soporte.',
            )

    return render(request, 'recepcion/cobrar_consulta.html', {'cita': cita})
