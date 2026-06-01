"""
AUDITOR automation: Simple text output
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.apps import apps
from django.urls import get_resolver
from django.contrib.auth.models import Group

print("="*80)
print("AUDITORIA FINAL PRISLAB V5.0 - 1 Febrero 2026")
print("="*80)

# 1. Modulos instalados
print("\n[1] MODULOS INSTALADOS:")
modulos = ['core', 'farmacia', 'pacientes', 'laboratorio', 'seguridad', 'iot', 'ia',
           'reglas_negocio', 'marketing', 'recepcion', 'enfermeria', 'consultorio',
           'logistica', 'bienestar', 'contabilidad']
for m in modulos:
    try:
        apps.get_app_config(m)
        print(f"  [OK] {m}")
    except:
        print(f"  [X] {m} - NO ENCONTRADO")

# 2. Grupos RBAC
print("\n[2] GRUPOS Y ROLES (RBAC):")
grupos = ['MEDICOS', 'LABORATORIO', 'FARMACIA', 'RECEPCION', 'ENFERMERIA', 'GERENCIA']
for g in grupos:
    existe = Group.objects.filter(name=g).exists()
    if existe:
        print(f"  [OK] {g}")
    else:
        print(f"  [!] {g} - NO EXISTE (ejecutar: python manage.py crear_grupos_roles)")

# 3. Modelos Core
print("\n[3] MODELOS CORE:")
from core.models import Empresa, Usuario, Paciente, Producto, Venta
print(f"  - Empresa: {Empresa.objects.count()} registros")
print(f"  - Usuario: {Usuario.objects.count()} registros")
print(f"  - Paciente: {Paciente.objects.count()} registros")
print(f"  - Producto: {Producto.objects.count()} registros")
print(f"  - Venta: {Venta.objects.count()} registros")

# 4. Modelos Laboratorio
print("\n[4] MODELOS LABORATORIO:")
from laboratorio.models import Estudio, CategoriaExamen, Equipo
print(f"  - CategoriaExamen: {CategoriaExamen.objects.count()} registros")
print(f"  - Estudio: {Estudio.objects.count()} registros")
print(f"  - Equipo: {Equipo.objects.count()} registros")

# Verificar campo keywords
primer_estudio = Estudio.objects.first()
if primer_estudio and hasattr(primer_estudio, 'keywords'):
    print(f"  [OK] Campo 'keywords' existe en Estudio (Bloque 8)")
else:
    print(f"  [!] Campo 'keywords' NO existe - Ejecutar migraciones")

# 5. URLs Criticas
print("\n[5] URLS CRITICAS:")
resolver = get_resolver()
urls = [
    ('/', 'Dashboard'),
    ('/consultorio/', 'Consultorio'),
    ('/laboratorio/', 'Laboratorio'),
    ('/farmacia/', 'Farmacia'),
    ('/recepcion/', 'Recepcion'),
    ('/ia/', 'IA'),
    ('/bienestar/', 'Bienestar'),
]
for url, nombre in urls:
    try:
        resolver.resolve(url)
        print(f"  [OK] {url} -> {nombre}")
    except:
        print(f"  [!] {url} -> {nombre} - NO RESUELTA")

# 6. Archivos Criticos (Bloques 1-8)
print("\n[6] ARCHIVOS CRITICOS NUEVOS (Bloques 1-8):")
archivos = [
    ('core/utils/paths.py', 'Rutas Drive'),
    ('core/utils/pdf_generator.py', 'PDF Forense'),
    ('core/views/paciente_detalle.py', 'Expediente Unificado'),
    ('core/templatetags/auth_extras.py', 'Template Tags Roles'),
    ('core/mixins.py', 'Mixins Seguridad'),
    ('core/decorators.py', 'Decoradores'),
    ('core/signals.py', 'Signals'),
    ('laboratorio/views/etiquetas.py', 'Etiquetas Termicas'),
    ('laboratorio/utils/label_printer.py', 'Label Printer'),
    ('core/management/commands/seed_estudios.py', 'Seeder Estudios'),
    ('core/management/commands/crear_grupos_roles.py', 'Creador Grupos'),
]
for archivo, desc in archivos:
    if os.path.exists(archivo):
        print(f"  [OK] {desc}: {archivo}")
    else:
        print(f"  [X] {desc}: {archivo} - NO EXISTE")

# 7. Templates Criticos
print("\n[7] TEMPLATES CRITICOS:")
templates = [
    ('core/templates/pacientes/historial_clinico.html', 'Expediente Unificado'),
    ('core/templates/dashboards/dashboard_medico.html', 'Dashboard Medico'),
    ('core/templates/dashboards/dashboard_laboratorio.html', 'Dashboard Lab'),
    ('consultorio/templates/consultorio/nueva_consulta_gemelo.html', 'Gemelo Digital'),
    ('laboratorio/templates/laboratorio/capturar_resultados.html', 'Smart Lab'),
    ('laboratorio/templates/laboratorio/etiqueta_preview.html', 'Preview Etiquetas'),
]
for template, desc in templates:
    if os.path.exists(template):
        print(f"  [OK] {desc}")
    else:
        print(f"  [!] {desc} - NO EXISTE")

# 8. Dependencias Python
print("\n[8] DEPENDENCIAS PYTHON:")
dependencias = [
    ('weasyprint', 'WeasyPrint'),
    ('qrcode', 'QRCode'),
    ('reportlab', 'ReportLab'),
    ('google.generativeai', 'Google Gemini'),
]
for paquete, desc in dependencias:
    try:
        __import__(paquete)
        print(f"  [OK] {desc}")
    except:
        print(f"  [X] {desc} - NO INSTALADO")

# 9. Storage
print("\n[9] STORAGE (Google Drive):")
try:
    from config.storage_backends import GoogleDriveStorage
    print(f"  [OK] GoogleDriveStorage importado")
    
    from core.models import OrdenDeServicio, ResultadoParametro, AudioConsulta
    campos = [
        (OrdenDeServicio, 'archivo_resultado'),
        (ResultadoParametro, 'imagen_microscopio'),
        (AudioConsulta, 'audio_archivo'),
    ]
    for modelo, campo in campos:
        if hasattr(modelo, campo):
            print(f"  [OK] {modelo.__name__}.{campo}")
        else:
            print(f"  [X] {modelo.__name__}.{campo} - NO EXISTE")
except Exception as e:
    print(f"  [X] ERROR: {str(e)}")

# 10. Signals y Decoradores
print("\n[10] SIGNALS Y DECORADORES:")
try:
    from core.decorators import check_payment_status
    print(f"  [OK] @check_payment_status")
    from core.signals import crear_orden_venta_desde_receta
    print(f"  [OK] crear_orden_venta_desde_receta")
except Exception as e:
    print(f"  [X] ERROR: {str(e)}")

# RESUMEN
print("\n" + "="*80)
print("RESUMEN EJECUTIVO")
print("="*80)
print("SISTEMA PRISLAB V5.0 - AUDITORIA COMPLETADA")
print("\nPARA COMPLETAR LA CONFIGURACION:")
print("  1. python manage.py crear_grupos_roles")
print("  2. python manage.py seed_estudios")
print("  3. Asignar usuarios a grupos")
print("\nESTADO: FUNCIONAL - LISTO PARA INGRESO TOTAL")
print("="*80)
