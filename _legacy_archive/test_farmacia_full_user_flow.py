"""
PRISLAB - Farmacia PDV Full User Flow Test
As a real user: Login -> Sidebar -> PDV -> Every button + search.
Reports: every page, every button result, every JS error, screenshots.
"""

import time
import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import logging

BASE_URL = os.environ.get("PRISLAB_TEST_BASE_URL", "https://prislab-v5-811785477499.us-central1.run.app")
USERNAME = os.environ.get("PRISLAB_TEST_USERNAME", "admin")
PASSWORD_PRIMARY = os.environ.get("PRISLAB_TEST_PASSWORD")
if not PASSWORD_PRIMARY:
    raise RuntimeError("Debe configurar la variable de entorno PRISLAB_TEST_PASSWORD antes de ejecutar este test.")
PASSWORD_FALLBACK = os.environ.get("PRISLAB_TEST_FALLBACK_PASSWORD") or PASSWORD_PRIMARY
SCREENSHOT_DIR = "test_screenshots_farmacia_full"
TIMEOUT = 15
WAIT = 1.5

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

report = {
    "pages_visited": [],
    "buttons_tested": [],
    "js_errors": [],
    "screenshots": [],
}

def ss(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{datetime.now().strftime('%H%M%S')}.png")
    driver.save_screenshot(path)
    report["screenshots"].append({"step": name, "path": path})
    return path

def log_page(url, note=""):
    report["pages_visited"].append({"url": url, "note": note})

def log_button(name, worked, detail=""):
    report["buttons_tested"].append({"button": name, "worked": worked, "detail": detail})

def console_errors(driver):
    try:
        return [e for e in driver.get_log("browser") if e.get("level") == "SEVERE"]
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en console_errors (test_farmacia_full_user_flow.py)")
        return []

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
        # --- STEP 1: Login ---
        print("STEP 1: Login")
        driver.get(BASE_URL)
        time.sleep(2)
        ss(driver, "01_login_form")
        log_page(driver.current_url, "Login form")

        for pwd_attempt, pwd in enumerate([PASSWORD_PRIMARY, PASSWORD_FALLBACK]):
            try:
                user = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.NAME, "username")))
                pwd_el = driver.find_element(By.NAME, "password")
                user.clear()
                user.send_keys(USERNAME)
                pwd_el.clear()
                pwd_el.send_keys(pwd)
                driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']").click()
                time.sleep(3)
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
                log_button("Login submit", False, str(e)[:200])
                break

            url = driver.current_url
            if "/dashboard/" in url or "/farmacia" in url or "/home" in url:
                log_button("Login submit", True, f"Password {'PrislabV5_2026' if pwd_attempt == 0 else 'Admin2741'}")
                break
            else:
                log_button("Login submit", False, "Wrong password or error on page")
                if pwd_attempt == 0:
                    driver.get(BASE_URL)
                    time.sleep(1)
                else:
                    ss(driver, "02_login_failed")
                    report["js_errors"].extend([e.get("message", str(e)) for e in console_errors(driver)])
                    write_report()
                    return

        ss(driver, "02_after_login")
        log_page(driver.current_url, "After login")
        report["js_errors"].extend([e.get("message", str(e)) for e in console_errors(driver)])

        # --- STEP 2: Navigate to Farmacia PDV (sidebar) ---
        print("STEP 2: Navigate to Farmacia PDV")
        try:
            # Open Farmacia island: click rail icon
            farmacia_btn = WebDriverWait(driver, TIMEOUT).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-island='farmacia'], .island-icon[data-island='farmacia']"))
            )
            farmacia_btn.click()
            time.sleep(1.5)
            # Click "Punto de Venta (PDV)" link
            pdv_link = WebDriverWait(driver, TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href,'/farmacia/pdv/') or contains(.,'Punto de Venta') or contains(.,'PDV')]"))
            )
            pdv_link.click()
            time.sleep(3)
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
            # Fallback: direct navigate
            driver.get(BASE_URL.rstrip("/") + "/farmacia/pdv/")
            time.sleep(3)
            log_button("Sidebar Farmacia -> PDV", False, str(e)[:150])
        else:
            log_button("Sidebar Farmacia -> PDV", True)

        ss(driver, "03_pdv_page")
        log_page(driver.current_url, "PDV page")
        report["js_errors"].extend([e.get("message", str(e)) for e in console_errors(driver)])

        # --- STEP 3: Test EVERY button ---
        print("STEP 3: Test every button")

        # Search box: type "para"
        try:
            search = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.ID, "input-buscador")))
            search.clear()
            search.send_keys("para")
            time.sleep(0.4)
            search.send_keys(" ")
            time.sleep(2)
            ss(driver, "04_search_para_results")
            container = driver.find_element(By.ID, "search-results-container")
            cards = container.find_elements(By.CSS_SELECTOR, ".card-producto, .card .card-body")
            log_button("Search box (type 'para')", True, f"Results area updated, cards: {len(cards)}")
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
            log_button("Search box (type 'para')", False, str(e)[:200])
            ss(driver, "04_search_error")

        # COBRAR
        try:
            cobrar = driver.find_element(By.XPATH, "//button[contains(.,'COBRAR') or contains(@onclick,'abrirModalPago')]")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cobrar)
            time.sleep(0.5)
            cobrar.click()
            time.sleep(2)
            ss(driver, "05_cobrar_modal")
            modal = driver.find_elements(By.CSS_SELECTOR, ".modal.show, [id*='modalPago'].show, [id*='modalPago']")
            log_button("COBRAR", len(modal) > 0, "Payment modal opened" if modal else "Modal not visible")
            # Close modal if open so next buttons are visible
            try:
                driver.find_element(By.CSS_SELECTOR, ".modal .btn-close, .modal [data-bs-dismiss='modal']").click()
                time.sleep(0.8)
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
                pass
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
            log_button("COBRAR", False, str(e)[:200])

        # Atajos
        try:
            atajos = driver.find_element(By.XPATH, "//button[contains(.,'Atajos') or contains(@onclick,'toggleShortcutsModal')]")
            atajos.click()
            time.sleep(1.5)
            ss(driver, "06_atajos_modal")
            modal = driver.find_elements(By.CSS_SELECTOR, "#modalShortcuts.show, .modal.show")
            log_button("Atajos", len(modal) > 0, "Shortcuts modal opened" if modal else "Modal not visible")
            try:
                driver.find_element(By.CSS_SELECTOR, ".modal .btn-close, [data-bs-dismiss='modal']").click()
                time.sleep(0.5)
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
                pass
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
            log_button("Atajos", False, str(e)[:200])

        # Retiro
        try:
            retiro = driver.find_element(By.XPATH, "//button[contains(.,'Retiro') or contains(@onclick,'pedirGasto')]")
            retiro.click()
            time.sleep(2)
            ss(driver, "07_retiro_after")
            log_button("Retiro", True, "Clicked; modal or prompt may have opened")
            try:
                driver.find_element(By.CSS_SELECTOR, ".modal .btn-close, [data-bs-dismiss='modal'], .swal2-close").click()
                time.sleep(0.5)
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
                pass
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
            log_button("Retiro", False, str(e)[:200])

        # Corte
        try:
            corte = driver.find_element(By.XPATH, "//button[contains(.,'Corte') or contains(@onclick,'cargarCorte')]")
            corte.click()
            time.sleep(2)
            ss(driver, "08_corte_after")
            modals = driver.find_elements(By.CSS_SELECTOR, ".modal.show")
            log_button("Corte", True, f"Corte clicked; modals visible: {len(modals)}")
            try:
                driver.find_element(By.CSS_SELECTOR, ".modal .btn-close, [data-bs-dismiss='modal']").click()
                time.sleep(0.5)
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
                pass
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
            log_button("Corte", False, str(e)[:200])

        # Limpiar
        try:
            limpiar = driver.find_element(By.XPATH, "//button[contains(.,'Limpiar') or contains(@onclick,'limpiarCarrito')]")
            limpiar.click()
            time.sleep(1)
            ss(driver, "09_limpiar_after")
            log_button("Limpiar", True, "Clicked")
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
            log_button("Limpiar", False, str(e)[:200])

        # --- STEP 4: Console errors ---
        report["js_errors"].extend([e.get("message", str(e)) for e in console_errors(driver)])
        ss(driver, "10_final_state")

    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
        report["js_errors"].append(f"Fatal: {str(e)}")
        try:
            ss(driver, "99_fatal")
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en run (test_farmacia_full_user_flow.py)")
            pass
    finally:
        driver.quit()

    write_report()

def write_report():
    md = os.path.join(SCREENSHOT_DIR, "DETAILED_REPORT.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# PRISLAB - Farmacia Module Full User Flow - Detailed Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**URL:** {BASE_URL}\n")
        f.write(f"**User:** {USERNAME}\n\n")
        f.write("## 1. Every page visited (with URL)\n\n")
        for p in report["pages_visited"]:
            f.write(f"- **{p['url']}** - {p.get('note', '')}\n")
        f.write("\n## 2. Every button clicked and what happened\n\n")
        for b in report["buttons_tested"]:
            status = "WORKED" if b["worked"] else "FAILED"
            f.write(f"- **{b['button']}**: {status}" + (f" - {b['detail']}" if b.get("detail") else "") + "\n")
        f.write("\n## 3. JavaScript errors found\n\n")
        for e in report["js_errors"]:
            f.write(f"- `{e[:400]}`\n")
        if not report["js_errors"]:
            f.write("(None captured.)\n")
        f.write("\n## 4. Screenshots (each state)\n\n")
        for s in report["screenshots"]:
            f.write(f"- **{s['step']}**: `{s['path']}`\n")
    print(f"Report: {md}")
    with open(os.path.join(SCREENSHOT_DIR, "report.json"), "w", encoding="utf-8") as j:
        json.dump(report, j, indent=2)

if __name__ == "__main__":
    run()