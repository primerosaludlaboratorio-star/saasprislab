# Generated manually — laboratorio no tiene grafo de migraciones; el modelo apunta a core.OrdenDeServicio.
from django.db import migrations


def _repoint_notificacion_panico_orden_fk(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor != 'postgresql':
        return
    with conn.cursor() as cursor:
        names = conn.introspection.table_names(cursor=cursor)
    if 'laboratorio_notificacionpanico' not in names:
        return
    table = 'laboratorio_notificacionpanico'
    col = 'orden_id'
    with conn.cursor() as cursor:
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
            [table, col],
        )
        rows = cursor.fetchall()
        for (cname,) in rows:
            cursor.execute(
                'ALTER TABLE laboratorio_notificacionpanico DROP CONSTRAINT IF EXISTS %s'
                % conn.ops.quote_name(cname)
            )
        cursor.execute(
            """
            ALTER TABLE laboratorio_notificacionpanico
            ADD CONSTRAINT laboratorio_notificacionpanico_orden_id_fkey
            FOREIGN KEY (orden_id) REFERENCES core_ordendeservicio (id)
            DEFERRABLE INITIALLY DEFERRED
            """
        )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0051_farmacia_tenant_lote_detalleventalote'),
    ]

    operations = [
        migrations.RunPython(_repoint_notificacion_panico_orden_fk, _noop_reverse),
    ]
