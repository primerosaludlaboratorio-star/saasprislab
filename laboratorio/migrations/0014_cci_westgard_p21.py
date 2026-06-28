# Punto 21 — CCI canónico + Westgard (deuda controlada §9.1: ancla core.0065)

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0065_forense_acceso_cofepris"),
        ("laboratorio", "0013_hl7_huerfano_y_notif"),
        ("lims", "0007_forense_acceso_cofepris"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialControl",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fabricante", models.CharField(max_length=200, verbose_name="Fabricante")),
                ("nombre", models.CharField(max_length=300, verbose_name="Nombre / referencia")),
                (
                    "descripcion_niveles",
                    models.CharField(
                        blank=True,
                        help_text="Ej. L1 Normal, L2 patologico alto",
                        max_length=500,
                        verbose_name="Niveles (texto)",
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                (
                    "analito",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="materiales_control",
                        to="lims.analito",
                        verbose_name="Analito LIMS",
                    ),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="materiales_control",
                        to="core.empresa",
                        verbose_name="Empresa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Material de control (CCI)",
                "verbose_name_plural": "Materiales de control (CCI)",
                "ordering": ["empresa", "fabricante", "nombre"],
            },
        ),
        migrations.CreateModel(
            name="LoteMaterialControl",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero_lote", models.CharField(max_length=120, verbose_name="Numero de lote")),
                (
                    "nivel",
                    models.CharField(
                        blank=True,
                        help_text="Ej. L1, L2, Alto",
                        max_length=50,
                        verbose_name="Nivel",
                    ),
                ),
                ("media", models.DecimalField(decimal_places=6, max_digits=16, verbose_name="Media (target)")),
                ("sd", models.DecimalField(decimal_places=6, max_digits=16, verbose_name="Desviacion estandar")),
                ("fecha_caducidad", models.DateField(blank=True, null=True, verbose_name="Caducidad")),
                ("activo", models.BooleanField(default=True)),
                (
                    "material",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lotes",
                        to="laboratorio.materialcontrol",
                        verbose_name="Material",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lote de material de control",
                "verbose_name_plural": "Lotes de material de control",
                "ordering": ["material", "numero_lote"],
            },
        ),
        migrations.CreateModel(
            name="MedicionControlInterno",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("valor", models.DecimalField(decimal_places=6, max_digits=16)),
                ("z_score", models.DecimalField(blank=True, decimal_places=6, max_digits=16, null=True)),
                ("reglas_disparadas", models.JSONField(blank=True, default=list)),
                ("westgard_estado", models.CharField(blank=True, default="", max_length=20)),
                (
                    "origen",
                    models.CharField(
                        choices=[("HL7", "HL7 / interfaz"), ("MANUAL", "Captura manual")],
                        default="HL7",
                        max_length=10,
                    ),
                ),
                ("fecha_medicion", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                (
                    "analito",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mediciones_cci",
                        to="lims.analito",
                    ),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mediciones_cci",
                        to="core.empresa",
                    ),
                ),
                (
                    "equipo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mediciones_cci",
                        to="laboratorio.equipo",
                    ),
                ),
                (
                    "lote_material",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mediciones",
                        to="laboratorio.lotematerialcontrol",
                    ),
                ),
            ],
            options={
                "verbose_name": "Medicion control interno",
                "verbose_name_plural": "Mediciones control interno",
                "ordering": ["-fecha_medicion"],
            },
        ),
        migrations.CreateModel(
            name="EstadoCanalAnalizador",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "estado_operativo",
                    models.CharField(
                        choices=[
                            ("NORMAL", "Normal"),
                            ("ALERTA_QC", "Alerta QC (Westgard rechazo)"),
                            ("BLOQUEO_METROLOGIA", "Bloqueo metrologia"),
                        ],
                        db_index=True,
                        default="NORMAL",
                        max_length=30,
                    ),
                ),
                ("motivo", models.TextField(blank=True, default="")),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                (
                    "analito",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="estados_canal",
                        to="lims.analito",
                    ),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="estados_canal_analizador",
                        to="core.empresa",
                    ),
                ),
                (
                    "equipo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="estados_canal",
                        to="laboratorio.equipo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Estado canal analizador",
                "verbose_name_plural": "Estados canal analizador",
            },
        ),
        migrations.AddConstraint(
            model_name="estadocanalanalizador",
            constraint=models.UniqueConstraint(
                fields=("empresa", "equipo", "analito"),
                name="lab_estcanal_emp_eq_an_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="materialcontrol",
            index=models.Index(fields=["empresa", "analito", "activo"], name="lab_mc_emp_an_act_idx"),
        ),
        migrations.AddConstraint(
            model_name="lotematerialcontrol",
            constraint=models.UniqueConstraint(
                fields=("material", "numero_lote", "nivel"),
                name="lab_lotemc_mat_lote_nivel_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="medicioncontrolinterno",
            index=models.Index(
                fields=["empresa", "equipo", "analito", "-fecha_medicion"],
                name="lab_mci_emp_eq_an_f_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="estadocanalanalizador",
            index=models.Index(
                fields=["empresa", "equipo", "estado_operativo"],
                name="lab_estcanal_emp_eq_st_idx",
            ),
        ),
    ]
