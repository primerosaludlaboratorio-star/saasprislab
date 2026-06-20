"""
MÓDULO INVENTARIO V8.0 — ARQUITECTURA DE SILOS INDEPENDIENTES
==============================================================
Autor: Arquitecto Senior PRISLAB
Normativa: COFEPRIS · ISO 15189 · NOM-072-SSA1-2012 · NOM-005-STPS

PRINCIPIO DE AISLAMIENTO LEGAL:
  ● SILO FARMACIA (app: farmacia) — COFEPRIS / Venta al público — INTOCABLE.
  ● SILO LABORATORIO      → Reactivos, Calibradores, Controles QC, Consumibles Analíticos.
  ● SILO CONSULTORIO      → Material de curación de uso interno médico/enfermería.
  ● SILO INSUMOS GENERALES→ Papelería, Limpieza, Infraestructura, Administración.
  ● MOTOR DE COMPRAS      → Consolidación directiva; lee los 3 silos vía GenericFK.

REGLA MULTI-TENANT:
  Cada modelo lleva `empresa = ForeignKey("core.Empresa")`.
  Toda consulta pública debe filtrar por empresa del usuario en sesión.
  Los modelos NO incluyen lógica de filtrado automático; eso es responsabilidad
  del middleware de empresa y de las vistas (siguiendo el patrón del sistema).

CONVENCIÓN DE STOCK:
  El stock disponible se calcula como:
      Σ(entradas) − Σ(salidas) por lote.
  El campo `cantidad_actual` en cada Lote se mantiene actualizado mediante
  las señales `post_save` de cada modelo de Salida (a implementar en signals.py).
  Para el Director, el stock consolidado se obtiene anotando los lotes activos.
"""
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CHOICES COMPARTIDAS (evitan duplicación entre silos)
# =============================================================================

UNIDAD_CHOICES = [
    # Volumen analítico
    ('ML',    'Mililitros (mL)'),
    ('UL',    'Microlitros (µL)'),
    ('L',     'Litros (L)'),
    # Masa
    ('G',     'Gramos (g)'),
    ('MG',    'Miligramos (mg)'),
    # Unidades discretas
    ('UNIDAD', 'Unidad (pza)'),
    ('KIT',    'Kit completo'),
    ('CAJA',   'Caja'),
    ('PAQUETE','Paquete'),
    ('ROLLO',  'Rollo'),
    ('PAR',    'Par'),
    ('SOBRE',  'Sobre'),
    ('TIRA',   'Tira / Strip'),
    # Especiales
    ('LITRO_L','Litro (L)'),
    ('OTRO',   'Otra unidad'),
]

AREA_CHOICES = [
    ('LABORATORIO',    'Laboratorio'),
    ('CONSULTORIO',    'Consultorio'),
    ('FARMACIA',       'Farmacia'),
    ('RECEPCION',      'Recepción'),
    ('ADMINISTRACION', 'Administración'),
    ('INTENDENCIA',    'Intendencia / Limpieza'),
    ('GENERAL',        'General / Toda la instalación'),
]


# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  PARTE 0: PROVEEDOR COMPARTIDO (3 silos nuevos)                        │
# │  NOTA: NO modifica ni extiende farmacia.Proveedor (COFEPRIS).          │
# │  Este proveedor es exclusivo para Lab, Consultorio e Insumos Generales.│
# └─────────────────────────────────────────────────────────────────────────┘
# =============================================================================

class ProveedorCompras(models.Model):
    """
    Catálogo de proveedores para los silos de Laboratorio, Consultorio e
    Insumos Generales.

    Aislado del modelo farmacia.Proveedor (que cumple regulación COFEPRIS).
    Este modelo cumple los requisitos de trazabilidad de la ISO 15189 para
    proveedores de reactivos y materiales analíticos.
    """
    TIPO_CHOICES = [
        ('REACTIVOS',         'Distribuidor de Reactivos / IVD'),
        ('MATERIAL_MEDICO',   'Distribuidor de Material Médico'),
        ('PAPELERIA',         'Proveedor de Papelería / Oficina'),
        ('LIMPIEZA',          'Proveedor de Limpieza / Higiene'),
        ('INFORMATICA',       'Proveedor de Informática / Tecnología'),
        ('INFRAESTRUCTURA',   'Proveedor de Infraestructura'),
        ('OTRO',              'Otro'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="proveedores_compras",
        verbose_name="Empresa",
    )
    razon_social = models.CharField(max_length=255, verbose_name="Razón Social")
    nombre_comercial = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Nombre Comercial"
    )
    rfc = models.CharField(max_length=13, verbose_name="RFC")
    tipo = models.CharField(
        max_length=20, choices=TIPO_CHOICES, default="OTRO",
        verbose_name="Tipo de Proveedor",
    )
    telefono   = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email      = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    contacto_nombre = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Nombre del Contacto"
    )
    dias_credito = models.IntegerField(
        default=0, verbose_name="Días de Crédito",
        help_text="0 = Contado. 30 = 30 días, etc."
    )
    activo     = models.BooleanField(default=True, verbose_name="Proveedor Activo")
    notas      = models.TextField(blank=True, null=True, verbose_name="Notas Internas")
    fecha_alta = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Alta")

    class Meta:
        verbose_name = "Proveedor (Inventario)"
        verbose_name_plural = "Proveedores (Inventario)"
        ordering = ["razon_social"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "rfc"],
                name="inventario_proveedor_empresa_rfc_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "activo"]),
        ]

    def __str__(self):
        return f"{self.razon_social} ({self.rfc})"


# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  PARTE 1: SILO LABORATORIO — ISO 15189                                 │
# │  Reactivos · Calibradores · Controles de Calidad · Consumibles         │
# │  ÚNICA vía de salida: Analítica (automática) o Técnica (mantenimiento) │
# │  PROHIBIDA la venta al público — no existe PDV en este silo.           │
# └─────────────────────────────────────────────────────────────────────────┘
# =============================================================================

class CatalogoReactivoLab(models.Model):
    """
    Catálogo maestro de reactivos, calibradores, controles y consumibles
    analíticos del laboratorio.

    ISO 15189 §6.6: Gestión de reactivos y material fungible.
    Cada artículo puede vincularse a uno o más Estudios mediante
    ConsumoEstudioReactivo para el descuento automático.
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

    # --- Control de Stock ---
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

    # --- Economía ---
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
        """
        Suma de `cantidad_actual` de todos los lotes ACTIVOS.
        Para reportes en tiempo real usar agregación ORM en la vista:
            CatalogoReactivoLab.objects.annotate(
                stock=Sum('lotes__cantidad_actual', filter=Q(lotes__estado='ACTIVO'))
            )
        """
        return self.lotes.filter(
            estado__in=["ACTIVO", "CUARENTENA"]
        ).aggregate(
            total=models.Sum("cantidad_actual")
        )["total"] or 0

    @property
    def necesita_reorden(self):
        """True si el stock disponible cayó al mínimo configurado."""
        return self.get_stock_disponible() <= self.stock_minimo


class ConsumoEstudioReactivo(models.Model):
    """
    Fórmula de consumo ISO 15189: cuánto reactivo consume cada analito LIMS
    al validarse un resultado.
    """
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
    """
    Lote físico de un reactivo recibido en el almacén.
    Tracking FEFO (First Expired, First Out) por fecha de caducidad.
    Sujeto a aprobación de QC antes de ser usado (ISO 15189 §6.6.2).
    """
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

    # --- Trazabilidad de compra ---
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

    # --- Validación QC (ISO 15189 §6.6.2) ---
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
        ordering = ["fecha_caducidad"]   # FEFO
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
        """Actualiza precio total del lote al crear/editar."""
        self.costo_total_lote = self.cantidad_inicial * self.precio_unitario_compra
        super().save(*args, **kwargs)


class SalidaAnaliticaLab(models.Model):
    """
    Descuento AUTOMÁTICO de reactivo generado cuando el Químico valida
    un resultado en la Worklist (ISO 15189 §5.8 — Fase Analítica).

    Este registro se crea mediante una señal post_save conectada a
    ResultadoParametro (cuando validado=True) o por la vista de validación
    masiva de la Worklist.

    Garantiza la trazabilidad completa del consumo analítico por orden.
    """
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
        help_text="Referencia a la fórmula que determinó la cantidad a descontar.",
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
        help_text="Determinista: lab_rp{resultado_id}_f{formula_id}_l{lote_id}. Evita doble descuento bajo concurrencia.",
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
    """
    Descuento MANUAL de reactivo / refacción por mantenimiento, calibración,
    control de calidad fuera de worklist, o merma por incidente.

    Vinculable a un Ticket de Mantenimiento (MantenimientoEquipo) cuando
    el Módulo de Ingeniería lo requiera.
    """
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

    # Hook para módulo de Ingeniería (FK opcional — sin romper integridad)
    ticket_mantenimiento = models.ForeignKey(
        "core.MantenimientoEquipo",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="salidas_tecnicas_reactivos",
        verbose_name="Ticket de Mantenimiento",
        help_text="Vincular cuando la salida corresponde a un mantenimiento registrado.",
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


# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  PARTE 2: SILO CONSULTORIO — Uso Interno Médico/Enfermería             │
# │  Gasas · Jeringas · Soluciones · EPP · Material de Curación           │
# │  Salida: vinculada a consulta / cita del paciente, sin cobro directo.  │
# └─────────────────────────────────────────────────────────────────────────┘
# =============================================================================

class CatalogoInsumoConsultorio(models.Model):
    """
    Catálogo de materiales de curación y consumibles de uso interno del
    consultorio médico y enfermería.

    NO es un PDV. La salida de este silo nunca genera un cargo directo en caja;
    el costo se absorbe operativamente o se distribuye por cita.
    """
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
        ordering = ["fecha_caducidad"]   # FEFO
        indexes = [models.Index(fields=["insumo", "cantidad_actual"])]

    def __str__(self):
        return f"{self.insumo.nombre} / L:{self.numero_lote or 'S/L'}"


class SalidaConsumoConsultorio(models.Model):
    """
    Registro de uso de insumo en consultorio durante la atención de un paciente.
    Vinculable a una cita médica (AgendaCita) como justificante operativo.
    """
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
        help_text="Cita durante la cual se utilizó el insumo.",
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


# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  PARTE 3: SILO INSUMOS GENERALES — Papelería · Limpieza · Admin       │
# │  Salida exclusivamente por Vale de Requisición autorizado.             │
# └─────────────────────────────────────────────────────────────────────────┘
# =============================================================================

class CatalogoInsumoGeneral(models.Model):
    """
    Catálogo de insumos generales: papelería, limpieza, informática,
    infraestructura y cualquier artículo administrativo.
    """
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
    """
    Vale de Requisición Interna: el mecanismo formal de solicitud de insumos
    generales por parte de cualquier área.

    Flujo: BORRADOR → PENDIENTE → APROBADO → ENTREGADO
           (o RECHAZADO / CANCELADO en cualquier punto).

    Solo el Director o el Responsable de Almacén puede aprobar.
    """
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


# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  PARTE 4: MOTOR DE COMPRAS — Visión Directiva                         │
# │  Lee los 3 silos. GenericFK para referenciar cualquier catálogo.      │
# │  PO generada automáticamente cuando un artículo llega a stock_minimo. │
# │  REQUIERE aprobación del Director antes de enviarse al proveedor.     │
# └─────────────────────────────────────────────────────────────────────────┘
# =============================================================================

class OrdenDeCompra(models.Model):
    """
    Orden de Compra (Purchase Order) consolidada.

    Puede agrupar artículos de los 3 silos nuevos, filtrados por el mismo
    proveedor para emitir un único documento de pedido.

    Ciclo de vida:
        BORRADOR → PENDIENTE_DIRECTOR → APROBADA → ENVIADA
        → PARCIALMENTE_RECIBIDA → COMPLETADA
        (o CANCELADA en cualquier etapa pre-envío)
    """
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

    # --- Totales financieros (calculados al guardar) ---
    subtotal = models.DecimalField(max_digits=14, decimal_places=4, default=0, verbose_name="Subtotal")
    iva      = models.DecimalField(max_digits=14, decimal_places=4, default=0, verbose_name="IVA")
    total    = models.DecimalField(max_digits=14, decimal_places=4, default=0, verbose_name="Total")

    # --- Trazabilidad de aprobación ---
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

    # --- Control de pago y evidencia (Contabilidad Personal del Director) ---
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
        """Recalcula subtotal, IVA y total desde las líneas."""
        from django.db.models import Sum
        subtotal = self.lineas.aggregate(t=Sum("subtotal"))["t"] or 0
        self.subtotal = subtotal
        self.iva = round(subtotal * 0.16, 4)
        self.total = round(subtotal + self.iva, 4)
        self.save(update_fields=["subtotal", "iva", "total"])


class LineaOrdenCompra(models.Model):
    """
    Línea de artículo en una Orden de Compra.

    Usa GenericForeignKey para referenciar cualquier catálogo de los 3 silos:
      · CatalogoReactivoLab     (silo = 'LAB')
      · CatalogoInsumoConsultorio (silo = 'CONSULTORIO')
      · CatalogoInsumoGeneral   (silo = 'GENERAL')

    El campo `descripcion_snapshot` guarda el nombre del artículo al momento
    de generar la OC, garantizando inmutabilidad histórica.
    """
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

    # --- Referencia genérica al catálogo del silo ---
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

    # --- Datos económicos ---
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

    # --- Snapshot de stock al momento de generar la OC ---
    stock_al_generar   = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name="Stock al Generar OC",
        help_text="Stock disponible en el momento en que el sistema generó la OC.",
    )
    stock_minimo_config = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name="Stock Mínimo Configurado",
    )

    # --- Recepción parcial ---
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
        """Recalcula subtotal al guardar."""
        precio = self.precio_unitario_real or self.precio_unitario_estimado
        self.subtotal = precio * self.cantidad_solicitada
        super().save(*args, **kwargs)


# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  PARTE 5: LOGÍSTICA INTER-SEDES — Traspasos + Notificaciones V8.3      │
# │  TraspasoInventario: mueve stock entre sucursales con firma PIN.        │
# │  NotificacionDiscrepancia: alerta automática al Director en recepciones.│
# └─────────────────────────────────────────────────────────────────────────┘
# =============================================================================

class TraspasoInventario(models.Model):
    """
    Traspaso de stock entre sucursales (empresas del mismo grupo) o entre
    almacenes internos de la misma empresa.

    Flujo de vida:
        BORRADOR → EN_TRANSITO → RECIBIDO
                               → RECHAZADO  (receptor rechaza con justificación)
        (o CANCELADO antes de EN_TRANSITO)

    El stock:
        · Sale del silo ORIGEN al pasar a EN_TRANSITO.
        · Entra al silo DESTINO solo al pasar a RECIBIDO (firma PIN del receptor).
        · Si RECHAZADO, el stock regresa al silo ORIGEN automáticamente.
    """
    SILO_CHOICES = [
        ('LAB',         'Laboratorio (Reactivos / Calibradores)'),
        ('CONSULTORIO', 'Consultorio (Material de Curación)'),
        ('GENERAL',     'Insumos Generales (Papelería / Limpieza)'),
    ]
    ESTADO_CHOICES = [
        ('BORRADOR',     'Borrador'),
        ('EN_TRANSITO',  'En Tránsito'),
        ('RECIBIDO',     'Recibido y Confirmado'),
        ('RECHAZADO',    'Rechazado por Receptor'),
        ('CANCELADO',    'Cancelado'),
    ]

    # Empresa origen y empresa destino (pueden ser la misma — almacén distinto)
    empresa_origen  = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="traspasos_enviados", verbose_name="Empresa Origen",
    )
    empresa_destino = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="traspasos_recibidos", verbose_name="Empresa Destino",
    )
    silo = models.CharField(max_length=15, choices=SILO_CHOICES, verbose_name="Silo")

    folio = models.CharField(max_length=30, verbose_name="Folio")
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES,
                               default="BORRADOR", verbose_name="Estado")
    motivo = models.TextField(verbose_name="Motivo del Traspaso")

    # Trazabilidad
    solicitado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="traspasos_solicitados", verbose_name="Solicitado por",
    )
    despachado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="traspasos_despachados", verbose_name="Despachado por",
    )
    receptor = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="traspasos_recibidos_personal", verbose_name="Receptor (firma PIN)",
    )
    razon_rechazo = models.TextField(blank=True, null=True, verbose_name="Razón de Rechazo")

    # Timestamps
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Solicitud")
    fecha_despacho  = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Despacho")
    fecha_recepcion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Recepción")

    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Traspaso de Inventario"
        verbose_name_plural = "Traspasos de Inventario"
        ordering = ["-fecha_solicitud"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_origen", "folio"],
                name="inventario_traspaso_empresa_folio_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["empresa_origen", "estado"]),
            models.Index(fields=["empresa_destino", "estado"]),
        ]

    def __str__(self):
        return (f"Traspaso {self.folio} — {self.silo} "
                f"{self.empresa_origen} → {self.empresa_destino} ({self.get_estado_display()})")


class LineaTraspasoInventario(models.Model):
    """
    Línea de artículo dentro de un TraspasoInventario.
    Referencia directamente al Lote de origen para garantizar trazabilidad FEFO.
    """
    SILO_LOTE_CHOICES = [
        ('LAB',         'Silo Laboratorio'),
        ('CONSULTORIO', 'Silo Consultorio'),
        ('GENERAL',     'Silo Generales'),
    ]

    traspaso = models.ForeignKey(
        TraspasoInventario, on_delete=models.CASCADE,
        related_name="lineas", verbose_name="Traspaso",
    )
    empresa_origen = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="lineas_traspaso_origen", verbose_name="Empresa Origen",
    )
    silo = models.CharField(max_length=15, choices=SILO_LOTE_CHOICES)

    # Referencia al lote específico (GenericFK multi-silo)
    lote_content_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT,
        verbose_name="Tipo de Lote",
        limit_choices_to={"app_label": "inventario",
                          "model__in": ["lotereactivolab",
                                        "loteinsumoconsultorio",
                                        "loteinsumogeneral"]},
    )
    lote_object_id  = models.PositiveIntegerField(verbose_name="ID del Lote")
    lote            = GenericForeignKey("lote_content_type", "lote_object_id")

    # Snapshot del artículo para historial inmutable
    nombre_articulo_snapshot = models.CharField(
        max_length=300, verbose_name="Artículo (snapshot al generar traspaso)",
    )
    numero_lote_snapshot = models.CharField(
        max_length=120, blank=True, null=True, verbose_name="Número de Lote (snapshot)",
    )

    cantidad_enviada  = models.DecimalField(max_digits=10, decimal_places=4,
                                             verbose_name="Cantidad Enviada")
    cantidad_recibida = models.DecimalField(max_digits=10, decimal_places=4, default=0,
                                             verbose_name="Cantidad Recibida")

    class Meta:
        verbose_name = "Línea de Traspaso"
        verbose_name_plural = "Líneas de Traspaso"

    def __str__(self):
        return (f"{self.nombre_articulo_snapshot} "
                f"× {self.cantidad_enviada} → {self.traspaso.folio}")


class NotificacionDiscrepancia(models.Model):
    """
    Notificación automática al Director cuando:
      a) Una OC recibida tiene diferencias entre pedido y recibido.
      b) Un Traspaso llega con cantidad diferente a la enviada.
      c) Cualquier anomalía de stock que requiera decisión ejecutiva.
    """
    TIPO_CHOICES = [
        ('OC_DISCREPANCIA',       'Discrepancia en Recepción de OC'),
        ('TRASPASO_DISCREPANCIA', 'Discrepancia en Traspaso Recibido'),
        ('STOCK_CRITICO',         'Stock Crítico Detectado'),
        ('LOTE_CADUCADO',         'Lote Caducado en Almacén'),
        ('HL7_MAPEO',             'HL7 — error de mapeo a LIMS'),
        ('HL7_CUARENTENA',        'HL7 — cuarentena (unidad/valor)'),
        ('QC_WESTGARD',           'CCI — rechazo reglas Westgard (ISO 15189)'),
    ]
    NIVEL_CHOICES = [
        ('INFO',       'Informativa'),
        ('ADVERTENCIA','Advertencia'),
        ('CRITICO',    'Crítico'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="notificaciones_discrepancia", verbose_name="Empresa",
    )
    tipo  = models.CharField(max_length=30, choices=TIPO_CHOICES, verbose_name="Tipo")
    nivel = models.CharField(max_length=15, choices=NIVEL_CHOICES,
                              default="ADVERTENCIA", verbose_name="Nivel")

    titulo   = models.CharField(max_length=255, verbose_name="Título")
    detalle  = models.TextField(verbose_name="Detalle de la Discrepancia")
    resuelta = models.BooleanField(default=False, verbose_name="Resuelta")

    # Referencia opcional a la OC o Traspaso origen
    oc       = models.ForeignKey(
        OrdenDeCompra, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notificaciones", verbose_name="OC Relacionada",
    )
    traspaso = models.ForeignKey(
        TraspasoInventario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notificaciones", verbose_name="Traspaso Relacionado",
    )

    generada_en   = models.DateTimeField(auto_now_add=True, verbose_name="Generada")
    resuelta_por  = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="discrepancias_resueltas", verbose_name="Resuelta por",
    )
    resuelta_en   = models.DateTimeField(null=True, blank=True, verbose_name="Resuelta en")
    notas_resolucion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Notificación de Discrepancia"
        verbose_name_plural = "Notificaciones de Discrepancia"
        ordering = ["-generada_en"]
        indexes = [
            models.Index(fields=["empresa", "resuelta", "-generada_en"]),
        ]

    def __str__(self):
        return f"[{self.nivel}] {self.titulo} — {self.generada_en:%d/%m/%Y}"
