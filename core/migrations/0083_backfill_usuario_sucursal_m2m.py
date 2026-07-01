# Data migration: FK usuario.sucursal → M2M Usuario_Sucursal
# Migra todos los datos existentes desde la FK antigua hacia la tabla intermedia.

from django.db import migrations, models
from django.utils import timezone


def backfill_usuario_sucursal_m2m(apps, schema_editor):
    """
    Copia todas las asignaciones de usuario.sucursal (FK antigua) hacia
    la tabla intermediaria Usuario_Sucursal (M2M nueva).
    """
    Usuario = apps.get_model('core', 'Usuario')
    Usuario_Sucursal = apps.get_model('core', 'Usuario_Sucursal')

    # Obtener todos los usuarios que tienen una sucursal asignada
    usuarios_con_sucursal = Usuario.objects.filter(sucursal_id__isnull=False)

    for usuario in usuarios_con_sucursal:
        if usuario.sucursal_id:
            # Crear entrada en M2M con la sucursal actual
            Usuario_Sucursal.objects.get_or_create(
                usuario=usuario,
                sucursal_id=usuario.sucursal_id,
                defaults={
                    'activa': True,
                    'fecha_asignacion': timezone.now(),
                    'fecha_vencimiento': None,
                }
            )


def reverse_backfill(apps, schema_editor):
    """
    Reverso: limpia la tabla M2M (datos fueron copiados, no movidos).
    La FK antigua se mantiene para rollback.
    """
    Usuario_Sucursal = apps.get_model('core', 'Usuario_Sucursal')
    Usuario_Sucursal.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0082_usuario_sucursal_m2m'),
    ]

    operations = [
        migrations.RunPython(backfill_usuario_sucursal_m2m, reverse_backfill),
        migrations.RemoveField(
            model_name='usuario',
            name='sucursal',
        ),
        migrations.AddField(
            model_name='usuario',
            name='sucursales',
            field=models.ManyToManyField(
                blank=True,
                related_name='usuarios',
                through='core.Usuario_Sucursal',
                to='core.sucursal',
                verbose_name='Sucursales Asignadas',
            ),
        ),
    ]
