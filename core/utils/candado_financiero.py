"""
PRISLAB — Candado Financiero de Entrega de Resultados
======================================================
Autoridad única para el bloqueo de salida de documentos médicos
cuando una OrdenDeServicio presenta saldo pendiente.

Reglas de negocio (aprobadas por Dirección General):
  - Recepción puede CONFIRMAR órdenes con saldo.
  - El área técnica (Químico/QC) puede PROCESAR y VALIDAR internamente.
  - NINGUNA ruta de ENTREGA física o digital puede ejecutarse con saldo > 0.
  - El bloqueo es omnicanal: PDF, WhatsApp, Email, Portal del Paciente, QR público.
"""
from decimal import Decimal
from django.http import HttpResponse, JsonResponse

import logging

logger = logging.getLogger(__name__)


class ReportePdfSaldoPendienteError(Exception):
    """
    El motor institucional de PDF (ReportLab) no debe dibujar ningún reporte
    mientras la orden tenga saldo pendiente (staff, paciente u orquestadores).
    """

    def __init__(self, saldo_pendiente: Decimal):
        self.saldo_pendiente = saldo_pendiente
        super().__init__(
            f"PDF bloqueado: saldo pendiente ${saldo_pendiente:.2f}"
        )


# Mensaje institucional unificado
MENSAJE_RETENIDOS = (
    "RESULTADOS RETENIDOS: Esta orden presenta un saldo pendiente. "
    "Favor de liquidar en sucursal para liberar la visualización "
    "e impresión de los estudios."
)


def calcular_saldo(orden) -> Decimal:
    """Devuelve el saldo pendiente de una OrdenDeServicio."""
    try:
        total = Decimal(str(orden.total or 0))
        anticipo = Decimal(str(orden.anticipo or 0))
        return max(Decimal("0.00"), total - anticipo)
    except Exception:
        logger.warning("candado_financiero: no se pudo calcular saldo para orden %s", getattr(orden, 'id', '?'))
        return Decimal("0.00")


def tiene_saldo_pendiente(orden) -> bool:
    """True si la orden tiene deuda mayor a 0.01 (tolerancia centavos de redondeo)."""
    return calcular_saldo(orden) > Decimal("0.01")


def respuesta_retenida_html(saldo: Decimal, folio: str = "") -> HttpResponse:
    """
    Devuelve una página HTML de error 403 que el navegador muestra al intentar
    abrir/imprimir el PDF cuando hay saldo pendiente.
    """
    folio_txt = f" (Folio: {folio})" if folio else ""
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Resultados Retenidos — PRISLAB</title>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #fff3f3;
           display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }}
    .card {{ background:#fff; border:2px solid #D32F2F; border-radius:10px;
             padding:40px 48px; max-width:520px; text-align:center;
             box-shadow:0 4px 24px rgba(211,47,47,0.12); }}
    .icon {{ font-size:56px; margin-bottom:12px; }}
    h2 {{ color:#D32F2F; font-size:20px; margin:0 0 12px; }}
    p  {{ color:#555; font-size:15px; line-height:1.6; margin:0 0 8px; }}
    .saldo {{ font-size:22px; font-weight:700; color:#B71C1C; margin:16px 0; }}
    .btn {{ display:inline-block; margin-top:20px; padding:10px 28px;
            background:#1565C0; color:#fff; border-radius:6px;
            text-decoration:none; font-weight:600; font-size:14px; }}
    .btn:hover {{ background:#0D47A1; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">⛔</div>
    <h2>RESULTADOS RETENIDOS{folio_txt}</h2>
    <p>{MENSAJE_RETENIDOS}</p>
    <div class="saldo">Saldo pendiente: ${saldo:.2f}</div>
    <a href="javascript:window.history.back()" class="btn">← Regresar</a>
  </div>
</body>
</html>"""
    return HttpResponse(html, status=403, content_type="text/html; charset=utf-8")


def respuesta_retenida_json(saldo: Decimal, orden_id=None) -> JsonResponse:
    """
    Devuelve una respuesta JSON 403 para endpoints API (email masivo, AJAX).
    """
    return JsonResponse(
        {
            "ok": False,
            "bloqueado": True,
            "motivo": "SALDO_PENDIENTE",
            "error": MENSAJE_RETENIDOS,
            "saldo_pendiente": float(saldo),
            "orden_id": orden_id,
        },
        status=403,
    )
