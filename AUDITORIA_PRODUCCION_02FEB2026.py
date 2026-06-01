#!/usr/bin/env python
"""
AUDITORÍA COMPLETA DEL SISTEMA PRISLAB V5.0 EN PRODUCCIÓN
==========================================================
Fecha: 02 de Febrero 2026
Objetivo: Verificar TODOS los módulos y detectar errores
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.db import connection
from django.apps import apps
import importlib

print("\n" + "=" * 80)
print("  AUDITORIA COMPLETA DEL SISTEMA PRISLAB V5.0")
print("=" * 80 + "\n")

# ==============================================================================
# 1. VERIFICAR BASE DE DATOS
# ==============================================================================
print("\n[1] VERIFICACION DE BASE DE DATOS")
print("-" * 80)

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()[0]
        print(f"[OK] Conexion a base de datos exitosa")
        print(f"     Version: {db_version}")
        
        # Contar tablas
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)
        num_tablas = cursor.fetchone()[0]
        print(f"[OK] Numero de tablas: {num_tablas}")
        
except Exception as e:
    print(f"[ERROR] Error en base de datos: {e}")

# ==============================================================================
# 2. VERIFICAR MODELOS PRINCIPALES
# ==============================================================================
print("\n[2] VERIFICACION DE MODELOS PRINCIPALES")
print("-" * 80)

modelos_criticos = [
    ('core', 'Usuario'),
    ('core', 'Empresa'),
    ('core', 'Sucursal'),
    ('core', 'Paciente'),
    ('core', 'Medico'),
    ('consultorio', 'ConsultaMedica'),
    ('consultorio', 'Cita'),
    ('laboratorio', 'Orden'),
    ('laboratorio', 'Estudio'),
    ('laboratorio', 'Parametro'),
    ('recepcion', 'PagoOrden'),
]

for app_label, model_name in modelos_criticos:
    try:
        Model = apps.get_model(app_label, model_name)
        count = Model.objects.count()
        print(f"[OK] {app_label}.{model_name}: {count} registros")
    except Exception as e:
        print(f"[ERROR] {app_label}.{model_name}: {e}")

# ==============================================================================
# 3. VERIFICAR IMPORTACIONES EN VISTAS
# ==============================================================================
print("\n[3] VERIFICACION DE VISTAS Y ERRORES DE IMPORTACION")
print("-" * 80)

vistas_criticas = [
    'core.views.contabilidad',
    'core.views.laboratorio',
    'core.views.entrega_resultados',
    'core.views.inventario',
    'consultorio.views',
    'consultorio.api_views',
    'laboratorio.views',
    'recepcion.views',
    'ia.views',
]

for vista_path in vistas_criticas:
    try:
        modulo = importlib.import_module(vista_path)
        print(f"[OK] {vista_path}: Importado correctamente")
    except Exception as e:
        print(f"[ERROR] {vista_path}: {str(e)[:100]}")

# ==============================================================================
# 4. VERIFICAR CAMPOS EN MODELOS (ERRORES COMUNES)
# ==============================================================================
print("\n[4] VERIFICACION DE CAMPOS EN MODELOS")
print("-" * 80)

# Verificar Orden tiene campo 'medico'
try:
    from laboratorio.models import Orden
    if hasattr(Orden, 'medico'):
        print(f"[OK] laboratorio.Orden tiene campo 'medico'")
    else:
        print(f"[ERROR] laboratorio.Orden NO tiene campo 'medico'")
        print(f"        Campos disponibles: {[f.name for f in Orden._meta.get_fields()]}")
except Exception as e:
    print(f"[ERROR] Error al verificar Orden: {e}")

# Verificar Medico tiene campo 'empresa'
try:
    from core.models import Medico
    if hasattr(Medico, 'empresa'):
        print(f"[OK] core.Medico tiene campo 'empresa'")
    else:
        print(f"[ERROR] core.Medico NO tiene campo 'empresa'")
        print(f"        Campos disponibles: {[f.name for f in Medico._meta.get_fields()]}")
except Exception as e:
    print(f"[ERROR] Error al verificar Medico: {e}")

# Verificar CatalogoCuenta existe
try:
    from contabilidad.models import CatalogoCuenta
    print(f"[OK] contabilidad.CatalogoCuenta existe")
    count = CatalogoCuenta.objects.count()
    print(f"     Total de cuentas: {count}")
except ImportError:
    print(f"[ERROR] contabilidad.CatalogoCuenta NO existe o no está importado")
except Exception as e:
    print(f"[ERROR] Error al verificar CatalogoCuenta: {e}")

# ==============================================================================
# 5. VERIFICAR CONFIGURACIONES CRÍTICAS
# ==============================================================================
print("\n[5] VERIFICACION DE CONFIGURACIONES")
print("-" * 80)

configs = [
    ('DEBUG', settings.DEBUG),
    ('SECRET_KEY configurado', bool(settings.SECRET_KEY)),
    ('DATABASES configurado', 'default' in settings.DATABASES),
    ('STATIC_ROOT', settings.STATIC_ROOT),
    ('MEDIA_URL', settings.MEDIA_URL),
]

for nombre, valor in configs:
    estado = "[OK]" if valor else "[ERROR]"
    print(f"{estado} {nombre}: {valor}")

# Verificar API keys
api_keys = [
    'GOOGLE_API_KEY',
    'GEMINI_API_KEY',
    'GOOGLE_CLOUD_PROJECT',
]

for key in api_keys:
    valor = getattr(settings, key, None) or os.environ.get(key)
    if valor:
        print(f"[OK] {key}: Configurado (longitud: {len(valor)})")
    else:
        print(f"[ERROR] {key}: NO configurado")

# ==============================================================================
# 6. VERIFICAR URLs PRINCIPALES
# ==============================================================================
print("\n[6] VERIFICACION DE URLs PRINCIPALES")
print("-" * 80)

from django.urls import reverse, NoReverseMatch

urls_criticas = [
    'login',
    'dashboard',
    'recepcion:registrar_paciente',
    'consultorio:nueva_consulta_simplificada',
    'laboratorio:recibir_orden',
    'laboratorio:captura_resultados',
    'contabilidad:dashboard',
    'ia:dashboard',
]

for url_name in urls_criticas:
    try:
        url = reverse(url_name)
        print(f"[OK] {url_name}: {url}")
    except NoReverseMatch:
        print(f"[ERROR] {url_name}: URL no encontrada")
    except Exception as e:
        print(f"[ERROR] {url_name}: {str(e)[:80]}")

# ==============================================================================
# 7. VERIFICAR MIGRACIONES PENDIENTES
# ==============================================================================
print("\n[7] VERIFICACION DE MIGRACIONES")
print("-" * 80)

from django.db.migrations.executor import MigrationExecutor
executor = MigrationExecutor(connection)
targets = executor.loader.graph.leaf_nodes()
plan = executor.migration_plan(targets)

if plan:
    print(f"[ERROR] Hay {len(plan)} migraciones pendientes:")
    for migration, _ in plan:
        print(f"        - {migration.app_label}.{migration.name}")
else:
    print(f"[OK] Todas las migraciones estan aplicadas")

# ==============================================================================
# 8. VERIFICAR SERVICIOS DE IA
# ==============================================================================
print("\n[8] VERIFICACION DE SERVICIOS DE IA")
print("-" * 80)

try:
    import google.generativeai as genai
    print(f"[OK] google-generativeai instalado")
    
    # Verificar configuración
    api_key = (
        getattr(settings, 'GOOGLE_API_KEY', None) or
        getattr(settings, 'GEMINI_API_KEY', None) or
        os.environ.get('GOOGLE_API_KEY') or
        os.environ.get('GEMINI_API_KEY')
    )
    
    if api_key:
        print(f"[OK] API key de Gemini configurada")
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("Di 'OK' si funcionas correctamente")
            if response.text:
                print(f"[OK] Gemini conectado y funcionando")
                print(f"     Respuesta: {response.text[:50]}")
        except Exception as e:
            print(f"[ERROR] Error al conectar con Gemini: {e}")
    else:
        print(f"[ERROR] API key de Gemini NO configurada")
        
except ImportError:
    print(f"[ERROR] google-generativeai NO esta instalado")

# ==============================================================================
# 9. RESUMEN DE ERRORES DETECTADOS
# ==============================================================================
print("\n" + "=" * 80)
print("  RESUMEN DE ERRORES DETECTADOS")
print("=" * 80 + "\n")

errores_detectados = []

# Error 1: CatalogoCuenta no importado en contabilidad.py
try:
    from contabilidad.models import CatalogoCuenta
except ImportError:
    errores_detectados.append({
        'modulo': 'contabilidad',
        'archivo': 'core/views/contabilidad.py',
        'error': 'NameError: name CatalogoCuenta is not defined',
        'solucion': 'Agregar: from contabilidad.models import CatalogoCuenta'
    })

# Error 2: Campo 'medico' no existe en Orden
try:
    from laboratorio.models import Orden
    if not hasattr(Orden, 'medico'):
        errores_detectados.append({
            'modulo': 'laboratorio',
            'archivo': 'core/views/laboratorio.py',
            'error': "Invalid field name 'medico' in select_related",
            'solucion': 'Cambiar .select_related("medico") por .select_related("medico_referente")'
        })
except:
    pass

# Error 3: Campo 'empresa' no existe en Medico
try:
    from core.models import Medico
    if not hasattr(Medico, 'empresa'):
        errores_detectados.append({
            'modulo': 'consultorio',
            'archivo': 'core/views/consultorio.py',
            'error': "Cannot resolve keyword 'empresa' into field in Medico",
            'solucion': 'El modelo Medico no tiene campo empresa, revisar filtros'
        })
except:
    pass

if errores_detectados:
    print(f"\nSe detectaron {len(errores_detectados)} errores criticos:\n")
    for i, error in enumerate(errores_detectados, 1):
        print(f"{i}. MODULO: {error['modulo']}")
        print(f"   ARCHIVO: {error['archivo']}")
        print(f"   ERROR: {error['error']}")
        print(f"   SOLUCION: {error['solucion']}")
        print()
else:
    print("\n[OK] No se detectaron errores criticos en la revision\n")

print("=" * 80)
print("  FIN DE LA AUDITORIA")
print("=" * 80 + "\n")
