"""
Farmacia module - step-by-step test as a real user.
Steps 1-16: PDV -> search -> COBRAR -> Corte -> Limpiar -> Historial -> Dashboard -> console check.
Report: for EVERY step - what clicked, what happened, errors.
"""

import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException

BASE_URL = "https://prislab-v5-811785477499.us-central1.run.app"
USERNAME = "admin"
PASSWORD = "PrislabV5_2026"
SCREENSHOT_DIR = "test_screenshots_farmacia_steps"
TIMEOUT = 15
WAIT = 1.5
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

steps_log = []
def log(step_num, action, what_happened, errors=""):
    steps_log.append({"step": step_num, "action": action, "result": what_happened, "errors": errors})

def ss(driver, step_name):
    path = os.path.join(SCREENSHOT_DIR, f"{step_name}_{datetime.now().strftime('%H%M%S')}.png")
    driver.save_screenshot(path)
    return path

def console_errors(driver):
    try:
        return [e.get("message", str(e)) for e in driver.get_log("browser") if e.get("level") == "SEVERE"]
    except Exception:
        return []

def run():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(5)
    try:
        # Login
        driver.get(BASE_URL)
        time.sleep(2)
        driver.find_element(By.NAME, "username").send_keys(USERNAME)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']").click()
        time.sleep(3)
        if "/dashboard/" not in driver.current_url and "/medico" not in driver.current_url:
            log(0, "Login", "FAIL - did not redirect to dashboard", str(driver.current_url))
        else:
            log(0, "Login", "OK - redirected to dashboard", "")

        # 1. Navigate to Farmacia > PDV
        driver.get(BASE_URL.rstrip("/") + "/farmacia/pdv/")
        time.sleep(4)
        log(1, "Navigate to Farmacia > Punto de Venta (PDV)", "OK" if "pdv" in driver.current_url else "FAIL", "")
        # 2. Snapshot PDV
        p2 = ss(driver, "02_pdv_page")
        log(2, "Take snapshot of PDV page", "OK - " + p2, "")

        # 3. Type "para" in search
        try:
            search = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.ID, "input-buscador")))
            search.clear()
            search.send_keys("para")
            time.sleep(0.5)
            search.send_keys(" ")
            time.sleep(2)
            log(3, 'Type "para" in search box', "OK", "")
        except Exception as e:
            log(3, 'Type "para" in search', "FAIL", str(e))
        # 4. Snapshot search results
        p4 = ss(driver, "04_search_results")
        log(4, "Take snapshot of search results", "OK - " + p4, "")

        # 5. Click COBRAR
        try:
            cobrar = driver.find_element(By.XPATH, "//button[contains(.,'COBRAR') or contains(@onclick,'abrirModalPago')]")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cobrar)
            time.sleep(0.5)
            cobrar.click()
            time.sleep(2)
            modal = driver.find_elements(By.CSS_SELECTOR, ".modal.show, [id*='modalPago'].show")
            log(5, "Click COBRAR button", "OK - modal opened" if modal else "Clicked, modal not visible", "")
        except Exception as e:
            log(5, "Click COBRAR", "FAIL", str(e))
        # 6. Snapshot payment modal
        p6 = ss(driver, "06_payment_modal")
        log(6, "Take snapshot of payment modal", "OK - " + p6, "")

        # 7. Close payment modal
        try:
            close_btn = driver.find_elements(By.CSS_SELECTOR, ".modal .btn-close, .modal [data-bs-dismiss='modal']")
            if close_btn:
                close_btn[0].click()
                time.sleep(1)
            log(7, "Close payment modal", "OK", "")
        except Exception as e:
            log(7, "Close modal", "FAIL", str(e))

        # 8. Click Corte
        try:
            corte = driver.find_elements(By.XPATH, "//button[contains(@onclick,'cargarCorte')] | //button[.//small[contains(.,'Corte')]]")
            if corte:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", corte[0])
                time.sleep(0.5)
                try:
                    corte[0].click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", corte[0])
                time.sleep(2)
                log(8, "Click Corte button", "OK", "")
            else:
                log(8, "Click Corte", "FAIL - button not found", "")
        except Exception as e:
            log(8, "Click Corte", "FAIL", str(e))
        # 9. Snapshot after Corte
        p9 = ss(driver, "09_after_corte")
        log(9, "Snapshot after Corte", "OK - " + p9, "")

        # 10. Click Limpiar
        try:
            limpiar = driver.find_elements(By.XPATH, "//button[contains(@onclick,'limpiarCarrito')] | //button[.//small[contains(.,'Limpiar')]]")
            if limpiar:
                try:
                    limpiar[0].click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", limpiar[0])
                time.sleep(1)
                log(10, "Click Limpiar button", "OK", "")
            else:
                log(10, "Click Limpiar", "FAIL - button not found", "")
        except Exception as e:
            log(10, "Click Limpiar", "FAIL", str(e))
        # 11. Snapshot
        p11 = ss(driver, "11_after_limpiar")
        log(11, "Snapshot after Limpiar", "OK - " + p11, "")

        # 12. Navigate to Historial de Ventas
        driver.get(BASE_URL.rstrip("/") + "/farmacia/historial-ventas/")
        time.sleep(3)
        ok = "historial" in driver.current_url or "ventas" in driver.current_url
        log(12, "Navigate to Farmacia > Historial de Ventas", "OK" if ok else "FAIL", "")
        # 13. Snapshot
        p13 = ss(driver, "13_historial_ventas")
        log(13, "Snapshot Historial de Ventas", "OK - " + p13, "")

        # 14. Navigate to Farmacia Dashboard
        driver.get(BASE_URL.rstrip("/") + "/farmacia/dashboard/")
        time.sleep(3)
        log(14, "Navigate to Farmacia > Dashboard", "OK" if "farmacia" in driver.current_url else "FAIL", "")
        # 15. Snapshot
        p15 = ss(driver, "15_farmacia_dashboard")
        log(15, "Snapshot Farmacia Dashboard", "OK - " + p15, "")

        # 16. Console errors
        errs = console_errors(driver)
        log(16, "Check browser console for JS errors", "OK" if not errs else "Found %d error(s)" % len(errs), "; ".join(e[:200] for e in errs[:10]))

    except Exception as e:
        steps_log.append({"step": 99, "action": "Fatal", "result": "FAIL", "errors": str(e)[:500]})
        try:
            ss(driver, "99_fatal")
        except Exception:
            pass
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    # Write report
    md = os.path.join(SCREENSHOT_DIR, "FARMACIA_STEP_BY_STEP_REPORT.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# Farmacia Module - Step-by-Step Test Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## For EVERY step: what you clicked, what happened, errors\n\n")
        for s in steps_log:
            f.write(f"### Step {s['step']}: {s['action']}\n")
            f.write(f"- **What happened:** {s['result']}\n")
            if s.get("errors"):
                f.write(f"- **Errors (on screen or console):** {s['errors'][:400]}\n")
            f.write("\n")
        f.write("\n## Screenshots\n\n")
        import glob
        for name in ["02_pdv_page", "04_search_results", "06_payment_modal", "09_after_corte", "11_after_limpiar", "13_historial_ventas", "15_farmacia_dashboard"]:
            g = list(glob.glob(os.path.join(SCREENSHOT_DIR, name + "_*.png")))
            if g:
                g.sort(key=os.path.getmtime)
                f.write(f"- **{name}**: `{os.path.basename(g[-1])}`\n")
    print("Report: " + md)

if __name__ == "__main__":
    run()
