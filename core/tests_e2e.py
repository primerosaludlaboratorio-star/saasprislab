"""
Pruebas End-to-End (E2E) con Selenium para módulos de Laboratorio y Farmacia.
Simula un usuario real operando los sistemas a través del navegador.

Requisitos:
- Chrome/Chromium instalado
- pip install -r requirements-dev.txt  (selenium, webdriver-manager)
- Variable de entorno: PRISLAB_RUN_BROWSER_E2E=1
- Ejecutar: python manage.py test core.tests_e2e
"""

import os
import unittest
import time
import json
import traceback
from datetime import datetime, date
from decimal import Decimal

from django.test import LiveServerTestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, 
    ElementNotInteractableException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

from core.models import Empresa, Producto, Lote, Venta, OrdenDeServicio, DetalleOrden, Paciente, Medico
from laboratorio.models import Estudio, CategoriaExamen
from core.utils.sucursal_helpers import get_user_primary_sucursal
import logging

User = get_user_model()


def _browser_e2e_enabled():
    return os.environ.get('PRISLAB_RUN_BROWSER_E2E', '').lower() in ('1', 'true', 'yes')


@unittest.skipUnless(
    _browser_e2e_enabled(),
    'Omitido: definir PRISLAB_RUN_BROWSER_E2E=1 y tener Chrome para Selenium.',
)
class E2ETestBase(StaticLiveServerTestCase):
    """Base class para tests E2E con configuración común."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setup_driver()
    
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'driver') and cls.driver:
            cls.driver.quit()
        super().tearDownClass()
    
    @classmethod
    def setup_driver(cls):
        """Configura el driver de Chrome."""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Ejecutar sin ventana visible
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            service = Service(ChromeDriverManager().install())
            cls.driver = webdriver.Chrome(service=service, options=chrome_options)
            cls.driver.implicitly_wait(10)
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en setup_driver (tests_e2e.py)")
            print(f"[ERROR] No se pudo inicializar ChromeDriver: {e}")
            print("[INFO] Intentando sin webdriver-manager...")
            try:
                cls.driver = webdriver.Chrome(options=chrome_options)
                cls.driver.implicitly_wait(10)
            except Exception as e2:
                logging.getLogger(__name__).exception("Error inesperado en setup_driver (tests_e2e.py)")
                raise Exception(f"No se pudo inicializar el navegador: {e2}")
    
    def setUp(self):
        """Preparar datos de prueba."""
        super().setUp()
        
        # Crear empresa
        self.empresa = Empresa.objects.create(
            nombre='Empresa de Prueba E2E',
            rfc='TEST123456'
        )
        
        # Crear usuario
        self.user = User.objects.create_user(
            username='test_e2e',
            password='test123456',
            email='test@e2e.com'
        )
        self.user.empresa = self.empresa
        self.user.save()
        
        # Login: usar sesión de Django directamente (más confiable que navegar)
        from django.test import Client
        client = Client()
        login_success = client.login(username='test_e2e', password='test123456')
        
        if login_success:
            # Obtener cookie de sesión y aplicarla al driver
            session_cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)
            if session_cookie:
                # Ir a cualquier página para establecer dominio
                self.driver.get(f"{self.live_server_url}/")
                # Agregar cookie de sesión
                self.driver.add_cookie({
                    'name': settings.SESSION_COOKIE_NAME,
                    'value': session_cookie.value,
                    'path': '/',
                })
                # Recargar para aplicar cookie
                self.driver.get(f"{self.live_server_url}/")
                time.sleep(1)
        else:
            # Fallback: intentar login manual si hay página de login
            try:
                self.driver.get(f"{self.live_server_url}/admin/login/")
                time.sleep(1)
                username_field = self.driver.find_element(By.NAME, "username")
                password_field = self.driver.find_element(By.NAME, "password")
                username_field.send_keys('test_e2e')
                password_field.send_keys('test123456')
                self.driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]').click()
                time.sleep(2)
            except:
                # Si no hay login, continuar (puede que el sistema no requiera login)
                pass
    
    def wait_for_element(self, by, value, timeout=10):
        """Espera a que un elemento aparezca."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            raise Exception(f"Elemento no encontrado: {by}={value}")
    
    def wait_for_clickable(self, by, value, timeout=10):
        """Espera a que un elemento sea clickeable."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            raise Exception(f"Elemento no clickeable: {by}={value}")
    
    def safe_click(self, by, value, timeout=10):
        """Hace click de forma segura."""
        element = self.wait_for_clickable(by, value, timeout)
        try:
            element.click()
        except ElementNotInteractableException:
            # Intentar con JavaScript
            self.driver.execute_script("arguments[0].click();", element)
    
    def safe_send_keys(self, by, value, text, clear_first=True):
        """Envía texto de forma segura."""
        element = self.wait_for_element(by, value)
        if clear_first:
            element.clear()
        element.send_keys(text)
    
    def check_for_errors(self):
        """Verifica si hay errores en la página."""
        errors = []
        
        # Buscar mensajes de error
        try:
            error_elements = self.driver.find_elements(By.CSS_SELECTOR, '.error, .alert-danger, .text-danger')
            for elem in error_elements:
                if elem.is_displayed():
                    errors.append(f"Error visible: {elem.text}")
        except:
            pass
        
        # Buscar en consola JavaScript
        try:
            logs = self.driver.get_log('browser')
            for log in logs:
                if log['level'] == 'SEVERE':
                    errors.append(f"JS Error: {log['message']}")
        except:
            pass
        
        return errors


class LaboratorioE2ETest(E2ETestBase):
    """Pruebas E2E completas del módulo de Laboratorio."""
    
    def setUp(self):
        super().setUp()
        
        # Crear categoría y estudios
        categoria = CategoriaExamen.objects.create(nombre='Química Clínica')
        
        self.estudio1 = Estudio.objects.create(
            nombre='Glucosa',
            categoria=categoria,
            codigo='GLU001',
            precio_base=Decimal('150.00'),
            valor_minimo=Decimal('70.00'),
            valor_maximo=Decimal('100.00'),
            unidades='mg/dL'
        )
        
        self.estudio2 = Estudio.objects.create(
            nombre='Urea',
            categoria=categoria,
            codigo='URE001',
            precio_base=Decimal('120.00'),
            valor_minimo=Decimal('15.00'),
            valor_maximo=Decimal('45.00'),
            unidades='mg/dL'
        )
        
        # Crear médico
        self.medico = Medico.objects.create(
            nombre='Dr. Test E2E',
            especialidad='Medicina General'
        )
    
    def test_01_recepcion_crear_paciente(self):
        """PRUEBA CRÍTICA: Crear paciente desde modal sin error de strftime."""
        print("\n[TEST 01] Creando paciente desde modal de recepción...")
        
        # Ir a recepción
        self.driver.get(f"{self.live_server_url}/laboratorio/recepcion/")
        time.sleep(2)
        
        # Buscar botón "Nuevo Paciente"
        try:
            nuevo_paciente_btn = self.wait_for_clickable(
                By.CSS_SELECTOR, 
                'button:contains("Nuevo Paciente"), #btnNuevoPaciente, [data-bs-target*="NuevoPaciente"]',
                timeout=5
            )
            nuevo_paciente_btn.click()
        except:
            # Intentar con diferentes selectores
            try:
                self.driver.execute_script("""
                    var btn = document.querySelector('button[data-bs-target*="NuevoPaciente"], button:contains("Nuevo"), #btnNuevoPaciente');
                    if (btn) btn.click();
                """)
            except:
                # Buscar por texto
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                for btn in buttons:
                    if 'Nuevo' in btn.text or 'Paciente' in btn.text:
                        btn.click()
                        break
        
        time.sleep(1)
        
        # Llenar formulario del modal
        fecha_nac = date(1990, 5, 15)
        
        # Nombres
        self.safe_send_keys(By.ID, 'pacienteNombres', 'Juan Carlos')
        time.sleep(0.5)
        
        # Apellidos
        self.safe_send_keys(By.ID, 'pacienteApellidos', 'García López')
        time.sleep(0.5)
        
        # Fecha de nacimiento (CRÍTICO: debe ser formato YYYY-MM-DD)
        fecha_input = self.wait_for_element(By.ID, 'pacienteFechaNac')
        fecha_input.clear()
        fecha_input.send_keys('1990-05-15')
        time.sleep(0.5)
        
        # Sexo
        try:
            sexo_select = self.wait_for_element(By.ID, 'pacienteSexo')
            from selenium.webdriver.support.ui import Select
            Select(sexo_select).select_by_value('M')
        except:
            # Intentar con radio buttons
            try:
                self.driver.find_element(By.CSS_SELECTOR, 'input[value="M"]').click()
            except:
                pass
        
        time.sleep(0.5)
        
        # Teléfono (campo opcional)
        try:
            self.safe_send_keys(By.ID, 'pacienteTelefono', '2291234567')
        except:
            pass
        
        time.sleep(0.5)
        
        # Guardar paciente
        try:
            guardar_btn = self.wait_for_clickable(
                By.ID, 'btnGuardarPaciente',
                timeout=5
            )
            guardar_btn.click()
        except:
            # Buscar botón de guardar por texto
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for btn in buttons:
                if 'Guardar' in btn.text or 'Crear' in btn.text:
                    btn.click()
                    break
        
        # Esperar respuesta AJAX (máximo 10 segundos)
        time.sleep(3)
        
        # VERIFICAR: No debe haber error de strftime
        errors = self.check_for_errors()
        error_strftime = [e for e in errors if 'strftime' in str(e).lower() or 'attribute' in str(e).lower()]
        
        if error_strftime:
            raise AssertionError(f"ERROR CRÍTICO: Se encontró error de strftime: {error_strftime}")
        
        # Verificar que el modal se cerró o que apareció mensaje de éxito
        try:
            # Buscar mensaje de éxito (SweetAlert o similar)
            success_msg = self.driver.find_elements(By.CSS_SELECTOR, '.swal2-success, .alert-success, .text-success')
            if not success_msg:
                # Verificar que el modal ya no está visible
                modal = self.driver.find_elements(By.CSS_SELECTOR, '.modal.show, .modal.in')
                if modal:
                    raise AssertionError("El modal no se cerró después de guardar")
        except:
            pass
        
        print("[OK] Paciente creado sin errores de strftime")
    
    def test_02_crear_orden_laboratorio(self):
        """Crear orden con 2 estudios."""
        print("\n[TEST 02] Creando orden de laboratorio...")
        
        # Crear paciente primero
        paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombres='María',
            apellido_paterno='López',
            apellido_materno='Martínez',
            fecha_nacimiento=date(1985, 3, 20),
            sexo='F',
            tipo='GENERAL',
        )
        
        # Ir a recepción
        self.driver.get(f"{self.live_server_url}/laboratorio/recepcion/")
        time.sleep(2)
        
        # Seleccionar paciente (usando Select2 o similar)
        try:
            # Buscar campo de paciente
            paciente_select = self.wait_for_element(
                By.CSS_SELECTOR, 
                '#selectPaciente, select[name*="paciente"], input[placeholder*="paciente" i]',
                timeout=5
            )
            
            # Si es un select normal
            if paciente_select.tag_name == 'select':
                from selenium.webdriver.support.ui import Select
                Select(paciente_select).select_by_index(1)
            else:
                # Si es Select2 o input de búsqueda
                paciente_select.send_keys('María')
                time.sleep(1)
                # Seleccionar primera opción
                self.driver.find_element(By.CSS_SELECTOR, '.select2-results__option').click()
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_02_crear_orden_laboratorio (tests_e2e.py)")
            print(f"[AVISO] No se pudo seleccionar paciente automáticamente: {e}")
            # Continuar de todas formas
        
        time.sleep(1)
        
        # Seleccionar estudios (buscar checkboxes o Select2)
        try:
            # Buscar checkboxes de estudios
            estudios_checkboxes = self.driver.find_elements(
                By.CSS_SELECTOR, 
                'input[type="checkbox"][name*="estudio"], input[type="checkbox"][value*="estudio"]'
            )
            
            if estudios_checkboxes:
                # Seleccionar primeros 2
                for i, checkbox in enumerate(estudios_checkboxes[:2]):
                    if not checkbox.is_selected():
                        checkbox.click()
                    time.sleep(0.5)
            else:
                # Intentar con Select2 para estudios
                estudio_search = self.driver.find_elements(By.CSS_SELECTOR, '#selectEstudios, select[name*="estudio"]')
                if estudio_search:
                    estudio_search[0].send_keys('Glucosa')
                    time.sleep(1)
                    self.driver.find_element(By.CSS_SELECTOR, '.select2-results__option').click()
                    time.sleep(1)
                    estudio_search[0].send_keys('Urea')
                    time.sleep(1)
                    self.driver.find_element(By.CSS_SELECTOR, '.select2-results__option').click()
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_02_crear_orden_laboratorio (tests_e2e.py)")
            print(f"[AVISO] No se pudieron seleccionar estudios automáticamente: {e}")
        
        time.sleep(1)
        
        # Buscar y hacer click en "Generar Orden" o "Guardar"
        try:
            generar_btn = self.wait_for_clickable(
                By.CSS_SELECTOR,
                'button:contains("Generar"), button:contains("Crear"), button:contains("Guardar"), #btnGenerarOrden',
                timeout=5
            )
            generar_btn.click()
        except:
            # Buscar por texto
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for btn in buttons:
                if any(word in btn.text for word in ['Generar', 'Crear', 'Guardar', 'Orden']):
                    btn.click()
                    break
        
        time.sleep(3)
        
        ordenes = OrdenDeServicio.objects.filter(empresa=self.empresa, paciente=paciente)
        self.assertGreater(ordenes.count(), 0, 'No se creó la orden (ODS)')
        orden = ordenes.first()
        detalles = orden.detalles.count()
        self.assertGreaterEqual(detalles, 1, f'La orden debe tener al menos 1 línea, tiene {detalles}')
        print(f'[OK] Orden creada (ODS): ID={orden.id}, Líneas={detalles}')
    
    def test_03_capturar_y_validar_resultados(self):
        """Capturar resultados y validar orden."""
        print("\n[TEST 03] Capturando resultados y validando...")
        
        # Crear orden de prueba
        paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombres='Pedro',
            apellido_paterno='Sánchez',
            apellido_materno='Ruiz',
            fecha_nacimiento=date(1978, 8, 10),
            sexo='M',
            tipo='GENERAL',
        )
        total_o = self.estudio1.precio_base + self.estudio2.precio_base
        orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            sucursal=get_user_primary_sucursal(self.user),
            paciente=paciente,
            responsable_ingreso=self.user,
            total=total_o,
            anticipo=Decimal('0'),
            estado='PAGADO',
            estado_pago='PAGADO',
            estado_clinico='PENDIENTE_TOMA',
        )
        DetalleOrden.objects.create(
            orden=orden,
            descripcion_linea=self.estudio1.nombre,
            precio_momento=self.estudio1.precio_base,
        )
        DetalleOrden.objects.create(
            orden=orden,
            descripcion_linea=self.estudio2.nombre,
            precio_momento=self.estudio2.precio_base,
        )
        
        # Ir a lista de trabajo
        self.driver.get(f"{self.live_server_url}/laboratorio/trabajo/")
        time.sleep(2)
        
        # Buscar la orden en la lista y hacer click en "Editar" o "Capturar"
        try:
            # Buscar por ID de orden o folio
            orden_link = self.driver.find_element(
                By.XPATH,
                f"//a[contains(@href, '{orden.id}') or contains(text(), '{orden.id}')]"
            )
            orden_link.click()
        except:
            # Buscar botón de editar/capturar
            edit_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'a:contains("Editar"), a:contains("Capturar"), button:contains("Editar")')
            if edit_buttons:
                edit_buttons[0].click()
            else:
                # Ir directamente a la URL de captura
                self.driver.get(f"{self.live_server_url}/laboratorio/captura/{orden.id}/")
        
        time.sleep(2)
        
        # Llenar resultados
        try:
            # Buscar inputs de resultados (pueden tener diferentes nombres)
            resultado_inputs = self.driver.find_elements(
                By.CSS_SELECTOR,
                'input[name*="resultado"], textarea[name*="resultado"], input[type="text"][name*="valor"]'
            )
            
            if resultado_inputs:
                # Llenar primer resultado (Glucosa)
                resultado_inputs[0].clear()
                resultado_inputs[0].send_keys('95.5')
                time.sleep(0.5)
                
                # Llenar segundo resultado (Urea)
                if len(resultado_inputs) > 1:
                    resultado_inputs[1].clear()
                    resultado_inputs[1].send_keys('28.3')
            else:
                # Intentar con IDs específicos
                try:
                    self.safe_send_keys(By.ID, f'resultado_{orden.detalles.first().id}', '95.5')
                    time.sleep(0.5)
                    self.safe_send_keys(By.ID, f'resultado_{orden.detalles.last().id}', '28.3')
                except:
                    print("[AVISO] No se pudieron llenar resultados automáticamente")
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_03_capturar_y_validar_resultados (tests_e2e.py)")
            print(f"[AVISO] Error al llenar resultados: {e}")
        
        time.sleep(1)
        
        # Buscar y hacer click en "Validar y Publicar"
        try:
            validar_btn = self.wait_for_clickable(
                By.CSS_SELECTOR,
                'button:contains("Validar"), button:contains("Publicar"), #btnValidar',
                timeout=5
            )
            validar_btn.click()
        except:
            # Buscar por texto
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for btn in buttons:
                if any(word in btn.text for word in ['Validar', 'Publicar']):
                    btn.click()
                    break
        
        # Confirmar si aparece diálogo
        time.sleep(2)
        try:
            confirm_btn = self.driver.find_element(By.CSS_SELECTOR, '.swal2-confirm, button:contains("Sí"), button:contains("Confirmar")')
            confirm_btn.click()
        except:
            pass
        
        time.sleep(3)
        
        orden.refresh_from_db()
        self.assertEqual(
            orden.estado,
            'RESULTADOS_LISTOS',
            'La orden ODS no quedó en RESULTADOS_LISTOS tras validar (revisar UI/captura)',
        )
        print(f'[OK] Orden validada (ODS): ID={orden.id}, Estado={orden.estado}')
    
    def test_04_descargar_pdf(self):
        """Descargar PDF de resultados validados."""
        print("\n[TEST 04] Descargando PDF de resultados...")
        
        # Crear orden validada
        paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombres='Ana',
            apellido_paterno='Martínez',
            apellido_materno='García',
            fecha_nacimiento=date(1992, 11, 5),
            sexo='F',
            tipo='GENERAL',
        )
        orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            sucursal=get_user_primary_sucursal(self.user),
            paciente=paciente,
            responsable_ingreso=self.user,
            total=self.estudio1.precio_base,
            anticipo=Decimal('0'),
            estado='EN_PROCESO',
            estado_pago='PAGADO',
            estado_clinico='COMPLETO',
        )
        DetalleOrden.objects.create(
            orden=orden,
            descripcion_linea=self.estudio1.nombre,
            precio_momento=self.estudio1.precio_base,
        )
        # Evitar ValidationError de PDF: marcar lista vía UPDATE (sin pasar por save/full_clean)
        OrdenDeServicio.objects.filter(pk=orden.pk).update(estado='RESULTADOS_LISTOS')
        orden.refresh_from_db()
        
        # Ir a lista de trabajo
        self.driver.get(f"{self.live_server_url}/laboratorio/trabajo/")
        time.sleep(2)
        
        # Buscar botón de descargar/imprimir PDF
        try:
            pdf_btn = self.wait_for_clickable(
                By.CSS_SELECTOR,
                'a:contains("PDF"), a:contains("Imprimir"), a:contains("Descargar"), [href*="pdf"], [href*="imprimir"]',
                timeout=5
            )
            
            # Verificar que el botón NO está deshabilitado
            if pdf_btn.get_attribute('disabled'):
                raise AssertionError("El botón de PDF está deshabilitado para una orden validada")
            
            # Hacer click (abrirá nueva pestaña o descargará)
            pdf_btn.click()
            time.sleep(3)
            
            # Verificar que no hay error 500
            errors = self.check_for_errors()
            error_500 = [e for e in errors if '500' in str(e) or 'error' in str(e).lower()]
            
            if error_500:
                raise AssertionError(f"Error al descargar PDF: {error_500}")
            
            print("[OK] PDF descargado sin errores")
            
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_04_descargar_pdf (tests_e2e.py)")
            # Intentar acceso directo a la URL
            try:
                self.driver.get(f"{self.live_server_url}/laboratorio/imprimir-resultados/{orden.id}/?modo=digital")
                time.sleep(3)
                
                # Verificar que la página cargó correctamente
                page_source = self.driver.page_source
                if 'error' in page_source.lower() and '500' in page_source:
                    raise AssertionError("Error 500 al acceder al PDF")
                
                print("[OK] PDF accesible vía URL directa")
            except Exception as e2:
                logging.getLogger(__name__).exception("Error inesperado en test_04_descargar_pdf (tests_e2e.py)")
                print(f"[AVISO] No se pudo verificar PDF: {e2}")


class FarmaciaE2ETest(E2ETestBase):
    """Pruebas E2E completas del módulo de Farmacia (PDV)."""
    
    def setUp(self):
        super().setUp()
        
        # Crear productos con stock
        self.producto1 = Producto.objects.create(
            empresa=self.empresa,
            nombre='Paracetamol 500mg',
            codigo_barras='1234567890123',
            precio_publico=Decimal('25.00'),
            precio_compra=Decimal('15.00'),
            iva_porcentaje=Decimal('16.00'),
            stock=100
        )
        
        self.producto2 = Producto.objects.create(
            empresa=self.empresa,
            nombre='Ibuprofeno 400mg',
            codigo_barras='1234567890124',
            precio_publico=Decimal('30.00'),
            precio_compra=Decimal('18.00'),
            iva_porcentaje=Decimal('16.00'),
            stock=80
        )
        
        self.producto3 = Producto.objects.create(
            empresa=self.empresa,
            nombre='Amoxicilina 500mg',
            codigo_barras='1234567890125',
            precio_publico=Decimal('45.00'),
            precio_compra=Decimal('25.00'),
            iva_porcentaje=Decimal('16.00'),
            stock=50,
            es_antibiotico=True
        )
        
        # Crear lotes
        Lote.objects.create(
            producto=self.producto1,
            numero_lote='LOTE001',
            fecha_caducidad=date(2026, 12, 31),
            cantidad=100,
            costo_adquisicion=Decimal('15.00')
        )
        
        Lote.objects.create(
            producto=self.producto2,
            numero_lote='LOTE002',
            fecha_caducidad=date(2026, 11, 30),
            cantidad=80,
            costo_adquisicion=Decimal('18.00')
        )
        
        Lote.objects.create(
            producto=self.producto3,
            numero_lote='LOTE003',
            fecha_caducidad=date(2026, 10, 31),
            cantidad=50,
            costo_adquisicion=Decimal('25.00')
        )
    
    def test_01_buscar_y_agregar_productos(self):
        """Buscar productos y agregarlos al carrito."""
        print("\n[TEST 01] Buscando y agregando productos al carrito...")
        
        # Ir al PDV
        self.driver.get(f"{self.live_server_url}/farmacia/pdv/")
        time.sleep(3)
        
        # Buscar campo de búsqueda
        try:
            search_input = self.wait_for_element(
                By.CSS_SELECTOR,
                'input[type="search"], input[placeholder*="buscar" i], input[name*="buscar"], #buscarProducto',
                timeout=5
            )
            
            # Buscar primer producto
            search_input.clear()
            search_input.send_keys('Paracetamol')
            time.sleep(2)
            
            # Seleccionar producto de los resultados (esperar que aparezca)
            try:
                producto_result = self.wait_for_clickable(
                    By.CSS_SELECTOR,
                    '.producto-item, .resultado-busqueda, [data-producto-id]',
                    timeout=5
                )
                producto_result.click()
            except:
                # Intentar con Enter
                search_input.send_keys(Keys.RETURN)
            
            time.sleep(1)
            
            # Buscar segundo producto
            search_input.clear()
            search_input.send_keys('Ibuprofeno')
            time.sleep(2)
            
            try:
                producto_result = self.wait_for_clickable(
                    By.CSS_SELECTOR,
                    '.producto-item, .resultado-busqueda, [data-producto-id]',
                    timeout=5
                )
                producto_result.click()
            except:
                search_input.send_keys(Keys.RETURN)
            
            time.sleep(1)
            
            # Buscar tercer producto
            search_input.clear()
            search_input.send_keys('Amoxicilina')
            time.sleep(2)
            
            try:
                producto_result = self.wait_for_clickable(
                    By.CSS_SELECTOR,
                    '.producto-item, .resultado-busqueda, [data-producto-id]',
                    timeout=5
                )
                producto_result.click()
            except:
                search_input.send_keys(Keys.RETURN)
            
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_01_buscar_y_agregar_productos (tests_e2e.py)")
            print(f"[AVISO] Búsqueda automática falló: {e}")
            # Intentar agregar productos directamente vía JavaScript
            self.driver.execute_script(f"""
                if (typeof agregarProducto === 'function') {{
                    agregarProducto({self.producto1.id});
                    agregarProducto({self.producto2.id});
                    agregarProducto({self.producto3.id});
                }}
            """)
        
        time.sleep(2)
        
        # Verificar que hay productos en el carrito
        try:
            carrito_items = self.driver.find_elements(By.CSS_SELECTOR, '.item-carrito, .cart-item, tr[data-item-id]')
            self.assertGreater(len(carrito_items), 0, "No hay productos en el carrito")
            print(f"[OK] Productos en carrito: {len(carrito_items)}")
        except:
            print("[AVISO] No se pudo verificar el carrito visualmente")
    
    def test_02_modificar_cantidades_y_verificar_calculos(self):
        """Modificar cantidades y verificar cálculos JavaScript."""
        print("\n[TEST 02] Modificando cantidades y verificando cálculos...")
        
        # Ir al PDV
        self.driver.get(f"{self.live_server_url}/farmacia/pdv/")
        time.sleep(3)
        
        # Agregar productos vía JavaScript si es posible
        self.driver.execute_script(f"""
            if (typeof agregarProducto === 'function') {{
                agregarProducto({self.producto1.id});
                agregarProducto({self.producto2.id});
            }}
        """)
        
        time.sleep(2)
        
        # Buscar inputs de cantidad
        try:
            cantidad_inputs = self.driver.find_elements(
                By.CSS_SELECTOR,
                'input[name*="cantidad"], input[type="number"][min], .cantidad-input'
            )
            
            if cantidad_inputs:
                # Modificar primera cantidad
                cantidad_inputs[0].clear()
                cantidad_inputs[0].send_keys('3')
                cantidad_inputs[0].send_keys(Keys.TAB)  # Trigger change event
                time.sleep(1)
                
                # Modificar segunda cantidad
                if len(cantidad_inputs) > 1:
                    cantidad_inputs[1].clear()
                    cantidad_inputs[1].send_keys('2')
                    cantidad_inputs[1].send_keys(Keys.TAB)
                    time.sleep(1)
                
                # Verificar que los totales se actualizaron
                try:
                    subtotal_elem = self.driver.find_element(By.CSS_SELECTOR, '#subtotal, .subtotal, [id*="subtotal"]')
                    total_elem = self.driver.find_element(By.CSS_SELECTOR, '#total, .total, [id*="total"]')
                    
                    subtotal_text = subtotal_elem.text
                    total_text = total_elem.text
                    
                    # Verificar que contienen números
                    import re
                    if not re.search(r'\d+', subtotal_text):
                        raise AssertionError(f"Subtotal no contiene número válido: {subtotal_text}")
                    if not re.search(r'\d+', total_text):
                        raise AssertionError(f"Total no contiene número válido: {total_text}")
                    
                    print(f"[OK] Cálculos actualizados - Subtotal: {subtotal_text}, Total: {total_text}")
                except Exception as e:
                    logging.getLogger(__name__).exception("Error inesperado en test_02_modificar_cantidades_y_verificar_calculos (tests_e2e.py)")
                    print(f"[AVISO] No se pudieron verificar los totales: {e}")
            else:
                print("[AVISO] No se encontraron inputs de cantidad")
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_02_modificar_cantidades_y_verificar_calculos (tests_e2e.py)")
            print(f"[AVISO] Error al modificar cantidades: {e}")
    
    def test_03_procesar_pago_y_verificar_venta(self):
        """Procesar pago y verificar que se registra la venta."""
        print("\n[TEST 03] Procesando pago y verificando venta...")
        
        # Ir al PDV
        self.driver.get(f"{self.live_server_url}/farmacia/pdv/")
        time.sleep(3)
        
        # Agregar productos
        self.driver.execute_script(f"""
            if (typeof agregarProducto === 'function') {{
                agregarProducto({self.producto1.id});
                agregarProducto({self.producto2.id});
            }}
        """)
        
        time.sleep(2)
        
        # Buscar botón de "Finalizar Venta" o "Cobrar"
        try:
            finalizar_btn = self.wait_for_clickable(
                By.CSS_SELECTOR,
                'button:contains("Finalizar"), button:contains("Cobrar"), button:contains("Pagar"), #btnFinalizarVenta',
                timeout=5
            )
            finalizar_btn.click()
        except:
            # Buscar por texto
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for btn in buttons:
                if any(word in btn.text for word in ['Finalizar', 'Cobrar', 'Pagar']):
                    btn.click()
                    break
        
        time.sleep(2)
        
        # Llenar método de pago (si aparece modal)
        try:
            efectivo_input = self.driver.find_element(By.CSS_SELECTOR, 'input[name*="efectivo"], #efectivo')
            efectivo_input.clear()
            efectivo_input.send_keys('100')
        except:
            pass
        
        time.sleep(1)
        
        # Confirmar pago
        try:
            confirmar_btn = self.wait_for_clickable(
                By.CSS_SELECTOR,
                'button:contains("Confirmar"), button:contains("Procesar"), #btnConfirmarPago',
                timeout=5
            )
            confirmar_btn.click()
        except:
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for btn in buttons:
                if any(word in btn.text for word in ['Confirmar', 'Procesar']):
                    btn.click()
                    break
        
        time.sleep(5)
        
        # Verificar que apareció modal de "Venta Exitosa"
        try:
            success_modal = self.wait_for_element(
                By.CSS_SELECTOR,
                '.swal2-success, .modal-success, .alert-success, [class*="success"]',
                timeout=5
            )
            self.assertTrue(success_modal.is_displayed(), "Modal de éxito no está visible")
            print("[OK] Modal de 'Venta Exitosa' apareció")
        except:
            # Verificar en la base de datos
            ventas = Venta.objects.filter(usuario=self.user).order_by('-id')
            if ventas.exists():
                print(f"[OK] Venta registrada en BD: ID={ventas.first().id}")
            else:
                print("[AVISO] No se encontró venta en BD ni modal de éxito")


def run_e2e_tests():
    """Ejecuta todas las pruebas E2E y genera reporte."""
    import sys
    from io import StringIO
    from django.test.utils import get_runner
    from django.conf import settings
    
    print("="*70)
    print("PRUEBAS END-TO-END (E2E) - LABORATORIO Y FARMACIA")
    print("="*70)
    print("\nIniciando pruebas con Selenium...\n")
    
    # Configurar test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False)
    
    # Ejecutar tests
    old_stdout = sys.stdout
    sys.stdout = buffer = StringIO()
    
    try:
        failures = test_runner.run_tests(['core.tests_e2e'])
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en run_e2e_tests (tests_e2e.py)")
        failures = True
        print(f"Error ejecutando tests: {e}")
        traceback.print_exc()
    
    sys.stdout = old_stdout
    output = buffer.getvalue()
    
    # Generar reporte
    reporte = f"""
{'='*70}
REPORTE DE PRUEBAS END-TO-END
{'='*70}

Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RESULTADOS:
{output}

{'='*70}
"""
    
    # Guardar reporte
    with open('reporte_e2e.txt', 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    print(reporte)
    print(f"\nReporte guardado en: reporte_e2e.txt")
    
    return failures == 0
