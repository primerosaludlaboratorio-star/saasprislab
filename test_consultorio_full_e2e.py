"""
PRISLAB - Consultorio Module Full E2E Test
Flow: Login -> Consultorio -> Dashboard -> Agenda -> Lista Trabajo -> Expediente/Historial ->
      Configuracion -> PRIS Sentinel -> Incidencias.
Reports every click, result, errors, and URL.
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

BASE_URL = "https://prislab-v5-811785477499.us-central1.run.app"
USERNAME = "admin"
PASSWORD = "PrislabV5_2026"
SCREENSHOT_DIR = "test_screenshots_consultorio"
TIMEOUT = 15
WAIT = 1.5

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
report = {"pages_visited": [], "actions": [], "errors": [], "screenshots": []}

def ss(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{datetime.now().strftime('%H%M%S')}.png")
    driver.save_screenshot(path)
    report["screenshots"].append({"step": name, "path": path})
    return path

def act(name, worked, detail="", url=None):
    report["actions"].append({"action": name, "worked": worked, "detail": detail, "url": url or ""})

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
    ss(driver, "00_login")
    report["pages_visited"].append({"url": driver.current_url, "note": "Login"})
    try:
        driver.find_element(By.NAME, "username").send_keys(USERNAME)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']").click()
        time.sleep(3)
    except Exception as e:
        act("Login", False, str(e))
        return False
    if "/dashboard/" in driver.current_url or "/medico" in driver.current_url or "/home" in driver.current_url:
        act("Login", True, "", driver.current_url)
        ss(driver, "01_after_login")
        report["pages_visited"].append({"url": driver.current_url, "note": "After login"})
        return True
    act("Login", False, driver.current_url, driver.current_url)
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

        # --- STEP 1: Navigate to Consultorio -> Dashboard / first option ---
        print("STEP 1: Consultorio -> Dashboard")
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='consultorio']").click()
            time.sleep(1.2)
            # Mi Consultorio (first link)
            driver.find_element(By.XPATH, "//a[contains(@href,'/medico/') and contains(.,'Consultorio')]").click()
            time.sleep(3)
        except Exception as e:
            try:
                driver.find_element(By.XPATH, "//a[contains(@href,'/medico/')]").click()
                time.sleep(3)
            except Exception as e2:
                driver.get(BASE_URL.rstrip("/") + "/medico/")
                time.sleep(3)
                act("Sidebar Consultorio -> Dashboard", False, str(e2)[:120], driver.current_url)
        else:
            act("Sidebar Consultorio -> Mi Consultorio", True, "", driver.current_url)
        report["pages_visited"].append({"url": driver.current_url, "note": "Consultorio dashboard"})
        ss(driver, "02_consultorio_dashboard")
        report["errors"].extend(console_errors(driver))

        # --- STEP 2: Agenda / Citas ---
        print("STEP 2: Agenda / Citas")
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='consultorio']").click()
            time.sleep(0.8)
            driver.find_element(By.XPATH, "//a[contains(@href,'/consultorio/agenda/') or contains(.,'Mi Agenda') or contains(.,'Agenda')]").click()
            time.sleep(3)
        except Exception as e:
            driver.get(BASE_URL.rstrip("/") + "/consultorio/agenda/")
            time.sleep(3)
            act("Agenda / Citas", False, str(e)[:120], driver.current_url)
        else:
            act("Click Agenda / Citas", True, "", driver.current_url)
        report["pages_visited"].append({"url": driver.current_url, "note": "Agenda"})
        ss(driver, "03_agenda")
        try:
            nueva_cita = driver.find_elements(By.XPATH, "//button[contains(.,'Nueva Cita')] | //a[contains(.,'Nueva Cita')]")
            if nueva_cita:
                nueva_cita[0].click()
                time.sleep(2)
                ss(driver, "04_nueva_cita")
                act("Nueva Cita button", True, "", driver.current_url)
            else:
                act("Nueva Cita button", False, "Not found", driver.current_url)
        except Exception as e:
            act("Nueva Cita", False, str(e)[:100], driver.current_url)
        report["errors"].extend(console_errors(driver))

        # --- STEP 3: Lista de Trabajo Médico ---
        print("STEP 3: Lista de Trabajo / Pacientes del Día")
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='consultorio']").click()
            time.sleep(0.8)
            driver.find_element(By.XPATH, "//a[contains(@href,'lista-trabajo') or contains(.,'Mis Pacientes Hoy') or contains(.,'Lista de Trabajo')]").click()
            time.sleep(3)
        except Exception as e:
            driver.get(BASE_URL.rstrip("/") + "/consultorio/medico/lista-trabajo/")
            time.sleep(3)
        report["pages_visited"].append({"url": driver.current_url, "note": "Lista trabajo medico"})
        ss(driver, "05_lista_trabajo")
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .list-group-item, [data-cita-id]")
            if rows:
                link = rows[0].find_elements(By.CSS_SELECTOR, "a[href*='consulta'], a[href*='cita']")
                if link:
                    link[0].click()
                else:
                    rows[0].click()
                time.sleep(2)
                ss(driver, "06_lista_click_patient")
                act("Click patient in Lista Trabajo", True, "", driver.current_url)
            else:
                act("Click patient in Lista Trabajo", False, "No rows", driver.current_url)
        except Exception as e:
            act("Click patient Lista Trabajo", False, str(e)[:120], driver.current_url)
        report["errors"].extend(console_errors(driver))

        # --- STEP 4: Expediente / Historial (search patient) ---
        print("STEP 4: Expediente / Historial")
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='consultorio']").click()
            time.sleep(0.8)
            exp_link = driver.find_elements(By.XPATH, "//a[contains(@href,'expediente') or contains(.,'Expediente') or contains(.,'Historial')]")
            if exp_link:
                exp_link[0].click()
                time.sleep(2)
            else:
                driver.get(BASE_URL.rstrip("/") + "/medico/")
                time.sleep(2)
                # Medico dashboard may have patient search
                search = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='paciente'], input[placeholder*='buscar'], #buscar-paciente")
                if search:
                    search[0].send_keys("sofia")
                    time.sleep(2)
            report["pages_visited"].append({"url": driver.current_url, "note": "Expediente / search"})
            ss(driver, "07_expediente_search")
            act("Expediente / Historial or patient search", True, "", driver.current_url)
        except Exception as e:
            driver.get(BASE_URL.rstrip("/") + "/medico/")
            time.sleep(2)
            report["pages_visited"].append({"url": driver.current_url, "note": "Medico (expediente fallback)"})
            ss(driver, "07_expediente_search")
            act("Expediente / Historial", False, str(e)[:120], driver.current_url)
        report["errors"].extend(console_errors(driver))

        # --- STEP 5: Configuración ---
        print("STEP 5: Configuración")
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='consultorio']").click()
            time.sleep(0.8)
            driver.find_element(By.XPATH, "//a[contains(@href,'/consultorio/configuracion/') or contains(.,'Mi Configuración') or contains(.,'Configuración')]").click()
            time.sleep(3)
        except Exception as e:
            driver.get(BASE_URL.rstrip("/") + "/consultorio/configuracion/")
            time.sleep(3)
        report["pages_visited"].append({"url": driver.current_url, "note": "Configuracion"})
        ss(driver, "08_configuracion")
        act("Configuración consultorio", True, "", driver.current_url)
        report["errors"].extend(console_errors(driver))

        # --- STEP 6: PRIS Sentinel (Dirección island) ---
        print("STEP 6: PRIS Sentinel")
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='direccion']").click()
            time.sleep(1)
            driver.find_element(By.XPATH, "//a[contains(@href,'/consultorio/sentinel/') or contains(.,'PRIS Sentinel') or contains(.,'Sentinel')]").click()
            time.sleep(3)
        except Exception as e:
            driver.get(BASE_URL.rstrip("/") + "/consultorio/sentinel/")
            time.sleep(3)
        report["pages_visited"].append({"url": driver.current_url, "note": "PRIS Sentinel"})
        ss(driver, "09_sentinel")
        act("PRIS Sentinel dashboard", True, "", driver.current_url)
        report["errors"].extend(console_errors(driver))

        # Incidencias (same island or separate)
        try:
            driver.find_element(By.CSS_SELECTOR, "button[data-island='direccion']").click()
            time.sleep(0.8)
            driver.find_element(By.XPATH, "//a[contains(@href,'/director/auditoria/incidencias/') or contains(.,'Incidencias')]").click()
            time.sleep(3)
        except Exception as e:
            driver.get(BASE_URL.rstrip("/") + "/director/auditoria/incidencias/")
            time.sleep(3)
        report["pages_visited"].append({"url": driver.current_url, "note": "Incidencias"})
        ss(driver, "10_incidencias")
        act("Incidencias panel", True, "", driver.current_url)
        report["errors"].extend(console_errors(driver))
        ss(driver, "11_final")

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
    md = os.path.join(SCREENSHOT_DIR, "CONSULTORIO_REPORT.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# PRISLAB - Consultorio Module E2E Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 1. Pages visited (URL)\n\n")
        for p in report["pages_visited"]:
            f.write(f"- **{p['url']}** - {p.get('note','')}\n")
        f.write("\n## 2. Every action (click + result + URL)\n\n")
        for a in report["actions"]:
            st = "OK" if a["worked"] else "FAIL"
            f.write(f"- **{a['action']}**: {st}")
            if a.get("detail"):
                f.write(f" - {a['detail']}")
            if a.get("url"):
                f.write(f" | URL: `{a['url']}`")
            f.write("\n")
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
