from django.db import migrations


def install_append_only_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    schema_editor.execute(
        """
        CREATE OR REPLACE FUNCTION prislab_reject_append_only_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'Append-only table % cannot be updated or deleted', TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$;
        """
    )
    for table, trigger in (
        ('core_auditlog', 'core_auditlog_append_only'),
        ('core_forenseacceso', 'core_forenseacceso_append_only'),
    ):
        schema_editor.execute(f'DROP TRIGGER IF EXISTS {trigger} ON {table};')
        schema_editor.execute(
            f"""
            CREATE TRIGGER {trigger}
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION prislab_reject_append_only_mutation();
            """
        )


def remove_append_only_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for table, trigger in (
        ('core_auditlog', 'core_auditlog_append_only'),
        ('core_forenseacceso', 'core_forenseacceso_append_only'),
    ):
        schema_editor.execute(f'DROP TRIGGER IF EXISTS {trigger} ON {table};')
    schema_editor.execute('DROP FUNCTION IF EXISTS prislab_reject_append_only_mutation();')


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0087_resultadoparametro_equipo'),
    ]

    operations = [
        migrations.RunPython(install_append_only_triggers, remove_append_only_triggers),
    ]
