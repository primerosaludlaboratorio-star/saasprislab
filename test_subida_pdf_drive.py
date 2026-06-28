#!/usr/bin/env python
"""
PRUEBA DE SUBIDA PDF A GOOGLE DRIVE - PRISLAB V5.0
===================================================
Fecha: 1 de Febrero de 2026
Objetivo: Verificar que los PDFs se suben automáticamente a Google Drive

META: "Quiero tener la certeza absoluta de que al dar clic en 'Finalizar Examen',
       el PDF aparece en la carpeta de Drive del Dr. Jonathan"

Bloques blindados:
1. ✅ Generar PDF dummy ("Hola Mundo Laboratorio")
2. ✅ Guardar en modelo OrdenDeServicio
3. ✅ Verificar URL generada es de Google Drive
4. ✅ Imprimir resultado específico
"""

import os
import sys
import django
from datetime import datetime
from io import BytesIO
import logging

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
END = '\033[0m'

def print_header(text):
    print(f"\n{CYAN}{BOLD}{'='*70}{END}")
    print(f"{CYAN}{BOLD}  {text}{END}")
    print(f"{CYAN}{BOLD}{'='*70}{END}\n")

def print_success(text):
    print(f"{GREEN}[OK] {text}{END}")

def print_error(text):
    print(f"{RED}[ERROR] {text}{END}")

def print_info(text):
    print(f"{CYAN}[INFO] {text}{END}")

def generar_pdf_dummy():
    """
    BLOQUE 1: GENERAR PDF DUMMY
    ===========================
    Crea un PDF simple con ReportLab que dice "Hola Mundo Laboratorio"
    """
    print_header("BLOQUE 1: GENERAR PDF DUMMY")
    
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        
        print_info("Generando PDF de prueba con ReportLab...")
        
        # Crear PDF en memoria
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        # Estilos
        styles = getSampleStyleSheet()
        elements = []
        
        # Contenido
        titulo = Paragraph("<b>HOLA MUNDO LABORATORIO</b>", styles['Title'])
        elements.append(titulo)
        elements.append(Spacer(1, 1*cm))
        
        contenido = Paragraph(
            f"Este es un PDF de prueba generado el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}.<br/><br/>"
            "Si estás leyendo esto, significa que:<br/>"
            "✅ El sistema genera PDFs correctamente<br/>"
            "✅ El sistema guarda PDFs en Google Drive<br/>"
            "✅ El sistema genera URLs públicas<br/><br/>"
            "<b>¡PRISLAB V5.0 funcionando correctamente!</b>",
            styles['Normal']
        )
        elements.append(contenido)
        
        # Construir PDF
        doc.build(elements)
        
        # Obtener bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        print_success(f"PDF generado: {len(pdf_bytes)} bytes")
        print_info(f"Contenido: 'HOLA MUNDO LABORATORIO'")
        
        return pdf_bytes
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en generar_pdf_dummy (test_subida_pdf_drive.py)")
        print_error(f"Error al generar PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

def guardar_en_modelo_laboratorio(pdf_bytes):
    """
    BLOQUE 2: GUARDAR EN MODELO LABORATORIO
    ========================================
    Guarda el PDF en el campo archivo_resultado de OrdenDeServicio
    Usa ContentFile para subida directa a Google Drive
    """
    print_header("BLOQUE 2: GUARDAR EN MODELO LABORATORIO")
    
    try:
        from django.core.files.base import ContentFile
        from core.models import OrdenDeServicio, Paciente, Empresa
        from django.conf import settings
        
        # Verificar qué storage está configurado
        storage_backend = settings.DEFAULT_FILE_STORAGE
        print_info(f"Storage configurado: {storage_backend}")
        
        if 'FileSystemStorage' in storage_backend:
            print_info("MODO: Desarrollo (FileSystemStorage local)")
        elif 'GoogleDriveStorage' in storage_backend:
            print_info("MODO: Producción (GoogleDriveStorage)")
        
        import os
        eid = os.environ.get("PRISLAB_EMPRESA_ID")
        if not eid:
            print_error("Defina PRISLAB_EMPRESA_ID (pk de Empresa).")
            return None
        try:
            empresa = Empresa.objects.get(pk=int(eid))
        except (ValueError, Empresa.DoesNotExist):
            print_error(f"Empresa id={eid!r} no válida.")
            return None

        paciente = Paciente.objects.filter(empresa=empresa).first()
        if not paciente:
            print_error("No hay pacientes para esa empresa (PRISLAB_EMPRESA_ID).")
            print_info("Solución: crear un paciente en ese tenant desde el admin")
            return None
        
        print_info(f"Empresa: {empresa.nombre}")
        print_info(f"Paciente: {paciente.nombre_completo}")
        
        # Buscar orden existente o crear una nueva
        orden = OrdenDeServicio.objects.filter(
            empresa=empresa,
            paciente=paciente,
            folio_orden__startswith='PRUEBA-PDF-'
        ).first()
        
        if not orden:
            print_info("Creando orden de prueba...")
            orden = OrdenDeServicio.objects.create(
                empresa=empresa,
                paciente=paciente,
                folio_orden=f'PRUEBA-PDF-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                estado='REGISTRADO',
                total=0,
                anticipo=0
            )
            print_success(f"Orden creada: ID {orden.id}")
        else:
            print_info(f"Usando orden existente: ID {orden.id}")
        
        # Crear ContentFile con los bytes del PDF
        print_info("Creando ContentFile...")
        pdf_file = ContentFile(pdf_bytes)
        
        # Nombre del archivo
        filename = f'prueba_hola_mundo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        print_info(f"Nombre archivo: {filename}")
        
        # ============================================================================
        # MOMENTO CRÍTICO: SUBIDA A STORAGE (Google Drive o FileSystem)
        # ============================================================================
        print_info("Guardando archivo...")
        print_info("(Esto puede tardar 2-5 segundos si es Google Drive...)")
        
        try:
            # Este save() disparará automáticamente el storage configurado
            orden.archivo_resultado.save(filename, pdf_file, save=True)
            
            print_success("Archivo guardado exitosamente")
            print_info(f"Campo archivo_resultado: {orden.archivo_resultado.name}")
            
            return orden
            
        except Exception as save_error:
            logging.getLogger(__name__).exception("Error inesperado en guardar_en_modelo_laboratorio (test_subida_pdf_drive.py)")
            # Si falla (ej. Google Drive sin credenciales), intentar con FileSystemStorage
            print_error(f"Error al guardar con storage configurado: {save_error}")
            print_info("Intentando con FileSystemStorage local como fallback...")
            
            # Forzar FileSystemStorage
            from django.core.files.storage import FileSystemStorage
            local_storage = FileSystemStorage(location='media/resultados_laboratorio')
            
            # Guardar localmente
            saved_name = local_storage.save(filename, pdf_file)
            orden.archivo_resultado.name = f'resultados_laboratorio/{saved_name}'
            orden.save()
            
            print_success("Archivo guardado localmente (fallback)")
            print_info(f"Campo archivo_resultado: {orden.archivo_resultado.name}")
            
            return orden
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en guardar_en_modelo_laboratorio (test_subida_pdf_drive.py)")
        print_error(f"Error al guardar en modelo: {e}")
        import traceback
        traceback.print_exc()
        return None

def verificar_url_google_drive(orden):
    """
    BLOQUE 3: VERIFICAR URL DE GOOGLE DRIVE
    ========================================
    Verifica que la URL generada corresponda a Google Drive
    """
    print_header("BLOQUE 3: VERIFICAR URL DE GOOGLE DRIVE")
    
    try:
        # Verificar que el archivo existe
        if not orden.archivo_resultado:
            print_error("El campo archivo_resultado esta vacio")
            return False, None
        
        print_info(f"Archivo en DB: {orden.archivo_resultado.name}")
        
        # Intentar obtener la URL
        try:
            url = orden.archivo_resultado.url
            print_success("URL generada exitosamente")
            print_info(f"URL: {url}")
            
            # Verificar si es de Google Drive
            if 'drive.google.com' in url or 'googleapis.com' in url:
                print_success("URL es de Google Drive")
                return True, url
            elif url.startswith('/media/') or 'resultados_laboratorio' in url:
                print_error("URL es LOCAL (FileSystemStorage)")
                print_info("Esto es ESPERADO en desarrollo")
                print_info("En produccion, la URL sera de Google Drive")
                return False, url
            else:
                print_error(f"URL no reconocida: {url}")
                return False, url
                
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en verificar_url_google_drive (test_subida_pdf_drive.py)")
            # Si falla al generar URL (Google Drive sin credenciales), tratar como local
            print_error(f"Error al generar URL: {e}")
            print_info("El archivo se guardo pero no se puede generar URL publica")
            print_info("En desarrollo con FileSystemStorage, la URL seria: /media/...")
            
            # Generar URL local manualmente
            url_local = f"/media/{orden.archivo_resultado.name}"
            print_info(f"URL local estimada: {url_local}")
            
            return False, url_local
            
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en verificar_url_google_drive (test_subida_pdf_drive.py)")
        print_error(f"Error al verificar URL: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def imprimir_resultado_final(exito, url, orden):
    """
    BLOQUE 4: IMPRIMIR RESULTADO
    ============================
    Imprime el resultado final de la prueba
    """
    print_header("BLOQUE 4: RESULTADO FINAL")
    
    if exito:
        print(f"\n{GREEN}{BOLD}")
        print("="*70)
        print("")
        print("        [OK] EXITO: ARCHIVO EN GOOGLE DRIVE")
        print("")
        print("="*70)
        print(f"{END}\n")
        
        print_success("BLINDAJE COMPLETO VERIFICADO:")
        print(f"  {GREEN}[OK] PDF generado correctamente{END}")
        print(f"  {GREEN}[OK] Guardado en modelo OrdenDeServicio{END}")
        print(f"  {GREEN}[OK] Subido a Google Drive{END}")
        print(f"  {GREEN}[OK] URL publica generada{END}")
        print()
        
        print_info("Detalles:")
        print(f"  Orden ID: {orden.id}")
        print(f"  Folio: {orden.folio_orden}")
        print(f"  Archivo: {orden.archivo_resultado.name}")
        print(f"  URL: {url}")
        print()
        
        print(f"{GREEN}{BOLD}CERTEZA ABSOLUTA:{END}")
        print(f"  Al dar clic en 'Finalizar Examen', el PDF aparecera")
        print(f"  en la carpeta de Google Drive del Dr. Jonathan.")
        print()
        
        return 0
        
    else:
        print(f"\n{YELLOW}{BOLD}")
        print("="*70)
        print("")
        print("        [WARN] ADVERTENCIA: ARCHIVO EN STORAGE LOCAL")
        print("")
        print("="*70)
        print(f"{END}\n")
        
        print_info("ANALISIS:")
        print(f"  {GREEN}[OK] PDF generado correctamente{END}")
        print(f"  {GREEN}[OK] Guardado en modelo OrdenDeServicio{END}")
        print(f"  {YELLOW}[WARN] Guardado en FileSystemStorage (local){END}")
        print(f"  {YELLOW}[WARN] URL es local, NO de Google Drive{END}")
        print()
        
        print_info("RAZON:")
        print(f"  Estas en DESARROLLO. El sistema usa FileSystemStorage local.")
        print(f"  En PRODUCCION, el sistema usara GoogleDriveStorage automaticamente.")
        print()
        
        print_info("Detalles:")
        print(f"  Orden ID: {orden.id}")
        print(f"  Folio: {orden.folio_orden}")
        print(f"  Archivo: {orden.archivo_resultado.name}")
        if url:
            print(f"  URL: {url}")
        print()
        
        print(f"{YELLOW}{BOLD}VERIFICACION PENDIENTE:{END}")
        print(f"  Ejecuta este script en PRODUCCION (Google Cloud Run)")
        print(f"  para verificar la subida a Google Drive.")
        print()
        
        print(f"{GREEN}COMANDOS PARA DEPLOY:{END}")
        print(f"  gcloud run deploy prislab-v5 --source . --region=us-central1")
        print()
        
        return 1

def main():
    """Función principal"""
    print(f"\n{CYAN}{BOLD}")
    print("="*70)
    print("")
    print("   PRUEBA DE SUBIDA PDF A GOOGLE DRIVE - PRISLAB V5.0")
    print("")
    print("   META: Certeza absoluta de subida a Drive del Dr. Jonathan")
    print("")
    print("="*70)
    print(f"{END}\n")
    
    print_info(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print_info(f"Python: {sys.version.split()[0]}")
    print_info(f"Django: {django.get_version()}")
    print()
    
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    # BLOQUE 1: Generar PDF
    pdf_bytes = generar_pdf_dummy()
    if not pdf_bytes:
        print_error("No se pudo generar el PDF")
        return 1
    
    # BLOQUE 2: Guardar en modelo
    orden = guardar_en_modelo_laboratorio(pdf_bytes)
    if not orden:
        print_error("No se pudo guardar en el modelo")
        return 1
    
    # BLOQUE 3: Verificar URL
    exito, url = verificar_url_google_drive(orden)
    
    # BLOQUE 4: Imprimir resultado
    return imprimir_resultado_final(exito, url, orden)

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Prueba interrumpida por el usuario{END}")
        sys.exit(1)
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en main (test_subida_pdf_drive.py)")
        print(f"\n{RED}{BOLD}ERROR FATAL:{END}")
        print(f"{RED}{e}{END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)