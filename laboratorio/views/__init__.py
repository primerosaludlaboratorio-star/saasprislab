"""
Laboratorio Views Package
Re-exports todas las vistas del modulo de laboratorio.
"""
import json
import base64
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from django.db.models import Q
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from core.utils.sucursal_helpers import get_request_sucursal

from core.models import Medico
from laboratorio.models import Estudio, PerfilLaboratorio

# Origen de recepción (mismos valores que laboratorio.Orden; evita depender del modelo legacy)
_ORIGEN_PUBLICO_GENERAL = 'PUBLICO_GENERAL'
_ORIGEN_CHOICES = [
    (_ORIGEN_PUBLICO_GENERAL, 'Público General'),
    ('CONVENIO', 'Convenio'),
    ('SEGURO', 'Seguro'),
    ('OTRO', 'Otro'),
]
from core.models import OrdenDeServicio, DetalleOrden as CoreDetalleOrden, Paciente
from lims.models import PerfilLims, Analito

from laboratorio.services.unificacion import (
    crear_paciente_unificado,
    buscar_pacientes_unificado,
)

# Re-export etiquetas
from laboratorio.views.etiquetas import *


@login_required
def recepcion_lab(request):
    """
    Vista para crear una nueva orden de laboratorio.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Tu usuario no tiene una empresa asignada. Contacta al administrador.')
        return redirect('home')
    estudios = Estudio.objects.all().order_by('nombre')
    perfiles = PerfilLaboratorio.objects.filter(activo=True).select_related('area_pertenencia').order_by('area_pertenencia__nombre', 'nombre')
    medicos = Medico.objects.filter(activo=True).order_by('nombre')
    origenes = _ORIGEN_CHOICES

    if request.method == 'POST':
        try:
            with transaction.atomic():
                paciente_id = request.POST.get('paciente_id')
                medico_id = request.POST.get('medico_id')
                medico_texto = request.POST.get('medico_texto', '').strip()
                origen = request.POST.get('origen', _ORIGEN_PUBLICO_GENERAL)
                estudios_seleccionados_ids = request.POST.getlist('estudios')
                perfiles_seleccionados_ids = request.POST.getlist('perfiles')

                if not paciente_id or (not estudios_seleccionados_ids and not perfiles_seleccionados_ids):
                    messages.error(request, "Debes seleccionar un paciente y al menos un estudio o perfil.")
                    return render(request, 'laboratorio/crear_orden.html', {
                        'estudios': estudios,
                        'perfiles': perfiles,
                        'medicos': medicos,
                        'origenes': origenes,
                    })

                from decimal import Decimal as _Dec

                sucursal = get_request_sucursal(request)
                try:
                    core_paciente = Paciente.objects.select_for_update().get(
                        pk=int(paciente_id),
                        empresa=empresa,
                        activo=True,
                    )
                except (Paciente.DoesNotExist, ValueError):
                    messages.error(
                        request,
                        'Paciente no encontrado o no pertenece a su empresa.',
                    )
                    return render(request, 'laboratorio/crear_orden.html', {
                        'estudios': estudios,
                        'perfiles': perfiles,
                        'medicos': medicos,
                        'origenes': origenes,
                    })

                total_orden = _Dec('0')
                estudios_agregados_por_perfil = {}
                estudios_duplicados = []

                nueva_orden = OrdenDeServicio.objects.create(
                    empresa=empresa,
                    sucursal=sucursal,
                    paciente=core_paciente,
                    responsable_ingreso=request.user,
                    total=_Dec('0'),
                    anticipo=_Dec('0'),
                    estado='PENDIENTE_PAGO',
                    estado_pago='PENDIENTE',
                    estado_clinico='PENDIENTE_TOMA',
                    notas_internas=(medico_texto or '')[:500] if medico_texto else None,
                )

                for perfil_id in perfiles_seleccionados_ids:
                    try:
                        perfil = PerfilLaboratorio.objects.get(id=perfil_id, activo=True)
                        pl = PerfilLims.objects.filter(
                            nombre__iexact=perfil.nombre.strip(), empresa=empresa
                        ).first()
                        CoreDetalleOrden.objects.create(
                            orden=nueva_orden,
                            perfil_lims=pl,
                            descripcion_linea=(perfil.nombre or 'Perfil')[:300],
                            precio_momento=perfil.precio or _Dec('0'),
                        )
                        total_orden += perfil.precio or _Dec('0')
                        estudios_agregados_por_perfil[perfil.nombre] = {'agregados': 1, 'duplicados': [], 'precio_total': perfil.precio}
                    except PerfilLaboratorio.DoesNotExist:
                        messages.warning(request, 'Un perfil seleccionado no existe o está inactivo.')

                estudios_objs = Estudio.objects.filter(id__in=estudios_seleccionados_ids)
                for estudio in estudios_objs:
                    an = Analito.objects.filter(
                        nombre__iexact=estudio.nombre.strip(), activo=True, empresa=empresa
                    ).first()
                    precio_al_momento = estudio.precio_base or _Dec('0')
                    CoreDetalleOrden.objects.create(
                        orden=nueva_orden,
                        analito=an,
                        descripcion_linea=(estudio.nombre or '')[:300],
                        precio_momento=precio_al_momento,
                    )
                    total_orden += precio_al_momento

                nueva_orden.total = total_orden
                nueva_orden.save(update_fields=['total'])

                folio = nueva_orden.folio_orden or nueva_orden.id
                msg = f'Orden LIMS {folio} creada (core). Total: ${total_orden:.2f}'
                if estudios_agregados_por_perfil:
                    msg += f" | Perfiles: {', '.join(estudios_agregados_por_perfil.keys())}"
                messages.success(request, msg)
                return redirect('recepcion_lab')
        except (DatabaseError, ValidationError) as e:
            messages.error(request, f"Error al crear la orden: {str(e)}")

    cotizacion_flash = request.session.get('cotizacion_flash', None)
    paciente_precargado = None
    estudios_precargados = []
    perfiles_precargados = []

    if cotizacion_flash:
        try:
            paciente_id = cotizacion_flash.get('paciente_id')
            estudios_ids = cotizacion_flash.get('estudios_ids', [])
            perfiles_ids = cotizacion_flash.get('perfiles_ids', [])
            if paciente_id:
                paciente_precargado = Paciente.objects.filter(
                    id=paciente_id, empresa=empresa, activo=True
                ).first()
            if estudios_ids:
                estudios_precargados = list(Estudio.objects.filter(id__in=estudios_ids).values_list('id', flat=True))
            if perfiles_ids:
                perfiles_precargados = list(PerfilLaboratorio.objects.filter(id__in=perfiles_ids).values_list('id', flat=True))
            del request.session['cotizacion_flash']
        except (KeyError, TypeError):
            pass

    context = {
        'estudios': estudios,
        'perfiles': perfiles,
        'medicos': medicos,
        'origenes': origenes,
        'paciente_precargado': paciente_precargado,
        'estudios_precargados': estudios_precargados,
        'perfiles_precargados': perfiles_precargados,
        'empresa': empresa,
    }
    return render(request, 'laboratorio/crear_orden.html', context)


@login_required
@require_http_methods(["POST"])
def crear_paciente_ajax(request):
    """
    Endpoint AJAX para crear un nuevo paciente desde el modal.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({
            'success': False,
            'error': 'Usuario sin empresa asignada.',
        }, status=403)
    try:
        data = json.loads(request.body)

        def safe_strip(value, default=''):
            if value is None:
                return default
            return str(value).strip() if value else default

        nombres = safe_strip(data.get('nombres'))
        apellidos = safe_strip(data.get('apellidos'))
        fecha_nacimiento_str = safe_strip(data.get('fecha_nacimiento'))
        sexo = safe_strip(data.get('sexo'))

        telefono_val = data.get('telefono')
        telefono = safe_strip(telefono_val) if telefono_val is not None else None
        telefono = telefono if telefono else None

        email_val = data.get('email')
        email = safe_strip(email_val) if email_val is not None else None
        email = email if email else None

        if not nombres or not apellidos or not fecha_nacimiento_str or not sexo:
            return JsonResponse({
                'success': False,
                'error': 'Faltan campos obligatorios: nombres, apellidos, fecha de nacimiento y sexo.'
            }, status=400)

        if sexo not in (Paciente.SEXO_MASCULINO, Paciente.SEXO_FEMENINO):
            return JsonResponse({
                'success': False,
                'error': 'Sexo invalido. Debe ser M (Masculino) o F (Femenino).'
            }, status=400)

        try:
            fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date()
        except (ValueError, TypeError) as e:
            return JsonResponse({
                'success': False,
                'error': f'Fecha de nacimiento invalida. Formato esperado: YYYY-MM-DD. Error: {str(e)}'
            }, status=400)

        try:
            sucursal = get_request_sucursal(request)
            resultado = crear_paciente_unificado(
                empresa=empresa,
                sucursal=sucursal,
                datos={
                    'nombres': nombres,
                    'apellidos': apellidos,
                    'fecha_nacimiento': fecha_nacimiento,
                    'sexo': sexo,
                    'telefono': telefono,
                    'email': email,
                }
            )
            paciente = resultado['core']
        except (DatabaseError, ValidationError) as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al crear el paciente: {str(e)}'
            }, status=500)

        ap_display = (
            f'{paciente.apellido_paterno} {paciente.apellido_materno}'.strip()
        )
        return JsonResponse({
            'success': True,
            'paciente': {
                'id': paciente.id,
                'fuente': 'core',
                'codigo': getattr(paciente, 'pris_id', '') or '',
                'nombre_completo': paciente.nombre_completo,
                'nombres': paciente.nombres,
                'apellidos': ap_display,
                'telefono': paciente.telefono or '',
                'email': paciente.email or '',
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Error al procesar los datos JSON.'
        }, status=400)
    except (DatabaseError, ValidationError) as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def crear_medico_ajax(request):
    """
    Endpoint AJAX para crear un nuevo medico desde el modal.
    Crea en core.models.Medico (modelo maestro con empresa y cédula).
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({
            'success': False,
            'error': 'Usuario sin empresa asignada.',
        }, status=403)
    try:
        data = json.loads(request.body)
        nombre = data.get('nombre', '').strip()
        especialidad = data.get('especialidad', '').strip() or 'Médico General'
        cedula = data.get('cedula_profesional', '').strip()

        if not nombre:
            return JsonResponse({
                'success': False,
                'error': 'El nombre del medico es obligatorio.'
            }, status=400)

        from core.models import Medico as CoreMedico

        if not cedula:
            import uuid as _uuid
            cedula = f"PEND-{_uuid.uuid4().hex[:8].upper()}"

        existing = CoreMedico.objects.filter(cedula_profesional=cedula, empresa=empresa).first()
        if existing:
            return JsonResponse({
                'success': True,
                'medico': {
                    'id': existing.id,
                    'nombre': existing.nombre_completo,
                    'nombre_completo': existing.nombre_completo,
                    'especialidad': existing.especialidad or '',
                }
            })

        medico = CoreMedico.objects.create(
            empresa=empresa,
            nombre_completo=nombre,
            cedula_profesional=cedula,
            especialidad=especialidad,
        )

        return JsonResponse({
            'success': True,
            'medico': {
                'id': medico.id,
                'nombre': medico.nombre_completo,
                'nombre_completo': medico.nombre_completo,
                'especialidad': medico.especialidad or '',
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Error al procesar los datos JSON.'
        }, status=400)
    except (DatabaseError, ValidationError) as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def buscar_estudios_ajax(request):
    """
    Endpoint AJAX para buscar estudios por nombre, codigo o categoria (para Select2).
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'estudios': []})
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'estudios': []})

    estudios = Estudio.objects.filter(
        Q(nombre__icontains=query) |
        Q(codigo__icontains=query)
    ).order_by('nombre')[:20]

    resultados = []
    for estudio in estudios:
        resultados.append({
            'id': estudio.id,
            'text': estudio.nombre,
            'nombre': estudio.nombre,
            'codigo': estudio.codigo or '',
            'categoria': estudio.categoria.nombre,
            'precio': float(estudio.precio_base),
            'unidades': estudio.unidades or '',
            'dias_entrega': estudio.dias_entrega or '',
        })

    return JsonResponse({'estudios': resultados})


@login_required
@require_http_methods(["GET"])
def buscar_pacientes_ajax(request):
    """
    Endpoint AJAX para buscar pacientes por nombre o codigo (autocomplete).
    Búsqueda en core.Paciente (tenant).
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'pacientes': []})
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'pacientes': []})

    resultados = buscar_pacientes_unificado(empresa, query, limit=20)
    return JsonResponse({'pacientes': resultados})
