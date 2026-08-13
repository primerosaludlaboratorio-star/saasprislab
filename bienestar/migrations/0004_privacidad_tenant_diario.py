from django.db import migrations, models

import core.fields


def backfill_empresa_y_cifrar(apps, schema_editor):
    DiarioEmocional = apps.get_model('bienestar', 'DiarioEmocional')

    # Recupera el tenant desde el usuario y vuelve a guardar el contenido
    # mediante EncryptedTextField. Los usuarios sin empresa quedan aislados
    # hasta que un operador los regularice explícitamente.
    for entrada in DiarioEmocional.objects.select_related('usuario').iterator():
        cambios = []
        empresa_id = getattr(entrada.usuario, 'empresa_id', None)
        if empresa_id and entrada.empresa_id != empresa_id:
            entrada.empresa_id = empresa_id
            cambios.append('empresa')
        if entrada.contenido_privado is not None:
            cambios.append('contenido_privado')
        if cambios:
            entrada.save(update_fields=cambios)


class Migration(migrations.Migration):
    dependencies = [
        ('bienestar', '0003_diarioemocional_anonimizado_and_more'),
        ('core', '0108_configuracion_pin_validacion_laboratorio'),
    ]

    operations = [
        migrations.AddField(
            model_name='diarioemocional',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                help_text='Empresa propietaria; se recupera del usuario al guardar.',
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name='diarios_emocionales',
                to='core.empresa',
                verbose_name='Empresa',
            ),
        ),
        migrations.AddField(
            model_name='recursocrecimiento',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                help_text='Vacío significa recurso global publicado por la plataforma.',
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name='recursos_bienestar',
                to='core.empresa',
                verbose_name='Empresa',
            ),
        ),
        migrations.AlterField(
            model_name='diarioemocional',
            name='contenido_privado',
            field=core.fields.EncryptedTextField(
                help_text='Contenido privado cifrado con Fernet',
                verbose_name='Contenido Privado',
            ),
        ),
        migrations.RunPython(backfill_empresa_y_cifrar, migrations.RunPython.noop),
    ]
