"""
Comando para sembrar 20 productos de prueba con stock real en Farmacia.
Idempotente: identifica por código de barras con prefijo TEST-PDV-.
Ejecutar: python manage.py seed_productos_prueba --empresa-id=<pk>
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from core.models import Producto
from farmacia.models import Lote


PRODUCTOS_TEST = [
    {
        "codigo": "TEST-PDV-001",
        "nombre": "PARACETAMOL 500MG TEST",
        "sustancia": "Paracetamol",
        "categoria": "Analgésico",
        "precio_compra": Decimal("8.50"),
        "precio_publico": Decimal("15.00"),
        "stock": 100,
    },
    {
        "codigo": "TEST-PDV-002",
        "nombre": "IBUPROFENO 400MG TEST",
        "sustancia": "Ibuprofeno",
        "categoria": "Analgésico",
        "precio_compra": Decimal("10.00"),
        "precio_publico": Decimal("22.00"),
        "stock": 80,
    },
    {
        "codigo": "TEST-PDV-003",
        "nombre": "AMOXICILINA 500MG TEST",
        "sustancia": "Amoxicilina",
        "categoria": "Antibiótico",
        "precio_compra": Decimal("25.00"),
        "precio_publico": Decimal("55.00"),
        "stock": 60,
        "es_antibiotico": True,
    },
    {
        "codigo": "TEST-PDV-004",
        "nombre": "OMEPRAZOL 20MG TEST",
        "sustancia": "Omeprazol",
        "categoria": "Gastrointestinal",
        "precio_compra": Decimal("12.00"),
        "precio_publico": Decimal("30.00"),
        "stock": 120,
    },
    {
        "codigo": "TEST-PDV-005",
        "nombre": "LORATADINA 10MG TEST",
        "sustancia": "Loratadina",
        "categoria": "Antihistamínico",
        "precio_compra": Decimal("6.00"),
        "precio_publico": Decimal("18.00"),
        "stock": 90,
    },
    {
        "codigo": "TEST-PDV-006",
        "nombre": "METFORMINA 850MG TEST",
        "sustancia": "Metformina",
        "categoria": "Antidiabético",
        "precio_compra": Decimal("9.00"),
        "precio_publico": Decimal("25.00"),
        "stock": 75,
    },
    {
        "codigo": "TEST-PDV-007",
        "nombre": "ATORVASTATINA 20MG TEST",
        "sustancia": "Atorvastatina",
        "categoria": "Cardiovascular",
        "precio_compra": Decimal("15.00"),
        "precio_publico": Decimal("45.00"),
        "stock": 50,
    },
    {
        "codigo": "TEST-PDV-008",
        "nombre": "LOSARTAN 50MG TEST",
        "sustancia": "Losartán Potásico",
        "categoria": "Cardiovascular",
        "precio_compra": Decimal("11.00"),
        "precio_publico": Decimal("32.00"),
        "stock": 65,
    },
    {
        "codigo": "TEST-PDV-009",
        "nombre": "VITAMINA C 1000MG TEST",
        "sustancia": "Ácido Ascórbico",
        "categoria": "Vitaminas",
        "precio_compra": Decimal("7.00"),
        "precio_publico": Decimal("20.00"),
        "stock": 150,
    },
    {
        "codigo": "TEST-PDV-010",
        "nombre": "CLONAZEPAM 0.5MG TEST",
        "sustancia": "Clonazepam",
        "categoria": "Controlado",
        "precio_compra": Decimal("18.00"),
        "precio_publico": Decimal("40.00"),
        "stock": 40,
        "requiere_receta": True,
    },
    {
        "codigo": "TEST-PDV-011",
        "nombre": "DEXAMETASONA 4MG TEST",
        "sustancia": "Dexametasona",
        "categoria": "Corticosteroide",
        "precio_compra": Decimal("14.00"),
        "precio_publico": Decimal("35.00"),
        "stock": 55,
    },
    {
        "codigo": "TEST-PDV-012",
        "nombre": "AZITROMICINA 500MG TEST",
        "sustancia": "Azitromicina",
        "categoria": "Antibiótico",
        "precio_compra": Decimal("30.00"),
        "precio_publico": Decimal("75.00"),
        "stock": 45,
        "es_antibiotico": True,
    },
    {
        "codigo": "TEST-PDV-013",
        "nombre": "RANITIDINA 150MG TEST",
        "sustancia": "Ranitidina",
        "categoria": "Gastrointestinal",
        "precio_compra": Decimal("8.00"),
        "precio_publico": Decimal("22.00"),
        "stock": 95,
    },
    {
        "codigo": "TEST-PDV-014",
        "nombre": "NAPROXENO 550MG TEST",
        "sustancia": "Naproxeno Sódico",
        "categoria": "Analgésico",
        "precio_compra": Decimal("9.50"),
        "precio_publico": Decimal("28.00"),
        "stock": 70,
    },
    {
        "codigo": "TEST-PDV-015",
        "nombre": "DICLOFENACO 100MG TEST",
        "sustancia": "Diclofenaco Sódico",
        "categoria": "Antiinflamatorio",
        "precio_compra": Decimal("7.50"),
        "precio_publico": Decimal("20.00"),
        "stock": 85,
    },
    {
        "codigo": "TEST-PDV-016",
        "nombre": "CETIRIZINA 10MG TEST",
        "sustancia": "Cetirizina",
        "categoria": "Antihistamínico",
        "precio_compra": Decimal("5.50"),
        "precio_publico": Decimal("16.00"),
        "stock": 110,
    },
    {
        "codigo": "TEST-PDV-017",
        "nombre": "FLUOXETINA 20MG TEST",
        "sustancia": "Fluoxetina",
        "categoria": "Antidepresivo",
        "precio_compra": Decimal("20.00"),
        "precio_publico": Decimal("50.00"),
        "stock": 35,
        "requiere_receta": True,
    },
    {
        "codigo": "TEST-PDV-018",
        "nombre": "SALBUTAMOL 100MCG TEST",
        "sustancia": "Salbutamol",
        "categoria": "Broncodilatador",
        "precio_compra": Decimal("45.00"),
        "precio_publico": Decimal("120.00"),
        "stock": 30,
    },
    {
        "codigo": "TEST-PDV-019",
        "nombre": "SUERO ORAL FARMACIA TEST",
        "sustancia": "Electrolitos orales",
        "categoria": "Hidratación",
        "precio_compra": Decimal("5.00"),
        "precio_publico": Decimal("12.00"),
        "stock": 200,
    },
    {
        "codigo": "TEST-PDV-020",
        "nombre": "MULTI VITAMINAS TEST",
        "sustancia": "Multivitamínico complejo",
        "categoria": "Vitaminas",
        "precio_compra": Decimal("35.00"),
        "precio_publico": Decimal("85.00"),
        "stock": 60,
    },
]


class Command(BaseCommand):
    help = "Siembra 20 productos de prueba con stock vigente para probar el PDV."

    def add_arguments(self, parser):
        from core.utils.tenant_strict import add_argument_empresa_id

        add_argument_empresa_id(parser, required=True)

    def handle(self, *args, **options):
        from core.utils.tenant_strict import empresa_desde_management

        from django.core.management.base import CommandError

        try:
            empresa = empresa_desde_management(options)
        except CommandError as e:
            self.stdout.write(self.style.ERROR(str(e)))
            return

        caducidad = date.today() + timedelta(days=730)  # 2 años
        creados = 0
        actualizados = 0

        for datos in PRODUCTOS_TEST:
            prod, created = Producto.objects.get_or_create(
                empresa=empresa,
                codigo_barras=datos["codigo"],
                defaults={
                    "nombre": datos["nombre"],
                    "sustancia_activa": datos["sustancia"],
                    "categoria": datos.get("categoria", "General"),
                    "precio_compra": datos["precio_compra"],
                    "precio_publico": datos["precio_publico"],
                    "iva_porcentaje": Decimal("0.00"),
                    "stock": datos["stock"],
                    "stock_minimo": 5,
                    "es_antibiotico": datos.get("es_antibiotico", False),
                    "requiere_receta": datos.get("requiere_receta", False),
                    "es_servicio": False,
                    "marca_laboratorio": "PRISLAB TEST",
                    "unidad_compra": "CAJA",
                    "unidad_venta": "PIEZA",
                    "factor_conversion": Decimal("1.00"),
                },
            )
            if not created:
                prod.nombre = datos["nombre"]
                prod.stock = datos["stock"]
                prod.precio_compra = datos["precio_compra"]
                prod.precio_publico = datos["precio_publico"]
                prod.save(update_fields=["nombre", "stock", "precio_compra", "precio_publico"])
                actualizados += 1
            else:
                creados += 1

            numero_lote = f"LOTE-TEST-{datos['codigo'][-3:]}"
            lote, lote_created = Lote.objects.get_or_create(
                producto=prod,
                numero_lote=numero_lote,
                defaults={
                    "fecha_fabricacion": date.today() - timedelta(days=30),
                    "fecha_caducidad": caducidad,
                    "cantidad": datos["stock"],
                    "costo_adquisicion": datos["precio_compra"],
                    "ubicacion_fisica": "A-1",
                },
            )
            if not lote_created:
                lote.cantidad = datos["stock"]
                lote.fecha_caducidad = caducidad
                lote.save(update_fields=["cantidad", "fecha_caducidad"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Productos TEST: {creados} creados, {actualizados} actualizados. "
                f"Empresa: {empresa.nombre}"
            )
        )
        self.stdout.write("")
        self.stdout.write("=== LISTA DE PRODUCTOS PRUEBA (búsqueda en PDV) ===")
        for p in PRODUCTOS_TEST:
            self.stdout.write(f"  [{p['codigo']}] {p['nombre']}  | stock: {p['stock']} | precio: ${p['precio_publico']}")
