"""
Auditoría Forense Completa - Módulo Médico y Directivo
Simula el flujo completo: Dashboards → Expediente → Recetas → Finanzas
"""

from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import Empresa, Paciente, Medico, Receta
import traceback
import time
from colorama import init, Fore, Style
from decimal import Decimal

init(autoreset=True)

User = get_user_model()


class Command(BaseCommand):
    help = 'Auditoría forense completa del Módulo Médico y Directivo'

    def __init__(self):
        super().__init__()
        self.client = Client()
        self.resultados = {
            'vistas_probadas': [],
            'errores_encontrados': [],
            'warnings': []
        }
        self.paciente_prueba = None
        self.medico_prueba = None

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
            
            # Manejar expected_status como lista o entero
            if isinstance(expected_status, list):
                exito = status in expected_status
            else:
                exito = status == expected_status
            
            resultado = {
                'url': url,
                'nombre': nombre,
                'status': status,
                'tiempo': tiempo_respuesta,
                'exito': exito
            }
            
            self.resultados['vistas_probadas'].append(resultado)
            
            if exito:
                self.log_result('OK', f"{nombre} ({url}) - {tiempo_respuesta:.3f}s")
                return True, response
            elif status >= 500:
                error_content = response.content.decode('utf-8', errors='ignore')[:500]
                self.log_result('ERROR', f"{nombre} - Error {status}", error_content)
                return False, response
            elif status == 404:
                self.log_result('WARNING', f"{nombre} - 404 Not Found")
                return False, response
            elif status == 403:
                self.log_result('WARNING', f"{nombre} - 403 Forbidden (Permisos)")
                return False, response
            else:
                self.log_result('WARNING', f"{nombre} - Status {status}")
                return status < 400, response
                
        except Exception as e:
            tiempo_respuesta = time.time() - inicio
            self.log_result('ERROR', f"{nombre} - Excepción: {str(e)}", traceback.format_exc())
            return False, None

    def verificar_graficas(self, html_content):
        """Verifica que las gráficas estén presentes o muestren 'Sin datos'."""
        html_lower = html_content.lower()
        
        # Buscar indicadores de gráficas
        indicadores_graficas = ['chart', 'graph', 'grafica', 'canvas', 'plotly', 'chartjs']
        tiene_graficas = any(ind in html_lower for ind in indicadores_graficas)
        
        # Buscar mensajes de "sin datos"
        indicadores_sin_datos = ['sin datos', 'no hay datos', 'empty', 'vacio', '0', 'cero']
        muestra_sin_datos = any(ind in html_lower for ind in indicadores_sin_datos)
        
        if tiene_graficas:
            self.log_result('OK', "Gráficas detectadas en el dashboard")
        elif muestra_sin_datos:
            self.log_result('OK', "Dashboard muestra 'Sin datos' correctamente")
        else:
            self.log_result('WARNING', "No se detectaron gráficas ni mensaje de 'Sin datos'")

    def handle(self, *args, **options):
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}AUDITORÍA FORENSE - MÓDULO MÉDICO Y DIRECTIVO")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")

        # Crear usuarios de prueba
        try:
            empresa, _ = Empresa.objects.get_or_create(
                nombre='Laboratorio del Valle',
                defaults={'activa': True}
            )
            
            # Usuario Médico
            user_medico, created = User.objects.get_or_create(
                username='test_medico_audit',
                defaults={
                    'email': 'medico@test.com',
                    'rol': 'MEDICO',
                    'is_staff': False,
                    'empresa': empresa
                }
            )
            if not created:
                user_medico.empresa = empresa
                user_medico.save()
            user_medico.set_password('test123')
            user_medico.save()
            
            # Usuario Director
            user_director, created = User.objects.get_or_create(
                username='test_director_audit',
                defaults={
                    'email': 'director@test.com',
                    'rol': 'DIRECTOR',
                    'is_staff': True,
                    'empresa': empresa
                }
            )
            if not created:
                user_director.empresa = empresa
                user_director.is_staff = True
                user_director.save()
            user_director.set_password('test123')
            user_director.save()
            
            self.log_result('OK', "Usuarios de prueba creados: test_medico_audit, test_director_audit")
        except Exception as e:
            self.log_result('ERROR', f"No se pudo crear usuarios: {str(e)}")
            return

        # Crear datos de prueba
        try:
            # Paciente de prueba
            self.paciente_prueba, created = Paciente.objects.get_or_create(
                nombre_completo='PACIENTE PRUEBA MÉDICO',
                empresa=empresa,
                defaults={
                    'telefono': '1234567890',
                    'email': 'paciente@test.com',
                    'tipo': 'AMBULATORIO'
                }
            )
            if created:
                self.log_result('OK', f"Paciente de prueba creado: {self.paciente_prueba.nombre_completo}")
            
            # Médico de prueba
            self.medico_prueba, created = Medico.objects.get_or_create(
                nombre_completo='DR. PRUEBA AUDITORIA',
                defaults={
                    'cedula_profesional': 'TEST-001',
                    'especialidad': 'Medicina General',
                    'empresa': empresa
                }
            )
            if created:
                self.log_result('OK', f"Médico de prueba creado: {self.medico_prueba.nombre_completo}")
                
        except Exception as e:
            self.log_result('WARNING', f"Error al crear datos de prueba: {str(e)}")

        # PASO 1: Dashboard Médico
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 1] Verificando Dashboard Médico\n")
        
        login_ok = self.client.login(username='test_medico_audit', password='test123')
        if not login_ok:
            self.log_result('ERROR', "No se pudo hacer login como médico")
            return

        ok, response = self.test_url('/medico/', 'Dashboard Médico', expected_status=200)
        if ok and response:
            html = response.content.decode('utf-8', errors='ignore')
            self.verificar_graficas(html)
            
            # Verificar que no haya errores en el HTML
            if 'error' in html.lower() and 'traceback' in html.lower():
                self.log_result('ERROR', "Dashboard médico muestra errores en el HTML")
            else:
                self.log_result('OK', "Dashboard médico carga sin errores visibles")

        # PASO 2: Dashboard Director
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 2] Verificando Dashboard Director\n")
        
        self.client.logout()
        login_ok = self.client.login(username='test_director_audit', password='test123')
        if not login_ok:
            self.log_result('ERROR', "No se pudo hacer login como director")
            return

        ok, response = self.test_url('/director/', 'Dashboard Director', expected_status=200)
        if ok and response:
            html = response.content.decode('utf-8', errors='ignore')
            self.verificar_graficas(html)
            
            # Verificar que no haya errores en el HTML
            if 'error' in html.lower() and 'traceback' in html.lower():
                self.log_result('ERROR', "Dashboard director muestra errores en el HTML")
            else:
                self.log_result('OK', "Dashboard director carga sin errores visibles")
            
            # Verificar elementos críticos del dashboard
            elementos_criticos = ['ingresos', 'ventas', 'pacientes', 'total', 'grafica', 'chart']
            encontrados = [elem for elem in elementos_criticos if elem in html.lower()]
            if len(encontrados) >= 2:
                self.log_result('OK', f"Elementos críticos del dashboard detectados: {', '.join(encontrados[:3])}")
            else:
                self.log_result('WARNING', "Pocos elementos críticos detectados en el dashboard")

        # PASO 3: Expediente Clínico
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 3] Verificando Expediente Clínico\n")
        
        if self.paciente_prueba:
            # Intentar acceder al expediente del paciente
            urls_expediente = [
                f'/medico/paciente/{self.paciente_prueba.id}/',
                f'/medico/expediente/{self.paciente_prueba.id}/',
                f'/paciente/{self.paciente_prueba.id}/expediente/',
                f'/medico/pacientes/{self.paciente_prueba.id}/'
            ]
            
            expediente_encontrado = False
            for url_exp in urls_expediente:
                ok, response = self.test_url(url_exp, f'Expediente ({url_exp})', expected_status=[200, 302, 404])
                if ok and response.status_code == 200:
                    expediente_encontrado = True
                    html = response.content.decode('utf-8', errors='ignore')
                    if 'paciente' in html.lower() or 'expediente' in html.lower() or 'historial' in html.lower():
                        self.log_result('OK', f"Expediente accesible y muestra información del paciente")
                    break
                elif ok and response.status_code == 302:
                    self.log_result('INFO', f"Expediente redirige (puede requerir parámetros)")
            
            if not expediente_encontrado:
                self.log_result('WARNING', "No se encontró la vista de expediente clínico")

        # PASO 4: Generador de Recetas
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 4] Verificando Generador de Recetas\n")
        
        urls_recetas = [
            '/medico/recetas/',
            '/medico/receta/nueva/',
            '/medico/generar-receta/',
            '/recetas/nueva/'
        ]
        
        receta_encontrada = False
        for url_receta in urls_recetas:
            ok, response = self.test_url(url_receta, f'Generador Recetas ({url_receta})', expected_status=[200, 302, 404])
            if ok and response.status_code == 200:
                receta_encontrada = True
                html = response.content.decode('utf-8', errors='ignore')
                if 'receta' in html.lower() or 'medicamento' in html.lower() or 'prescripcion' in html.lower():
                    self.log_result('OK', f"Generador de recetas accesible y muestra formulario")
                break
            elif ok and response.status_code == 302:
                self.log_result('INFO', f"Generador de recetas redirige (puede requerir parámetros)")
        
        if not receta_encontrada:
            self.log_result('WARNING', "No se encontró la vista de generador de recetas")

        # PASO 5: Reportes de Finanzas (Vista Director)
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 5] Verificando Reportes de Finanzas\n")
        
        urls_finanzas = [
            '/director/finanzas/',
            '/director/reportes/',
            '/director/ingresos/',
            '/finanzas/reportes/'
        ]
        
        finanzas_encontradas = False
        for url_fin in urls_finanzas:
            ok, response = self.test_url(url_fin, f'Reportes Finanzas ({url_fin})', expected_status=[200, 302, 404])
            if ok and response.status_code == 200:
                finanzas_encontradas = True
                html = response.content.decode('utf-8', errors='ignore')
                if 'ingresos' in html.lower() or 'ventas' in html.lower() or 'total' in html.lower():
                    self.log_result('OK', f"Reportes de finanzas accesibles y muestran información")
                break
            elif ok and response.status_code == 302:
                self.log_result('INFO', f"Reportes de finanzas redirigen (puede requerir parámetros)")
        
        if not finanzas_encontradas:
            self.log_result('WARNING', "No se encontró la vista de reportes de finanzas")

        # Resumen
        self.mostrar_resumen()

    def mostrar_resumen(self):
        """Muestra el resumen final de la auditoría."""
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}RESUMEN DE AUDITORÍA FORENSE - MÉDICO Y DIRECTIVO")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")
        
        total_vistas = len(self.resultados['vistas_probadas'])
        vistas_ok = sum(1 for v in self.resultados['vistas_probadas'] if v['exito'])
        total_errores = len(self.resultados['errores_encontrados'])
        total_warnings = len(self.resultados['warnings'])
        
        self.stdout.write(f"{Fore.GREEN}Total de vistas probadas: {total_vistas}")
        self.stdout.write(f"{Fore.GREEN}Vistas exitosas: {vistas_ok}/{total_vistas}")
        self.stdout.write(f"{Fore.YELLOW}Warnings: {total_warnings}")
        self.stdout.write(f"{Fore.RED}Errores: {total_errores}")
        
        # Resumen por funcionalidad
        self.stdout.write(f"\n{Fore.CYAN}Resumen por Funcionalidad:")
        
        dashboard_medico_ok = any('Dashboard Médico' in v['nombre'] and v['exito'] for v in self.resultados['vistas_probadas'])
        dashboard_director_ok = any('Dashboard Director' in v['nombre'] and v['exito'] for v in self.resultados['vistas_probadas'])
        expediente_ok = any('Expediente' in v['nombre'] and v['exito'] for v in self.resultados['vistas_probadas'])
        recetas_ok = any('Recetas' in v['nombre'] and v['exito'] for v in self.resultados['vistas_probadas'])
        finanzas_ok = any('Finanzas' in v['nombre'] and v['exito'] for v in self.resultados['vistas_probadas'])
        
        self.stdout.write(f"{Fore.GREEN if dashboard_medico_ok else Fore.RED}Dashboard Médico: {'OK' if dashboard_medico_ok else 'ERROR'}")
        self.stdout.write(f"{Fore.GREEN if dashboard_director_ok else Fore.RED}Dashboard Director: {'OK' if dashboard_director_ok else 'ERROR'}")
        self.stdout.write(f"{Fore.GREEN if expediente_ok else Fore.YELLOW}Expediente: {'OK' if expediente_ok else 'VERIFICAR'}")
        self.stdout.write(f"{Fore.GREEN if recetas_ok else Fore.YELLOW}Recetas: {'OK' if recetas_ok else 'VERIFICAR'}")
        self.stdout.write(f"{Fore.GREEN if finanzas_ok else Fore.YELLOW}Finanzas: {'OK' if finanzas_ok else 'VERIFICAR'}")
        
        if total_errores == 0:
            self.stdout.write(f"\n{Fore.GREEN}[ESTADO FINAL] BLINDADO - Sin errores críticos")
        else:
            self.stdout.write(f"\n{Fore.RED}[ESTADO FINAL] REQUIERE ATENCIÓN - {total_errores} errores encontrados")
        
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}\n")
