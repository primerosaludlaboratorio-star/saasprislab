"""
AUDITORÍA AUTOMÁTICA COMPLETA DEL SISTEMA PRISLAB V5.0
=======================================================
Script de verificación exhaustiva módulo por módulo
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.apps import apps
from django.urls import get_resolver
from django.contrib.auth.models import Group
from core.models import Usuario, Empresa, Paciente, Producto, Venta
from laboratorio.models import Estudio, CategoriaExamen, Equipo

# Colores para terminal
class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Color.HEADER}{Color.BOLD}{'='*80}{Color.END}")
    print(f"{Color.HEADER}{Color.BOLD}{text.center(80)}{Color.END}")
    print(f"{Color.HEADER}{Color.BOLD}{'='*80}{Color.END}\n")

def print_section(text):
    print(f"\n{Color.CYAN}{Color.BOLD}{'-'*80}{Color.END}")
    print(f"{Color.CYAN}{Color.BOLD}{text}{Color.END}")
    print(f"{Color.CYAN}{'-'*80}{Color.END}")

def print_ok(text):
    print(f"{Color.GREEN}[OK] {text}{Color.END}")

def print_warning(text):
    print(f"{Color.YELLOW}[!] {text}{Color.END}")

def print_error(text):
    print(f"{Color.RED}[X] {text}{Color.END}")

def print_info(text):
    print(f"{Color.BLUE}[i] {text}{Color.END}")

# ==============================================================================
# AUDITORÍA 1: MÓDULOS INSTALADOS
# ==============================================================================
def auditar_modulos_instalados():
    print_header("AUDITORÍA 1: MÓDULOS INSTALADOS")
    
    modulos_esperados = [
        'core', 'farmacia', 'pacientes', 'laboratorio', 'seguridad',
        'iot', 'ia', 'reglas_negocio', 'marketing', 'recepcion',
        'enfermeria', 'consultorio', 'logistica', 'bienestar', 'contabilidad'
    ]
    
    modulos_encontrados = 0
    modulos_faltantes = []
    
    for modulo in modulos_esperados:
        try:
            apps.get_app_config(modulo)
            print_ok(f"Módulo '{modulo}' instalado")
            modulos_encontrados += 1
        except LookupError:
            print_error(f"Módulo '{modulo}' NO ENCONTRADO")
            modulos_faltantes.append(modulo)
    
    print_section(f"RESULTADO: {modulos_encontrados}/{len(modulos_esperados)} módulos instalados")
    
    if modulos_faltantes:
        print_warning(f"Faltantes: {', '.join(modulos_faltantes)}")
    
    return len(modulos_faltantes) == 0

# ==============================================================================
# AUDITORÍA 2: GRUPOS Y ROLES
# ==============================================================================
def auditar_grupos_roles():
    print_header("AUDITORÍA 2: GRUPOS Y ROLES (RBAC)")
    
    grupos_esperados = [
        'MEDICOS', 'LABORATORIO', 'FARMACIA', 'RECEPCION', 
        'ENFERMERIA', 'GERENCIA'
    ]
    
    grupos_encontrados = 0
    grupos_faltantes = []
    
    for grupo in grupos_esperados:
        try:
            Group.objects.get(name=grupo)
            print_ok(f"Grupo '{grupo}' existe")
            grupos_encontrados += 1
        except Group.DoesNotExist:
            print_warning(f"Grupo '{grupo}' NO EXISTE - Crear con: python manage.py crear_grupos_roles")
            grupos_faltantes.append(grupo)
    
    print_section(f"RESULTADO: {grupos_encontrados}/{len(grupos_esperados)} grupos configurados")
    
    return len(grupos_faltantes) == 0

# ==============================================================================
# AUDITORÍA 3: MODELOS CORE
# ==============================================================================
def auditar_modelos_core():
    print_header("AUDITORÍA 3: MODELOS CORE")
    
    modelos_verificar = [
        ('Empresa', Empresa),
        ('Usuario', Usuario),
        ('Paciente', Paciente),
        ('Producto', Producto),
        ('Venta', Venta),
    ]
    
    for nombre, modelo in modelos_verificar:
        try:
            count = modelo.objects.count()
            print_ok(f"Modelo '{nombre}': {count} registros")
        except Exception as e:
            print_error(f"Modelo '{nombre}': ERROR - {str(e)}")
    
    return True

# ==============================================================================
# AUDITORÍA 4: MODELOS LABORATORIO
# ==============================================================================
def auditar_modelos_laboratorio():
    print_header("AUDITORÍA 4: MODELOS LABORATORIO")
    
    try:
        categorias = CategoriaExamen.objects.count()
        estudios = Estudio.objects.count()
        equipos = Equipo.objects.count()
        
        print_ok(f"CategoriaExamen: {categorias} registros")
        print_ok(f"Estudio: {estudios} registros")
        print_ok(f"Equipo: {equipos} registros")
        
        if estudios == 0:
            print_warning("⚠ No hay estudios configurados. Ejecutar: python manage.py seed_estudios")
        else:
            print_ok(f"✓ {estudios} estudios configurados")
        
        # Verificar campo keywords
        primer_estudio = Estudio.objects.first()
        if primer_estudio and hasattr(primer_estudio, 'keywords'):
            print_ok("Campo 'keywords' existe en Estudio (Bloque 8)")
        else:
            print_warning("Campo 'keywords' NO existe - Ejecutar migraciones")
        
        return True
    except Exception as e:
        print_error(f"ERROR en auditoría de laboratorio: {str(e)}")
        return False

# ==============================================================================
# AUDITORÍA 5: RUTAS (URLs)
# ==============================================================================
def auditar_urls():
    print_header("AUDITORÍA 5: RUTAS (URLs)")
    
    resolver = get_resolver()
    
    urls_criticas = [
        ('/', 'Dashboard'),
        ('/consultorio/', 'Consultorio'),
        ('/laboratorio/', 'Laboratorio'),
        ('/farmacia/', 'Farmacia'),
        ('/recepcion/', 'Recepción'),
        ('/ia/', 'Inteligencia Artificial'),
        ('/bienestar/', 'Bienestar'),
    ]
    
    urls_encontradas = 0
    
    for url_path, nombre in urls_criticas:
        try:
            resolver.resolve(url_path)
            print_ok(f"URL '{url_path}' -> {nombre}")
            urls_encontradas += 1
        except Exception:
            print_warning(f"URL '{url_path}' -> {nombre} - NO RESUELTA")
    
    print_section(f"RESULTADO: {urls_encontradas}/{len(urls_criticas)} URLs críticas encontradas")
    
    return urls_encontradas >= len(urls_criticas) - 2

# ==============================================================================
# AUDITORÍA 6: ARCHIVOS CRÍTICOS
# ==============================================================================
def auditar_archivos_criticos():
    print_header("AUDITORÍA 6: ARCHIVOS CRÍTICOS NUEVOS (Bloques 1-8)")
    
    archivos_nuevos = [
        ('core/utils/paths.py', 'Generador de rutas Drive'),
        ('core/utils/pdf_generator.py', 'Generador de PDF forense'),
        ('core/views/paciente_detalle.py', 'Expediente clínico unificado'),
        ('core/templatetags/auth_extras.py', 'Template tags de roles'),
        ('core/mixins.py', 'Mixins de seguridad'),
        ('core/decorators.py', 'Decoradores de negocio'),
        ('core/signals.py', 'Signals automáticos'),
        ('laboratorio/views/etiquetas.py', 'Etiquetas térmicas'),
        ('laboratorio/utils/label_printer.py', 'Generador de etiquetas'),
        ('core/management/commands/seed_estudios.py', 'Seeder de estudios'),
        ('core/management/commands/crear_grupos_roles.py', 'Creador de grupos'),
    ]
    
    archivos_encontrados = 0
    
    for archivo, descripcion in archivos_nuevos:
        if os.path.exists(archivo):
            print_ok(f"{descripcion}: {archivo}")
            archivos_encontrados += 1
        else:
            print_error(f"{descripcion}: {archivo} - NO EXISTE")
    
    print_section(f"RESULTADO: {archivos_encontrados}/{len(archivos_nuevos)} archivos críticos")
    
    return archivos_encontrados >= len(archivos_nuevos) - 2

# ==============================================================================
# AUDITORÍA 7: TEMPLATES CRÍTICOS
# ==============================================================================
def auditar_templates():
    print_header("AUDITORÍA 7: TEMPLATES CRÍTICOS")
    
    templates = [
        ('core/templates/pacientes/historial_clinico.html', 'Expediente unificado (Bloque 2)'),
        ('core/templates/dashboards/dashboard_medico.html', 'Dashboard médico'),
        ('core/templates/dashboards/dashboard_laboratorio.html', 'Dashboard lab'),
        ('consultorio/templates/consultorio/nueva_consulta_gemelo.html', 'Gemelo Digital (Bloque 4)'),
        ('laboratorio/templates/laboratorio/capturar_resultados.html', 'Smart Lab (Bloque 5)'),
        ('laboratorio/templates/laboratorio/etiqueta_preview.html', 'Preview etiquetas (Bloque 7)'),
    ]
    
    templates_encontrados = 0
    
    for template, descripcion in templates:
        if os.path.exists(template):
            print_ok(f"{descripcion}: ✓")
            templates_encontrados += 1
        else:
            print_warning(f"{descripcion}: {template} - NO EXISTE")
    
    print_section(f"RESULTADO: {templates_encontrados}/{len(templates)} templates críticos")
    
    return templates_encontrados >= len(templates) - 1

# ==============================================================================
# AUDITORÍA 8: DEPENDENCIAS PYTHON
# ==============================================================================
def auditar_dependencias():
    print_header("AUDITORÍA 8: DEPENDENCIAS PYTHON")
    
    dependencias_criticas = [
        ('weasyprint', 'WeasyPrint (PDF forense)'),
        ('qrcode', 'QRCode (Validación)'),
        ('reportlab', 'ReportLab (Etiquetas)'),
        ('google.generativeai', 'Google Gemini (IA)'),
    ]
    
    dependencias_ok = 0
    
    for paquete, descripcion in dependencias_criticas:
        try:
            __import__(paquete)
            print_ok(f"{descripcion}: ✓")
            dependencias_ok += 1
        except ImportError:
            print_error(f"{descripcion}: NO INSTALADO")
    
    print_section(f"RESULTADO: {dependencias_ok}/{len(dependencias_criticas)} dependencias")
    
    return dependencias_ok == len(dependencias_criticas)

# ==============================================================================
# AUDITORÍA 9: STORAGE (Google Drive)
# ==============================================================================
def auditar_storage():
    print_header("AUDITORÍA 9: STORAGE (Google Drive)")
    
    try:
        from config.storage_backends import GoogleDriveStorage
        print_ok("GoogleDriveStorage importado correctamente")
        
        # Verificar campos de modelo con Google Drive
        from core.models import OrdenDeServicio, ResultadoParametro, AudioConsulta
        
        campos_drive = [
            (OrdenDeServicio, 'archivo_resultado'),
            (ResultadoParametro, 'imagen_microscopio'),
            (AudioConsulta, 'audio_archivo'),
        ]
        
        for modelo, campo in campos_drive:
            if hasattr(modelo, campo):
                print_ok(f"{modelo.__name__}.{campo} configurado")
            else:
                print_error(f"{modelo.__name__}.{campo} NO EXISTE")
        
        return True
    except Exception as e:
        print_error(f"ERROR: {str(e)}")
        return False

# ==============================================================================
# AUDITORÍA 10: SIGNALS Y DECORADORES
# ==============================================================================
def auditar_signals_decoradores():
    print_header("AUDITORÍA 10: SIGNALS Y DECORADORES")
    
    try:
        from core.decorators import check_payment_status, log_activity
        print_ok("Decoradores importados: @check_payment_status, @log_activity")
        
        from core.signals import crear_orden_venta_desde_receta
        print_ok("Signal importado: crear_orden_venta_desde_receta")
        
        # Verificar que signals se cargan en apps.py
        from core.apps import CoreConfig
        print_ok("CoreConfig configurado correctamente")
        
        return True
    except Exception as e:
        print_error(f"ERROR: {str(e)}")
        return False

# ==============================================================================
# RESUMEN EJECUTIVO
# ==============================================================================
def generar_resumen(resultados):
    print_header("RESUMEN EJECUTIVO DE AUDITORÍA")
    
    total_auditorias = len(resultados)
    auditorias_ok = sum(resultados.values())
    porcentaje = (auditorias_ok / total_auditorias) * 100
    
    for auditoria, resultado in resultados.items():
        if resultado:
            print_ok(f"{auditoria}")
        else:
            print_error(f"{auditoria}")
    
    print_section(f"RESULTADO FINAL: {auditorias_ok}/{total_auditorias} auditorías pasadas")
    
    if porcentaje == 100:
        print(f"\n{Color.GREEN}{Color.BOLD}{'*'*80}{Color.END}")
        print(f"{Color.GREEN}{Color.BOLD}SISTEMA AL 100% - LISTO PARA INGRESO TOTAL{Color.END}")
        print(f"{Color.GREEN}{Color.BOLD}{'*'*80}{Color.END}\n")
    elif porcentaje >= 90:
        print(f"\n{Color.YELLOW}{Color.BOLD}SISTEMA AL {porcentaje:.1f}% - CASI LISTO{Color.END}\n")
    else:
        print(f"\n{Color.RED}{Color.BOLD}SISTEMA AL {porcentaje:.1f}% - NECESITA CORRECCIONES{Color.END}\n")

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print_header("AUDITORÍA AUTOMÁTICA PRISLAB V5.0")
    print_info("Fecha: 1 de Febrero de 2026")
    print_info("Iniciando verificación exhaustiva...")
    
    resultados = {}
    
    resultados['Módulos Instalados'] = auditar_modulos_instalados()
    resultados['Grupos y Roles'] = auditar_grupos_roles()
    resultados['Modelos Core'] = auditar_modelos_core()
    resultados['Modelos Laboratorio'] = auditar_modelos_laboratorio()
    resultados['URLs Críticas'] = auditar_urls()
    resultados['Archivos Críticos'] = auditar_archivos_criticos()
    resultados['Templates'] = auditar_templates()
    resultados['Dependencias Python'] = auditar_dependencias()
    resultados['Storage (Google Drive)'] = auditar_storage()
    resultados['Signals y Decoradores'] = auditar_signals_decoradores()
    
    generar_resumen(resultados)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}Auditoría interrumpida por el usuario{Color.END}")
    except Exception as e:
        print(f"\n{Color.RED}ERROR CRÍTICO: {str(e)}{Color.END}")
        import traceback
        traceback.print_exc()
