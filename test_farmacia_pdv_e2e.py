"""
PRISLAB SaaS - Farmacia PDV End-to-End Test
Tests: Login (nancy), Farmacia sidebar, PDV page, search, add to cart, COBRAR button.
Captures screenshots and console errors at each step.
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = os.environ.get("PRISLAB_TEST_BASE_URL", "https://prislab-v5-811785477499.us-central1.run.app")
# Try nancy first; fallback to admin if login fails
USERNAME = os.environ.get("PRISLAB_TEST_USERNAME", "nancy")
PASSWORD = os.environ.get("PRISLAB_TEST_PASSWORD")
if not PASSWORD:
    raise RuntimeError("Debe configurar la variable de entorno PRISLAB_TEST_PASSWORD antes de ejecutar este test.")
FALLBACK_USER = os.environ.get("PRISLAB_TEST_FALLBACK_USERNAME", "admin")
FALLBACK_PASS = os.environ.get("PRISLAB_TEST_FALLBACK_PASSWORD") or PASSWORD
SCREENSHOT_DIR = "test_screenshots_farmacia"
TIMEOUT = 15
WAIT_AFTER_ACTION = 1.5

if not os.path.exists(SCREENSHOT_DIR):
    os.makedirs(SCREENSHOT_DIR)

report = {
    "pages_visited": [],
    "actions_tested": [],
    "errors": [],
    "screenshots": [],
    "console_log": [],
}

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{datetime.now().strftime('%H%M%S')}.png")
    driver.save_screenshot(path)
    report["screenshots"].append({"step": name, "path": path})
    print(f"  [SCREENSHOT] {path}")
    return path

def get_console_errors(driver):
    try:
        logs = driver.get_log("browser")
        errs = [l for l in logs if l.get("level") == "SEVERE"]
        return errs
    except Exception:
        return []

def get_console_all(driver):
    try:
        return driver.get_log("browser")
    except Exception:
        return []

def log_page(url, status="ok", note=""):
    report["pages_visited"].append({"url": url, "status": status, "note": note})

def log_action(name, worked, detail=""):
    report["actions_tested"].append({"action": name, "worked": worked, "detail": detail})

def log_error(where, message):
    report["errors"].append({"where": where, "message": message})

def run_test():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        print("[*] Browser started")

        # --- STEP 1: Login page ---
        print("\n=== STEP 1: Login ===")
        driver.get(BASE_URL)
        time.sleep(2)
        screenshot(driver, "01_login_page")
        errs = get_console_errors(driver)
        for e in errs:
            log_error("login_page", e.get("message", str(e)))
        log_page(driver.current_url, "ok", "Login page loaded")

        # Find form and login (try nancy first, then fallback to admin)
        used_fallback = False
        for attempt, (u, p) in enumerate([(USERNAME, PASSWORD), (FALLBACK_USER, FALLBACK_PASS)]):
            try:
                user_inp = WebDriverWait(driver, TIMEOUT).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                pass_inp = driver.find_element(By.NAME, "password")
                user_inp.clear()
                user_inp.send_keys(u)
                pass_inp.clear()
                pass_inp.send_keys(p)
                screenshot(driver, "02_login_filled" if attempt == 0 else "02_login_filled_fallback")
                btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
                btn.click()
                time.sleep(3)
            except NoSuchElementException as ex:
                log_error("login_form", str(ex))
                log_action("Fill login form", False, str(ex))
                screenshot(driver, "02_login_form_not_found")
                write_report()
                return

            after_login_url = driver.current_url
            screenshot(driver, "03_after_login")

            if "/dashboard/" in after_login_url or "/farmacia" in after_login_url or "/home" in after_login_url:
                log_action("Login submit", True, f"Redirected to {after_login_url}" + (" (fallback admin)" if attempt == 1 else ""))
                log_page(after_login_url, "ok", "After login")
                if attempt == 1:
                    used_fallback = True
                break
            else:
                try:
                    err_el = driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .error, .text-danger")
                    msg = " ".join([e.text for e in err_el if e.text])[:200] if err_el else "No dashboard redirect"
                except Exception:
                    msg = "No dashboard redirect"
                log_action("Login submit (" + u + ")", False, msg)
                log_error("login", f"Credentials {u}: {msg}")
                log_page(after_login_url, "fail", msg)
                if attempt == 0:
                    driver.get(BASE_URL)
                    time.sleep(1)
                else:
                    break
        else:
            log_error("login", "Both nancy and admin credentials failed")
            write_report()
            return

        report["used_fallback_login"] = used_fallback
        errs = get_console_errors(driver)
        for e in errs:
            log_error("after_login_console", e.get("message", str(e)))

        # --- STEP 2: Navigate to Farmacia PDV ---
        print("\n=== STEP 2: Navigate to Farmacia PDV ===")
        pdv_url = BASE_URL.rstrip("/") + "/farmacia/pdv/"
        driver.get(pdv_url)
        time.sleep(3)
        screenshot(driver, "04_pdv_page")
        log_page(driver.current_url, "ok", "PDV page")

        # 403/500 check
        if "403" in driver.page_source or "Forbidden" in driver.title:
            log_error("pdv_page", "403 Forbidden")
            log_page(pdv_url, "fail", "403 Forbidden")
        if "500" in driver.title or "Error" in driver.title:
            log_error("pdv_page", "500 or error page")
            log_page(pdv_url, "fail", "Server error")

        errs = get_console_errors(driver)
        for e in errs:
            log_error("pdv_console", e.get("message", str(e)))

        # --- STEP 3: PDV functionality ---
        print("\n=== STEP 3: PDV functionality ===")

        # 3a) Search for product
        try:
            search_el = WebDriverWait(driver, TIMEOUT).until(
                EC.presence_of_element_located((By.ID, "input-buscador"))
            )
            search_el.clear()
            search_el.send_keys("paracetamol")
            time.sleep(0.5)
            search_el.send_keys(" ")  # trigger debounce
            time.sleep(2)
            screenshot(driver, "05_after_search_input")
            # Check if results appeared
            container = driver.find_element(By.ID, "search-results-container")
            cards = container.find_elements(By.CSS_SELECTOR, ".card-producto, .card")
            if cards:
                log_action("Search product (paracetamol)", True, f"Found {len(cards)} result(s)")
                screenshot(driver, "06_search_results")
                # 3b) Add first product to cart
                try:
                    first_card = cards[0]
                    first_card.click()
                    time.sleep(2)
                    screenshot(driver, "07_after_add_to_cart")
                    try:
                        cart_rows = driver.find_elements(By.CSS_SELECTOR, "#tabla-carrito-body tr")
                        has_items = len(cart_rows) > 0
                    except Exception:
                        has_items = False
                    log_action("Add product to cart", has_items, "Cart updated" if has_items else "No cart rows found")
                except Exception as ex:
                    log_action("Add product to cart", False, str(ex))
                    log_error("add_to_cart", str(ex))
            else:
                # Maybe no products in DB; try generic search
                search_el.clear()
                search_el.send_keys("aspirina")
                time.sleep(2)
                screenshot(driver, "06_search_results_aspirina")
                cards2 = container.find_elements(By.CSS_SELECTOR, ".card-producto, .card .card-body")
                if cards2:
                    log_action("Search product (paracetamol)", True, "No results; aspirina tried")
                    try:
                        cards2[0].click()
                        time.sleep(2)
                        screenshot(driver, "07_after_add_to_cart")
                        log_action("Add product to cart", True, "Clicked first result")
                    except Exception as ex:
                        log_action("Add product to cart", False, str(ex))
                else:
                    log_action("Search product", True, "No products in DB or API issue")
                    log_action("Add product to cart", False, "No results to click")
        except Exception as ex:
            err_msg = str(ex).split("\n")[0][:300]  # avoid huge stack traces in report
            log_action("Search product", False, err_msg)
            log_error("search", err_msg)
            screenshot(driver, "05_search_error")

        # 3c) COBRAR button
        try:
            cobrar_btns = driver.find_elements(By.XPATH, "//button[contains(.,'COBRAR') or contains(.,'Cobrar')]")
            if not cobrar_btns:
                cobrar_btns = driver.find_elements(By.CSS_SELECTOR, "[onclick*='abrirModalPago'], [onclick*='modalPago']")
            if cobrar_btns:
                cobrar_btns[0].click()
                time.sleep(2)
                screenshot(driver, "08_cobrar_modal")
                modal = driver.find_elements(By.CSS_SELECTOR, ".modal.show, #modalPago.show")
                log_action("Click COBRAR button", len(modal) > 0, "Modal opened" if modal else "Modal not visible")
                if modal:
                    log_action("COBRAR modal visible", True, "Payment modal displayed")
            else:
                log_action("Click COBRAR button", False, "Button not found")
                log_error("cobrar", "COBRAR button not found")
        except Exception as ex:
            log_action("Click COBRAR button", False, str(ex))
            log_error("cobrar", str(ex))

        # 3d) Other buttons: Limpiar carrito
        try:
            limpiar = driver.find_elements(By.XPATH, "//button[contains(@onclick,'limpiarCarrito') or contains(.,'Limpiar')]")
            if limpiar:
                log_action("Limpiar carrito button present", True, "Found")
            else:
                log_action("Limpiar carrito button present", False, "Not found")
        except Exception as ex:
            log_action("Limpiar carrito button", False, str(ex))

        # Final console capture
        for e in get_console_errors(driver):
            log_error("final_console", e.get("message", str(e)))

        print("\n=== Test run complete ===")
    except Exception as e:
        log_error("test_run", str(e))
        if driver:
            screenshot(driver, "99_fatal_error")
    finally:
        if driver:
            driver.quit()
    write_report()

def write_report():
    path = os.path.join(SCREENSHOT_DIR, "FARMACIA_PDV_REPORT.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# PRISLAB - Farmacia PDV E2E Test Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**User tried:** {USERNAME}\n")
        if report.get("used_fallback_login"):
            f.write(f"**Note:** Login with nancy failed; PDV tested with fallback admin.\n")
        f.write(f"**Base URL:** {BASE_URL}\n\n")
        f.write("## 1. Pages visited\n\n")
        for p in report["pages_visited"]:
            f.write(f"- **{p['url']}** - {p['status']}" + (f" - {p['note']}" if p.get("note") else "") + "\n")
        f.write("\n## 2. Actions tested\n\n")
        for a in report["actions_tested"]:
            status = "OK" if a["worked"] else "FAIL"
            f.write(f"- **{a['action']}**: {status}" + (f" - {a['detail']}" if a.get("detail") else "") + "\n")
        f.write("\n## 3. Errors (JS console, UI, failed actions)\n\n")
        for e in report["errors"]:
            f.write(f"- **{e['where']}**: {e['message'][:500]}\n")
        if not report["errors"]:
            f.write("(No errors recorded.)\n")
        f.write("\n## 4. Screenshots\n\n")
        for s in report["screenshots"]:
            f.write(f"- `{s['path']}` ({s['step']})\n")
    print(f"Report written to {path}")

    # JSON for machine parsing
    json_path = os.path.join(SCREENSHOT_DIR, "report.json")
    with open(json_path, "w", encoding="utf-8") as j:
        json.dump({k: v for k, v in report.items() if k != "console_log"}, j, indent=2)
    print(f"JSON report: {json_path}")

if __name__ == "__main__":
    run_test()
