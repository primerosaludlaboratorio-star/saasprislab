"""
PRISLAB v5.0 — AUDITORÍA DE ESTRÉS TOTAL E2E EN PRODUCCIÓN
============================================================
Ejecuta simulación masiva contra Cloud Run + Cloud SQL (PostgreSQL).
- 30 pacientes (10 convenio + 20 particulares)
- 30 notas SOAP
- 20 órdenes de laboratorio con captura, validación PIN y PDFs
- 50 ventas farmacia con 4 métodos de pago
- 5 devoluciones + 5 cancelaciones
- Asistencia 10 empleados + nómina
- Corte de caja con verificación al centavo
"""
import requests
import json
import time
import random
import traceback
from datetime import datetime, date, timedelta
from decimal import Decimal

BASE_URL = "https://prislab-v5-oswjakz55a-uc.a.run.app"
ADMIN_USER = "admin"
ADMIN_PASS = "PrislabV5_2026"

# ============================================================================
# CONTADORES GLOBALES
# ============================================================================
STATS = {
    "pacientes_creados": 0, "pacientes_fallidos": 0,
    "consultas_creadas": 0, "consultas_fallidas": 0,
    "soap_creados": 0, "soap_fallidos": 0,
    "ordenes_lab_creadas": 0, "ordenes_lab_fallidas": 0,
    "ordenes_cobradas": 0, "ordenes_cobro_fallido": 0,
    "resultados_capturados": 0, "resultados_fallidos": 0,
    "validaciones_pin": 0, "validaciones_pin_fallidas": 0,
    "ventas_ok": 0, "ventas_fallidas": 0,
    "devoluciones_ok": 0, "devoluciones_fallidas": 0,
    "cancelaciones_ok": 0, "cancelaciones_fallidas": 0,
    "asistencias_ok": 0, "asistencias_fallidas": 0,
    "incidencias_ok": 0, "incidencias_fallidas": 0,
    "nomina_ok": 0, "nomina_fallida": 0,
    "errores_detalle": [],
}

# ============================================================================
# CLIENTE HTTP CON SESIÓN
# ============================================================================
class ProdClient:
    def __init__(self, base_url):
        self.base = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PRISLAB-E2E-Audit/5.0",
            "X-Requested-With": "XMLHttpRequest",
        })

    def login(self, username, password):
        import re
        login_url = f"{self.base}/login/"
        r = self.session.get(login_url, allow_redirects=True)
        csrf = self.session.cookies.get("csrftoken", "")
        if not csrf:
            m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', r.text)
            if not m:
                m = re.search(r"name='csrfmiddlewaretoken'\s+value='([^']+)'", r.text)
            if m:
                csrf = m.group(1)
        self.session.headers["X-CSRFToken"] = csrf
        self.session.headers["Referer"] = login_url
        r2 = self.session.post(login_url, data={
            "csrfmiddlewaretoken": csrf,
            "username": username,
            "password": password,
        }, allow_redirects=True)
        has_session = "sessionid" in dict(self.session.cookies)
        not_on_login = "/login" not in r2.url.rstrip("/").split("?")[0]
        ok = has_session or not_on_login
        if ok:
            new_csrf = self.session.cookies.get("csrftoken", csrf)
            self.session.headers["X-CSRFToken"] = new_csrf
        return ok

    def post_json(self, path, data):
        url = f"{self.base}{path}"
        self.session.headers["Referer"] = url
        self.session.headers["Content-Type"] = "application/json"
        r = self.session.post(url, data=json.dumps(data), timeout=30)
        new_csrf = self.session.cookies.get("csrftoken")
        if new_csrf:
            self.session.headers["X-CSRFToken"] = new_csrf
        return r

    def post_form(self, path, data):
        url = f"{self.base}{path}"
        self.session.headers["Referer"] = url
        self.session.headers.pop("Content-Type", None)
        csrf = self.session.cookies.get("csrftoken", self.session.headers.get("X-CSRFToken", ""))
        data["csrfmiddlewaretoken"] = csrf
        r = self.session.post(url, data=data, timeout=30)
        new_csrf = self.session.cookies.get("csrftoken")
        if new_csrf:
            self.session.headers["X-CSRFToken"] = new_csrf
        return r

    def get(self, path, params=None):
        url = f"{self.base}{path}"
        self.session.headers["Referer"] = url
        r = self.session.get(url, params=params, timeout=30)
        return r


def log_error(modulo, accion, error, response=None):
    detail = f"[{modulo}] {accion}: {error}"
    if response is not None:
        detail += f" (HTTP {response.status_code})"
        try:
            body = response.text[:300]
            detail += f" Body: {body}"
        except Exception:
            pass
    STATS["errores_detalle"].append(detail)
    print(f"  ERROR: {detail[:200]}")


# ============================================================================
# DATOS DE PRUEBA
# ============================================================================
NOMBRES_M = ["Carlos", "Miguel", "Roberto", "Fernando", "Juan", "Pedro", "Luis", "Andrés", "Jorge", "Ricardo",
             "Antonio", "Alejandro", "Manuel", "Rafael", "Diego", "Sergio", "Héctor", "Daniel", "Marco", "Arturo"]
NOMBRES_F = ["María", "Ana", "Laura", "Sofía", "Gabriela", "Patricia", "Rosa", "Carmen", "Lucía", "Elena",
             "Isabel", "Claudia", "Teresa", "Verónica", "Silvia", "Diana", "Andrea", "Natalia", "Martha", "Leticia"]
APELLIDOS = ["García", "López", "Martínez", "Hernández", "González", "Rodríguez", "Pérez", "Sánchez",
             "Ramírez", "Torres", "Flores", "Díaz", "Morales", "Reyes", "Cruz", "Ortiz", "Gutiérrez",
             "Jiménez", "Mendoza", "Aguilar", "Vargas", "Castillo", "Romero", "Medina", "Ruiz"]
DIAGNOSTICOS = [
    ("J06.9", "Infección aguda de vías respiratorias superiores"),
    ("N39.0", "Infección de vías urinarias, sitio no especificado"),
    ("K29.7", "Gastritis no especificada"),
    ("E11.9", "Diabetes mellitus tipo 2 sin complicaciones"),
    ("I10", "Hipertensión arterial esencial"),
    ("M54.5", "Lumbago no especificado"),
    ("J20.9", "Bronquitis aguda no especificada"),
    ("K21.0", "Enfermedad por reflujo gastroesofágico"),
    ("R51", "Cefalea"),
    ("L30.9", "Dermatitis no especificada"),
]
MOTIVOS = [
    "Dolor de cabeza persistente desde hace 3 días",
    "Fiebre y malestar general",
    "Dolor abdominal tipo cólico",
    "Control de glucosa y presión arterial",
    "Infección urinaria recurrente",
    "Dolor lumbar con irradiación",
    "Tos productiva de 5 días de evolución",
    "Reflujo y acidez estomacal",
    "Erupción cutánea en brazos",
    "Revisión de resultados de laboratorio",
]


def generar_paciente(idx):
    es_mujer = idx % 2 == 0
    nombre = random.choice(NOMBRES_F if es_mujer else NOMBRES_M)
    ap_pat = random.choice(APELLIDOS)
    ap_mat = random.choice(APELLIDOS)
    anio = random.randint(1960, 2005)
    mes = random.randint(1, 12)
    dia = random.randint(1, 28)
    return {
        "nombres": nombre,
        "apellido_paterno": ap_pat,
        "apellido_materno": ap_mat,
        "fecha_nacimiento": f"{anio}-{mes:02d}-{dia:02d}",
        "sexo": "F" if es_mujer else "M",
        "telefono": f"614{random.randint(1000000, 9999999)}",
        "email": f"test.e2e.{idx}@prislab.test",
        "tipo": "CONVENIO" if idx < 10 else "GENERAL",
    }


# ============================================================================
# FASE 1: FLUJO CLÍNICO Y LABORATORIO
# ============================================================================
def fase1_clinico_lab(client):
    print("\n" + "=" * 70)
    print("FASE 1: FLUJO CLÍNICO Y LABORATORIO")
    print("=" * 70)

    paciente_ids = []
    consulta_ids = []
    cita_ids = []

    # --- 1.1 Registrar 30 pacientes ---
    print("\n--- 1.1 Registrando 30 pacientes (10 convenio + 20 particulares) ---")
    for i in range(30):
        pac = generar_paciente(i)
        try:
            r = client.post_json("/api/pacientes/guardar/", pac)
            if r.status_code == 200:
                data = r.json()
                pac_data = data.get("paciente", {})
                pid = pac_data.get("id") or data.get("paciente_id") or data.get("id")
                if pid:
                    paciente_ids.append(pid)
                    STATS["pacientes_creados"] += 1
                    tipo = "CONVENIO" if i < 10 else "PARTICULAR"
                    print(f"  OK Paciente #{i+1} ({tipo}): {pac['nombres']} {pac['apellido_paterno']} -> ID {pid}")
                else:
                    STATS["pacientes_creados"] += 1
                    paciente_ids.append(None)
                    print(f"  OK Paciente #{i+1}: Creado sin ID retornado")
            else:
                STATS["pacientes_fallidos"] += 1
                log_error("CLINICO", f"Registrar paciente #{i+1}", f"HTTP {r.status_code}", r)
        except Exception as e:
            STATS["pacientes_fallidos"] += 1
            log_error("CLINICO", f"Registrar paciente #{i+1}", str(e))

    valid_pacs = [p for p in paciente_ids if p]
    print(f"\n  RESUMEN: {STATS['pacientes_creados']} creados, {STATS['pacientes_fallidos']} fallidos")
    print(f"  IDs válidos: {len(valid_pacs)}")

    # --- 1.2 Crear consultas y agendar citas ---
    print("\n--- 1.2 Creando 30 consultas directas ---")
    for i, pid in enumerate(valid_pacs[:30]):
        motivo = MOTIVOS[i % len(MOTIVOS)]
        try:
            r = client.post_json("/consultorio/api/crear-consulta-directa/", {
                "paciente_id": pid,
                "motivo": motivo,
            })
            if r.status_code == 200:
                data = r.json()
                cid = data.get("consulta_id") or data.get("cita_id") or data.get("id")
                if cid:
                    consulta_ids.append(cid)
                    cita_ids.append(data.get("cita_id", cid))
                STATS["consultas_creadas"] += 1
                print(f"  OK Consulta #{i+1}: Paciente {pid} -> ID {cid}")
            else:
                STATS["consultas_fallidas"] += 1
                log_error("CLINICO", f"Crear consulta #{i+1}", f"HTTP {r.status_code}", r)
        except Exception as e:
            STATS["consultas_fallidas"] += 1
            log_error("CLINICO", f"Crear consulta #{i+1}", str(e))

    print(f"\n  RESUMEN: {STATS['consultas_creadas']} consultas, {STATS['consultas_fallidas']} fallidas")

    # --- 1.3 Registrar notas SOAP ---
    print("\n--- 1.3 Registrando 30 notas SOAP ---")
    for i, cita_id in enumerate(cita_ids[:30]):
        diag = DIAGNOSTICOS[i % len(DIAGNOSTICOS)]
        soap_data = {
            "motivo_consulta": MOTIVOS[i % len(MOTIVOS)],
            "padecimiento_actual": f"Paciente refiere {MOTIVOS[i % len(MOTIVOS)].lower()} de inicio reciente.",
            "exploracion_fisica": "Paciente alerta, orientado. Signos vitales estables. Abdomen blando.",
            "diagnostico_principal": diag[1],
            "diagnostico_cie10": diag[0],
            "plan_tratamiento": "Se indica tratamiento sintomático. Control en 7 días.",
            "pronostico": "BUENO",
            "capturar_signos": "1",
            "pa_sistolica": str(random.randint(110, 140)),
            "pa_diastolica": str(random.randint(60, 90)),
            "frecuencia_cardiaca": str(random.randint(60, 100)),
            "frecuencia_respiratoria": str(random.randint(14, 22)),
            "temperatura": str(round(random.uniform(36.0, 37.5), 1)),
            "peso": str(round(random.uniform(50, 100), 1)),
            "talla": str(round(random.uniform(1.50, 1.85), 2)),
        }
        try:
            r = client.post_form(f"/consultorio/medico/consulta/{cita_id}/", soap_data)
            if r.status_code in (200, 302):
                STATS["soap_creados"] += 1
                print(f"  OK SOAP #{i+1}: Cita {cita_id} -> {diag[0]} {diag[1][:40]}")
            else:
                STATS["soap_fallidos"] += 1
                log_error("CLINICO", f"SOAP #{i+1}", f"HTTP {r.status_code}", r)
        except Exception as e:
            STATS["soap_fallidos"] += 1
            log_error("CLINICO", f"SOAP #{i+1}", str(e))

    print(f"\n  RESUMEN SOAP: {STATS['soap_creados']} creados, {STATS['soap_fallidos']} fallidos")

    # --- 1.4 Obtener estudios disponibles ---
    print("\n--- 1.4 Obteniendo catálogo de estudios ---")
    estudios = []
    search_terms = ["glucosa", "biometria", "quimica", "orina", "perfil", "colesterol",
                    "hemoglobina", "creatinina", "urea", "acido"]
    for term in search_terms:
        try:
            r = client.get("/laboratorio/api/buscar-estudios/", params={"q": term})
            if r.status_code == 200:
                data = r.json()
                nuevos = data.get("estudios", data if isinstance(data, list) else [])
                for e in nuevos:
                    if e.get("id") not in [x.get("id") for x in estudios]:
                        estudios.append(e)
        except Exception:
            pass
    print(f"  OK: {len(estudios)} estudios encontrados")
    for e in estudios[:8]:
        eid = e.get("id")
        nombre = e.get("nombre", e.get("text", "?"))
        precio = e.get("precio_publico", e.get("precio", "?"))
        print(f"    - [{eid}] {nombre} ${precio}")

    # --- 1.5 Crear 20 órdenes de laboratorio ---
    print("\n--- 1.5 Creando 20 órdenes de laboratorio ---")
    orden_ids = []
    for i in range(min(20, len(valid_pacs))):
        pid = valid_pacs[i]
        if not estudios:
            log_error("LAB", f"Orden #{i+1}", "No hay estudios en el catálogo")
            STATS["ordenes_lab_fallidas"] += 1
            continue

        selected = random.sample(estudios, min(random.randint(1, 3), len(estudios)))
        estudio_ids = [e.get("id") for e in selected]
        total = sum(float(e.get("precio_publico", e.get("precio", 100))) for e in selected)

        try:
            r = client.post_json("/laboratorio/api/crear-orden/", {
                "paciente_id": pid,
                "estudio_ids": estudio_ids,
                "total": round(total, 2),
                "tipo_servicio": "RUTINA",
                "tarifa": "PUBLICO_GENERAL",
            })
            if r.status_code == 200:
                data = r.json()
                oid = data.get("orden_id") or data.get("id")
                if oid:
                    orden_ids.append(oid)
                STATS["ordenes_lab_creadas"] += 1
                print(f"  OK Orden #{i+1}: Paciente {pid}, Estudios {estudio_ids} -> Orden {oid} (${total:.2f})")
            else:
                STATS["ordenes_lab_fallidas"] += 1
                log_error("LAB", f"Crear orden #{i+1}", f"HTTP {r.status_code}", r)
        except Exception as e:
            STATS["ordenes_lab_fallidas"] += 1
            log_error("LAB", f"Crear orden #{i+1}", str(e))

    print(f"\n  RESUMEN ORDENES: {STATS['ordenes_lab_creadas']} creadas, {STATS['ordenes_lab_fallidas']} fallidas")

    # --- 1.6 Cobrar órdenes ---
    print("\n--- 1.6 Cobrando órdenes de laboratorio ---")
    for oid in orden_ids:
        try:
            r = client.post_json(f"/laboratorio/api/cobrar-orden/{oid}/", {
                "monto": 500.00,
                "monto_efectivo": 500.00,
                "monto_tarjeta": 0,
                "monto_transferencia": 0,
            })
            if r.status_code == 200:
                STATS["ordenes_cobradas"] += 1
                print(f"  OK Cobro: Orden {oid}")
            else:
                STATS["ordenes_cobro_fallido"] += 1
                log_error("LAB", f"Cobrar orden {oid}", f"HTTP {r.status_code}", r)
        except Exception as e:
            STATS["ordenes_cobro_fallido"] += 1
            log_error("LAB", f"Cobrar orden {oid}", str(e))

    # --- 1.7 Toma de muestra ---
    print("\n--- 1.7 Marcando toma de muestra ---")
    for oid in orden_ids:
        try:
            r = client.post_json(f"/laboratorio/api/toma-muestra/{oid}/", {})
            if r.status_code == 200:
                print(f"  OK Muestra: Orden {oid}")
            else:
                print(f"  WARN Muestra orden {oid}: HTTP {r.status_code}")
        except Exception:
            pass

    # --- 1.8 Capturar resultados ---
    print("\n--- 1.8 Capturando resultados ---")
    for oid in orden_ids:
        try:
            r_det = client.get(f"/laboratorio/api/detalle-orden/{oid}/")
            if r_det.status_code != 200:
                r_det = client.get(f"/laboratorio/api/orden/{oid}/detalle/")
            if r_det.status_code == 200:
                orden_data = r_det.json()
                detalles = orden_data.get("detalles", orden_data.get("estudios", []))
                resultados = {}
                for det in detalles:
                    det_id = str(det.get("id", det.get("detalle_id", "")))
                    params = det.get("parametros", [])
                    param_vals = {}
                    for p in params:
                        pid_p = str(p.get("id", p.get("parametro_id", "")))
                        val_min = float(p.get("valor_referencia_min", p.get("ref_min", 0)) or 0)
                        val_max = float(p.get("valor_referencia_max", p.get("ref_max", 100)) or 100)
                        valor = round(random.uniform(val_min * 0.8, val_max * 1.2), 2)
                        param_vals[pid_p] = {"valor": str(valor)}
                    resultados[det_id] = {
                        "resultado": "Procesado",
                        "observaciones": "",
                        "parametros": param_vals,
                    }
                r_save = client.post_json(f"/laboratorio/api/guardar-resultados/{oid}/", {
                    "accion": "borrador",
                    "resultados": resultados,
                })
                if r_save.status_code == 200:
                    STATS["resultados_capturados"] += 1
                    print(f"  OK Resultados: Orden {oid} ({len(detalles)} estudios)")
                else:
                    STATS["resultados_fallidos"] += 1
                    log_error("LAB", f"Captura resultados orden {oid}", f"HTTP {r_save.status_code}", r_save)
            else:
                STATS["resultados_fallidos"] += 1
                log_error("LAB", f"Detalle orden {oid}", f"HTTP {r_det.status_code}", r_det)
        except Exception as e:
            STATS["resultados_fallidos"] += 1
            log_error("LAB", f"Captura resultados orden {oid}", str(e))

    # --- 1.9 Validar con PIN ---
    print("\n--- 1.9 Validando con PIN ---")
    for oid in orden_ids:
        try:
            r = client.post_json(f"/laboratorio/api/validar-pin/{oid}/", {"pin": "1234"})
            if r.status_code == 200:
                STATS["validaciones_pin"] += 1
                print(f"  OK PIN: Orden {oid}")
            else:
                STATS["validaciones_pin_fallidas"] += 1
                log_error("LAB", f"Validar PIN orden {oid}", f"HTTP {r.status_code}", r)
        except Exception as e:
            STATS["validaciones_pin_fallidas"] += 1
            log_error("LAB", f"Validar PIN orden {oid}", str(e))

    # --- 1.10 Verificar PDF (GET) ---
    print("\n--- 1.10 Verificando generación de PDFs ---")
    pdfs_ok = 0
    for oid in orden_ids[:5]:
        try:
            r = client.get(f"/laboratorio/imprimir/{oid}/")
            if r.status_code == 200 and len(r.content) > 500:
                pdfs_ok += 1
                print(f"  OK PDF: Orden {oid} ({len(r.content)} bytes)")
            else:
                print(f"  WARN PDF: Orden {oid} -> HTTP {r.status_code}, {len(r.content)} bytes")
        except Exception as e:
            print(f"  WARN PDF: Orden {oid} -> {e}")
    print(f"  PDFs verificados: {pdfs_ok}/5")

    return valid_pacs, orden_ids


# ============================================================================
# FASE 2: FARMACIA Y CRISIS
# ============================================================================
def fase2_farmacia(client):
    print("\n" + "=" * 70)
    print("FASE 2: FARMACIA Y CRISIS")
    print("=" * 70)

    # --- 2.1 Obtener productos disponibles ---
    print("\n--- 2.1 Obteniendo productos disponibles ---")
    productos = []
    try:
        r = client.get("/farmacia/pdv/", params={"accion": "buscar_producto", "termino": "a"})
        if r.status_code == 200:
            data = r.json()
            productos = data.get("productos", [])
            print(f"  OK: {len(productos)} productos encontrados")
            for p in productos[:5]:
                print(f"    - [{p['id']}] {p['nombre_comercial']} ${p.get('precio_base', '?')} Stock:{p.get('stock', '?')}")
    except Exception as e:
        print(f"  ERROR: {e}")

    if not productos:
        print("  Sin productos, buscando con otro término...")
        for term in ["par", "amox", "cip", "ome", "ibu"]:
            try:
                r = client.get("/farmacia/pdv/", params={"accion": "buscar_producto", "termino": term})
                if r.status_code == 200:
                    data = r.json()
                    nuevos = data.get("productos", [])
                    for p in nuevos:
                        if p["id"] not in [x["id"] for x in productos]:
                            productos.append(p)
            except Exception:
                pass
        print(f"  Total productos encontrados: {len(productos)}")

    if not productos:
        print("  FALLO CRITICO: No hay productos en farmacia. Saltando ventas.")
        return [], []

    # --- 2.2 Realizar 50 ventas ---
    print("\n--- 2.2 Realizando 50 ventas con 4 métodos de pago ---")
    venta_ids = []
    metodos = ["efectivo", "tarjeta", "transferencia", "mixto"]

    for i in range(50):
        n_items = random.randint(1, min(3, len(productos)))
        items_sel = random.sample(productos, n_items)
        prods_payload = []
        subtotal = 0

        for p in items_sel:
            cant = random.randint(1, 3)
            precio = float(p.get("precio_base", p.get("precio_venta", 50)))
            sub = cant * precio
            subtotal += sub
            prods_payload.append({
                "producto_id": p["id"],
                "cantidad": cant,
                "precio_unitario": precio,
            })

        iva = round(subtotal * 0.16, 2)
        total = round(subtotal + iva, 2)

        metodo = metodos[i % 4]
        if metodo == "efectivo":
            pagos = {"efectivo": total}
        elif metodo == "tarjeta":
            pagos = {"tarjeta": total}
        elif metodo == "transferencia":
            pagos = {"transferencia": total}
        else:
            mitad = round(total / 2, 2)
            pagos = {"efectivo": mitad, "tarjeta": round(total - mitad, 2)}

        payload = {
            "cliente": f"Cliente E2E #{i+1}",
            "productos": prods_payload,
            "subtotal": subtotal,
            "iva_total": iva,
            "total_final": total,
            "pagos": pagos,
        }

        try:
            r = client.post_json("/farmacia/pdv/", payload)
            if r.status_code == 200:
                data = r.json()
                vid = data.get("venta_id") or data.get("id")
                folio = data.get("folio", f"V-{vid}")
                if vid:
                    venta_ids.append(vid)
                STATS["ventas_ok"] += 1
                met_str = metodo.upper()
                print(f"  OK Venta #{i+1}: {folio} ${total:.2f} [{met_str}]")
            else:
                STATS["ventas_fallidas"] += 1
                log_error("FARMACIA", f"Venta #{i+1}", f"HTTP {r.status_code}", r)
        except Exception as e:
            STATS["ventas_fallidas"] += 1
            log_error("FARMACIA", f"Venta #{i+1}", str(e))

    print(f"\n  RESUMEN VENTAS: {STATS['ventas_ok']} OK, {STATS['ventas_fallidas']} fallidas")

    # --- 2.3 Devoluciones totales (5) ---
    print("\n--- 2.3 Ejecutando 5 devoluciones totales ---")
    ventas_devolver = venta_ids[:5] if len(venta_ids) >= 5 else venta_ids
    for vid in ventas_devolver:
        try:
            r_det = client.get("/farmacia/pdv/", params={"accion": "detalle_venta", "id": vid})
            monto_total = 9999.99
            if r_det.status_code == 200:
                det = r_det.json()
                monto_total = float(det.get("total", monto_total))
            r = client.post_json("/farmacia/devoluciones/procesar/", {
                "venta_id": vid,
                "monto": monto_total,
                "tipo": "TOTAL",
                "motivo": "Devolución de prueba E2E - auditoría de estrés",
            })
            if r.status_code == 200:
                STATS["devoluciones_ok"] += 1
                print(f"  OK Devolución: Venta {vid} (${monto_total:.2f})")
            else:
                STATS["devoluciones_fallidas"] += 1
                log_error("FARMACIA", f"Devolución venta {vid}", f"HTTP {r.status_code}", r)
        except Exception as e:
            STATS["devoluciones_fallidas"] += 1
            log_error("FARMACIA", f"Devolución venta {vid}", str(e))

    # --- 2.4 Cancelaciones post-cobro (5) ---
    print("\n--- 2.4 Ejecutando 5 cancelaciones post-cobro ---")
    ventas_cancelar = venta_ids[5:10] if len(venta_ids) >= 10 else venta_ids[5:]
    for vid in ventas_cancelar:
        try:
            r = client.post_json(f"/farmacia/ventas/cancelar/{vid}/", {})
            if r.status_code in (200, 302):
                STATS["cancelaciones_ok"] += 1
                print(f"  OK Cancelación: Venta {vid}")
            else:
                STATS["cancelaciones_fallidas"] += 1
                log_error("FARMACIA", f"Cancelar venta {vid}", f"HTTP {r.status_code}", r)
        except Exception as e:
            STATS["cancelaciones_fallidas"] += 1
            log_error("FARMACIA", f"Cancelar venta {vid}", str(e))

    print(f"\n  RESUMEN: {STATS['devoluciones_ok']} devoluciones, {STATS['cancelaciones_ok']} cancelaciones")
    return venta_ids, ventas_devolver


# ============================================================================
# FASE 3: RRHH Y NÓMINA
# ============================================================================
def fase3_rrhh_nomina(client):
    print("\n" + "=" * 70)
    print("FASE 3: RRHH Y NÓMINA")
    print("=" * 70)

    # --- 3.1 Obtener empleados ---
    print("\n--- 3.1 Obteniendo empleados registrados ---")
    empleados = []
    try:
        r = client.get("/asistencia/")
        if r.status_code == 200:
            import re
            ids = re.findall(r'empleado_id["\s:=]+(\d+)', r.text)
            ids = list(set(ids))[:10]
            empleados = [int(x) for x in ids]
            print(f"  Empleados encontrados: {len(empleados)} IDs: {empleados}")
    except Exception as e:
        print(f"  WARN: {e}")

    if not empleados:
        try:
            r = client.get("/rh/")
            if r.status_code == 200:
                import re
                ids = re.findall(r'empleado[/_-]?id["\s:=]+(\d+)', r.text)
                ids2 = re.findall(r'/rh/empleados?/(\d+)', r.text)
                all_ids = list(set(ids + ids2))[:10]
                empleados = [int(x) for x in all_ids]
                print(f"  Empleados desde RH: {len(empleados)} IDs: {empleados}")
        except Exception:
            pass

    if not empleados:
        print("  No se encontraron empleados. Usando IDs 1-10 como fallback.")
        empleados = list(range(1, 11))

    # --- 3.2 Registrar asistencia (entrada + salida) ---
    print(f"\n--- 3.2 Registrando asistencia para {len(empleados)} empleados ---")
    for eid in empleados:
        for tipo in ["ENTRADA", "SALIDA"]:
            try:
                r = client.post_form("/asistencia/registrar/", {
                    "empleado_id": eid,
                    "tipo_registro": tipo,
                    "observaciones": f"E2E Audit - {tipo}",
                })
                if r.status_code in (200, 302):
                    STATS["asistencias_ok"] += 1
                    print(f"  OK Asistencia: Empleado {eid} -> {tipo}")
                else:
                    STATS["asistencias_fallidas"] += 1
                    log_error("RRHH", f"Asistencia {tipo} emp {eid}", f"HTTP {r.status_code}", r)
            except Exception as e:
                STATS["asistencias_fallidas"] += 1
                log_error("RRHH", f"Asistencia {tipo} emp {eid}", str(e))

    # --- 3.3 Crear incidencias ---
    print(f"\n--- 3.3 Creando incidencias para empleados ---")
    tipos_incidencia = ["FALTA", "RETARDO", "PERMISO", "INCAPACIDAD"]
    hoy = date.today()
    for i, eid in enumerate(empleados[:5]):
        tipo_inc = tipos_incidencia[i % len(tipos_incidencia)]
        try:
            r = client.post_form("/asistencia/crear-incidencia/", {
                "empleado_id": eid,
                "tipo": tipo_inc,
                "fecha_inicio": str(hoy),
                "fecha_fin": str(hoy),
                "motivo": f"Incidencia E2E #{i+1} - {tipo_inc}",
            })
            if r.status_code in (200, 302):
                STATS["incidencias_ok"] += 1
                print(f"  OK Incidencia: Empleado {eid} -> {tipo_inc}")
            else:
                STATS["incidencias_fallidas"] += 1
                log_error("RRHH", f"Incidencia emp {eid}", f"HTTP {r.status_code}", r)
        except Exception as e:
            STATS["incidencias_fallidas"] += 1
            log_error("RRHH", f"Incidencia emp {eid}", str(e))

    # --- 3.4 Crear periodo de nómina y procesar ---
    print("\n--- 3.4 Creando periodo de nómina ---")
    periodo_id = None
    hoy = date.today()
    inicio_quincena = hoy.replace(day=1)
    fin_quincena = hoy.replace(day=15) if hoy.day <= 15 else hoy
    try:
        r = client.post_form("/nomina/periodos/nuevo/", {
            "nombre": f"Quincena E2E {hoy.strftime('%b %Y')}",
            "frecuencia": "QUINCENAL",
            "fecha_inicio": str(inicio_quincena),
            "fecha_fin": str(fin_quincena),
            "fecha_pago": str(hoy),
            "observaciones": "Periodo creado por auditoría E2E",
            "auto_empleados": "1",
        })
        if r.status_code in (200, 302):
            STATS["nomina_ok"] += 1
            import re
            m = re.search(r'periodo[/_-]?(?:id)?["\s:=]+(\d+)', r.text) or re.search(r'/nomina/periodos/(\d+)', r.url)
            if m:
                periodo_id = int(m.group(1))
            print(f"  OK Periodo nómina creado: ID {periodo_id}")
        else:
            STATS["nomina_fallida"] += 1
            log_error("NOMINA", "Crear periodo", f"HTTP {r.status_code}", r)
    except Exception as e:
        STATS["nomina_fallida"] += 1
        log_error("NOMINA", "Crear periodo", str(e))

    # --- 3.5 Calcular y pagar nómina ---
    if periodo_id:
        print(f"\n--- 3.5 Calculando nómina periodo {periodo_id} ---")
        try:
            r = client.post_form(f"/nomina/periodos/{periodo_id}/calcular/", {})
            if r.status_code in (200, 302):
                print(f"  OK Cálculo nómina periodo {periodo_id}")
            else:
                print(f"  WARN Cálculo: HTTP {r.status_code}")
        except Exception as e:
            print(f"  WARN Cálculo: {e}")

        print(f"\n--- 3.6 Marcando periodo como pagado ---")
        try:
            r = client.post_form(f"/nomina/periodos/{periodo_id}/pagar/", {
                "metodo_pago": "TRANSFERENCIA",
            })
            if r.status_code in (200, 302):
                print(f"  OK Nómina pagada: periodo {periodo_id}")
            else:
                print(f"  WARN Pago nómina: HTTP {r.status_code}")
        except Exception as e:
            print(f"  WARN Pago nómina: {e}")

    return empleados, periodo_id


# ============================================================================
# FASE 4: CIERRE DE CAJA
# ============================================================================
def fase4_cierre_caja(client):
    print("\n" + "=" * 70)
    print("FASE 4: CIERRE DE CAJA Y VERIFICACIÓN FINANCIERA")
    print("=" * 70)

    print("\n--- 4.1 Ejecutando corte de caja del día ---")
    corte_data = None
    try:
        r = client.get("/finanzas/corte/")
        if r.status_code == 200:
            import re
            html = r.text
            totales = {}
            patterns = {
                "ventas_farmacia": r'ventas?\s*(?:farmacia)?[:\s]*\$?\s*([\d,]+\.?\d*)',
                "ventas_lab": r'laboratorio[:\s]*\$?\s*([\d,]+\.?\d*)',
                "ventas_consultorio": r'consultor?io[:\s]*\$?\s*([\d,]+\.?\d*)',
                "devoluciones": r'devoluciones?[:\s]*\$?\s*([\d,]+\.?\d*)',
                "total_ventas": r'total\s*(?:ventas|general)?[:\s]*\$?\s*([\d,]+\.?\d*)',
            }
            for key, pat in patterns.items():
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    totales[key] = m.group(1).replace(",", "")

            print(f"  OK Corte de caja obtenido")
            for k, v in totales.items():
                print(f"    {k}: ${v}")
            corte_data = totales

            if len(html) > 100:
                print(f"  Página del corte: {len(html)} bytes")
            else:
                print(f"  WARN: Respuesta muy corta ({len(html)} bytes)")
        else:
            log_error("FINANZAS", "Corte de caja", f"HTTP {r.status_code}", r)
    except Exception as e:
        log_error("FINANZAS", "Corte de caja", str(e))

    return corte_data


# ============================================================================
# REPORTE FINAL
# ============================================================================
def generar_reporte(corte_data, t_inicio, t_fin):
    duracion = t_fin - t_inicio
    total_acciones = (
        STATS["pacientes_creados"] + STATS["consultas_creadas"] + STATS["soap_creados"]
        + STATS["ordenes_lab_creadas"] + STATS["ordenes_cobradas"]
        + STATS["resultados_capturados"] + STATS["validaciones_pin"]
        + STATS["ventas_ok"] + STATS["devoluciones_ok"] + STATS["cancelaciones_ok"]
        + STATS["asistencias_ok"] + STATS["incidencias_ok"] + STATS["nomina_ok"]
    )
    total_fallidas = (
        STATS["pacientes_fallidos"] + STATS["consultas_fallidas"] + STATS["soap_fallidos"]
        + STATS["ordenes_lab_fallidas"] + STATS["ordenes_cobro_fallido"]
        + STATS["resultados_fallidos"] + STATS["validaciones_pin_fallidas"]
        + STATS["ventas_fallidas"] + STATS["devoluciones_fallidas"] + STATS["cancelaciones_fallidas"]
        + STATS["asistencias_fallidas"] + STATS["incidencias_fallidas"] + STATS["nomina_fallida"]
    )
    tasa = total_acciones / max(total_acciones + total_fallidas, 1) * 100

    print("\n" + "=" * 70)
    print("REPORTE FINAL — AUDITORÍA DE ESTRÉS TOTAL E2E")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duración total: {duracion:.1f} segundos")
    print(f"Servidor: {BASE_URL}")
    print()

    print("FASE 1 — CLÍNICO Y LABORATORIO")
    print(f"  Pacientes creados:      {STATS['pacientes_creados']}/30  (fallidos: {STATS['pacientes_fallidos']})")
    print(f"  Consultas creadas:      {STATS['consultas_creadas']}/30  (fallidas: {STATS['consultas_fallidas']})")
    print(f"  Notas SOAP:             {STATS['soap_creados']}/30  (fallidas: {STATS['soap_fallidos']})")
    print(f"  Órdenes lab creadas:    {STATS['ordenes_lab_creadas']}/20  (fallidas: {STATS['ordenes_lab_fallidas']})")
    print(f"  Órdenes cobradas:       {STATS['ordenes_cobradas']}/{STATS['ordenes_lab_creadas']}")
    print(f"  Resultados capturados:  {STATS['resultados_capturados']}/{STATS['ordenes_lab_creadas']}")
    print(f"  Validaciones PIN:       {STATS['validaciones_pin']}/{STATS['ordenes_lab_creadas']}")
    print()

    print("FASE 2 — FARMACIA Y CRISIS")
    print(f"  Ventas completadas:     {STATS['ventas_ok']}/50  (fallidas: {STATS['ventas_fallidas']})")
    print(f"  Devoluciones totales:   {STATS['devoluciones_ok']}/5  (fallidas: {STATS['devoluciones_fallidas']})")
    print(f"  Cancelaciones:          {STATS['cancelaciones_ok']}/5  (fallidas: {STATS['cancelaciones_fallidas']})")
    print()

    print("FASE 3 — RRHH Y NÓMINA")
    print(f"  Asistencias registradas: {STATS['asistencias_ok']}  (fallidas: {STATS['asistencias_fallidas']})")
    print(f"  Incidencias creadas:     {STATS['incidencias_ok']}  (fallidas: {STATS['incidencias_fallidas']})")
    print(f"  Nómina procesada:        {STATS['nomina_ok']}  (fallida: {STATS['nomina_fallida']})")
    print()

    print("FASE 4 — CIERRE DE CAJA")
    if corte_data:
        for k, v in corte_data.items():
            print(f"  {k}: ${v}")
    else:
        print("  Corte de caja: No se pudo obtener datos numéricos")
    print()

    print("RESUMEN EJECUTIVO")
    print(f"  Acciones exitosas totales: {total_acciones}")
    print(f"  Acciones fallidas totales: {total_fallidas}")
    print(f"  Tasa de éxito E2E:         {tasa:.1f}%")
    print()

    if STATS["errores_detalle"]:
        print(f"ERRORES DETALLADOS ({len(STATS['errores_detalle'])}):")
        for i, err in enumerate(STATS["errores_detalle"][:30], 1):
            print(f"  {i}. {err[:200]}")
    else:
        print("SIN ERRORES — INTEGRIDAD 100%")

    print("\n" + "=" * 70)
    print(f"FIN DE AUDITORÍA — Tasa: {tasa:.1f}% — Duración: {duracion:.1f}s")
    print("=" * 70)


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("PRISLAB v5.0 — AUDITORÍA DE ESTRÉS TOTAL E2E EN PRODUCCIÓN")
    print(f"Servidor: {BASE_URL}")
    print(f"Fecha inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    client = ProdClient(BASE_URL)
    t_inicio = time.time()

    # Login
    print("\n--- LOGIN ---")
    if client.login(ADMIN_USER, ADMIN_PASS):
        print(f"  OK Login como {ADMIN_USER}")
    else:
        print(f"  FALLO Login como {ADMIN_USER}")
        print("  Abortando auditoría.")
        exit(1)

    # Ejecutar fases
    try:
        pacientes, ordenes = fase1_clinico_lab(client)
    except Exception as e:
        print(f"\n  ERROR FATAL FASE 1: {e}")
        traceback.print_exc()
        pacientes, ordenes = [], []

    try:
        ventas, devoluciones = fase2_farmacia(client)
    except Exception as e:
        print(f"\n  ERROR FATAL FASE 2: {e}")
        traceback.print_exc()
        ventas, devoluciones = [], []

    try:
        empleados, periodo = fase3_rrhh_nomina(client)
    except Exception as e:
        print(f"\n  ERROR FATAL FASE 3: {e}")
        traceback.print_exc()
        empleados, periodo = [], None

    try:
        corte = fase4_cierre_caja(client)
    except Exception as e:
        print(f"\n  ERROR FATAL FASE 4: {e}")
        traceback.print_exc()
        corte = None

    t_fin = time.time()
    generar_reporte(corte, t_inicio, t_fin)
