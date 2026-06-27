"""
INVENTARIO V8.0 — Silo Laboratorio (ISO 15189)
Reactivos · Calibradores · Controles de Calidad · Consumibles
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date

from .base import ProveedorCompras, UNIDAD_CHOICES


# =============================================================================
# PARTE 1: SILO LABORATORIO — ISO 15189
# =============================================================================

class CatalogoReactivoLab(models.Model):
    """
    Catálogo maestro de reactivos, calibradores, controles y consumibles
    analíticos del laboratorio.
    """
    TIPO_CHOICES = [
        ('REACTIVO',       'Reactivo Analítico'),
        ('CALIBRADOR',     'Calibrador'),
        ('CONTROL_QC',     'Control de Calidad (QC)'),
        ('CONSUMIBLE',     'Consumible Analítico (tubos, puntas, etc.)'),
        ('REFACCION',      'Refacción de Equipo (lámpara, filtro, etc.)'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="reactivos_lab",
        verbose_name="Empresa",
    )
    codigo_interno = models.CharField(
        max_length=50, verbose_name="Código Interno",
        help_text="Código único del artículo dentro de la empresa.",
    )
    nombre      = models.CharField(max_length=255, verbose_name="Nombre del Artículo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción Técnica")
    tipo        = models.CharField(
        max_length=15, choices=TIPO_CHOICES, default="REACTIVO",
        verbose_name="Tipo de Artículo",
    )
    fabricante            = models.CharField(max_length=200, blank=True, null=True, verbose_name="Fabricante")
    referencia_fabricante = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Referencia del Fabricante",
        help_text="Número de catálogo del fabricante (REF).",
    )
    unidad_medida = models.CharField(
        max_length=10, choices=UNIDAD_CHOICES, default="UNIDAD",
        verbose_name="Unidad de Medida",
    )
    temperatura_almacenamiento = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Temperatura de Almacenamiento",
        help_text="Ej: '2-8°C', '-20°C', 'Temperatura ambiente (15-25°C)'.",
    )
    requiere_cadena_frio = models.BooleanField(
        default=False, verbose_name="Requiere Cadena de Frío",
    )

    stock_minimo = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        verbose_name="Stock Mínimo",
        help_text="Al llegar a este nivel se genera una Orden de Compra automática.",
    )
    stock_maximo = models.DecimalField(
        max_digits=10, decimal_places=4, blank=True, null=True,
        verbose_name="Stock Máximo",
        help_text="Cantidad máxima recomendada en el almacén.",
    )

    proveedor_preferido = models.ForeignKey(
        ProveedorCompras,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reactivos_preferidos", verbose_name="Proveedor Preferido",
    )
    precio_ultima_compra = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        verbose_name="Precio Última Compra",
    )

    activo = models.BooleanField(default=True, verbose_name="Artículo Activo")
    notas  = models.TextField(blank=True, null=True, verbose_name="Notas Técnicas")

    class Meta:
        verbose_name = "Reactivo / Insumo de Laboratorio"
        verbose_name_plural = "Reactivos / Insumos de Laboratorio"
        ordering = ["tipo", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo_interno"],
                name="inventario_reactivolab_empresa_codigo_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "tipo", "activo"]),
        ]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.codigo_interno} — {self.nombre}"

    def get_stock_disponible(self):
        return self.lotes.filter(
            estado__in=["ACTIVO", "CUARENTENA"]
        ).aggregate(
            total=models.Sum("cantidad_actual")
        )["total"] or 0

    @property
    def necesita_reorden(self):
        return self.get_stock_disponible() <= self.stock_minimo


class ConsumoEstudioReactivo(models.Model):
    """Fórmula de consumo ISO 15189: cuánto reactivo consume cada analito LIMS."""
    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="consumos_estudio_reactivo",
        verbose_name="Empresa",
    )
    analito = models.ForeignKey(
        "lims.Analito",
        on_delete=models.CASCADE,
        related_name="consumos_reactivos",
        verbose_name="Analito LIMS",
    )
    reactivo = models.ForeignKey(
        CatalogoReactivoLab,
        on_delete=models.CASCADE,
        related_name="consumos_por_estudio",
        verbose_name="Reactivo",
    )
    cantidad_por_prueba = models.DecimalField(
        max_digits=10, decimal_places=4,
        verbose_name="Cantidad por Ejecución",
        help_text="Volumen/unidades consumidas al procesar 1 resultado de este estudio.",
    )
    unidad = models.CharField(
        max_length=10, choices=UNIDAD_CHOICES, default="UL",
        verbose_name="Unidad de la Cantidad",
    )
    incluye_overhead_qc = models.BooleanField(
        default=False,
        verbose_name="Incluye Overhead de QC",
        help_text="Si True, la cantidad ya contempla el volumen promedio de controles.",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Fórmula de Consumo Reactivo por Estudio"
        verbose_name_plural = "Fórmulas de Consumo Reactivo por Estudio"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "analito", "reactivo"],
                name="inventario_consumo_estudio_reactivo_uniq",
            )
        ]

    def __str__(self):
        return f"{self.analito} → {self.cantidad_por_prueba} {self.unidad} de {self.reactivo}"


class LoteReactivoLab(models.Model):
    """Lote físico de un reactivo recibido en el almacén. FEFO."""
    ESTADO_CHOICES = [
        ('CUARENTENA', 'En Cuarentena (Pendiente de QC)'),
        ('ACTIVO',     'Activo — En Uso'),
        ('AGOTADO',    'Agotado'),
        ('VENCIDO',    'Vencido'),
        ('BAJA',       'Dado de Baja (Merma/Incidente)'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="lotes_reactivo_lab",
        verbose_name="Empresa",
    )
    reactivo       = models.ForeignKey(
        CatalogoReactivoLab,
        on_delete=models.PROTECT,
        related_name="lotes",
        verbose_name="Reactivo",
    )
    numero_lote    = models.CharField(max_length=120, verbose_name="Número de Lote")
    fecha_caducidad = models.DateField(verbose_name="Fecha de Caducidad")
    fecha_apertura  = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Apertura",
        help_text="Fecha en que se abrió/comenzó a usar el lote.",
    )
    cantidad_inicial = models.DecimalField(
        max_digits=12, decimal_places=4,
        verbose_name="Cantidad Inicial (al recibir)",
    )
    cantidad_actual = models.DecimalField(
        max_digits=12, decimal_places=4,
        verbose_name="Cantidad Actual",
        help_text="Se actualiza automáticamente con cada Salida registrada.",
    )

    proveedor            = models.ForeignKey(
        ProveedorCompras,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lotes_reactivo", verbose_name="Proveedor",
    )
    precio_unitario_compra = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        verbose_name="Precio Unitario de Compra",
    )
    costo_total_lote = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        verbose_name="Costo Total del Lote",
    )
    orden_compra = models.ForeignKey(
        "inventario.OrdenDeCompra",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lotes_reactivo_generados",
        verbose_name="Orden de Compra de Origen",
    )

    lote_aprobado_qc   = models.BooleanField(default=False, verbose_name="Aprobado por QC")
    aprobado_por       = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lotes_reactivo_aprobados_qc", verbose_name="Aprobado por (QC)",
    )
    fecha_aprobacion_qc = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Aprobación QC")
    observaciones_qc    = models.TextField(blank=True, null=True, verbose_name="Observaciones de QC")

    estado       = models.CharField(
        max_length=15, choices=ESTADO_CHOICES, default="CUARENTENA",
        verbose_name="Estado del Lote",
    )
    fecha_recepcion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Recepción")
    recibido_por    = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lotes_reactivo_recibidos", verbose_name="Recibido por",
    )

    class Meta:
        verbose_name = "Lote de Reactivo de Laboratorio"
        verbose_name_plural = "Lotes de Reactivos de Laboratorio"
        ordering = ["fecha_caducidad"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "reactivo", "numero_lote"],
                name="inventario_lotereactivolab_empresa_reactivo_lote_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "estado", "fecha_caducidad"]),
            models.Index(fields=["reactivo", "estado"]),
        ]

    def __str__(self):
        return f"{self.reactivo.codigo_interno} / L:{self.numero_lote} — cad:{self.fecha_caducidad}"

    def clean(self):
        if self.cantidad_actual < 0:
            raise ValidationError("La cantidad actual no puede ser negativa.")
        if self.cantidad_actual > self.cantidad_inicial:
            raise ValidationError(
                "La cantidad actual no puede superar la cantidad inicial del lote."
            )

    def save(self, *args, **kwargs):
        self.costo_total_lote = self.cantidad_inicial * self.precio_unitario_compra
        super().save(*args, **kwargs)

    @property
    def semaforo(self):
        if self.estado in ('VENCIDO', 'BAJA', 'AGOTADO') or self.estado == 'CUARENTENA':
            return 'rojo'
        if self.fecha_caducidad:
            dias = (self.fecha_caducidad - date.today()).days
            if dias < 0:
                return 'rojo'
            if dias <= 30:
                return 'amarillo'
        return 'verde'


class SalidaAnaliticaLab(models.Model):
    """Descuento automático de reactivo al validar un resultado."""
    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="salidas_analiticas_lab",
        verbose_name="Empresa",
    )
    lote = models.ForeignKey(
        LoteReactivoLab,
        on_delete=models.PROTECT,
        related_name="salidas_analiticas",
        verbose_name="Lote Consumido",
    )
    orden = models.ForeignKey(
        "core.OrdenDeServicio",
        on_delete=models.PROTECT,
        related_name="salidas_analiticas_reactivos",
        verbose_name="Orden de Servicio",
    )
    analito = models.ForeignKey(
        "lims.Analito",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="salidas_analiticas",
        verbose_name="Analito LIMS",
    )
    formula_consumo = models.ForeignKey(
        ConsumoEstudioReactivo,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="salidas_generadas",
        verbose_name="Fórmula de Consumo Usada",
    )
    cantidad_consumida = models.DecimalField(
        max_digits=10, decimal_places=4,
        verbose_name="Cantidad Consumida",
    )
    validado_por = models.ForeignKey(
        "core.Usuario",
        on_delete=models.PROTECT,
        related_name="salidas_analiticas_registradas",
        verbose_name="Validado por",
    )
    idempotency_key = models.CharField(
        max_length=190,
        unique=True,
        verbose_name="Clave de idempotencia",
        help_text="Determinista: lab_rp{resultado_id}_f{formula_id}_l{lote_id}.",
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha / Hora")

    class Meta:
        verbose_name = "Descuento Analítico de Reactivo"
        verbose_name_plural = "Descuentos Analíticos de Reactivos"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["empresa", "-fecha"]),
            models.Index(fields=["lote", "-fecha"]),
            models.Index(fields=["orden"]),
        ]

    def __str__(self):
        return f"Orden #{self.orden_id} → {self.cantidad_consumida} de {self.lote}"


class SalidaTecnicaLab(models.Model):
    """Descuento manual de reactivo / refacción por mantenimiento, calibración, etc."""
    TIPO_CHOICES = [
        ('MANTENIMIENTO',   'Mantenimiento Preventivo / Correctivo'),
        ('CALIBRACION',     'Calibración de Equipo'),
        ('CONTROL_CALIDAD', 'Control de Calidad (fuera de worklist)'),
        ('MERMA',           'Merma / Caducidad / Derrame'),
        ('DONACION',        'Donación / Préstamo Inter-laboratorio'),
        ('OTRO',            'Otro'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="salidas_tecnicas_lab",
        verbose_name="Empresa",
    )
    lote = models.ForeignKey(
        LoteReactivoLab,
        on_delete=models.PROTECT,
        related_name="salidas_tecnicas",
        verbose_name="Lote Afectado",
    )
    tipo     = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Descuento")
    cantidad = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Cantidad")
    motivo   = models.TextField(verbose_name="Motivo / Descripción")

    ticket_mantenimiento = models.ForeignKey(
        "core.MantenimientoEquipo",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="salidas_tecnicas_reactivos",
        verbose_name="Ticket de Mantenimiento",
    )
    registrado_por = models.ForeignKey(
        "core.Usuario",
        on_delete=models.PROTECT,
        related_name="salidas_tecnicas_registradas",
        verbose_name="Registrado por",
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha / Hora")

    class Meta:
        verbose_name = "Descuento Técnico de Reactivo"
        verbose_name_plural = "Descuentos Técnicos de Reactivos"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["empresa", "-fecha"]),
            models.Index(fields=["lote"]),
        ]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.cantidad} de {self.lote} — {self.fecha:%Y-%m-%d}"
