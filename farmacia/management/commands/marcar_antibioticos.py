"""
Comando de gestión: marcar_antibioticos
Actualiza el campo es_antibiotico y clasificacion_sanitaria en los productos
de farmacia que corresponden a antibióticos o medicamentos controlados,
basándose en su nombre, sustancia activa o categoría.
"""
from django.core.management.base import BaseCommand
from farmacia.models import Producto

# Palabras clave para detectar antibióticos y controlados
ANTIBIOTICO_KEYWORDS = [
    'floxacino', 'cilina', 'micina', 'cicina', 'bactam', 'penem',
    'amoxicilina', 'ampicilina', 'azitromicina', 'claritromicina',
    'doxiciclina', 'tetraciclina', 'clindamicina', 'eritromicina',
    'vancomicina', 'trimetoprim', 'sulfametoxazol', 'nitrofurantoina',
    'ceftriaxona', 'cefuroxima', 'cefadroxilo', 'cefalexina',
    'imipenem', 'meropenem', 'levofloxacino', 'norfloxacino', 'ciprofloxacino',
    'metronidazol', 'fluconazol', 'tinidazol', 'itraconazol',
    'gentamicina', 'tobramicina', 'kanamicina', 'neomicina',
    'sulfato de gentamicina', 'penicilina', 'dicloxacilina', 'oxacilina',
]

CONTROLADO_KEYWORDS = [
    'tramadol', 'codeina', 'morfina', 'fentanilo', 'oxicodona',
    'alprazolam', 'diazepam', 'clonazepam', 'lorazepam', 'midazolam',
    'zolpidem', 'buprenorfina', 'metadona', 'pentobarbital',
    'anfetamina', 'metilfenidato',
]


class Command(BaseCommand):
    help = 'Marca es_antibiotico=True en productos que son antibióticos o controlados'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo mostrar, no guardar')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        updated = 0
        total = Producto.objects.count()

        for p in Producto.objects.all():
            texto = f"{p.nombre or ''} {p.sustancia_activa or ''}".lower()

            is_antibiotico = any(k in texto for k in ANTIBIOTICO_KEYWORDS)
            is_controlado = any(k in texto for k in CONTROLADO_KEYWORDS)

            needs_update = False
            if is_antibiotico or is_controlado:
                if not p.es_antibiotico:
                    p.es_antibiotico = True
                    needs_update = True
                if p.clasificacion_sanitaria != 'IV':
                    p.clasificacion_sanitaria = 'IV'
                    needs_update = True
                if is_antibiotico and p.categoria not in ('ANTIBIOTICO',):
                    p.categoria = 'ANTIBIOTICO'
                    needs_update = True

            if needs_update:
                updated += 1
                self.stdout.write(
                    f"  {'[DRY]' if dry_run else '[UPDATE]'} {p.nombre} "
                    f"(antibiotic={is_antibiotico}, controlado={is_controlado})"
                )
                if not dry_run:
                    p.save(update_fields=['es_antibiotico', 'clasificacion_sanitaria', 'categoria'])

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTotal productos: {total} | Actualizados: {updated} | Dry-run: {dry_run}"
            )
        )
