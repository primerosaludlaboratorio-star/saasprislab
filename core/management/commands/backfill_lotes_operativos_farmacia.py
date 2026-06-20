from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Empresa, Producto
from core.services.ventas.venta_farmacia_service import VentaFarmaciaService


class Command(BaseCommand):
    help = (
        "Crea lotes operativos automáticos para productos de farmacia que tienen "
        "stock heredado en Producto.stock pero ningún lote registrado."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id",
            type=int,
            default=1,
            help="ID de empresa destino (default: 1).",
        )

    def handle(self, *args, **options):
        empresa = Empresa.objects.filter(pk=options["empresa_id"]).first()
        if not empresa:
            empresa = Empresa.objects.order_by("pk").first()
        if not empresa:
            self.stderr.write(self.style.ERROR("No hay empresas disponibles."))
            return

        candidatos = Producto.objects.filter(
            empresa=empresa,
            stock__gt=0,
        ).exclude(
            lotes__isnull=False,
        ).distinct()

        creados = 0
        with transaction.atomic():
            for producto in candidatos.select_for_update():
                lote = VentaFarmaciaService.materializar_lote_operativo_si_falta(producto, empresa)
                if lote:
                    creados += 1
                    self.stdout.write(
                        f"[OK] Producto {producto.id} -> lote {lote.numero_lote} ({lote.cantidad} u)"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Empresa [{empresa.pk}] {empresa} | lotes operativos creados: {creados}"
            )
        )
