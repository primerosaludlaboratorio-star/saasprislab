from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from contabilidad.models import FacturaCFDI


class Command(BaseCommand):
    help = (
        "Devuelve a PENDIENTE las facturas en FACTURANDO con timbrado_intento_en > 5 minutos "
        "(recuperación tras timeout PAC)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=5,
            help="Minutos en FACTURANDO antes de reconciliar (default 5).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo listar IDs afectados.",
        )

    def handle(self, *args, **options):
        minutes = max(1, int(options["minutes"]))
        limite = timezone.now() - timedelta(minutes=minutes)
        qs = FacturaCFDI.objects.filter(
            estado="FACTURANDO",
            timbrado_intento_en__isnull=False,
            timbrado_intento_en__lt=limite,
        )
        ids = list(qs.values_list("id", flat=True))
        self.stdout.write(f"Candidatas (FACTURANDO > {minutes} min): {len(ids)} — {ids[:50]}")
        if options["dry_run"]:
            return
        n = qs.update(
            estado="PENDIENTE",
            timbrando_en_proceso=False,
            timbrado_intento_en=None,
        )
        self.stdout.write(self.style.SUCCESS(f"Actualizadas: {n}"))
