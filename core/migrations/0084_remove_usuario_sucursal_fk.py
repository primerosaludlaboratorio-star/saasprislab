# Elimina la FK antigua usuario.sucursal DESPUÉS del backfill de 0083.
# Reordenamiento respecto al diseño original: el borrado se separó de 0082 para
# no perder los datos existentes de usuario.sucursal (0082 lo borraba antes del
# backfill, lo que rompía el chain y descartaba los datos).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0083_backfill_usuario_sucursal_m2m'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usuario',
            name='sucursal',
        ),
    ]
