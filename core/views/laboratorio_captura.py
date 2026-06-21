"""
Vista de Captura de Resultados con IA Integrada.
Catálogo LIMS v7.5: una fila de captura por analito en línea (FK `analito` en `DetalleOrden` y `ResultadoParametro`).

Escudo / ISO 15189: el guardado de valores desde el grid usa la API
``core.views.laboratorio.api_guardar_resultados`` (motor ``ResultadoParametro.validar_contra_rango``
100% LIMS + ``notificar_panico_escudo_lims`` hacia ``NotificacionPanico`` en ODS).
Validación clínica (``RESULTADOS_LISTOS``) no se bloquea por saldo: si el motor PDF lanza
``ReportePdfSaldoPendienteError``, la API responde **200** con ``pdf_pendiente_pago``; el PDF
se genera al cobrar (Portero en extracción).
"""
from types import SimpleNamespace

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import date

from core.models import OrdenDeServicio, DetalleOrden, ResultadoParametro, AuditLog
from core.lims_cart import detalle_orden_etiqueta
from core.services.ia_clinical_governance import METODO_IA_BORRADOR
from lims.models import Analito, ValorReferenciaAnalito
from laboratorio.models import Equipo, NotificacionPanico
import logging

logger = logging.getLogger(__name__)


def _estudio_like(detalle):
    if detalle.analito_id:
        a = detalle.analito
        seccion = SimpleNamespace(nombre=(a.departamento or '').strip() or '')
        return SimpleNamespace(nombre=a.nombre, codigo=a.codigo or '', seccion=seccion)
    seccion = SimpleNamespace(nombre='')
    return SimpleNamespace(
        nombre=detalle_orden_etiqueta(detalle),
        codigo='',
        seccion=seccion,
    )


def _ref_analito(analito, edad_anos, sexo):
    if not analito:
        return None
    qs = (
        ValorReferenciaAnalito.objects.filter(analito=analito)
        .filter(Q(sexo=sexo) | Q(sexo='I'))
        .order_by('unidad_edad', 'edad_minima')
    )
    edad = edad_anos if edad_anos is not None else 0
    for r in qs:
        if r.unidad_edad == 'ANOS' and r.edad_minima <= edad <= r.edad_maxima:
            return r
    return qs.first()


@login_required
def captura_resultados_industrial(request, orden_id):
    """
    Vista de captura de resultados estilo DeveLab.
    Panel izquierdo con folios del día, panel derecho con cuadrícula de captura.
    """
    user = request.user
    
    # PATRÓN CORRECTO: Validar empresa siempre, pero permitir superuser/staff CON empresa válida
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.warning(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    
    # Superuser/staff con empresa válida pueden operar
    if user.is_superuser or user.is_staff:
        pass  # Permitir continuar
    else:
        if not ((getattr(user, 'rol', '') or '').upper().strip() in ('QUIMICO', 'LABORATORIO', 'ADMIN', 'ADMINISTRADOR')
                or user.groups.filter(name__in=['LABORATORIO', 'GERENCIA_OPERATIVA']).exists()):
            messages.warning(request, 'No tienes permisos para captura de resultados.')
            return redirect('home')

    try:
        orden = (
            OrdenDeServicio.objects
            .select_related('paciente', 'sucursal')
            .get(id=orden_id, empresa=empresa)
        )
    except OrdenDeServicio.DoesNotExist:
        logger.warning(
            'captura_resultados: orden_id=%s no encontrada para empresa=%s usuario=%s — '
            'posible URL directa stale o acceso cross-empresa.',
            orden_id, getattr(empresa, 'pk', '?'), request.user.username
        )
        messages.warning(
            request,
            f'La orden #{orden_id} no está disponible para tu empresa o ya fue eliminada. '
            'Selecciona una orden desde la lista de trabajo.'
        )
        return redirect('lista_trabajo_lab')

    paciente = orden.paciente
    edad_paciente = None
    sexo_paciente = paciente.sexo if hasattr(paciente, 'sexo') else 'I'

    if paciente.fecha_nacimiento:
        hoy = date.today()
        edad_paciente = hoy.year - paciente.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (paciente.fecha_nacimiento.month, paciente.fecha_nacimiento.day):
            edad_paciente -= 1

    detalles_qs = orden.detalles.select_related(
        'analito', 'perfil_lims', 'paquete_lims'
    ).order_by('id')

    aid_set = [d.analito_id for d in detalles_qs if d.analito_id]
    resultados_previos_dict = {
        rp.analito_id: rp
        for rp in ResultadoParametro.objects.filter(orden=orden, analito_id__in=aid_set)
    }

    delta_check_dict = {}
    for rp in (
        ResultadoParametro.objects.filter(
            orden__paciente=paciente,
            analito_id__in=aid_set,
        )
        .exclude(orden=orden)
        .exclude(valor='')
        .exclude(valor__isnull=True)
        .select_related('orden')
        .order_by('analito_id', '-orden__fecha_creacion')
    ):
        if rp.analito_id and rp.analito_id not in delta_check_dict:
            delta_check_dict[rp.analito_id] = rp

    detalles_procesados = []
    total_parametros = 0

    for detalle in detalles_qs:
        estudio = _estudio_like(detalle)
        parametros_list = []

        if detalle.analito_id:
            an = detalle.analito
            r = _ref_analito(an, edad_paciente, sexo_paciente)
            ref_min = round(float(r.ref_minimo), 2) if r and r.ref_minimo is not None else None
            ref_max = round(float(r.ref_maximo), 2) if r and r.ref_maximo is not None else None
            critico_min = (
                round(float(r.valor_critico_bajo), 2)
                if r and r.valor_critico_bajo is not None
                else None
            )
            critico_max = (
                round(float(r.valor_critico_alto), 2)
                if r and r.valor_critico_alto is not None
                else None
            )
            panico_fuera_ref = bool(r and getattr(r, 'es_critico_si_fuera_de_rango', False))
            ref_texto = ''
            if r:
                ref_texto = (r.texto_referencia or '').strip()
                if ref_min is not None and ref_max is not None and not ref_texto:
                    ref_texto = f'{ref_min:.2f} - {ref_max:.2f}'
            rp = resultados_previos_dict.get(an.id)
            resultado_anterior = delta_check_dict.get(an.id)
            valor_prev = (rp.valor if rp else '') or (detalle.resultado or '')
            escudo_ia_advertencia = False
            if rp and (valor_prev or '').strip():
                if not getattr(rp, 'aprobado_por_humano', True):
                    escudo_ia_advertencia = True
                elif getattr(rp, 'metodo_captura', '') == METODO_IA_BORRADOR:
                    escudo_ia_advertencia = True
            parametros_list.append({
                'parametro_id': an.id,
                'descripcion': an.nombre,
                'codigo_estudio': an.codigo or '',
                'abreviatura': (an.abreviatura or '').strip(),
                'tipo_resultado': an.tipo_resultado or 'NUMERICO',
                'es_calculado': bool(getattr(an, 'es_calculado', False)),
                'ref_min': ref_min,
                'ref_max': ref_max,
                'ref_texto': ref_texto,
                'unidades': an.unidades or '',
                'critico_min': critico_min,
                'critico_max': critico_max,
                'panico_fuera_ref': panico_fuera_ref,
                'formula': an.formula or '',
                'valor_previo': valor_prev,
                'escudo_ia_advertencia': escudo_ia_advertencia,
                'resultado_anterior': {
                    'valor': resultado_anterior.valor if resultado_anterior else '',
                    'fecha': resultado_anterior.orden.fecha_creacion.strftime('%d/%m/%Y')
                    if resultado_anterior and resultado_anterior.orden.fecha_creacion else '',
                    'folio': resultado_anterior.orden.folio_orden if resultado_anterior else '',
                } if resultado_anterior else None,
            })
            total_parametros += 1
        else:
            parametros_list.append({
                'parametro_id': 0,
                'descripcion': detalle_orden_etiqueta(detalle),
                'codigo_estudio': '',
                'ref_min': None,
                'ref_max': None,
                'ref_texto': '',
                'unidades': '',
                'critico_min': None,
                'critico_max': None,
                'panico_fuera_ref': False,
                'formula': '',
                'valor_previo': detalle.resultado or '',
                'escudo_ia_advertencia': False,
                'resultado_anterior': None,
            })
            total_parametros += 1

        seccion_nombre = ''
        if detalle.analito_id and detalle.analito:
            seccion_nombre = (detalle.analito.departamento or '').strip()

        detalles_procesados.append({
            'detalle': detalle,
            'estudio': estudio,
            'seccion': seccion_nombre,
            'parametros': parametros_list,
        })

    esta_validado = orden.estado == 'RESULTADOS_LISTOS'

    hoy = date.today()
    folios_dia = []
    try:
        ordenes_hoy = OrdenDeServicio.objects.filter(
            empresa=empresa,
            fecha_creacion__date=hoy,
        ).select_related('paciente').order_by('-fecha_creacion')[:50]

        for o in ordenes_hoy:
            folios_dia.append({
                'id': o.id,
                'folio': o.folio_orden or f'ORD-{o.id}',
                'paciente': o.paciente.nombre_completo if o.paciente else 'Sin paciente',
                'estado': o.estado,
                'es_actual': o.id == orden.id,
            })
    except Exception:
        logger.warning('captura_resultados: error cargando folios_dia para empresa %s', empresa, exc_info=True)

    from decimal import Decimal as _D
    _total = orden.total or _D('0')
    _anticipo = orden.anticipo or _D('0')
    saldo_cero = (_total - _anticipo) <= _D('0')
    puede_imprimir = esta_validado and saldo_cero

    token_acceso = str(orden.token_acceso) if getattr(orden, 'token_acceso', None) else None

    equipos_laboratorio = list(
        Equipo.objects.filter(activo=True).order_by('marca', 'nombre')[:100]
    )

    context = {
        'orden': orden,
        'paciente': paciente,
        'edad_paciente': edad_paciente,
        'sexo_paciente': sexo_paciente,
        'detalles': detalles_procesados,
        'total_parametros': total_parametros,
        'esta_validado': esta_validado,
        'saldo_cero': saldo_cero,
        'puede_imprimir': puede_imprimir,
        'token_acceso': token_acceso,
        'folios_dia': folios_dia,
        'equipos_laboratorio': equipos_laboratorio,
    }

    return render(request, 'core/captura_resultados_industrial.html', context)


@login_required
@require_http_methods(['POST'])
def registrar_notificacion_panico(request, orden_id):
    """
    Registra la notificación de un valor crítico al médico tratante.
    Cumplimiento ISO 15189:2012, Punto 5.9.
    """
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    try:
        analito_id_raw = request.POST.get('parametro_id') or request.POST.get('analito_id')
        valor_critico = request.POST.get('valor_critico')
        medico_notificado = request.POST.get('medico_notificado')
        cargo_receptor = request.POST.get('cargo_receptor', '')
        medio_notificacion = request.POST.get('medio_notificacion')
        numero_contacto = request.POST.get('numero_contacto', '')
        observaciones = request.POST.get('observaciones', '')
        confirmacion_recepcion = request.POST.get('confirmacion_recepcion') == 'on'

        if not analito_id_raw or not str(analito_id_raw).isdigit():
            return JsonResponse({
                'success': False,
                'error': 'Falta analito / parámetro válido (identificador numérico)',
            }, status=400)
        analito_id = int(analito_id_raw)
        if analito_id <= 0:
            return JsonResponse({
                'success': False,
                'error': 'La notificación de pánico requiere un analito LIMS identificado',
            }, status=400)

        if not medico_notificado or not medio_notificacion:
            return JsonResponse({
                'success': False,
                'error': 'Faltan campos obligatorios: médico notificado y medio de notificación'
            }, status=400)

        if not orden.detalles.filter(analito_id=analito_id).exists():
            logger.warning(
                '[Pánico IDOR] analito_id=%s no está en orden %s — usuario %s',
                analito_id, orden_id, request.user.username,
            )

        analito = get_object_or_404(Analito, id=analito_id, activo=True)

        from django.db import transaction as _dbt
        with _dbt.atomic():
            resultado = ResultadoParametro.objects.filter(
                orden=orden,
                analito=analito,
            ).first()

            if not resultado:
                resultado = ResultadoParametro.objects.create(
                    orden=orden,
                    analito=analito,
                    valor=valor_critico or '',
                    capturado_por=request.user,
                    es_critico=True,
                )
            else:
                resultado.es_critico = True
                resultado.save(update_fields=['es_critico'])

            notificacion = NotificacionPanico.objects.create(
                resultado=resultado,
                orden=orden,
                medico_notificado=medico_notificado,
                cargo_receptor=cargo_receptor,
                medio_notificacion=medio_notificacion,
                numero_contacto=numero_contacto,
                observaciones=observaciones,
                usuario_notifico=request.user,
                confirmacion_recepcion=confirmacion_recepcion
            )

            AuditLog.objects.create(
                empresa=empresa,
                usuario=request.user,
                accion=AuditLog.ACCION_CREATE,
                modelo='NotificacionPanico',
                objeto_id=notificacion.id,
                descripcion=(
                    f'Notificación de valor crítico: {analito.nombre} = {valor_critico} | '
                    f'Notificado a: {medico_notificado}'
                ),
            )

        logger.info(
            "Notificación de pánico registrada: Orden %s, Analito %s, Notificó: %s",
            orden.folio_orden, analito.nombre, request.user.username,
        )

        return JsonResponse({
            'success': True,
            'message': 'Notificación registrada correctamente',
            'notificacion_id': notificacion.id
        })

    except Exception as e:
        logger.error("Error al registrar notificación de pánico: %s", e, exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error al registrar notificación: {str(e)}'
        }, status=500)
