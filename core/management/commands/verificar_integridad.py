"""
Management Command: Verificar integridad de la base de datos tras restore o de forma periodica.
Cuenta registros en tablas clave, comprueba huerfanos (FK rotas) y secuencias.
"""
import logging
from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verifica integridad de la BD: conteos, huerfanos y secuencias.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Solo conteos en tablas clave (sin chequeo de huerfanos)',
        )

    def handle(self, *args, **options):
        quick = options.get('quick', False)
        errors = []
        warnings = []

        key_models = [
            ('core', 'Empresa'),
            ('core', 'Usuario'),
            ('core', 'Paciente'),
            ('core', 'OrdenDeServicio'),
            ('core', 'Venta'),
            ('core', 'Producto'),
        ]

        self.stdout.write(self.style.SUCCESS('\n=== VERIFICACION DE INTEGRIDAD ===\n'))

        self.stdout.write('1. Conteo en tablas clave:')
        for app_label, model_name in key_models:
            try:
                model = apps.get_model(app_label, model_name)
                count = model.objects.count()
                self.stdout.write('   %s.%s: %s' % (app_label, model_name, count))
                if model_name == 'Empresa' and count == 0:
                    errors.append('No hay ninguna Empresa.')
                if model_name == 'Usuario' and count == 0:
                    errors.append('No hay ningun Usuario.')
            except Exception as e:
                self.stdout.write(self.style.ERROR('   %s.%s: ERROR %s' % (app_label, model_name, e)))
                errors.append('%s.%s: %s' % (app_label, model_name, e))

        if not quick and connection.vendor == 'postgresql':
            self.stdout.write('\n2. Secuencias PostgreSQL:')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT sequencename, last_value
                        FROM pg_sequences
                        WHERE schemaname = 'public'
                        ORDER BY sequencename
                        LIMIT 20
                    """)
                    for seq_name, last_val in cursor.fetchall():
                        self.stdout.write('   %s: last_value=%s' % (seq_name, last_val))
            except Exception as e:
                warnings.append('Secuencias: %s' % e)

        if not quick:
            self.stdout.write('\n3. Muestra de chequeo de huerfanos (FK):')
            orphan_checks = [
                ('core', 'OrdenDeServicio', 'paciente_id', 'core', 'Paciente'),
                ('core', 'OrdenDeServicio', 'empresa_id', 'core', 'Empresa'),
                ('core', 'Venta', 'empresa_id', 'core', 'Empresa'),
                # CICLO 12: Phantom payments / registros huérfanos tras rollback
                ('core', 'Pago', 'venta', 'core', 'Venta'),
                ('core', 'DetalleVenta', 'venta', 'core', 'Venta'),
                ('core', 'PagoOrden', 'orden', 'core', 'OrdenDeServicio'),
                ('farmacia', 'MovimientoInventario', 'lote', 'core', 'Lote'),
            ]
            for app, model_name, fk_attr, parent_app, parent_model_name in orphan_checks:
                try:
                    model = apps.get_model(app, model_name)
                    parent = apps.get_model(parent_app, parent_model_name)
                    fk_field = model._meta.get_field(fk_attr)
                    related_column = fk_field.column
                    parent_table = parent._meta.db_table
                    parent_pk = parent._meta.pk.column
                    table = model._meta.db_table
                    # Nota: table/column vienen de model._meta (Django); en PostgreSQL son lowercase, seguros.
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT COUNT(*) FROM %s m
                            LEFT JOIN %s p ON m.%s = p.%s
                            WHERE p.%s IS NULL AND m.%s IS NOT NULL
                        """ % (table, parent_table, related_column, parent_pk, parent_pk, related_column))
                        orphan_count = cursor.fetchone()[0]
                    if orphan_count > 0:
                        self.stdout.write(self.style.WARNING('   %s.%s (%s): %s huerfanos' % (app, model_name, fk_attr, orphan_count)))
                        warnings.append('%s.%s: %s huerfanos en %s' % (app, model_name, orphan_count, fk_attr))
                    else:
                        self.stdout.write('   %s.%s (%s): OK' % (app, model_name, fk_attr))
                except Exception as e:
                    self.stdout.write(self.style.WARNING('   %s.%s: skip (%s)' % (app, model_name, e)))

        self.stdout.write('\n=== RESUMEN ===')
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR('  FAIL: %s' % e))
        if warnings:
            for w in warnings:
                self.stdout.write(self.style.WARNING('  WARN: %s' % w))
        if not errors and not warnings:
            self.stdout.write(self.style.SUCCESS('  OK: Integridad correcta.'))
        elif not errors:
            self.stdout.write(self.style.SUCCESS('  OK con advertencias.'))
        else:
            self.stdout.write(self.style.ERROR('  FALLOS detectados. Revisar antes de dar trafico a la app.'))
