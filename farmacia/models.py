"""
MÓDULO FARMACIA - MODELOS DE BLINDAJE FORENSE
Arquitectura ERP con Kardex, Proveedores y Trazabilidad Total
"""
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import logging
import re

from core.models import Empresa, Sucursal, Usuario, Producto, Lote, Venta, AjusteInventario
from core.validators import validate_image_upload

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. CATÁLOGO DE PROVEEDORES (ORIGEN DE ACTIVOS)
# ==============================================================================
class Proveedor(models.Model):
    """
    Catálogo de proveedores farmacéuticos.
    Laboratorios y distribuidores autorizados.
    """
    CATEGORIA_CHOICES = [
        ('LABORATORIO', 'Laboratorio Farmacéutico'),
        ('DISTRIBUIDOR', 'Distribuidor / Mayorista'),
        ('IMPORTADOR', 'Importador'),
        ('OTRO', 'Otro'),
    ]
    
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='proveedores_farmacia',
        verbose_name="Empresa"
    )
    
    # Identificación Legal
    razon_social = models.CharField(
        max_length=255, 
        verbose_name="Razón Social",
        help_text="Nombre legal del proveedor"
    )
    nombre_comercial = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Nombre Comercial"
    )
    rfc = models.CharField(
        max_length=13,
        verbose_name="RFC",
        help_text="Registro Federal de Contribuyentes (12-13 caracteres)"
    )
    
    # Clasificación
    categoria = models.CharField(
        max_length=20, 
        choices=CATEGORIA_CHOICES, 
        default='DISTRIBUIDOR',
        verbose_name="Categoría de Proveedor"
    )
    
    # Contacto
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección Fiscal")
    contacto_nombre = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Nombre del Contacto"
    )
    
    # Términos Comerciales
    dias_credito = models.IntegerField(
        default=0, 
        verbose_name="Días de Crédito",
        help_text="0 = Contado, 30 = Crédito a 30 días"
    )
    descuento_volumen = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        verbose_name="% Descuento por Volumen"
    )
    
    # Estado
    activo = models.BooleanField(default=True, verbose_name="Proveedor Activo")
    fecha_alta = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Alta")
    notas = models.TextField(blank=True, null=True, verbose_name="Notas Internas")
    
    class Meta:
        verbose_name = "Proveedor Farmacéutico"
        verbose_name_plural = "Proveedores Farmacéuticos"
        ordering = ['razon_social']
        indexes = [
            models.Index(fields=['empresa', 'rfc']),
            models.Index(fields=['empresa', 'activo']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'rfc'], name='proveedor_empresa_rfc_unique'),
        ]
    
    def clean(self):
        """Validación de RFC mexicano."""
        if self.rfc:
            # RFC debe ser 12 (moral) o 13 (física) caracteres
            if len(self.rfc) not in [12, 13]:
                raise ValidationError("El RFC debe tener 12 o 13 caracteres.")
            
            # Validación básica de formato (letras y números)
            if not re.match(r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$', self.rfc.upper()):
                raise ValidationError("Formato de RFC inválido.")
            
            self.rfc = self.rfc.upper()
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.razon_social} ({self.rfc})"


# ==============================================================================
# 2. CATÁLOGO DE MOTIVOS DE AJUSTE (EVITAR TEXTO LIBRE)
# ==============================================================================
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


# ==============================================================================
# 3. KARDEX - MOVIMIENTO INVENTARIO (LA ÚNICA FUENTE DE VERDAD)
# ==============================================================================
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
        'Proveedor', 
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
            models.Index(fields=['empresa', '-fecha_movimiento']),  # listado principal por tenant
            models.Index(fields=['empresa', 'tipo_movimiento', '-fecha_movimiento']),
            models.Index(fields=['producto', '-fecha_movimiento']),
            models.Index(fields=['lote', '-fecha_movimiento']),
            models.Index(fields=['usuario_responsable', '-fecha_movimiento']),
            models.Index(fields=['tipo_movimiento', '-fecha_movimiento']),
            models.Index(fields=['folio']),
            models.Index(fields=['venta']),  # para reversión en cancelar_venta
        ]
        permissions = [
            ("autorizar_movimientos", "Puede autorizar movimientos de inventario"),
        ]
    
    def __str__(self):
        return f"{self.folio} | {self.tipo_movimiento} | {self.producto.nombre} | {self.cantidad}"
    
    def clean(self):
        """Validaciones de negocio."""
        # Cantidad siempre positiva
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero.")
        
        # Validar que haya proveedor en compras (se permite sin proveedor si hay observaciones)
        if self.tipo_movimiento == 'ENTRADA_COMPRA' and not self.proveedor and not self.observaciones:
            raise ValidationError("Las compras deben tener un proveedor o una observación de origen.")
        
        # Validar que haya venta en salidas por venta
        if self.tipo_movimiento == 'SALIDA_VENTA' and not self.venta:
            raise ValidationError("Las salidas por venta deben tener una venta asociada.")
        
        # Validar que ajustes tengan motivo
        if 'AJUSTE' in self.tipo_movimiento and not self.motivo_ajuste:
            raise ValidationError("Los ajustes deben tener un motivo del catálogo.")
    
    def save(self, *args, **kwargs):
        """
        CEREBRO TRANSACCIONAL - El corazón del sistema.
        
        Garantiza integridad atómica:
        1. Calcula el nuevo stock
        2. Actualiza el Lote
        3. Actualiza el Producto (stock + costo promedio)
        4. Guarda el movimiento
        
        Si algo falla, ROLLBACK TOTAL.
        """
        # Si es un movimiento nuevo (no tiene PK)
        if not self.pk:
            with transaction.atomic():
                # 1. Generar folio único si no existe (ANTES de full_clean)
                if not self.folio:
                    from datetime import datetime
                    año = datetime.now().year
                    ultimo = MovimientoInventario.objects.filter(
                        folio__startswith=f'KDX-{año}'
                    ).count()
                    self.folio = f'KDX-{año}-{(ultimo + 1):06d}'
                
                # 2. Obtener stock actual del producto
                stock_producto_actual = self.producto.stock or Decimal('0')
                self.stock_anterior = stock_producto_actual
                
                # 3. Obtener costo promedio actual
                self.costo_promedio_anterior = self.producto.precio_compra or Decimal('0')
                
                # 4. Calcular nuevo stock según tipo de movimiento
                es_entrada = self.tipo_movimiento.startswith('ENTRADA')
                
                if es_entrada:
                    self.stock_resultante = self.stock_anterior + self.cantidad
                else:
                    self.stock_resultante = self.stock_anterior - self.cantidad
                    # ACAYUCAN v7.5 / Farmacia v1.13: el stock a nivel Producto puede quedar < 0
                    # (última unidad, desfase vs suma de lotes). La verdad operativa es el LOTE:
                    # nunca cantidad negativa en lote cuando hay lote (PDV: select_for_update).
                
                # 5. Calcular costo total (redondeo a 2 decimales para respetar el campo decimal_places=2)
                from decimal import ROUND_HALF_UP
                raw_costo = self.cantidad * self.costo_unitario
                self.costo_total = raw_costo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                # Validaciones completas DESPUÉS de calcular todos los campos requeridos
                self.full_clean()
                
                # 6. Actualizar LOTE si existe
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
                
                # 7. Calcular COSTO PROMEDIO PONDERADO (solo para entradas)
                if es_entrada and self.tipo_movimiento == 'ENTRADA_COMPRA':
                    # Fórmula: (Stock_Anterior * Costo_Anterior + Cantidad_Nueva * Costo_Nuevo) / Stock_Nuevo
                    valor_anterior = self.stock_anterior * self.costo_promedio_anterior
                    valor_nuevo = self.cantidad * self.costo_unitario
                    valor_total = valor_anterior + valor_nuevo
                    
                    # CPP: sin división por cero ni denominador inválido (ACAYUCAN v7.5)
                    if self.stock_resultante < 0:
                        raise ValidationError(
                            f"No se puede calcular CPP: stock resultante es {self.stock_resultante}. "
                            f"Stock anterior: {self.stock_anterior}, Cantidad entrada: {self.cantidad}."
                        )
                    if self.stock_resultante == 0:
                        self.costo_promedio_nuevo = self.costo_unitario
                    else:
                        self.costo_promedio_nuevo = valor_total / self.stock_resultante
                    
                    # Actualizar costo en Producto
                    self.producto.precio_compra = self.costo_promedio_nuevo
                else:
                    # Para salidas, el costo promedio no cambia
                    self.costo_promedio_nuevo = self.costo_promedio_anterior
                
                # 8. Actualizar STOCK en Producto
                self.producto.stock = self.stock_resultante
                self.producto.save()
                
                # 9. Guardar el movimiento
                super().save(*args, **kwargs)
        else:
            # Si ya existe, NO permitir edición (inmutable)
            raise ValidationError(
                "Los movimientos de inventario son INMUTABLES. "
                "No se pueden editar una vez creados."
            )
    
    @property
    def es_entrada(self):
        """Indica si el movimiento incrementa el stock."""
        return self.tipo_movimiento.startswith('ENTRADA')
    
    @property
    def es_salida(self):
        """Indica si el movimiento reduce el stock."""
        return self.tipo_movimiento.startswith('SALIDA')


# ==============================================================================
# 4. GESTIÓN DE MERMAS (BAJAS AUDITADAS)
# ==============================================================================
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
    
    # Identificación
    folio = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Folio de Merma",
        help_text="Generado automáticamente. Ej: MERMA-2026-00001"
    )
    
    # Relaciones
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
    
    # Detalles de la Merma
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
    
    # Auditoría y Evidencia
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
    
    # Autorización (para mermas mayores a X monto)
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
    
    # Vinculación con Kardex
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
        """Validaciones de negocio."""
        from django.core.exceptions import ValidationError
        
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero.")
        
        # Validar que haya stock suficiente en el lote
        if self.lote and self.lote.cantidad < self.cantidad:
            raise ValidationError(
                f"Stock insuficiente en lote {self.lote.numero_lote}. "
                f"Disponible: {self.lote.cantidad}, Solicitado: {self.cantidad}"
            )
    
    def save(self, *args, **kwargs):
        """
        Al guardar, genera automáticamente el MovimientoInventario correspondiente.
        """
        from django.db import transaction
        
        self.full_clean()
        
        # Si es nuevo y no tiene movimiento kardex
        if not self.pk and not self.movimiento_kardex:
            with transaction.atomic():
                # 1. Generar folio si no existe
                if not self.folio:
                    from datetime import datetime
                    año = datetime.now().year
                    ultimo = MermaFarmacia.objects.filter(
                        folio__startswith=f'MERMA-{año}'
                    ).count()
                    self.folio = f'MERMA-{año}-{(ultimo + 1):06d}'
                
                # 2. Guardar la merma primero
                super().save(*args, **kwargs)
                
                # 3. Crear el movimiento de inventario (SALIDA_MERMA)
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
                
                # 4. Vincular el movimiento con la merma
                self.movimiento_kardex = movimiento
                super().save(update_fields=['movimiento_kardex'])
        else:
            super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.folio} | {self.motivo} | {self.producto.nombre} | {self.cantidad}"


# ==============================================================================
# 5. CIERRE DE TURNO (CORTE DE CAJA CIEGO)
# ==============================================================================
class CierreTurnoFarmacia(models.Model):
    """
    Corte de caja ciego para farmacia.
    Nancy ingresa cuánto tiene en mano, el sistema compara con lo teórico.
    """
    # Identificación
    folio = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Folio de Cierre",
        help_text="Generado automáticamente. Ej: CIERRE-2026-00001"
    )
    
    # Relaciones
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
    usuario_responsable = models.ForeignKey(
        Usuario, 
        on_delete=models.PROTECT,
        related_name='cierres_farmacia',
        verbose_name="Usuario que Cierra (Nancy)"
    )
    apertura_caja = models.OneToOneField(
        'AperturaCaja',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cierre_asociado',
        verbose_name="Apertura de Caja Asociada",
        help_text="Vincula con la apertura para incluir fondo inicial"
    )
    
    # Fechas y Horarios
    fecha_apertura = models.DateTimeField(
        verbose_name="Fecha/Hora de Apertura del Turno"
    )
    fecha_cierre = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha/Hora de Cierre"
    )
    
    # MONTOS DECLARADOS (Lo que Nancy cuenta en mano)
    efectivo_declarado = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Efectivo Declarado (Contado en Mano)"
    )
    tarjeta_declarado = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tarjeta Declarado (Suma de Vouchers)"
    )
    vales_declarado = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Vales Declarado (Vales Físicos Contados)"
    )
    
    # MONTOS TEÓRICOS (Lo que el sistema dice que debería haber)
    efectivo_teorico = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Efectivo Teórico (Por Ventas del Sistema)"
    )
    tarjeta_teorico = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tarjeta Teórico (Por Ventas del Sistema)"
    )
    vales_teorico = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Vales Teórico (Por Ventas del Sistema)"
    )
    
    # DIFERENCIAS (Calculadas automáticamente)
    diferencia_efectivo = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Diferencia Efectivo (Declarado - Teórico)"
    )
    diferencia_tarjeta = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Diferencia Tarjeta"
    )
    diferencia_vales = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Diferencia Vales"
    )
    diferencia_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Diferencia Total (Faltante/Sobrante)"
    )
    
    # Observaciones y Justificación
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones del Cierre"
    )
    justificacion_diferencia = models.TextField(
        blank=True,
        null=True,
        verbose_name="Justificación de Diferencias",
        help_text="Explicar faltantes o sobrantes"
    )
    
    # Estado y Autorización
    requiere_revision = models.BooleanField(
        default=False,
        verbose_name="Requiere Revisión Gerencial",
        help_text="Se activa automáticamente si diferencia > umbral"
    )
    revisado = models.BooleanField(
        default=False,
        verbose_name="Revisado por Gerencia"
    )
    revisado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cierres_revisados',
        verbose_name="Revisado Por"
    )
    fecha_revision = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Revisión"
    )
    
    class Meta:
        verbose_name = "Cierre de Turno Farmacia"
        verbose_name_plural = "Cierres de Turno Farmacia"
        ordering = ['-fecha_cierre']
        constraints = [
            models.UniqueConstraint(
                fields=['apertura_caja'],
                name='unique_cierre_por_apertura',
                condition=models.Q(apertura_caja__isnull=False),
                violation_error_message="Ya existe un cierre para esta apertura de caja."
            ),
        ]
        indexes = [
            models.Index(fields=['sucursal', '-fecha_cierre']),
            models.Index(fields=['usuario_responsable', '-fecha_cierre']),
            models.Index(fields=['folio']),
        ]
    
    def clean(self):
        """Validaciones de negocio."""
        from django.core.exceptions import ValidationError
        
        if self.fecha_apertura and self.fecha_cierre:
            if self.fecha_apertura >= self.fecha_cierre:
                raise ValidationError("La fecha de apertura debe ser anterior a la de cierre.")
        
        # VALIDACIÓN INTEGRIDAD v1.13: Verificar que la apertura esté activa
        if self.apertura_caja and not self.apertura_caja.activa:
            raise ValidationError(
                "No se puede cerrar una caja que no está activa o ya fue cerrada. "
                f"Apertura {self.apertura_caja.folio} ya está cerrada."
            )
    
    def save(self, *args, **kwargs):
        """
        Calcula automáticamente las diferencias y determina si requiere revisión.
        """
        # 1. Generar folio si no existe
        if not self.folio:
            from datetime import datetime
            año = datetime.now().year
            ultimo = CierreTurnoFarmacia.objects.filter(
                folio__startswith=f'CIERRE-{año}'
            ).count()
            self.folio = f'CIERRE-{año}-{(ultimo + 1):06d}'
        
        # 2. Ajustar efectivo teórico con fondo inicial (si hay apertura vinculada)
        efectivo_teorico_ajustado = self.efectivo_teorico
        if self.apertura_caja:
            # Fórmula: Fondo Inicial + Ventas Efectivo = Efectivo Esperado
            efectivo_teorico_ajustado = self.apertura_caja.fondo_efectivo + self.efectivo_teorico
        
        # 3. Calcular diferencias
        self.diferencia_efectivo = self.efectivo_declarado - efectivo_teorico_ajustado
        self.diferencia_tarjeta = self.tarjeta_declarado - self.tarjeta_teorico
        self.diferencia_vales = self.vales_declarado - self.vales_teorico
        self.diferencia_total = (
            self.diferencia_efectivo + 
            self.diferencia_tarjeta + 
            self.diferencia_vales
        )
        
        # 3. Determinar si requiere revisión (umbral: diferencia > $100 o > 2%)
        umbral_absoluto = Decimal('100.00')
        total_teorico = self.efectivo_teorico + self.tarjeta_teorico + self.vales_teorico
        
        if total_teorico > 0:
            porcentaje_diferencia = abs(self.diferencia_total / total_teorico * 100)
        else:
            porcentaje_diferencia = Decimal('0.00')
        
        if abs(self.diferencia_total) > umbral_absoluto or porcentaje_diferencia > 2:
            self.requiere_revision = True
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        # 4. Cerrar la apertura de caja asociada (si existe)
        if self.apertura_caja and self.apertura_caja.activa:
            self.apertura_caja.cerrar_caja()
            self.apertura_caja.cerrada_con = self
            self.apertura_caja.save(update_fields=['cerrada_con'])
    
    @property
    def total_declarado(self):
        """Total de todos los métodos de pago declarados."""
        return self.efectivo_declarado + self.tarjeta_declarado + self.vales_declarado
    
    @property
    def total_teorico(self):
        """Total de todos los métodos de pago teóricos."""
        return self.efectivo_teorico + self.tarjeta_teorico + self.vales_teorico
    
    @property
    def estado_diferencia(self):
        """Retorna FALTANTE, SOBRANTE o EXACTO."""
        if self.diferencia_total < 0:
            return f'FALTANTE (${abs(self.diferencia_total):.2f})'
        elif self.diferencia_total > 0:
            return f'SOBRANTE (${self.diferencia_total:.2f})'
        else:
            return 'EXACTO'
    
    def __str__(self):
        return f"{self.folio} | {self.usuario_responsable.get_full_name()} | {self.estado_diferencia}"


# ==============================================================================
# 6. GESTIÓN DE APERTURA DE CAJA (FONDO INICIAL)
# ==============================================================================
class AperturaCaja(models.Model):
    """
    Registro de apertura de caja al inicio del turno.
    Define el fondo inicial de efectivo para calcular correctamente el cierre.
    """
    # Identificación
    folio = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Folio de Apertura",
        help_text="Generado automáticamente. Ej: APERT-2026-00001"
    )
    
    # Relaciones
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
    usuario_responsable = models.ForeignKey(
        Usuario, 
        on_delete=models.PROTECT,
        related_name='aperturas_caja',
        verbose_name="Usuario que Abre (Nancy)"
    )
    
    # Fechas
    fecha_apertura = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha/Hora de Apertura"
    )
    
    # Fondos Iniciales
    fondo_efectivo = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Fondo Inicial de Efectivo",
        help_text="Dinero en caja al abrir (para dar cambio)"
    )
    fondo_vales = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Vales Disponibles (Opcional)"
    )
    
    # Estado
    activa = models.BooleanField(
        default=True,
        verbose_name="Caja Abierta",
        help_text="True mientras el turno está activo"
    )
    cerrada_con = models.OneToOneField(
        'CierreTurnoFarmacia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='apertura',
        verbose_name="Cerrada Con"
    )
    
    # Observaciones
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones de Apertura"
    )
    
    class Meta:
        verbose_name = "Apertura de Caja"
        verbose_name_plural = "Aperturas de Caja"
        ordering = ['-fecha_apertura']
        indexes = [
            models.Index(fields=['sucursal', '-fecha_apertura']),
            models.Index(fields=['usuario_responsable', '-fecha_apertura']),
            models.Index(fields=['activa', '-fecha_apertura']),
        ]
    
    def save(self, *args, **kwargs):
        """Genera folio automáticamente."""
        if not self.folio:
            from datetime import datetime
            año = datetime.now().year
            ultimo = AperturaCaja.objects.filter(
                folio__startswith=f'APERT-{año}'
            ).count()
            self.folio = f'APERT-{año}-{(ultimo + 1):06d}'
        
        super().save(*args, **kwargs)
    
    def cerrar_caja(self):
        """Marca la caja como cerrada (se debe llamar desde CierreTurnoFarmacia)."""
        self.activa = False
        self.save(update_fields=['activa'])
    
    def __str__(self):
        estado = 'ABIERTA' if self.activa else 'CERRADA'
        return f"{self.folio} | {self.usuario_responsable.get_full_name()} | {estado}"


# ==============================================================================
# 7. DEVOLUCIONES Y CANCELACIONES (CON REINGRESO A STOCK)
# ==============================================================================
class DevolucionVenta(models.Model):
    """
    Registro de devoluciones de ventas (total o parcial).
    Permite reingresar mercancía al stock o enviarla a mermas.
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
    
    # Identificación
    folio = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Folio de Devolución",
        help_text="Generado automáticamente. Ej: DEV-2026-00001"
    )
    
    # Relaciones
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
    
    # Detalles de la Devolución
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
    
    # Montos
    monto_devolucion = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Monto a Devolver"
    )
    
    # Gestión de Stock
    reingresar_a_stock = models.BooleanField(
        default=True,
        verbose_name="¿Reingresar Mercancía al Inventario?",
        help_text="Si=Vuelve al stock. No=Envía a Mermas"
    )
    
    # Auditoría
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
    
    # Autorización
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
    
    # Evidencia
    evidencia_fotografica = models.ImageField(
        upload_to='devoluciones/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Evidencia Fotográfica",
        validators=[validate_image_upload],
    )
    
    # Procesado
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
        """
        Al guardar, genera folio y determina si requiere autorización.
        """
        # Generar folio
        if not self.folio:
            from datetime import datetime
            año = datetime.now().year
            ultimo = DevolucionVenta.objects.filter(
                folio__startswith=f'DEV-{año}'
            ).count()
            self.folio = f'DEV-{año}-{(ultimo + 1):06d}'
        
        # Determinar si requiere autorización (umbral: $500)
        if self.monto_devolucion > Decimal('500.00'):
            self.requiere_autorizacion = True
        
        super().save(*args, **kwargs)
    
    def procesar_devolucion(self, usuario=None):
        """
        Procesa la devolución: Reingreso a stock o envío a mermas.
        Debe llamarse manualmente después de crear la devolución.
        
        Args:
            usuario: Usuario que procesa la devolución (para trazabilidad).
        """
        from django.db import transaction
        from decimal import Decimal
        
        if self.procesada:
            raise ValidationError("Esta devolución ya fue procesada.")
        
        if self.requiere_autorizacion and not self.autorizado:
            raise ValidationError("La devolución requiere autorización gerencial.")
        
        with transaction.atomic():
            venta = self.venta_original
            detalles = venta.detalles.all()
            
            if self.reingresar_a_stock:
                # OPCIÓN A: Reingresar al inventario via Kardex
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
                    except Exception as e:
                        logger.warning(f"Kardex falló para {detalle.producto}: {e}. Ajuste manual de stock.")
                        detalle.producto.stock += detalle.cantidad
                        detalle.producto.save(update_fields=['stock'])
                logger.info(f"Mercancía de {self.folio} reingresada al stock")
            else:
                # OPCIÓN B: Enviar a mermas (MermaFarmacia requiere lote no nulo)
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
            
            # Marcar como procesada
            self.procesada = True
            self.save(update_fields=['procesada'])
    
    def __str__(self):
        return f"{self.folio} | {self.tipo} | ${self.monto_devolucion} | {self.motivo}"


# ==============================================================================
# 8. LIBRO DE CONTROL DE ANTIBIÓTICOS (COMPLIANCE COFEPRIS)
# ==============================================================================
class RegistroAntibiotico(models.Model):
    """
    Libro de control obligatorio para venta de antibióticos (Fracción IV).
    Cumple con NOM-072-SSA1-2012.
    """
    # Identificación del Registro
    folio = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Folio de Registro",
        help_text="Generado automáticamente. Ej: ATB-2026-00001"
    )
    
    # Relaciones
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
    venta = models.ForeignKey(
        Venta, 
        on_delete=models.PROTECT,
        related_name='registros_antibioticos',
        verbose_name="Venta Asociada"
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.PROTECT,
        related_name='registros_antibioticos',
        verbose_name="Antibiótico Vendido"
    )
    
    # Datos del Paciente
    paciente = models.ForeignKey(
        'core.Paciente', 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='antibioticos_recibidos',
        verbose_name="Paciente"
    )
    paciente_nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre del Paciente",
        help_text="Si no hay paciente registrado, capturar nombre"
    )
    paciente_edad = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Edad del Paciente"
    )
    
    # Datos del Médico Prescriptor (OBLIGATORIO COFEPRIS)
    medico_cedula = models.CharField(
        max_length=50,
        verbose_name="Cédula Profesional del Médico",
        help_text="OBLIGATORIO para antibióticos"
    )
    medico_nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre del Médico Prescriptor"
    )
    
    # Datos de la Receta (si aplica)
    receta_folio = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Folio de Receta Médica"
    )
    receta_fecha = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de la Receta"
    )
    
    # Producto Vendido
    cantidad_vendida = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        verbose_name="Cantidad Vendida"
    )
    lote_vendido = models.ForeignKey(
        Lote, 
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='registros_antibioticos',
        verbose_name="Lote del Producto"
    )
    
    # Auditoría
    fecha_venta = models.DateTimeField(
        verbose_name="Fecha/Hora de Venta"
    )
    usuario_vendedor = models.ForeignKey(
        Usuario, 
        on_delete=models.PROTECT,
        related_name='antibioticos_vendidos',
        verbose_name="Usuario que Vendió"
    )
    
    class Meta:
        verbose_name = "Registro de Antibiótico (Libro COFEPRIS)"
        verbose_name_plural = "Registros de Antibióticos (Libro COFEPRIS)"
        ordering = ['-fecha_venta']
        indexes = [
            models.Index(fields=['producto', '-fecha_venta']),
            models.Index(fields=['medico_cedula', '-fecha_venta']),
            models.Index(fields=['sucursal', '-fecha_venta']),
            models.Index(fields=['folio']),
        ]
    
    def clean(self):
        """Validaciones COFEPRIS."""
        from django.core.exceptions import ValidationError
        
        if not self.medico_cedula or not self.medico_nombre:
            raise ValidationError(
                "Para venta de antibióticos es OBLIGATORIO registrar Cédula y Nombre del Médico Prescriptor (NOM-072)."
            )
        
        if not self.paciente and not self.paciente_nombre:
            raise ValidationError(
                "Se requiere nombre del paciente para registro COFEPRIS."
            )
    
    def save(self, *args, **kwargs):
        """Genera folio y valida."""
        if not self.folio:
            from datetime import datetime
            año = datetime.now().year
            ultimo = RegistroAntibiotico.objects.filter(
                folio__startswith=f'ATB-{año}'
            ).count()
            self.folio = f'ATB-{año}-{(ultimo + 1):06d}'
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.folio} | {self.producto.nombre} | {self.paciente_nombre} | Dr. {self.medico_nombre}"
