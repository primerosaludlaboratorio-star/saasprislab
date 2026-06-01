"""
Comando de Django para auditar todas las rutas del sistema.
Detecta URLs rotas, vistas faltantes y inconsistencias.
"""
from django.core.management.base import BaseCommand
from django.urls import get_resolver, NoReverseMatch
from django.conf import settings
import django
django.setup()


class Command(BaseCommand):
    help = 'Audita todas las rutas del sistema para detectar errores 404 y 500'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== AUDITORÍA DE RUTAS PRISLAB v5 ===\n'))
        
        resolver = get_resolver()
        urls_encontradas = []
        errores = []
        
        def extraer_urls(url_patterns, prefix=''):
            for pattern in url_patterns:
                if hasattr(pattern, 'url_patterns'):
                    # Es un include
                    try:
                        extraer_urls(pattern.url_patterns, prefix + str(pattern.pattern))
                    except Exception as e:
                        errores.append(f"Error en include {pattern.pattern}: {e}")
                else:
                    # Es un path
                    try:
                        ruta_completa = prefix + str(pattern.pattern)
                        nombre = pattern.name if hasattr(pattern, 'name') and pattern.name else 'SIN_NOMBRE'
                        callback = pattern.callback if hasattr(pattern, 'callback') else None
                        
                        urls_encontradas.append({
                            'ruta': ruta_completa,
                            'nombre': nombre,
                            'callback': callback.__name__ if callback else 'N/A',
                            'modulo': callback.__module__ if callback else 'N/A'
                        })
                    except Exception as e:
                        errores.append(f"Error en pattern {pattern}: {e}")
        
        try:
            extraer_urls(resolver.url_patterns)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al extraer URLs: {e}'))
        
        # Agrupar por módulo
        urls_por_modulo = {}
        for url in urls_encontradas:
            modulo = url['modulo'].split('.')[0] if '.' in url['modulo'] else url['modulo']
            if modulo not in urls_por_modulo:
                urls_por_modulo[modulo] = []
            urls_por_modulo[modulo].append(url)
        
        # Mostrar resultados
        self.stdout.write(self.style.SUCCESS(f'\nTotal de URLs encontradas: {len(urls_encontradas)}\n'))
        
        for modulo, urls in sorted(urls_por_modulo.items()):
            self.stdout.write(self.style.WARNING(f'\n=== {modulo.upper()} ==='))
            for url in urls[:10]:  # Mostrar primeras 10
                self.stdout.write(f"  {url['ruta']} -> {url['nombre']} ({url['callback']})")
            if len(urls) > 10:
                self.stdout.write(f"  ... y {len(urls) - 10} más")
        
        if errores:
            self.stdout.write(self.style.ERROR(f'\n=== ERRORES ENCONTRADOS: {len(errores)} ==='))
            for error in errores[:10]:
                self.stdout.write(self.style.ERROR(f"  {error}"))
        
        # Verificar URLs críticas de PRIS
        urls_pris_criticas = [
            'api_dictado_inventario',
            'api_dictado_resultado',
            'api_ocr_documento',
            'api_crear_archivo_raw',
            'api_consulta_voz',
            'dashboard_capacitacion',
            'consultar_pris_rag',
            'chat_bienestar',
            'enviar_mensaje_bienestar',
        ]
        
        self.stdout.write(self.style.SUCCESS('\n=== VERIFICACIÓN DE URLs CRÍTICAS PRIS ==='))
        nombres_urls = [url['nombre'] for url in urls_encontradas]
        for url_critica in urls_pris_criticas:
            if url_critica in nombres_urls:
                self.stdout.write(self.style.SUCCESS(f"  ✓ {url_critica}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ {url_critica} - NO ENCONTRADA"))
        
        self.stdout.write(self.style.SUCCESS('\n=== AUDITORÍA COMPLETADA ==='))
