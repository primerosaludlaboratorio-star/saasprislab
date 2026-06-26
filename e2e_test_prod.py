import subprocess, sys, json, re
import logging

BASE = "https://prislab.labcorecloud.com"
COOKIES = "/tmp/e2e_cookies.txt"
results = {}

def curl(*args, follow=True, out_file="/dev/null"):
    cmd = ["curl", "-s", "-k", "-b", COOKIES, "-c", COOKIES,
           "-w", "\n__HTTP_CODE__%{http_code}__",
           "-o", out_file, "--max-time", "15"]
    if follow:
        cmd.append("-L")
    cmd.extend(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    out_body = ""
    if out_file != "/dev/null":
        try:
            with open(out_file, "r", errors="replace") as fp:
                out_body = fp.read()
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en curl (e2e_test_prod.py)")
            out_body = ""
    code_m = re.search(r"__HTTP_CODE__(\d+)__", r.stdout)
    code = int(code_m.group(1)) if code_m else 0
    return code, out_body

def extract_csrf(html):
    m = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', html)
    if not m:
        m = re.search(r'value=["\']([^"\']+)["\'] name=["\']csrfmiddlewaretoken["\']', html)
    return m.group(1) if m else ""

# 0. GET LOGIN
code, html = curl(BASE + "/login/", out_file="/tmp/e2e_login.html")
csrf = extract_csrf(html)
results["0_login_page"] = {"http": code, "csrf_found": bool(csrf)}
print(f"[0] GET Login: HTTP {code} | CSRF: {csrf[:20]}...")

# 1. POST LOGIN
code, html = curl(
    "-X", "POST", BASE + "/login/",
    "-d", "username=admin&password=PrislabV5_2026&csrfmiddlewaretoken=" + csrf,
    "-H", "Referer: " + BASE + "/login/",
    "-H", "Origin: " + BASE,
    out_file="/tmp/e2e_post_login.html"
)
t = re.search(r"<title>([^<]+)", html)
title = t.group(1).strip() if t else "no-title"
results["1_login"] = {"http": code, "title": title}
print(f"[1] POST Login: HTTP {code} | Titulo: {title}")

# 2. DASHBOARD FARMACIA
code, html = curl(BASE + "/farmacia/", out_file="/tmp/e2e_farm.html")
t = re.search(r"<title>([^<]+)", html)
results["2_dashboard_farmacia"] = {"http": code, "title": t.group(1).strip() if t else "?"}
print(f"[2] Dashboard Farmacia: HTTP {code} | {results['2_dashboard_farmacia']['title']}")

# 3. PDV
code, html = curl(BASE + "/farmacia/pdv/", out_file="/tmp/e2e_pdv.html")
results["3_pdv"] = {
    "http": code,
    "carrito": "tabla-carrito" in html,
    "buscador": "input-buscador" in html,
    "multi_tab": "nuevoTicket" in html,
    "listas_precio": "selector-lista-precio" in html
}
print(f"[3] PDV: HTTP {code} | {results['3_pdv']}")

# 4. API BUSCAR PRODUCTO
code, body = curl(
    BASE + "/farmacia/api/buscar-producto-pdv/?termino=paracetamol",
    "-H", "X-Requested-With: XMLHttpRequest",
    out_file="/tmp/e2e_buscar.json"
)
try:
    data = json.loads(body)
    prods = data.get("productos", [])
    results["4_buscar_producto"] = {"http": code, "count": len(prods),
                                     "primer": prods[0].get("nombre_comercial", "?") if prods else "sin_resultados"}
except Exception as e:
    logging.getLogger(__name__).exception("Error inesperado en extract_csrf (e2e_test_prod.py)")
    results["4_buscar_producto"] = {"http": code, "error": str(e)[:80]}
print(f"[4] Buscar Producto API: HTTP {code} | {results['4_buscar_producto']}")

# 5. API LISTAS PRECIO
code, body = curl(
    BASE + "/farmacia/api/listas-precio/",
    "-H", "X-Requested-With: XMLHttpRequest",
    out_file="/tmp/e2e_listas.json"
)
try:
    data = json.loads(body)
    listas = data.get("listas", [])
    results["5_listas_precio"] = {"http": code, "count": len(listas),
                                   "nombres": [l["nombre"] for l in listas]}
except Exception as e:
    logging.getLogger(__name__).exception("Error inesperado en extract_csrf (e2e_test_prod.py)")
    results["5_listas_precio"] = {"http": code, "error": str(e)[:80]}
print(f"[5] Listas Precio API: HTTP {code} | {results['5_listas_precio']}")

# 6. KPIs 3 periodos
for periodo in ["7d", "30d", "mes_actual"]:
    code, body = curl(
        BASE + "/farmacia/api/kpis/?periodo=" + periodo,
        "-H", "X-Requested-With: XMLHttpRequest",
        out_file="/tmp/e2e_kpis_" + periodo + ".json"
    )
    try:
        data = json.loads(body)
        results["6_kpis_" + periodo] = {
            "http": code, "status": data.get("status"),
            "labels": len(data.get("labels", [])),
            "top": len(data.get("top_productos", [])),
            "margen": data.get("pct_margen", 0)
        }
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en extract_csrf (e2e_test_prod.py)")
        results["6_kpis_" + periodo] = {"http": code, "error": str(e)[:80]}
    print(f"[6] KPIs {periodo}: {results['6_kpis_' + periodo]}")

# 7. INVENTARIO
code, html = curl(BASE + "/farmacia/inventario/", out_file="/tmp/e2e_inv.html")
results["7_inventario"] = {"http": code, "ok": code == 200}
print(f"[7] Inventario: HTTP {code}")

# 8. KARDEX
code, html = curl(BASE + "/farmacia/kardex/", out_file="/tmp/e2e_kdx.html")
results["8_kardex"] = {"http": code, "ok": code == 200, "movimientos": "folio" in html.lower() or "kdx" in html}
print(f"[8] Kardex: HTTP {code} | movimientos={results['8_kardex']['movimientos']}")

# 9. SEMAFORO CADUCIDAD
code, html = curl(BASE + "/farmacia/semaforo-caducidad/", out_file="/tmp/e2e_sem.html")
results["9_semaforo"] = {"http": code, "ok": code == 200, "lotes": "lote" in html.lower()}
print(f"[9] Semaforo Caducidad: HTTP {code}")

# 10. STOCK CRITICO
code, html = curl(BASE + "/farmacia/stock-critico/", out_file="/tmp/e2e_stk.html")
results["10_stock_critico"] = {"http": code, "ok": code == 200}
print(f"[10] Stock Critico: HTTP {code}")

# 11. DEVOLUCIONES
code, html = curl(BASE + "/farmacia/devoluciones/", out_file="/tmp/e2e_dev.html")
results["11_devoluciones"] = {"http": code, "ok": code == 200, "form": "folio" in html.lower()}
print(f"[11] Devoluciones: HTTP {code}")

# 12. COFEPRIS ANTIBIOTICOS
code, html = curl(BASE + "/farmacia/antibioticos/reporte-cofepris/", out_file="/tmp/e2e_atb.html")
results["12_cofepris"] = {"http": code, "ok": code == 200}
print(f"[12] COFEPRIS: HTTP {code}")

# 13. CORTE DE CAJA
code, html = curl(BASE + "/farmacia/corte-caja/", out_file="/tmp/e2e_caja.html")
results["13_corte_caja"] = {"http": code, "ok": code == 200}
print(f"[13] Corte Caja: HTTP {code}")

# 14. VALORIZACIÓN
code, html = curl(BASE + "/farmacia/reporte/valorizacion/", out_file="/tmp/e2e_val.html")
results["14_valorizacion"] = {"http": code, "ok": code == 200}
print(f"[14] Valorizacion: HTTP {code}")

# 15. LABORATORIO RECEPCION
code, html = curl(BASE + "/recepcion_lab/", out_file="/tmp/e2e_lab.html")
results["15_lab_recepcion"] = {"http": code, "ok": code in [200, 302], "estudios": "estudio" in html.lower()}
print(f"[15] Lab Recepcion: HTTP {code}")

# 16. AUDITORIA
code, html = curl(BASE + "/auditoria/", out_file="/tmp/e2e_audit.html")
results["16_auditoria"] = {"http": code, "ok": code in [200, 302]}
print(f"[16] Auditoria: HTTP {code}")

# 17. HOME
code, html = curl(BASE + "/", out_file="/tmp/e2e_home.html")
t = re.search(r"<title>([^<]+)", html)
results["17_home"] = {"http": code, "title": t.group(1).strip() if t else "?"}
print(f"[17] Home: HTTP {code} | {results['17_home']['title']}")

# RESUMEN
print("\n" + "="*65)
print("RESUMEN E2E PRODUCCION - PRISLAB SaaS")
print("="*65)
ok_count = sum(1 for v in results.values() if v.get("http") in [200, 302])
total = len(results)
print(f"  TOTAL PASS: {ok_count}/{total}")
print("="*65)
for k, v in sorted(results.items()):
    http = v.get("http", 0)
    estado = "PASS" if http in [200, 302] else "FAIL"
    print(f"  [{estado}] {k}: HTTP {http}")
print("="*65)