"""
Control de calidad, toma de muestra, validación por PIN, preparación y extracción.
"""
import json
import re
import logging
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.db import transaction, IntegrityError
from django.conf import settings
from django.db.models import Q

from core.models import (
    OrdenDeServicio, ControlCalidad, TomaMuestra,
)
from core.lims_cart import detalle_orden_etiqueta
from core.services.audit_service import registrar_auditoria
from core.services.forense_service import metadata_consentimiento_snapshot, registrar_acceso_forense
from core.models import ForenseAcceso
from core.utils.detalle_orden import attach_detalle_display_attrs
from core.utils.sucursal_helpers import get_request_sucursal
from lims.models import Analito

from ._helpers import _detalle_codigo_lista

logger = logging.getLogger('core')
logger_core = logging.getLogger('core')


# Orden estándar de extracción por color de tubo (NOM-007 / CLSI GP41)
# Deuda técnica: mover a core/constants/laboratorio.py
ORDEN_EXTRACCION_TUBOS = ['AZUL', 'AMARILLO', 'ROJO', 'VERDE', 'MORADO', 'GRIS', 'NEGRO']

TUBO_INFO = {
    'ROJO':    {'label': 'Rojo',    'subtitulo': 'Suero',       'hex': '#e53935'},
    'MORADO':  {'label': 'Morado',  'subtitulo': 'EDTA',        'hex': '#8e24aa'},
    'AZUL':    {'label': 'Azul',    'subtitulo': 'Citrato Na',   'hex': '#1e88e5'},
    'VERDE':   {'label': 'Verde',   'subtitulo': 'Heparina Li',  'hex': '#43a047'},
    'GRIS':    {'label': 'Gris',    'subtitulo': 'Fluoruro Na',  'hex': '#757575'},
    'AMARILLO':{'label': 'Amarillo','subtitulo': 'Gel/Suero',    'hex': '#f9a825'},
    'NEGRO':   {'label': 'Negro',   'subtitulo': 'VSG/ESR',      'hex': '#212121'},
}


@login_required
def control_calidad(request):
    """
    Dashboard de Control de Calidad (Levey-Jennings).
    Permite ingreso manual de valores de control, carga por lote,
    gráfica de Levey-Jennings y asistencia de PRIS.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')

    # POST: guardar nuevo registro de control
    if request.method == 'POST':
        try:
            with transaction.atomic():
                lote = request.POST.get('lote_control', '').strip()
                parametro_nombre = request.POST.get('parametro_nombre', '').strip()
                valor_str = request.POST.get('valor', '').strip()
                valor_esperado_str = request.POST.get('valor_esperado', '').strip()
                desviacion_str = request.POST.get('desviacion_std', '').strip()
                equipo_nombre = ''
                equipo_id = request.POST.get('equipo_id') or None
                if equipo_id:
                    try:
                        from laboratorio.models import Equipo as EquipoLab
                        eq = EquipoLab.objects.filter(id=int(equipo_id)).first()
                        equipo_nombre = str(eq) if eq else ''
                    except (ImportError, ValueError, LookupError):
                        pass
                nivel = request.POST.get('observaciones', 'Normal').strip() or 'Normal'

                valor_num = Decimal(valor_str.replace(',', '.')) if valor_str else Decimal('0')
                valor_esperado_num = Decimal(valor_esperado_str.replace(',', '.')) if valor_esperado_str else None
                # Calcular desviación vs media
                desviacion = Decimal('0')
                if valor_esperado_num:
                    desviacion = valor_num - valor_esperado_num
                elif desviacion_str:
                    desviacion = Decimal(desviacion_str.replace(',', '.'))

                ControlCalidad.objects.create(
                    empresa=empresa,
                    lote=lote or f'LOTE-{timezone.now().strftime("%Y%m%d")}',
                    parametro=parametro_nombre,
                    valor=valor_num,
                    desviacion=desviacion,
                    equipo=equipo_nombre,
                    nivel=nivel,
                )
                from django.contrib import messages
                messages.success(request, f'Control registrado: {parametro_nombre} = {valor_str}')
        except (IntegrityError, ValueError, TypeError) as _e:
            from django.contrib import messages
            messages.error(request, f'Error al registrar: {_e}')
        return redirect('control_calidad')

    # GET: listar controles y preparar contexto para gráficas
    try:
        qs = ControlCalidad.objects.filter(empresa=empresa).order_by('-fecha_registro')[:200]
    except (ImportError, AttributeError, LookupError):
        logger.error('Error en control_calidad', exc_info=True)
        qs = ControlCalidad.objects.none()

    # Preparar datos para Levey-Jennings (últimas 30 lecturas por parámetro)
    graficas_data = {}
    try:
        from django.db.models import Avg, StdDev
        parametros_en_cc = qs.values_list('parametro', flat=True).distinct()[:10]
        for param_nombre in parametros_en_cc:
            if not param_nombre:
                continue
            lecturas = ControlCalidad.objects.filter(
                empresa=empresa,
                parametro=param_nombre,
            ).order_by('fecha_registro')[:30]
            valores = []
            fechas = []
            for l in lecturas:
                try:
                    valores.append(float(l.valor))
                    fechas.append(l.fecha_registro.strftime('%d/%m'))
                except (ValueError, TypeError):
                    pass
            if valores:
                promedio = sum(valores) / len(valores)
                graficas_data[param_nombre] = {
                    'valores': valores,
                    'fechas': fechas,
                    'promedio': round(promedio, 3),
                }
    except (ImportError, AttributeError, LookupError, ValueError, TypeError):
        pass

    # Equipos disponibles
    equipos = []
    try:
        from laboratorio.models import Equipo
        equipos = list(Equipo.objects.filter(activo=True).values('id', 'nombre', 'marca'))
    except (ImportError, AttributeError, LookupError):
        pass

    parametros_lista = list(
        Analito.objects.filter(activo=True).values_list('nombre', flat=True).order_by('nombre')[:200]
    )
    analitos_cci = list(
        Analito.objects.filter(activo=True)
        .order_by('nombre')
        .values('id', 'codigo', 'nombre')[:400]
    )
    from core.services.feature_flags import flag_activo

    qc_westgard_estricto = flag_activo('QC_WESTGARD_ACTIVO', empresa)

    return render(request, 'core/control_calidad.html', {
        'empresa': empresa,
        'controles': qs,
        'graficas_data_json': json.dumps(graficas_data),
        'equipos': equipos,
        'parametros_lista_json': json.dumps(parametros_lista),
        'analitos_cci_json': json.dumps(analitos_cci),
        'qc_westgard_estricto': qc_westgard_estricto,
    })


@login_required
def toma_muestra_index(request):
    """
    Índice de toma de muestra:
    - Filtra órdenes PAGADAS que aún no tienen registro de TomaMuestra.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    from django.db.models import Exists, OuterRef
    ordenes_pagadas = (
        OrdenDeServicio.objects
        .filter(empresa=empresa, estado="PAGADO")
        .annotate(_tiene_toma=Exists(TomaMuestra.objects.filter(orden=OuterRef('pk'))))
        .filter(_tiene_toma=False)
        .select_related("paciente")
        .prefetch_related('detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims')
        .order_by("-fecha_creacion")[:300]
    )
    ordenes_pendientes = list(ordenes_pagadas)
    for orden in ordenes_pendientes:
        attach_detalle_display_attrs(list(orden.detalles.all()))

    if request.method == "POST":
        orden_id = request.POST.get("orden_id")
        orden = OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa).first()
        _ya_tiene_toma = TomaMuestra.objects.filter(orden=orden).exists() if orden else True
        if orden and orden.estado == "PAGADO" and not _ya_tiene_toma:
            TomaMuestra.objects.create(
                empresa=empresa,
                sucursal=get_request_sucursal(request),
                orden=orden,
                tomada_por=request.user,
            )
        from django.shortcuts import redirect
        return redirect("toma_muestra_index")

    return render(
        request,
        "core/toma_muestra_index.html",
        {"empresa": empresa, "ordenes": ordenes_pendientes},
    )


@login_required
@require_http_methods(["POST"])
def api_toma_muestra(request, orden_id: int):
    """API: marca toma de muestra (crea TomaMuestra) sin recargar."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({"ok": False, "error": "Usuario sin empresa asignada"}, status=403)
    orden = OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa).first()
    if not orden:
        return JsonResponse({"ok": False, "error": "Orden no encontrada"}, status=404)

    if orden.estado != "PAGADO":
        return JsonResponse({"ok": False, "error": "La orden debe estar PAGADA para tomar muestra."}, status=400)

    if TomaMuestra.objects.filter(orden=orden).exists():
        return JsonResponse({"ok": True, "ya_existia": True})

    TomaMuestra.objects.create(
        empresa=empresa,
        sucursal=get_request_sucursal(request),
        orden=orden,
        tomada_por=request.user,
    )
    return JsonResponse({"ok": True, "ya_existia": False})


@login_required
def api_validar_pin(request, orden_id: int):
    """API: valida resultados por PIN (MVP)."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({"ok": False, "error": "Usuario sin empresa asignada"}, status=403)
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = {}

    pin = str(data.get("pin") or "").strip()
    if not pin:
        return JsonResponse({"ok": False, "error": "PIN requerido"}, status=400)

    validation_pin = str(getattr(settings, "LAB_VALIDATION_PIN", "") or "").strip()
    if not validation_pin:
        logger_core.error(
            'api_validar_pin: LAB_VALIDATION_PIN no configurado; orden=%s usuario=%s',
            orden_id,
            getattr(request.user, 'username', 'anon'),
        )
        return JsonResponse(
            {"ok": False, "error": "PIN de validación no configurado"},
            status=503,
        )

    if pin != validation_pin:
        return JsonResponse({"ok": False, "error": "PIN incorrecto"}, status=403)

    orden = OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa).first()
    if not orden:
        return JsonResponse({"ok": False, "error": "Orden no encontrada"}, status=404)

    try:
        from core.utils.candado_financiero import tiene_saldo_pendiente
        if not tiene_saldo_pendiente(orden) and not (
            orden.archivo_resultado and getattr(orden.archivo_resultado, 'name', None)
        ):
            from core.services.motor_reportes_lab import (
                generar_reporte_pdf,
                generar_reporte_pdf_simple,
                guardar_reporte_en_storage,
            )
            try:
                pdf_bytes = generar_reporte_pdf(orden, request=request)
            except (RuntimeError, ValueError, OSError):
                logger_core.warning(
                    'api_validar_pin: motor PDF principal fallo, usando contingencia orden=%s',
                    orden.id,
                    exc_info=True,
                )
                pdf_bytes = generar_reporte_pdf_simple(orden, request=request)

            pdf_url = guardar_reporte_en_storage(orden, pdf_bytes)
            orden.refresh_from_db(fields=['archivo_resultado'])
            if not pdf_url and not (
                orden.archivo_resultado and getattr(orden.archivo_resultado, 'name', None)
            ):
                return JsonResponse(
                    {"ok": False, "error": "No se pudo guardar el PDF de resultados"},
                    status=500,
                )
    except (RuntimeError, ValueError, OSError, ImportError, LookupError):
        logger_core.exception(
            'api_validar_pin: no se pudo preparar PDF antes de validar orden=%s',
            orden.id,
        )
        return JsonResponse(
            {"ok": False, "error": "No se pudo generar el PDF de resultados"},
            status=500,
        )

    orden.estado = 'RESULTADOS_LISTOS'
    try:
        OrdenDeServicio.objects.filter(id=orden.id, empresa=empresa).update(estado='RESULTADOS_LISTOS')
    except (IntegrityError, OperationalError):
        logger_core.exception('api_validar_pin: no se pudo marcar orden validada orden=%s', orden.id)
        return JsonResponse(
            {"ok": False, "error": "No se pudo validar la orden"},
            status=500,
        )

    try:
        registrar_auditoria(
            accion='UPDATE',
            modelo='OrdenDeServicio',
            objeto_id=str(orden.id),
            datos_nuevos={'validacion_pin': True, 'folio': orden.folio_orden or str(orden.id)},
            request=request,
        )
    except (RuntimeError, ValueError, TypeError):
        pass

    # WhatsApp trigger — generar enlace listo para enviar al paciente (LFPDPPP)
    whatsapp_enlace = None
    from core.utils.lfpdppp_resultados import paciente_autorizado_canal_digital_resultados

    lfpdppp_bloqueo_canal = bool(
        orden.paciente and not paciente_autorizado_canal_digital_resultados(orden.paciente)
    )
    if lfpdppp_bloqueo_canal:
        logger_core.warning(
            'api_validar_pin: WhatsApp omitido por LFPDPPP (sin consentimiento digital) orden=%s paciente=%s',
            orden.id,
            orden.paciente_id,
        )

    try:
        if orden.paciente and orden.paciente.telefono and not lfpdppp_bloqueo_canal:
            from core.utils.whatsapp_sender import enviar_whatsapp, generar_enlace_whatsapp
            empresa_nombre = getattr(empresa, 'nombre', 'PRISLAB')
            folio_display = orden.folio_orden or str(orden.id)
            nombre_pac = (orden.paciente.nombre_completo or '').split()[0] if orden.paciente.nombre_completo else 'Paciente'
            # Incluir link al PDF público si el token de acceso existe
            pdf_link = ''
            try:
                site_url = getattr(settings, 'SITE_URL', '')
                if not site_url:
                    site_url = request.build_absolute_uri('/').rstrip('/')
                if orden.token_acceso:
                    pdf_link = f'\n\n🔗 Descarga tu reporte aquí:\n{site_url}/validar/resultado/{orden.token_acceso}/'
            except (AttributeError, ValueError, TypeError):
                pass
            mensaje_wa = (
                f"Hola {nombre_pac} 👋\n\n"
                f"Tus resultados de laboratorio ({folio_display}) "
                f"de *{empresa_nombre}* ya están listos y validados por nuestro equipo.{pdf_link}\n\n"
                f"¡Que te encuentres muy bien! 🧬"
            )
            # Intento de envío automático — si hay credenciales API, envía solo; si no, devuelve link
            wa_resultado = enviar_whatsapp(orden.paciente.telefono, mensaje_wa)
            if wa_resultado.get('enviado'):
                whatsapp_enlace = None  # Ya se envió — no hace falta el link manual
                logger.info(
                    'api_validar_orden_pin: WA enviado automáticamente a orden %s via %s',
                    orden.id, wa_resultado.get('canal')
                )
            else:
                whatsapp_enlace = wa_resultado.get('link') or generar_enlace_whatsapp(
                    orden.paciente.telefono, mensaje_wa
                )
    except (ImportError, AttributeError, ValueError, TypeError, RuntimeError):
        pass

    wmeta = metadata_consentimiento_snapshot(orden.paciente) if orden.paciente_id else {}
    wmeta['lfpdppp_bloqueo_canal_digital'] = lfpdppp_bloqueo_canal
    wmeta['whatsapp_enlace_generado'] = bool(whatsapp_enlace)
    wmeta['validacion_pin'] = True
    registrar_acceso_forense(
        request,
        ForenseAcceso.ACCION_WHATSAPP_ENVIO,
        paciente_id=orden.paciente_id,
        orden_id=orden.id,
        metadata=wmeta,
        es_publico=False,
        empresa=empresa,
    )

    return JsonResponse({
        "ok": True,
        "whatsapp_enlace": whatsapp_enlace,
        "whatsapp_enviado_auto": whatsapp_enlace is None and not lfpdppp_bloqueo_canal,
        "lfpdppp_bloqueo_canal_digital": lfpdppp_bloqueo_canal,
    })


@login_required
def preparacion_toma(request, orden_id):
    """
    Consola de trabajo del flebotomista antes de iniciar la extracción.
    Muestra: datos del paciente, guía visual de tubos, checklist de seguridad.
    Al pulsar INICIAR TOMA el frontend llama api_iniciar_toma vía fetch.
    """
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    # Verificar que la orden aún es elegible (PAGADO o ya en extracción)
    if orden.estado not in ('PAGADO',) and orden.estado_clinico not in ('PENDIENTE_TOMA', 'EN_EXTRACCION'):
        from django.contrib import messages as _msg
        _msg.warning(request, 'Esta orden ya no está en estado de toma de muestra.')
        return redirect('toma_muestra_index')

    detalles = (
        orden.detalles
        .select_related('analito', 'perfil_lims', 'paquete_lims')
        .filter(estado_procesamiento='PENDIENTE_TOMA')
    )

    tubos_dict = {}
    for det in detalles:
        color = 'ROJO'
        if color not in tubos_dict:
            tubos_dict[color] = {
                **TUBO_INFO.get(color, {'label': color, 'subtitulo': '', 'hex': '#9e9e9e'}),
                'color': color,
                'estudios': [],
            }
        tubos_dict[color]['estudios'].append(detalle_orden_etiqueta(det))

    # Ordenar tubos según estándar CLSI
    tubos_guia = sorted(
        tubos_dict.values(),
        key=lambda t: ORDEN_EXTRACCION_TUBOS.index(t['color'])
        if t['color'] in ORDEN_EXTRACCION_TUBOS else 99
    )

    # Estado actual de la toma (si ya se inició en sesión previa)
    toma_existente = getattr(orden, 'toma_muestra', None)
    ya_iniciada = (
        toma_existente is not None and
        toma_existente.hora_inicio_extraccion is not None and
        toma_existente.hora_fin_extraccion is None
    )

    # Verificar si hay consentimiento firmado
    consentimiento_firmado = False
    try:
        from core.models import ConsentimientoInformado
        consentimiento_firmado = ConsentimientoInformado.objects.filter(
            orden=orden, firmado=True
        ).exists()
    except (ImportError, AttributeError, LookupError):
        pass

    return render(request, 'core/preparacion_toma.html', {
        'orden': orden,
        'paciente': orden.paciente,
        'tubos_guia': tubos_guia,
        'detalles': detalles,
        'ya_iniciada': ya_iniciada,
        'toma': toma_existente,
        'consentimiento_firmado': consentimiento_firmado,
    })


@login_required
@require_http_methods(["POST"])
def api_iniciar_toma(request, orden_id):
    """
    Marca el inicio de la extracción:
    - Crea o recupera el registro TomaMuestra
    - Registra hora_inicio_extraccion
    - Cambia estado_clinico → EN_EXTRACCION
    - Devuelve timestamp para el cronómetro frontend
    """
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError, TypeError):
        data = {}

    identidad = data.get('identidad_verificada', False)
    ayuno = data.get('ayuno_confirmado', False)
    consentimiento = data.get('consentimiento_firmado', False)

    with transaction.atomic():
        toma, _ = TomaMuestra.objects.get_or_create(
            orden=orden,
            defaults={
                'empresa': empresa,
                'sucursal': get_request_sucursal(request),
                'tomada_por': request.user,
            }
        )
        ahora = timezone.now()
        toma.hora_inicio_extraccion = ahora
        toma.hora_fin_extraccion = None
        toma.identidad_verificada = identidad
        toma.ayuno_confirmado = ayuno
        toma.consentimiento_firmado = consentimiento
        toma.save(update_fields=[
            'hora_inicio_extraccion', 'hora_fin_extraccion',
            'identidad_verificada', 'ayuno_confirmado', 'consentimiento_firmado',
        ])

        orden.estado_clinico = 'EN_EXTRACCION'
        orden.save(update_fields=['estado_clinico'])

    logger.info("TOMA INICIADA orden=%s usuario=%s", orden_id, request.user.username)

    return JsonResponse({
        'ok': True,
        'toma_id': toma.id,
        'timestamp_inicio': ahora.isoformat(),
    })


@login_required
@require_http_methods(["POST"])
def api_finalizar_toma(request, orden_id):
    """
    Cierra la sesión de extracción:
    - Registra hora_fin_extraccion y duracion
    - Guarda audio cifrado (si se envió como base64)
    - Guarda transcripción / notas PRIS
    - Cambia estado_clinico → TOMA_REALIZADA
    - Cambia estado_procesamiento de detalles → TOMA_REALIZADA
    """
    from core.models import AudioTomaMuestra
    import hashlib, base64

    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Cuerpo JSON inválido'}, status=400)

    audio_b64 = data.get('audio_b64', '')       # base64 del audio WebM
    transcripcion = data.get('transcripcion', '')
    notas_ia = data.get('notas_ia', '')
    checklist_final = data.get('checklist_final') or {}

    toma = getattr(orden, 'toma_muestra', None)
    if not toma:
        return JsonResponse({'ok': False, 'error': 'No existe registro de inicio de toma'}, status=400)

    ahora = timezone.now()
    duracion = 0
    if toma.hora_inicio_extraccion:
        duracion = int((ahora - toma.hora_inicio_extraccion).total_seconds())

    with transaction.atomic():
        toma.hora_fin_extraccion = ahora
        toma.duracion_extraccion_seg = duracion
        toma.notas_ia = notas_ia or transcripcion
        # Sincronizar checklist de seguridad con el cierre (fuente de verdad: sesión completa)
        if checklist_final:
            toma.identidad_verificada = bool(checklist_final.get('IDENTIDAD', toma.identidad_verificada))
            toma.ayuno_confirmado = bool(checklist_final.get('AYUNO', toma.ayuno_confirmado))
            toma.consentimiento_firmado = bool(checklist_final.get('CONSENTIMIENTO', toma.consentimiento_firmado))
        toma.save(update_fields=[
            'hora_fin_extraccion', 'duracion_extraccion_seg', 'notas_ia',
            'identidad_verificada', 'ayuno_confirmado', 'consentimiento_firmado',
        ])

        # Cifrar y guardar audio si fue enviado
        if audio_b64:
            try:
                audio_bytes = base64.b64decode(audio_b64)
                sha = hashlib.sha256(audio_bytes).hexdigest()

                # Cifrado Fernet si FERNET_KEY está configurada
                cifrado = audio_bytes  # fallback: sin cifrar
                try:
                    from cryptography.fernet import Fernet
                    from django.conf import settings as _cfg
                    fernet_key = getattr(_cfg, 'FERNET_KEY', None)
                    if fernet_key:
                        f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
                        cifrado = f.encrypt(audio_bytes)
                except (ImportError, ValueError, TypeError, RuntimeError) as e_fernet:
                    logger.warning("Fernet no disponible para audio toma: %s", e_fernet)

                audio_rec, _ = AudioTomaMuestra.objects.get_or_create(toma=toma)
                audio_rec.audio_cifrado = cifrado
                audio_rec.hash_sha256 = sha
                audio_rec.duracion_segundos = duracion
                audio_rec.transcripcion_ia = transcripcion
                audio_rec.timestamp_inicio = toma.hora_inicio_extraccion
                audio_rec.timestamp_fin = ahora
                audio_rec.ip_origen = request.META.get('REMOTE_ADDR', '')
                audio_rec.save()
            except (ValueError, TypeError, ImportError, RuntimeError) as e_audio:
                logger.error("Error guardando audio toma orden=%s: %s", orden_id, e_audio)

        # Actualizar estado clínico de la orden
        orden.estado_clinico = 'TOMA_REALIZADA'
        orden.fecha_toma_muestra = ahora
        orden.usuario_tomo_muestra = request.user
        orden.save(update_fields=['estado_clinico', 'fecha_toma_muestra', 'usuario_tomo_muestra'])

        # Actualizar detalles pendientes
        orden.detalles.filter(estado_procesamiento='PENDIENTE_TOMA').update(
            estado_procesamiento='TOMA_REALIZADA'
        )

    logger.info("TOMA FINALIZADA orden=%s duracion=%ss usuario=%s", orden_id, duracion, request.user.username)

    return JsonResponse({
        'ok': True,
        'duracion_segundos': duracion,
        'redirect_url': f'/laboratorio/lista-trabajo/',
    })


@login_required
def reporte_tiempos_proceso(request):
    """
    REPORTE DE TIEMPOS DE PROCESO: Muestra estudios que exceden el tiempo configurado.
    Integrado con Dashboard Pendientes para alertas en tiempo real.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    ahora = timezone.now()

    # Obtener todas las órdenes en proceso o con resultados listos
    ordenes_activas = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado__in=['PAGADO', 'EN_PROCESO', 'RESULTADOS_LISTOS']
    ).select_related('paciente', 'sucursal').prefetch_related(
        'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
    )

    estudios_excedidos = []

    for orden in ordenes_activas:
        tiempo_transcurrido = ahora - orden.fecha_creacion
        horas_transcurridas = tiempo_transcurrido.total_seconds() / 3600

        for detalle in orden.detalles.all():
            etiqueta = detalle_orden_etiqueta(detalle)
            estudio = SimpleNamespace(nombre=etiqueta)
            tiempo_proceso_estudio = '1 día'

            # Parsear tiempo_proceso (ej: "1 día", "2 horas", "3 días")
            horas_limite = parsear_tiempo_proceso(tiempo_proceso_estudio)

            if horas_limite and horas_transcurridas > horas_limite:
                # Calcular retraso
                horas_retraso = horas_transcurridas - horas_limite

                # Determinar nivel de alerta
                if horas_retraso > 24:
                    nivel_alerta = 'CRITICO'
                    clase_css = 'blink-critical'
                elif horas_retraso > 12:
                    nivel_alerta = 'ALTO'
                    clase_css = 'alert-danger'
                else:
                    nivel_alerta = 'MEDIO'
                    clase_css = 'alert-warning'

                estudios_excedidos.append({
                    'orden': orden,
                    'detalle': detalle,
                    'estudio': estudio,
                    'tiempo_configurado': tiempo_proceso_estudio,
                    'horas_limite': horas_limite,
                    'horas_transcurridas': round(horas_transcurridas, 1),
                    'horas_retraso': round(horas_retraso, 1),
                    'nivel_alerta': nivel_alerta,
                    'clase_css': clase_css,
                })

    # Ordenar por horas de retraso (mayor primero)
    estudios_excedidos.sort(key=lambda x: x['horas_retraso'], reverse=True)

    # Estadísticas
    stats = {
        'total_excedidos': len(estudios_excedidos),
        'criticos': len([e for e in estudios_excedidos if e['nivel_alerta'] == 'CRITICO']),
        'altos': len([e for e in estudios_excedidos if e['nivel_alerta'] == 'ALTO']),
        'medios': len([e for e in estudios_excedidos if e['nivel_alerta'] == 'MEDIO']),
    }

    return render(request, 'core/laboratorio/reporte_tiempos_proceso.html', {
        'estudios_excedidos': estudios_excedidos,
        'stats': stats,
    })


def parsear_tiempo_proceso(tiempo_str):
    """
    Parsea el string de tiempo_proceso a horas.
    Ejemplos: "1 día" -> 24, "2 horas" -> 2, "3 días" -> 72
    """
    if not tiempo_str:
        return None

    tiempo_str = tiempo_str.lower().strip()

    # Buscar días
    if 'día' in tiempo_str or 'dia' in tiempo_str:
        match = re.search(r'(\d+)', tiempo_str)
        if match:
            dias = int(match.group(1))
            return dias * 24

    # Buscar horas
    if 'hora' in tiempo_str:
        match = re.search(r'(\d+)', tiempo_str)
        if match:
            return int(match.group(1))

    # Por defecto, asumir 24 horas (1 día)
    return 24
