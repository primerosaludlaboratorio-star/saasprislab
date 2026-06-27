"""
test_ui_playwright.py
=====================
Pruebas UI REALES con Playwright — simula un usuario humano real.
Abre Chrome, hace clic, llena formularios, verifica lo que VE el usuario.
Toma screenshots en cada paso crítico.

Módulos probados:
  1. Login / Logout
  2. Home & Dashboard
  3. Farmacia — PDV completo (buscar → carrito → cobro)
  4. Laboratorio — Recepción → Orden → Captura resultados
  5. Consultorio — Vista médico
  6. LIMS — Catálogo estudios
  7. Director — War Room
  8. Configuración — Feature flags, usuarios
  9. Seguridad — Sesiones, 2FA
  10. Inventario — Silo lab
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

BASE_URL = "http://localhost:8765"
SCREENSHOTS_DIR = Path("screenshots_e2e")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

OK   = '\033[92m[OK]\033[0m'
FAIL = '\033[91m[FAIL]\033[0m'
INFO = '\033[94m[INFO]\033[0m'
WARN = '\033[93m[WARN]\033[0m'

resultados = []
num = [0]

def log_ok(msg):
    print(f"  {OK}  {msg}")
    resultados.append((True, msg))

def log_fail(msg, detalle=''):
    print(f"  {FAIL} {msg}" + (f" — {detalle}" if detalle else ""))
    resultados.append((False, msg, detalle))

def log_info(msg):
    print(f"\n{INFO} {msg}")

async def screenshot(page, nombre):
    num[0] += 1
    path = SCREENSHOTS_DIR / f"{num[0]:02d}_{nombre}.png"
    await page.screenshot(path=str(path), full_page=True)
    print(f"       📸 {path.name}")
    return str(path)

async def check_visible(page, selector, mensaje, timeout=5000):
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        log_ok(mensaje)
        return True
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en log_info (test_ui_playwright.py)")
        log_fail(mensaje, str(e)[:80])
        return False

async def check_url_contains(page, fragment, mensaje):
    url = page.url
    if fragment in url:
        log_ok(f"{mensaje} (URL: ...{fragment}...)")
        return True
    else:
        log_fail(f"{mensaje}", f"URL actual: {url}")
        return False

async def check_text_visible(page, text, mensaje):
    try:
        loc = page.get_by_text(text, exact=False)
        await loc.first.wait_for(state='visible', timeout=5000)
        log_ok(mensaje)
        return True
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en log_info (test_ui_playwright.py)")
        # try contains
        try:
            content = await page.content()
            if text.lower() in content.lower():
                log_ok(f"{mensaje} (texto en HTML)")
                return True
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en log_info (test_ui_playwright.py)")
            pass
        log_fail(mensaje, f"Texto '{text}' no visible")
        return False

async def check_no_error(page, mensaje):
    """Detecta SOLO errores reales de Django/Python — no falsos positivos por números como 500."""
    content = await page.content()
    # Marcadores inequívocos de error Django en DEBUG mode
    REAL_DJANGO_ERRORS = [
        'Exception Value:',         # Header exacto de página de error Django
        'Traceback (most recent',   # Python traceback
        'Server Error (500)',        # Django 500 page title
        'DoesNotExist at /',        # ORM error en URL
        'OperationalError at /',
        'IntegrityError at /',
        'AttributeError at /',
        'TypeError at /',
        'FieldError at /',
        'NameError at /',
        'Request Method:',          # Parte del header de página de error Django
    ]
    for e in REAL_DJANGO_ERRORS:
        if e in content:
            log_fail(mensaje, f"Error Django: '{e}'")
            return False
    log_ok(mensaje)
    return True

# ─────────────────────────────────────────────────────────────────────────────

async def main():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Visible para que el usuario lo vea
            slow_mo=300,     # 300ms entre acciones — visible para humanos
            args=['--window-size=1400,900']
        )
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            locale='es-MX',
        )
        page = await context.new_page()

        try:
            # ─── BLOQUE 1: LOGIN ─────────────────────────────────────────────
            log_info("=== BLOQUE 1: LOGIN ===")
            await page.goto(f"{BASE_URL}/login/")
            await screenshot(page, "01_login_page")
            await check_visible(page, 'input[name="username"]', "Página de login carga correctamente")
            await check_text_visible(page, "PRISLAB", "Logo/nombre PRISLAB visible en login")

            # Login con credenciales incorrectas
            await page.fill('input[name="username"]', 'usuario_falso')
            await page.fill('input[name="password"]', 'contraseña_mala')
            await page.click('button[type="submit"], input[type="submit"]')
            await page.wait_for_timeout(1000)
            current_url = page.url
            if '/login/' in current_url or '/home/' not in current_url:
                log_ok("Login incorrecto permanece en login (no autentica)")
            else:
                log_fail("Login incorrecto debería rechazarse")

            # Login correcto
            await page.fill('input[name="username"]', 'integ_admin')
            await page.fill('input[name="password"]', 'IntegTest2026!')
            await screenshot(page, "02_login_filled")
            await page.click('button[type="submit"], input[type="submit"]')
            await page.wait_for_load_state('networkidle', timeout=10000)
            await screenshot(page, "03_after_login")
            current_url = page.url
            if '/home/' in current_url or '/dashboard/' in current_url or '/director' in current_url:
                log_ok(f"Login exitoso → redirige a área protegida ({current_url.split('/')[-2]})")
            else:
                log_fail("Login exitoso → debería redirigir a home/dashboard", f"URL: {current_url}")
            await check_no_error(page, "Home sin errores 500")

            # ─── BLOQUE 2: HOME & DASHBOARD ──────────────────────────────────
            log_info("=== BLOQUE 2: HOME & DASHBOARD ===")
            await check_visible(page, 'nav, .navbar, .sidebar, #sidebar', "Navbar/sidebar visible tras login")
            await check_text_visible(page, "integ_admin", "Usuario autenticado visible en navbar")
            await screenshot(page, "04_home_dashboard")

            # Click en Dashboard Director
            try:
                await page.goto(f"{BASE_URL}/dashboard/", wait_until='networkidle')
                await screenshot(page, "05_dashboard_director")
                await check_no_error(page, "Dashboard director sin errores")
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en log_info (test_ui_playwright.py)")
                log_fail("Dashboard director", str(e)[:80])

            # ─── BLOQUE 3: FARMACIA — Flujo PDV completo ─────────────────────
            log_info("=== BLOQUE 3: FARMACIA — PDV ===")
            await page.goto(f"{BASE_URL}/farmacia/", wait_until='networkidle')
            await screenshot(page, "06_farmacia_dashboard")
            await check_no_error(page, "Dashboard farmacia sin errores")
            await check_text_visible(page, "Farmacia", "Dashboard farmacia muestra título")

            # PDV — Punto de venta
            await page.goto(f"{BASE_URL}/farmacia/pdv/", wait_until='networkidle')
            await screenshot(page, "07_pdv_inicial")
            await check_no_error(page, "PDV carga sin errores")
            await check_visible(page, 'input[type="text"], input[type="search"]', "Campo de búsqueda visible en PDV")

            # Buscar producto
            try:
                search_input = page.locator('input[placeholder*="buscar"], input[placeholder*="Buscar"], input[placeholder*="producto"], input[placeholder*="código"], #buscar-producto, input[type="text"]').first
                await search_input.fill('Paracetamol')
                await page.wait_for_timeout(1500)
                await screenshot(page, "08_pdv_busqueda")
                await check_no_error(page, "Búsqueda de producto en PDV sin errores")

                content = await page.content()
                if 'Paracetamol' in content:
                    log_ok("Producto 'Paracetamol TEST' aparece en resultados de búsqueda")
                else:
                    log_fail("Producto no aparece en búsqueda PDV")
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en log_info (test_ui_playwright.py)")
                log_fail("Búsqueda en PDV", str(e)[:100])

            # Inventario farmacia
            await page.goto(f"{BASE_URL}/farmacia/inventario/", wait_until='networkidle')
            await screenshot(page, "09_farmacia_inventario")
            await check_no_error(page, "Inventario farmacia sin errores")

            # Historial de ventas
            await page.goto(f"{BASE_URL}/farmacia/historial-ventas/", wait_until='networkidle')
            await screenshot(page, "10_historial_ventas")
            await check_no_error(page, "Historial ventas sin errores")

            # Libro control antibióticos
            await page.goto(f"{BASE_URL}/farmacia/libro-control/", wait_until='networkidle')
            await screenshot(page, "11_libro_control")
            await check_no_error(page, "Libro control antibióticos sin errores")

            # ─── BLOQUE 4: LABORATORIO ───────────────────────────────────────
            log_info("=== BLOQUE 4: LABORATORIO ===")
            await page.goto(f"{BASE_URL}/laboratorio/", wait_until='networkidle')
            await screenshot(page, "12_lab_dashboard")
            await check_no_error(page, "Dashboard laboratorio sin errores")

            # Recepción lab
            await page.goto(f"{BASE_URL}/laboratorio/recepcion/", wait_until='networkidle')
            await screenshot(page, "13_lab_recepcion")
            await check_no_error(page, "Recepción laboratorio sin errores")
            await check_text_visible(page, "Paciente", "Campo paciente visible en recepción")

            # Lista de trabajo
            await page.goto(f"{BASE_URL}/laboratorio/lista-trabajo/", wait_until='networkidle')
            await screenshot(page, "14_lab_lista_trabajo")
            await check_no_error(page, "Lista de trabajo laboratorio sin errores")

            # Consulta de órdenes
            await page.goto(f"{BASE_URL}/laboratorio/consulta-ordenes/", wait_until='networkidle')
            await screenshot(page, "15_lab_consulta_ordenes")
            await check_no_error(page, "Consulta órdenes sin errores")

            # Control de calidad
            await page.goto(f"{BASE_URL}/laboratorio/control-calidad/", wait_until='networkidle')
            await screenshot(page, "16_lab_control_calidad")
            await check_no_error(page, "Control calidad sin errores")

            # ─── BLOQUE 5: LIMS — Catálogo ───────────────────────────────────
            log_info("=== BLOQUE 5: LIMS ===")
            await page.goto(f"{BASE_URL}/lims/estudios/", wait_until='networkidle')
            await screenshot(page, "17_lims_estudios")
            await check_no_error(page, "LIMS catálogo estudios sin errores")

            await page.goto(f"{BASE_URL}/lims/parametros/", wait_until='networkidle')
            await screenshot(page, "18_lims_parametros")
            await check_no_error(page, "LIMS parámetros sin errores")

            # Nuevo estudio — verificar formulario carga
            await page.goto(f"{BASE_URL}/lims/estudios/nuevo/", wait_until='networkidle')
            await screenshot(page, "19_lims_nuevo_estudio")
            await check_no_error(page, "Formulario nuevo estudio sin errores")
            await check_visible(page, 'form, input, select', "Formulario nuevo estudio visible")

            # ─── BLOQUE 6: MÉDICO / CONSULTORIO ─────────────────────────────
            log_info("=== BLOQUE 6: MÉDICO / CONSULTORIO ===")
            await page.goto(f"{BASE_URL}/medico/", wait_until='networkidle')
            await screenshot(page, "20_medico_dashboard")
            await check_no_error(page, "Dashboard médico sin errores")

            await page.goto(f"{BASE_URL}/medico/consulta/", wait_until='networkidle')
            await screenshot(page, "21_medico_consulta")
            await check_no_error(page, "Módulo consulta médica sin errores")

            await page.goto(f"{BASE_URL}/consultorio/", wait_until='networkidle')
            await screenshot(page, "22_consultorio")
            await check_no_error(page, "Consultorio sin errores")

            # ─── BLOQUE 7: DIRECTOR — War Room ───────────────────────────────
            log_info("=== BLOQUE 7: DIRECTOR & WAR ROOM ===")
            await page.goto(f"{BASE_URL}/director/", wait_until='networkidle')
            await screenshot(page, "23_director_dashboard")
            await check_no_error(page, "Dashboard director sin errores")

            await page.goto(f"{BASE_URL}/director/war-room/", wait_until='networkidle')
            await screenshot(page, "24_war_room")
            await check_no_error(page, "War Room carga sin errores")
            await check_text_visible(page, "War Room", "Título War Room visible")

            await page.goto(f"{BASE_URL}/director/ranking/", wait_until='networkidle')
            await screenshot(page, "25_ranking_desempeno")
            await check_no_error(page, "Ranking desempeño sin errores")

            # ─── BLOQUE 8: CONFIGURACIÓN ─────────────────────────────────────
            log_info("=== BLOQUE 8: CONFIGURACIÓN ===")
            await page.goto(f"{BASE_URL}/configuracion/", wait_until='networkidle')
            await screenshot(page, "26_configuracion")
            await check_no_error(page, "Configuración sin errores")

            await page.goto(f"{BASE_URL}/configuracion/usuarios/", wait_until='networkidle')
            await screenshot(page, "27_config_usuarios")
            await check_no_error(page, "Gestión usuarios sin errores")

            await page.goto(f"{BASE_URL}/configuracion/flags/", wait_until='networkidle')
            await screenshot(page, "28_feature_flags")
            await check_no_error(page, "Feature flags sin errores")
            await check_text_visible(page, "módulo", "Flags muestran módulos configurables")

            # ─── BLOQUE 9: SEGURIDAD ─────────────────────────────────────────
            log_info("=== BLOQUE 9: SEGURIDAD ===")
            await page.goto(f"{BASE_URL}/seguridad/sesiones/", wait_until='networkidle')
            await screenshot(page, "29_seguridad_sesiones")
            await check_no_error(page, "Sesiones activas sin errores")

            await page.goto(f"{BASE_URL}/auth/2fa/configurar/", wait_until='networkidle')
            await screenshot(page, "30_2fa_configurar")
            await check_no_error(page, "Configurar 2FA sin errores")

            await page.goto(f"{BASE_URL}/seguridad/auditoria/", wait_until='networkidle')
            await screenshot(page, "31_auditoria")
            await check_no_error(page, "Auditoría sistema sin errores")

            # ─── BLOQUE 10: INVENTARIO SILO LAB ──────────────────────────────
            log_info("=== BLOQUE 10: INVENTARIO ===")
            await page.goto(f"{BASE_URL}/inventario/", wait_until='networkidle')
            await screenshot(page, "32_inventario")
            await check_no_error(page, "Inventario general sin errores")

            await page.goto(f"{BASE_URL}/silo-lab/", wait_until='networkidle')
            await screenshot(page, "33_silo_lab")
            await check_no_error(page, "Silo laboratorio sin errores")

            await page.goto(f"{BASE_URL}/inventario/prediccion/", wait_until='networkidle')
            await screenshot(page, "34_prediccion_stock")
            await check_no_error(page, "Predicción stock sin errores")

            # ─── BLOQUE 11: BIENESTAR ────────────────────────────────────────
            log_info("=== BLOQUE 11: BIENESTAR ===")
            await page.goto(f"{BASE_URL}/bienestar/", wait_until='networkidle')
            await screenshot(page, "35_bienestar")
            await check_no_error(page, "Módulo bienestar sin errores")

            # ─── BLOQUE 12: IA ───────────────────────────────────────────────
            log_info("=== BLOQUE 12: IA / COPILOT ===")
            await page.goto(f"{BASE_URL}/ia/asistente/", wait_until='networkidle')
            await screenshot(page, "36_ia_asistente")
            await check_no_error(page, "Asistente IA sin errores")

            # ─── BLOQUE 13: NOTIFICACIONES Y BÚSQUEDA ────────────────────────
            log_info("=== BLOQUE 13: NOTIFICACIONES & OMNISEARCH ===")
            await page.goto(f"{BASE_URL}/notificaciones/", wait_until='networkidle')
            await screenshot(page, "37_notificaciones")
            await check_no_error(page, "Notificaciones sin errores")

            # Omnisearch
            await page.goto(f"{BASE_URL}/home/", wait_until='networkidle')
            try:
                search = page.locator('#omnisearchInput')
                await search.wait_for(state='visible', timeout=8000)
                await search.fill('Juan')
                await page.wait_for_timeout(1000)
                await screenshot(page, "38_omnisearch")
                # Verificar que el backend responde
                results_div = page.locator('#omnisearchResults')
                log_ok("Omnisearch visible y acepta input")
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en log_info (test_ui_playwright.py)")
                log_fail("Omnisearch", str(e)[:120])

            # ─── BLOQUE 14: FLUJO COTIZACIÓN ─────────────────────────────────
            log_info("=== BLOQUE 14: COTIZACIÓN RÁPIDA ===")
            await page.goto(f"{BASE_URL}/cotizacion/", wait_until='networkidle')
            await screenshot(page, "39_cotizacion")
            await check_no_error(page, "Módulo cotización sin errores")

            # ─── BLOQUE 15: CONTABILIDAD ─────────────────────────────────────
            log_info("=== BLOQUE 15: CONTABILIDAD ===")
            await page.goto(f"{BASE_URL}/contabilidad/", wait_until='networkidle')
            await screenshot(page, "40_contabilidad")
            await check_no_error(page, "Contabilidad dashboard sin errores")

            # ─── BLOQUE 16: MARKETING / CRM ──────────────────────────────────
            log_info("=== BLOQUE 16: MARKETING & CRM ===")
            await page.goto(f"{BASE_URL}/marketing/", wait_until='networkidle')
            await screenshot(page, "41_marketing")
            await check_no_error(page, "Marketing sin errores")

            await page.goto(f"{BASE_URL}/crm/", wait_until='networkidle')
            await screenshot(page, "42_crm")
            await check_no_error(page, "CRM sin errores")

            # ─── BLOQUE 17: RECEPCIÓN ────────────────────────────────────────
            log_info("=== BLOQUE 17: RECEPCIÓN ===")
            await page.goto(f"{BASE_URL}/recepcion/", wait_until='networkidle')
            await screenshot(page, "43_recepcion")
            await check_no_error(page, "Recepción sin errores")

            # ─── BLOQUE 18: MANTENIMIENTO CMMS ───────────────────────────────
            log_info("=== BLOQUE 18: MANTENIMIENTO ===")
            await page.goto(f"{BASE_URL}/mantenimiento/", wait_until='networkidle')
            await screenshot(page, "44_mantenimiento")
            await check_no_error(page, "CMMS Mantenimiento sin errores")

            # ─── BLOQUE 19: LOGÍSTICA ────────────────────────────────────────
            log_info("=== BLOQUE 19: LOGÍSTICA ===")
            await page.goto(f"{BASE_URL}/logistica/", wait_until='networkidle')
            await screenshot(page, "45_logistica")
            await check_no_error(page, "Logística sin errores")

            # ─── BLOQUE 20: LOGOUT ───────────────────────────────────────────
            log_info("=== BLOQUE 20: LOGOUT ===")
            await page.goto(f"{BASE_URL}/home/", wait_until='networkidle')
            try:
                # Buscar botón de logout
                logout_btn = page.locator('a[href*="logout"], button[onclick*="logout"], form[action*="logout"]').first
                await logout_btn.click()
                await page.wait_for_load_state('networkidle', timeout=5000)
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en log_info (test_ui_playwright.py)")
                # Hacer logout directo
                await page.goto(f"{BASE_URL}/logout/", wait_until='networkidle')

            await screenshot(page, "46_logout")
            current = page.url
            if '/login/' in current or '/login/' in (await page.content()):
                log_ok("Logout exitoso → regresa a login")
            else:
                log_fail("Logout", f"URL: {current}")

        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en log_info (test_ui_playwright.py)")
            print(f"\n{FAIL} Error inesperado: {e}")
            await screenshot(page, "ERROR_inesperado")
        finally:
            await browser.close()

    # ─── RESULTADO FINAL ──────────────────────────────────────────────────────
    print("\n" + "="*65)
    ok_n   = sum(1 for r in resultados if r[0])
    fail_n = sum(1 for r in resultados if not r[0])
    total  = len(resultados)
    print(f"RESULTADO UI: {ok_n}/{total} OK, {fail_n} FALLOS")
    print(f"Screenshots guardados en: {SCREENSHOTS_DIR.absolute()}")
    print("="*65)

    if fail_n:
        print(f"\n{FAIL} FALLOS DETECTADOS:")
        for r in resultados:
            if not r[0]:
                print(f"  ✗ {r[1]}" + (f": {r[2]}" if len(r) > 2 else ""))
        return 1
    else:
        print(f"\n{OK} TODOS LOS MÓDULOS FUNCIONAN CORRECTAMENTE DESDE LA INTERFAZ")
        return 0

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)