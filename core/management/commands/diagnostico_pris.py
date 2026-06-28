"""
PRIS - Sistema de Auto-Diagnóstico Inteligente
Management Command para verificación profunda del sistema PRISLAB

Ejecutar: python manage.py diagnostico_pris
"""
from django.core.management.base import BaseCommand
from django.urls import get_resolver, URLPattern, URLResolver
from django.test import Client
from django.db import connection
from django.conf import settings
from django.apps import apps
import sys
import logging


class Command(BaseCommand):
    help = 'Diagnóstico completo del sistema PRISLAB por PRIS'

    def __init__(self):
        super().__init__()
        self.errores_criticos = []
        self.advertencias = []
        self.ok_count = 0

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Ejecutar diagnóstico completo incluyendo pruebas de URLs',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("          PRIS - SISTEMA DE AUTO-DIAGNOSTICO"))
        self.stdout.write("="*80 + "\n")

        # 1. Check de Configuración
        self.check_configuracion()
        
        # 2. Check de Base de Datos
        self.check_base_datos()
        
        # 3. Check de Modelos Críticos
        self.check_modelos_criticos()
        
        # 4. Check de URLs (solo con --full)
        if options['full']:
            self.check_urls()
        else:
            self.stdout.write(self.style.WARNING(
                "\nPrueba de URLs omitida. Usa --full para incluirla."
            ))
        
        # Resumen Final
        self.mostrar_resumen()

    def check_configuracion(self):
        """Verifica la configuración de Django"""
        self.stdout.write("\n[1] VERIFICANDO CONFIGURACION...")
        
        # Check DEBUG
        if settings.DEBUG:
            self.stdout.write(self.style.WARNING("  [!] DEBUG esta en True (desarrollo)"))
            self.advertencias.append("DEBUG=True en producción no es recomendado")
        else:
            self.stdout.write(self.style.SUCCESS("  [OK] DEBUG configurado correctamente"))
            self.ok_count += 1
        
        # Check SECRET_KEY
        if settings.SECRET_KEY and len(settings.SECRET_KEY) > 20:
            self.stdout.write(self.style.SUCCESS("  [OK] SECRET_KEY configurada"))
            self.ok_count += 1
        else:
            self.stdout.write(self.style.ERROR("  [X] SECRET_KEY debil o ausente"))
            self.errores_criticos.append("SECRET_KEY no configurada correctamente")
        
        # Check ALLOWED_HOSTS
        if settings.ALLOWED_HOSTS:
            self.stdout.write(self.style.SUCCESS(f"  [OK] ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}"))
            self.ok_count += 1
        else:
            self.stdout.write(self.style.WARNING("  [!] ALLOWED_HOSTS vacio"))
            self.advertencias.append("ALLOWED_HOSTS debe configurarse en producción")

    def check_base_datos(self):
        """Verifica la conectividad y estado de la base de datos"""
        self.stdout.write("\n[2] VERIFICANDO BASE DE DATOS...")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                self.stdout.write(self.style.SUCCESS("  [OK] Conexion a base de datos activa"))
                self.ok_count += 1
                
                # Contar tablas
                cursor.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                )
                tabla_count = cursor.fetchone()[0]
                self.stdout.write(self.style.SUCCESS(f"  [OK] {tabla_count} tablas en base de datos"))
                self.ok_count += 1
                
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en check_base_datos (diagnostico_pris.py)")
            self.stdout.write(self.style.ERROR(f"  [X] Error de BD: {str(e)}"))
            self.errores_criticos.append(f"Error de base de datos: {str(e)}")

    def check_modelos_criticos(self):
        """Verifica la existencia e integridad de modelos críticos"""
        self.stdout.write("\n[3] VERIFICANDO MODELOS CRITICOS...")
        
        modelos_criticos = [
            ('core', 'Usuario'),
            ('core', 'Empresa'),
            ('core', 'Paciente'),
            ('core', 'OrdenDeServicio'),
            ('lims', 'Analito'),
            ('lims', 'ValorReferenciaAnalito'),
            ('lims', 'PerfilLims'),
            ('core', 'ResultadoParametro'),
            ('core', 'Producto'),
            ('core', 'Receta'),
        ]
        
        for app_label, model_name in modelos_criticos:
            try:
                model = apps.get_model(app_label, model_name)
                count = model.objects.count()
                self.stdout.write(
                    self.style.SUCCESS(f"  [OK] {model_name}: {count} registros")
                )
                self.ok_count += 1
            except LookupError:
                self.stdout.write(
                    self.style.ERROR(f"  [X] Modelo {model_name} NO EXISTE")
                )
                self.errores_criticos.append(f"Modelo {model_name} no encontrado")
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en check_modelos_criticos (diagnostico_pris.py)")
                self.stdout.write(
                    self.style.ERROR(f"  [X] Error en {model_name}: {str(e)}")
                )
                self.errores_criticos.append(f"Error en modelo {model_name}: {str(e)}")

    def check_urls(self):
        """Verifica las URLs del sistema haciendo requests internos"""
        self.stdout.write("\n[4] VERIFICANDO URLS (esto puede tardar)...")
        
        client = Client()
        resolver = get_resolver()
        
        # Obtener todas las URLs
        urls_to_test = []
        self._extract_urls(resolver.url_patterns, '', urls_to_test)
        
        self.stdout.write(f"  Encontradas {len(urls_to_test)} URLs para verificar...")
        
        errores_urls = []
        ok_urls = 0
        
        for url_pattern in urls_to_test[:50]:  # Limitar a 50 para no tardar mucho
            try:
                # Intentar GET (sin autenticación, esperamos 302 o 200)
                response = client.get(url_pattern, follow=False)
                
                if response.status_code in [200, 301, 302, 304]:
                    ok_urls += 1
                elif response.status_code == 404:
                    pass  # URL válida pero sin contenido
                elif response.status_code == 500:
                    errores_urls.append(f"{url_pattern} -> ERROR 500")
                    
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en check_urls (diagnostico_pris.py)")
                errores_urls.append(f"{url_pattern} -> {str(e)[:50]}")
        
        if errores_urls:
            self.stdout.write(self.style.ERROR(f"\n  [X] {len(errores_urls)} URLs con errores:"))
            for error in errores_urls[:10]:  # Mostrar solo los primeros 10
                self.stdout.write(self.style.ERROR(f"      {error}"))
            self.errores_criticos.extend(errores_urls)
        else:
            self.stdout.write(self.style.SUCCESS(f"  [OK] {ok_urls} URLs verificadas sin errores 500"))
            self.ok_count += 1

    def _extract_urls(self, urlpatterns, prefix, urls_list):
        """Extrae recursivamente todas las URLs del sistema"""
        for pattern in urlpatterns:
            if isinstance(pattern, URLPattern):
                url = prefix + str(pattern.pattern)
                # Limpiar parámetros dinámicos
                url = url.replace('<int:pk>', '1')
                url = url.replace('<int:id>', '1')
                url = url.replace('<int:orden_id>', '1')
                url = url.replace('<str:token>', 'test')
                url = url.replace('<uuid:uuid>', '00000000-0000-0000-0000-000000000000')
                
                if not any(c in url for c in ['<', '>']):  # Solo URLs sin parámetros complejos
                    urls_list.append('/' + url.lstrip('^').rstrip('$'))
                    
            elif isinstance(pattern, URLResolver):
                self._extract_urls(
                    pattern.url_patterns, 
                    prefix + str(pattern.pattern), 
                    urls_list
                )

    def mostrar_resumen(self):
        """Muestra el resumen final del diagnóstico"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("RESUMEN DEL DIAGNOSTICO"))
        self.stdout.write("="*80)
        
        self.stdout.write(self.style.SUCCESS(f"\nVerificaciones exitosas: {self.ok_count}"))
        
        if self.advertencias:
            self.stdout.write(self.style.WARNING(f"\nAdvertencias ({len(self.advertencias)}):"))
            for adv in self.advertencias[:5]:
                self.stdout.write(self.style.WARNING(f"  - {adv}"))
        
        if self.errores_criticos:
            self.stdout.write(self.style.ERROR(f"\nErrores criticos ({len(self.errores_criticos)}):"))
            for err in self.errores_criticos[:10]:
                self.stdout.write(self.style.ERROR(f"  - {err}"))
            self.stdout.write("\n")
            self.stdout.write(self.style.ERROR(
                "ESTADO: SISTEMA CON ERRORES - Requiere atencion"
            ))
            sys.exit(1)
        else:
            self.stdout.write("\n")
            self.stdout.write(self.style.SUCCESS(
                "ESTADO: SISTEMA OPERATIVO - PRIS tiene el control"
            ))
            self.stdout.write("="*80 + "\n")