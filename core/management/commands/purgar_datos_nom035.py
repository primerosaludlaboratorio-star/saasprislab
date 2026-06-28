"""
Comando de gestión: purgar_datos_nom035
=======================================

Blindaje H-011: Cumplimiento NOM-035 y privacidad de datos de salud mental.

Por ley (NOM-035-STPS-2018), no podemos retener datos emocionales sensibles
definidamente sin justificación. Este comando anonimiza registros del módulo
de bienestar (alertas ROJO_VIDA, ROJO_VIOLENCIA, etc.) que tengan más de
6 meses de antigüedad.

Lógica de Purga:
- No borra la estadística, la anonimiza
- Desvincula al empleado (usuario = None)
- Reemplaza texto_original con marcador de anonimización
- Marca el registro como anonimizado
- Conserva el nivel de riesgo para estadísticas agregadas

Cronjob recomendado: Ejecutar el 1ro de cada mes a las 03:00 AM
"""

import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from bienestar.models import DiarioEmocional

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Anonimiza registros de bienestar (NOM-035) mayores a 6 meses. "
        "Preserva estadísticas pero elimina identificación personal."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--meses',
            type=int,
            default=6,
            help='Meses de retención antes de anonimizar (default: 6)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular ejecución sin modificar datos',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza ejecución sin confirmación',
        )

    def handle(self, *args, **options):
        meses_retencion = options['meses']
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(self.style.NOTICE(
            f"{'[SIMULACIÓN] ' if dry_run else ''}"
            f"Iniciando purga NOM-035: Anonimizando registros > {meses_retencion} meses"
        ))

        # Calcular fecha límite
        fecha_limite = timezone.now() - relativedelta(months=meses_retencion)
        
        self.stdout.write(f"Fecha límite: {fecha_limite.strftime('%Y-%m-%d')}")

        # Buscar registros a anonimizar
        registros = DiarioEmocional.objects.filter(
            fecha__lt=fecha_limite.date(),
            anonimizado=False,
        ).select_related('usuario')

        total_registros = registros.count()

        if total_registros == 0:
            self.stdout.write(self.style.SUCCESS(
                "No hay registros para anonimizar. El sistema está al día con NOM-035."
            ))
            return

        # Desglose por nivel de riesgo
        desglose = {
            'ROJO_VIDA': registros.filter(nivel_riesgo='ROJO_VIDA').count(),
            'ROJO_VIOLENCIA': registros.filter(nivel_riesgo='ROJO_VIOLENCIA').count(),
            'ROJO_ACOSO': registros.filter(nivel_riesgo='ROJO_ACOSO').count(),
            'AMARILLO': registros.filter(nivel_riesgo='AMARILLO').count(),
            'VERDE': registros.filter(nivel_riesgo='VERDE').count(),
        }

        self.stdout.write(self.style.WARNING(
            f"Se encontraron {total_registros} registros para anonimizar:"
        ))
        for nivel, count in desglose.items():
            if count > 0:
                self.stdout.write(f"  - {nivel}: {count} registros")

        # Confirmación si no es dry-run
        if not dry_run and not force:
            confirm = input("\n¿Proceder con la anonimización? [s/N]: ")
            if confirm.lower() != 's':
                self.stdout.write(self.style.NOTICE("Operación cancelada por el usuario."))
                return

        # Procesar anonimización
        anonimizados = 0
        errores = 0

        with transaction.atomic():
            for registro in registros:
                try:
                    if not dry_run:
                        # Anonimizar registro
                        registro.usuario = None  # Desvincular empleado
                        registro.contenido_privado = "ANONIMIZADO_POR_LEY"
                        registro.sentimiento_ia = "ANONIMIZADO"
                        registro.anonimizado = True
                        registro.fecha_anonimizacion = timezone.now()
                        registro.save(update_fields=[
                            'usuario', 'contenido_privado', 'sentimiento_ia',
                            'anonimizado', 'fecha_anonimizacion'
                        ])
                    
                    anonimizados += 1
                    
                    if anonimizados % 100 == 0:
                        self.stdout.write(f"  Procesados: {anonimizados}/{total_registros}")
                        
                except Exception as e:
                    errores += 1
                    logger.error(f"Error anonimizando registro {registro.id}: {e}")
                    if not dry_run:
                        raise  # Rollback en caso de error real

        # Reporte final
        if dry_run:
            self.stdout.write(self.style.NOTICE(
                f"\n[SIMULACIÓN] Se habrían anonimizado {anonimizados} registros"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Anonimización completada: {anonimizados} registros procesados"
            ))
            
            if errores > 0:
                self.stdout.write(self.style.ERROR(
                    f"⚠ Errores encontrados: {errores} registros"
                ))

        # Generar resumen para auditoría
        resumen = {
            'timestamp': timezone.now().isoformat(),
            'comando': 'purgar_datos_nom035',
            'meses_retencion': meses_retencion,
            'fecha_limite': fecha_limite.isoformat(),
            'total_registros': total_registros,
            'anonimizados': anonimizados,
            'errores': errores,
            'desglose_riesgo': desglose,
            'dry_run': dry_run,
        }
        
        logger.info(f"NOM-035 Purga completada: {resumen}")
        
        self.stdout.write(self.style.NOTICE(
            "\nNota: Los registros anonimizados mantienen su nivel de riesgo "
            "para estadísticas agregadas, pero ya no pueden vincularse a un empleado específico."
        ))
