# v1.51 — Paso 1/2 (SQLite): quitar solo unique_together que referencian `estudio` en tablas legacy.
#
# La migración monolítica que mezclaba RemoveField/DeleteModel con estas restricciones provocaba
# fallos al reconstruir tablas (FieldDoesNotExist: Parametro.estudio). Estudio no tenía
# unique_together en el estado 0071 (solo unique en el campo `codigo`).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0071_sucursal_gestion_inventario_activa'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='convenioprecioestudio',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='parametro',
            unique_together=set(),
        ),
    ]
