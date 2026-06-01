"""
Auditoría Secuencial y Exhaustiva - PRISLAB v5
Verifica módulo por módulo, deteniéndose en errores.
"""

from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import transaction
import traceback
from colorama import init, Fore, Style

init(autoreset=True)

User = get_user_model()


class Command(BaseCommand):
    help = 'Auditoría secuencial módulo por módulo'

    def __init__(self):
        super().__init__()
        self.client = Client()
        self.errores_encontrados = []
        self.modulo_actual = None

    def log_error(self, url, nombre, error, traceback_str=""):
        """Registra un error encontrado."""
        self.errores_encontrados.append({
            'modulo': self.modulo_actual,
            'url': url,
            'nombre': nombre,
            'error': str(error),
            'traceback': traceback_str
        })
        self.stdout.write(f"{Fore.RED}[ERROR] {nombre}: {error}")

    def test_url(self, url, nombre, metodo='GET', data=None, expected_status=200, follow=True):
        """Prueba una URL y retorna el resultado."""
        try:
            if metodo == 'GET':
                response = self.client.get(url, follow=follow)
            elif metodo == 'POST':
                response = self.client.post(url, data or {}, follow=follow)
            else:
                response = self.client.get(url, follow=follow)
            
            status = response.status_code
            
            if status == expected_status:
                self.stdout.write(f"{Fore.GREEN}[OK] {nombre}")
                return True
            elif status >= 500:
                error_msg = f"Error {status}"
                try:
                    content = response.content.decode('utf-8')[:500]
                    if 'Traceback' in content:
                        error_msg = f"Error {status} - Ver traceback en logs"
                except:
                    pass
                self.log_error(url, nombre, error_msg)
                return False
            elif status == 404:
                self.stdout.write(f"{Fore.YELLOW}[404] {nombre} - Ruta no encontrada")
                return False
            elif status in [301, 302, 303, 307, 308]:
                self.stdout.write(f"{Fore.CYAN}[REDIRECT] {nombre} -> {status}")
                return True
            else:
                self.stdout.write(f"{Fore.YELLOW}[{status}] {nombre}")
                return status < 400
                
        except Exception as e:
            self.log_error(url, nombre, str(e), traceback.format_exc())
            return False

    def crear_usuario_test(self, username, rol, is_staff=False):
        """Crea un usuario de prueba para simular roles."""
        try:
            from core.models import Empresa
            empresa, _ = Empresa.objects.get_or_create(
                nombre='Laboratorio del Valle',
                defaults={'activa': True}
            )
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@test.com',
                    'rol': rol,
                    'is_staff': is_staff,
                    'empresa': empresa
                }
            )
            if not created:
                user.rol = rol
                user.is_staff = is_staff
                user.empresa = empresa
                user.save()
            
            user.set_password('test123')
            user.save()
            return user
        except Exception as e:
            self.stdout.write(f"{Fore.RED}[ERROR] No se pudo crear usuario {username}: {e}")
            return None

    def handle(self, *args, **options):
        fase = options.get('fase', '1')
        
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}AUDITORÍA SECUENCIAL - FASE {fase}")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")

        if fase == '1':
            self.fase_1_acceso_core()
        elif fase == '2':
            self.fase_2_laboratorio()
        elif fase == '3':
            self.fase_3_farmacia()
        elif fase == '4':
            self.fase_4_medico()
        else:
            self.stdout.write(f"{Fore.RED}[ERROR] Fase {fase} no válida. Use 1, 2, 3 o 4")

        # Resumen final
        self.mostrar_resumen()

    def fase_1_acceso_core(self):
        """FASE 1: ACCESO Y CORE"""
        self.modulo_actual = "FASE 1: ACCESO Y CORE"
        self.stdout.write(f"\n{Fore.YELLOW}{'='*80}")
        self.stdout.write(f"{Fore.YELLOW}{self.modulo_actual}")
        self.stdout.write(f"{Fore.YELLOW}{'='*80}\n")

        # 1.1 Login
        self.stdout.write(f"\n{Fore.CYAN}[1.1] Verificando Login...")
        if not self.test_url('/', 'Login (Ruta Raíz)', expected_status=200):
            self.stdout.write(f"{Fore.RED}[BLOQUEADO] No se puede continuar. Corrige el login primero.")
            return
        
        if not self.test_url('/login/', 'Login (Ruta /login/)', expected_status=200):
            self.stdout.write(f"{Fore.RED}[BLOQUEADO] No se puede continuar. Corrige el login primero.")
            return

        # 1.2 Crear usuarios de prueba para diferentes roles
        self.stdout.write(f"\n{Fore.CYAN}[1.2] Creando usuarios de prueba...")
        user_quimico = self.crear_usuario_test('test_quimico', 'QUIMICO', False)
        user_farmacia = self.crear_usuario_test('test_farmacia', 'CAJERO', False)
        user_director = self.crear_usuario_test('test_director', 'DIRECTOR', True)
        user_staff = self.crear_usuario_test('test_staff', 'CAJERO', True)

        # 1.3 Verificar redirección por rol
        self.stdout.write(f"\n{Fore.CYAN}[1.3] Verificando redirección automática por rol...")
        
        # Químico
        if user_quimico:
            self.client.login(username='test_quimico', password='test123')
            response = self.client.get('/', follow=True)
            if response.status_code == 200:
                # Verificar que redirigió al dashboard correcto
                final_url = response.request.get('PATH_INFO', '')
                if 'laboratorio' in final_url or 'lista-trabajo' in final_url:
                    self.stdout.write(f"{Fore.GREEN}[OK] Redirección Químico correcta")
                else:
                    self.stdout.write(f"{Fore.YELLOW}[ADVERTENCIA] Químico redirigió a: {final_url}")
            self.client.logout()

        # Farmacia
        if user_farmacia:
            self.client.login(username='test_farmacia', password='test123')
            response = self.client.get('/', follow=True)
            if response.status_code == 200:
                final_url = response.request.get('PATH_INFO', '')
                if 'farmacia' in final_url or 'pdv' in final_url:
                    self.stdout.write(f"{Fore.GREEN}[OK] Redirección Farmacia correcta")
                else:
                    self.stdout.write(f"{Fore.YELLOW}[ADVERTENCIA] Farmacia redirigió a: {final_url}")
            self.client.logout()

        # Director
        if user_director:
            self.client.login(username='test_director', password='test123')
            response = self.client.get('/', follow=True)
            if response.status_code == 200:
                final_url = response.request.get('PATH_INFO', '')
                if 'director' in final_url:
                    self.stdout.write(f"{Fore.GREEN}[OK] Redirección Director correcta")
                else:
                    self.stdout.write(f"{Fore.YELLOW}[ADVERTENCIA] Director redirigió a: {final_url}")
            self.client.logout()

        # 1.4 Verificar Admin bloqueado para no-staff
        self.stdout.write(f"\n{Fore.CYAN}[1.4] Verificando protección del Admin...")
        if user_farmacia:
            self.client.login(username='test_farmacia', password='test123')
            response = self.client.get('/admin/', follow=True)
            if response.status_code == 403 or 'login' in response.request.get('PATH_INFO', ''):
                self.stdout.write(f"{Fore.GREEN}[OK] Admin bloqueado para usuarios no-staff")
            else:
                self.stdout.write(f"{Fore.RED}[ERROR] Admin accesible para usuario no-staff")
            self.client.logout()

        # Admin accesible para staff
        if user_staff:
            self.client.login(username='test_staff', password='test123')
            if self.test_url('/admin/', 'Admin (Usuario Staff)', expected_status=200):
                self.stdout.write(f"{Fore.GREEN}[OK] Admin accesible para staff")
            self.client.logout()

        self.stdout.write(f"\n{Fore.GREEN}[FASE 1 COMPLETADA]")

    def fase_2_laboratorio(self):
        """FASE 2: MÓDULO LABORATORIO"""
        self.modulo_actual = "FASE 2: LABORATORIO"
        self.stdout.write(f"\n{Fore.YELLOW}{'='*80}")
        self.stdout.write(f"{Fore.YELLOW}{self.modulo_actual}")
        self.stdout.write(f"{Fore.YELLOW}{'='*80}\n")

        # Crear usuario químico
        user_quimico = self.crear_usuario_test('test_quimico', 'QUIMICO', False)
        if not user_quimico:
            self.stdout.write(f"{Fore.RED}[BLOQUEADO] No se pudo crear usuario de prueba")
            return

        self.client.login(username='test_quimico', password='test123')

        # 2.1 Recepción
        self.stdout.write(f"\n{Fore.CYAN}[2.1] Verificando Recepción de Laboratorio...")
        if not self.test_url('/laboratorio/recepcion/', 'Recepción Lab', expected_status=200):
            self.stdout.write(f"{Fore.RED}[BLOQUEADO] Error en Recepción. Corrige antes de continuar.")
            return

        # 2.2 Lista de Trabajo
        self.stdout.write(f"\n{Fore.CYAN}[2.2] Verificando Lista de Trabajo...")
        if not self.test_url('/laboratorio/lista-trabajo/', 'Lista Trabajo Lab', expected_status=200):
            self.stdout.write(f"{Fore.RED}[BLOQUEADO] Error en Lista de Trabajo. Corrige antes de continuar.")
            return

        # 2.3 Control de Calidad
        self.stdout.write(f"\n{Fore.CYAN}[2.3] Verificando Control de Calidad...")
        self.test_url('/laboratorio/control-calidad/', 'Control de Calidad', expected_status=200)

        # 2.4 Toma de Muestra
        self.stdout.write(f"\n{Fore.CYAN}[2.4] Verificando Toma de Muestra...")
        self.test_url('/laboratorio/toma-muestra/', 'Toma de Muestra', expected_status=200)

        self.client.logout()
        self.stdout.write(f"\n{Fore.GREEN}[FASE 2 COMPLETADA]")

    def fase_3_farmacia(self):
        """FASE 3: MÓDULO FARMACIA"""
        self.modulo_actual = "FASE 3: FARMACIA"
        self.stdout.write(f"\n{Fore.YELLOW}{'='*80}")
        self.stdout.write(f"{Fore.YELLOW}{self.modulo_actual}")
        self.stdout.write(f"{Fore.YELLOW}{'='*80}\n")

        # Crear usuario de farmacia
        user_farmacia = self.crear_usuario_test('test_farmacia', 'CAJERO', False)
        if not user_farmacia:
            self.stdout.write(f"{Fore.RED}[BLOQUEADO] No se pudo crear usuario de prueba")
            return

        self.client.login(username='test_farmacia', password='test123')

        # 3.1 Punto de Venta (CRÍTICO)
        self.stdout.write(f"\n{Fore.CYAN}[3.1] Verificando Punto de Venta (CRÍTICO)...")
        if not self.test_url('/farmacia/pdv/', 'PDV Farmacia', expected_status=200):
            self.stdout.write(f"{Fore.RED}[BLOQUEADO] Error crítico en PDV. Corrige antes de continuar.")
            return

        # 3.2 Dashboard Farmacia
        self.stdout.write(f"\n{Fore.CYAN}[3.2] Verificando Dashboard Farmacia...")
        self.test_url('/farmacia/dashboard/', 'Dashboard Farmacia', expected_status=200)

        # 3.3 Historial de Ventas
        self.stdout.write(f"\n{Fore.CYAN}[3.3] Verificando Historial de Ventas...")
        self.test_url('/farmacia/historial-ventas/', 'Historial Ventas', expected_status=200)

        # 3.4 Entrada de Mercancía
        self.stdout.write(f"\n{Fore.CYAN}[3.4] Verificando Entrada de Mercancía...")
        self.test_url('/farmacia/almacen/entradas/', 'Entrada Mercancía', expected_status=200)

        # 3.5 Corte de Caja
        self.stdout.write(f"\n{Fore.CYAN}[3.5] Verificando Corte de Caja...")
        self.test_url('/finanzas/corte/', 'Corte de Caja', expected_status=200)

        self.client.logout()
        self.stdout.write(f"\n{Fore.GREEN}[FASE 3 COMPLETADA]")

    def fase_4_medico(self):
        """FASE 4: MÓDULO MÉDICO"""
        self.modulo_actual = "FASE 4: MÉDICO"
        self.stdout.write(f"\n{Fore.YELLOW}{'='*80}")
        self.stdout.write(f"{Fore.YELLOW}{self.modulo_actual}")
        self.stdout.write(f"{Fore.YELLOW}{'='*80}\n")

        # Crear usuario médico
        user_medico = self.crear_usuario_test('test_medico', 'MEDICO', False)
        if not user_medico:
            self.stdout.write(f"{Fore.RED}[BLOQUEADO] No se pudo crear usuario de prueba")
            return

        self.client.login(username='test_medico', password='test123')

        # 4.1 Dashboard Médico
        self.stdout.write(f"\n{Fore.CYAN}[4.1] Verificando Dashboard Médico...")
        if not self.test_url('/medico/', 'Dashboard Médico', expected_status=200):
            self.stdout.write(f"{Fore.RED}[BLOQUEADO] Error en Dashboard Médico. Corrige antes de continuar.")
            return

        # 4.2 Consulta Médica
        self.stdout.write(f"\n{Fore.CYAN}[4.2] Verificando Consulta Médica...")
        self.test_url('/medico/consulta/', 'Consulta Médica', expected_status=200)

        # 4.3 Lista Trabajo USG
        self.stdout.write(f"\n{Fore.CYAN}[4.3] Verificando Lista Trabajo USG...")
        self.test_url('/medico/ultrasonido/lista-trabajo/', 'Lista Trabajo USG', expected_status=200)

        # 4.4 Captura Reporte USG
        self.stdout.write(f"\n{Fore.CYAN}[4.4] Verificando Captura Reporte USG...")
        self.test_url('/medico/ultrasonido/captura/', 'Captura Reporte USG', expected_status=200)

        self.client.logout()
        self.stdout.write(f"\n{Fore.GREEN}[FASE 4 COMPLETADA]")

    def mostrar_resumen(self):
        """Muestra el resumen final de la auditoría."""
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}RESUMEN DE AUDITORÍA")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")

        if self.errores_encontrados:
            self.stdout.write(f"{Fore.RED}[!] Se encontraron {len(self.errores_encontrados)} errores:\n")
            for i, error in enumerate(self.errores_encontrados, 1):
                self.stdout.write(f"{Fore.RED}[{i}] {error['modulo']}")
                self.stdout.write(f"    URL: {error['url']}")
                self.stdout.write(f"    Error: {error['error']}")
                if error['traceback']:
                    self.stdout.write(f"    Traceback: {error['traceback'][:300]}...")
                self.stdout.write("")
        else:
            self.stdout.write(f"{Fore.GREEN}[OK] No se encontraron errores críticos.\n")

        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")

    def add_arguments(self, parser):
        parser.add_argument(
            '--fase',
            type=str,
            default='1',
            help='Fase a ejecutar (1, 2, 3 o 4)',
        )
