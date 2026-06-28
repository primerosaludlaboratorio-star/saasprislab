#!/usr/bin/env python
"""
SCRIPT DE PRUEBA DE CONEXIÓN - PRISLAB V5.0
===========================================
Fecha: 1 de Febrero de 2026
Objetivo: Verificar conexión a todos los motores de almacenamiento

Pruebas incluidas:
1. ✅ Base de datos (PostgreSQL/SQLite)
2. ✅ Google Drive Storage (media files)
3. ✅ Static Files (WhiteNoise)
4. ✅ Subida de archivo de prueba
5. ✅ Generación de URL pública
6. ✅ Eliminación de archivo de prueba

Uso:
    python test_conexion_storage.py
"""

import os
import sys
import django
from datetime import datetime
from io import BytesIO
import logging

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}  {text}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}[OK] {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}[ERROR] {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}[INFO] {text}{Colors.END}")

def test_database():
    """Prueba 1: Conexión a la base de datos"""
    print_header("PRUEBA 1: CONEXIÓN A BASE DE DATOS")
    
    try:
        from django.db import connection
        from django.conf import settings
        
        # Obtener información de la base de datos
        db_engine = settings.DATABASES['default']['ENGINE']
        db_name = settings.DATABASES['default']['NAME']
        
        print_info(f"Motor: {db_engine}")
        print_info(f"Base de datos: {db_name}")
        
        # Probar la conexión
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result[0] == 1:
                print_success("Conexión a base de datos EXITOSA")
                
                # Obtener información adicional
                if 'postgresql' in db_engine:
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    print_info(f"Versión: {version.split(',')[0]}")
                elif 'sqlite' in db_engine:
                    cursor.execute("SELECT sqlite_version()")
                    version = cursor.fetchone()[0]
                    print_info(f"Versión SQLite: {version}")
                
                return True
            else:
                print_error("Conexión a base de datos FALLIDA")
                return False
                
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_database (test_conexion_storage.py)")
        print_error(f"Error al conectar a la base de datos: {e}")
        return False

def test_models():
    """Prueba 2: Verificar modelos críticos"""
    print_header("PRUEBA 2: VERIFICACIÓN DE MODELOS")
    
    try:
        from core.models import OrdenDeServicio, Paciente, Empresa
        
        # Contar registros
        total_ordenes = OrdenDeServicio.objects.count()
        total_pacientes = Paciente.objects.count()
        total_empresas = Empresa.objects.count()
        
        print_success(f"Modelo OrdenDeServicio: {total_ordenes} registros")
        print_success(f"Modelo Paciente: {total_pacientes} registros")
        print_success(f"Modelo Empresa: {total_empresas} registros")
        
        # Verificar campo archivo_resultado
        orden_con_pdf = OrdenDeServicio.objects.filter(
            archivo_resultado__isnull=False
        ).first()
        
        if orden_con_pdf:
            print_success(f"Orden con PDF encontrada: {orden_con_pdf.id}")
            print_info(f"   Archivo: {orden_con_pdf.archivo_resultado.name}")
        else:
            print_warning("No hay órdenes con PDF guardado aún")
        
        return True
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_models (test_conexion_storage.py)")
        print_error(f"Error al verificar modelos: {e}")
        return False

def test_google_drive_storage():
    """Prueba 3: Configuración de Google Drive Storage"""
    print_header("PRUEBA 3: GOOGLE DRIVE STORAGE")
    
    try:
        from django.conf import settings
        
        # Verificar configuración
        default_storage = settings.DEFAULT_FILE_STORAGE
        print_info(f"Storage backend: {default_storage}")
        
        if 'GoogleDriveStorage' in default_storage:
            print_success("Google Drive Storage CONFIGURADO")
            
            # Intentar importar el storage backend
            from config.storage_backends import GoogleDriveStorage
            storage = GoogleDriveStorage()
            
            print_success("Storage backend importado correctamente")
            
            # Verificar credenciales
            if hasattr(storage, 'service'):
                print_success("Credenciales de Google Drive DISPONIBLES")
            else:
                print_warning("Credenciales no verificadas (se cargan en el primer uso)")
            
            return True
        else:
            print_warning(f"Usando storage local: {default_storage}")
            return True
            
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_google_drive_storage (test_conexion_storage.py)")
        print_error(f"Error al verificar Google Drive Storage: {e}")
        return False

def test_upload_file():
    """Prueba 4: Subir archivo de prueba"""
    print_header("PRUEBA 4: SUBIDA DE ARCHIVO DE PRUEBA")
    
    try:
        from django.core.files.base import ContentFile
        from core.models import OrdenDeServicio, Paciente, Empresa
        
        import os
        eid = os.environ.get("PRISLAB_EMPRESA_ID")
        if not eid:
            print_error("Defina PRISLAB_EMPRESA_ID (pk de Empresa) para esta prueba.")
            return False
        try:
            empresa = Empresa.objects.get(pk=int(eid))
        except (ValueError, Empresa.DoesNotExist):
            print_error(f"Empresa id={eid!r} no válida.")
            return False

        paciente = Paciente.objects.filter(empresa=empresa).first()
        if not paciente:
            print_error("No hay pacientes para esa empresa (PRISLAB_EMPRESA_ID).")
            return False
        
        # Buscar una orden existente o crear una
        orden = OrdenDeServicio.objects.filter(
            empresa=empresa,
            paciente=paciente
        ).first()
        
        if not orden:
            print_warning("No hay órdenes existentes, creando orden de prueba...")
            orden = OrdenDeServicio.objects.create(
                empresa=empresa,
                paciente=paciente,
                folio_orden=f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                estado='REGISTRADO',
                total=0,
                anticipo=0
            )
            print_info(f"Orden de prueba creada: ID {orden.id}")
        else:
            print_info(f"Usando orden existente: ID {orden.id}")
        
        # Crear contenido de prueba (PDF simulado)
        pdf_content = b"%PDF-1.4\n%Test PDF\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF"
        pdf_file = ContentFile(pdf_content)
        
        # Nombre del archivo
        filename = f'test_conexion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        print_info(f"Subiendo archivo: {filename}")
        print_info(f"Tamaño: {len(pdf_content)} bytes")
        
        # Subir el archivo
        orden.archivo_resultado.save(filename, pdf_file, save=True)
        
        print_success(f"Archivo subido exitosamente")
        print_info(f"   Nombre guardado: {orden.archivo_resultado.name}")
        
        # Intentar obtener la URL
        try:
            url = orden.archivo_resultado.url
            print_success(f"URL pública generada:")
            print(f"{Colors.WHITE}   {url}{Colors.END}")
            
            # Guardar ID de la orden para limpieza posterior
            return orden.id
            
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_upload_file (test_conexion_storage.py)")
            print_warning(f"No se pudo generar URL pública: {e}")
            return orden.id
            
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_upload_file (test_conexion_storage.py)")
        print_error(f"Error al subir archivo: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cleanup(orden_id):
    """Prueba 5: Limpiar archivo de prueba"""
    print_header("PRUEBA 5: LIMPIEZA DE ARCHIVO DE PRUEBA")
    
    if not orden_id:
        print_warning("No hay archivo de prueba para limpiar")
        return True
    
    try:
        from core.models import OrdenDeServicio
        
        orden = OrdenDeServicio.objects.get(id=orden_id)
        
        if orden.archivo_resultado:
            print_info(f"Eliminando archivo: {orden.archivo_resultado.name}")
            
            # Eliminar el archivo
            orden.archivo_resultado.delete(save=True)
            
            print_success("Archivo de prueba eliminado")
            
            # Si la orden fue creada para prueba, eliminarla
            if orden.folio_orden.startswith('TEST-'):
                print_info(f"Eliminando orden de prueba: {orden.id}")
                orden.delete()
                print_success("Orden de prueba eliminada")
            
            return True
        else:
            print_warning("No hay archivo para eliminar")
            return True
            
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_cleanup (test_conexion_storage.py)")
        print_error(f"Error al limpiar archivo: {e}")
        return False

def test_static_files():
    """Prueba 6: Verificar archivos estáticos"""
    print_header("PRUEBA 6: ARCHIVOS ESTÁTICOS")
    
    try:
        from django.conf import settings
        
        # Verificar configuración de static files
        static_url = settings.STATIC_URL
        static_root = settings.STATIC_ROOT
        staticfiles_storage = settings.STATICFILES_STORAGE
        
        print_info(f"STATIC_URL: {static_url}")
        print_info(f"STATIC_ROOT: {static_root}")
        print_info(f"Storage: {staticfiles_storage}")
        
        if 'WhiteNoise' in staticfiles_storage:
            print_success("WhiteNoise CONFIGURADO correctamente")
        else:
            print_warning("WhiteNoise no detectado")
        
        # Verificar si STATIC_ROOT existe
        if os.path.exists(static_root):
            # Contar archivos estáticos
            total_files = sum(len(files) for _, _, files in os.walk(static_root))
            print_success(f"STATIC_ROOT existe: {total_files} archivos")
        else:
            print_warning("STATIC_ROOT no existe (ejecutar collectstatic)")
        
        return True
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_static_files (test_conexion_storage.py)")
        print_error(f"Error al verificar archivos estáticos: {e}")
        return False

def main():
    """Función principal"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("="*63)
    print("")
    print("        PRISLAB V5.0 - PRUEBA DE CONEXION STORAGE         ")
    print("")
    print("     Verificando: Database, Google Drive, Static Files    ")
    print("")
    print("="*63)
    print(f"{Colors.END}\n")
    
    print_info(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print_info(f"Python: {sys.version.split()[0]}")
    print_info(f"Django: {django.get_version()}")
    print()
    
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    # Resultados
    resultados = {
        'database': False,
        'models': False,
        'google_drive': False,
        'upload': False,
        'cleanup': False,
        'static': False
    }
    
    orden_id_prueba = None
    
    # Ejecutar pruebas
    try:
        resultados['database'] = test_database()
        resultados['models'] = test_models()
        resultados['google_drive'] = test_google_drive_storage()
        resultados['upload'] = orden_id_prueba = test_upload_file()
        resultados['static'] = test_static_files()
        
        # Limpieza (solo si se solicita)
        print()
        respuesta = input(f"{Colors.YELLOW}¿Deseas eliminar el archivo de prueba? (s/n): {Colors.END}").lower()
        if respuesta == 's' and orden_id_prueba:
            resultados['cleanup'] = test_cleanup(orden_id_prueba)
        elif orden_id_prueba:
            print_info(f"Archivo de prueba conservado en orden ID: {orden_id_prueba}")
            resultados['cleanup'] = True  # No es un error no limpiar
        
    except KeyboardInterrupt:
        print_warning("\n\nPrueba interrumpida por el usuario")
        sys.exit(1)
    
    # Resumen final
    print_header("RESUMEN DE PRUEBAS")
    
    total_pruebas = len(resultados)
    pruebas_exitosas = sum(1 for r in resultados.values() if r)
    
    print()
    for nombre, resultado in resultados.items():
        nombre_formateado = nombre.replace('_', ' ').title()
        if resultado:
            print_success(f"{nombre_formateado}: PASÓ")
        else:
            print_error(f"{nombre_formateado}: FALLÓ")
    
    print()
    print(f"{Colors.BOLD}Total: {pruebas_exitosas}/{total_pruebas} pruebas exitosas{Colors.END}")
    
    if pruebas_exitosas == total_pruebas:
        print(f"\n{Colors.GREEN}{Colors.BOLD}")
        print("="*63)
        print("")
        print("          TODAS LAS PRUEBAS PASARON                     ")
        print("")
        print("      El sistema de almacenamiento esta funcionando     ")
        print("                  correctamente                          ")
        print("")
        print("="*63)
        print(f"{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}")
        print("="*63)
        print("")
        print("          ALGUNAS PRUEBAS FALLARON                      ")
        print("")
        print("      Revisa los errores anteriores para mas detalles   ")
        print("")
        print("="*63)
        print(f"{Colors.END}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())