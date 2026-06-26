"""
Módulo de Contabilidad - PRISLAB
Gestión de catálogo de cuentas, pólizas contables y movimientos.
"""
from decimal import Decimal
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from contabilidad.models import CuentaContable, Poliza, AsientoContable
from core.decorators import role_required
from core.models import Empresa
from core.utils.trazabilidad import registrar_trazabilidad
import logging


TIPOS_CUENTA_NATURALEZA = {
    'ACTIVO': 'DEUDOR',
    'PASIVO': 'ACREEDOR',
    'CAPITAL': 'ACREEDOR',
    'INGRESO': 'ACREEDOR',
    'COSTO': 'DEUDOR',
    'GASTO': 'DEUDOR',
}


def _empresa_contable(request):
    """Devuelve la empresa efectiva o redirige a home."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return None
    return empresa


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def dashboard_contabilidad(request):
    """Dashboard de contabilidad con datos reales del mes y del catálogo."""
    empresa = _empresa_contable(request)
    if not empresa:
        return redirect('home')

    hoy = timezone.localdate()
    mes_inicio = hoy.replace(day=1)

    # Ingresos y gastos del mes
    ingresos_mes = Decimal('0')
    ventas_count = 0
    try:
        from core.models import Venta
        agg = Venta.objects.filter(
            empresa=empresa, fecha__date__gte=mes_inicio, estado='COMPLETADA'
        ).aggregate(total=Sum('total'), count=Count('id'))
        ingresos_mes = agg['total'] or Decimal('0')
        ventas_count = agg['count'] or 0
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en dashboard_contabilidad (contabilidad.py)")
        pass

    gastos_mes = Decimal('0')
    gastos_count = 0
    try:
        from core.models import GastoCaja
        agg = GastoCaja.objects.filter(
            empresa=empresa, fecha__date__gte=mes_inicio
        ).aggregate(total=Sum('monto'), count=Count('id'))
        gastos_mes = agg['total'] or Decimal('0')
        gastos_count = agg['count'] or 0
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en dashboard_contabilidad (contabilidad.py)")
        pass

    # Ordenes de lab pagadas
    ordenes_mes = Decimal('0')
    try:
        from core.models import OrdenDeServicio
        ordenes_mes = OrdenDeServicio.objects.filter(
            empresa=empresa, fecha_creacion__date__gte=mes_inicio, estado_pago='PAGADO'
        ).aggregate(t=Sum('total'))['t'] or Decimal('0')
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en dashboard_contabilidad (contabilidad.py)")
        pass

    ingreso_total = ingresos_mes + ordenes_mes
    utilidad_mes = ingreso_total - gastos_mes

    # Cuentas y pólizas
    total_cuentas = CuentaContable.objects.filter(empresa=empresa, activa=True).count()
    total_polizas = Poliza.objects.filter(empresa=empresa).count()
    polizas_borrador = Poliza.objects.filter(empresa=empresa, estado='BORRADOR').count()
    polizas_autorizadas = Poliza.objects.filter(empresa=empresa, estado='AUTORIZADA').count()
    polizas_recientes = Poliza.objects.filter(empresa=empresa).select_related('creado_por')[:5]

    # CFDI pendientes (FacturaCFDI + FacturaSAT)
    cfdi_pendientes = 0
    try:
        from contabilidad.models import FacturaCFDI
        cfdi_pendientes += FacturaCFDI.objects.filter(
            empresa=empresa, estado__in=['BORRADOR', 'PENDIENTE', 'ERROR']
        ).count()
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en dashboard_contabilidad (contabilidad.py)")
        pass
    try:
        from core.models import FacturaSAT
        cfdi_pendientes += FacturaSAT.objects.filter(
            empresa=empresa, estatus=FacturaSAT.ESTATUS_BORRADOR
        ).count()
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en dashboard_contabilidad (contabilidad.py)")
        pass

    return render(request, 'core/contabilidad/dashboard.html', {
        'empresa': empresa,
        'ingresos_mes': ingresos_mes,
        'ingreso_total': ingreso_total,
        'gastos_mes': gastos_mes,
        'utilidad_mes': utilidad_mes,
        'ventas_count': ventas_count,
        'gastos_count': gastos_count,
        'cfdi_pendientes': cfdi_pendientes,
        'mes_nombre': mes_inicio.strftime('%B %Y'),
        'total_cuentas': total_cuentas,
        'total_polizas': total_polizas,
        'polizas_abiertas': polizas_borrador,
        'polizas_autorizadas': polizas_autorizadas,
        'polizas_recientes': polizas_recientes,
        'movimientos_mes': {'total_debe': ingreso_total, 'total_haber': gastos_mes},
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def catalogo_cuentas(request):
    """Lista paginada del catálogo de cuentas."""
    empresa = _empresa_contable(request)
    if not empresa:
        return redirect('home')

    q = request.GET.get('q', '').strip()
    cuentas = CuentaContable.objects.filter(empresa=empresa)
    if q:
        cuentas = cuentas.filter(
            Q(codigo__icontains=q) | Q(nombre__icontains=q)
        )
    cuentas = cuentas.order_by('codigo')

    paginator = Paginator(cuentas, 30)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'core/contabilidad/catalogo_cuentas.html', {
        'page_obj': page,
        'q': q,
        'tipos': CuentaContable.TIPO_CHOICES,
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
@require_http_methods(["GET", "POST"])
def crear_cuenta(request):
    """Crear una cuenta contable."""
    empresa = _empresa_contable(request)
    if not empresa:
        return redirect('home')

    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip().upper()
        nombre = request.POST.get('nombre', '').strip()
        tipo = request.POST.get('tipo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        if not codigo or not nombre or tipo not in dict(CuentaContable.TIPO_CHOICES):
            messages.error(request, 'Código, nombre y tipo válidos son obligatorios.')
        elif CuentaContable.objects.filter(empresa=empresa, codigo=codigo).exists():
            messages.error(request, f'Ya existe una cuenta con código {codigo}.')
        else:
            CuentaContable.objects.create(
                empresa=empresa,
                codigo=codigo,
                nombre=nombre,
                tipo=tipo,
                naturaleza=TIPOS_CUENTA_NATURALEZA.get(tipo, 'DEUDOR'),
                descripcion=descripcion,
            )
            messages.success(request, f'Cuenta {codigo} - {nombre} creada.')
            return redirect('contabilidad:catalogo_cuentas')

    return render(request, 'core/contabilidad/crear_cuenta.html', {
        'tipos': CuentaContable.TIPO_CHOICES,
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def lista_polizas(request):
    """Lista paginada de pólizas contables."""
    empresa = _empresa_contable(request)
    if not empresa:
        return redirect('home')

    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    polizas = Poliza.objects.filter(empresa=empresa)
    if q:
        polizas = polizas.filter(
            Q(folio__icontains=q) | Q(concepto__icontains=q)
        )
    if estado in dict(Poliza.ESTADO_CHOICES):
        polizas = polizas.filter(estado=estado)

    polizas = polizas.select_related('creado_por', 'autorizado_por').order_by('-fecha', '-fecha_creacion')
    paginator = Paginator(polizas, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'core/contabilidad/lista_polizas.html', {
        'page_obj': page,
        'q': q,
        'estado': estado,
        'estados': Poliza.ESTADO_CHOICES,
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
@require_http_methods(["GET", "POST"])
def crear_poliza(request):
    """Crear una póliza contable con sus asientos (partida doble mínima)."""
    empresa = _empresa_contable(request)
    if not empresa:
        return redirect('home')

    cuentas = CuentaContable.objects.filter(empresa=empresa, activa=True).order_by('codigo')

    if request.method == 'POST':
        tipo = request.POST.get('tipo', 'DIARIO')
        concepto = request.POST.get('concepto', '').strip()
        fecha_str = request.POST.get('fecha', '')
        fecha = timezone.localdate()
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        lineas = []
        total_cargo = Decimal('0')
        total_abono = Decimal('0')
        i = 0
        while True:
            cuenta_id = request.POST.get(f'cuenta_{i}')
            cargo = request.POST.get(f'cargo_{i}', '0')
            abono = request.POST.get(f'abono_{i}', '0')
            if cuenta_id is None:
                break
            try:
                cargo_d = Decimal(str(cargo)) if cargo else Decimal('0')
                abono_d = Decimal(str(abono)) if abono else Decimal('0')
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en crear_poliza (contabilidad.py)")
                cargo_d = Decimal('0')
                abono_d = Decimal('0')
            if cargo_d > 0 or abono_d > 0:
                lineas.append((cuenta_id, cargo_d, abono_d))
                total_cargo += cargo_d
                total_abono += abono_d
            i += 1

        if tipo not in dict(Poliza.TIPO_CHOICES):
            messages.error(request, 'Tipo de póliza no válido.')
        elif not concepto:
            messages.error(request, 'El concepto es obligatorio.')
        elif not lineas:
            messages.error(request, 'La póliza debe tener al menos un asiento.')
        elif total_cargo != total_abono:
            messages.error(
                request,
                f'La póliza no cuadra: cargo ${total_cargo} vs abono ${total_abono}.'
            )
        else:
            try:
                with transaction.atomic():
                    poliza = Poliza.objects.create(
                        empresa=empresa,
                        tipo=tipo,
                        concepto=concepto,
                        fecha=fecha,
                        creado_por=request.user,
                    )
                    for cuenta_id, cargo_d, abono_d in lineas:
                        cuenta = CuentaContable.objects.get(id=cuenta_id, empresa=empresa)
                        AsientoContable.objects.create(
                            poliza=poliza,
                            cuenta=cuenta,
                            cargo=cargo_d,
                            abono=abono_d,
                        )
                messages.success(request, f'Póliza {poliza.folio} creada correctamente.')
                return redirect('contabilidad:ver_poliza', poliza_id=poliza.id)
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en crear_poliza (contabilidad.py)")
                messages.error(request, f'Error al crear la póliza: {e}')

    return render(request, 'core/contabilidad/crear_poliza.html', {
        'cuentas': cuentas,
        'tipos': Poliza.TIPO_CHOICES,
        'hoy': timezone.localdate().isoformat(),
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def ver_poliza(request, poliza_id):
    """Detalle de una póliza contable."""
    empresa = _empresa_contable(request)
    if not empresa:
        return redirect('home')

    poliza = get_object_or_404(Poliza, id=poliza_id, empresa=empresa)
    asientos = poliza.asientos.select_related('cuenta')

    return render(request, 'core/contabilidad/ver_poliza.html', {
        'poliza': poliza,
        'asientos': asientos,
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
@require_http_methods(["POST"])
def autorizar_poliza(request, poliza_id):
    """Autoriza una póliza en estado BORRADOR."""
    empresa = _empresa_contable(request)
    if not empresa:
        return redirect('home')

    poliza = get_object_or_404(Poliza, id=poliza_id, empresa=empresa)
    if poliza.estado != 'BORRADOR':
        messages.error(request, 'Solo se pueden autorizar pólizas en borrador.')
    else:
        poliza.estado = 'AUTORIZADA'
        poliza.autorizado_por = request.user
        poliza.fecha_autorizacion = timezone.now()
        poliza.save()
        registrar_trazabilidad(
            tipo_operacion='AUTORIZAR_POLIZA',
            modulo='CONTABILIDAD',
            referencia_id=poliza.id,
            referencia_tipo='Poliza',
            accion='AUTORIZAR',
            descripcion=f'Póliza {poliza.folio} autorizada.',
            usuario=request.user,
            empresa=empresa,
            request=request,
        )
        messages.success(request, f'Póliza {poliza.folio} autorizada.')
    return redirect('contabilidad:ver_poliza', poliza_id=poliza.id)


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
@require_http_methods(["GET"])
def api_cuentas(request):
    """API JSON para buscar cuentas contables (autocomplete)."""
    empresa = _empresa_contable(request)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa'}, status=403)

    q = request.GET.get('q', '').strip()
    qs = CuentaContable.objects.filter(empresa=empresa, activa=True)
    if q:
        qs = qs.filter(Q(codigo__icontains=q) | Q(nombre__icontains=q))
    cuentas = [
        {'id': c.id, 'codigo': c.codigo, 'nombre': c.nombre, 'tipo': c.tipo}
        for c in qs[:50]
    ]
    return JsonResponse({'cuentas': cuentas})


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def reporte_fiscal(request):
    """Redirige al reporte fiscal mensual disponible."""
    return redirect('reporte_fiscal')