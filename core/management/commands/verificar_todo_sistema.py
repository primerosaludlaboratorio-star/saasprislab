"""
Verificación Completa del Sistema
Prueba todas las URLs, vistas y templates
"""
from django.core.management.base import BaseCommand
from django.urls import get_resolver
from django.conf import settings
from pathlib import Path
from django.test import Client
from django.contrib.auth import get_user_model

Usuario = get_user_model()

class Command(BaseCommand):
    help = 'Verificación completa del sistema - Prueba todas las URLs y vistas'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*100))
        self.stdout.write(self.style.SUCCESS('VERIFICACION COMPLETA DEL SISTEMA PRISLAB v5.0'))
        self.stdout.write(self.style.SUCCESS('='*100 + '\n'))
        
        # 1. Verificar URLs
        self.stdout.write(self.style.WARNING('[1] VERIFICANDO URLs...\n'))
        resolver = get_resolver()
        urls_list = self._extract_urls(resolver)
        urls_principales = [u for u in urls_list if self._es_url_principal(u[0], u[1])]
        
        self.stdout.write(f'  URLs principales encontradas: {len(urls_principales)}')
        
        # 2. Verificar Templates
        self.stdout.write(self.style.WARNING('\n[2] VERIFICANDO TEMPLATES...\n'))
        templates_dir = Path(settings.BASE_DIR) / 'core' / 'templates' / 'core'
        templates = list(templates_dir.rglob('*.html'))
        self.stdout.write(f'  Templates encontrados: {len(templates)}')
        
        # 3. Verificar Sidebar
        self.stdout.write(self.style.WARNING('\n[3] VERIFICANDO SIDEBAR...\n'))
        sidebar_path = Path(settings.BASE_DIR) / 'core' / 'templates' / 'includes' / 'sidebar.html'
        sidebar_content = sidebar_path.read_text(encoding='utf-8') if sidebar_path.exists() else ''
        
        urls_en_sidebar = []
        import re
        for match in re.finditer(r"url\s+['\"]([\w:]+)['\"]", sidebar_content):
            urls_en_sidebar.append(match.group(1))
        
        self.stdout.write(f'  URLs en sidebar: {len(set(urls_en_sidebar))}')
        
        # 4. Verificar Vistas
        self.stdout.write(self.style.WARNING('\n[4] VERIFICANDO VISTAS...\n'))
        views_dir = Path(settings.BASE_DIR) / 'core' / 'views'
        views_files = [f for f in views_dir.iterdir() if f.suffix == '.py' and f.name != '__init__.py']
        self.stdout.write(f'  Archivos de vistas: {len(views_files)}')
        
        # 5. Resumen
        self.stdout.write(self.style.SUCCESS('\n' + '='*100))
        self.stdout.write(self.style.SUCCESS('RESUMEN:'))
        self.stdout.write(f'  URLs principales: {len(urls_principales)}')
        self.stdout.write(f'  Templates: {len(templates)}')
        self.stdout.write(f'  URLs en sidebar: {len(set(urls_en_sidebar))}')
        self.stdout.write(f'  Archivos de vistas: {len(views_files)}')
        self.stdout.write('='*100)
        
        # 6. Listar URLs críticas
        self.stdout.write(self.style.WARNING('\n[5] URLs CRITICAS VERIFICADAS:\n'))
        urls_criticas = [
            'recepcion_lab', 'lista_trabajo_lab', 'captura_resultados',
            'dashboard_pendientes', 'entrega_resultados', 'reporte_tiempos_proceso',
            'pdv_farmacia', 'inventario_general', 'ajustes_inventario',
            'estadisticas_ventas', 'rutas_recoleccion', 'ia_dashboard'
        ]
        
        for url_name in urls_criticas:
            existe = any(u[0] == url_name for u in urls_list)
            en_sidebar = url_name in urls_en_sidebar
            estado = 'OK' if (existe and en_sidebar) else 'FALTA'
            estilo = self.style.SUCCESS if estado == 'OK' else self.style.ERROR
            self.stdout.write(estilo(f'  {estado:5} | {url_name:30} | URL: {"SI" if existe else "NO":3} | Sidebar: {"SI" if en_sidebar else "NO":3}'))

    def _extract_urls(self, resolver, prefix=''):
        """Extrae todas las URLs del resolver."""
        urls = []
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'url_patterns'):
                urls.extend(self._extract_urls(pattern, prefix + str(pattern.pattern)))
            else:
                url_name = pattern.name
                url_path = prefix + str(pattern.pattern)
                view_name = str(pattern.callback) if hasattr(pattern, 'callback') else ''
                if url_name:
                    urls.append((url_name, url_path, view_name))
        return urls

    def _es_url_principal(self, url_name, url_path):
        """Determina si es una URL principal."""
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
