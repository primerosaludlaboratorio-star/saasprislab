import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from laboratorio.models import CategoriaExamen, Estudio


class Command(BaseCommand):
    help = "Importa/actualiza masivamente el catálogo de estudios desde tarifas.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            default='tarifas.csv',
            help='Nombre del archivo CSV en la raíz del proyecto (por defecto: tarifas.csv)',
        )

    def handle(self, *args, **options):
        archivo_nombre = options['archivo']
        base_dir = Path(getattr(settings, 'BASE_DIR', Path(__file__).resolve().parents[4]))
        ruta_csv = base_dir / archivo_nombre

        if not ruta_csv.exists():
            self.stderr.write(self.style.ERROR(f'No se encontró el archivo: {ruta_csv}'))
            return

        self.stdout.write(self.style.WARNING(f'Leyendo archivo: {ruta_csv}'))

        total_lineas = 0
        importados = 0
        actualizados_precio = 0

        with ruta_csv.open('r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)

            # Saltar basura hasta encontrar encabezado real
            for row in reader:
                total_lineas += 1
                if not row:
                    continue
                # Detectar encabezado por texto 'Tipo' y 'Código'
                if row[0].strip().lower() == 'tipo' and len(row) > 1:
                    col1 = row[1].strip().lower()
                    if col1 in ('código', 'codigo'):
                        break

            # Procesar filas de datos
            for row in reader:
                total_lineas += 1
                if not row or len(row) < 5:
                    continue

                tipo = (row[0] or '').strip()
                codigo = (row[1] or '').strip()
                abreviatura = (row[2] or '').strip() if len(row) > 2 else ''
                descripcion = (row[3] or '').strip()
                importe_raw = (row[4] or '').strip()

                if not codigo and not descripcion:
                    continue

                # Categoría
                if not tipo:
                    tipo = 'Sin categoría'
                categoria, _ = CategoriaExamen.objects.get_or_create(nombre=tipo)

                # Limpieza y conversión del precio
                precio = Decimal('0.00')
                if importe_raw:
                    try:
                        limpio = importe_raw.replace(',', '').replace('$', '').strip()
                        if limpio:
                            precio = Decimal(limpio)
                    except (InvalidOperation, ValueError):
                        precio = Decimal('0.00')

                # Crear / actualizar Estudio por código
                estudio_vals = {
                    'categoria': categoria,
                    'nombre': descripcion or codigo,
                    'precio_base': precio,
                }

                # Buscar por código exacto O por código en abreviatura
                estudio_existente = Estudio.objects.filter(codigo=codigo).first()
                if not estudio_existente and abreviatura:
                    estudio_existente = Estudio.objects.filter(codigo=abreviatura).first()

                if estudio_existente:
                    # Solo actualizar precio (lo más importante)
                    changed = False
                    if estudio_existente.precio_base != precio and precio > 0:
                        estudio_existente.precio_base = precio
                        changed = True
                        actualizados_precio += 1
                    if changed:
                        try:
                            estudio_existente.save(update_fields=['precio_base'])
                        except (DatabaseError, IntegrityError) as save_err:
                            self.stderr.write(f'  Warn: No se pudo actualizar {codigo}: {save_err}')
                else:
                    try:
                        Estudio.objects.create(
                            codigo=codigo,
                            categoria=categoria,
                            nombre=descripcion or codigo,
                            precio_base=precio,
                        )
                    except (DatabaseError, IntegrityError, ValidationError) as create_err:
                        # Si ya existe con esa combinación categoria+nombre, actualizar precio
                        try:
                            existing = Estudio.objects.filter(
                                categoria=categoria, nombre=descripcion or codigo
                            ).first()
                            if existing and precio > 0:
                                existing.precio_base = precio
                                existing.save(update_fields=['precio_base'])
                                actualizados_precio += 1
                        except (DatabaseError, IntegrityError, ValidationError):
                            self.stderr.write(f'  Warn: No se pudo crear/actualizar {codigo}: {create_err}')

                importados += 1
                if importados % 100 == 0:
                    self.stdout.write(f'{importados} estudios procesados...')

        self.stdout.write(self.style.SUCCESS(
            f'Importación completada. Estudios procesados: {importados}, '
            f'precios actualizados: {actualizados_precio}, líneas leídas: {total_lineas}'
        ))

