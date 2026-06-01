from django.db import migrations


def _repair_client_mutation_schema(apps, schema_editor):
    connection = schema_editor.connection
    introspection = connection.introspection
    OrdenDeServicio = apps.get_model('core', 'OrdenDeServicio')
    PagoOrden = apps.get_model('core', 'PagoOrden')

    def _column_names(table_name):
        with connection.cursor() as cursor:
            description = introspection.get_table_description(cursor, table_name)
        return {col.name for col in description}

    def _constraint_names(table_name):
        with connection.cursor() as cursor:
            constraints = introspection.get_constraints(cursor, table_name)
        return set(constraints.keys())

    orden_table = OrdenDeServicio._meta.db_table
    pago_table = PagoOrden._meta.db_table

    orden_field = OrdenDeServicio._meta.get_field('client_mutation_id')
    pago_field = PagoOrden._meta.get_field('client_mutation_id')

    orden_cols = _column_names(orden_table)
    if 'client_mutation_id' not in orden_cols:
        schema_editor.add_field(OrdenDeServicio, orden_field)

    pago_cols = _column_names(pago_table)
    if 'client_mutation_id' not in pago_cols:
        schema_editor.add_field(PagoOrden, pago_field)

    orden_constraints = _constraint_names(orden_table)
    for constraint in OrdenDeServicio._meta.constraints:
        if constraint.name == 'unique_orden_client_mutation_per_empresa' and constraint.name not in orden_constraints:
            schema_editor.add_constraint(OrdenDeServicio, constraint)

    pago_constraints = _constraint_names(pago_table)
    for constraint in PagoOrden._meta.constraints:
        if constraint.name == 'unique_pago_orden_client_mutation' and constraint.name not in pago_constraints:
            schema_editor.add_constraint(PagoOrden, constraint)


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0069_detalleorden_drop_legacy_estudio_id'),
    ]

    operations = [
        migrations.RunPython(_repair_client_mutation_schema, _noop_reverse),
    ]
