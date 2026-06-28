from decimal import Decimal
import logging
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import Empresa, Sucursal, Usuario, Producto, Lote, Venta, AjusteInventario
from core.validators import validate_image_upload

logger = logging.getLogger(__name__)

class MotivoAjuste(models.Model):
    """
    Catálogo cerrado de motivos para ajustes de inventario.
    Cada ajuste debe tener una razón válida del catálogo.
    """
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='motivos_ajuste_farmacia',
        verbose_name="Empresa"
    )
    
    codigo = models.CharField(
        max_length=20, 
        verbose_name="Código",
        help_text="Ej: MERMA_CAD, ROTURA, ROBO"
    )
    descripcion = models.CharField(
        max_length=255, 
        verbose_name="Descripción",
        help_text="Ej: Merma por Caducidad Vencida"
    )
    
    # Clasificación
    es_responsabilidad_empleado = models.BooleanField(
        default=False,
        verbose_name="Responsabilidad del Empleado",
        help_text="Si es TRUE, puede generar descuento en nómina"
    )
    requiere_evidencia_fotografica = models.BooleanField(
        default=False,
        verbose_name="Requiere Foto de Evidencia"
    )
    requiere_autorizacion_gerente = models.BooleanField(
        default=False,
        verbose_name="Requiere Autorización de Gerente"
    )
    
    # Estado
    activo = models.BooleanField(default=True, verbose_name="Motivo Activo")
    
    class Meta:
        verbose_name = "Motivo de Ajuste"
        verbose_name_plural = "Motivos de Ajuste"
        ordering = ['codigo']
        unique_together = [['empresa', 'codigo']]
    
    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class MovimientoInventario(models.Model):
    """
    KARDEX FORENSE - Registro inmutable de cada movimiento de inventario.
    
    PRINCIPIO: El stock en Producto es SOLO una consecuencia de la suma
    de los movimientos del Kardex. NUNCA se edita directamente.
    
    Cada pastilla tiene un origen y un destino trazable.
    """
    TIPO_MOVIMIENTO = [
        ('ENTRADA_COMPRA', 'Entrada por Compra a Proveedor'),
        ('ENTRADA_DEVOLUCION', 'Entrada por Devolución de Cliente'),
        ('ENTRADA_AJUSTE', 'Entrada por Ajuste (Corrección Positiva)'),
        ('SALIDA_VENTA', 'Salida por Venta'),
        ('SALIDA_MERMA', 'Salida por Merma/Caducidad'),
        ('SALIDA_ROBO', 'Salida por Robo/Faltante'),
        ('SALIDA_AJUSTE', 'Salida por Ajuste (Corrección Negativa)'),
        ('SALIDA_USO_INTERNO', 'Salida por Uso Interno/Laboratorio'),
    ]
    
    # Identificación del Movimiento
    folio = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Folio Único del Movimiento",
        help_text="Generado automáticamente. Ej: KDX-2026-00001"
    )
    
    # Relaciones Principales
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.PROTECT,
        verbose_name="Empresa"
    )
    sucursal = models.ForeignKey(
        Sucursal, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        verbose_name="Sucursal"
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.PROTECT,
        related_name='movimientos_kardex',
        verbose_name="Producto"
    )
    lote = models.ForeignKey(
        Lote, 
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_kardex',
        verbose_name="Lote Específico",
        help_text="CRÍTICO: El stock se mueve por lote, no por producto genérico"
    )
    
    # Tipo y Cantidad del Movimiento
    tipo_movimiento = models.CharField(
        max_length=30, 
        choices=TIPO_MOVIMIENTO,
        verbose_name="Tipo de Movimiento"
    )
    cantidad = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        verbose_name="Cantidad",
        help_text="Siempre positivo. El tipo define si suma o resta."
    )
    
    # Valuación Financiera (Costo en el momento exacto del movimiento)
    costo_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        verbose_name="Costo Unitario en el Momento del Movimiento",
        help_text="Para entradas: costo de compra. Para salidas: costo promedio actual."
    )
    costo_total = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Costo Total del Movimiento",
        help_text="cantidad * costo_unitario"
    )
    
    # Snapshots de Stock (Foto del momento)
    stock_anterior = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        verbose_name="Stock Antes del Movimiento"
    )
    stock_resultante = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        verbose_name="Stock Después del Movimiento"
    )
    
    # Costo Promedio Ponderado (Solo para productos, snapshot)
    costo_promedio_anterior = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Costo Promedio Anterior"
    )
    costo_promedio_nuevo = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Costo Promedio Después del Movimiento"
    )
    
    # Trazabilidad de Origen/Destino
    proveedor = models.ForeignKey(
        'farmacia.Proveedor', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='movimientos_kardex',
        verbose_name="Proveedor (para compras)"
    )
    venta = models.ForeignKey(
        Venta, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='movimientos_kardex',
        verbose_name="Venta (para salidas por venta)"
    )
    ajuste = models.ForeignKey(
        AjusteInventario, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='movimientos_kardex',
        verbose_name="Ajuste (para correcciones)"
    )
    motivo_ajuste = models.ForeignKey(
        MotivoAjuste, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='movimientos_kardex',
        verbose_name="Motivo del Ajuste"
    )
    
    # Auditoría Forense
    usuario_responsable = models.ForeignKey(
        Usuario, 
        on_delete=models.PROTECT,
        related_name='movimientos_kardex_realizados',
        verbose_name="Usuario Responsable"
    )
    fecha_movimiento = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y Hora del Movimiento"
    )
    
    # Evidencia y Notas
    evidencia = models.ImageField(
        upload_to='kardex_evidencias/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Evidencia Fotográfica",
        help_text="Foto de producto roto, caducado, etc.",
        validators=[validate_image_upload],
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones"
    )
    documento_referencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Documento de Referencia",
        help_text="Ej: Factura, Remisión, Ticket de Venta"
    )
    
    # Validación y Autorización
    requiere_autorizacion = models.BooleanField(
        default=False,
        verbose_name="Requiere Autorización"
    )
    autorizado = models.BooleanField(
        default=False,
        verbose_name="Autorizado"
    )
    autorizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_kardex_autorizados',
        verbose_name="Autorizado Por"
    )
    fecha_autorizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Autorización"
    )
    
    class Meta:
        verbose_name = "Movimiento de Inventario (Kardex)"
        verbose_name_plural = "Movimientos de Inventario (Kardex)"
        ordering = ['-fecha_movimiento']
        indexes = [
            models.Index(fields=['empresa', '-fecha_movimiento']),
            models.Index(fields=['empresa', 'tipo_movimiento', '-fecha_movimiento']),
            models.Index(fields=['producto', '-fecha_movimiento']),
            models.Index(fields=['lote', '-fecha_movimiento']),
            models.Index(fields=['usuario_responsable', '-fecha_movimiento']),
            models.Index(fields=['tipo_movimiento', '-fecha_movimiento']),
            models.Index(fields=['folio']),
            models.Index(fields=['venta']),
        ]
        permissions = [
            ("autorizar_movimientos", "Puede autorizar movimientos de inventario"),
        ]
    
    def __str__(self):
        return f"{self.folio} | {self.tipo_movimiento} | {self.producto.nombre} | {self.cantidad}"
    
    def clean(self):
        """Validaciones de negocio."""
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero.")
        
        if self.tipo_movimiento == 'ENTRADA_COMPRA' and not self.proveedor and not self.observaciones:
            raise ValidationError("Las compras deben tener un proveedor o una observación de origen.")
        
        if self.tipo_movimiento == 'SALIDA_VENTA' and not self.venta:
            raise ValidationError("Las salidas por venta deben tener una venta asociada.")
        
        if 'AJUSTE' in self.tipo_movimiento and not self.motivo_ajuste:
            raise ValidationError("Los ajustes deben tener un motivo del catálogo.")
    
    def save(self, *args, **kwargs):
        if not self.pk:
            with transaction.atomic():
                if not self.folio:
                    from django.utils import timezone as _tz
                    año = _tz.localtime(_tz.now()).year
                    ultimo = MovimientoInventario.objects.filter(
                        folio__startswith=f'KDX-{año}'
                    ).count()
                    self.folio = f'KDX-{año}-{(ultimo + 1):06d}'
                
                stock_producto_actual = self.producto.stock or Decimal('0')
                self.stock_anterior = stock_producto_actual
                
                self.costo_promedio_anterior = self.producto.precio_compra or Decimal('0')
                
                es_entrada = self.tipo_movimiento.startswith('ENTRADA')
                
                if es_entrada:
                    self.stock_resultante = self.stock_anterior + self.cantidad
                else:
                    self.stock_resultante = self.stock_anterior - self.cantidad
                
                from decimal import ROUND_HALF_UP
                raw_costo = self.cantidad * self.costo_unitario
                self.costo_total = raw_costo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                self.full_clean()
                
                if self.lote:
                    if es_entrada:
                        self.lote.cantidad += self.cantidad
                    else:
                        self.lote.cantidad -= self.cantidad
                        if self.lote.cantidad < 0:
                            raise ValidationError(
                                f"Stock insuficiente en lote {self.lote.numero_lote}. "
                                f"Disponible: {self.lote.cantidad + self.cantidad}"
                            )
                    self.lote.save()
                
                if es_entrada and self.tipo_movimiento == 'ENTRADA_COMPRA':
                    valor_anterior = self.stock_anterior * self.costo_promedio_anterior
                    valor_nuevo = self.cantidad * self.costo_unitario
                    valor_total = valor_anterior + valor_nuevo
                    
                    if self.stock_resultante < 0:
                        raise ValidationError(
                            f"No se puede calcular CPP: stock resultante es {self.stock_resultante}. "
                            f"Stock anterior: {self.stock_anterior}, Cantidad entrada: {self.cantidad}."
                        )
                    if self.stock_resultante == 0:
                        self.costo_promedio_nuevo = self.costo_unitario
                    else:
                        self.costo_promedio_nuevo = valor_total / self.stock_resultante
                    
                    self.producto.precio_compra = self.costo_promedio_nuevo
                else:
                    self.costo_promedio_nuevo = self.costo_promedio_anterior
                
                self.producto.stock = self.stock_resultante
                self.producto.save()
                
                super().save(*args, **kwargs)
        else:
            raise ValidationError(
                "Los movimientos de inventario son INMUTABLES. "
                "No se pueden editar una vez creados."
            )
    
    @property
    def es_entrada(self):
        return self.tipo_movimiento.startswith('ENTRADA')
    
    @property
    def es_salida(self):
        return self.tipo_movimiento.startswith('SALIDA')


class MermaFarmacia(models.Model):
    """
    Registro especializado de mermas/bajas de inventario.
    Genera automáticamente un MovimientoInventario tipo SALIDA_MERMA.
    """
    MOTIVO_CHOICES = [
        ('CADUCIDAD', 'Caducidad Vencida'),
        ('DAÑO', 'Daño Físico del Producto'),
        ('ROBO', 'Robo/Faltante'),
        ('USO_INTERNO', 'Uso Interno/Laboratorio'),
        ('DEVOLUCION_CLIENTE', 'Devolución de Cliente'),
        ('OTRO', 'Otro (Especificar en Justificación)'),
    ]
    
    folio = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Folio de Merma",
        help_text="Generado automáticamente. Ej: MERMA-2026-00001"
    )
    
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.PROTECT,
        verbose_name="Empresa"
    )
    sucursal = models.ForeignKey(
        Sucursal, 
        on_delete=models.PROTECT,
        verbose_name="Sucursal"
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.PROTECT,
        related_name='mermas',
        verbose_name="Producto"
    )
    lote = models.ForeignKey(
        Lote, 
        on_delete=models.PROTECT,
        related_name='mermas',
        verbose_name="Lote Afectado"
    )
    
    cantidad = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        verbose_name="Cantidad Dada de Baja"
    )
    motivo = models.CharField(
        max_length=20, 
        choices=MOTIVO_CHOICES,
        verbose_name="Motivo de la Merma"
    )
    justificacion_qc = models.TextField(
        verbose_name="Justificación QC",
        help_text="Explicación detallada del motivo de la baja"
    )
    
    usuario_reporta = models.ForeignKey(
        Usuario, 
        on_delete=models.PROTECT,
        related_name='mermas_reportadas',
        verbose_name="Usuario que Reporta"
    )
    fecha_reporte = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Reporte"
    )
    evidencia_fotografica = models.ImageField(
        upload_to='mermas/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Evidencia Fotográfica",
        validators=[validate_image_upload],
    )
    
    requiere_autorizacion = models.BooleanField(
        default=False,
        verbose_name="Requiere Autorización"
    )
    autorizado = models.BooleanField(
        default=False,
        verbose_name="Autorizado"
    )
    autorizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='mermas_autorizadas',
        verbose_name="Autorizado Por"
    )
    fecha_autorizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Autorización"
    )
    
    movimiento_kardex = models.OneToOneField(
        MovimientoInventario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='merma',
        verbose_name="Movimiento Kardex Generado"
    )
    
    class Meta:
        verbose_name = "Merma de Farmacia"
        verbose_name_plural = "Mermas de Farmacia"
        ordering = ['-fecha_reporte']
        indexes = [
            models.Index(fields=['producto', '-fecha_reporte']),
            models.Index(fields=['motivo', '-fecha_reporte']),
            models.Index(fields=['folio']),
        ]
    
    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero.")
        
        if self.lote and self.lote.cantidad < self.cantidad:
            raise ValidationError(
                f"Stock insuficiente en lote {self.lote.numero_lote}. "
                f"Disponible: {self.lote.cantidad}, Solicitado: {self.cantidad}"
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        
        if not self.pk and not self.movimiento_kardex:
            with transaction.atomic():
                if not self.folio:
                    from django.utils import timezone as _tz
                    año = _tz.localtime(_tz.now()).year
                    ultimo = MermaFarmacia.objects.filter(
                        folio__startswith=f'MERMA-{año}'
                    ).count()
                    self.folio = f'MERMA-{año}-{(ultimo + 1):06d}'
                
                super().save(*args, **kwargs)
                
                movimiento = MovimientoInventario.objects.create(
                    empresa=self.empresa,
                    sucursal=self.sucursal,
                    producto=self.producto,
                    lote=self.lote,
                    tipo_movimiento='SALIDA_MERMA',
                    cantidad=self.cantidad,
                    costo_unitario=self.lote.costo_adquisicion,
                    usuario_responsable=self.usuario_reporta,
                    observaciones=f"Merma {self.folio}: {self.motivo} - {self.justificacion_qc}",
                    evidencia=self.evidencia_fotografica,
                    requiere_autorizacion=self.requiere_autorizacion,
                    autorizado=self.autorizado,
                    autorizado_por=self.autorizado_por,
                    fecha_autorizacion=self.fecha_autorizacion
                )
                
                self.movimiento_kardex = movimiento
                super().save(update_fields=['movimiento_kardex'])
        else:
            super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.folio} | {self.motivo} | {self.producto.nombre} | {self.cantidad}"
