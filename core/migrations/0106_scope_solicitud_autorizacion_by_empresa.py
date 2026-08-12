from django.db import migrations, models
import django.db.models.deletion


def backfill_empresa(apps, schema_editor):
    Solicitud = apps.get_model('core', 'SolicitudAutorizacion')
    Usuario = apps.get_model('core', 'Usuario')
    solicitudes = Solicitud.objects.filter(empresa__isnull=True).select_related('usuario_solicita')
    huerfanas = []
    for solicitud in solicitudes.iterator():
        empresa_id = Usuario.objects.filter(
            pk=solicitud.usuario_solicita_id,
        ).values_list('empresa_id', flat=True).first()
        if empresa_id is None:
            huerfanas.append(solicitud.pk)
            continue
        Solicitud.objects.filter(pk=solicitud.pk).update(empresa_id=empresa_id)
    if huerfanas:
        raise RuntimeError(
            'No se puede completar core.0106: solicitudes sin empresa: '
            + ','.join(str(pk) for pk in huerfanas[:20])
        )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0105_remove_hashraizdiario_core_hashra_fecha_8da07a_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudautorizacion',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='solicitudes_autorizacion',
                to='core.empresa',
                verbose_name='Empresa',
            ),
        ),
        migrations.RunPython(backfill_empresa, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='solicitudautorizacion',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='solicitudes_autorizacion',
                to='core.empresa',
                verbose_name='Empresa',
            ),
        ),
    ]
