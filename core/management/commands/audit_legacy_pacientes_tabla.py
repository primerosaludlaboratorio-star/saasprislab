"""
Cuenta filas en la tabla física legacy `pacientes_paciente` (si existe).
Uso previo a migraciones que eliminen el modelo duplicado. Por defecto solo informa (dry-run).
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Cuenta registros en pacientes_paciente (legacy) si la tabla existe.'

    def handle(self, *args, **options):
        table = 'pacientes_paciente'
        with connection.cursor() as cursor:
            tables = connection.introspection.table_names(cursor=cursor)
        if table not in tables:
            self.stdout.write(
                self.style.SUCCESS(f'La tabla "{table}" no existe (omitir o ya migrado).')
            )
            return
        qn = connection.ops.quote_name(table)
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT COUNT(*) FROM {qn}')
            n = cursor.fetchone()[0]
        self.stdout.write(f'Filas en {table}: {n}')
        if n:
            self.stdout.write(
                self.style.WARNING(
                    'Hay datos legacy: no eliminar el modelo sin plan de migración de datos.'
                )
            )
