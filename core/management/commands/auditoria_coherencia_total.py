"""
Protocolo de Auditoría de Coherencia Total (TCAP)
Escaneo 360 del repositorio para eliminar 'ceguera' del sistema.
"""
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.urls import get_resolver
from django.conf import settings

class Command(BaseCommand):
    help = 'Auditoría de Coherencia Total - Escaneo 360 del sistema'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write(self.style.SUCCESS('PROTOCOLO DE AUDITORIA DE COHERENCIA TOTAL (TCAP)'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        # 1. INVENTARIO FÍSICO DE ARCHIVOS
        self.stdout.write(self.style.WARNING('\n[1] INVENTARIO FISICO DE ARCHIVOS\n'))
        self.inventario_archivos()
        
        # 2. AUDITORÍA DE ENLACES Y BOTONES
        self.stdout.write(self.style.WARNING('\n[2] AUDITORIA DE ENLACES Y BOTONES\n'))
        self.auditoria_enlaces()
        
        # 3. MAPEO END-TO-END
        self.stdout.write(self.style.WARNING('\n[3] MAPEO END-TO-END DE MODULOS\n'))
        self.mapeo_modulos()
        
        # 4. REPORTE FINAL
        self.stdout.write(self.style.WARNING('\n[4] REPORTE FINAL\n'))
        self.generar_reporte_final()

    def inventario_archivos(self):
        """Inventario físico de archivos en templates, views y models."""
        base_dir = Path(settings.BASE_DIR)
        
        # Templates
        templates_dir = base_dir / 'core' / 'templates' / 'core'
        if templates_dir.exists():
            templates = list(templates_dir.glob('*.html'))
            self.stdout.write(f'Templates encontrados: {len(templates)}')
            for t in sorted(templates)[:10]:
                self.stdout.write(f'  - {t.name}')
            if len(templates) > 10:
                self.stdout.write(f'  ... y {len(templates) - 10} mas')
        
        # Views
        views_dir = base_dir / 'core' / 'views'
        if views_dir.exists():
            views = [f for f in views_dir.iterdir() if f.suffix == '.py' and f.name != '__init__.py']
            self.stdout.write(f'\nVistas encontradas: {len(views)}')
            for v in sorted(views)[:10]:
                self.stdout.write(f'  - {v.name}')
            if len(views) > 10:
                self.stdout.write(f'  ... y {len(views) - 10} mas')

    def auditoria_enlaces(self):
        """Auditoría de enlaces en sidebar e includes."""
        sidebar_path = Path(settings.BASE_DIR) / 'core' / 'templates' / 'includes' / 'sidebar.html'
        
        if not sidebar_path.exists():
            self.stdout.write(self.style.ERROR('  ERROR: sidebar.html no encontrado'))
            return
        
        with open(sidebar_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar enlaces vacíos o con #
        import re
        enlaces_vacios = re.findall(r'href=["\']#["\']', content)
        enlaces_tooltip = re.findall(r'href=["\']#["\'].*?data-toggle=["\']tooltip["\']', content)
        
        self.stdout.write(f'  Enlaces vacios (href="#"): {len(enlaces_vacios)}')
        self.stdout.write(f'  Enlaces con tooltip (modulo en construccion): {len(enlaces_tooltip)}')
        
        # Verificar URLs en el sidebar
        urls_encontradas = re.findall(r"url\s+['\"]([\w:]+)['\"]", content)
        self.stdout.write(f'\n  URLs encontradas en sidebar: {len(urls_encontradas)}')
        
        # Verificar contra urls.py
        resolver = get_resolver()
        urls_validas = []
        urls_invalidas = []
        
        for url_name in urls_encontradas:
            try:
                resolver.reverse(url_name)
                urls_validas.append(url_name)
            except:
                urls_invalidas.append(url_name)
        
        self.stdout.write(f'  URLs validas: {len(urls_validas)}')
        if urls_invalidas:
            self.stdout.write(self.style.ERROR(f'  URLs invalidas: {len(urls_invalidas)}'))
            for url in urls_invalidas[:5]:
                self.stdout.write(self.style.ERROR(f'    - {url}'))

    def mapeo_modulos(self):
        """Mapeo end-to-end de módulos principales."""
        modulos_estandar = [
            ('Captura de Resultados', 'captura_resultados', 'captura_resultados_industrial.html'),
            ('Dashboard Pendientes', 'dashboard_pendientes', 'dashboard_pendientes.html'),
            ('Entrega Resultados', 'entrega_resultados', 'entrega_resultados.html'),
            ('Lista de Trabajo', 'lista_trabajo_lab', 'lista_trabajo.html'),
            ('Recepción', 'recepcion_lab', 'recepcion_lab.html'),
            ('Control Calidad', 'control_calidad', 'control_calidad.html'),
            ('Toma de Muestra', 'toma_muestra_index', 'toma_muestra_index.html'),
            ('Corte de Caja', 'corte_dia', 'corte_caja_dia.html'),
            ('Facturación', 'facturacion_40', 'facturacion_40.html'),
            ('Inventario', 'inventario_general', 'inventario_general.html'),
            ('Dashboard Director', 'dashboard_director', 'dashboard_director.html'),
            ('Buzón Kanban', 'buzon_kanban', 'buzon_kanban.html'),
            ('Biblioteca', 'biblioteca_liderazgo', 'biblioteca_liderazgo.html'),
            ('Ranking', 'ranking_desempeno', 'ranking_desempeno.html'),
            ('Configuración', 'configuracion_dashboard', 'configuracion_dashboard.html'),
        ]
        
        resolver = get_resolver()
        resultados = []
        
        for nombre, url_name, template in modulos_estandar:
            tiene_url = False
            tiene_template = False
            
            # Verificar URL
            try:
                resolver.reverse(url_name)
                tiene_url = True
            except:
                pass
            
            # Verificar template
            template_path = Path(settings.BASE_DIR) / 'core' / 'templates' / 'core' / template
            tiene_template = template_path.exists()
            
            estado = 'OK' if (tiene_url and tiene_template) else 'ERROR'
            resultados.append({
                'nombre': nombre,
                'url': url_name,
                'template': template,
                'tiene_url': tiene_url,
                'tiene_template': tiene_template,
                'estado': estado
            })
        
        # Mostrar resultados
        self.stdout.write('\n  Modulo | URL | Template | Estado')
        self.stdout.write('  ' + '-'*60)
        for r in resultados:
            url_status = 'SI' if r['tiene_url'] else 'NO'
            template_status = 'SI' if r['tiene_template'] else 'NO'
            estilo = self.style.SUCCESS if r['estado'] == 'OK' else self.style.ERROR
            self.stdout.write(estilo(
                f"  {r['nombre'][:20]:20} | {url_status:3} | {template_status:3} | {r['estado']}"
            ))

    def generar_reporte_final(self):
        """Genera reporte final con recomendaciones."""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('RECOMENDACIONES DE REPARACION:'))
        self.stdout.write('='*80)
        self.stdout.write('\n1. Revisar enlaces con href="#" en sidebar.html')
        self.stdout.write('2. Verificar que todos los templates tengan vistas asociadas')
        self.stdout.write('3. Agregar accesos faltantes al sidebar')
        self.stdout.write('4. Probar manualmente cada URL para confirmar funcionamiento')
