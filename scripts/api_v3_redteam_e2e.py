import argparse
import copy
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import requests


TWOPLACES = Decimal("0.01")


def q(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def load_json(path: str) -> dict[str, Any]:
    """Carga JSON y elimina claves `_qa_*` (instrucciones QA; no se envían al API)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not str(k).startswith("_qa_")}


def build_session(sessionid: str, csrftoken: str | None, base_url: str) -> requests.Session:
    s = requests.Session()
    s.cookies.set("sessionid", sessionid)
    if csrftoken:
        s.cookies.set("csrftoken", csrftoken)
        s.headers["X-CSRFToken"] = csrftoken
    referer = base_url.rstrip("/") + "/"
    s.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "PRISLAB-RedTeam-E2E/1.0",
        "Referer": referer,
    })
    return s


def extract_request_id(body: Any) -> str | None:
    if isinstance(body, dict):
        return body.get("request_id") or body.get("detail", {}).get("request_id")
    return None


def print_response(label: str, response: requests.Response) -> None:
    print(f"\n=== {label} ===")
    print(f"HTTP {response.status_code}")
    hdr = response.headers.get("X-Request-ID") or response.headers.get("x-request-id") or "—"
    print(f"X-Request-ID (cabecera): {hdr}")
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}
    print(f"request_id (cuerpo JSON): {extract_request_id(body)}")
    print(json.dumps(body, indent=2, ensure_ascii=False))


def post_json(session: requests.Session, base_url: str, path: str, payload: dict[str, Any]) -> requests.Response:
    url = f"{base_url.rstrip('/')}{path}"
    return session.post(url, json=payload, timeout=60)


def rebuild_pdv_totals(payload: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(payload)
    items = out.get("items", [])
    subtotal = Decimal("0.00")
    iva_total = Decimal("0.00")

    for item in items:
        cantidad = q(item.get("cantidad", 0))
        precio = q(item.get("precio_unitario", 0))
        proporcion_iva = Decimal("0.00")
        original_sub = q(item.get("subtotal", 0))
        original_iva = q(item.get("iva_item", 0))
        if original_sub > 0:
            proporcion_iva = (original_iva / original_sub)
        nuevo_sub = (cantidad * precio).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        nuevo_iva = (nuevo_sub * proporcion_iva).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        item["subtotal"] = float(nuevo_sub)
        item["iva_item"] = float(nuevo_iva)
        subtotal += nuevo_sub
        iva_total += nuevo_iva

    redondeo = q(out.get("redondeo", 0))
    total_final = (subtotal + iva_total + redondeo).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    out["subtotal"] = float(subtotal)
    out["iva_total"] = float(iva_total)
    out["total_original"] = float(total_final)
    out["total_final"] = float(total_final)

    pagos = out.get("pagos")
    if isinstance(pagos, dict):
        out["pagos"] = {
            "efectivo": float(total_final),
            "tarjeta": 0.0,
            "transferencia": 0.0,
        }
    elif isinstance(pagos, list):
        if pagos:
            nuevos = []
            restante = total_final
            for idx, pago in enumerate(pagos):
                nuevo = dict(pago)
                if idx == 0:
                    nuevo["monto"] = float(total_final)
                else:
                    nuevo["monto"] = 0.0
                nuevos.append(nuevo)
                restante = Decimal("0.00")
            out["pagos"] = nuevos
        else:
            out["pagos"] = [{"metodo": "EFECTIVO", "monto": float(total_final)}]

    efectivo_recibido = q(out.get("efectivo_recibido", total_final))
    if efectivo_recibido < total_final:
        efectivo_recibido = total_final
    out["efectivo_recibido"] = float(efectivo_recibido)
    out["cambio_entregado"] = float((efectivo_recibido - total_final).quantize(TWOPLACES, rounding=ROUND_HALF_UP))
    return out


def build_pdv_impossible_payload(success_payload: dict[str, Any], huge_quantity: int) -> dict[str, Any]:
    out = copy.deepcopy(success_payload)
    if not out.get("items"):
        raise ValueError("El payload PDV no tiene items.")
    out["items"][0]["cantidad"] = huge_quantity
    return rebuild_pdv_totals(out)


def build_lims_formula_incomplete_payload(
    success_payload: dict[str, Any],
    detalle_id: str | None,
    analito_id: str | None,
) -> dict[str, Any]:
    out = copy.deepcopy(success_payload)
    out["accion"] = "validar"
    resultados = out.get("resultados") or {}
    if not resultados:
        raise ValueError("El payload LIMS no contiene resultados.")

    detalle_key = detalle_id or next(iter(resultados.keys()))
    if detalle_key not in resultados:
        raise ValueError(f"detalle_id objetivo no existe en resultados: {detalle_key}")

    target = resultados[detalle_key]
    parametros = target.get("parametros") or {}
    if not parametros:
        raise ValueError(
            "El payload LIMS objetivo no tiene parametros. Para forzar FORMULA_INCOMPLETA, usa una orden con analitos derivados y parámetros base."
        )

    if analito_id:
        if analito_id not in parametros:
            raise ValueError(f"analito_id objetivo no existe en parametros: {analito_id}")
        parametros.pop(analito_id, None)
    else:
        first_key = next(iter(parametros.keys()))
        parametros.pop(first_key, None)

    target["parametros"] = parametros
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Red Team E2E externo para API v3 PRISLAB.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--sessionid", required=True)
    parser.add_argument("--csrftoken")
    parser.add_argument("--farmacia-success", required=True, help="Ruta al JSON válido para /api/v3/farmacia/pdv/cobrar")
    parser.add_argument("--lims-success", required=True, help="Ruta al JSON válido para /api/v3/lims/resultados/captura")
    parser.add_argument("--huge-quantity", type=int, default=999999)
    parser.add_argument("--formula-break-detalle-id")
    parser.add_argument("--formula-break-analito-id")
    args = parser.parse_args()

    session = build_session(args.sessionid, args.csrftoken, args.base_url)
    farmacia_ok = load_json(args.farmacia_success)
    lims_ok = load_json(args.lims_success)

    farmacia_bad = build_pdv_impossible_payload(farmacia_ok, args.huge_quantity)
    lims_bad = build_lims_formula_incomplete_payload(
        lims_ok,
        args.formula_break_detalle_id,
        args.formula_break_analito_id,
    )

    response = post_json(session, args.base_url, "/api/v3/farmacia/pdv/cobrar", farmacia_ok)
    print_response("PDV COBRO EXITOSO", response)

    response = post_json(session, args.base_url, "/api/v3/farmacia/pdv/cobrar", farmacia_bad)
    print_response("PDV COBRO IMPOSIBLE / STOCK", response)

    response = post_json(session, args.base_url, "/api/v3/lims/resultados/captura", lims_ok)
    print_response("LIMS CAPTURA VÁLIDA", response)

    response = post_json(session, args.base_url, "/api/v3/lims/resultados/captura", lims_bad)
    print_response("LIMS FORMULA_INCOMPLETA", response)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
