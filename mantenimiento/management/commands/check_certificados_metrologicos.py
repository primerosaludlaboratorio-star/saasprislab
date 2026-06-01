"""
Management Command: check_certificados_metrologicos
=====================================================
Revisa diariamente todos los CertificadoMetrologia activos y:
  1. Actualiza su estado (VIGENTE / POR_VENCER / VENCIDO).
  2. Si vence en ≤30 días y no se envió alerta aún → crea NotificacionDiscrepancia.
  3. Si ya venció → crea NotificacionDiscrepancia CRITICA (si no existe una no resuelta).

Ejecución recomendada vía Cloud Scheduler o cron:
    python manage.py check_certificados_metrologicos

Configurable en cloudbuild.yaml como step de Cloud Run Jobs.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Revisa vencimientos de certificados de metrología y genera alertas al Director."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias-alerta', type=int, default=30,
            help='Días antes del vencimiento para disparar alerta (default: 30).'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo reporta sin crear notificaciones.'
        )

    def handle(self, *args, **options):
        dias_alerta = options['dias_alerta']
        dry_run     = options['dry_run']
        hoy         = date.today()
        limite      = hoy + timedelta(days=dias_alerta)

        try:
            from mantenimiento.models import CertificadoMetrologia
            from inventario.models import NotificacionDiscrepancia
        except ImportError as exc:
            self.stderr.write(f"Error importando modelos: {exc}")
            return

        certs = CertificadoMetrologia.objects.filter(
            estado__in=['VIGENTE', 'POR_VENCER']
        ).select_related('empresa', 'expediente')

        alertas_generadas = 0
        actualizaciones   = 0

        for cert in certs:
            estado_anterior = cert.estado

            # Actualizar estado
            if cert.fecha_vencimiento < hoy:
                cert.estado = 'VENCIDO'
            elif cert.fecha_vencimiento <= limite:
                cert.estado = 'POR_VENCER'
            else:
                cert.estado = 'VIGENTE'

            if cert.estado != estado_anterior:
                if not dry_run:
                    cert.save(update_fields=['estado'])
                actualizaciones += 1

            # Alerta de vencimiento próximo (30 días)
            if cert.estado == 'POR_VENCER' and not cert.alerta_30d_enviada:
                dias_restantes = (cert.fecha_vencimiento - hoy).days
                titulo = (f"Certificado próximo a vencer: {cert.get_tipo_display()} "
                          f"— {cert.expediente.equipo}")
                detalle = (
                    f"Equipo: {cert.expediente.equipo}\n"
                    f"Tipo: {cert.get_tipo_display()}\n"
                    f"N° Certificado: {cert.numero_certificado or 'S/N'}\n"
                    f"Laboratorio emisor: {cert.laboratorio_emisor or 'No especificado'}\n"
                    f"Vence: {cert.fecha_vencimiento:%d/%m/%Y} ({dias_restantes} días)\n"
                    f"Acción requerida: Gestionar renovación con laboratorio certificado."
                )
                self.stdout.write(f"  ⚠  {titulo}")

                if not dry_run:
                    # Evitar duplicados: ¿ya existe notificación no resuelta?
                    existe = NotificacionDiscrepancia.objects.filter(
                        empresa=cert.empresa,
                        titulo__startswith=f"Certificado próximo a vencer",
                        resuelta=False,
                    ).filter(titulo__icontains=str(cert.expediente.equipo)).exists()

                    if not existe:
                        NotificacionDiscrepancia.objects.create(
                            empresa=cert.empresa,
                            tipo='STOCK_CRITICO',  # Reutilizamos como alerta general
                            nivel='ADVERTENCIA',
                            titulo=titulo,
                            detalle=detalle,
                        )
                        cert.alerta_30d_enviada = True
                        cert.save(update_fields=['alerta_30d_enviada'])
                        alertas_generadas += 1

            # Alerta de certificado VENCIDO
            elif cert.estado == 'VENCIDO':
                titulo = (f"CERTIFICADO VENCIDO: {cert.get_tipo_display()} "
                          f"— {cert.expediente.equipo}")
                self.stdout.write(self.style.ERROR(f"  🔴 {titulo}"))

                if not dry_run:
                    existe = NotificacionDiscrepancia.objects.filter(
                        empresa=cert.empresa,
                        titulo__startswith="CERTIFICADO VENCIDO",
                        resuelta=False,
                    ).filter(titulo__icontains=str(cert.expediente.equipo)).exists()

                    if not existe:
                        NotificacionDiscrepancia.objects.create(
                            empresa=cert.empresa,
                            tipo='LOTE_CADUCADO',
                            nivel='CRITICO',
                            titulo=titulo,
                            detalle=(
                                f"Equipo: {cert.expediente.equipo}\n"
                                f"Tipo: {cert.get_tipo_display()}\n"
                                f"Vencido: {cert.fecha_vencimiento:%d/%m/%Y}\n"
                                f"Días vencido: {(hoy - cert.fecha_vencimiento).days}\n"
                                f"ACCIÓN URGENTE: El equipo puede no estar apto para uso "
                                f"según ISO 15189 §6.4.3. Contactar laboratorio certificado "
                                f"de inmediato."
                            ),
                        )
                        alertas_generadas += 1

        msg = (
            f"check_certificados_metrologicos completado: "
            f"{certs.count()} certificados revisados, "
            f"{actualizaciones} estados actualizados, "
            f"{alertas_generadas} alertas generadas."
        )
        if dry_run:
            msg += " [DRY RUN — sin cambios en DB]"

        self.stdout.write(self.style.SUCCESS(msg))
        logger.info(msg)
