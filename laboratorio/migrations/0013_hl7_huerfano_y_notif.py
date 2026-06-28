# Punto 13 — Cola de cuarentena HL7 (ResultadoHL7Huerfano)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0064_consentimiento_marketing_y_orden_opcional'),
        ('lims', '0006_escudo_clinico_v114'),
        ('laboratorio', '0012_blindaje_hl7_admin_worm'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResultadoHL7Huerfano',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'motivo',
                    models.CharField(
                        choices=[
                            ('SIN_MAPEO_ANALITO', 'Codigo equipo sin match en LIMS'),
                            ('UNIDAD_INCOMPATIBLE', 'Unidad equipo distinta al catalogo'),
                            ('VALOR_NO_NUMERICO', 'Valor no convertible a Decimal (analito numerico)'),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                ('codigo_equipo', models.CharField(max_length=80)),
                ('valor_raw', models.CharField(max_length=200)),
                ('unidad_equipo', models.CharField(blank=True, max_length=80)),
                ('unidad_catalogo', models.CharField(blank=True, max_length=120)),
                ('item_json', models.TextField(help_text='Item parseado + meta (JSON)')),
                ('mensaje_contexto', models.TextField(blank=True, help_text='Extracto del mensaje crudo')),
                ('ip_equipo', models.GenericIPAddressField(blank=True, null=True)),
                ('protocolo', models.CharField(blank=True, max_length=10)),
                ('numero_orden_equipo', models.CharField(blank=True, max_length=80)),
                (
                    'estado_revision',
                    models.CharField(
                        choices=[
                            ('PENDIENTE', 'Pendiente revision QC'),
                            ('REVISADO', 'Revisado'),
                        ],
                        db_index=True,
                        default='PENDIENTE',
                        max_length=20,
                    ),
                ),
                ('creado', models.DateTimeField(auto_now_add=True)),
                (
                    'analito',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='hl7_huerfanos',
                        to='lims.analito',
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='hl7_huerfanos',
                        to='core.empresa',
                    ),
                ),
            ],
            options={
                'verbose_name': 'HL7 — resultado en cuarentena',
                'verbose_name_plural': 'HL7 — cola de cuarentena',
                'ordering': ['-creado'],
            },
        ),
        migrations.AddIndex(
            model_name='resultadohl7huerfano',
            index=models.Index(fields=['empresa', 'estado_revision', '-creado'], name='hl7huerf_emp_est_idx'),
        ),
    ]
