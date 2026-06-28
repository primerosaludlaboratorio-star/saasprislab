"""
INVENTARIO V8.0 — Motor de Compras (Ordenes de Compra)
"""
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from .base import ProveedorCompras


# =============================================================================
# PARTE 4: MOTOR DE COMPRAS
# =============================================================================

class OrdenDeCompra(models.Model):
    """Orden de Compra (Purchase Order) consolidada para los 3 silos."""
    ESTADO_CHOICES = [
        ('BORRADOR',               'Borrador / Auto-generada'),
        ('PENDIENTE_DIRECTOR',     'Pendiente de Aprobación del Director'),
        ('APROBADA',               'Aprobada por el Director'),
        ('ENVIADA',                'Enviada al Proveedor'),
        ('PARCIALMENTE_RECIBIDA',  'Parcialmente Recibida'),
        ('COMPLETADA',             'Completada / Cerrada'),
        ('CANCELADA',              'Cancelada'),
    ]
    ORIGEN_CHOICES = [
        ('AUTOMATICA', 'Generada Automáticamente (Stock Mínimo)'),
        ('MANUAL',     'Creada Manualmente por el Director'),
    ]

    empresa   = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="ordenes_de_compra", verbose_name="Empresa",
    )
    folio     = models.CharField(
        max_length=30, verbose_name="Folio",
        help_text="Ej: OC-2026-001. Se genera automáticamente.",
    )
    proveedor = models.ForeignKey(
        ProveedorCompras, on_delete=models.PROTECT,
        related_name="ordenes_de_compra", verbose_name="Proveedor",
    )
    estado = models.CharField(
        max_length=25, choices=ESTADO_CHOICES, default="BORRADOR",
        verbose_name="Estado",
    )
    origen = models.CharField(
        max_length=15, choices=ORIGEN_CHOICES, default="AUTOMATICA",
        verbose_name="Origen de la OC",
    )

    subtotal = models.DecimalField(max_digits=14, decimal_places=4, default=0, verbose_name="Subtotal")
    iva      = models.DecimalField(max_digits=14, decimal_places=4, default=0, verbose_name="IVA")
    total    = models.DecimalField(max_digits=14, decimal_places=4, default=0, verbose_name="Total")

    generada_por   = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ordenes_compra_generadas", verbose_name="Generada por",
    )
    aprobada_por   = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ordenes_compra_aprobadas", verbose_name="Aprobada por",
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Generación")
    fecha_aprobacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Aprobación")
    fecha_envio      = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Envío")
    fecha_cierre     = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Cierre")

    notas_director   = models.TextField(
        blank=True, null=True, verbose_name="Notas del Director",
        help_text="Condiciones especiales, justificación de cancelación, etc.",
    )

    FORMA_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('TARJETA_EMPRESARIAL', 'Tarjeta Empresarial'),
        ('CREDITO', 'Crédito con proveedor'),
    ]
    factura_adjunta = models.FileField(
        upload_to='compras/facturas/%Y/%m/', null=True, blank=True,
        verbose_name="Factura del proveedor",
    )
    foto_evidencia = models.ImageField(
        upload_to='compras/evidencia/%Y/%m/', null=True, blank=True,
        verbose_name="Foto de evidencia (recepción de mercancía)",
    )
    forma_pago = models.CharField(
        max_length=25, blank=True, choices=FORMA_PAGO_CHOICES,
        verbose_name="Forma de pago",
    )
    referencia_transferencia = models.CharField(max_length=100, blank=True)
    pagada = models.BooleanField(default=False, verbose_name="Pagada")
    fecha_pago = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de pago")

    class Meta:
        verbose_name = "Orden de Compra"
        verbose_name_plural = "Órdenes de Compra"
        ordering = ["-fecha_generacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "folio"],
                name="inventario_ordendecompra_empresa_folio_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "estado", "-fecha_generacion"]),
        ]

    def __str__(self):
        return f"OC {self.folio} — {self.proveedor.razon_social} ({self.get_estado_display()})"

    def recalcular_totales(self):
        from django.db.models import Sum
        subtotal = self.lineas.aggregate(t=Sum("subtotal"))["t"] or 0
        self.subtotal = subtotal
        self.iva = round(subtotal * 0.16, 4)
        self.total = round(subtotal + self.iva, 4)
        self.save(update_fields=["subtotal", "iva", "total"])


class LineaOrdenCompra(models.Model):
    """Línea de artículo en una Orden de Compra usando GenericFK."""
    SILO_CHOICES = [
        ('LAB',         'Laboratorio (Reactivos / Calibradores / QC)'),
        ('CONSULTORIO', 'Consultorio (Material de Curación)'),
        ('GENERAL',     'Insumos Generales (Papelería / Limpieza)'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="lineas_orden_compra", verbose_name="Empresa",
    )
    orden   = models.ForeignKey(
        OrdenDeCompra, on_delete=models.CASCADE,
        related_name="lineas", verbose_name="Orden de Compra",
    )
    silo    = models.CharField(max_length=15, choices=SILO_CHOICES, verbose_name="Silo de Origen")

    content_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT,
        verbose_name="Tipo de Artículo",
        limit_choices_to={
            "app_label": "inventario",
            "model__in": [
                "catalogoreactivolab",
                "catalogoinsumoconsultorio",
                "catalogoinsumogeneral",
            ],
        },
    )
    object_id = models.PositiveIntegerField(verbose_name="ID del Artículo")
    articulo  = GenericForeignKey("content_type", "object_id")

    descripcion_snapshot    = models.CharField(
        max_length=300, verbose_name="Descripción (al generar OC)",
        help_text="Nombre del artículo en el momento de crear la OC. Inmutable.",
    )
    cantidad_solicitada     = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="Cantidad Solicitada"
    )
    unidad_medida           = models.CharField(max_length=20, verbose_name="Unidad")
    precio_unitario_estimado = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        verbose_name="Precio Unitario Estimado",
        help_text="Basado en el último precio de compra del catálogo.",
    )
    precio_unitario_real    = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name="Precio Unitario Real",
        help_text="Actualizado al confirmar la factura del proveedor.",
    )
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=4, default=0,
        verbose_name="Subtotal de Línea",
    )

    stock_al_generar   = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name="Stock al Generar OC",
        help_text="Stock disponible en el momento en que el sistema generó la OC.",
    )
    stock_minimo_config = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name="Stock Mínimo Configurado",
    )

    cantidad_recibida = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        verbose_name="Cantidad Recibida",
        help_text="Se actualiza al registrar lotes recibidos contra esta OC.",
    )

    class Meta:
        verbose_name = "Línea de Orden de Compra"
        verbose_name_plural = "Líneas de Órdenes de Compra"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["orden"]),
        ]

    def __str__(self):
        return f"OC {self.orden.folio} → {self.descripcion_snapshot} × {self.cantidad_solicitada}"

    def save(self, *args, **kwargs):
        precio = self.precio_unitario_real or self.precio_unitario_estimado
        self.subtotal = precio * self.cantidad_solicitada
        super().save(*args, **kwargs)
