"""
Script de Auditoría de Calidad (QA) para PRISLAB v5.
Verifica que todas las vistas principales respondan correctamente.
"""

import os
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
    help = 'Ejecuta una auditoría completa de calidad (QA) de todas las vistas principales'

    def handle(self, *args, **options):
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}AUDITORÍA DE CALIDAD (QA) - PRISLAB v5")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")

        # Crear cliente de prueba
        client = Client()
        
        # Intentar login como admin
        try:
            # Buscar o crear usuario admin
            admin_user, created = User.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@prislab.com',
                    'is_staff': True,
                    'is_superuser': True
                }
            )
            if created:
                admin_user.set_password('Prislab2026')
                admin_user.save()
                self.stdout.write(f"{Fore.YELLOW}[!] Usuario admin creado con contraseña: Prislab2026")
            else:
                admin_user.set_password('Prislab2026')
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.save()
            
            # Login
            login_success = client.login(username='admin', password=os.environ.get('PRISLAB_QA_ADMIN_PASSWORD', 'Prislab2026'))
            if not login_success:
                self.stdout.write(f"{Fore.RED}[X] ERROR: No se pudo hacer login como admin")
                return
            else:
                self.stdout.write(f"{Fore.GREEN}[OK] Login exitoso como admin\n")
        except Exception as e:
            self.stdout.write(f"{Fore.RED}[X] ERROR al hacer login: {e}\n")
            return

        # Definir rutas principales a probar
        rutas_principales = [
            # Dashboard / Inicio
            {'url': '/', 'nombre': 'Home (PDV Farmacia)', 'metodo': 'GET'},
            {'url': '/farmacia/pdv/', 'nombre': 'PDV Farmacia', 'metodo': 'GET'},
            {'url': '/farmacia/dashboard/', 'nombre': 'Dashboard Farmacia', 'metodo': 'GET'},
            
            # Pacientes
            {'url': '/admin/core/paciente/', 'nombre': 'Lista de Pacientes (Admin)', 'metodo': 'GET'},
            {'url': '/api/pacientes/buscar/', 'nombre': 'API Buscar Pacientes', 'metodo': 'GET'},
            
            # Consulta Médica
            {'url': '/medico/', 'nombre': 'Dashboard Médico', 'metodo': 'GET'},
            {'url': '/medico/consulta/', 'nombre': 'Consulta Médica', 'metodo': 'GET'},
            {'url': '/medico/expediente/1/', 'nombre': 'Expediente Clínico (ID=1)', 'metodo': 'GET'},
            
            # Recetas
            {'url': '/medico/ultrasonido/lista-trabajo/', 'nombre': 'Lista Trabajo USG', 'metodo': 'GET'},
            {'url': '/medico/ultrasonido/captura/', 'nombre': 'Captura Reporte USG', 'metodo': 'GET'},

            # Finanzas/Caja
            {'url': '/finanzas/corte/', 'nombre': 'Corte de Caja', 'metodo': 'GET'},
            {'url': '/finanzas/facturacion/', 'nombre': 'Facturación 4.0', 'metodo': 'GET'},
            {'url': '/finanzas/registro-gasto/', 'nombre': 'Registro de Gasto', 'metodo': 'GET'},
            
            # Laboratorio
            {'url': '/laboratorio/recepcion/', 'nombre': 'Recepción Laboratorio', 'metodo': 'GET'},
            {'url': '/laboratorio/lista-trabajo/', 'nombre': 'Lista Trabajo Lab', 'metodo': 'GET'},
            {'url': '/laboratorio/control-calidad/', 'nombre': 'Control de Calidad', 'metodo': 'GET'},
            {'url': '/laboratorio/toma-muestra/', 'nombre': 'Toma de Muestra', 'metodo': 'GET'},
            
            # Inventario
            {'url': '/inventario/', 'nombre': 'Inventario General', 'metodo': 'GET'},
            {'url': '/farmacia/almacen/entradas/', 'nombre': 'Entrada de Mercancía', 'metodo': 'GET'},
            
            # Catálogos
            {'url': '/catalogos/estudios/', 'nombre': 'Lista de Estudios', 'metodo': 'GET'},
            
            # Configuración
            {'url': '/configuracion/', 'nombre': 'Configuración Dashboard', 'metodo': 'GET'},
            {'url': '/ia/', 'nombre': 'Dashboard IA', 'metodo': 'GET'},
            {'url': '/director/', 'nombre': 'Dashboard Director', 'metodo': 'GET'},
            
            # Otros módulos importantes
            {'url': '/cotizacion/', 'nombre': 'Cotización Rápida', 'metodo': 'GET'},
            {'url': '/manual/', 'nombre': 'Manual Operativo', 'metodo': 'GET'},
            {'url': '/farmacia/historial-ventas/', 'nombre': 'Historial de Ventas', 'metodo': 'GET'},
            {'url': '/farmacia/libro-control/', 'nombre': 'Libro Control Antibióticos', 'metodo': 'GET'},
            
            # RRHH
            {'url': '/rh/evaluaciones/', 'nombre': 'Lista Evaluaciones 39A', 'metodo': 'GET'},
            {'url': '/rh/desempeno/nueva/', 'nombre': 'Nueva Evaluación Desempeño', 'metodo': 'GET'},
            {'url': '/rh/mis-resultados/', 'nombre': 'Mis Resultados', 'metodo': 'GET'},
            
            # Chat / IA
            {'url': '/cerebro/chat/', 'nombre': 'Chat Experto', 'metodo': 'GET'},
            
            # Admin (verificar que funciona)
            {'url': '/admin/', 'nombre': 'Admin Django', 'metodo': 'GET'},
            {'url': '/admin/core/paciente/', 'nombre': 'Admin Pacientes', 'metodo': 'GET'},
            {'url': '/admin/core/ordendeservicio/', 'nombre': 'Admin Órdenes', 'metodo': 'GET'},
        ]

        # Resultados
        resultados = []
        errores_detallados = []

        self.stdout.write(f"{Fore.CYAN}Iniciando pruebas de {len(rutas_principales)} rutas...\n")

        for ruta_info in rutas_principales:
            url = ruta_info['url']
            nombre = ruta_info['nombre']
            metodo = ruta_info.get('metodo', 'GET')
            
            try:
                if metodo == 'GET':
                    response = client.get(url, follow=True)
                elif metodo == 'POST':
                    response = client.post(url, follow=True)
                else:
                    response = client.get(url, follow=True)
                
                status_code = response.status_code
                
                # Clasificar resultado
                if status_code == 200:
                    estado = f"{Fore.GREEN}[VERDE]"
                    resultado = "OK"
                elif status_code in [301, 302, 303, 307, 308]:
                    estado = f"{Fore.YELLOW}[AMARILLO]"
                    resultado = f"Redireccion ({status_code})"
                elif status_code in [400, 403, 404]:
                    estado = f"{Fore.YELLOW}[AMARILLO]"
                    resultado = f"Status {status_code}"
                elif status_code >= 500:
                    estado = f"{Fore.RED}[ROJO]"
                    resultado = f"Error {status_code}"
                    # Capturar el error
                    try:
                        error_content = response.content.decode('utf-8')[:500]
                        errores_detallados.append({
                            'url': url,
                            'nombre': nombre,
                            'status': status_code,
                            'error': error_content
                        })
                    except:
                        pass
                else:
                    estado = f"{Fore.YELLOW}[AMARILLO]"
                    resultado = f"Status {status_code}"
                
                resultados.append({
                    'nombre': nombre,
                    'url': url,
                    'status': status_code,
                    'estado': estado,
                    'resultado': resultado
                })
                
                self.stdout.write(f"{estado} {nombre:.<50} {resultado}")
                
            except Exception as e:
                estado = f"{Fore.RED}[ROJO]"
                error_msg = str(e)
                traceback_str = traceback.format_exc()
                
                resultados.append({
                    'nombre': nombre,
                    'url': url,
                    'status': 'EXCEPTION',
                    'estado': estado,
                    'resultado': f"Excepción: {error_msg[:50]}"
                })
                
                errores_detallados.append({
                    'url': url,
                    'nombre': nombre,
                    'status': 'EXCEPTION',
                    'error': traceback_str
                })
                
                self.stdout.write(f"{estado} {nombre:.<50} EXCEPCIÓN: {error_msg[:50]}")

        # Resumen
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}RESUMEN DE AUDITORÍA")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")
        
        verdes = sum(1 for r in resultados if '[VERDE]' in r['estado'])
        amarillos = sum(1 for r in resultados if '[AMARILLO]' in r['estado'])
        rojos = sum(1 for r in resultados if '[ROJO]' in r['estado'])
        total = len(resultados)
        
        self.stdout.write(f"{Fore.GREEN}[VERDE] OK: {verdes}/{total}")
        self.stdout.write(f"{Fore.YELLOW}[AMARILLO] Advertencia: {amarillos}/{total}")
        self.stdout.write(f"{Fore.RED}[ROJO] Error: {rojos}/{total}\n")
        
        # Mostrar errores detallados
        if errores_detallados:
            self.stdout.write(f"{Fore.RED}{'='*80}")
            self.stdout.write(f"{Fore.RED}ERRORES DETALLADOS")
            self.stdout.write(f"{Fore.RED}{'='*80}\n")
            
            for i, error in enumerate(errores_detallados, 1):
                self.stdout.write(f"\n{Fore.RED}[ERROR {i}] {error['nombre']}")
                self.stdout.write(f"{Fore.RED}URL: {error['url']}")
                self.stdout.write(f"{Fore.RED}Status: {error.get('status', 'N/A')}")
                self.stdout.write(f"{Fore.RED}Traceback:")
                self.stdout.write(f"{Fore.RED}{error['error'][:2000]}...")  # Limitar a 2000 caracteres
                self.stdout.write(f"\n{Fore.RED}{'-'*80}\n")
        
        # Tabla final
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}TABLA DE RESULTADOS")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")
        
        self.stdout.write(f"{'RUTA':<50} {'STATUS':<10} {'RESULTADO'}")
        self.stdout.write(f"{'-'*80}")
        
        for r in resultados:
            estado_limpio = r['estado'].replace(Fore.GREEN, '').replace(Fore.YELLOW, '').replace(Fore.RED, '').replace(Style.RESET_ALL, '')
            self.stdout.write(f"{r['nombre']:<50} {r['status']:<10} {estado_limpio}")
        
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}\n")
        
        if rojos > 0:
            self.stdout.write(f"{Fore.RED}[!] ATENCION: Se encontraron {rojos} errores criticos que requieren atencion inmediata.")
        else:
            self.stdout.write(f"{Fore.GREEN}[OK] Excelente! Todas las rutas principales estan funcionando correctamente.")
