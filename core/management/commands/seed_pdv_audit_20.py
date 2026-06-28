"""
Seeding local: 20 medicamentos de auditoría PDV v7 (empresa explícita).
Uso: python manage.py seed_pdv_audit_20
     python manage.py seed_pdv_audit_20 --empresa-id 2
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Empresa, Producto


# 20 ítems fijos: nombre comercial, código de barras 13 dígitos, precio público
AUDIT_CATALOG = [
    ("AMOXICILINA 500MG TAB AUDIT-01", "7501234567800", Decimal("45.00")),
    ("AMOXICILINA SUSP 250MG AUDIT-02", "7501234567801", Decimal("88.50")),
    ("IBUPROFENO 400MG TAB AUDIT-03", "7501234567802", Decimal("32.00")),
    ("PARACETAMOL 500MG TAB AUDIT-04", "7501234567803", Decimal("18.00")),
    ("OMEPRAZOL 20MG CAP AUDIT-05", "7501234567804", Decimal("55.00")),
    ("METFORMINA 850MG TAB AUDIT-06", "7501234567805", Decimal("42.00")),
    ("LOSARTAN 50MG TAB AUDIT-07", "7501234567806", Decimal("65.00")),
    ("ATORVASTATINA 20MG TAB AUDIT-08", "7501234567807", Decimal("120.00")),
    ("AZITROMICINA 500MG TAB AUDIT-09", "7501234567808", Decimal("210.00")),
    ("CETIRIZINA 10MG TAB AUDIT-10", "7501234567809", Decimal("28.00")),
    ("CLARITROMICINA 500MG AUDIT-11", "7501234567810", Decimal("195.00")),
    ("DICLOFENACO 50MG TAB AUDIT-12", "7501234567811", Decimal("22.00")),
    ("NAPROXENO 550MG TAB AUDIT-13", "7501234567812", Decimal("35.00")),
    ("RANITIDINA 150MG AUDIT-14", "7501234567813", Decimal("48.00")),
    ("SALBUTAMOL INHAL AUDIT-15", "7501234567814", Decimal("95.00")),
    ("LEVOTIROXINA 100MCG AUDIT-16", "7501234567815", Decimal("72.00")),
    ("GABAPENTINA 300MG CAP AUDIT-17", "7501234567816", Decimal("180.00")),
    ("SERTRALINA 50MG TAB AUDIT-18", "7501234567817", Decimal("140.00")),
    ("HIDROCLOROTIAZIDA 25 AUDIT-19", "7501234567818", Decimal("15.00")),
    ("VITAMINA C 1G EFERV AUDIT-20", "7501234567819", Decimal("62.00")),
]


class Command(BaseCommand):
    help = "Inserta 20 productos de prueba PDV vinculados a una Empresa (id=1 por defecto)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id",
            type=int,
            default=1,
            help="ID de Empresa destino (default: 1)",
        )

    def handle(self, *args, **opts):
        eid = opts["empresa_id"]
        emp = Empresa.objects.filter(pk=eid).first()
        if not emp:
            emp = Empresa.objects.order_by("pk").first()
            if not emp:
                self.stderr.write(self.style.ERROR("No hay Empresa en la base de datos."))
                return
            self.stdout.write(self.style.WARNING(f"Empresa id={eid} no existe; usando id={emp.pk} ({emp})"))

        created = 0
        updated = 0
        with transaction.atomic():
            for nombre, cb, precio in AUDIT_CATALOG:
                obj, was_created = Producto.objects.update_or_create(
                    codigo_barras=cb,
                    defaults={
                        "empresa": emp,
                        "nombre": nombre,
                        "sustancia_activa": "AUDIT-SEED",
                        "forma_farmaceutica": "Tableta",
                        "concentracion": "Según envase",
                        "presentacion": "Caja prueba",
                        "precio_publico": precio,
                        "precio_compra": Decimal("10.00"),
                        "stock": 100,
                        "stock_minimo": 5,
                        "categoria": "GENERICO",
                        "es_antibiotico": "AMOX" in nombre.upper() or "AZITRO" in nombre.upper(),
                        "requiere_receta": False,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Empresa: [{emp.pk}] {emp}\nCreados: {created} | Actualizados: {updated}"
        ))
        self.stdout.write("\n--- Hoja de ruta (nombre | código) ---\n")
        for nombre, cb, _ in AUDIT_CATALOG:
            self.stdout.write(f"  {nombre} | {cb}")
