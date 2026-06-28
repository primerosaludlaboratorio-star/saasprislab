"""
Comando Django para cierre de día.
Limpia items sugeridos que no fueron procesados y registra estadísticas.

Uso:
    python manage.py cierre_dia
    python manage.py cierre_dia --empresa=1  # Específico por empresa
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import RecetaItem, DemandaInsatisfecha, Empresa
from django.db import transaction
import logging


class Command(BaseCommand):
    help = 'Cierre de día: Limpia items sugeridos no procesados y registra estadísticas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=int,
            help='ID de la empresa específica para cierre. Si no se provee, procesa todas.',
        )
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha específica a procesar (formato: YYYY-MM-DD). Por defecto: ayer.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('🌙  INICIANDO CIERRE DE DÍA - MOTOR DE LIMPIEZA'))
        self.stdout.write(self.style.WARNING('=' * 80))
        
        # Determinar fecha de procesamiento
        if options['fecha']:
            try:
                fecha_proceso = datetime.strptime(options['fecha'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR(f'Error: Formato de fecha inválido. Use YYYY-MM-DD'))
                return
        else:
            # Por defecto: procesar items de ayer
            fecha_proceso = (timezone.localtime(timezone.now()) - timedelta(days=1)).date()
        
        self.stdout.write(f'\n📅  Fecha de procesamiento: {fecha_proceso}')
        
        # Determinar empresas a procesar
        if options['empresa']:
            empresas = Empresa.objects.filter(id=options['empresa'])
            if not empresas.exists():
                self.stdout.write(self.style.ERROR(f'Error: Empresa con ID {options["empresa"]} no encontrada'))
                return
        else:
            empresas = Empresa.objects.filter(activa=True)
        
        self.stdout.write(f'🏢  Empresas a procesar: {empresas.count()}\n')
        
        # Estadísticas globales
        total_items_procesados = 0
        total_demandas_creadas = 0
        total_items_eliminados = 0
        
        for empresa in empresas:
            self.stdout.write(f'\n{'─' * 80}')
            self.stdout.write(f'🏢  Procesando: {empresa.nombre}')
            self.stdout.write(f'{'─' * 80}')
            
            try:
                with transaction.atomic():
                    # Buscar items SUGERIDO que no fueron procesados
                    items_pendientes = RecetaItem.objects.filter(
                        receta__empresa=empresa,
                        receta__fecha_emision__date=fecha_proceso,
                        estado='SUGERIDO'
                    ).select_related('receta', 'receta__paciente', 'medicamento')
                    
                    count_items = items_pendientes.count()
                    
                    if count_items == 0:
                        self.stdout.write(self.style.SUCCESS(f'   ✅  Sin items pendientes para esta empresa'))
                        continue
                    
                    self.stdout.write(f'\n   📦  Items SUGERIDO encontrados: {count_items}')
                    
                    demandas_creadas = 0
                    items_eliminados = 0
                    
                    # Procesar cada item
                    for item in items_pendientes:
                        try:
                            # Crear registro de demanda insatisfecha
                            producto_nombre = item.medicamento.nombre if item.medicamento else item.texto_libre
                            
                            DemandaInsatisfecha.objects.create(
                                producto_nombre=producto_nombre,
                                cantidad_dejada=item.cantidad,
                                causa='No confirmado en caja - Cierre automático',
                                fecha=timezone.now(),
                                usuario=None,  # Sistema automático
                                receta_item=item,
                                empresa=empresa,
                                sucursal=item.receta.sucursal if item.receta.sucursal else None
                            )
                            demandas_creadas += 1
                            
                            # Eliminar item sugerido
                            item.delete()
                            items_eliminados += 1
                            
                        except Exception as e:
                            logging.getLogger(__name__).exception("Error inesperado en handle (cierre_dia.py)")
                            self.stdout.write(
                                self.style.ERROR(f'   ❌  Error procesando item {item.id}: {str(e)}')
                            )
                    
                    # Actualizar estadísticas
                    total_items_procesados += count_items
                    total_demandas_creadas += demandas_creadas
                    total_items_eliminados += items_eliminados
                    
                    # Resultados de la empresa
                    self.stdout.write(f'\n   📊  Resultados:')
                    self.stdout.write(f'      • Demandas insatisfechas creadas: {demandas_creadas}')
                    self.stdout.write(f'      • Items eliminados: {items_eliminados}')
                    self.stdout.write(self.style.SUCCESS(f'   ✅  Cierre completado para {empresa.nombre}'))
                    
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en handle (cierre_dia.py)")
                self.stdout.write(
                    self.style.ERROR(f'   ❌  Error crítico procesando empresa {empresa.nombre}: {str(e)}')
                )
        
        # Resumen final
        self.stdout.write(f'\n{'=' * 80}')
        self.stdout.write(self.style.SUCCESS('✨  CIERRE DE DÍA COMPLETADO'))
        self.stdout.write(f'{'=' * 80}')
        self.stdout.write(f'\n📊  RESUMEN GLOBAL:')
        self.stdout.write(f'   • Total items procesados: {total_items_procesados}')
        self.stdout.write(f'   • Total demandas insatisfechas: {total_demandas_creadas}')
        self.stdout.write(f'   • Total items eliminados: {total_items_eliminados}')
        self.stdout.write(f'\n💾  Los datos estadísticos están guardados en el modelo DemandaInsatisfecha')
        self.stdout.write(self.style.SUCCESS(f'\n✅  Sistema listo para un nuevo día\n'))