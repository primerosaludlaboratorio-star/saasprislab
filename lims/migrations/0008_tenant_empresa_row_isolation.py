from django.db import migrations, models


def backfill_lims_empresa(apps, schema_editor):
    Empresa = apps.get_model('core', 'Empresa')
    Analito = apps.get_model('lims', 'Analito')
    PerfilLims = apps.get_model('lims', 'PerfilLims')
    PaqueteLims = apps.get_model('lims', 'PaqueteLims')
    PrecioItem = apps.get_model('lims', 'PrecioItem')

    empresa_ids = list(Empresa.objects.values_list('id', flat=True))
    empresa_unica_id = empresa_ids[0] if len(empresa_ids) == 1 else None

    if empresa_unica_id:
        Analito.objects.filter(empresa__isnull=True).update(empresa_id=empresa_unica_id)
        PerfilLims.objects.filter(empresa__isnull=True).update(empresa_id=empresa_unica_id)
        PaqueteLims.objects.filter(empresa__isnull=True).update(empresa_id=empresa_unica_id)

    for precio in PrecioItem.objects.filter(empresa__isnull=True).iterator():
        empresa_id = None
        if getattr(precio, 'analito_id', None):
            empresa_id = Analito.objects.filter(pk=precio.analito_id).values_list('empresa_id', flat=True).first()
        elif getattr(precio, 'perfil_id', None):
            empresa_id = PerfilLims.objects.filter(pk=precio.perfil_id).values_list('empresa_id', flat=True).first()
        elif getattr(precio, 'paquete_id', None):
            empresa_id = PaqueteLims.objects.filter(pk=precio.paquete_id).values_list('empresa_id', flat=True).first()
        if empresa_id:
            PrecioItem.objects.filter(pk=precio.pk).update(empresa_id=empresa_id)

    pendientes = (
        Analito.objects.filter(empresa__isnull=True).exists()
        or PerfilLims.objects.filter(empresa__isnull=True).exists()
        or PaqueteLims.objects.filter(empresa__isnull=True).exists()
        or PrecioItem.objects.filter(empresa__isnull=True).exists()
    )
    if pendientes:
        raise RuntimeError(
            'No fue posible backfillear empresa en LIMS de forma segura. '
            'Ejecute `python manage.py lims_amnistia_empresa` tras 0007b y vuelva a migrar.'
        )


class Migration(migrations.Migration):
    """
    Depende solo de 0007 para alinear BD que aplicaron esta migración antes de existir 0007b.
    Los AddField nullable van aquí (antes eran 0007b) para installs limpios.
    """

    dependencies = [
        ('core', '0074_pagoorden_empresa_tenant_guard'),
        ('lims', '0007_forense_acceso_cofepris'),
    ]

    operations = [
        migrations.AddField(
            model_name='analito',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='analitos_lims',
                to='core.empresa',
            ),
        ),
        migrations.AddField(
            model_name='paquetelims',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='paquetes_lims',
                to='core.empresa',
            ),
        ),
        migrations.AddField(
            model_name='perfillims',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='perfiles_lims',
                to='core.empresa',
            ),
        ),
        migrations.AddField(
            model_name='precioitem',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='precios_lims',
                to='core.empresa',
            ),
        ),
        migrations.RunPython(backfill_lims_empresa, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='analito',
            name='empresa',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='analitos_lims',
                to='core.empresa',
            ),
        ),
        migrations.AlterField(
            model_name='paquetelims',
            name='empresa',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='paquetes_lims',
                to='core.empresa',
            ),
        ),
        migrations.AlterField(
            model_name='perfillims',
            name='empresa',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='perfiles_lims',
                to='core.empresa',
            ),
        ),
        migrations.AlterField(
            model_name='precioitem',
            name='empresa',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='precios_lims',
                to='core.empresa',
            ),
        ),
    ]
