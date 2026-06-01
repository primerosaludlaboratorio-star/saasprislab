"""
Catálogos operativos (médicos, convenios). Estudios/pruebas: solo LIMS v7.5 (app lims).
"""
import logging
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render

from core.decorators import role_required
from core.models import Convenio, ConvenioPrecioLims, Empresa, Medico
from lims.models import Analito

logger = logging.getLogger('core')

try:
    from core.models import ClienteCRM
except ImportError:
    ClienteCRM = None


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def lista_estudios(request):
    """Catálogo de pruebas: redirige al admin LIMS (única fuente de verdad)."""
    return redirect('/admin/lims/analito/')


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def editar_estudio(request, estudio_id):
    return redirect('/admin/lims/analito/')


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def api_vincular_componentes(request):
    return JsonResponse(
        {'status': 'error', 'mensaje': 'Use el admin LIMS para componer perfiles y paquetes.'},
        status=410,
    )


@login_required
def catalogo_medicos(request):
    """Catálogo maestro de médicos (creación básica)."""
    try:
        empresa = getattr(request.user, 'empresa', None)

        if request.method == 'POST':
            nombre = (request.POST.get('nombre_completo') or '').strip()
            cedula = (request.POST.get('cedula_profesional') or '').strip()
            especialidad = (request.POST.get('especialidad') or 'Médico General').strip()

            if not nombre or not cedula:
                return JsonResponse({'status': 'error', 'mensaje': 'Nombre y cédula son obligatorios'}, status=400)

            medico, creado = Medico.objects.get_or_create(
                cedula_profesional=cedula,
                defaults={'nombre_completo': nombre, 'especialidad': especialidad, 'empresa': empresa},
            )
            if not creado:
                medico.nombre_completo = nombre
                medico.especialidad = especialidad
                if empresa:
                    medico.empresa = empresa
                medico.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'mensaje': 'Médico guardado', 'medico_id': medico.id})
            return redirect('catalogo_medicos')

        medicos = Medico.objects.filter(empresa=empresa).order_by('nombre_completo') if empresa else Medico.objects.none()
        return render(request, 'core/catalogos/medicos.html', {'empresa': empresa, 'medicos': medicos})
    except Exception as e:
        logger.error('Error en catalogo_medicos: %s', e, exc_info=True)
        return render(
            request,
            'core/catalogos/medicos.html',
            {'empresa': getattr(request.user, 'empresa', None), 'medicos': [], 'error': str(e)},
        )


@login_required
def catalogo_convenios(request):
    """Catálogo maestro de convenios (por médico o empresa)."""
    try:
        empresa = getattr(request.user, 'empresa', None)

        if request.method == 'POST':
            nombre = (request.POST.get('nombre') or '').strip()
            tipo_raw = (request.POST.get('tipo') or 'EMPRESA').strip()
            tipo = tipo_raw if tipo_raw in ('EMPRESA', 'ASEGURADORA', 'GOBIERNO', 'ONG') else 'EMPRESA'
            descuento = request.POST.get('descuento_porcentaje') or '0'
            medico_id = request.POST.get('medico_id') or None
            cliente_id = request.POST.get('cliente_crm_id') or None

            if not nombre:
                return JsonResponse({'status': 'error', 'mensaje': 'Nombre del convenio es obligatorio'}, status=400)

            Medico.objects.filter(id=medico_id).first() if medico_id else None
            if ClienteCRM and cliente_id and empresa:
                ClienteCRM.objects.filter(id=cliente_id, empresa=empresa).first()

            try:
                descuento_dec = Decimal(str(descuento))
            except Exception:
                descuento_dec = 0

            Convenio.objects.create(
                empresa=empresa,
                nombre=nombre,
                tipo=tipo,
                descuento_porcentaje=descuento_dec,
                activo=True,
            )

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'mensaje': 'Convenio creado'})
            return redirect('catalogo_convenios')

        convenios = Convenio.objects.filter(empresa=empresa).order_by('nombre')
        medicos = Medico.objects.filter(empresa=empresa).order_by('nombre_completo') if empresa else Medico.objects.none()
        clientes = ClienteCRM.objects.filter(empresa=empresa).order_by('nombre_completo')[:500] if ClienteCRM and empresa else []

        return render(
            request,
            'core/catalogos/convenios.html',
            {'empresa': empresa, 'convenios': convenios, 'medicos': medicos, 'clientes': clientes},
        )

    except Exception as e:
        logger.error('Error en catalogo_convenios: %s', e, exc_info=True)
        return render(
            request,
            'core/catalogos/convenios.html',
            {'empresa': getattr(request.user, 'empresa', None), 'convenios': [], 'error': str(e)},
        )


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def convenio_precios(request, convenio_id: int):
    """Precios especiales por analito LIMS para un convenio."""
    empresa = getattr(request.user, 'empresa', None)
    convenio = Convenio.objects.filter(id=convenio_id, empresa=empresa).first()
    if not convenio:
        return render(request, 'core/error.html', {'mensaje': 'Convenio no encontrado'}, status=404)

    if request.method == 'POST':
        with transaction.atomic():
            for key, val in request.POST.items():
                if not key.startswith('precio_a_'):
                    continue
                try:
                    analito_id = int(key.replace('precio_a_', ''))
                except ValueError:
                    continue
                val = (val or '').strip()
                q = ConvenioPrecioLims.objects.filter(convenio=convenio, analito_id=analito_id)
                if val == '':
                    q.delete()
                    continue
                try:
                    precio = Decimal(str(val))
                except Exception:
                    continue
                obj, created = ConvenioPrecioLims.objects.get_or_create(
                    convenio=convenio,
                    analito_id=analito_id,
                    defaults={'precio_convenio': precio, 'perfil_lims_id': None, 'paquete_lims_id': None},
                )
                if not created:
                    obj.precio_convenio = precio
                    obj.save(update_fields=['precio_convenio'])

        return redirect('convenio_precios', convenio_id=convenio.id)

    from core.lims_cart import precio_publico_analito

    analitos = (
        Analito.objects.filter(activo=True, empresa=empresa)
        .order_by('departamento', 'nombre')[:800]
    )
    precios_existentes = {
        p.analito_id: p for p in ConvenioPrecioLims.objects.filter(convenio=convenio, analito__isnull=False)
    }
    filas = []
    for a in analitos:
        filas.append({
            'analito': a,
            'precio_publico': precio_publico_analito(a, empresa=empresa),
            'precio_obj': precios_existentes.get(a.id),
        })

    return render(
        request,
        'core/catalogos/convenio_precios.html',
        {'empresa': empresa, 'convenio': convenio, 'filas': filas},
    )
