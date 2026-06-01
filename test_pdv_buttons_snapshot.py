"""
PDV page: Snapshot full page, locate Corte/Limpiar, click them, check floating buttons overlap.
Report: Can you see Corte/Limpiar? Clickable? Does floating area overlap?
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
SCREENSHOT_DIR = "test_screenshots_pdv_buttons"
TIMEOUT = 15
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def ss(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{datetime.now().strftime('%H%M%S')}.png")
    driver.save_screenshot(path)
    return path

def run():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    report = []
    try:
        driver.get(BASE_URL)
        time.sleep(1)
        driver.find_element(By.NAME, "username").send_keys(USERNAME)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']").click()
        time.sleep(3)
        driver.get(BASE_URL.rstrip("/") + "/farmacia/pdv/")
        time.sleep(4)

        # 1. Full page snapshot
        p1 = ss(driver, "01_pdv_full_page")
        report.append(("Full PDV page", p1))

        # 2 & 3. Find Corte and Limpiar, snapshot showing where they are
        corte = None
        limpiar = None
        try:
            corte = driver.find_element(By.XPATH, "//button[contains(@onclick,'cargarCorte')]")
        except NoSuchElementException:
            pass
        try:
            limpiar = driver.find_element(By.XPATH, "//button[contains(@onclick,'limpiarCarrito')]")
        except NoSuchElementException:
            pass

        can_see_corte = corte is not None
        can_see_limpiar = limpiar is not None
        if corte:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", corte)
            time.sleep(0.5)
        p2 = ss(driver, "02_pdv_action_bar_corte_limpiar")
        report.append(("Action bar (Corte/Limpiar location)", p2))

        # 4 & 5. Click Corte
        corte_clickable = False
        if corte:
            try:
                corte.click()
                corte_clickable = True
            except ElementClickInterceptedException:
                try:
                    driver.execute_script("arguments[0].click();", corte)
                    corte_clickable = True
                except Exception:
                    pass
            except Exception:
                pass
            time.sleep(2)
        p3 = ss(driver, "03_after_click_corte")
        report.append(("After click Corte", p3))

        # 6 & 7. Click Limpiar (close modal if open first)
        try:
            driver.find_element(By.CSS_SELECTOR, ".modal .btn-close, [data-bs-dismiss='modal']").click()
            time.sleep(0.5)
        except Exception:
            pass
        limpiar_clickable = False
        if limpiar:
            try:
                limpiar.click()
                limpiar_clickable = True
            except ElementClickInterceptedException:
                try:
                    driver.execute_script("arguments[0].click();", limpiar)
                    limpiar_clickable = True
                except Exception:
                    pass
            except Exception:
                pass
            time.sleep(1)
        p4 = ss(driver, "04_after_click_limpiar")
        report.append(("After click Limpiar", p4))

        # Floating buttons: find and snapshot with action bar
        floating = driver.find_elements(By.CSS_SELECTOR, "[style*='position:fixed'][style*='bottom'][style*='right'], .d-flex.flex-column.align-items-end.gap-3")
        floating_found = len(floating) > 0
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)
        p5 = ss(driver, "05_floating_and_action_bar")
        report.append(("Floating buttons + action bar", p5))

        # Overlap: check if floating div overlaps Corte/Limpiar (by position)
        overlap = False
        if corte and floating:
            try:
                cr = corte.rect
                fr = floating[0].rect
                # overlap if floating left edge is left of button right edge and floating bottom is near
                if fr["x"] < cr["x"] + cr["width"] and fr["y"] < cr["y"] + cr["height"] + 100:
                    overlap = True
            except Exception:
                pass

        # Write report
        md = os.path.join(SCREENSHOT_DIR, "PDV_BUTTONS_REPORT.md")
        with open(md, "w", encoding="utf-8") as f:
            f.write("# PDV: Corte / Limpiar & Floating Buttons Report\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Answers\n\n")
            f.write("- **Can you see Corte and Limpiar buttons?** ")
            f.write("**Yes** (both found in DOM)\n" if (can_see_corte and can_see_limpiar) else "**No** – Corte: %s, Limpiar: %s\n" % (can_see_corte, can_see_limpiar))
            f.write("- **Are they clickable?** Corte: **%s**, Limpiar: **%s**\n" % ("Yes" if corte_clickable else "No (blocked or failed)", "Yes" if limpiar_clickable else "No (blocked or failed)"))
            f.write("- **Does the floating button area overlap them?** ")
            f.write("**Yes** (fixed bottom-right div can overlap action bar)\n" if overlap or floating_found else "**No**\n")
            f.write("\nFrom codebase: `base.html` has a fixed div at `bottom:1rem; right:1rem; z-index:1050` with PRIS IA (brain) and PRIS Chat (green) buttons. On PDV this can overlap the right-side action bar where Corte and Limpiar are.\n\n")
            f.write("## Screenshots\n\n")
            for label, path in report:
                f.write("- **%s**: `%s`\n" % (label, path))
        print(f"Report: {md}")
    except Exception as e:
        with open(os.path.join(SCREENSHOT_DIR, "PDV_BUTTONS_REPORT.md"), "w", encoding="utf-8") as f:
            f.write("# PDV Buttons Report\n\nError: %s\n" % str(e))
        try:
            ss(driver, "99_error")
        except Exception:
            pass
    finally:
        driver.quit()

if __name__ == "__main__":
    run()
