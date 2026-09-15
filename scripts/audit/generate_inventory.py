#!/usr/bin/env python
"""
PRISLAB Audit Inventory Generator

Genera INVENTARIO.json mapeando todas las aplicaciones Django, rutas, modelos, 
migraciones, tareas Celery, comandos, plantillas y dependencias.

Uso:
    python scripts/audit/generate_inventory.py --output audit/INVENTARIO.json

Salida:
    audit/INVENTARIO.json
    audit/INVENTARIO.csv
"""

import json
import csv
import os
import sys
import importlib
import inspect
from pathlib import Path
from datetime import datetime
import re


def get_django_apps():
    """Extrae todas las aplicaciones Django instaladas."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    import django
    django.setup()
    from django.conf import settings
    
    apps = []
    for app_config in settings.INSTALLED_APPS:
        app_name = app_config.split('.')[-1] if '.' in app_config else app_config
        
        # Obtener ruta de la app
        try:
            app_module = importlib.import_module(app_name)
            app_path = Path(app_module.__file__).parent
        except:
            app_path = None
        
        apps.append({
            "name": app_name,
            "label": app_name,
            "path": str(app_path) if app_path else "N/A",
            "type": "django_app",
            "status": "installed",
        })
    
    return apps


def get_models(app_name):
    """Extrae todos los modelos de una aplicación."""
    try:
        from django.apps import apps
        app_config = apps.get_app_config(app_name)
        models = []
        
        for model in app_config.get_models():
            # Obtener campos
            fields = [f.name for f in model._meta.get_fields()]
            
            # Verificar si tiene filtro de tenant
            has_tenant_filter = any('empresa' in str(f) or 'sucursal' in str(f) for f in fields)
            
            models.append({
                "model": model.__name__,
                "app": app_name,
                "fields": fields,
                "field_count": len(fields),
                "has_tenant_filter": has_tenant_filter,
                "table": model._meta.db_table,
            })
        
        return models
    except Exception as e:
        return []


def get_views(app_name):
    """Extrae vistas de una aplicación."""
    views = []
    
    try:
        views_module = importlib.import_module(f"{app_name}.views")
        
        for name, obj in inspect.getmembers(views_module):
            if inspect.isclass(obj) and name.endswith('View'):
                # Es una Class-Based View
                views.append({
                    "name": name,
                    "type": "CBV",
                    "methods": [m for m in dir(obj) if not m.startswith('_')],
                })
            elif inspect.isfunction(obj) and not name.startswith('_'):
                # Es una Function-Based View
                views.append({
                    "name": name,
                    "type": "FBV",
                    "file": inspect.getfile(obj),
                })
    except:
        pass
    
    return views


def get_migrations(app_name):
    """Extrae migraciones de una aplicación."""
    migrations = []
    migrations_path = Path(f"{app_name}/migrations")
    
    if migrations_path.exists():
        for migration_file in sorted(migrations_path.glob("*.py")):
            if migration_file.name != "__init__.py":
                migrations.append({
                    "name": migration_file.stem,
                    "file": str(migration_file),
                })
    
    return migrations


def get_urls():
    """Extrae todas las rutas URL de URLconf."""
    urls = []
    
    try:
        from django.conf import settings
        from django.urls import get_resolver
        
        resolver = get_resolver()
        
        for pattern in resolver.url_patterns:
            pattern_str = str(pattern.pattern)
            name = pattern.name or "N/A"
            callback = str(pattern.callback) if hasattr(pattern, 'callback') else "N/A"
            
            urls.append({
                "path": pattern_str,
                "name": name,
                "callback": callback[:80],  # Limitar longitud
                "method": "N/A",
            })
    except Exception as e:
        pass
    
    return urls


def get_celery_tasks():
    """Extrae tareas Celery definidas."""
    tasks = []
    
    # Buscar archivos tasks.py en apps
    for app_path in Path('.').glob('*/tasks.py'):
        try:
            app_name = app_path.parent.name
            tasks_module = importlib.import_module(f"{app_name}.tasks")
            
            for name, obj in inspect.getmembers(tasks_module):
                if hasattr(obj, 'delay') or hasattr(obj, 'apply_async'):
                    tasks.append({
                        "name": name,
                        "app": app_name,
                        "queue": getattr(obj, 'queue', 'default'),
                    })
        except:
            pass
    
    return tasks


def get_management_commands():
    """Extrae comandos de manage.py."""
    commands = []
    
    for app_path in Path('.').glob('*/management/commands'):
        if app_path.exists():
            app_name = app_path.parent.parent.name
            
            for cmd_file in app_path.glob('*.py'):
                if cmd_file.name != "__init__.py":
                    commands.append({
                        "name": cmd_file.stem,
                        "app": app_name,
                        "file": str(cmd_file),
                    })
    
    return commands


def get_dependencies():
    """Extrae dependencias del requirements.lock."""
    dependencies = []
    
    if Path('requirements.lock').exists():
        with open('requirements.lock', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '==' in line:
                    pkg_name, version = line.split('==')[:2]
                    dependencies.append({
                        "name": pkg_name.strip(),
                        "version": version.strip(),
                        "type": "python",
                    })
    
    return dependencies


def generate_inventory(output_json="audit/INVENTARIO.json", output_csv="audit/INVENTARIO.csv"):
    """Genera archivo INVENTARIO completo."""
    
    print("🔍 Generando INVENTARIO...")
    
    # Obtener apps
    apps = get_django_apps()
    print(f"✅ {len(apps)} aplicaciones Django encontradas")
    
    inventory = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0",
        "scope": "Django apps, models, views, URLs, migrations, tasks, commands, dependencies",
        
        "applications": apps,
        "models": {},
        "views": {},
        "migrations": {},
        "urls": get_urls(),
        "celery_tasks": get_celery_tasks(),
        "management_commands": get_management_commands(),
        "dependencies": get_dependencies()[:50],  # Top 50 para brevedad
    }
    
    # Por cada app, obtener modelos, vistas, migraciones
    for app in apps:
        app_name = app['name']
        
        # Modelos
        models = get_models(app_name)
        if models:
            inventory["models"][app_name] = models
            print(f"  ├─ {app_name}: {len(models)} modelos")
        
        # Vistas
        views = get_views(app_name)
        if views:
            inventory["views"][app_name] = views
            print(f"  ├─ {app_name}: {len(views)} vistas")
        
        # Migraciones
        migrations = get_migrations(app_name)
        if migrations:
            inventory["migrations"][app_name] = migrations
            print(f"  └─ {app_name}: {len(migrations)} migraciones")
    
    # Estadísticas
    inventory["stats"] = {
        "total_apps": len(apps),
        "total_models": sum(len(m) for m in inventory["models"].values()),
        "total_views": sum(len(v) for v in inventory["views"].values()),
        "total_urls": len(inventory["urls"]),
        "total_migrations": sum(len(m) for m in inventory["migrations"].values()),
        "total_tasks": len(inventory["celery_tasks"]),
        "total_commands": len(inventory["management_commands"]),
        "total_dependencies": len(inventory["dependencies"]),
    }
    
    # Crear directorio si no existe
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    
    # Escribir JSON
    with open(output_json, 'w') as f:
        json.dump(inventory, f, indent=2)
    
    print(f"\n✅ INVENTARIO.json generado: {output_json}")
    
    # Escribir CSV (resumen de modelos)
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['App', 'Model', 'Fields', 'Tenant Filter', 'Table'])
        
        for app_name, models in inventory["models"].items():
            for model in models:
                writer.writerow([
                    app_name,
                    model['model'],
                    len(model['fields']),
                    "✓" if model['has_tenant_filter'] else "✗",
                    model['table'],
                ])
    
    print(f"✅ INVENTARIO.csv generado: {output_csv}")
    
    # Imprimir estadísticas
    print("\n📊 Estadísticas:")
    for key, value in inventory["stats"].items():
        print(f"   {key}: {value}")
    
    return inventory


if __name__ == "__main__":
    try:
        inventory = generate_inventory()
        print(f"\n📦 Inventario completado exitosamente")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
