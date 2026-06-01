"""
Auditoría Completa de Botones y Pantallas
Identifica botones que no funcionan y pantallas que nunca se han visto
"""
import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.urls import get_resolver
from django.conf import settings

class Command(BaseCommand):
    help = 'Auditoría completa de botones y pantallas - Identifica problemas'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*100))
        self.stdout.write(self.style.SUCCESS('AUDITORÍA COMPLETA: BOTONES Y PANTALLAS'))
        self.stdout.write(self.style.SUCCESS('='*100 + '\n'))
        
        # 1. Leer sidebar para ver qué está accesible
        sidebar_path = Path(settings.BASE_DIR) / 'core' / 'templates' / 'includes' / 'sidebar.html'
        sidebar_content = sidebar_path.read_text(encoding='utf-8') if sidebar_path.exists() else ''
        
        # 2. Obtener todas las URLs
        resolver = get_resolver()
        urls_list = self._extract_urls(resolver)
        urls_dict = {name: path for name, path, _ in urls_list if name}
        
        # 3. Escanear todos los templates
        templates_dir = Path(settings.BASE_DIR) / 'core' / 'templates' / 'core'
        templates = list(templates_dir.rglob('*.html'))
        
        self.stdout.write(self.style.WARNING(f'\n[1] ESCANEANDO {len(templates)} TEMPLATES...\n'))
        
        problemas_botones = []
        pantallas_sin_acceso = []
        botones_rotos = []
        
        for template_path in templates:
            rel_path = template_path.relative_to(templates_dir)
            content = template_path.read_text(encoding='utf-8')
            
            # Buscar botones y enlaces
            botones = self._extraer_botones(content, str(rel_path))
            
            for boton in botones:
                if boton['tipo'] == 'url_tag':
                    url_name = boton['url_name']
                    if url_name not in urls_dict:
                        botones_rotos.append({
                            'template': str(rel_path),
                            'boton': boton['texto'],
                            'url': url_name,
                            'problema': 'URL no existe en urls.py'
                        })
                    elif not self._tiene_boton_sidebar(url_name, sidebar_content):
                        # Verificar si es una pantalla principal
                        if self._es_pantalla_principal(url_name, urls_dict[url_name]):
                            pantallas_sin_acceso.append({
                                'template': str(rel_path),
                                'url_name': url_name,
                                'url_path': urls_dict[url_name],
                                'boton': boton['texto']
                            })
                
                elif boton['tipo'] == 'onclick':
                    # Verificar si la función JavaScript existe
                    if not self._funcion_js_existe(boton['funcion'], content):
                        problemas_botones.append({
                            'template': str(rel_path),
                            'boton': boton['texto'],
                            'problema': f"Función JavaScript '{boton['funcion']}' no encontrada"
                        })
        
        # 4. Reporte
        self.stdout.write(self.style.ERROR('\n[2] BOTONES ROTOS (URLs que no existen):'))
        self.stdout.write('-' * 100)
        if botones_rotos:
            for item in botones_rotos[:20]:  # Mostrar primeros 20
                self.stdout.write(self.style.ERROR(
                    f"  ❌ {item['template']} | Botón: '{item['boton']}' | URL: {item['url']} | {item['problema']}"
                ))
            if len(botones_rotos) > 20:
                self.stdout.write(self.style.ERROR(f"  ... y {len(botones_rotos) - 20} más"))
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ No se encontraron botones rotos'))
        
        self.stdout.write(self.style.WARNING('\n[3] PANTALLAS SIN ACCESO EN SIDEBAR:'))
        self.stdout.write('-' * 100)
        if pantallas_sin_acceso:
            for item in pantallas_sin_acceso:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠️  {item['url_name']} | {item['url_path']} | Template: {item['template']}"
                ))
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ Todas las pantallas tienen acceso'))
        
        self.stdout.write(self.style.ERROR('\n[4] PROBLEMAS CON JAVASCRIPT:'))
        self.stdout.write('-' * 100)
        if problemas_botones:
            for item in problemas_botones[:20]:
                self.stdout.write(self.style.ERROR(
                    f"  ❌ {item['template']} | Botón: '{item['boton']}' | {item['problema']}"
                ))
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ No se encontraron problemas con JavaScript'))
        
        # 5. Resumen
        self.stdout.write(self.style.SUCCESS('\n' + '='*100))
        self.stdout.write(self.style.SUCCESS('RESUMEN:'))
        self.stdout.write(f"  Botones rotos: {len(botones_rotos)}")
        self.stdout.write(f"  Pantallas sin acceso: {len(pantallas_sin_acceso)}")
        self.stdout.write(f"  Problemas JavaScript: {len(problemas_botones)}")
        self.stdout.write('='*100)

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

    def _extraer_botones(self, content, template_path):
        """Extrae botones y enlaces del contenido HTML."""
        botones = []
        
        # Buscar {% url 'nombre' %}
        url_pattern = r"{%\s*url\s+['\"]([\w:]+)['\"]"
        for match in re.finditer(url_pattern, content):
            # Buscar el texto del botón/enlace cercano
            contexto = content[max(0, match.start()-200):match.end()+200]
            texto_match = re.search(r'>(.*?)</a>|<button[^>]*>(.*?)</button>', contexto, re.DOTALL)
            texto = (texto_match.group(1) or texto_match.group(2) or '').strip()[:50] if texto_match else 'Sin texto'
            texto = re.sub(r'<[^>]+>', '', texto)[:50]
            
            botones.append({
                'tipo': 'url_tag',
                'url_name': match.group(1),
                'texto': texto,
                'posicion': match.start()
            })
        
        # Buscar onclick="funcion()"
        onclick_pattern = r'onclick=["\']([\w]+)\([^)]*\)["\']'
        for match in re.finditer(onclick_pattern, content):
            contexto = content[max(0, match.start()-200):match.end()+200]
            texto_match = re.search(r'>(.*?)</button>|>(.*?)</a>', contexto, re.DOTALL)
            texto = (texto_match.group(1) or texto_match.group(2) or '').strip()[:50] if texto_match else 'Sin texto'
            texto = re.sub(r'<[^>]+>', '', texto)[:50]
            
            botones.append({
                'tipo': 'onclick',
                'funcion': match.group(1),
                'texto': texto,
                'posicion': match.start()
            })
        
        return botones

    def _tiene_boton_sidebar(self, url_name, sidebar_content):
        """Verifica si hay un botón en el sidebar para esta URL."""
        pattern1 = f"url '{url_name}'"
        pattern2 = f'url "{url_name}"'
        return pattern1 in sidebar_content or pattern2 in sidebar_content

    def _es_pantalla_principal(self, url_name, url_path):
        """Determina si es una pantalla principal (no API ni endpoint interno)."""
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

    def _funcion_js_existe(self, funcion, content):
        """Verifica si la función JavaScript existe en el contenido."""
        pattern = rf'function\s+{funcion}\s*\(|const\s+{funcion}\s*=|let\s+{funcion}\s*=|var\s+{funcion}\s*='
        return bool(re.search(pattern, content, re.IGNORECASE))
