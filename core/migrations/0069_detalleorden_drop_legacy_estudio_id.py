# Elimina columna legada estudio_id en DetalleOrden si aún existe en BD (ORM LIMS v7.5 sin ese campo).

from django.db import migrations


def _drop_legacy_estudio_id(apps, schema_editor):
    conn = schema_editor.connection
    table = 'core_detalleorden'
    col = 'estudio_id'
    with conn.cursor() as cursor:
        if conn.vendor == 'postgresql':
            cursor.execute(
                f'ALTER TABLE {conn.ops.quote_name(table)} '
                f'DROP COLUMN IF EXISTS {conn.ops.quote_name(col)}'
            )
            return
        if conn.vendor == 'sqlite':
            cursor.execute('PRAGMA table_info(core_detalleorden)')
            names = [row[1] for row in cursor.fetchall()]
            if col not in names:
                return
            cursor.execute('PRAGMA index_list(core_detalleorden)')
            for row in cursor.fetchall():
                idx_name = row[1]
                cursor.execute(f'PRAGMA index_info({idx_name!r})')
                cols = [r[2] for r in cursor.fetchall()]
                if col in cols:
                    cursor.execute(f'DROP INDEX IF EXISTS {idx_name}')
            cursor.execute('ALTER TABLE core_detalleorden DROP COLUMN estudio_id')


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0068_detalleorden_lims_fk_columns'),
    ]

    operations = [
        migrations.RunPython(_drop_legacy_estudio_id, _noop_reverse),
    ]
