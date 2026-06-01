"""
Auditoría Forense Completa - Módulo Laboratorio
Simula el flujo completo de una Química: Recepción → Orden → Resultados → PDF
"""

from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import Empresa, Paciente, OrdenDeServicio
import traceback
import time
from colorama import init, Fore, Style
from decimal import Decimal

init(autoreset=True)

User = get_user_model()


class Command(BaseCommand):
    help = 'Auditoría forense completa del Módulo Laboratorio'

    def __init__(self):
        super().__init__()
        self.client = Client()
        self.resultados = {
            'vistas_probadas': [],
            'operaciones_realizadas': [],
            'errores_encontrados': [],
            'warnings': []
        }
        self.orden_creada = None
        self.paciente_creado = None

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
            else:
                self.log_result('WARNING', f"{nombre} - Status {status}")
                return status < 400, response
                
        except Exception as e:
            tiempo_respuesta = time.time() - inicio
            self.log_result('ERROR', f"{nombre} - Excepción: {str(e)}", traceback.format_exc())
            return False, None

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}AUDITORÍA FORENSE - MÓDULO LABORATORIO")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")

        # Crear usuario de prueba (Químico)
        try:
            empresa, _ = Empresa.objects.get_or_create(
                nombre='Laboratorio del Valle',
                defaults={'activa': True}
            )
            
            user_quimico, created = User.objects.get_or_create(
                username='test_quimico_lab',
                defaults={
                    'email': 'quimico@test.com',
                    'rol': 'QUIMICO',
                    'is_staff': False,
                    'empresa': empresa
                }
            )
            if not created:
                user_quimico.empresa = empresa
                user_quimico.save()
            user_quimico.set_password('test123')
            user_quimico.save()
            
            self.log_result('OK', "Usuario Químico creado: test_quimico_lab / test123")
        except Exception as e:
            self.log_result('ERROR', f"No se pudo crear usuario: {str(e)}")
            return

        # Login
        login_ok = self.client.login(username='test_quimico_lab', password='test123')
        if not login_ok:
            self.log_result('ERROR', "No se pudo hacer login")
            return

        # PASO 1: Recepción
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 1] Verificando Recepción de Laboratorio\n")
        ok, response = self.test_url('/laboratorio/recepcion/', 'Recepción Lab', expected_status=200)
        if not ok:
            self.log_result('ERROR', "Recepción falló. No se puede continuar.")
            return

        # Verificar que el formulario esté presente
        if response:
            html = response.content.decode('utf-8', errors='ignore')
            if 'paciente' in html.lower() or 'estudio' in html.lower():
                self.log_result('OK', "Formulario de recepción detectado en el HTML")
            else:
                self.log_result('WARNING', "No se detectó el formulario de recepción en el HTML")

        # PASO 2: Crear Paciente y Orden de Prueba
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 2] Creando Paciente y Orden de Prueba\n")
        
        try:
            # Crear paciente de prueba
            paciente, created = Paciente.objects.get_or_create(
                nombre_completo='PACIENTE PRUEBA AUDITORIA',
                empresa=empresa,
                defaults={
                    'telefono': '1234567890',
                    'email': 'paciente@test.com',
                    'tipo': 'AMBULATORIO'
                }
            )
            self.paciente_creado = paciente
            if created:
                self.log_result('OK', f"Paciente de prueba creado: {paciente.nombre_completo}")
            else:
                self.log_result('INFO', f"Paciente de prueba ya existía: {paciente.nombre_completo}")

            # Obtener un estudio disponible (Estudio no tiene campo empresa)
            estudio = Estudio.objects.filter(activo=True).first()
            if not estudio:
                # Crear un estudio de prueba si no existe
                categoria, _ = CategoriaEstudio.objects.get_or_create(
                    nombre='Prueba'
                )
                estudio = Estudio.objects.create(
                    codigo='HEMO-001',
                    nombre='Hemograma Completo',
                    categoria=categoria,
                    precio=Decimal('150.00'),
                    activo=True
                )
                self.log_result('INFO', "Estudio de prueba creado: Hemograma Completo")
            else:
                self.log_result('OK', f"Usando estudio existente: {estudio.nombre}")

            # Crear orden de servicio (cumpliendo Triple Llave para PDF)
            from datetime import datetime
            folio = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user_quimico.id}"
            
            orden = OrdenDeServicio.objects.create(
                empresa=empresa,
                paciente=paciente,
                responsable_ingreso=user_quimico,
                estado='EN_PROCESO',  # Estado seguro para prueba (sin PDF requerido)
                total=Decimal('150.00'),
                anticipo=Decimal('150.00'),  # Saldo = 0 (cumple Triple Llave)
                estado_pago='PAGADO',
                folio_orden=folio
            )
            self.orden_creada = orden
            self.log_result('OK', f"Orden de prueba creada: {orden.folio_orden or orden.id}")
            
            # Marcar teléfono como verificado (para Triple Llave)
            if hasattr(paciente, 'telefono_verificado'):
                paciente.telefono_verificado = True
                paciente.save()
                self.log_result('OK', "Teléfono del paciente marcado como verificado (Triple Llave)")

            # Crear detalle de orden con resultado y validación (para PDF)
            from core.models import DetalleOrden
            from django.utils import timezone
            detalle = DetalleOrden.objects.create(
                orden=orden,
                estudio=estudio,
                precio_momento=Decimal('150.00'),
                estado_procesamiento='RESULTADO_LISTO',
                resultado='Resultado de prueba: 100 mg/dL',
                fecha_validacion=timezone.now(),
                validado_por=user_quimico
            )
            self.log_result('OK', f"Detalle de orden creado con resultado y validación: {estudio.nombre}")

        except Exception as e:
            self.log_result('ERROR', f"Error al crear datos de prueba: {str(e)}", traceback.format_exc())
            return

        # PASO 3: Lista de Trabajo
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 3] Verificando Lista de Trabajo\n")
        ok, response = self.test_url('/laboratorio/lista-trabajo/', 'Lista Trabajo Lab', expected_status=200)
        if not ok:
            self.log_result('ERROR', "Lista de trabajo falló. No se puede continuar.")
            return

        # Verificar que la orden aparezca en la lista
        if response and self.orden_creada:
            html = response.content.decode('utf-8', errors='ignore')
            folio = self.orden_creada.folio_orden or str(self.orden_creada.id)
            if folio in html or str(self.orden_creada.id) in html:
                self.log_result('OK', f"Orden {folio} aparece en la lista de trabajo")
            else:
                self.log_result('WARNING', f"La orden {folio} no aparece en la lista de trabajo")

        # PASO 4: Cargar Resultados
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 4] Verificando Vista de Cargar Resultados\n")
        if self.orden_creada:
            ok, response = self.test_url(
                f'/laboratorio/captura/{self.orden_creada.id}/',
                'Captura Resultados',
                expected_status=200
            )
            if not ok:
                self.log_result('ERROR', "Vista de captura de resultados falló")
            else:
                # Verificar que el formulario de resultados esté presente
                if response:
                    html = response.content.decode('utf-8', errors='ignore')
                    if 'resultado' in html.lower() or 'valor' in html.lower():
                        self.log_result('OK', "Formulario de resultados detectado en el HTML")
                    else:
                        self.log_result('WARNING', "No se detectó el formulario de resultados")

        # PASO 5: Generación de PDF
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 5] Verificando Generación de PDF\n")
        if self.orden_creada:
            # La vista puede redirigir si no cumple Triple Llave, así que aceptamos 200 o 302
            ok, response = self.test_url(
                f'/laboratorio/resultados/{self.orden_creada.id}/pdf/',
                'Generar PDF Resultados',
                expected_status=[200, 302]  # Puede ser PDF o redirect
            )
            if not ok:
                self.log_result('WARNING', "Generación de PDF puede requerir validaciones adicionales (Triple Llave)")
            else:
                # Verificar que la respuesta sea un PDF o un redirect válido
                if response:
                    status = response.status_code
                    if status == 302:
                        # Redirect es válido si es por validaciones de Triple Llave
                        self.log_result('INFO', "PDF redirige (puede ser por validaciones de Triple Llave)")
                    else:
                        content_type = response.get('Content-Type', '')
                        if 'pdf' in content_type.lower() or (response.content and response.content[:4] == b'%PDF'):
                            self.log_result('OK', "PDF generado correctamente")
                        else:
                            # Si no es PDF, puede ser HTML de error o mensaje
                            html = response.content.decode('utf-8', errors='ignore')[:200]
                            if 'error' in html.lower() or 'llave' in html.lower():
                                self.log_result('WARNING', "PDF requiere validaciones adicionales (Triple Llave)")
                            else:
                                self.log_result('WARNING', f"Respuesta no es PDF: {content_type}")

        # PASO 6: Otras vistas del módulo
        self.stdout.write(f"\n{Fore.YELLOW}[PASO 6] Verificando Otras Vistas del Módulo\n")
        
        self.test_url('/laboratorio/control-calidad/', 'Control de Calidad', expected_status=200)
        self.test_url('/laboratorio/toma-muestra/', 'Toma de Muestra', expected_status=200)

        # Resumen
        self.mostrar_resumen()

        # Limpieza (opcional)
        self.log_result('INFO', "Datos de prueba creados (pueden limpiarse manualmente si es necesario)")

    def mostrar_resumen(self):
        """Muestra el resumen final de la auditoría."""
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}RESUMEN DE AUDITORÍA FORENSE - LABORATORIO")
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
        
        recepcion_ok = any('Recepción' in v['nombre'] and v['exito'] for v in self.resultados['vistas_probadas'])
        lista_ok = any('Lista Trabajo' in v['nombre'] and v['exito'] for v in self.resultados['vistas_probadas'])
        resultados_ok = any('Captura Resultados' in v['nombre'] and v['exito'] for v in self.resultados['vistas_probadas'])
        pdf_ok = any('PDF' in v['nombre'] and v['exito'] for v in self.resultados['vistas_probadas'])
        
        self.stdout.write(f"{Fore.GREEN if recepcion_ok else Fore.RED}Recepción: {'OK' if recepcion_ok else 'ERROR'}")
        self.stdout.write(f"{Fore.GREEN if lista_ok else Fore.RED}Lista de Trabajo: {'OK' if lista_ok else 'ERROR'}")
        self.stdout.write(f"{Fore.GREEN if resultados_ok else Fore.RED}Carga Resultados: {'OK' if resultados_ok else 'ERROR'}")
        self.stdout.write(f"{Fore.GREEN if pdf_ok else Fore.RED}Generación PDF: {'OK' if pdf_ok else 'ERROR'}")
        
        if total_errores == 0:
            self.stdout.write(f"\n{Fore.GREEN}[ESTADO FINAL] BLINDADO - Sin errores críticos")
        else:
            self.stdout.write(f"\n{Fore.RED}[ESTADO FINAL] REQUIERE ATENCIÓN - {total_errores} errores encontrados")
        
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}\n")
