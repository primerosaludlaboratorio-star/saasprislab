"""
INVENTARIO V8.0 — Silo Consultorio (uso interno médico/enfermería)
"""
from django.db import models

from .base import ProveedorCompras, UNIDAD_CHOICES


# =============================================================================
# PARTE 2: SILO CONSULTORIO
# =============================================================================

class CatalogoInsumoConsultorio(models.Model):
    """Catálogo de materiales de curación y consumibles de uso interno."""
    TIPO_CHOICES = [
        ('CURACION',    'Material de Curación (gasas, apósitos)'),
        ('INYECTABLE',  'Material Inyectable (jeringas, agujas)'),
        ('SOLUCIONES',  'Soluciones y Líquidos'),
        ('DIAGNOSTICO', 'Material de Diagnóstico (tiras, lancetas)'),
        ('EPP',         'Equipo de Protección Personal (guantes, cubrebocas)'),
        ('MEDICAMENTO', 'Medicamento de Uso Interno (no PDV)'),
        ('OTRO',        'Otro Material'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="insumos_consultorio",
        verbose_name="Empresa",
    )
    codigo_interno = models.CharField(max_length=50, verbose_name="Código Interno")
    nombre         = models.CharField(max_length=255, verbose_name="Nombre del Insumo")
    descripcion    = models.TextField(blank=True, null=True, verbose_name="Descripción")
    tipo           = models.CharField(max_length=15, choices=TIPO_CHOICES, verbose_name="Tipo")
    unidad_medida  = models.CharField(
        max_length=10, choices=UNIDAD_CHOICES, default="UNIDAD",
        verbose_name="Unidad de Medida",
    )
    stock_minimo = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Stock Mínimo"
    )
    stock_maximo = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        verbose_name="Stock Máximo"
    )
    proveedor_preferido = models.ForeignKey(
        ProveedorCompras,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="insumos_consultorio_preferidos",
        verbose_name="Proveedor Preferido",
    )
    precio_ultima_compra = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        verbose_name="Precio Última Compra",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    notas  = models.TextField(blank=True, null=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Insumo de Consultorio"
        verbose_name_plural = "Insumos de Consultorio"
        ordering = ["tipo", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo_interno"],
                name="inventario_insumoconsultorio_empresa_codigo_uniq",
            )
        ]
        indexes = [models.Index(fields=["empresa", "tipo", "activo"])]

    def __str__(self):
        return f"{self.codigo_interno} — {self.nombre}"

    def get_stock_disponible(self):
        return self.lotes.filter(cantidad_actual__gt=0).aggregate(
            total=models.Sum("cantidad_actual")
        )["total"] or 0

    @property
    def necesita_reorden(self):
        return self.get_stock_disponible() <= self.stock_minimo


class LoteInsumoConsultorio(models.Model):
    """Lote de insumo de consultorio. Tracking FEFO."""
    empresa        = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="lotes_insumo_consultorio", verbose_name="Empresa",
    )
    insumo         = models.ForeignKey(
        CatalogoInsumoConsultorio, on_delete=models.PROTECT,
        related_name="lotes", verbose_name="Insumo",
    )
    numero_lote    = models.CharField(max_length=120, blank=True, null=True, verbose_name="Número de Lote")
    fecha_caducidad = models.DateField(blank=True, null=True, verbose_name="Fecha de Caducidad")
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cantidad Inicial")
    cantidad_actual  = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cantidad Actual")
    precio_unitario_compra = models.DecimalField(
        max_digits=10, decimal_places=4, default=0, verbose_name="Precio Unitario de Compra"
    )
    orden_compra = models.ForeignKey(
        "inventario.OrdenDeCompra",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lotes_consultorio_generados",
        verbose_name="Orden de Compra de Origen",
    )
    fecha_recepcion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Recepción")
    recibido_por    = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lotes_consultorio_recibidos", verbose_name="Recibido por",
    )

    class Meta:
        verbose_name = "Lote de Insumo de Consultorio"
        verbose_name_plural = "Lotes de Insumos de Consultorio"
        ordering = ["fecha_caducidad"]
        indexes = [models.Index(fields=["insumo", "cantidad_actual"])]

    def __str__(self):
        return f"{self.insumo.nombre} / L:{self.numero_lote or 'S/L'}"


class SalidaConsumoConsultorio(models.Model):
    """Registro de uso de insumo en consultorio durante la atención de un paciente."""
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="salidas_consumo_consultorio", verbose_name="Empresa",
    )
    lote     = models.ForeignKey(
        LoteInsumoConsultorio, on_delete=models.PROTECT,
        related_name="salidas", verbose_name="Lote Consumido",
    )
    cantidad = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Cantidad Consumida")
    cita     = models.ForeignKey(
        "consultorio.AgendaCita",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consumos_insumos",
        verbose_name="Cita Médica",
    )
    motivo         = models.CharField(max_length=255, verbose_name="Motivo / Procedimiento")
    registrado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="salidas_consultorio_registradas", verbose_name="Registrado por",
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha / Hora")

    class Meta:
        verbose_name = "Consumo de Insumo de Consultorio"
        verbose_name_plural = "Consumos de Insumos de Consultorio"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["empresa", "-fecha"]),
            models.Index(fields=["lote"]),
        ]

    def __str__(self):
        return f"{self.cantidad} × {self.lote.insumo.nombre} — {self.fecha:%Y-%m-%d}"
