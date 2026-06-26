"""
farmacia/services/impresora_termica.py
════════════════════════════════════════════════════════════════════════════════
FASE 8 — Impresora Térmica ESC/POS por TCP/IP

Envío directo de comandos ESC/POS a impresoras térmicas de red.
NO depende de QZ Tray, Java ni ningún plugin del navegador.
Funciona con cualquier impresora térmica con interfaz de red (Epson, Bixolon, etc.)

Comandos ESC/POS implementados:
  - ESC @ — Inicializar impresora
  - ESC E  — Negrita ON/OFF
  - ESC a  — Alineación (izquierda/centro/derecha)
  - GS V   — Corte de papel
  - Caracteres: Latin-1 / CP1252

Uso:
  from farmacia.services.impresora_termica import ImpressoraTermicaTCP
  imp = ImpressoraTermicaTCP('192.168.1.200')
  ticket = TicketBuilder().header('PRISLAB').linea('Glucosa', '450.00').total('450.00')
  imp.imprimir(ticket.build())
════════════════════════════════════════════════════════════════════════════════
"""
import socket
import logging
from django.utils import timezone

logger = logging.getLogger('farmacia.impresora_termica')

# ── Comandos ESC/POS ──────────────────────────────────────────────────────────
ESC = b'\x1b'
GS = b'\x1d'

CMD_INIT        = ESC + b'@'           # Inicializar
CMD_BOLD_ON     = ESC + b'E\x01'
CMD_BOLD_OFF    = ESC + b'E\x00'
CMD_ALIGN_LEFT  = ESC + b'a\x00'
CMD_ALIGN_CENTER = ESC + b'a\x01'
CMD_ALIGN_RIGHT = ESC + b'a\x02'
CMD_SIZE_NORMAL = ESC + b'!\x00'
CMD_SIZE_DOUBLE = ESC + b'!\x30'       # Doble ancho + alto
CMD_CUT_FULL    = GS  + b'V\x00'       # Corte total
CMD_CUT_PARTIAL = GS  + b'V\x01'       # Corte parcial
CMD_FEED_5      = ESC + b'd\x05'       # Avanzar 5 líneas
LF              = b'\n'


# ── Builder de tickets ────────────────────────────────────────────────────────

class TicketBuilder:
    """Builder fluent para construir tickets ESC/POS."""

    def __init__(self, ancho_chars: int = 40):
        self._ancho = ancho_chars
        self._buffer = bytearray()
        self._buffer += CMD_INIT

    def header(self, empresa: str, direccion: str = '', tel: str = '') -> 'TicketBuilder':
        self._buffer += CMD_ALIGN_CENTER + CMD_BOLD_ON + CMD_SIZE_DOUBLE
        self._buffer += empresa.encode('latin-1', errors='replace') + LF
        self._buffer += CMD_SIZE_NORMAL + CMD_BOLD_OFF
        if direccion:
            self._buffer += direccion[:self._ancho].encode('latin-1', errors='replace') + LF
        if tel:
            self._buffer += f'Tel: {tel}'.encode('latin-1', errors='replace') + LF
        self._buffer += CMD_ALIGN_LEFT
        self._buffer += b'-' * self._ancho + LF
        return self

    def fecha_folio(self, folio: str = '', cajero: str = '') -> 'TicketBuilder':
        now = timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')
        self._buffer += f'Fecha: {now}'.encode('latin-1', errors='replace') + LF
        if folio:
            self._buffer += f'Folio: {folio}'.encode('latin-1', errors='replace') + LF
        if cajero:
            self._buffer += f'Cajero: {cajero}'.encode('latin-1', errors='replace') + LF
        self._buffer += b'-' * self._ancho + LF
        return self

    def paciente(self, nombre: str = '', folio_orden: str = '') -> 'TicketBuilder':
        if nombre:
            self._buffer += f'Pac: {nombre[:self._ancho-5]}'.encode('latin-1', errors='replace') + LF
        if folio_orden:
            self._buffer += f'Orden: {folio_orden}'.encode('latin-1', errors='replace') + LF
        return self

    def linea(self, concepto: str, precio: str, cantidad: int = 1) -> 'TicketBuilder':
        """Agrega una línea de concepto con precio alineado a la derecha."""
        precio_fmt = f'${precio}'
        espacio = self._ancho - len(concepto[:self._ancho-15]) - len(precio_fmt)
        linea = f'{concepto[:self._ancho-15]}{" " * max(1, espacio)}{precio_fmt}'
        self._buffer += linea.encode('latin-1', errors='replace') + LF
        return self

    def subtotal(self, monto: str) -> 'TicketBuilder':
        self._buffer += b'-' * self._ancho + LF
        return self._linea_derecha('Subtotal:', f'${monto}')

    def descuento(self, monto: str) -> 'TicketBuilder':
        return self._linea_derecha('Descuento:', f'-${monto}')

    def total(self, monto: str) -> 'TicketBuilder':
        self._buffer += CMD_BOLD_ON + CMD_SIZE_DOUBLE
        total_line = f'TOTAL: ${monto}'
        self._buffer += CMD_ALIGN_CENTER
        self._buffer += total_line.encode('latin-1', errors='replace') + LF
        self._buffer += CMD_SIZE_NORMAL + CMD_BOLD_OFF + CMD_ALIGN_LEFT
        return self

    def forma_pago(self, forma: str, monto: str, cambio: str = '0.00') -> 'TicketBuilder':
        self._buffer += b'-' * self._ancho + LF
        self._linea_derecha(forma + ':', f'${monto}')
        if float(cambio.replace(',', '')) > 0:
            self._linea_derecha('Cambio:', f'${cambio}')
        return self

    def texto_libre(self, texto: str, centrado: bool = False) -> 'TicketBuilder':
        cmd = CMD_ALIGN_CENTER if centrado else CMD_ALIGN_LEFT
        self._buffer += cmd
        for linea in texto.split('\n'):
            self._buffer += linea[:self._ancho].encode('latin-1', errors='replace') + LF
        self._buffer += CMD_ALIGN_LEFT
        return self

    def separador(self) -> 'TicketBuilder':
        self._buffer += b'=' * self._ancho + LF
        return self

    def footer(self, mensaje: str = '¡Gracias por su preferencia!') -> 'TicketBuilder':
        self._buffer += b'-' * self._ancho + LF
        self._buffer += CMD_ALIGN_CENTER
        self._buffer += mensaje.encode('latin-1', errors='replace') + LF
        self._buffer += CMD_ALIGN_LEFT
        self._buffer += CMD_FEED_5
        return self

    def cortar(self, corte_parcial: bool = True) -> 'TicketBuilder':
        self._buffer += CMD_CUT_PARTIAL if corte_parcial else CMD_CUT_FULL
        return self

    def build(self) -> bytes:
        return bytes(self._buffer)

    def _linea_derecha(self, label: str, valor: str) -> 'TicketBuilder':
        espacio = self._ancho - len(label) - len(valor)
        linea = f'{label}{" " * max(1, espacio)}{valor}'
        self._buffer += linea.encode('latin-1', errors='replace') + LF
        return self


# ── Cliente TCP ───────────────────────────────────────────────────────────────

class ImpressoraTermicaTCP:
    """
    Cliente TCP para impresoras térmicas ESC/POS con interfaz de red.
    Puerto estándar: 9100.
    """

    def __init__(self, host: str, port: int = 9100, timeout: int = 8):
        self.host = host
        self.port = port
        self.timeout = timeout

    def imprimir(self, datos: bytes) -> dict:
        """Envía datos crudos ESC/POS a la impresora por TCP."""
        if not self.host:
            return {'ok': False, 'mensaje': 'Host de impresora no configurado.'}
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.sendall(datos)
            logger.info(f'[ESC/POS] {len(datos)} bytes enviados a {self.host}:{self.port}')
            return {'ok': True, 'mensaje': f'Impresión enviada ({len(datos)} bytes)'}
        except socket.timeout:
            logger.warning(f'[ESC/POS] Timeout: {self.host}:{self.port}')
            return {'ok': False, 'mensaje': f'La impresora {self.host} no responde.'}
        except ConnectionRefusedError:
            return {'ok': False, 'mensaje': f'Impresora {self.host} apagada o sin conexión.'}
        except OSError as exc:
            logger.error(f'[ESC/POS] Error: {exc}')
            return {'ok': False, 'mensaje': str(exc)}

    def test_conexion(self) -> dict:
        """Verifica que la impresora sea alcanzable."""
        try:
            with socket.create_connection((self.host, self.port), timeout=3):
                pass
            return {'ok': True, 'mensaje': f'Impresora {self.host}:{self.port} disponible.'}
        except OSError as exc:
            return {'ok': False, 'mensaje': str(exc)}
