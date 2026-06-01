"""
laboratorio/services/etiquetas_zpl.py
════════════════════════════════════════════════════════════════════════════════
FASE 7 — Generación Nativa ZPL para Impresoras Zebra

Genera código ZPL puro sin dependencia de PDF ni QZ Tray.
Envío directo por TCP/IP al puerto 9100 de la impresora.

Modelos de impresoras soportadas:
  - Zebra ZD220, ZD230, ZD420 (203/300 dpi)
  - Zebra ZT410, ZT610 (industrial)
  - Cualquier impresora con soporte ZPL II

Tipos de etiquetas:
  - Tubo de muestra (con código de barras Code128 + QR)
  - Lote de tubos (múltiples etiquetas en una sola impresión)
  - Urgente (marco rojo + asterisco)

Uso:
  zpl = generar_zpl_tubo(folio, paciente_nombre, estudios)
  enviar_zpl_tcp(zpl, host='192.168.1.100', port=9100)
════════════════════════════════════════════════════════════════════════════════
"""
import socket
import logging
from datetime import date

logger = logging.getLogger('laboratorio.zpl')

# Tamaño de etiqueta estándar de laboratorio (mm)
LABEL_W_MM = 57    # 57mm ancho
LABEL_H_MM = 32    # 32mm alto
DPI = 203          # puntos por pulgada estándar

# Conversión mm → dots
def _mm(mm: float) -> int:
    return round(mm * DPI / 25.4)


def generar_zpl_tubo(
    folio: str,
    paciente_nombre: str,
    fecha_nacimiento: str = '',
    estudios: list[str] | None = None,
    urgente: bool = False,
    empresa_nombre: str = 'PRISLAB',
) -> str:
    """
    Genera ZPL para etiqueta de tubo de muestra.

    Returns:
        str: Código ZPL II listo para enviar a impresora Zebra.
    """
    estudios = estudios or []
    fecha_hoy = date.today().strftime('%d/%m/%Y')
    estudios_str = ', '.join(estudios[:3])  # máximo 3 en etiqueta
    if len(estudios) > 3:
        estudios_str += f' +{len(estudios)-3}'

    # Nombre truncado para etiqueta pequeña
    nombre_corto = paciente_nombre[:28] if len(paciente_nombre) > 28 else paciente_nombre

    zpl_lines = [
        '^XA',                          # Inicio etiqueta
        '^CI28',                        # Encoding UTF-8
        f'^PW{_mm(LABEL_W_MM)}',        # Ancho en dots
        f'^LL{_mm(LABEL_H_MM)}',        # Largo en dots
        '^LH0,0',                       # Home label
    ]

    # ── Marco urgente (opcional) ──────────────────────────────────────────────
    if urgente:
        zpl_lines += [
            f'^FO2,2^GB{_mm(LABEL_W_MM)-4},{_mm(LABEL_H_MM)-4},3,B^FS',
            f'^FO{_mm(42)},2^A0N,14,14^FD *** URGENTE ***^FS',
        ]

    # ── Nombre del laboratorio ────────────────────────────────────────────────
    zpl_lines += [
        f'^FO4,4^A0N,12,12^FD{empresa_nombre[:18]}^FS',
    ]

    # ── Nombre del paciente ───────────────────────────────────────────────────
    zpl_lines += [
        f'^FO4,20^A0N,18,18^FD{nombre_corto}^FS',
    ]

    # ── Fecha nacimiento y fecha hoy ──────────────────────────────────────────
    zpl_lines += [
        f'^FO4,42^A0N,12,12^FDNac: {fecha_nacimiento}  |  {fecha_hoy}^FS',
    ]

    # ── Estudios solicitados ──────────────────────────────────────────────────
    if estudios_str:
        zpl_lines += [
            f'^FO4,58^A0N,12,12^FD{estudios_str[:35]}^FS',
        ]

    # ── Código de barras Code128 (folio de orden) ─────────────────────────────
    zpl_lines += [
        f'^FO4,74^BY1,3,30',
        f'^BCN,30,Y,N,N',
        f'^FD{folio}^FS',
    ]

    # ── Folio textual bajo el código de barras ────────────────────────────────
    zpl_lines += [
        f'^FO4,108^A0N,11,11^FDFolio: {folio}^FS',
    ]

    zpl_lines.append('^XZ')  # Fin etiqueta
    return '\n'.join(zpl_lines)


def generar_zpl_lote(ordenes: list[dict]) -> str:
    """
    Genera ZPL para múltiples etiquetas en un solo trabajo de impresión.
    Cada dict en ordenes debe tener: folio, paciente_nombre, estudios, urgente.
    """
    zpl_parts = []
    for orden in ordenes:
        zpl_parts.append(generar_zpl_tubo(
            folio=orden.get('folio', ''),
            paciente_nombre=orden.get('paciente_nombre', ''),
            fecha_nacimiento=orden.get('fecha_nacimiento', ''),
            estudios=orden.get('estudios', []),
            urgente=orden.get('urgente', False),
            empresa_nombre=orden.get('empresa_nombre', 'PRISLAB'),
        ))
    return '\n'.join(zpl_parts)


def enviar_zpl_tcp(
    zpl: str,
    host: str,
    port: int = 9100,
    timeout: int = 10,
) -> dict:
    """
    Envía código ZPL directamente por TCP/IP a una impresora Zebra.

    Args:
        zpl: Código ZPL II generado
        host: IP o hostname de la impresora Zebra
        port: Puerto TCP (default 9100)
        timeout: Timeout en segundos

    Returns:
        {'ok': bool, 'mensaje': str, 'bytes_enviados': int}
    """
    if not host:
        return {'ok': False, 'mensaje': 'Host de impresora no configurado.', 'bytes_enviados': 0}

    try:
        datos = zpl.encode('utf-8')
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(datos)
            bytes_env = len(datos)
        logger.info(f'[ZPL] Enviados {bytes_env} bytes a {host}:{port}')
        return {'ok': True, 'mensaje': f'Impresión enviada a {host}:{port}', 'bytes_enviados': bytes_env}
    except socket.timeout:
        logger.warning(f'[ZPL] Timeout conectando a {host}:{port}')
        return {'ok': False, 'mensaje': f'Timeout: La impresora {host} no responde.', 'bytes_enviados': 0}
    except ConnectionRefusedError:
        logger.warning(f'[ZPL] Conexión rechazada: {host}:{port}')
        return {'ok': False, 'mensaje': f'Impresora {host} no disponible o apagada.', 'bytes_enviados': 0}
    except OSError as exc:
        logger.error(f'[ZPL] Error de red: {exc}')
        return {'ok': False, 'mensaje': f'Error de red: {exc}', 'bytes_enviados': 0}


def zpl_desde_orden_legacy(orden) -> str:
    """
    Genera ZPL desde core.OrdenDeServicio (v7.5). El nombre se mantiene por compatibilidad de imports.
    """
    folio = getattr(orden, 'folio_orden', '') or getattr(orden, 'folio', '') or str(orden.pk)

    paciente = getattr(orden, 'paciente', None)
    nombre = ''
    nacimiento = ''
    if paciente:
        nombre = (
            getattr(paciente, 'nombre_completo', '') or
            f"{getattr(paciente, 'apellidos', '')} {getattr(paciente, 'nombres', '')}".strip()
        )
        nac = getattr(paciente, 'fecha_nacimiento', None)
        if nac:
            try:
                nacimiento = nac.strftime('%d/%m/%Y')
            except AttributeError:
                nacimiento = str(nac)

    estudios = []
    detalles = getattr(orden, 'detalles', None)
    if detalles is not None:
        for det in detalles.all():
            label = (getattr(det, 'descripcion_linea', '') or '').strip()
            an = getattr(det, 'analito', None)
            if not label and an is not None:
                label = getattr(an, 'nombre', '') or ''
            pf = getattr(det, 'perfil_lims', None)
            if not label and pf is not None:
                label = getattr(pf, 'nombre', '') or ''
            pq = getattr(det, 'paquete_lims', None)
            if not label and pq is not None:
                label = getattr(pq, 'nombre', '') or ''
            if label:
                estudios.append(label)

    empresa_nombre = ''
    empresa = getattr(orden, 'empresa', None)
    if empresa:
        empresa_nombre = getattr(empresa, 'nombre', 'PRISLAB')

    urgente = getattr(orden, 'urgente', False) or getattr(orden, 'es_urgente', False)

    return generar_zpl_tubo(
        folio=folio,
        paciente_nombre=nombre,
        fecha_nacimiento=nacimiento,
        estudios=estudios,
        urgente=urgente,
        empresa_nombre=empresa_nombre or 'PRISLAB',
    )
