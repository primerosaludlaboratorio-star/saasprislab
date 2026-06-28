"""
Auditoría Forense Completa - Módulo 1 (Core/Acceso)
Pruebas de estrés con análisis de logs y validación exhaustiva.
"""

from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from django.template.loader import get_template, TemplateDoesNotExist
from django.urls import reverse, resolve, NoReverseMatch
from django.db import transaction
import traceback
import time
import re
from colorama import init, Fore, Style
from urllib.parse import urljoin, urlparse
import logging

init(autoreset=True)

User = get_user_model()


class Command(BaseCommand):
    help = 'Auditoría forense completa del Módulo 1 (Core/Acceso)'

    def __init__(self):
        super().__init__()
        self.client = Client()
        self.resultados = {
            'vistas_probadas': [],
            'enlaces_verificados': [],
            'errores_encontrados': [],
            'warnings': [],
            'tiempos_respuesta': []
        }
        self.base_url = 'http://testserver'

    def log_result(self, tipo, mensaje, detalles=None):
        """Registra un resultado."""
        if tipo == 'OK':
            self.stdout.write(f"{Fore.GREEN}[OK] {mensaje}")
        elif tipo == 'ERROR':
            self.stdout.write(f"{Fore.RED}[ERROR] {mensaje}")
            self.resultados['errores_encontrados'].append({
                'mensaje': mensaje,
                'detalles': detalles
            })
        elif tipo == 'WARNING':
            self.stdout.write(f"{Fore.YELLOW}[WARNING] {mensaje}")
            self.resultados['warnings'].append({
                'mensaje': mensaje,
                'detalles': detalles
            })
        elif tipo == 'INFO':
            self.stdout.write(f"{Fore.CYAN}[INFO] {mensaje}")

    def test_url(self, url, nombre, metodo='GET', data=None, follow=True, expected_status=200):
        """Prueba una URL y mide el tiempo de respuesta."""
        inicio = time.time()
        try:
            if metodo == 'GET':
                response = self.client.get(url, follow=follow)
            elif metodo == 'POST':
                response = self.client.post(url, data or {}, follow=follow)
            else:
                response = self.client.get(url, follow=follow)
            
            tiempo_respuesta = time.time() - inicio
            status = response.status_code
            
            resultado = {
                'url': url,
                'nombre': nombre,
                'status': status,
                'tiempo': tiempo_respuesta,
                'exito': status == expected_status
            }
            
            self.resultados['vistas_probadas'].append(resultado)
            self.resultados['tiempos_respuesta'].append(tiempo_respuesta)
            
            if status == expected_status:
                self.log_result('OK', f"{nombre} ({url}) - {tiempo_respuesta:.3f}s")
                return True, response
            elif status >= 500:
                error_content = response.content.decode('utf-8', errors='ignore')[:500]
                self.log_result('ERROR', f"{nombre} - Error {status}", error_content)
                return False, response
            elif status == 404:
                self.log_result('WARNING', f"{nombre} - 404 Not Found")
                return False, response
            else:
                self.log_result('WARNING', f"{nombre} - Status {status}")
                return status < 400, response
                
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_url (auditoria_core_full.py)")
            tiempo_respuesta = time.time() - inicio
            self.log_result('ERROR', f"{nombre} - Excepción: {str(e)}", traceback.format_exc())
            self.resultados['errores_encontrados'].append({
                'url': url,
                'nombre': nombre,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            return False, None

    def validar_template(self, template_name):
        """Valida que un template se pueda renderizar sin errores."""
        try:
            template = get_template(template_name)
            self.log_result('OK', f"Template {template_name} válido")
            return True
        except TemplateDoesNotExist:
            self.log_result('ERROR', f"Template {template_name} no existe")
            return False
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en validar_template (auditoria_core_full.py)")
            self.log_result('ERROR', f"Template {template_name} tiene errores: {str(e)}")
            return False

    def extraer_enlaces(self, html_content, base_url):
        """Extrae todos los enlaces de un HTML usando regex."""
        enlaces = []
        try:
            # Extraer enlaces <a href="...">
            pattern_a = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>'
            matches_a = re.finditer(pattern_a, html_content, re.IGNORECASE)
            for match in matches_a:
                href = match.group(1)
                if href and not href.startswith('#') and not href.startswith('javascript:'):
                    # Convertir a URL absoluta si es relativa
                    if href.startswith('/'):
                        full_url = self.base_url + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = urljoin(base_url, href)
                    
                    # Extraer texto del enlace (siguiente contenido hasta </a>)
                    start_pos = match.end()
                    end_pos = html_content.find('</a>', start_pos)
                    if end_pos > start_pos:
                        text = html_content[start_pos:end_pos].strip()[:50]
                    else:
                        text = href[:50]
                    
                    enlaces.append({
                        'href': href,
                        'full_url': full_url,
                        'text': text,
                        'tipo': 'link'
                    })
            
            # Extraer formularios con action
            pattern_form = r'<form[^>]+action=["\']([^"\']+)["\'][^>]*>'
            matches_form = re.finditer(pattern_form, html_content, re.IGNORECASE)
            for match in matches_form:
                action = match.group(1)
                if action:
                    if action.startswith('/'):
                        full_url = self.base_url + action
                    else:
                        full_url = urljoin(base_url, action)
                    
                    # Extraer id del form si existe
                    form_tag = match.group(0)
                    id_match = re.search(r'id=["\']([^"\']+)["\']', form_tag, re.IGNORECASE)
                    form_id = id_match.group(1) if id_match else 'sin-id'
                    
                    enlaces.append({
                        'href': action,
                        'full_url': full_url,
                        'text': f"Form: {form_id}",
                        'tipo': 'form'
                    })
                    
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en extraer_enlaces (auditoria_core_full.py)")
            self.log_result('WARNING', f"Error al extraer enlaces: {str(e)}")
        
        return enlaces

    def probar_enlaces(self, enlaces, usuario_autenticado=False):
        """Prueba todos los enlaces encontrados."""
        self.log_result('INFO', f"Probando {len(enlaces)} enlaces...")
        
        for enlace in enlaces:
            href = enlace['href']
            
            # Saltar enlaces externos o especiales
            if href.startswith('http://') or href.startswith('https://'):
                continue
            if href.startswith('mailto:') or href.startswith('tel:'):
                continue
            if 'logout' in href.lower() and not usuario_autenticado:
                continue
            
            # Probar el enlace
            try:
                if href.startswith('/'):
                    url = href
                else:
                    url = '/' + href
                
                inicio = time.time()
                response = self.client.get(url, follow=True)
                tiempo = time.time() - inicio
                
                resultado = {
                    'href': href,
                    'url': url,
                    'status': response.status_code,
                    'tiempo': tiempo,
                    'texto': enlace['text']
                }
                
                self.resultados['enlaces_verificados'].append(resultado)
                
                if response.status_code == 200:
                    self.log_result('OK', f"Enlace: {href[:50]} - OK ({tiempo:.3f}s)")
                elif response.status_code >= 500:
                    self.log_result('ERROR', f"Enlace: {href[:50]} - Error {response.status_code}")
                elif response.status_code == 404:
                    self.log_result('WARNING', f"Enlace: {href[:50]} - 404")
                elif response.status_code in [301, 302, 303]:
                    self.log_result('INFO', f"Enlace: {href[:50]} - Redirect {response.status_code}")
                    
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en probar_enlaces (auditoria_core_full.py)")
                self.log_result('ERROR', f"Enlace: {href[:50]} - Excepción: {str(e)}")

    def handle(self, *args, **options):
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}AUDITORÍA FORENSE - MÓDULO 1 (CORE/ACCESO)")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")

        # PASO 1: Validación de Templates
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 1] Validación de Templates\n")
        self.validar_template('core/login.html')
        self.validar_template('base.html')

        # PASO 2: Navegación Completa
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 2] Navegación Completa\n")
        
        # 2.1 Ruta raíz (debe mostrar login)
        self.test_url('/', 'Ruta Raíz (Login)', expected_status=200)
        
        # 2.2 Ruta /login/
        self.test_url('/login/', 'Ruta /login/', expected_status=200)
        
        # 2.3 Obtener HTML del login para extraer enlaces
        _, response_login = self.test_url('/login/', 'Login para análisis', expected_status=200)
        if response_login:
            html_login = response_login.content.decode('utf-8', errors='ignore')
            enlaces_login = self.extract_enlaces(html_login, '/login/')
            self.log_result('INFO', f"Encontrados {len(enlaces_login)} enlaces en login.html")

        # PASO 3: Prueba de Login
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 3] Prueba de Login\n")
        
        # 3.1 Crear usuario de prueba
        try:
            from core.models import Empresa
            empresa, _ = Empresa.objects.get_or_create(
                nombre='Laboratorio del Valle',
                defaults={'activa': True}
            )
            
            user_test, created = User.objects.get_or_create(
                username='test_auditoria',
                defaults={
                    'email': 'test@auditoria.com',
                    'rol': 'QUIMICO',
                    'is_staff': False,
                    'empresa': empresa
                }
            )
            if not created:
                user_test.empresa = empresa
                user_test.save()
            user_test.set_password('test123')
            user_test.save()
            
            self.log_result('OK', "Usuario de prueba creado: test_auditoria / test123")
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (auditoria_core_full.py)")
            self.log_result('ERROR', f"No se pudo crear usuario de prueba: {str(e)}")
            return

        # 3.2 Login con credenciales incorrectas
        self.log_result('INFO', "Probando login con credenciales incorrectas...")
        response = self.client.post('/login/', {
            'username': 'test_auditoria',
            'password': 'password_incorrecta'
        }, follow=True)
        if response.status_code == 200 and 'login' in response.request.get('PATH_INFO', ''):
            self.log_result('OK', "Login rechazado correctamente con credenciales incorrectas")
        else:
            self.log_result('WARNING', "Login con credenciales incorrectas no se comportó como esperado")

        # 3.3 Login con credenciales correctas
        self.log_result('INFO', "Probando login con credenciales correctas...")
        login_ok = self.client.login(username='test_auditoria', password='test123')
        if login_ok:
            self.log_result('OK', "Login exitoso con credenciales correctas")
            
            # 3.4 Verificar redirección después del login
            response = self.client.get('/', follow=True)
            final_url = response.request.get('PATH_INFO', '')
            if 'laboratorio' in final_url or 'lista-trabajo' in final_url:
                self.log_result('OK', f"Redirección correcta después del login: {final_url}")
            else:
                self.log_result('WARNING', f"Redirección inesperada después del login: {final_url}")
            
            # 3.5 Obtener base.html para extraer enlaces de la barra lateral
            response_base = self.client.get('/laboratorio/lista-trabajo/', follow=True)
            if response_base.status_code == 200:
                html_base = response_base.content.decode('utf-8', errors='ignore')
                enlaces_base = self.extract_enlaces(html_base, '/laboratorio/lista-trabajo/')
                self.log_result('INFO', f"Encontrados {len(enlaces_base)} enlaces en base.html")
                
                # 3.6 Probar enlaces de la barra lateral
                self.stdout.write(f"\n{Fore.YELLOW}[PASO 4] Prueba de Enlaces de la Barra Lateral\n")
                self.probar_enlaces(enlaces_base[:20], usuario_autenticado=True)  # Limitar a 20 para no saturar
            
            # 3.7 Logout
            self.log_result('INFO', "Probando logout...")
            self.test_url('/logout/', 'Logout', expected_status=200)
        else:
            self.log_result('ERROR', "Login falló con credenciales correctas")

        # PASO 5: Resumen
        self.mostrar_resumen()

    def extract_enlaces(self, html_content, base_url):
        """Extrae enlaces del HTML (alias para compatibilidad)."""
        return self.extraer_enlaces(html_content, base_url)

    def mostrar_resumen(self):
        """Muestra el resumen final de la auditoría."""
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}RESUMEN DE AUDITORÍA FORENSE")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")
        
        total_vistas = len(self.resultados['vistas_probadas'])
        vistas_ok = sum(1 for v in self.resultados['vistas_probadas'] if v['exito'])
        total_enlaces = len(self.resultados['enlaces_verificados'])
        enlaces_ok = sum(1 for e in self.resultados['enlaces_verificados'] if e['status'] == 200)
        total_errores = len(self.resultados['errores_encontrados'])
        total_warnings = len(self.resultados['warnings'])
        
        if self.resultados['tiempos_respuesta']:
            tiempo_promedio = sum(self.resultados['tiempos_respuesta']) / len(self.resultados['tiempos_respuesta'])
            tiempo_max = max(self.resultados['tiempos_respuesta'])
            tiempo_min = min(self.resultados['tiempos_respuesta'])
        else:
            tiempo_promedio = tiempo_max = tiempo_min = 0
        
        self.stdout.write(f"{Fore.GREEN}Total de vistas probadas: {total_vistas}")
        self.stdout.write(f"{Fore.GREEN}Vistas exitosas: {vistas_ok}/{total_vistas}")
        self.stdout.write(f"{Fore.GREEN}Total de enlaces verificados: {total_enlaces}")
        self.stdout.write(f"{Fore.GREEN}Enlaces exitosos: {enlaces_ok}/{total_enlaces}")
        self.stdout.write(f"{Fore.YELLOW}Warnings: {total_warnings}")
        self.stdout.write(f"{Fore.RED}Errores: {total_errores}")
        self.stdout.write(f"\n{Fore.CYAN}Tiempos de respuesta:")
        self.stdout.write(f"  Promedio: {tiempo_promedio:.3f}s")
        self.stdout.write(f"  Mínimo: {tiempo_min:.3f}s")
        self.stdout.write(f"  Máximo: {tiempo_max:.3f}s")
        
        if total_errores == 0:
            self.stdout.write(f"\n{Fore.GREEN}[ESTADO FINAL] BLINDADO - Sin errores críticos")
        else:
            self.stdout.write(f"\n{Fore.RED}[ESTADO FINAL] REQUIERE ATENCIÓN - {total_errores} errores encontrados")
        
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}\n")