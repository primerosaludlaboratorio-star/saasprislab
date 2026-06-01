"""
core/services/lims/interfaces_lims_service.py
════════════════════════════════════════════════════════════════════════════════
Receptor HL7/ASTM/JSON — capa de servicio LIMS (Fase 2 / Sprint 7).

Endpoint HTTP: POST /api/iot/hl7/ (vista enrutador en laboratorio.views.hl7_receptor).

Tras parseo y QC previo, la persistencia en paciente pasa por
`ResultadosLimsService.guardar_captura_desde_datos` (mismas reglas que captura manual).

Autenticación: API Key (X-PRISLAB-API-KEY) o IP whitelistada.
Tenant: HL7_IP_EMPRESA_MAP o X-EMPRESA-ID / empresa_id.
════════════════════════════════════════════════════════════════════════════════
"""
import logging
import json
import os
import re
import hashlib

from django.db import IntegrityError

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger('laboratorio.hl7')


class _FalloIntegracionClinica(Exception):
    """Rollback atómico HL7 cuando ResultadosLimsService rechaza el payload."""

    def __init__(self, out: dict):
        super().__init__(str(out))
        self.out = out


def _usuario_interfaz_clinica():
    """Usuario técnico para auditoría / captura INTERFAZ (HL7 sin sesión humana)."""
    from django.conf import settings
    from core.models import Usuario

    pk = getattr(settings, 'PRISLAB_ESCUDO_USUARIO_ID', None)
    if pk:
        u = Usuario.objects.filter(pk=pk).first()
        if u:
            return u
    return Usuario.objects.filter(is_staff=True).order_by('pk').first()


def _resolver_empresa_hl7(empresa_id_raw):
    if empresa_id_raw is None or str(empresa_id_raw).strip() == '':
        return None
    try:
        from core.models import Empresa

        return Empresa.objects.filter(pk=int(empresa_id_raw)).first()
    except (ValueError, TypeError):
        return None


def _hl7_mapa_ip_empresa() -> dict:
    """IP del cliente (middleware/gateway) → empresa_id. JSON en env HL7_IP_EMPRESA_MAP."""
    raw = os.environ.get('HL7_IP_EMPRESA_MAP', '').strip()
    if not raw:
        return {}
    try:
        d = json.loads(raw)
        return {str(k).strip(): int(v) for k, v in d.items()}
    except Exception:
        logger.warning('[HL7] HL7_IP_EMPRESA_MAP no es JSON válido; se ignora.')
        return {}


def _empresa_hl7_autoritativa(request, ip: str):
    """
    # FIX V8.2 HL7 TENANT: empresa nunca infiere solo del cuerpo del mensaje.
    Orden: mapa IP (env) → header X-EMPRESA-ID / query empresa_id.
    """
    m = _hl7_mapa_ip_empresa()
    if ip and str(ip).strip() in m:
        return _resolver_empresa_hl7(m[str(ip).strip()])
    eid = request.META.get('HTTP_X_EMPRESA_ID') or request.GET.get('empresa_id')
    return _resolver_empresa_hl7(eid)


def _persistir_huerfano_hl7(
    *,
    empresa,
    motivo: str,
    item: dict,
    mensaje_crudo: str,
    protocolo: str,
    ip: str,
    analito=None,
    unidad_catalogo: str = '',
):
    """Dead letter queue + trazabilidad para Director QC."""
    from laboratorio.models import ResultadoHL7Huerfano

    payload = dict(item)
    payload['mensaje_snippet'] = (mensaje_crudo or '')[:800]
    try:
        ResultadoHL7Huerfano.objects.create(
            empresa=empresa,
            motivo=motivo,
            codigo_equipo=str(item.get('codigo', '') or '')[:80],
            valor_raw=str(item.get('valor', '') or '')[:200],
            unidad_equipo=str(item.get('unidad', '') or '')[:80],
            unidad_catalogo=(unidad_catalogo or '')[:120],
            analito=analito,
            item_json=json.dumps(payload, ensure_ascii=False)[:8000],
            mensaje_contexto=(mensaje_crudo or '')[:4000],
            ip_equipo=ip or None,
            protocolo=(protocolo or '')[:10],
            numero_orden_equipo=str(item.get('numero_orden', '') or '')[:80],
        )
    except Exception as exc:
        logger.error('[HL7] No se pudo persistir ResultadoHL7Huerfano: %s', exc, exc_info=True)


def _war_room_notificar_hl7(empresa, tipo: str, titulo: str, detalle: str) -> None:
    if not empresa:
        logger.warning('[HL7] War Room: sin empresa; no se crea NotificacionDiscrepancia (%s)', titulo[:80])
        return
    try:
        from inventario.models import NotificacionDiscrepancia

        NotificacionDiscrepancia.objects.create(
            empresa=empresa,
            tipo=tipo,
            nivel='CRITICO',
            titulo=titulo[:255],
            detalle=(detalle or '')[:4000],
        )
    except Exception as exc:
        logger.error('[HL7] War Room notificación falló: %s', exc, exc_info=True)


def _get_hl7_active():
    return bool(getattr(settings, 'HL7_ACTIVE', False))


def _get_hl7_allowed_ips():
    return set(getattr(settings, 'HL7_ALLOWED_IPS', []))


def _get_hl7_api_key():
    return getattr(settings, 'HL7_API_KEY', '')


@csrf_exempt
@require_http_methods(['POST'])
def receptor_hl7(request):
    """
    Recibe mensajes HL7 v2.x o ASTM E1394 desde analizadores de laboratorio.
    Parsea el mensaje, mapea parámetros y dispara validación QC automática.

    STANDBY MODE: El endpoint permanece desactivado (HL7_ACTIVE=False) hasta que
    se reciban los manuales de protocolo de los fabricantes y se complete la
    interfaz con los analizadores físicos. Para activar: settings.HL7_ACTIVE = True.
    """
    if not _get_hl7_active():
        logger.info('[HL7] Solicitud recibida pero el receptor está en modo Standby (HL7_ACTIVE=False).')
        return JsonResponse(
            {'error': 'Receptor HL7 en modo Standby. Contacte al administrador del sistema.'},
            status=503
        )

    # ── Autenticación ─────────────────────────────────────────────────────────
    if not _autenticar_request_hl7(request):
        logger.warning(f'[HL7] Request no autorizado desde: {_get_ip(request)}')
        return JsonResponse({'error': 'No autorizado'}, status=401)

    ip_equipo = _get_ip(request)
    empresa_tenant = _empresa_hl7_autoritativa(request, ip_equipo)
    if not empresa_tenant:
        logger.warning(
            '[HL7] Sin empresa resoluble (X-EMPRESA-ID / empresa_id o HL7_IP_EMPRESA_MAP). IP=%s',
            ip_equipo,
        )
        return JsonResponse(
            {
                'error': (
                    'Empresa no identificada: envíe cabecera X-EMPRESA-ID (o query empresa_id) '
                    'o configure HL7_IP_EMPRESA_MAP para esta IP.'
                ),
            },
            status=400,
        )

    # ── Parsear cuerpo ────────────────────────────────────────────────────────
    body = request.body.decode('utf-8', errors='replace')
    content_type = request.content_type or ''
    datos_json_root = None

    if 'json' in content_type:
        try:
            datos = json.loads(body)
            datos_json_root = datos
            protocolo = datos.get('protocolo', 'JSON')
            mensaje_crudo = json.dumps(datos)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
    else:
        # HL7 v2.x o ASTM en texto plano
        mensaje_crudo = body
        protocolo = 'HL7' if body.startswith('MSH') else 'ASTM'

    if not mensaje_crudo.strip():
        return JsonResponse({'error': 'Cuerpo vacío'}, status=400)

    # ── Parsear HL7 ───────────────────────────────────────────────────────────
    try:
        resultados_parseados = _parsear_mensaje(mensaje_crudo, protocolo)
    except Exception as exc:
        logger.error(f'[HL7] Error al parsear mensaje: {exc}')
        return JsonResponse({'error': f'Error de parseo: {exc}'}, status=422)

    if not resultados_parseados:
        logger.info(f'[HL7] Mensaje recibido sin resultados OBX: {mensaje_crudo[:100]}')
        return JsonResponse({'ok': True, 'integrados': 0, 'detalle': 'Sin OBX'})

    # ── Mapear y procesar ítems (empresa_tenant ya validada arriba) ───────────
    _mcid_mensaje = _extraer_message_control_id_hl7(mensaje_crudo, protocolo, datos_json_root)
    procesados = []

    for item in resultados_parseados:
        resultado = _procesar_item_hl7(
            request,
            item,
            mensaje_crudo,
            protocolo,
            ip_equipo,
            empresa_tenant,
            hl7_message_control_id=_mcid_mensaje,
        )
        procesados.append(resultado)

    integrados = sum(1 for p in procesados if p.get('estado') == 'QC_OK')
    criticos = sum(1 for p in procesados if p.get('critico'))
    duplicados = sum(1 for p in procesados if p.get('estado') == 'duplicate_ignored')

    logger.info(
        f'[HL7] Procesados: {len(procesados)}, Integrados: {integrados}, '
        f'Críticos: {criticos}, Duplicados ignorados: {duplicados}, IP: {ip_equipo}'
    )

    return JsonResponse({
        'ok': True,
        'recibidos': len(procesados),
        'integrados': integrados,
        'criticos': criticos,
        'duplicados_ignorados': duplicados,
        'detalle': procesados,
    })


def _autenticar_request_hl7(request):
    """Autenticación por API key o IP allowlist."""
    ip = _get_ip(request)
    api_key_header = request.META.get('HTTP_X_PRISLAB_API_KEY', '')

    # 1) API Key
    hl7_api_key = _get_hl7_api_key()
    if hl7_api_key and api_key_header and api_key_header == hl7_api_key:
        return True

    # 2) IP allowlist
    hl7_allowed_ips = _get_hl7_allowed_ips()
    if hl7_allowed_ips and ip in hl7_allowed_ips:
        return True

    return False


def _es_muestra_control_por_pid(item: dict) -> bool:
    """Heurística PID: id o nombre empieza por QC- o CTRL- (Directriz CCI)."""
    pid = (item.get('paciente_id') or '').strip().upper()
    pname = (item.get('paciente_nombre') or '').strip().upper()
    for prefix in ('QC-', 'CTRL-'):
        if pid.startswith(prefix) or pname.startswith(prefix):
            return True
    return False


def _parsear_mensaje(mensaje: str, protocolo: str) -> list[dict]:
    """
    Parsea mensaje HL7 v2.x o ASTM y extrae segmentos OBX.

    HL7 OBX ejemplo:
      OBX|1|NM|GLU^Glucosa||5.6|mmol/L|3.9^6.1|N|||F|||20260329120000
    ASTM ejemplo:
      R|1|^^^GLU|5.6|mmol/L|3.9^6.1|N|||R|

    Returns:
      Lista de dicts con: codigo, valor, unidad, rango_ref, flags, numero_orden
    """
    items = []
    st = _get_estado_hl7()
    st.numero_orden = ''
    st.pid_paciente_id = ''
    st.pid_paciente_nombre = ''

    if protocolo == 'JSON':
        # Formato JSON simplificado para integraciones modernas
        try:
            datos = json.loads(mensaje)
            pid_root = str(datos.get('paciente_id') or datos.get('pid') or '').strip()
            pname_root = str(
                datos.get('paciente_nombre') or datos.get('nombre_paciente') or ''
            ).strip()
            _root_tid = str(
                datos.get('transaccion_id') or datos.get('message_control_id') or ''
            ).strip()[:120]
            for r in datos.get('resultados', []):
                _line_tid = str(
                    r.get('transaccion_id') or r.get('message_control_id') or _root_tid or ''
                ).strip()[:120]
                items.append({
                    'codigo': r.get('codigo', ''),
                    'nombre': r.get('nombre', ''),
                    'valor': str(r.get('valor', '')),
                    'unidad': r.get('unidad', ''),
                    'numero_orden': str(r.get('numero_orden', '')),
                    'flags': r.get('flags', 'N'),
                    'protocolo': 'JSON',
                    'paciente_id': str(r.get('paciente_id') or pid_root or ''),
                    'paciente_nombre': str(r.get('paciente_nombre') or pname_root or ''),
                    'transaccion_id': _line_tid,
                })
        except Exception as exc:
            logger.error('[HL7] Error parseando payload JSON: %s | trama: %.200s', exc, mensaje)
        return items

    if protocolo == 'HL7':
        for linea in mensaje.split('\n'):
            linea = linea.strip().replace('\r', '')
            if linea.startswith('PID|'):
                partes = linea.split('|')
                raw_id = partes[3] if len(partes) > 3 else ''
                raw_name = partes[5] if len(partes) > 5 else ''
                st.pid_paciente_id = raw_id.split('^')[0].strip() if raw_id else ''
                st.pid_paciente_nombre = raw_name.split('^')[0].strip() if raw_name else ''
            if linea.startswith('OBX'):
                item = _parsear_obx_hl7(linea)
                if item:
                    items.append(item)
            elif linea.startswith('OBR'):
                # Extraer número de orden del OBR
                partes = linea.split('|')
                numero_orden = partes[3] if len(partes) > 3 else ''
                # Inyectar número de orden en los próximos OBX
                _estado_parseo_hl7['numero_orden'] = numero_orden

    elif protocolo == 'ASTM':
        for linea in mensaje.split('\n'):
            linea = linea.strip()
            if linea.startswith('R|'):
                item = _parsear_resultado_astm(linea)
                if item:
                    items.append(item)
            elif linea.startswith('O|'):
                partes = linea.split('|')
                _estado_parseo_hl7['numero_orden'] = partes[3] if len(partes) > 3 else ''

    return items


import threading
_hl7_local = threading.local()  # Thread-safe: cada worker tiene su estado independiente

def _get_estado_hl7():
    if not hasattr(_hl7_local, 'numero_orden'):
        _hl7_local.numero_orden = ''
    if not hasattr(_hl7_local, 'pid_paciente_id'):
        _hl7_local.pid_paciente_id = ''
    if not hasattr(_hl7_local, 'pid_paciente_nombre'):
        _hl7_local.pid_paciente_nombre = ''
    return _hl7_local

# Retrocompatibilidad con código que usa _estado_parseo_hl7
class _EstadoHL7Compat:
    def get(self, key, default=''):
        return getattr(_get_estado_hl7(), key, default)

    def __setitem__(self, key, val):
        setattr(_get_estado_hl7(), key, val)

    def __getitem__(self, key):
        return getattr(_get_estado_hl7(), key, '')

_estado_parseo_hl7 = _EstadoHL7Compat()


def _parsear_obx_hl7(linea: str) -> dict | None:
    """Parsea un segmento OBX de HL7 v2.x."""
    partes = linea.split('|')
    if len(partes) < 6:
        return None
    # OBX|SetID|TipoValor|ObservationID|SubID|ObservationValue|Units|RefRange|AbnormalFlags
    codigo_raw = partes[3] if len(partes) > 3 else ''
    codigo = codigo_raw.split('^')[0].strip()
    nombre = codigo_raw.split('^')[1].strip() if '^' in codigo_raw else codigo
    return {
        'codigo': codigo,
        'nombre': nombre,
        'valor': partes[5].strip() if len(partes) > 5 else '',
        'unidad': partes[6].strip() if len(partes) > 6 else '',
        'rango_ref': partes[7].strip() if len(partes) > 7 else '',
        'flags': partes[8].strip() if len(partes) > 8 else 'N',
        'numero_orden': _estado_parseo_hl7.get('numero_orden', ''),
        'protocolo': 'HL7',
        'paciente_id': _estado_parseo_hl7.get('pid_paciente_id', ''),
        'paciente_nombre': _estado_parseo_hl7.get('pid_paciente_nombre', ''),
    }


def _parsear_resultado_astm(linea: str) -> dict | None:
    """Parsea una línea de resultado ASTM E1394."""
    partes = linea.split('|')
    if len(partes) < 4:
        return None
    codigo_raw = partes[2] if len(partes) > 2 else ''
    codigo = codigo_raw.split('^')[-1].strip() if '^' in codigo_raw else codigo_raw.strip()
    return {
        'codigo': codigo,
        'nombre': codigo,
        'valor': partes[3].strip() if len(partes) > 3 else '',
        'unidad': partes[4].strip() if len(partes) > 4 else '',
        'rango_ref': partes[5].strip() if len(partes) > 5 else '',
        'flags': partes[6].strip() if len(partes) > 6 else 'N',
        'numero_orden': _estado_parseo_hl7.get('numero_orden', ''),
        'protocolo': 'ASTM',
        'paciente_id': _estado_parseo_hl7.get('pid_paciente_id', ''),
        'paciente_nombre': _estado_parseo_hl7.get('pid_paciente_nombre', ''),
    }


def _buscar_analito_por_codigo_equipo(codigo: str, empresa):
    """
    Resuelve lims.Analito a partir del código enviado por el equipo (HL7/ASTM/JSON).
    Orden: codigo, abreviatura, codigo_rastreo_iso; luego id_legacy numérico;
    último recurso: laboratorio.Parametro.codigo_interfaz → Analito por misma abreviatura.
    """
    from django.db.models import Q
    from lims.models import Analito

    if not codigo or not str(codigo).strip() or not empresa:
        return None
    c = str(codigo).strip()
    # FIX V8.2 HL7 TENANT: catálogo LIMS acotado al tenant (endpoint sin usuario Django)
    base = Analito.objects.filter(empresa=empresa, activo=True)
    found = (
        base.filter(
            Q(codigo__iexact=c)
            | Q(abreviatura__iexact=c)
            | Q(codigo_rastreo_iso__iexact=c)
        )
        .first()
    )
    if found:
        return found
    if c.isdigit():
        legacy_id = int(c)
        found = base.filter(id_legacy=legacy_id).first()
        if found:
            return found
    try:
        from laboratorio.models import Parametro as LabParametro

        p = LabParametro.objects.filter(codigo_interfaz__iexact=c).first()
        if p and (p.abreviatura or '').strip():
            return base.filter(abreviatura__iexact=p.abreviatura.strip()).first()
    except Exception:
        pass
    return None


def _resolver_equipo_por_ip(ip: str):
    if not (ip or '').strip():
        return None
    try:
        from laboratorio.models import Equipo

        return Equipo.objects.filter(ip_address=ip.strip(), activo=True).first()
    except Exception:
        return None


def _extraer_message_control_id_hl7(
    mensaje_crudo: str, protocolo: str, datos_json: dict | None
) -> str:
    """MSH-10 (HL7), raíz JSON, o cadena vacía si no aplica."""
    if protocolo == 'JSON' and datos_json:
        return str(
            datos_json.get('transaccion_id')
            or datos_json.get('message_control_id')
            or ''
        ).strip()[:120]
    if protocolo == 'HL7':
        for linea in (mensaje_crudo or '').split('\n'):
            linea = linea.strip().replace('\r', '')
            if linea.startswith('MSH|'):
                partes = linea.split('|')
                if len(partes) > 9:
                    return (partes[9] or '').strip()[:120]
    return ''


def _linea_transaccion_id_hl7(item: dict, mcid_global: str) -> str:
    """Clave por equipo + retransmisión: MCID|código|nº orden (única por OBX)."""
    mcid = (mcid_global or '').strip() or str(
        item.get('transaccion_id') or item.get('message_control_id') or ''
    ).strip()[:120]
    if not mcid:
        return ''
    cod = str(item.get('codigo') or '')[:40]
    nord = str(item.get('numero_orden') or '')[:40]
    return f'{mcid}|{cod}|{nord}'[:190]


def _hash_idempotencia_hl7(
    ip: str,
    orden_ods,
    analito_id: int,
    codigo: str,
    valor_str: str,
    numero_orden: str,
    empresa_pk: int | None = None,
) -> str:
    """SHA-256 hex de identidad clínica + red para deduplicar integraciones."""
    payload = json.dumps(
        {
            'empresa_pk': empresa_pk,
            'ip': (ip or '').strip(),
            'orden_pk': orden_ods.pk if orden_ods else None,
            'numero_orden': str(numero_orden or '').strip(),
            'analito_id': analito_id,
            'codigo': str(codigo or '').strip(),
            'valor': str(valor_str or '').strip(),
        },
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _procesar_item_hl7(
    request,
    item: dict,
    mensaje_crudo: str,
    protocolo: str,
    ip: str,
    empresa_tenant,
    *,
    hl7_message_control_id: str = '',
) -> dict:
    """
    Mapea un ítem HL7 a un Resultado y ejecuta QC.

    empresa_tenant: instancia core.Empresa ya validada en receptor_hl7 (mapa IP o cabecera).
    request: HttpRequest del POST (requerido para ResultadosLimsService / auditoría).
    """
    codigo = item.get('codigo', '')
    valor_str = item.get('valor', '')
    numero_orden = item.get('numero_orden', '')

    respuesta = {
        'codigo': codigo, 'valor': valor_str,
        'estado': 'RECIBIDO', 'critico': False,
    }

    if not empresa_tenant:
        respuesta['estado'] = 'SIN_EMPRESA_TENANT'
        return respuesta

    try:
        from laboratorio.models import ResultadoHL7
        from core.models import OrdenDeServicio, ResultadoParametro
        from laboratorio.services.iso15189 import validar_resultado_analito_lims
        from laboratorio.services.metrologia_lab import evaluar_metrologia_equipo
        from iot.models import TransaccionHL7

        empresa_ctx = empresa_tenant

        # 1. Mapear código → lims.Analito (v7.5)
        analito = _buscar_analito_por_codigo_equipo(codigo, empresa_ctx)
        if not analito:
            logger.warning('[HL7] Código sin mapeo LIMS: %s', codigo)
            _persistir_huerfano_hl7(
                empresa=empresa_ctx,
                motivo='SIN_MAPEO_ANALITO',
                item=item,
                mensaje_crudo=mensaje_crudo,
                protocolo=protocolo,
                ip=ip,
            )
            if empresa_ctx:
                _war_room_notificar_hl7(
                    empresa_ctx,
                    'HL7_MAPEO',
                    f'HL7: sin mapeo LIMS ({codigo})',
                    (
                        f'Código equipo «{codigo}» sin match en lims.Analito. '
                        f'Revisar cola laboratorio.ResultadoHL7Huerfano.'
                    ),
                )
            respuesta['estado'] = 'SIN_MAPEO'
            respuesta['cuarentena'] = True
            return respuesta

        tipo_res = (analito.tipo_resultado or 'NUMERICO').upper()
        unidad_payload = str(item.get('unidad') or '')

        if tipo_res in ('NUMERICO', 'CALCULO'):
            from laboratorio.services.hl7_handshake import (
                decimal_desde_valor_hl7,
                formatear_decimal_para_rp,
                unidad_equipo_vs_catalogo,
            )

            ok_u, _razon_u = unidad_equipo_vs_catalogo(analito.unidades or '', unidad_payload)
            if not ok_u:
                _persistir_huerfano_hl7(
                    empresa=empresa_ctx,
                    motivo='UNIDAD_INCOMPATIBLE',
                    item=item,
                    mensaje_crudo=mensaje_crudo,
                    protocolo=protocolo,
                    ip=ip,
                    analito=analito,
                    unidad_catalogo=analito.unidades or '',
                )
                if empresa_ctx:
                    _war_room_notificar_hl7(
                        empresa_ctx,
                        'HL7_CUARENTENA',
                        f'HL7: unidad incompatible ({analito.abreviatura})',
                        (
                            f'Equipo envió «{unidad_payload or "∅"}»; catálogo exige '
                            f'«{analito.unidades or "∅"}» para {analito.codigo}. No se integró.'
                        ),
                    )
                respuesta['estado'] = 'CUARENTENA_UNIDAD'
                respuesta['cuarentena'] = True
                return respuesta

            dec_val, dec_err = decimal_desde_valor_hl7(valor_str)
            if dec_val is None:
                _persistir_huerfano_hl7(
                    empresa=empresa_ctx,
                    motivo='VALOR_NO_NUMERICO',
                    item=item,
                    mensaje_crudo=mensaje_crudo,
                    protocolo=protocolo,
                    ip=ip,
                    analito=analito,
                    unidad_catalogo=analito.unidades or '',
                )
                if empresa_ctx:
                    _war_room_notificar_hl7(
                        empresa_ctx,
                        'HL7_CUARENTENA',
                        f'HL7: valor no numérico ({analito.abreviatura})',
                        (
                            f'Valor «{valor_str}» no es Decimal válido ({dec_err}). '
                            f'Analito {analito.codigo}.'
                        ),
                    )
                respuesta['estado'] = 'CUARENTENA_VALOR'
                respuesta['cuarentena'] = True
                return respuesta

            valor_str = formatear_decimal_para_rp(dec_val, analito.decimales)
            item = {**item, 'valor': valor_str}

        equipo_lab = _resolver_equipo_por_ip(ip)
        nivel_metro, msg_metro = evaluar_metrologia_equipo(equipo_lab)
        if nivel_metro == 'hard':
            logger.error('[HL7] Metrología HARD: %s | IP=%s', msg_metro, ip)
            if empresa_ctx and equipo_lab and analito:
                from laboratorio.services.cci_canal import persistir_bloqueo_metrologia

                persistir_bloqueo_metrologia(
                    empresa_ctx, equipo_lab, analito, msg_metro or ''
                )
            respuesta['estado'] = 'METROLOGIA_BLOQUEADO'
            respuesta['detalle_metrologia'] = msg_metro
            return respuesta
        if nivel_metro == 'soft':
            logger.warning('[HL7] Metrología SOFT: %s | IP=%s', msg_metro, ip)
            respuesta['advertencia_metrologia'] = msg_metro

        # CCI: muestra de control por PID (QC-/CTRL-) → Westgard, sin ResultadoParametro paciente
        if _es_muestra_control_por_pid(item):
            if tipo_res not in ('NUMERICO', 'CALCULO'):
                respuesta['estado'] = 'CCI_TIPO_NO_NUMERICO'
                return respuesta
            if not empresa_ctx:
                respuesta['estado'] = 'CCI_SIN_EMPRESA'
                return respuesta
            if not equipo_lab:
                respuesta['estado'] = 'CCI_SIN_EQUIPO'
                return respuesta
            try:
                vf = float(str(valor_str).replace(',', '.'))
            except (TypeError, ValueError):
                respuesta['estado'] = 'CCI_VALOR_INVALIDO'
                return respuesta
            from laboratorio.services.cci_canal import procesar_medicion_control_hl7

            detalle_cci, est_cci = procesar_medicion_control_hl7(
                empresa=empresa_ctx,
                equipo=equipo_lab,
                analito=analito,
                valor_float=vf,
                origen='HL7',
            )
            respuesta['estado'] = est_cci
            respuesta['detalle_cci'] = detalle_cci
            return respuesta

        # Paciente: barrera ALERTA_QC / BLOQUEO_METROLOGIA en EstadoCanalAnalizador
        if empresa_ctx and equipo_lab and analito:
            from laboratorio.services.cci_canal import QC_CANAL_CODIGO, mensaje_bloqueo_canal

            msg_canal = mensaje_bloqueo_canal(empresa_ctx, equipo_lab, analito)
            if msg_canal:
                respuesta['estado'] = 'QC_CANAL_BLOQUEADO'
                respuesta['detalle_canal'] = msg_canal
                respuesta['codigo'] = QC_CANAL_CODIGO
                return respuesta

        # 2. Buscar Orden — FIX V8.2 HL7 TENANT: siempre filtrar por empresa validada
        _empresa_filter = {'empresa_id': empresa_ctx.pk}

        orden_ods = None
        if numero_orden:
            # Solo core.OrdenDeServicio (v7.5 — sin fallback laboratorio.Orden)
            orden_ods = (OrdenDeServicio.objects
                         .filter(folio_orden=numero_orden, **_empresa_filter)
                         .select_related('paciente')
                         .first())
            if not orden_ods:
                try:
                    oid = int(numero_orden)
                    orden_ods = OrdenDeServicio.objects.filter(
                        id=oid, **_empresa_filter
                    ).select_related('paciente').first()
                except (ValueError, TypeError):
                    logger.debug('[HL7] numero_orden %r no es entero válido para lookup por ID', numero_orden)

        # 3. Validación QC / escudo LIMS (DIAS neonatos + ANOS)
        paciente_obj = None
        if orden_ods and hasattr(orden_ods, 'paciente') and orden_ods.paciente:
            paciente_obj = orden_ods.paciente

        from core.utils.referencia_lims_edad import contexto_edad_sexo_para_lims

        _ctx_lim = contexto_edad_sexo_para_lims(orden_ods, paciente_obj)
        _edad_qc = _ctx_lim['edad']
        _edad_dias_qc = _ctx_lim['edad_dias']
        _sexo_qc = _ctx_lim['sexo']

        try:
            _prev_val = validar_resultado_analito_lims(
                analito.pk,
                valor_str,
                _edad_qc,
                _sexo_qc,
                edad_dias=_edad_dias_qc,
            )
            respuesta['estado'] = 'QC_OK'
            respuesta['critico'] = bool(getattr(_prev_val, 'es_critico', False))
            respuesta['nivel'] = getattr(_prev_val, 'nivel', 'NORMAL')
        except Exception as _ve:
            logger.warning('[HL7] validación QC: %s', _ve)
            respuesta['estado'] = 'QC_ERROR'

        _digest = _hash_idempotencia_hl7(
            ip, orden_ods, analito.pk, codigo, valor_str, numero_orden, empresa_ctx.pk
        )
        _tid_equipo = ''
        if equipo_lab:
            _tid_equipo = _linea_transaccion_id_hl7(item, hl7_message_control_id)

        detalle_para_integracion = None
        if orden_ods:
            from core.models import DetalleOrden

            detalle_para_integracion = DetalleOrden.objects.filter(
                orden=orden_ods, analito=analito
            ).first()
            if not detalle_para_integracion:
                logger.warning(
                    '[HL7] Sin DetalleOrden para analito=%s orden=%s',
                    analito.pk,
                    orden_ods.pk,
                )
                respuesta['estado'] = 'SIN_DETALLE_ORDEN'
                return respuesta
            usuario_iface = _usuario_interfaz_clinica()
            if not usuario_iface:
                logger.error(
                    '[HL7] Sin usuario técnico (PRISLAB_ESCUDO_USUARIO_ID o staff) para integración clínica'
                )
                respuesta['estado'] = 'SIN_USUARIO_INTERFAZ'
                return respuesta

        # 4. Integrar — FIX CONCURRENCIA MÁQUINAS: una sola transacción (idempotencia + HL7 + RP)
        with transaction.atomic():
            try:
                TransaccionHL7.objects.create(
                    hash_mensaje=_digest,
                    equipo=equipo_lab,
                    orden_de_servicio=orden_ods,
                    analito_id=analito.pk,
                    codigo_equipo=codigo[:80],
                    ip_origen=ip or None,
                    transaccion_id=_tid_equipo or '',
                )
            except IntegrityError:
                logger.info('[HL7] Duplicado ignorado (idempotencia) hash=%.16s…', _digest)
                respuesta['estado'] = 'duplicate_ignored'
                return respuesta

            # Persistir ResultadoHL7 crudo (campos alineados al modelo laboratorio.ResultadoHL7)
            _hl7_estado_inicial = 'RECIBIDO'
            _proto_store = protocolo if protocolo in ('HL7', 'ASTM', 'JSON') else 'HL7'
            _notas_meta = json.dumps(
                {
                    'nombre_parametro': item.get('nombre', codigo),
                    'rango_ref_equipo': item.get('rango_ref', ''),
                    'flags_equipo': item.get('flags', ''),
                    'numero_orden_equipo': numero_orden,
                },
                ensure_ascii=False,
            )
            try:
                _hl7_row = ResultadoHL7.objects.create(
                    mensaje_crudo=(mensaje_crudo or '')[:2000],
                    orden=None,
                    parametro=None,
                    codigo_parametro_equipo=codigo[:50],
                    valor_raw=str(valor_str)[:100],
                    unidad_raw=str(item.get('unidad') or '')[:30],
                    estado=_hl7_estado_inicial,
                    ip_equipo=ip or None,
                    protocolo=_proto_store,
                    notas_qc=_notas_meta[:4000],
                )
            except Exception as _e:
                logger.warning('[HL7] No se pudo persistir ResultadoHL7: %s', _e)
                _hl7_row = None

            # 4a. Persistencia clínica canónica vía ResultadosLimsService (rangos, fórmulas, pánico)
            if orden_ods and detalle_para_integracion:
                from core.services.lims.resultados_lims_service import ResultadosLimsService

                data_cap = {
                    'accion': 'borrador',
                    'metodo_captura': 'INTERFAZ',
                    'resultados': {
                        str(detalle_para_integracion.id): {
                            'resultado': valor_str,
                            'observaciones': '',
                            'parametros': {
                                str(analito.id): {'valor': valor_str},
                            },
                        },
                    },
                }
                out = ResultadosLimsService.guardar_captura_desde_datos(
                    request,
                    empresa_ctx,
                    orden_ods.id,
                    data_cap,
                    usuario_efectivo=usuario_iface,
                )
                if out['http_status'] != 200:
                    logger.error('[HL7] ResultadosLimsService rechazó integración: %s', out)
                    raise _FalloIntegracionClinica(out)

                if _hl7_row:
                    _hl7_row.estado = 'INTEGRADO'
                    _hl7_row.save(update_fields=['estado'])
                respuesta['estado'] = 'INTEGRADO'
                rp = ResultadoParametro.objects.filter(orden=orden_ods, analito=analito).first()
                respuesta['critico'] = bool(rp and getattr(rp, 'es_critico', False))

    except _FalloIntegracionClinica as fic:
        logger.warning('[HL7] Integración clínica rechazada: %s', fic.out)
        respuesta['estado'] = 'INTEGRACION_CLINICA_RECHAZADA'
        respuesta['detalle_servicio'] = fic.out.get('body')
        respuesta['http_status_servicio'] = fic.out.get('http_status')
    except Exception as exc:
        logger.error(f'[HL7] Error procesando item {codigo}: {exc}')
        respuesta['estado'] = 'ERROR'
        respuesta['error'] = str(exc)[:200]

    return respuesta


def _get_ip(request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '')


class InterfacesLimsService:
    """Traductor HL7/ASTM/JSON → `ResultadosLimsService` (reglas clínicas unificadas)."""

    @staticmethod
    def procesar_receptor_post(request):
        return receptor_hl7(request)
