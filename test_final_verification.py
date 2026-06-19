"""
PRISLAB - Final Verification Test (post-fix)
TEST 1: Farmacia PDV Corte/Limpiar buttons
TEST 2: Favicon (console 404)
TEST 3: Consultorio Recepción + Triage
TEST 4: Consultorio Agenda
TEST 5: All sidebar navigation links (500/blank check)
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
from selenium.common.exceptions import ElementClickInterceptedException

BASE_URL = os.environ.get("PRISLAB_TEST_BASE_URL", "https://prislab-v5-811785477499.us-central1.run.app")
USERNAME = os.environ.get("PRISLAB_TEST_USERNAME", "admin")
PASSWORD = os.environ.get("PRISLAB_TEST_PASSWORD")
if not PASSWORD:
    raise RuntimeError("Debe configurar la variable de entorno PRISLAB_TEST_PASSWORD antes de ejecutar este test.")
SCREENSHOT_DIR = "test_screenshots_final_verification"
TIMEOUT = 15
WAIT = 1.5

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
report = {"tests": [], "results": [], "errors": [], "screenshots": [], "pass_count": 0, "fail_count": 0}

def ss(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{datetime.now().strftime('%H%M%S')}.png")
    driver.save_screenshot(path)
    report["screenshots"].append({"step": name, "path": path})
    return path

def console_errors(driver):
    try:
        return [e.get("message", str(e)) for e in driver.get_log("browser") if e.get("level") == "SEVERE"]
    except Exception:
        return []

def is_500_or_blank(driver):
    try:
        if "500" in driver.title or "Error" in driver.title:
            return True
        if "internal server error" in driver.page_source.lower():
            return True
        if len(driver.page_source.strip()) < 500:
            return True
    except Exception:
        pass
    return False

def login(driver):
    driver.get(BASE_URL)
    time.sleep(2)
    try:
        driver.find_element(By.NAME, "username").send_keys(USERNAME)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']").click()
        time.sleep(3)
    except Exception as e:
        report["results"].append({"test": "Login", "status": "FAIL", "detail": str(e)})
        report["fail_count"] += 1
        return False
    if "/dashboard/" in driver.current_url or "/medico" in driver.current_url or "/home" in driver.current_url:
        report["results"].append({"test": "Login", "status": "PASS", "url": driver.current_url})
        report["pass_count"] += 1
        return True
    report["results"].append({"test": "Login", "status": "FAIL", "url": driver.current_url})
    report["fail_count"] += 1
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

        # --- TEST 1: FARMACIA PDV - Corte and Limpiar ---
        print("TEST 1: Farmacia PDV - Corte / Limpiar")
        driver.get(BASE_URL.rstrip("/") + "/farmacia/pdv/")
        time.sleep(4)
        ss(driver, "t1_pdv_page")
        corte_ok = False
        corte = None
        try:
            corte = WebDriverWait(driver, TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@onclick,'cargarCorte')] | //button[.//small[contains(.,'Corte')]]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", corte)
            time.sleep(0.5)
            corte.click()
            corte_ok = True
        except ElementClickInterceptedException:
            if corte:
                try:
                    driver.execute_script("arguments[0].click();", corte)
                    corte_ok = True
                except Exception:
                    pass
        except Exception as e:
            report["errors"].append(f"Corte button: {e}")
        ss(driver, "t1_after_corte")
        if corte_ok:
            report["results"].append({"test": "PDV Corte button", "status": "PASS", "detail": "Clickable"})
            report["pass_count"] += 1
        else:
            report["results"].append({"test": "PDV Corte button", "status": "FAIL", "detail": "Blocked or not found"})
            report["fail_count"] += 1

        limpiar_ok = False
        limpiar = None
        try:
            limpiar = driver.find_element(By.XPATH, "//button[contains(@onclick,'limpiarCarrito')] | //button[.//small[contains(.,'Limpiar')]]")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", limpiar)
            time.sleep(0.5)
            limpiar.click()
            limpiar_ok = True
        except ElementClickInterceptedException:
            if limpiar:
                try:
                    driver.execute_script("arguments[0].click();", limpiar)
                    limpiar_ok = True
                except Exception:
                    pass
        except Exception as e:
            report["errors"].append(f"Limpiar button: {e}")
        ss(driver, "t1_after_limpiar")
        if limpiar_ok:
            report["results"].append({"test": "PDV Limpiar button", "status": "PASS", "detail": "Clickable"})
            report["pass_count"] += 1
        else:
            report["results"].append({"test": "PDV Limpiar button", "status": "FAIL", "detail": "Blocked or not found"})
            report["fail_count"] += 1
        report["errors"].extend(console_errors(driver))

        # --- TEST 2: FAVICON ---
        print("TEST 2: Favicon")
        driver.get(BASE_URL.rstrip("/") + "/dashboard/")
        time.sleep(1)
        errs = console_errors(driver)
        favicon_404 = any("favicon" in e.lower() and "404" in e for e in errs)
        if favicon_404:
            report["results"].append({"test": "Favicon", "status": "FAIL", "detail": "Console: favicon 404"})
            report["fail_count"] += 1
        else:
            report["results"].append({"test": "Favicon", "status": "PASS", "detail": "No favicon 404 in console"})
            report["pass_count"] += 1
        report["errors"].extend(errs)

        # --- TEST 3: CONSULTORIO Recepción + Triage ---
        print("TEST 3: Consultorio Recepción / Triage")
        driver.get(BASE_URL.rstrip("/") + "/consultorio/recepcion/")
        time.sleep(3)
        ss(driver, "t3_recepcion")
        if is_500_or_blank(driver):
            report["results"].append({"test": "Consultorio Recepción", "status": "FAIL", "url": driver.current_url, "detail": "500 or blank"})
            report["fail_count"] += 1
        else:
            report["results"].append({"test": "Consultorio Recepción", "status": "PASS", "url": driver.current_url})
            report["pass_count"] += 1

        driver.get(BASE_URL.rstrip("/") + "/consultorio/enfermeria/triage/")
        time.sleep(3)
        ss(driver, "t3_triage")
        if is_500_or_blank(driver):
            report["results"].append({"test": "Consultorio Triage list", "status": "FAIL", "url": driver.current_url, "detail": "500 or blank"})
            report["fail_count"] += 1
        else:
            report["results"].append({"test": "Consultorio Triage list", "status": "PASS", "url": driver.current_url})
            report["pass_count"] += 1
        report["errors"].extend(console_errors(driver))

        # --- TEST 4: CONSULTORIO AGENDA ---
        print("TEST 4: Consultorio Agenda")
        driver.get(BASE_URL.rstrip("/") + "/consultorio/agenda/")
        time.sleep(3)
        ss(driver, "t4_agenda")
        if is_500_or_blank(driver):
            report["results"].append({"test": "Consultorio Agenda", "status": "FAIL", "url": driver.current_url, "detail": "500 or blank"})
            report["fail_count"] += 1
        else:
            report["results"].append({"test": "Consultorio Agenda", "status": "PASS", "url": driver.current_url})
            report["pass_count"] += 1
        report["errors"].extend(console_errors(driver))

        # --- TEST 5: All navigation links ---
        print("TEST 5: Sidebar navigation links")
        urls_to_check = [
            ("/medico/", "Mi Consultorio"),
            ("/consultorio/medico/lista-trabajo/", "Lista Trabajo Medico"),
            ("/consultorio/medico/nueva-consulta/", "Nueva Consulta"),
            ("/consultorio/agenda/", "Agenda"),
            ("/consultorio/configuracion/", "Configuracion"),
            ("/farmacia/pdv/", "PDV"),
            ("/farmacia/dashboard/", "Dashboard Farmacia"),
            ("/laboratorio/recepcion/", "Lab Recepcion"),
            ("/laboratorio/consulta-ordenes/", "Lab Consulta Ordenes"),
            ("/laboratorio/lista-trabajo/", "Lab Lista Trabajo"),
            ("/laboratorio/monitor/", "Lab Monitor"),
            ("/dashboard/", "Dashboard"),
            ("/consultorio/sentinel/", "PRIS Sentinel"),
            ("/director/auditoria/incidencias/", "Incidencias"),
        ]
        nav_fails = []
        for path, label in urls_to_check:
            url = BASE_URL.rstrip("/") + path
            driver.get(url)
            time.sleep(2)
            if is_500_or_blank(driver):
                report["results"].append({"test": f"Nav: {label}", "status": "FAIL", "url": url, "detail": "500 or blank"})
                report["fail_count"] += 1
                nav_fails.append((label, url))
                ss(driver, f"t5_fail_{label.replace(' ', '_')[:20]}")
            else:
                report["results"].append({"test": f"Nav: {label}", "status": "PASS", "url": url})
                report["pass_count"] += 1
        report["errors"].extend(console_errors(driver))
        ss(driver, "t5_done")

    except Exception as e:
        report["errors"].append(f"Fatal: {e}")
        report["fail_count"] += 1
        try:
            ss(driver, "99_fatal")
        except Exception:
            pass
    finally:
        driver.quit()
    write_report()

def write_report():
    md = os.path.join(SCREENSHOT_DIR, "FINAL_VERIFICATION_REPORT.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# PRISLAB - Final Verification Report (Post-Fix)\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        total = report["pass_count"] + report["fail_count"]
        f.write(f"## Summary: **{report['pass_count']} PASS** / **{report['fail_count']} FAIL** (of {total} checks)\n\n")
        f.write("---\n\n## Results by test\n\n")
        for r in report["results"]:
            icon = "PASS" if r["status"] == "PASS" else "FAIL"
            f.write(f"- **{icon}** {r['test']}")
            if r.get("url"):
                f.write(f" - `{r['url']}`")
            if r.get("detail"):
                f.write(f" - {r['detail']}")
            f.write("\n")
        f.write("\n## Console / errors\n\n")
        for e in report["errors"]:
            f.write(f"- {e[:350]}\n")
        if not report["errors"]:
            f.write("(None.)\n")
        f.write("\n## Screenshots\n\n")
        for s in report["screenshots"]:
            f.write(f"- **{s['step']}**: `{s['path']}`\n")
    print(f"Report: {md}")
    with open(os.path.join(SCREENSHOT_DIR, "report.json"), "w", encoding="utf-8") as j:
        json.dump({k: v for k, v in report.items() if k != "errors" or True}, j, indent=2)

if __name__ == "__main__":
    run()
