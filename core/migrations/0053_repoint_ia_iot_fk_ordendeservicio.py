# Repunta FKs de ia/iot desde laboratorio_orden hacia core_ordendeservicio (PostgreSQL).
from django.db import migrations


def _repoint_fk_to_ods(schema_editor, table: str, column: str):
    conn = schema_editor.connection
    if conn.vendor != 'postgresql':
        return
    with conn.cursor() as cursor:
        names = conn.introspection.table_names(cursor=cursor)
        if table not in names:
            return
        cursor.execute(
            """
            SELECT tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_schema = kcu.constraint_schema
             AND tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = 'public'
              AND tc.table_name = %s
              AND tc.constraint_type = 'FOREIGN KEY'
              AND kcu.column_name = %s
            """,
            [table, column],
        )
        cnames = [row[0] for row in cursor.fetchall()]
        for cname in cnames:
            cursor.execute(
                'ALTER TABLE %s DROP CONSTRAINT IF EXISTS %s'
                % (conn.ops.quote_name(table), conn.ops.quote_name(cname))
            )
        cstr = f'{table}_{column}_fkey'
        cursor.execute(
            'ALTER TABLE %s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES core_ordendeservicio (id) DEFERRABLE INITIALLY DEFERRED'
            % (
                conn.ops.quote_name(table),
                conn.ops.quote_name(cstr),
                conn.ops.quote_name(column),
            )
        )


def forwards(apps, schema_editor):
    for tbl, col in (
        ('ia_cotizacionocr', 'orden_asociada_id'),
        ('ia_transcripcionvoz', 'orden_asociada_id'),
        ('iot_verificacionkiosco', 'orden_id'),
    ):
        _repoint_fk_to_ods(schema_editor, tbl, col)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0052_notificacionpanico_fk_ordendeservicio'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
