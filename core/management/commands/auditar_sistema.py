"""
Script de Auditoría Completa del Sistema Prislab
Verifica todas las funcionalidades implementadas y su estado.

Uso:
    python manage.py auditar_sistema
"""
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings
from django.db import connection
from django.urls import get_resolver
from django.utils import timezone
from datetime import timedelta
import os
import sys


class Command(BaseCommand):
    help = 'Audita el estado completo del sistema Prislab'

    def handle(self, *args, **options):
        """Ejecuta auditoría completa."""
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('AUDITORIA COMPLETA DEL SISTEMA PRISLAB'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        resultados = {
            'modelos': self._auditar_modelos(),
            'vistas': self._auditar_vistas(),
            'urls': self._auditar_urls(),
            'migraciones': self._auditar_migraciones(),
            'dependencias': self._auditar_dependencias(),
            'archivos_media': self._auditar_archivos_media(),
            'funcionalidades': self._auditar_funcionalidades(),
        }
        
        self._generar_reporte(resultados)

    def _auditar_modelos(self):
        """Audita todos los modelos del sistema."""
        self.stdout.write(self.style.WARNING('AUDITANDO MODELOS...\n'))
        
        modelos = {}
        apps_config = apps.get_app_configs()
        
        for app_config in apps_config:
            app_name = app_config.name
            if app_name in ['core', 'laboratorio', 'pacientes', 'seguridad', 'iot', 'ia']:
                try:
                    app_models = app_config.get_models()
                    modelos[app_name] = []
                    
                    for model in app_models:
                        nombre = model.__name__
                        campos = len([f for f in model._meta.get_fields()])
                        registros = model.objects.count()
                        
                        modelos[app_name].append({
                            'nombre': nombre,
                            'campos': campos,
                            'registros': registros
                        })
                        
                        self.stdout.write(f'   [OK] {app_name}.{nombre} - {campos} campos, {registros} registros')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   [ERROR] Error en {app_name}: {str(e)}'))
        
        return modelos

    def _auditar_vistas(self):
        """Audita todas las vistas del sistema."""
        self.stdout.write(self.style.WARNING('\nAUDITANDO VISTAS...\n'))
        
        vistas = {}
        apps_config = apps.get_app_configs()
        
        # Buscar vistas en módulos core.views
        try:
            from core import views
            modulos_vistas = [
                ('farmacia', views.farmacia),
                ('laboratorio', views.laboratorio),
                ('pacientes', views.pacientes),
                ('medico', views.medico),
                ('rh', views.rh),
                ('director', views.director),
                ('ia', views.ia),
            ]
            
            for modulo, modulo_views in modulos_vistas:
                vistas[modulo] = []
                try:
                    for nombre in dir(modulo_views):
                        if not nombre.startswith('_') and callable(getattr(modulo_views, nombre)):
                            vistas[modulo].append(nombre)
                            self.stdout.write(f'   [OK] {modulo}.{nombre}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   [ERROR] Error en {modulo}: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   [ERROR] Error al cargar vistas: {str(e)}'))
        
        return vistas

    def _auditar_urls(self):
        """Audita todas las URLs del sistema."""
        self.stdout.write(self.style.WARNING('\nAUDITANDO URLs...\n'))
        
        urls = []
        try:
            resolver = get_resolver()
            
            def extraer_urls(url_patterns, prefijo=''):
                for pattern in url_patterns:
                    if hasattr(pattern, 'url_patterns'):
                        extraer_urls(pattern.url_patterns, prefijo + str(pattern.pattern))
                    else:
                        nombre = pattern.name or 'sin-nombre'
                        ruta = prefijo + str(pattern.pattern)
                        urls.append({
                            'ruta': ruta,
                            'nombre': nombre
                        })
                        self.stdout.write(f'   [OK] {ruta} -> {nombre}')
            
            extraer_urls(resolver.url_patterns)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   [ERROR] Error al auditar URLs: {str(e)}'))
        
        return urls

    def _auditar_migraciones(self):
        """Audita el estado de las migraciones."""
        self.stdout.write(self.style.WARNING('\nAUDITANDO MIGRACIONES...\n'))
        
        migraciones = {}
        apps_config = apps.get_app_configs()
        
        for app_config in apps_config:
            app_name = app_config.name
            if app_name in ['core', 'laboratorio', 'pacientes', 'seguridad', 'iot', 'ia']:
                try:
                    # Verificar directorio de migraciones
                    migraciones_dir = os.path.join(app_config.path, 'migrations')
                    if os.path.exists(migraciones_dir):
                        archivos_migracion = [f for f in os.listdir(migraciones_dir) if f.endswith('.py') and f != '__init__.py']
                        migraciones[app_name] = len(archivos_migracion)
                        self.stdout.write(f'   [OK] {app_name}: {len(archivos_migracion)} migraciones')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   [ERROR] Error en {app_name}: {str(e)}'))
        
        return migraciones

    def _auditar_dependencias(self):
        """Audita las dependencias instaladas."""
        self.stdout.write(self.style.WARNING('\nAUDITANDO DEPENDENCIAS...\n'))
        
        dependencias_requeridas = [
            'Django', 'qrcode', 'reportlab', 'cryptography', 'pillow',
            'pandas', 'openpyxl', 'selenium', 'psycopg2-binary'
        ]
        
        dependencias = {}
        
        for dep in dependencias_requeridas:
            try:
                if dep == 'psycopg2-binary':
                    import psycopg2
                    version = psycopg2.__version__
                    dependencias[dep] = {'instalada': True, 'version': version}
                elif dep == 'pillow':
                    # Pillow se importa como PIL, no como "pillow"
                    import PIL
                    version = getattr(PIL, '__version__', 'N/A')
                    dependencias[dep] = {'instalada': True, 'version': version}
                else:
                    mod = __import__(dep.lower())
                    version = getattr(mod, '__version__', 'N/A')
                    dependencias[dep] = {'instalada': True, 'version': version}
                
                self.stdout.write(f'   [OK] {dep}: {version}')
            except ImportError:
                dependencias[dep] = {'instalada': False, 'version': None}
                self.stdout.write(self.style.ERROR(f'   [ERROR] {dep}: NO INSTALADA'))
        
        return dependencias

    def _auditar_archivos_media(self):
        """Audita los directorios de archivos multimedia."""
        self.stdout.write(self.style.WARNING('\nAUDITANDO ARCHIVOS MEDIA...\n'))
        
        archivos_media = {}
        media_root = settings.MEDIA_ROOT
        
        directorios_esperados = [
            'logos',
            'firmas',
            'firmas_recetas',
            'pdfs',
            'backups'
        ]
        
        for dir_name in directorios_esperados:
            dir_path = os.path.join(media_root, dir_name)
            if os.path.exists(dir_path):
                archivos = len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
                tamanio = sum(os.path.getsize(os.path.join(dir_path, f)) 
                             for f in os.listdir(dir_path) 
                             if os.path.isfile(os.path.join(dir_path, f)))
                tamanio_mb = tamanio / (1024 * 1024)
                
                archivos_media[dir_name] = {
                    'existe': True,
                    'archivos': archivos,
                    'tamanio_mb': round(tamanio_mb, 2)
                }
                self.stdout.write(f'   [OK] {dir_name}: {archivos} archivos ({tamanio_mb:.2f} MB)')
            else:
                archivos_media[dir_name] = {'existe': False, 'archivos': 0, 'tamanio_mb': 0}
                self.stdout.write(self.style.WARNING(f'   [WARN] {dir_name}: No existe'))
        
        return archivos_media

    def _auditar_funcionalidades(self):
        """Audita funcionalidades específicas implementadas."""
        self.stdout.write(self.style.WARNING('\nAUDITANDO FUNCIONALIDADES...\n'))
        
        funcionalidades = {}
        
        # 1. Multi-Tenant
        try:
            from core.models import Empresa, Sucursal, ConfiguracionModulos
            empresas_count = Empresa.objects.count()
            sucursales_count = Sucursal.objects.count()
            funcionalidades['multi_tenant'] = {
                'implementado': True,
                'empresas': empresas_count,
                'sucursales': sucursales_count
            }
            self.stdout.write(f'   [OK] Multi-Tenant: {empresas_count} empresas, {sucursales_count} sucursales')
        except Exception as e:
            funcionalidades['multi_tenant'] = {'implementado': False, 'error': str(e)}
            self.stdout.write(self.style.ERROR(f'   [ERROR] Multi-Tenant: {str(e)}'))
        
        # 2. FEFO
        try:
            from core.models import Lote
            lotes_count = Lote.objects.count()
            lotes_proximos = Lote.objects.filter(
                fecha_caducidad__lte=timezone.now().date() + timedelta(days=30)
            ).count()
            funcionalidades['fefo'] = {
                'implementado': True,
                'lotes': lotes_count,
                'lotes_proximos_vencer': lotes_proximos
            }
            self.stdout.write(f'   [OK] FEFO: {lotes_count} lotes, {lotes_proximos} proximos a vencer')
        except Exception as e:
            funcionalidades['fefo'] = {'implementado': False, 'error': str(e)}
            self.stdout.write(self.style.ERROR(f'   [ERROR] FEFO: {str(e)}'))
        
        # 3. Auditoría Forense
        try:
            from core.models import AuditLog
            logs_count = AuditLog.objects.count()
            logs_recientes = AuditLog.objects.filter(
                fecha_cierta__gte=timezone.now() - timedelta(days=7)
            ).count()
            funcionalidades['auditoria_forense'] = {
                'implementado': True,
                'logs_totales': logs_count,
                'logs_ultimos_7_dias': logs_recientes
            }
            self.stdout.write(f'   [OK] Auditoria Forense: {logs_count} logs totales, {logs_recientes} ultimos 7 dias')
        except Exception as e:
            funcionalidades['auditoria_forense'] = {'implementado': False, 'error': str(e)}
            self.stdout.write(self.style.ERROR(f'   [ERROR] Auditoria Forense: {str(e)}'))
        
        # 4. Triple Llave
        try:
            from core.models import OrdenDeServicio
            ordenes_count = OrdenDeServicio.objects.count()
            ordenes_validadas = OrdenDeServicio.objects.filter(
                estado__in=('RESULTADOS_LISTOS', 'ENTREGADO')
            ).count()
            funcionalidades['triple_llave'] = {
                'implementado': True,
                'ordenes': ordenes_count,
                'ordenes_validadas': ordenes_validadas
            }
            self.stdout.write(f'   [OK] Triple Llave (ODS): {ordenes_count} ordenes, {ordenes_validadas} con resultados listos/entregado')
        except Exception as e:
            funcionalidades['triple_llave'] = {'implementado': False, 'error': str(e)}
            self.stdout.write(self.style.ERROR(f'   [ERROR] Triple Llave: {str(e)}'))
        
        # 5. Perfiles de Laboratorio
        try:
            from laboratorio.models import PerfilLaboratorio
            perfiles_count = PerfilLaboratorio.objects.count()
            funcionalidades['perfiles_laboratorio'] = {
                'implementado': True,
                'perfiles': perfiles_count
            }
            self.stdout.write(f'   [OK] Perfiles Laboratorio: {perfiles_count} perfiles')
        except Exception as e:
            funcionalidades['perfiles_laboratorio'] = {'implementado': False, 'error': str(e)}
            self.stdout.write(self.style.ERROR(f'   [ERROR] Perfiles Laboratorio: {str(e)}'))
        
        # 6. Backup Nocturno
        try:
            from core.models import BackupRegistro
            backups_count = BackupRegistro.objects.count()
            backups_exitosos = BackupRegistro.objects.filter(estado='COMPLETADO').count()
            funcionalidades['backup_nocturno'] = {
                'implementado': True,
                'backups': backups_count,
                'backups_exitosos': backups_exitosos
            }
            self.stdout.write(f'   [OK] Backup Nocturno: {backups_count} backups, {backups_exitosos} exitosos')
        except Exception as e:
            funcionalidades['backup_nocturno'] = {'implementado': False, 'error': str(e)}
            self.stdout.write(self.style.ERROR(f'   [ERROR] Backup Nocturno: {str(e)}'))
        
        # 7. Receta Digital 4.0
        try:
            from core.models import Receta
            recetas_count = Receta.objects.count()
            recetas_con_qr = Receta.objects.filter(qr_verificacion__isnull=False).count()
            funcionalidades['receta_digital'] = {
                'implementado': True,
                'recetas': recetas_count,
                'recetas_con_qr': recetas_con_qr
            }
            self.stdout.write(f'   [OK] Receta Digital 4.0: {recetas_count} recetas, {recetas_con_qr} con QR')
        except Exception as e:
            funcionalidades['receta_digital'] = {'implementado': False, 'error': str(e)}
            self.stdout.write(self.style.ERROR(f'   [ERROR] Receta Digital 4.0: {str(e)}'))
        
        # 8. RH - Bitácora 39-A
        try:
            from core.models import Bitacora39A
            evaluaciones_count = Bitacora39A.objects.count()
            funcionalidades['rh_39a'] = {
                'implementado': True,
                'evaluaciones': evaluaciones_count
            }
            self.stdout.write(f'   [OK] RH - Bitacora 39-A: {evaluaciones_count} evaluaciones')
        except Exception as e:
            funcionalidades['rh_39a'] = {'implementado': False, 'error': str(e)}
            self.stdout.write(self.style.ERROR(f'   [ERROR] RH - Bitacora 39-A: {str(e)}'))
        
        return funcionalidades

    def _generar_reporte(self, resultados):
        """Genera reporte final consolidado."""
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('REPORTE FINAL DE AUDITORIA'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        # Resumen de Modelos
        total_modelos = sum(len(models) for models in resultados['modelos'].values())
        total_registros = sum(
            sum(m['registros'] for m in models)
            for models in resultados['modelos'].values()
        )
        self.stdout.write(f'MODELOS: {total_modelos} modelos, {total_registros:,} registros totales')
        
        # Resumen de Vistas
        total_vistas = sum(len(vistas) for vistas in resultados['vistas'].values())
        self.stdout.write(f'VISTAS: {total_vistas} vistas implementadas')
        
        # Resumen de URLs
        total_urls = len(resultados['urls'])
        self.stdout.write(f'URLS: {total_urls} rutas configuradas')
        
        # Resumen de Migraciones
        total_migraciones = sum(resultados['migraciones'].values())
        self.stdout.write(f'MIGRACIONES: {total_migraciones} archivos de migracion')
        
        # Resumen de Dependencias
        dependencias_instaladas = sum(1 for d in resultados['dependencias'].values() if d.get('instalada'))
        total_dependencias = len(resultados['dependencias'])
        self.stdout.write(f'DEPENDENCIAS: {dependencias_instaladas}/{total_dependencias} instaladas')
        
        # Resumen de Media
        total_archivos_media = sum(dir_info.get('archivos', 0) for dir_info in resultados['archivos_media'].values())
        total_tamanio_mb = sum(dir_info.get('tamanio_mb', 0) for dir_info in resultados['archivos_media'].values())
        self.stdout.write(f'MEDIA: {total_archivos_media} archivos ({total_tamanio_mb:.2f} MB)')
        
        # Resumen de Funcionalidades
        func_implementadas = sum(1 for f in resultados['funcionalidades'].values() if f.get('implementado'))
        total_func = len(resultados['funcionalidades'])
        self.stdout.write(f'FUNCIONALIDADES: {func_implementadas}/{total_func} implementadas\n')
        
        # Estado del Sistema
        self.stdout.write(self.style.SUCCESS('='*80))
        if func_implementadas == total_func and dependencias_instaladas == total_dependencias:
            self.stdout.write(self.style.SUCCESS('ESTADO DEL SISTEMA: OPTIMO'))
        elif func_implementadas >= total_func * 0.8:
            self.stdout.write(self.style.WARNING('ESTADO DEL SISTEMA: BUENO (Revisar funcionalidades faltantes)'))
        else:
            self.stdout.write(self.style.ERROR('ESTADO DEL SISTEMA: REQUIERE ATENCION'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
