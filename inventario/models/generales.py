"""
INVENTARIO V8.0 — Silo Insumos Generales y Vales de Requisición
"""
from django.db import models

from .base import ProveedorCompras, UNIDAD_CHOICES, AREA_CHOICES


# =============================================================================
# PARTE 3: SILO INSUMOS GENERALES
# =============================================================================

class CatalogoInsumoGeneral(models.Model):
    """Catálogo de insumos generales: papelería, limpieza, informática, etc."""
    CATEGORIA_CHOICES = [
        ('PAPELERIA',       'Papelería y Oficina'),
        ('LIMPIEZA',        'Limpieza e Higiene'),
        ('INFORMATICA',     'Informática y Tecnología'),
        ('INFRAESTRUCTURA', 'Infraestructura / Mantenimiento'),
        ('CAFETERIA',       'Cafetería y Comedor'),
        ('UNIFORME',        'Uniformes y Vestuario'),
        ('OTRO',            'Otro'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="insumos_generales", verbose_name="Empresa",
    )
    codigo_interno  = models.CharField(max_length=50, verbose_name="Código Interno")
    nombre          = models.CharField(max_length=255, verbose_name="Nombre del Artículo")
    descripcion     = models.TextField(blank=True, null=True, verbose_name="Descripción")
    categoria       = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, verbose_name="Categoría")
    area_principal  = models.CharField(
        max_length=20, choices=AREA_CHOICES, default="GENERAL",
        verbose_name="Área Principal de Uso",
    )
    unidad_medida   = models.CharField(max_length=50, verbose_name="Unidad de Medida")
    stock_minimo    = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Stock Mínimo"
    )
    stock_maximo    = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Stock Máximo"
    )
    proveedor_preferido = models.ForeignKey(
        ProveedorCompras,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="insumos_generales_preferidos",
        verbose_name="Proveedor Preferido",
    )
    precio_ultima_compra = models.DecimalField(
        max_digits=10, decimal_places=4, default=0, verbose_name="Precio Última Compra"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    notas  = models.TextField(blank=True, null=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Insumo General"
        verbose_name_plural = "Insumos Generales"
        ordering = ["categoria", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo_interno"],
                name="inventario_insumogeneral_empresa_codigo_uniq",
            )
        ]
        indexes = [models.Index(fields=["empresa", "categoria", "activo"])]

    def __str__(self):
        return f"{self.codigo_interno} — {self.nombre} [{self.get_categoria_display()}]"

    def get_stock_disponible(self):
        return self.lotes.filter(cantidad_actual__gt=0).aggregate(
            total=models.Sum("cantidad_actual")
        )["total"] or 0

    @property
    def necesita_reorden(self):
        return self.get_stock_disponible() <= self.stock_minimo


class LoteInsumoGeneral(models.Model):
    """Lote de insumo general recibido."""
    empresa   = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="lotes_insumo_general", verbose_name="Empresa",
    )
    insumo    = models.ForeignKey(
        CatalogoInsumoGeneral, on_delete=models.PROTECT,
        related_name="lotes", verbose_name="Insumo",
    )
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cantidad Inicial")
    cantidad_actual  = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cantidad Actual")
    precio_unitario_compra = models.DecimalField(
        max_digits=10, decimal_places=4, default=0, verbose_name="Precio Unitario de Compra"
    )
    orden_compra = models.ForeignKey(
        "inventario.OrdenDeCompra",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lotes_general_generados",
        verbose_name="Orden de Compra de Origen",
    )
    fecha_recepcion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Recepción")
    recibido_por    = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lotes_general_recibidos", verbose_name="Recibido por",
    )

    class Meta:
        verbose_name = "Lote de Insumo General"
        verbose_name_plural = "Lotes de Insumos Generales"
        ordering = ["-fecha_recepcion"]
        indexes = [models.Index(fields=["insumo", "cantidad_actual"])]

    def __str__(self):
        return f"{self.insumo.nombre} — Lote recibido {self.fecha_recepcion:%Y-%m-%d}"


class ValeRequisicion(models.Model):
    """Vale de Requisición Interna para insumos generales."""
    ESTADO_CHOICES = [
        ('BORRADOR',  'Borrador'),
        ('PENDIENTE', 'Pendiente de Aprobación'),
        ('APROBADO',  'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('ENTREGADO', 'Entregado / Despachado'),
        ('CANCELADO', 'Cancelado'),
    ]

    empresa   = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="vales_requisicion", verbose_name="Empresa",
    )
    folio = models.CharField(
        max_length=30, verbose_name="Folio",
        help_text="Ej: REQ-2026-001. Se genera automáticamente.",
    )
    area_solicitante = models.CharField(
        max_length=20, choices=AREA_CHOICES, verbose_name="Área Solicitante"
    )
    solicitado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="vales_solicitados", verbose_name="Solicitado por",
    )
    aprobado_por = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="vales_aprobados", verbose_name="Aprobado / Rechazado por",
    )
    estado            = models.CharField(max_length=15, choices=ESTADO_CHOICES, default="BORRADOR")
    fecha_solicitud   = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_aprobacion  = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Aprobación")
    fecha_entrega     = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Entrega")
    observaciones     = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    razon_rechazo     = models.TextField(
        blank=True, null=True, verbose_name="Razón de Rechazo",
        help_text="Obligatorio si el estado es RECHAZADO.",
    )

    class Meta:
        verbose_name = "Vale de Requisición Interna"
        verbose_name_plural = "Vales de Requisición Interna"
        ordering = ["-fecha_solicitud"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "folio"],
                name="inventario_valerequisicion_empresa_folio_uniq",
            )
        ]
        indexes = [models.Index(fields=["empresa", "estado", "-fecha_solicitud"])]

    def __str__(self):
        return f"Vale {self.folio} — {self.area_solicitante} ({self.get_estado_display()})"


class LineaValeRequisicion(models.Model):
    """Línea (artículo) dentro de un Vale de Requisición."""
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="lineas_vale_requisicion", verbose_name="Empresa",
    )
    vale    = models.ForeignKey(
        ValeRequisicion, on_delete=models.CASCADE,
        related_name="lineas", verbose_name="Vale",
    )
    insumo  = models.ForeignKey(
        CatalogoInsumoGeneral, on_delete=models.PROTECT,
        related_name="lineas_requisicion", verbose_name="Insumo Solicitado",
    )
    cantidad_solicitada = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Cantidad Solicitada"
    )
    cantidad_entregada  = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Cantidad Entregada"
    )
    lote_entregado = models.ForeignKey(
        LoteInsumoGeneral,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="entregas_vale",
        verbose_name="Lote Entregado",
        help_text="Se asigna al despachar, siguiendo FEFO.",
    )
    observaciones = models.CharField(max_length=255, blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Línea de Vale de Requisición"
        verbose_name_plural = "Líneas de Vale de Requisición"
        unique_together = [("vale", "insumo")]

    def __str__(self):
        return f"Vale {self.vale.folio} → {self.insumo.nombre} × {self.cantidad_solicitada}"
