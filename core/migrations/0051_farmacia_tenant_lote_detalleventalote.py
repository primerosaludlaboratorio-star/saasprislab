# Generated manually — Lote.empresa (backfill), DetalleVentaLote, Empresa.farmacia_dias_max_antiguedad_receta

import django.db.models.deletion
from django.db import migrations, models


def backfill_lote_empresa(apps, schema_editor):
    Lote = apps.get_model("core", "Lote")
    Producto = apps.get_model("core", "Producto")
    for lote in Lote.objects.all().iterator():
        pid = lote.producto_id
        if not pid:
            continue
        eid = Producto.objects.filter(pk=pid).values_list("empresa_id", flat=True).first()
        if eid:
            Lote.objects.filter(pk=lote.pk).update(empresa_id=eid)


def backfill_detalleventalote(apps, schema_editor):
    DetalleVenta = apps.get_model("core", "DetalleVenta")
    DetalleVentaLote = apps.get_model("core", "DetalleVentaLote")
    for d in DetalleVenta.objects.filter(lote_vendido_id__isnull=False).iterator():
        DetalleVentaLote.objects.get_or_create(
            detalle_venta_id=d.id,
            lote_id=d.lote_vendido_id,
            defaults={"cantidad_extraida": d.cantidad},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0050_lims_parametro_develab_v6"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="farmacia_dias_max_antiguedad_receta",
            field=models.PositiveSmallIntegerField(
                default=30,
                help_text="Rechazo de dispensación si la receta supera estos días (política COFEPRIS / institucional).",
                verbose_name="Farmacia: antigüedad máxima de receta (días)",
            ),
        ),
        migrations.AddField(
            model_name="lote",
            name="empresa",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lotes_inventario",
                to="core.empresa",
                verbose_name="Empresa (tenant)",
            ),
        ),
        migrations.RunPython(backfill_lote_empresa, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="lote",
            name="empresa",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lotes_inventario",
                to="core.empresa",
                verbose_name="Empresa (tenant)",
            ),
        ),
        migrations.AddIndex(
            model_name="lote",
            index=models.Index(fields=["empresa", "fecha_caducidad"], name="core_lote_empresa_cad_idx"),
        ),
        migrations.CreateModel(
            name="DetalleVentaLote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "cantidad_extraida",
                    models.PositiveIntegerField(
                        help_text="Unidades enteras retiradas de este lote para esta partida.",
                        verbose_name="Cantidad extraída de este lote",
                    ),
                ),
                (
                    "detalle_venta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lotes_extraidos",
                        to="core.detalleventa",
                        verbose_name="Partida de venta",
                    ),
                ),
                (
                    "lote",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="detalles_venta_consumo",
                        to="core.lote",
                        verbose_name="Lote surtido",
                    ),
                ),
            ],
            options={
                "verbose_name": "Detalle venta por lote (trazabilidad)",
                "verbose_name_plural": "Detalle ventas por lote",
            },
        ),
        migrations.AddIndex(
            model_name="detalleventalote",
            index=models.Index(fields=["detalle_venta", "lote"], name="core_dvl_det_lote_idx"),
        ),
        migrations.RunPython(backfill_detalleventalote, migrations.RunPython.noop),
    ]
