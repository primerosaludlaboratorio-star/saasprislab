"""
core/views/autofactura.py
══════════════════════════
Portal público de Autofacturación CFDI 4.0
El paciente llega desde el QR del ticket, captura sus datos fiscales
y el sistema registra la solicitud en FacturaSAT (BORRADOR).
El equipo de facturación timbra desde el módulo interno.

URL pública: /facturacion/autofactura/?folio=VTA-0001
"""
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from django.contrib.auth.decorators import login_required

logger = logging.getLogger('core.autofactura')

# Catálogos SAT (subset más frecuente)
REGIMENES_FISCALES = [
    ('601', 'General de Ley Personas Morales'),
    ('603', 'Personas Morales con Fines no Lucrativos'),
    ('605', 'Sueldos y Salarios e Ingresos Asimilados a Salarios'),
    ('606', 'Arrendamiento'),
    ('607', 'Régimen de Enajenación o Adquisición de Bienes'),
    ('608', 'Demás ingresos'),
    ('609', 'Consolidación'),
    ('610', 'Residentes en el Extranjero sin Establecimiento en México'),
    ('611', 'Ingresos por Dividendos'),
    ('612', 'Personas Físicas con Actividades Empresariales y Profesionales'),
    ('614', 'Ingresos por intereses'),
    ('615', 'Régimen de los ingresos por obtención de premios'),
    ('616', 'Sin obligaciones fiscales'),
    ('620', 'Sociedades Cooperativas de Producción'),
    ('621', 'Incorporación Fiscal'),
    ('622', 'Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
    ('623', 'Opcional para Grupos de Sociedades'),
    ('624', 'Coordinados'),
    ('625', 'Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas'),
    ('626', 'Régimen Simplificado de Confianza'),
]

USOS_CFDI = [
    ('G01', 'Adquisición de mercancias'),
    ('G02', 'Devoluciones, descuentos o bonificaciones'),
    ('G03', 'Gastos en general'),
    ('I01', 'Construcciones'),
    ('I02', 'Mobiliario y equipo de oficina por inversiones'),
    ('I03', 'Equipo de transporte'),
    ('I04', 'Equipo de computo y accesorios'),
    ('I05', 'Dados, troqueles, moldes, matrices y herramental'),
    ('I06', 'Comunicaciones telefónicas'),
    ('I07', 'Comunicaciones satelitales'),
    ('I08', 'Otra maquinaria y equipo'),
    ('D01', 'Honorarios médicos, dentales y gastos hospitalarios'),
    ('D02', 'Gastos médicos por incapacidad o discapacidad'),
    ('D03', 'Gastos funerales'),
    ('D04', 'Donativos'),
    ('D05', 'Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación)'),
    ('D06', 'Aportaciones voluntarias al SAR'),
    ('D07', 'Primas por seguros de gastos médicos'),
    ('D08', 'Gastos de transportación escolar obligatoria'),
    ('D09', 'Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones'),
    ('D10', 'Pagos por servicios educativos (colegiaturas)'),
    ('S01', 'Sin efectos fiscales'),
    ('CP01', 'Pagos'),
    ('CN01', 'Nómina'),
]


def autofactura_publica(request):
    """
    Portal público: el paciente captura sus datos fiscales para solicitar su CFDI.
    No requiere login. Protegido por CSRF.
    Acepta GET (mostrar formulario) y POST (procesar solicitud).
    """
    folio = request.GET.get('folio', '').strip() or request.POST.get('folio', '').strip()
    venta = None
    empresa = None
    error_folio = None
    exito = False
    factura_existente = None

    # ── Buscar la venta por folio ──────────────────────────────────────────────
    if folio:
        try:
            from core.models import Venta
            venta = (
                Venta.objects
                .select_related('empresa', 'paciente')
                .filter(folio_operacion=folio, estado='COMPLETADA')
                .first()
            )
            if not venta:
                error_folio = f'No encontramos ninguna venta con el folio "{folio}". Verifica el ticket.'
            else:
                empresa = venta.empresa
                # Verificar si ya tiene una factura registrada
                from core.models import FacturaSAT
                factura_existente = FacturaSAT.objects.filter(venta=venta).first()
        except Exception as e:
            logger.warning('autofactura_publica: error buscando folio %s: %s', folio, e)
            error_folio = 'Error al buscar el folio. Intenta de nuevo.'

    # ── Procesar formulario POST ───────────────────────────────────────────────
    if request.method == 'POST' and venta and not error_folio:
        rfc = request.POST.get('rfc', '').strip().upper()
        razon_social = request.POST.get('razon_social', '').strip().upper()
        cp = request.POST.get('cp', '').strip()
        regimen = request.POST.get('regimen_fiscal', '').strip()
        uso = request.POST.get('uso_cfdi', '').strip()
        email = request.POST.get('email', '').strip()

        # Validación mínima
        errores_form = []
        if not rfc or len(rfc) < 12:
            errores_form.append('El RFC debe tener al menos 12 caracteres.')
        if not razon_social:
            errores_form.append('La razón social es obligatoria.')
        if not cp or len(cp) != 5:
            errores_form.append('El código postal debe tener exactamente 5 dígitos.')
        if not regimen:
            errores_form.append('Selecciona tu régimen fiscal.')
        if not uso:
            errores_form.append('Selecciona el uso del CFDI.')

        if not errores_form:
            try:
                from core.models import FacturaSAT
                # Idempotente: si ya existe, actualizar datos
                factura, created = FacturaSAT.objects.update_or_create(
                    venta=venta,
                    defaults={
                        'empresa': empresa,
                        'paciente': venta.paciente,
                        'folio': venta.folio_operacion,
                        'estatus': FacturaSAT.ESTATUS_BORRADOR,
                    }
                )
                # Guardar datos fiscales como JSON en el campo uuid (reutilizamos como metadata
                # hasta integrar PAC — no afecta el timbrado real)
                import json
                datos_fiscales = {
                    'rfc': rfc,
                    'razon_social': razon_social,
                    'cp': cp,
                    'regimen_fiscal': regimen,
                    'uso_cfdi': uso,
                    'email': email,
                    'fecha_solicitud': timezone.now().isoformat(),
                    'ip': request.META.get('REMOTE_ADDR', ''),
                }
                factura.uuid = json.dumps(datos_fiscales)
                factura.save()

                logger.info(
                    'autofactura_publica: solicitud registrada — venta=%s rfc=%s',
                    venta.id, rfc
                )
                exito = True
                factura_existente = factura
            except Exception as e:
                logger.error('autofactura_publica: error guardando solicitud: %s', e, exc_info=True)
                errores_form.append('Error interno al registrar la solicitud. Intenta de nuevo.')

        return render(request, 'core/autofactura_publica.html', {
            'folio': folio,
            'venta': venta,
            'empresa': empresa,
            'error_folio': error_folio,
            'exito': exito,
            'factura_existente': factura_existente,
            'errores_form': errores_form,
            'regimenes': REGIMENES_FISCALES,
            'usos_cfdi': USOS_CFDI,
            # Pre-poblar con datos enviados
            'form_data': request.POST,
        })

    return render(request, 'core/autofactura_publica.html', {
        'folio': folio,
        'venta': venta,
        'empresa': empresa,
        'error_folio': error_folio,
        'exito': exito,
        'factura_existente': factura_existente,
        'errores_form': [],
        'regimenes': REGIMENES_FISCALES,
        'usos_cfdi': USOS_CFDI,
        'form_data': {},
    })


@login_required
def bandeja_cfdi(request):
    """
    Bandeja interna (staff/director) para ver solicitudes de autofacturación
    en estado BORRADOR y procesarlas.
    """
    from django.shortcuts import redirect
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Sin empresa asignada.')
        return redirect('home')

    from core.models import FacturaSAT
    estado_filtro = request.GET.get('estado', 'BORRADOR')
    facturas = (
        FacturaSAT.objects
        .select_related('venta', 'paciente')
        .filter(empresa=empresa)
        .order_by('-fecha_creacion')
    )
    if estado_filtro != 'TODAS':
        facturas = facturas.filter(estatus=estado_filtro)

    # Parsear datos fiscales del campo uuid (guardado como JSON)
    facturas_data = []
    for f in facturas[:100]:
        datos = {}
        try:
            if f.uuid:
                datos = json.loads(f.uuid)
        except Exception:
            pass
        facturas_data.append({'factura': f, 'datos': datos})

    pendientes = FacturaSAT.objects.filter(
        empresa=empresa, estatus=FacturaSAT.ESTATUS_BORRADOR
    ).count()

    return render(request, 'core/facturacion/bandeja_cfdi.html', {
        'facturas_data': facturas_data,
        'estado_filtro': estado_filtro,
        'pendientes': pendientes,
        'empresa': empresa,
    })


@login_required
@require_http_methods(['POST'])
def api_marcar_cfdi_timbrada(request, factura_id: int):
    """Marca una FacturaSAT como TIMBRADA (manual, hasta integrar PAC)."""
    from django.shortcuts import get_object_or_404
    empresa = getattr(request.user, 'empresa', None)
    from core.models import FacturaSAT
    factura = get_object_or_404(FacturaSAT, id=factura_id, empresa=empresa)
    uuid_cfdi = request.POST.get('uuid_cfdi', '').strip()
    factura.estatus = FacturaSAT.ESTATUS_TIMBRADA
    if uuid_cfdi:
        # Guardar UUID SAT real sobreescribiendo el JSON anterior
        factura.uuid = uuid_cfdi
    factura.save()
    logger.info('bandeja_cfdi: factura %s marcada TIMBRADA por %s', factura_id, request.user)
    return JsonResponse({'ok': True})
