#!/usr/bin/env python3
"""
PRISLAB v8.5 — Batería E2E externa (Red Team) contra API v3 (Ninja + Cadenero).

NO modifica Django; solo HTTP contra tu servidor local.

Requisitos:
  pip install requests

Uso típico (después de definir IDs reales de tu BD local):

  set BASE_URL=http://127.0.0.1:8000
  set PRISLAB_LOGIN_USER=cajero_demo
  set PRISLAB_LOGIN_PASSWORD=********
  set PDV_PRODUCT_ID=1847
  set LIMS_ORDEN_ID=45821
  set LIMS_DETALLE_ID=90344
  set LIMS_ANALITO_GLUCOSA=112
  set LIMS_ANALITO_SODIO=113
  set LIMS_ORDEN_FORMULA=45822
  set LIMS_DETALLE_FORMULA=90350
  python scripts/e2e_api_v3_redteam.py

Alternativa sin login programático (usuario con 2FA, etc.):
  1) Inicia sesión en el navegador.
  2) Copia la cookie sessionid (y opcionalmente csrftoken) desde DevTools.
  set PRISLAB_SESSION_ID=abc123...
  python scripts/e2e_api_v3_redteam.py

El escenario FORMULA_INCOMPLETA solo corre si defines LIMS_ORDEN_FORMULA (+ detalle)
sobre una orden de QA que tenga analitos calculados cuyas bases no estén cubiertas
al validar; si no, el script lo marca como OMITIDO con instrucciones.

Variables de entorno (referencia):
  BASE_URL                 default http://127.0.0.1:8000
  PRISLAB_LOGIN_USER / PRISLAB_LOGIN_PASSWORD
  PRISLAB_SESSION_ID       valor crudo de la cookie sessionid
  PDV_PRODUCT_ID           entero, producto con stock vigente
  LIMS_*                   ver argparse / main()
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

import requests


def _env_int(name: str, default: int | None = None) -> int | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _extract_csrf_from_html(html: str) -> str | None:
    m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


def build_session(args: argparse.Namespace) -> requests.Session:
    s = requests.Session()
    base = args.base_url.rstrip("/")

    sid = (os.environ.get("PRISLAB_SESSION_ID") or "").strip()
    if sid:
        s.cookies.set("sessionid", sid, path="/")
        print("[auth] Sesión vía PRISLAB_SESSION_ID (cookie sessionid inyectada).")
        return s

    user = (os.environ.get("PRISLAB_LOGIN_USER") or "").strip()
    pw = (os.environ.get("PRISLAB_LOGIN_PASSWORD") or "").strip()
    if not user or not pw:
        print(
            "[auth] ERROR: Define PRISLAB_SESSION_ID o PRISLAB_LOGIN_USER + PRISLAB_LOGIN_PASSWORD.",
            file=sys.stderr,
        )
        sys.exit(2)

    r = s.get(f"{base}/login/", timeout=30)
    r.raise_for_status()
    token = _extract_csrf_from_html(r.text)
    if not token:
        print("[auth] ERROR: No se encontró csrfmiddlewaretoken en /login/.", file=sys.stderr)
        sys.exit(2)

    r2 = s.post(
        f"{base}/login/",
        data={
            "username": user,
            "password": pw,
            "csrfmiddlewaretoken": token,
            "next": "/",
        },
        headers={"Referer": f"{base}/login/"},
        allow_redirects=True,
        timeout=30,
    )
    if r2.url and ("/auth/2fa/" in r2.url or "verificar_2fa" in r2.url):
        print(
            "[auth] ERROR: La cuenta requiere 2FA. Inicia sesión en el navegador y "
            "exporta PRISLAB_SESSION_ID.",
            file=sys.stderr,
        )
        sys.exit(2)

    if not s.cookies.get("sessionid"):
        print(
            "[auth] ERROR: No hay cookie sessionid tras POST /login/. "
            "Credenciales incorrectas o flujo bloqueado; usa PRISLAB_SESSION_ID.",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"[auth] Login OK como {user!r} (cookies de sesión cargadas).")
    return s


def warmup_csrf(session: requests.Session, base: str) -> None:
    """Primera petición GET para recibir csrftoken (necesario en POST JSON con sesión)."""
    try:
        session.get(f"{base.rstrip('/')}/", allow_redirects=True, timeout=30)
    except requests.RequestException as exc:
        print(f"[warn] warmup GET / falló: {exc}")


def csrf_headers(session: requests.Session, referer: str) -> dict[str, str]:
    tok = session.cookies.get("csrftoken")
    h: dict[str, str] = {"Referer": referer.rstrip("/") + "/"}
    if tok:
        h["X-CSRFToken"] = tok
    return h


def post_json(
    session: requests.Session,
    base: str,
    path: str,
    payload: dict[str, Any],
) -> requests.Response:
    url = f"{base.rstrip('/')}{path}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        **csrf_headers(session, base),
    }
    return session.post(url, headers=headers, data=json.dumps(payload), timeout=120)


def report(label: str, resp: requests.Response) -> None:
    """Imprime HTTP, X-Request-ID y request_id del cuerpo (Cadenero / respuesta 200)."""
    hdr_rid = resp.headers.get("X-Request-ID") or resp.headers.get("x-request-id") or "—"
    body_rid = "—"
    code = "—"
    message = ""
    try:
        data = resp.json()
        body_rid = str(data.get("request_id") or "—")
        code = str(data.get("code") or "—")
        message = str(data.get("message") or data.get("mensaje") or "")[:200]
    except Exception:
        data = None
    extra = f" | envelope.code={code}" if code != "—" else ""
    if message:
        extra += f" | msg={message!r}"
    print(
        f"[{label}] HTTP {resp.status_code} | X-Request-ID: {hdr_rid} | body.request_id: {body_rid}{extra}"
    )
    if data is not None and len(json.dumps(data, ensure_ascii=False)) < 1200:
        print(f"    JSON: {json.dumps(data, ensure_ascii=False)[:800]}")


def payload_pdv_ok(product_id: int) -> dict[str, Any]:
    return {
        "cliente": "QA Red Team — cobro controlado",
        "paciente_id": None,
        "subtotal": 348.28,
        "iva_total": 55.72,
        "redondeo": 0.0,
        "total_final": 404.0,
        "descuento_aplicado": 0,
        "descuento_porcentaje": 0,
        "total_original": 404.0,
        "items": [
            {
                "producto_id": product_id,
                "cantidad": 2,
                "precio_unitario": 174.14,
                "subtotal": 348.28,
                "iva_item": 55.72,
            }
        ],
        "pagos": {"efectivo": 404.0, "tarjeta": 0, "transferencia": 0},
        "efectivo_recibido": 500.0,
        "cambio_entregado": 96.0,
        "referencia_pago": "E2E-REDTEAM",
    }


def payload_pdv_stock_attack(product_id: int, qty: int) -> dict[str, Any]:
    p = payload_pdv_ok(product_id)
    p["items"] = [
        {
            "producto_id": product_id,
            "cantidad": qty,
            "precio_unitario": 174.14,
            "subtotal": float(174.14 * qty),
            "iva_item": round(float(174.14 * qty) * 0.16, 2),
        }
    ]
    sub = float(174.14 * qty)
    iva = round(sub * 0.16, 2)
    p["subtotal"] = sub
    p["iva_total"] = iva
    p["total_final"] = round(sub + iva, 2)
    p["total_original"] = p["total_final"]
    p["pagos"] = {"efectivo": p["total_final"], "tarjeta": 0, "transferencia": 0}
    p["efectivo_recibido"] = p["total_final"] + 100
    p["cambio_entregado"] = 100.0
    return p


def payload_lims_borrador(
    orden_id: int,
    detalle_id: int,
    analito_glucosa: int,
    analito_sodio: int,
) -> dict[str, Any]:
    return {
        "orden_id": orden_id,
        "accion": "borrador",
        "metodo_captura": "MANUAL",
        "resultados": {
            str(detalle_id): {
                "resultado": "98",
                "observaciones": "E2E Red Team — borrador",
                "parametros": {
                    str(analito_glucosa): {"valor": "5.2"},
                    str(analito_sodio): {"valor": "140"},
                },
            }
        },
    }


def payload_lims_formula_probe(
    orden_id: int,
    detalle_id: int,
) -> dict[str, Any]:
    """
    Intento de forzar FORMULA_INCOMPLETA en validar: línea con resultado textual
    pero sin paretrós que alimenten analitos base de fórmulas (comportamiento depende del catálogo).
    En muchas BD reales hará falta ajustar este cuerpo según analitos de la orden.
    """
    return {
        "orden_id": orden_id,
        "accion": "validar",
        "metodo_captura": "MANUAL",
        "resultados": {
            str(detalle_id): {
                "resultado": "1",
                "observaciones": "E2E — validar sin parámetros para stress de fórmulas",
                "parametros": {},
            }
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Red Team E2E API v3 (farmacia + LIMS).")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
    )
    parser.add_argument("--stock-qty", type=int, default=999_999, help="Cantidad ridícula PDV.")
    args = parser.parse_args()
    base = args.base_url

    pdv_path = "/api/v3/farmacia/pdv/cobrar"
    lims_path = "/api/v3/lims/resultados/captura"

    session = build_session(args)
    warmup_csrf(session, base)

    product_id = _env_int("PDV_PRODUCT_ID")
    orden_id = _env_int("LIMS_ORDEN_ID")
    detalle_id = _env_int("LIMS_DETALLE_ID")
    ag = _env_int("LIMS_ANALITO_GLUCOSA", 112)
    asn = _env_int("LIMS_ANALITO_SODIO", 113)

    print("\n=== 1) PDV — cobro esperado OK (puede fallar si ID/stock no existen) ===")
    if not product_id:
        print("[SKIP] PDV: define PDV_PRODUCT_ID (entero con stock).")
    else:
        r = post_json(session, base, pdv_path, payload_pdv_ok(product_id))
        report("PDV cobro OK (intento)", r)

    print("\n=== 2) PDV — ataque stock (cantidad enorme → 409 STOCK_INSUFFICIENT esperado) ===")
    if not product_id:
        print("[SKIP] PDV stock: mismo PDV_PRODUCT_ID requerido.")
    else:
        r = post_json(session, base, pdv_path, payload_pdv_stock_attack(product_id, args.stock_qty))
        report("PDV stock attack", r)
        if r.status_code != 409:
            print(
                f"    [nota] Esperábamos 409 si hay producto y sin stock; "
                f"otros códigos indican 404 producto, 403 auth, etc."
            )

    print("\n=== 3) LIMS — borrador JSON (IDs reales requeridos) ===")
    if not orden_id or not detalle_id:
        print("[SKIP] LIMS borrador: define LIMS_ORDEN_ID y LIMS_DETALLE_ID.")
    else:
        r = post_json(
            session,
            base,
            lims_path,
            payload_lims_borrador(orden_id, detalle_id, ag, asn),
        )
        report("LIMS borrador", r)

    print("\n=== 4) LIMS — estrés FORMULA_INCOMPLETA (422 esperado si el catálogo/orden cooperan) ===")
    orden_f = _env_int("LIMS_ORDEN_FORMULA")
    detalle_f = _env_int("LIMS_DETALLE_FORMULA")
    if not orden_f or not detalle_f:
        print(
            "[OMITIDO] Define LIMS_ORDEN_FORMULA y LIMS_DETALLE_FORMULA con una orden QA que tenga "
            "analitos calculados; opcionalmente edita payload_lims_formula_probe() en el script "
            "para omitir parámetros base y forzar FORMULA_INCOMPLETA."
        )
    else:
        r = post_json(session, base, lims_path, payload_lims_formula_probe(orden_f, detalle_f))
        report("LIMS formula stress", r)
        if r.status_code != 422:
            print(
                "    [nota] Si no ves 422 FORMULA_INCOMPLETA, ajusta orden/detalle o el payload "
                "según tu LIMS real (el motor exige analitos base según fórmula)."
            )

    print("\n=== Fin batería ===")


if __name__ == "__main__":
    main()
