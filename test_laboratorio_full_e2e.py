"""
PRISLAB - Laboratorio Module Full E2E Test
Flow: Login -> Lab sidebar -> Registro Orden -> patient/study search -> Generar Orden ->
      Consulta Ordenes -> order row -> Detalle -> study search, Agregar Pago, print ->
      Lista Trabajo / Captura -> Entrega Resultados.
Reports every click, success/error, and console errors.
"""

import time
import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = os.environ.get("PRISLAB_TEST_BASE_URL", "https://prislab-v5-811785477499.us-central1.run.app")
USERNAME = os.environ.get("PRISLAB_TEST_USERNAME", "admin")
PASSWORD = os.environ.get("PRISLAB_TEST_PASSWORD")
if not PASSWORD:
    raise RuntimeError("Debe configurar la variable de entorno PRISLAB_TEST_PASSWORD antes de ejecutar este test.")
SCREENSHOT_DIR = "test_screenshots_laboratorio"
TIMEOUT = 15
WAIT = 1.5

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
report = {"pages_visited": [], "actions": [], "errors": [], "screenshots": []}

def ss(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{datetime.now().strftime('%H%M%S')}.png")
    driver.save_screenshot(path)
    report["screenshots"].append({"step": name, "path": path})
    return path

def act(driver, name, worked, detail=""):
    report["actions"].append({"action": name, "worked": worked, "detail": detail})

def err(msg):
    report["errors"].append(msg)

def console_errors(driver):
    try:
        return [e.get("message", str(e)) for e in driver.get_log("browser") if e.get("level") == "SEVERE"]
    except Exception:
        return []

def login(driver):
    driver.get(BASE_URL)
    time.sleep(2)
    ss(driver, "00_login_page")
    report["pages_visited"].append({"url": driver.current_url, "note": "Login"})
    try:
        driver.find_element(By.NAME, "username").send_keys(USERNAME)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']").click()
        time.sleep(3)
    except Exception as e:
        act(driver, "Login", False, str(e))
        return False
    if "/dashboard/" in driver.current_url or "/farmacia" in driver.current_url or "/home" in driver.current_url:
        act(driver, "Login", True)
        ss(driver, "01_after_login")
        report["pages_visited"].append({"url": driver.current_url, "note": "After login"})
        return True
    act(driver, "Login", False, driver.current_url)
    return False

def run():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--ignore-certificate-errors")
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    try:
        if not login(driver):
            write_report()
            return
        report["errors"].extend(console_errors(driver))

        # --- STEP 1: Navigate to Laboratorio -> Registro de Orden ---
        print("STEP 1: Laboratorio -> Registro de Orden")
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='laboratorio']").click()
            time.sleep(1.2)
            driver.find_element(By.XPATH, "//a[contains(@href,'/laboratorio/recepcion/') or contains(.,'Registro de Orden')]").click()
            time.sleep(3)
        except Exception as e:
            driver.get(BASE_URL.rstrip("/") + "/laboratorio/recepcion/")
            time.sleep(3)
            act(driver, "Sidebar Lab -> Registro Orden", False, str(e)[:150])
        else:
            act(driver, "Sidebar Lab -> Registro Orden", True)
        report["pages_visited"].append({"url": driver.current_url, "note": "Reception page"})
        ss(driver, "02_recepcion_page")
        report["errors"].extend(console_errors(driver))

        # --- STEP 2: Reception - patient search, study search, Generar Orden ---
        print("STEP 2: Reception - search and Generar Orden")
        # Patient search "sofia"
        try:
            inp = driver.find_element(By.ID, "buscar-paciente")
            inp.clear()
            inp.send_keys("sofia")
            time.sleep(2)
            ss(driver, "03_patient_search_sofia")
            res = driver.find_elements(By.CSS_SELECTOR, "#resultados-pacientes-lab .list-group-item, #resultados-pacientes-lab li")
            act(driver, "Patient search (sofia)", True, f"Results area: {len(res)} items")
        except Exception as e:
            act(driver, "Patient search (sofia)", False, str(e)[:150])
            err(f"Patient search: {e}")
        # Study search "bio"
        try:
            inp = driver.find_element(By.ID, "buscar-estudio")
            inp.clear()
            inp.send_keys("bio")
            time.sleep(2)
            ss(driver, "04_study_search_bio")
            res = driver.find_elements(By.CSS_SELECTOR, "#resultados-estudios .list-group-item-action, #resultados-estudios .list-group-item")
            act(driver, "Study search (bio)", True, f"Results: {len(res)} items")
        except Exception as e:
            act(driver, "Study search (bio)", False, str(e)[:150])
            err(f"Study search: {e}")
        # Generar Orden (CONFIRMAR ORDEN)
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(.,'CONFIRMAR ORDEN') or contains(@onclick,'generarOrden')]")
            btn.click()
            time.sleep(2)
            ss(driver, "05_after_generar_orden")
            # Check for alert/Swal or error on page
            alerts = driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .swal2-popup, [role='alert']")
            err_visible = any("error" in (a.text or "").lower() or "debe" in (a.text or "").lower() for a in alerts)
            act(driver, "Generar Orden (click)", True, "Expected validation if no patient/studies" if err_visible else "Clicked")
        except Exception as e:
            act(driver, "Generar Orden", False, str(e)[:150])
            err(f"Generar Orden: {e}")
        report["errors"].extend(console_errors(driver))

        # --- STEP 3: Consulta de Ordenes ---
        print("STEP 3: Consulta de Ordenes")
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='laboratorio']").click()
            time.sleep(0.8)
            driver.find_element(By.XPATH, "//a[contains(@href,'/laboratorio/consulta-ordenes/') or contains(.,'Consulta de Órdenes')]").click()
            time.sleep(3)
        except Exception as e:
            driver.get(BASE_URL.rstrip("/") + "/laboratorio/consulta-ordenes/")
            time.sleep(3)
        report["pages_visited"].append({"url": driver.current_url, "note": "Consulta Ordenes"})
        ss(driver, "06_consulta_ordenes")
        # Click first order row if any
        try:
            row = driver.find_elements(By.CSS_SELECTOR, "table tbody tr[data-orden-id], table tbody tr a[href*='detalle-orden'], table tbody tr.clickable")
            if not row:
                row = driver.find_elements(By.XPATH, "//tbody/tr[.//a[contains(@href,'detalle')]]")
            if not row:
                row = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            if row:
                try:
                    link = row[0].find_element(By.CSS_SELECTOR, "a[href*='detalle']")
                    link.click()
                except Exception:
                    row[0].click()
                time.sleep(2)
                ss(driver, "07_detalle_orden")
                report["pages_visited"].append({"url": driver.current_url, "note": "Detalle orden"})
                act(driver, "Click order row -> Detalle", True)
            else:
                act(driver, "Click order row", False, "No rows found")
        except Exception as e:
            act(driver, "Click order row", False, str(e)[:150])

        # --- STEP 4: Detalle - study search, Agregar Pago, print buttons ---
        print("STEP 4: Detalle orden actions")
        if "/detalle-orden/" in driver.current_url:
            try:
                study_inp = driver.find_elements(By.ID, "buscar-estudio")
                if not study_inp:
                    study_inp = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='estudio'], input[placeholder*='Buscar']")
                if study_inp:
                    study_inp[0].send_keys("bio")
                    time.sleep(1.5)
                    ss(driver, "08_detalle_study_search")
                    act(driver, "Detalle study search bar", True)
                else:
                    act(driver, "Detalle study search bar", False, "Input not found")
            except Exception as e:
                act(driver, "Detalle study search", False, str(e)[:100])
            try:
                agregar_pago = driver.find_elements(By.XPATH, "//button[contains(.,'Agregar Pago') or contains(.,'Pago')]")
                if agregar_pago:
                    agregar_pago[0].click()
                    time.sleep(1.5)
                    ss(driver, "09_agregar_pago")
                    act(driver, "Agregar Pago button", True)
                else:
                    act(driver, "Agregar Pago button", False, "Not found")
            except Exception as e:
                act(driver, "Agregar Pago", False, str(e)[:100])
            try:
                reimprimir = driver.find_elements(By.XPATH, "//a[contains(@href,'ticket') or contains(.,'Recibo') or contains(.,'Reimprimir')]")
                etiqueta = driver.find_elements(By.XPATH, "//a[contains(@href,'etiqueta') or contains(.,'Etiqueta')]")
                for lbl, el in [("Reimprimir Recibo", reimprimir), ("Etiqueta", etiqueta)]:
                    if el:
                        act(driver, f"Print button {lbl}", True, "Present")
                    else:
                        act(driver, f"Print button {lbl}", False, "Not found")
                ss(driver, "10_detalle_print_buttons")
            except Exception as e:
                act(driver, "Print buttons check", False, str(e)[:100])
        report["errors"].extend(console_errors(driver))

        # --- STEP 5: Captura / Lista de Trabajo ---
        print("STEP 5: Captura / Lista de Trabajo")
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='laboratorio']").click()
            time.sleep(0.8)
            driver.find_element(By.XPATH, "//a[contains(@href,'/laboratorio/lista-trabajo/') or contains(.,'Registro de Resultados') or contains(.,'Lista de Trabajo')]").click()
            time.sleep(3)
        except Exception as e:
            driver.get(BASE_URL.rstrip("/") + "/laboratorio/lista-trabajo/")
            time.sleep(3)
        report["pages_visited"].append({"url": driver.current_url, "note": "Lista trabajo"})
        ss(driver, "11_lista_trabajo")
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .list-group-item, [data-orden-id]")
            if rows:
                link = rows[0].find_elements(By.CSS_SELECTOR, "a[href*='captura']")
                if link:
                    link[0].click()
                else:
                    rows[0].click()
                time.sleep(2)
                ss(driver, "12_captura_page")
                report["pages_visited"].append({"url": driver.current_url, "note": "Captura resultados"})
                act(driver, "Click order -> Captura", True)
                result_input = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='number']")
                if result_input:
                    result_input[0].send_keys("1")
                    time.sleep(0.5)
                    ss(driver, "13_captura_value_entered")
                    act(driver, "Enter value in result field", True)
                else:
                    act(driver, "Enter value in result field", False, "No input found")
            else:
                act(driver, "Click order in Lista Trabajo", False, "No rows")
        except Exception as e:
            act(driver, "Lista Trabajo -> Captura", False, str(e)[:150])
        report["errors"].extend(console_errors(driver))

        # --- STEP 6: Entrega de Resultados ---
        print("STEP 6: Entrega de Resultados")
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='laboratorio']").click()
            time.sleep(0.8)
            driver.find_element(By.XPATH, "//a[contains(@href,'/laboratorio/entrega-resultados/') or contains(.,'Entrega de Resultados')]").click()
            time.sleep(3)
        except Exception as e:
            driver.get(BASE_URL.rstrip("/") + "/laboratorio/entrega-resultados/")
            time.sleep(3)
        report["pages_visited"].append({"url": driver.current_url, "note": "Entrega resultados"})
        ss(driver, "14_entrega_resultados")
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, "button.btn, a.btn")
            if btns:
                act(driver, "Entrega Resultados page buttons", True, f"{len(btns)} buttons present")
            else:
                act(driver, "Entrega Resultados page", True, "Page loaded")
        except Exception as e:
            act(driver, "Entrega Resultados", False, str(e)[:100])
        report["errors"].extend(console_errors(driver))
        ss(driver, "15_final")

    except Exception as e:
        err(f"Fatal: {e}")
        try:
            ss(driver, "99_fatal")
        except Exception:
            pass
    finally:
        driver.quit()
    write_report()

def write_report():
    md = os.path.join(SCREENSHOT_DIR, "LABORATORIO_REPORT.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# PRISLAB - Laboratorio Module E2E Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 1. Pages visited (URL)\n\n")
        for p in report["pages_visited"]:
            f.write(f"- {p['url']} - {p.get('note','')}\n")
        f.write("\n## 2. Every action (click / result)\n\n")
        for a in report["actions"]:
            st = "OK" if a["worked"] else "FAIL"
            f.write(f"- **{a['action']}**: {st}" + (f" - {a['detail']}" if a.get("detail") else "") + "\n")
        f.write("\n## 3. Errors (on-screen + console)\n\n")
        for e in report["errors"]:
            f.write(f"- {e[:400]}\n")
        if not report["errors"]:
            f.write("(None captured.)\n")
        f.write("\n## 4. Screenshots\n\n")
        for s in report["screenshots"]:
            f.write(f"- **{s['step']}**: `{s['path']}`\n")
    print(f"Report: {md}")
    with open(os.path.join(SCREENSHOT_DIR, "report.json"), "w", encoding="utf-8") as j:
        json.dump(report, j, indent=2)

if __name__ == "__main__":
    run()
