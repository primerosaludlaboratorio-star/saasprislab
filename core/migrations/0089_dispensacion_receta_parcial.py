from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0088_append_only_audit_forense'),
    ]

    operations = [
        migrations.CreateModel(
            name='DispensacionReceta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad_prescrita', models.PositiveIntegerField()),
                ('cantidad_surtida', models.PositiveIntegerField()),
                ('cantidad_pendiente', models.PositiveIntegerField(default=0)),
                ('motivo_parcial', models.CharField(blank=True, choices=[('PRESUPUESTO_INSUFICIENTE', 'Presupuesto insuficiente'), ('DECISION_PACIENTE', 'Decisión del paciente'), ('SIN_EXISTENCIA', 'Existencia insuficiente'), ('OTRO', 'Otro')], max_length=40, null=True)),
                ('observaciones', models.TextField(blank=True, default='')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('detalle_venta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='dispensaciones_receta', to='core.detalleventa')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dispensaciones_receta', to='core.empresa')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.producto')),
                ('receta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='dispensaciones', to='core.receta')),
                ('receta_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dispensaciones', to='core.recetaitem')),
                ('sucursal', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.sucursal')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='dispensaciones_receta', to='core.usuario')),
                ('venta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='dispensaciones_receta', to='core.venta')),
            ],
            options={
                'ordering': ['-creado_en'],
                'indexes': [
                    models.Index(fields=['empresa', 'receta', 'producto'], name='core_dispen_empresa_71e0e2_idx'),
                    models.Index(fields=['venta', 'producto'], name='core_dispen_venta_i_ce26a7_idx'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='dispensacionreceta',
            constraint=models.CheckConstraint(check=models.Q(('cantidad_surtida__lte', models.F('cantidad_prescrita'))), name='dispensacion_surtida_no_supera_prescrita'),
        ),
        migrations.AddConstraint(
            model_name='dispensacionreceta',
            constraint=models.CheckConstraint(check=models.Q(('cantidad_pendiente__lte', models.F('cantidad_prescrita'))), name='dispensacion_pendiente_no_supera_prescrita'),
        ),
    ]
