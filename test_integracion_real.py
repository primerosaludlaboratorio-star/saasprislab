"""
Smoke script de integracion real para ejecucion manual.

Importante:
- Debe poder importarse sin ejecutar nada, para no romper `manage.py test`.
- Para correrlo manualmente:
  `.\\.venv\\Scripts\\python.exe test_integracion_real.py`
"""
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


OK = "\033[92m[OK]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"


@dataclass
class CheckResult:
    ok: bool
    name: str
    detail: str = ""


def _bootstrap_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ["PYTHONUTF8"] = "1"
    os.environ["DEBUG"] = "True"
    os.environ["E2E_DISABLE_SSL"] = "1"
    os.environ.pop("DB_HOST", None)

    import django

    django.setup()


def _check(resultados, nombre, condicion, detalle=""):
    if condicion:
        print(f"  {OK}  {nombre}")
        resultados.append(CheckResult(True, nombre))
        return
    print(f"  {FAIL} {nombre}" + (f" — {detalle}" if detalle else ""))
    resultados.append(CheckResult(False, nombre, detalle))


def _prepare_data():
    from django.contrib.auth import get_user_model
    from django.test import Client
    from core.models import Empresa, Lote, Producto

    usuario_model = get_user_model()
    empresa, _ = Empresa.objects.get_or_create(
        nombre="PRISLAB INTEGRATION TEST",
        defaults={"rfc": "PRI900101TST"},
    )
    admin, _ = usuario_model.objects.get_or_create(
        username="integ_admin",
        defaults={
            "email": "integ@test.com",
            "is_staff": True,
            "is_superuser": True,
            "rol": "ADMIN",
            "empresa": empresa,
        },
    )
    admin.set_password("IntegTest2026!")
    admin.empresa = empresa
    admin.save()

    producto, _ = Producto.objects.get_or_create(
        codigo_barras="7501INTEGTEST1",
        empresa=empresa,
        defaults={
            "nombre": "Paracetamol TEST",
            "precio_publico": Decimal("45.00"),
            "precio_compra": Decimal("20.00"),
            "stock": 100,
            "categoria": "MEDICAMENTO",
        },
    )
    Lote.objects.get_or_create(
        numero_lote="LOTE-INTEG-001",
        producto=producto,
        empresa=empresa,
        defaults={
            "fecha_caducidad": date.today() + timedelta(days=365),
            "cantidad": 100,
            "costo_adquisicion": Decimal("20.00"),
        },
    )

    print(f"\n{INFO} Preparando datos de prueba...")
    print(f"  {OK}  Setup OK (empresa_id={empresa.id}, admin=integ_admin)")
    return Client(SERVER_NAME="localhost"), producto


def _run_checks():
    from django.test import Client

    resultados = []
    client, producto = _prepare_data()

    print(f"\n{INFO} === BLOQUE 1: AUTENTICACION ===")
    resp = client.post("/login/", {"username": "integ_admin", "password": "IntegTest2026!"}, follow=True)
    _check(resultados, "Login admin -> 200 final", resp.status_code == 200, f"Status={resp.status_code}")
    _check(
        resultados,
        "Login redirige a area protegida",
        any(("/home/" in url or "/dashboard/" in url) for url, _status in resp.redirect_chain),
        f"chain={resp.redirect_chain}",
    )
    _check(resultados, "Sesion autenticada", "_auth_user_id" in client.session, f"keys={list(client.session.keys())}")

    bad = Client(SERVER_NAME="localhost")
    bad.post("/login/", {"username": "nadie", "password": "mala"})
    _check(resultados, "Login incorrecto -> no autentica", "_auth_user_id" not in bad.session)

    print(f"\n{INFO} === BLOQUE 2: FARMACIA / LAB / SEGURIDAD BASICA ===")
    for ruta in ["/home/", "/farmacia/pdv/", "/laboratorio/recepcion/", "/director/war-room/", "/inventario/"]:
        resp = client.get(ruta, follow=True)
        _check(resultados, f"GET {ruta} -> 200", resp.status_code == 200, f"Status={resp.status_code}")

    resp = client.get("/farmacia/api/buscar-producto-pdv/?q=Paracetamol", follow=True)
    _check(resultados, "API buscar producto PDV -> 200", resp.status_code == 200, f"Status={resp.status_code}")
    if resp.status_code == 200:
        try:
            data = json.loads(resp.content)
            productos = data if isinstance(data, list) else data.get("productos", data.get("resultados", []))
            _check(
                resultados,
                "Paracetamol TEST aparece en resultado",
                any("Paracetamol" in str(item) for item in productos),
                f"Data sample: {str(data)[:200]}",
            )
        except Exception as exc:
            _check(resultados, "API productos retorna JSON valido", False, str(exc))

    resp = client.get(f"/farmacia/api/lotes-producto/{producto.id}/", follow=True)
    _check(resultados, "API lotes de producto -> 200", resp.status_code == 200, f"Status={resp.status_code}")

    print(f"\n{INFO} === BLOQUE 3: RESILIENCIA ===")
    resp = client.get("/ruta-que-no-existe-xyz-abc/", follow=True)
    _check(resultados, "Ruta inexistente -> 404", resp.status_code == 404, f"Status={resp.status_code}")

    resp = client.post(
        "/api/pacientes/guardar/",
        b"{ esto no es json {{{",
        content_type="application/json",
        follow=True,
    )
    _check(resultados, "JSON malformado -> no 500", resp.status_code != 500, f"Status={resp.status_code}")

    return resultados


def main() -> int:
    _bootstrap_django()
    resultados = _run_checks()

    ok_count = sum(1 for r in resultados if r.ok)
    fail_count = sum(1 for r in resultados if not r.ok)
    total = len(resultados)

    print("\n" + "=" * 60)
    print(f"RESULTADO: {ok_count}/{total} OK, {fail_count} FALLOS")
    print("=" * 60)

    if fail_count:
        print(f"\n{FAIL} FALLOS:")
        for resultado in resultados:
            if not resultado.ok:
                suffix = f": {resultado.detail}" if resultado.detail else ""
                print(f"  - {resultado.name}{suffix}")
        return 1

    print(f"\n{OK} TODOS LOS TESTS DE INTEGRACION PASARON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
