from decimal import Decimal
import logging
from django.db import models, transaction, DatabaseError
from django.core.exceptions import ValidationError
from core.models import Empresa, Sucursal, Usuario, Venta
from core.validators import validate_image_upload

logger = logging.getLogger(__name__)

class DevolucionVenta(models.Model):
    """
    Registro de devoluciones de ventas (total o parcial).
    """
    TIPO_DEVOLUCION = [
        ('TOTAL', 'Devolución Total'),
        ('PARCIAL', 'Devolución Parcial'),
    ]
    
    MOTIVO_CHOICES = [
        ('ERROR_VENTA', 'Error en la Venta'),
        ('PRODUCTO_DEFECTUOSO', 'Producto Defectuoso'),
        ('CLIENTE_INSATISFECHO', 'Cliente Insatisfecho'),
        ('PRODUCTO_EQUIVOCADO', 'Producto Equivocado'),
        ('OTRO', 'Otro (Especificar)'),
    ]
    
    folio = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Folio de Devolución",
        help_text="Generado automáticamente. Ej: DEV-2026-00001"
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
    venta_original = models.ForeignKey(
        Venta, 
        on_delete=models.PROTECT,
        related_name='devoluciones_farmacia',
        verbose_name="Venta Original"
    )
    
    tipo = models.CharField(
        max_length=10, 
        choices=TIPO_DEVOLUCION,
        verbose_name="Tipo de Devolución"
    )
    motivo = models.CharField(
        max_length=30, 
        choices=MOTIVO_CHOICES,
        verbose_name="Motivo de la Devolución"
    )
    motivo_detallado = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo Detallado"
    )
    
    monto_devolucion = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Monto a Devolver"
    )
    
    reingresar_a_stock = models.BooleanField(
        default=True,
        verbose_name="¿Reingresar Mercancía al Inventario?",
        help_text="Si=Vuelve al stock. No=Envía a Mermas"
    )
    
    usuario_procesa = models.ForeignKey(
        Usuario, 
        on_delete=models.PROTECT,
        related_name='devoluciones_procesadas',
        verbose_name="Usuario que Procesa la Devolución"
    )
    fecha_devolucion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha/Hora de Devolución"
    )
    
    requiere_autorizacion = models.BooleanField(
        default=False,
        verbose_name="Requiere Autorización Gerencial",
        help_text="True si monto > umbral"
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
        related_name='devoluciones_farmacia_autorizadas',
        verbose_name="Autorizado Por"
    )
    
    evidencia_fotografica = models.ImageField(
        upload_to='devoluciones/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Evidencia Fotográfica",
        validators=[validate_image_upload],
    )
    
    procesada = models.BooleanField(
        default=False,
        verbose_name="Devolución Procesada",
        help_text="True cuando se ejecutó reingreso/merma"
    )
    
    class Meta:
        verbose_name = "Devolución de Venta"
        verbose_name_plural = "Devoluciones de Venta"
        ordering = ['-fecha_devolucion']
        indexes = [
            models.Index(fields=['venta_original', '-fecha_devolucion']),
            models.Index(fields=['sucursal', '-fecha_devolucion']),
            models.Index(fields=['folio']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.folio:
            from django.utils import timezone as _tz
            año = _tz.localtime(_tz.now()).year
            ultimo = DevolucionVenta.objects.filter(
                folio__startswith=f'DEV-{año}'
            ).count()
            self.folio = f'DEV-{año}-{(ultimo + 1):06d}'
        
        if self.monto_devolucion > Decimal('500.00'):
            self.requiere_autorizacion = True
        
        super().save(*args, **kwargs)
    
    def procesar_devolucion(self, usuario=None):
        from farmacia.models.inventario import MovimientoInventario, MermaFarmacia
        
        if self.procesada:
            raise ValidationError("Esta devolución ya fue procesada.")
        
        if self.requiere_autorizacion and not self.autorizado:
            raise ValidationError("La devolución requiere autorización gerencial.")
 
        if self.tipo == 'PARCIAL':
            raise ValidationError(
                "La devolución parcial requiere detalle por producto/cantidad antes de afectar stock o mermas."
            )
 
        with transaction.atomic():
            venta = self.venta_original
            detalles = venta.detalles.all()
            
            if self.reingresar_a_stock:
                for detalle in detalles:
                    try:
                        costo = getattr(detalle, 'precio_unitario', None) or getattr(detalle.producto, 'precio_compra', None) or Decimal('0')
                        costo = Decimal(str(costo)) if costo is not None else Decimal('0')
                        usuario_resp = usuario or self.usuario_procesa
                        MovimientoInventario.objects.create(
                            empresa=venta.empresa,
                            sucursal=venta.sucursal,
                            producto=detalle.producto,
                            lote=getattr(detalle, 'lote_vendido', None) or getattr(detalle, 'lote', None),
                            tipo_movimiento='ENTRADA_DEVOLUCION',
                            cantidad=Decimal(str(detalle.cantidad)),
                            costo_unitario=costo,
                            usuario_responsable=usuario_resp,
                            observaciones=f'Reingreso automático por devolución {self.folio}'
                        )
                    except (DatabaseError, ValidationError, ValueError, TypeError) as e:
                        logger.exception("Kardex falló para %s. Ajuste manual de stock.", detalle.producto)
                        detalle.producto.stock += detalle.cantidad
                        detalle.producto.save(update_fields=['stock'])
                logger.info(f"Mercancía de {self.folio} reingresada al stock")
            else:
                for detalle in detalles:
                    lote = getattr(detalle, 'lote_vendido', None) or getattr(detalle, 'lote', None)
                    if not lote:
                        lote = detalle.producto.lotes.filter(cantidad__gt=0).order_by('fecha_caducidad').first()
                    if not lote:
                        logger.warning(
                            f"Devolución {self.folio}: sin lote para {detalle.producto.nombre}; omitiendo merma."
                        )
                        continue
                    MermaFarmacia.objects.create(
                        empresa=venta.empresa,
                        sucursal=venta.sucursal,
                        producto=detalle.producto,
                        lote=lote,
                        cantidad=detalle.cantidad,
                        motivo='DEVOLUCION_CLIENTE',
                        justificacion_qc=f'Devolución {self.folio}: {self.motivo}',
                        usuario_reporta=usuario or self.usuario_procesa
                    )
                logger.info(f"Mercancía de {self.folio} enviada a mermas")
            
            self.procesada = True
            self.save(update_fields=['procesada'])
    
    def __str__(self):
        return f"{self.folio} | {self.tipo} | ${self.monto_devolucion} | {self.motivo}"
