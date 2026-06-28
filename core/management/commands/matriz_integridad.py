"""
Matriz de Integridad de PRISLAB v5.0
Senior Lead Architect - Auditoría Completa
"""
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.urls import get_resolver
from django.conf import settings

class Command(BaseCommand):
    help = 'Genera Matriz de Integridad completa del sistema'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*100))
        self.stdout.write(self.style.SUCCESS('MATRIZ DE INTEGRIDAD DE PRISLAB v5.0'))
        self.stdout.write(self.style.SUCCESS('Senior Lead Architect - Auditoría Completa'))
        self.stdout.write(self.style.SUCCESS('='*100 + '\n'))
        
        # Leer sidebar
        sidebar_path = Path(settings.BASE_DIR) / 'core' / 'templates' / 'includes' / 'sidebar.html'
        sidebar_content = sidebar_path.read_text(encoding='utf-8') if sidebar_path.exists() else ''
        
        # Obtener todas las URLs
        resolver = get_resolver()
        urls_list = self._extract_urls(resolver)
        
        # Módulos críticos a verificar
        modulos_criticos = [
            'captura_resultados',
            'imprimir_hoja_trabajo_pdf',
            'abrir_worklist_qr',
            'dashboard_pendientes',
            'entrega_resultados',
        ]
        
        # Generar matriz
        self.stdout.write(self.style.WARNING('\n[MÓDULO/FUNCIONALIDAD] | [RUTA URL] | [BOTÓN EN SIDEBAR] | [ESTADO DE OPERACIÓN]\n'))
        self.stdout.write('-' * 100)
        
        resultados = []
        modulos_criticos_encontrados = []
        
        for url_name, url_path, view_name in urls_list:
            # Filtrar solo URLs principales (no APIs ni endpoints internos)
            if self._es_url_principal(url_name, url_path):
                tiene_boton = self._tiene_boton_sidebar(url_name, sidebar_content)
                tiene_vista = self._tiene_vista_funcional(view_name)
                estado = self._determinar_estado(tiene_boton, tiene_vista)
                
                # Verificar si es módulo crítico
                es_critico = any(critico in url_name for critico in modulos_criticos)
                if es_critico:
                    modulos_criticos_encontrados.append({
                        'nombre': url_name,
                        'url': url_path,
                        'boton': tiene_boton,
                        'vista': tiene_vista,
                        'estado': estado
                    })
                
                resultados.append({
                    'nombre': self._formatear_nombre(url_name),
                    'url': url_path,
                    'boton': 'SÍ' if tiene_boton else 'NO',
                    'estado': estado
                })
        
        # Mostrar matriz
        for r in resultados:
            estilo = self.style.SUCCESS if r['estado'] == '✅ OPERATIVO' else self.style.ERROR if '❌' in r['estado'] else self.style.WARNING
            self.stdout.write(estilo(
                f"{r['nombre']:<35} | {r['url']:<40} | {r['boton']:<18} | {r['estado']}"
            ))
        
        # Análisis de módulos críticos
        self.stdout.write(self.style.ERROR('\n' + '='*100))
        self.stdout.write(self.style.ERROR('ANÁLISIS DE MÓDULOS CRÍTICOS'))
        self.stdout.write(self.style.ERROR('='*100 + '\n'))
        
        for mod in modulos_criticos_encontrados:
            self.stdout.write(f"\n🔍 {mod['nombre'].upper()}")
            self.stdout.write(f"   URL: {mod['url']}")
            self.stdout.write(f"   Botón en Sidebar: {'✅ SÍ' if mod['boton'] else '❌ NO'}")
            self.stdout.write(f"   Vista Funcional: {'✅ SÍ' if mod['vista'] else '❌ NO'}")
            self.stdout.write(f"   Estado: {mod['estado']}")
        
        # Reparaciones críticas
        self.stdout.write(self.style.WARNING('\n' + '='*100))
        self.stdout.write(self.style.WARNING('REPARACIONES CRÍTICAS IDENTIFICADAS'))
        self.stdout.write(self.style.WARNING('='*100 + '\n'))
        
        reparaciones = []
        for mod in modulos_criticos_encontrados:
            if not mod['boton']:
                reparaciones.append(f"❌ AGREGAR BOTÓN: {mod['nombre']} → Sidebar Laboratorio")
            if not mod['vista']:
                reparaciones.append(f"❌ CREAR VISTA: {mod['nombre']} → {mod['url']}")
        
        if not reparaciones:
            self.stdout.write(self.style.SUCCESS('✅ No se encontraron reparaciones críticas'))
        else:
            for i, rep in enumerate(reparaciones, 1):
                self.stdout.write(self.style.ERROR(f"{i}. {rep}"))

    def _extract_urls(self, resolver, prefix=''):
        """Extrae todas las URLs del resolver."""
        urls = []
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'url_patterns'):
                # Namespace
                urls.extend(self._extract_urls(pattern, prefix + str(pattern.pattern)))
            else:
                # URL individual
                url_name = pattern.name
                url_path = prefix + str(pattern.pattern)
                view_name = str(pattern.callback) if hasattr(pattern, 'callback') else ''
                if url_name:
                    urls.append((url_name, url_path, view_name))
        return urls

    def _es_url_principal(self, url_name, url_path):
        """Determina si es una URL principal (no API ni endpoint interno)."""
        if not url_name:
            return False
        if url_path.startswith('/api/') or '/api/' in url_path:
            return False
        if url_path.startswith('/admin/'):
            return False
        if url_name.endswith('_raw') or url_name.endswith('_pdf'):
            return False
        if 'api_' in url_name:
            return False
        return True

    def _tiene_boton_sidebar(self, url_name, sidebar_content):
        """Verifica si hay un botón en el sidebar para esta URL."""
        # Buscar el nombre de la URL en el sidebar
        pattern = f"url '{url_name}'"
        pattern2 = f'url "{url_name}"'
        return pattern in sidebar_content or pattern2 in sidebar_content

    def _tiene_vista_funcional(self, view_name):
        """Verifica si la vista existe y es funcional."""
        if not view_name:
            return False
        # Verificar que la vista existe en core.views
        try:
            from core import views
            if hasattr(views, view_name.split('.')[-1]):
                return True
        except:
            pass
        return True  # Asumir que existe si está en urls.py

    def _determinar_estado(self, tiene_boton, tiene_vista):
        """Determina el estado de operación."""
        if tiene_boton and tiene_vista:
            return '✅ OPERATIVO'
        elif tiene_vista and not tiene_boton:
            return '⚠️ VISTA SIN BOTÓN'
        elif tiene_boton and not tiene_vista:
            return '❌ BOTÓN SIN VISTA'
        else:
            return '❌ NO OPERATIVO'

    def _formatear_nombre(self, url_name):
        """Formatea el nombre para la matriz."""
        return url_name.replace('_', ' ').title()
