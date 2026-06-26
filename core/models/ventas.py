"""
core/models/ventas.py
Ventas, Recetas, Pagos, Devoluciones, Finanzas y Cuentas por Cobrar.
Depende de: base.py, catalogos.py
FKs cruzados a Paciente, OrdenDeServicio y AuditLog usan string references o apps.get_model().
"""
from decimal import Decimal
from django.db import models
from django.utils import timezone
import uuid

from core.tenant import TenantModel
from core.validators import validate_image_upload
from .base import Empresa, Sucursal, Usuario, get_google_drive_storage
import logging


# ==============================================================================
# 4. CONTROL NORMADO: RECETAS (COFEPRIS)
# ==============================================================================
class Receta(models.Model):
    """Receta Médica 4.0 con QR de validación y sincronización FEFO."""
    medico = models.ForeignKey('Medico', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Médico que expide")
    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='recetas_recibidas', null=True, blank=True, verbose_name="Paciente")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='recetas_medicas', null=True, blank=True)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sucursal")

    folio_receta = models.CharField(max_length=100, unique=True, verbose_name="Folio de la Receta")
    fecha_emision = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Emisión")

    presion_arterial_sistolica = models.IntegerField(null=True, blank=True, verbose_name="PA Sistólica (mmHg)")
    presion_arterial_diastolica = models.IntegerField(null=True, blank=True, verbose_name="PA Diastólica (mmHg)")
    frecuencia_cardiaca = models.IntegerField(null=True, blank=True, verbose_name="FC (lat/min)")
    frecuencia_respiratoria = models.IntegerField(null=True, blank=True, verbose_name="FR (resp/min)")
    temperatura = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="Temp (°C)")
    peso = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Peso (kg)")
    talla = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="Talla (m)")
    imc = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="IMC")
    saturacion_oxigeno = models.IntegerField(null=True, blank=True, verbose_name="SpO₂ (%)")
    glucosa = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Glucosa (mg/dL)")

    diagnostico_principal = models.CharField(max_length=500, verbose_name="Diagnóstico Principal", default="Sin diagnóstico")
    diagnostico_secundario = models.CharField(max_length=500, blank=True, null=True, verbose_name="Diagnóstico Secundario")
    indicaciones = models.TextField(verbose_name="Indicaciones (IDX)", help_text="Tratamiento prescrito - Se verifica existencia en farmacia", default="")

    medico_nombre_completo = models.CharField(max_length=255, verbose_name="Nombre Completo del Médico", default="Médico")
    medico_cedula = models.CharField(max_length=50, verbose_name="Cédula Profesional", default="")
    medico_especialidad = models.CharField(max_length=150, verbose_name="Especialidad", default="Médico General")
    medico_firma_digital = models.ImageField(
        upload_to='core.utils.paths.generar_ruta_drive_receta',
        storage=get_google_drive_storage,
        blank=True,
        null=True,
        verbose_name="Firma Digital",
        help_text="Firma digital del médico almacenada en Google Drive",
        validators=[validate_image_upload],
    )

    qr_verificacion = models.TextField(blank=True, null=True, verbose_name="Código QR de Validación (Base64)")
    hash_verificacion = models.CharField(max_length=64, blank=True, null=True, verbose_name="Hash SHA-256 para Verificación")
    fecha_vencimiento_cedula = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento de Cédula")
    cedula_vigente = models.BooleanField(default=True, verbose_name="Cédula Vigente")

    url_drive_backup = models.URLField(blank=True, null=True, verbose_name="URL Backup en Google Drive", help_text="Link de visualización del PDF en Drive")
    drive_file_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="ID de Archivo en Drive")
    drive_sync_pending = models.BooleanField(default=False, verbose_name="Sincronización Pendiente", help_text="True si el archivo aún no se ha sincronizado a Drive")
    drive_status = models.CharField(max_length=20, choices=[('PENDIENTE', 'Pendiente'), ('SINCRONIZADO', 'Sincronizado'), ('ERROR', 'Error')], default='PENDIENTE', verbose_name="Estado de Sincronización")
    drive_last_error = models.TextField(blank=True, null=True, verbose_name="Último Error de Drive", help_text="Mensaje de error para debug")

    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Fecha de Creación")
    activa = models.BooleanField(default=True, verbose_name="Receta Activa")

    # ── SPRINT 2.3: Trazabilidad completa del documento físico ───────────────
    numero_receta_externo = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Número de Receta (documento médico)",
        help_text=(
            "Folio impreso en el talonario del médico. "
            "Distinto al folio_receta que genera PRISLAB automáticamente. "
            "Permite vincular el expediente digital con el papel físico."
        ),
    )
    informacion_adicional = models.TextField(
        blank=True, null=True,
        verbose_name="Información Adicional",
        help_text=(
            "Indicaciones especiales, observaciones de dispensación, "
            "notas del farmacéutico o instrucciones de uso especiales."
        ),
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Receta Médica 4.0"
        verbose_name_plural = "Recetas Médicas 4.0"
        ordering = ['-fecha_emision']
        indexes = [
            models.Index(fields=['medico_cedula', '-fecha_emision']),
            models.Index(fields=['paciente', '-fecha_emision']),
            models.Index(fields=['folio_receta']),
        ]

    def __str__(self):
        return f"Receta: {self.folio_receta} | Dr. {self.medico_nombre_completo} | {self.paciente.nombre_completo if self.paciente else 'Paciente Externo'}"

    def validar_items_antes_de_emitir(self):
        """Valida que la receta tenga al menos un medicamento antes de imprimir/emitir PDF."""
        from django.core.exceptions import ValidationError
        if not self.items.exists():
            raise ValidationError(
                'No se puede imprimir o emitir una receta sin medicamentos. '
                'Agregue al menos un medicamento a la receta.'
            )

    def save(self, *args, **kwargs):
        if not self.folio_receta:
            from django.utils import timezone as _tz
            ahora = _tz.localtime(_tz.now())
            prefijo = f'REC-{ahora.strftime("%Y%m")}-'
            ultimos = Receta.objects.filter(folio_receta__startswith=prefijo).count()
            self.folio_receta = f'{prefijo}{str(ultimos + 1).zfill(5)}'
        self.calcular_imc()
        super().save(*args, **kwargs)

    def calcular_imc(self):
        """Calcula el IMC automáticamente si hay peso y talla."""
        if self.peso and self.talla and self.talla > 0:
            self.imc = self.peso / (self.talla ** 2)
            return self.imc
        return None


class RecetaItem(models.Model):
    """Items individuales de una receta médica (medicamentos prescritos)."""
    ESTADO_CHOICES = [
        ('SUGERIDO', 'Sugerido'),
        ('PROCESADO', 'Procesado'),
    ]

    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name='items', verbose_name="Receta")
    medicamento = models.ForeignKey('Producto', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Medicamento", help_text="Producto del catálogo (si está disponible)")
    texto_libre = models.CharField(max_length=500, blank=True, null=True, verbose_name="Texto Libre", help_text="Prescripción libre cuando el producto no está en catálogo")
    cantidad = models.IntegerField(default=1, verbose_name="Cantidad Recetada")
    precio_momento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio al Momento de la Receta")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='SUGERIDO', verbose_name="Estado")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        app_label = 'core'
        verbose_name = "Item de Receta"
        verbose_name_plural = "Items de Receta"
        ordering = ['-fecha_creacion']

    def __str__(self):
        if self.medicamento:
            return f"{self.medicamento.nombre} x{self.cantidad} - {self.estado}"
        return f"{self.texto_libre} x{self.cantidad} - {self.estado}"

    @property
    def nombre_display(self):
        """Retorna el nombre del producto o texto libre."""
        return self.medicamento.nombre if self.medicamento else self.texto_libre or "Sin nombre"


class DemandaInsatisfecha(models.Model):
    """Registro de productos solicitados pero no vendidos (stock insuficiente o no encontrados)."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='demandas_insatisfechas', verbose_name="Empresa")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Sucursal")
    producto_nombre = models.CharField(max_length=500, verbose_name="Nombre del Producto")
    cantidad_dejada = models.IntegerField(verbose_name="Cantidad No Vendida", help_text="Diferencia entre cantidad recetada y cantidad vendida")
    causa = models.CharField(
        max_length=100,
        choices=[
            ('SIN_STOCK', 'Sin Stock Disponible'),
            ('NO_ENCONTRADO', 'Producto No Encontrado en Catálogo'),
            ('PRECIO_INACEPTABLE', 'Precio No Aceptado por Cliente'),
            ('OTRO', 'Otra Causa')
        ],
        default='SIN_STOCK',
        verbose_name="Causa"
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, verbose_name="Usuario que Registró")
    receta_item = models.ForeignKey(RecetaItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='demandas', verbose_name="Item de Receta Relacionado")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        app_label = 'core'
        verbose_name = "Demanda Insatisfecha"
        verbose_name_plural = "Demandas Insatisfechas"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.producto_nombre} - {self.cantidad_dejada} unidades - {self.causa}"


# ==============================================================================
# 5. VENTAS Y FINANZAS: RIGOR FISCAL Y SEGURIDAD
# ==============================================================================
class Venta(TenantModel):
    """Registro de transacciones con soporte para pago referenciado y sello digital."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sucursal")
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, verbose_name="Cajero")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha/Hora de Generación")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Importe Neto")
    impuestos_iva = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Impuestos (IVA)")
    redondeo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Ajuste por Redondeo")
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Total a Recibir")

    folio_operacion = models.CharField(max_length=50, unique=True, null=True, verbose_name="Folio y Paginado")
    linea_captura = models.CharField(max_length=100, unique=True, null=True, verbose_name="Línea de Captura Única")
    sello_digital = models.TextField(blank=True, null=True, verbose_name="Sello y Firma Digital")

    paciente = models.ForeignKey('Paciente', on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas', verbose_name="Paciente / Cliente (Ambulatorio/Lab)")
    paciente_nombre = models.CharField(max_length=255, blank=True, null=True, verbose_name="Cliente Anónimo (Farmacia Rápida)", help_text="Usado para ventas rápidas sin crear expediente. Ej: 'Público General'")
    fecha_limite_pago = models.DateField(null=True, blank=True, verbose_name="Fecha Límite de Pago")
    observaciones = models.TextField(default="SIN OBSERVACIONES", verbose_name="Bitácora de Observaciones")
    poliza_aclaracion = models.CharField(max_length=255, default="PLAZO DE ACLARACIÓN: 90 DÍAS HÁBILES", verbose_name="Política de Aclaración")

    descuento_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Descuento Aplicado")
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Porcentaje de Descuento Aplicado")
    politica_descuento = models.ForeignKey('DiscountPolicy', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Política de Descuento Utilizada")

    receta = models.ForeignKey(Receta, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas', verbose_name="Receta Vinculada")
    estado = models.CharField(
        max_length=20,
        default='COMPLETADA',
        choices=[
            ('PENDIENTE', 'Pendiente'),
            ('COMPLETADA', 'Completada'),
            ('CANCELADA', 'Cancelada'),
        ],
    )

    efectivo_recibido = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True, verbose_name="Efectivo Recibido (Billete)", help_text="Monto del billete que recibió el cajero")
    cambio_entregado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True, verbose_name="Cambio Entregado", help_text="Monto de cambio devuelto al cliente")

    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Eliminación", help_text="Para Soft Delete - no borrar físicamente")
    motivo_eliminacion = models.TextField(blank=True, null=True, verbose_name="Motivo de Eliminación")

    es_cortesia = models.BooleanField(default=False, verbose_name="Es Cortesía / Beca", help_text="Indica si esta venta es un apoyo social (sin cobro)")
    motivo_cortesia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Motivo de Cortesía",
                                       choices=[
                                           ('MEDICO', 'Médico / Personal de Salud'),
                                           ('COLABORADOR', 'Colaborador Interno'),
                                           ('VULNERABILIDAD', 'Vulnerabilidad Alta'),
                                           ('OTRO', 'Otro')
                                       ])
    autorizado_por_cortesia = models.CharField(max_length=200, blank=True, null=True, verbose_name="Autorizado por (Cortesía)")
    total_original = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         verbose_name="Total Original",
                                         help_text="Valor original antes de aplicar cortesía (para estadísticas)")

    # Campo de idempotencia para descuento de inventario (integridad transaccional)
    inventario_descontado = models.BooleanField(
        default=False,
        verbose_name="Inventario Descontado",
        help_text="True si el Kardex ya descontó el stock. Previene doble descuento en reconexiones de signal."
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['empresa', 'fecha']),
            models.Index(fields=['empresa', 'estado', 'fecha']),
        ]

    def save(self, *args, **kwargs):
        if not self.folio_operacion:
            from django.utils import timezone as _tz
            ahora = _tz.localtime(_tz.now())
            prefijo = f'VTA-{ahora.strftime("%Y%m")}-'
            ultimos = Venta.objects.filter(folio_operacion__startswith=prefijo).count()
            self.folio_operacion = f'{prefijo}{str(ultimos + 1).zfill(5)}'
        if not self.linea_captura:
            self.linea_captura = f"PRI-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)


class DetalleVenta(models.Model):
    """Partida detallada de cada producto vendido, vinculado a su lote específico."""
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey('Producto', on_delete=models.PROTECT)
    lote_vendido = models.ForeignKey('Lote', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Número de Serie / Lote Surtido")
    cantidad = models.IntegerField(verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario")
    iva_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="IVA Trasladado")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Subtotal Partida")
    costo_unitario_momento = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Costo unitario al momento de la venta"
    )

    class Meta:
        app_label = 'core'


class DetalleVentaLote(models.Model):
    """
    Trazabilidad COFEPRIS / FEFO: cantidad surtida por cada lote físico en una partida de venta.
    Un DetalleVenta puede tener N filas aquí si el PEPS consumió varios lotes.
    """
    detalle_venta = models.ForeignKey(
        DetalleVenta,
        on_delete=models.CASCADE,
        related_name="lotes_extraidos",
        verbose_name="Partida de venta",
    )
    lote = models.ForeignKey(
        "Lote",
        on_delete=models.PROTECT,
        related_name="detalles_venta_consumo",
        verbose_name="Lote surtido",
    )
    cantidad_extraida = models.PositiveIntegerField(
        verbose_name="Cantidad extraída de este lote",
        help_text="Unidades enteras retiradas de este lote para esta partida.",
    )

    class Meta:
        app_label = "core"
        verbose_name = "Detalle venta por lote (trazabilidad)"
        verbose_name_plural = "Detalle ventas por lote"
        indexes = [
            models.Index(fields=["detalle_venta", "lote"], name="core_dvl_det_lote_idx"),
        ]

    def __str__(self):
        return f"{self.detalle_venta_id} ← Lote {self.lote_id} × {self.cantidad_extraida}"


class DevolucionVenta(models.Model):
    """Registro forense de devoluciones de productos vendidos."""
    RAZON_CHOICES = [
        ('CADUCADO', 'Producto Caducado/Por Caducar'),
        ('DEFECTUOSO', 'Defecto de Fábrica'),
        ('ERROR_CAJERO', 'Error en Venta/Cobro'),
        ('CAMBIO_MEDICO', 'Cambio de Prescripción Médica'),
        ('CAMBIO_CLIENTE', 'Cambio de Opinión del Cliente'),
        ('REACCION_ADVERSA', 'Reacción Adversa Reportada'),
        ('OTRO', 'Otro (Especificar)'),
    ]
    venta_original = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name='devoluciones_forenses')
    detalle_venta = models.ForeignKey(DetalleVenta, on_delete=models.PROTECT, related_name='devoluciones_forenses')
    cantidad_devuelta = models.IntegerField()
    monto_devuelto = models.DecimalField(max_digits=10, decimal_places=2)
    razon = models.CharField(max_length=50, choices=RAZON_CHOICES)
    descripcion_detallada = models.TextField()
    evidencia_foto = models.ImageField(upload_to='devoluciones/%Y/%m/', null=True, blank=True, validators=[validate_image_upload])
    solicitado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='devoluciones_solicitadas_forense')
    autorizado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='devoluciones_autorizadas_forense')
    fecha_devolucion = models.DateTimeField(auto_now_add=True)
    reintegrado_inventario = models.BooleanField(default=False)
    lote_reintegrado = models.ForeignKey('Lote', on_delete=models.SET_NULL, null=True, blank=True)
    fecha_reintegracion = models.DateTimeField(null=True, blank=True)
    metodo_reembolso = models.CharField(
        max_length=50,
        choices=[('EFECTIVO', 'Efectivo'), ('TARJETA', 'Devolución a Tarjeta'), ('NOTA_CREDITO', 'Nota de Crédito')],
        default='EFECTIVO'
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='devoluciones_forenses')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name='devoluciones_forenses')

    class Meta:
        app_label = 'core'
        verbose_name = "Devolución de Venta (Forense)"
        verbose_name_plural = "Devoluciones de Ventas (Forenses)"
        ordering = ['-fecha_devolucion']
        indexes = [
            models.Index(fields=['empresa', 'sucursal', '-fecha_devolucion']),
            models.Index(fields=['razon', '-fecha_devolucion']),
        ]

    def __str__(self):
        prod_nombre = 'N/A'
        if self.detalle_venta and self.detalle_venta.producto:
            prod_nombre = self.detalle_venta.producto.nombre
        return f"Devolución Forense {self.id} - {prod_nombre} x{self.cantidad_devuelta}"

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        if self.detalle_venta and self.cantidad_devuelta > self.detalle_venta.cantidad:
            raise ValidationError("No se puede devolver más de lo vendido")
        super().save(*args, **kwargs)
        try:
            prod_nombre = 'N/A'
            if self.detalle_venta and self.detalle_venta.producto:
                prod_nombre = self.detalle_venta.producto.nombre
            from django.apps import apps
            AuditLog = apps.get_model('core', 'AuditLog')
            AuditLog.objects.create(
                empresa=self.empresa,
                usuario=self.autorizado_por,
                accion='UPDATE',
                modelo_afectado='DevolucionVenta',
                objeto_id=str(self.id),
                datos_nuevos={
                    'descripcion': f'Devolución: {prod_nombre} x{self.cantidad_devuelta}',
                    'cantidad_devuelta': self.cantidad_devuelta,
                    'monto_devuelto': str(self.monto_devuelto),
                    'razon': self.razon,
                },
            )
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en save (ventas.py)")
            pass  # Auditoría best-effort: no debe fallar la transacción principal de devolución.


class Pago(models.Model):
    METODOS = [
        ('EFECTIVO', 'Efectivo'),
        ('SPEI', 'Transferencia (SPEI)'),
        ('SANTANDER', 'Banco Santander'),
        ('BBVA', 'Banco BBVA'),
        ('BANAMEX', 'Banco Banamex'),
        ('OXXO', 'OXXO / 7-24'),
        ('TIENDA', 'Chedraui / Walmart / Ahorro'),
        ('TARJETA', 'Tarjeta de Crédito/Débito'),
    ]
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos', null=True, blank=True)
    metodo = models.CharField(max_length=50, choices=METODOS, verbose_name="Método de Pago")
    clabe_interbancaria = models.CharField(max_length=20, blank=True, null=True, default="0123 4567 8901 2345", verbose_name="CLABE para SPEI")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Recibido")

    monto_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Monto en Efectivo")
    monto_tarjeta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Monto en Tarjeta")
    monto_transferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Monto en Transferencia")
    referencia_pago = models.CharField(max_length=50, blank=True, null=True, verbose_name="Referencia de Pago", help_text="Número de autorización, referencia de transferencia, etc.")
    fecha_pago = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Pago")

    class Meta:
        app_label = 'core'


class PagoOrden(TenantModel):
    """
    Registro de pagos multimodales para órdenes de laboratorio.
    Auditoría forense: cada registro incluye quién cobró, cuándo y si fue cancelado.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='pagos_orden', null=True, blank=True, verbose_name='Empresa')
    orden = models.ForeignKey('OrdenDeServicio', on_delete=models.PROTECT, related_name='pagos_realizados', verbose_name="Orden de Servicio")
    monto_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Efectivo")
    monto_credito = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="T. Crédito")
    monto_debito = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="T. Débito")
    # monto_tarjeta mantiene la suma crédito+débito para compatibilidad con código legacy
    monto_tarjeta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Tarjeta (Total)")
    monto_transferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Transferencia")
    referencia_pago = models.CharField(max_length=200, blank=True, null=True, verbose_name="Referencia / Autorización")
    fecha_pago = models.DateTimeField(default=timezone.now, verbose_name="Fecha y Hora del Cobro")
    usuario_registro = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pagos_registrados', verbose_name="Cobrado por"
    )
    # ── Auditoría de cancelación ──────────────────────────────────────────────
    cancelado = models.BooleanField(default=False, verbose_name="Cancelado")
    cancelado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pagos_cancelados', verbose_name="Cancelado por"
    )
    fecha_cancelacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Cancelación")
    motivo_cancelacion = models.CharField(max_length=200, blank=True, null=True, verbose_name="Motivo de Cancelación")

    client_mutation_id = models.UUIDField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
        verbose_name="Idempotencia cliente (offline)",
        help_text="UUID enviado por el cliente para deduplicar el cobro al sincronizar sin red.",
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Pago de Orden"
        verbose_name_plural = "Pagos de Órdenes"
        ordering = ['-fecha_pago']
        constraints = [
            models.UniqueConstraint(
                fields=['orden', 'client_mutation_id'],
                condition=models.Q(client_mutation_id__isnull=False),
                name='unique_pago_orden_client_mutation',
            ),
        ]

    def __str__(self):
        return f"Pago Orden #{self.orden.id} - ${self.monto_total:.2f}"

    @property
    def monto_total(self):
        """Monto total del pago activo (excluye si está cancelado)."""
        if self.cancelado:
            return Decimal('0.00')
        return self.monto_efectivo + self.monto_tarjeta + self.monto_transferencia

    @property
    def monto_bruto(self):
        """Monto original (sin considerar cancelación)."""
        return self.monto_efectivo + self.monto_tarjeta + self.monto_transferencia

    def save(self, *args, **kwargs):
        if self.orden_id:
            self.empresa_id = self.orden.empresa_id
        super().save(*args, **kwargs)


class Gasto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    concepto = models.CharField(max_length=255)

    class Meta:
        app_label = 'core'
        indexes = [
            models.Index(fields=['empresa', '-fecha'], name='gasto_empresa_fecha_idx'),
        ]


class AjusteInventario(models.Model):
    TIPOS_AJUSTE = [
        ('MERMA', 'Merma (Rotura/Daño)'),
        ('CADUCIDAD', 'Caducidad Vencida'),
        ('ROBO', 'Robo / Faltante'),
        ('USO_INTERNO', 'Uso Interno / Laboratorio'),
        ('CORRECCION', 'Corrección de Inventario'),
    ]

    producto = models.ForeignKey('Producto', on_delete=models.PROTECT)
    lote = models.ForeignKey('Lote', on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    tipo_movimiento = models.CharField(max_length=20, choices=TIPOS_AJUSTE)
    observacion = models.TextField(blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    class Meta:
        app_label = 'core'

    def __str__(self):
        return f"{self.tipo_movimiento} - {self.producto.nombre}"


class GastoCaja(models.Model):
    """Registro de salidas menores de dinero de caja (garrafón, limpieza, etc.)."""
    concepto = models.CharField(max_length=100, verbose_name="Concepto")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, verbose_name="Usuario que registra")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, verbose_name="Empresa")
    documento_adjunto = models.FileField(
        upload_to='gastos_caja/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Comprobante / documento",
        help_text="Obligatorio si el monto supera el límite Zona Verde (Política de Límites de la empresa).",
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Gasto de Caja"
        verbose_name_plural = "Gastos de Caja"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['empresa', '-fecha'], name='gastocaja_empresa_fecha_idx'),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        politica = getattr(self.empresa, 'politica_caja', None)
        if politica and self.monto is not None and self.monto > politica.limite_verde:
            if not self.documento_adjunto:
                raise ValidationError(
                    {
                        'documento_adjunto': (
                            f'Gastos mayores a ${politica.limite_verde} (Zona Verde) requieren '
                            'documento_adjunto según Bankguard.'
                        )
                    }
                )

    def save(self, *args, **kwargs):
        skip = kwargs.pop('skip_politica_clean', False)
        if not skip:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"- ${self.monto} ({self.concepto})"


class MovimientoCaja(models.Model):
    """KARDEX DE CAJA - Registro forense de TODOS los movimientos de efectivo."""
    TIPO_MOVIMIENTO_CHOICES = [
        ('INGRESO', 'Ingreso (Venta, Cobro)'),
        ('EGRESO', 'Egreso (Reembolso, Gasto)'),
        ('AJUSTE', 'Ajuste (Arqueo, Corrección)'),
        ('TRANSFERENCIA', 'Transferencia (Retiro a Bóveda)'),
    ]

    CONCEPTO_CHOICES = [
        ('VENTA', 'Venta de Producto/Servicio'),
        ('REEMBOLSO_DEVOLUCION', 'Reembolso por Devolución'),
        ('GASTO_MENOR', 'Gasto Menor (Operativo)'),
        ('ARQUEO', 'Arqueo de Caja'),
        ('RETIRO_BOVEDA', 'Retiro a Bóveda/Banco'),
        ('APERTURA_CAJA', 'Apertura de Caja (Fondo Inicial)'),
        ('CIERRE_CAJA', 'Cierre de Caja'),
        ('OTRO', 'Otro (Especificar en Referencia)'),
    ]

    caja_nombre = models.CharField(
        max_length=100, verbose_name="Nombre de Caja", null=True, blank=True,
        help_text="Identificador de la caja física (ej: 'Caja 1', 'Caja Principal')"
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='movimientos_caja', verbose_name="Empresa")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name='movimientos_caja', verbose_name="Sucursal")

    tipo_movimiento = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO_CHOICES, verbose_name="Tipo de Movimiento", db_index=True)
    concepto = models.CharField(max_length=50, choices=CONCEPTO_CHOICES, verbose_name="Concepto", db_index=True)

    monto = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Monto",
        help_text="Cantidad en pesos (siempre positiva, el tipo define si es ingreso/egreso)"
    )

    usuario_responsable = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name='movimientos_caja_realizados',
        verbose_name="Usuario Responsable", null=True, blank=True
    )
    fecha_movimiento = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora del Movimiento", db_index=True)

    referencia = models.CharField(
        max_length=255, verbose_name="Referencia",
        help_text="Descripción adicional o número de folio relacionado", blank=True
    )
    
    # 🔐 NIVEL 1.5: Idempotency Key (Bankguard v1.14)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Clave de Idempotencia",
        help_text="UUID único para evitar duplicados en retries/reconexiones HTTP/Celery"
    )
    
    venta = models.ForeignKey('Venta', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_caja', verbose_name="Venta Relacionada")
    devolucion_venta = models.ForeignKey('DevolucionVenta', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_caja', verbose_name="Devolución Relacionada")

    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Saldo Anterior", null=True, blank=True, help_text="Saldo de caja antes de este movimiento")
    saldo_posterior = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Saldo Posterior", null=True, blank=True, help_text="Saldo de caja después de este movimiento")

    class Meta:
        app_label = 'core'
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"
        ordering = ['-fecha_movimiento']
        indexes = [
            models.Index(fields=['empresa', 'sucursal', '-fecha_movimiento']),
            models.Index(fields=['tipo_movimiento', '-fecha_movimiento']),
            models.Index(fields=['concepto', '-fecha_movimiento']),
            models.Index(fields=['usuario_responsable', '-fecha_movimiento']),
            models.Index(fields=['idempotency_key'], name='mov_caja_idem_idx'),  # 🔐 NUEVO v1.14
        ]

    def __str__(self):
        signo = '+' if self.tipo_movimiento == 'INGRESO' else '-'
        return (
            f"{self.get_tipo_movimiento_display()} | "
            f"{self.get_concepto_display()} | "
            f"{signo}${self.monto:.2f} | "
            f"{self.fecha_movimiento.strftime('%d/%m/%Y %H:%M')}"
        )

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        if self.monto <= 0:
            raise ValidationError("El monto debe ser mayor a 0")
        was_new = self.pk is None
        super().save(*args, **kwargs)
        if hasattr(self, 'empresa') and self.empresa:
            try:
                from django.apps import apps
                AuditLog = apps.get_model('core', 'AuditLog')
                AuditLog.objects.create(
                    empresa=self.empresa,
                    usuario=self.usuario_responsable,
                    accion='CREATE' if was_new else 'UPDATE',
                    modelo_afectado='MovimientoCaja',
                    objeto_id=str(self.pk),
                    datos_nuevos={
                        'descripcion': f"{self.get_tipo_movimiento_display()}: {self.get_concepto_display()} - ${self.monto:.2f}",
                        'monto': str(self.monto),
                    },
                )
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en save (ventas.py)")
                pass  # Auditoría best-effort: no debe fallar la transacción principal de caja.


# ==============================================================================
# 8. FINANZAS 4.0 - GASTOS OPERATIVOS
# ==============================================================================
class GastoOperativo(models.Model):
    CATEGORIA_CHOICES = [
        ("SERVICIOS", "Servicios"),
        ("INSUMOS", "Insumos"),
        ("MANTENIMIENTO", "Mantenimiento"),
        ("NOMINA", "Nómina"),
        ("OTROS", "Otros"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="gastos_operativos")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, related_name="gastos_operativos")
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name="gastos_operativos")

    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, default="OTROS")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    evidencia_foto = models.ImageField(upload_to="gastos_operativos/", blank=True, null=True, validators=[validate_image_upload])
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Gasto Operativo"
        verbose_name_plural = "Gastos Operativos"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=['empresa', '-fecha'], name='gastoop_empresa_fecha_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.categoria} - ${self.monto}"


class FacturaSAT(models.Model):
    """Facturación 4.0 (SAT) - placeholder."""
    ESTATUS_BORRADOR = "BORRADOR"
    ESTATUS_TIMBRADA = "TIMBRADA"
    ESTATUS_CANCELADA = "CANCELADA"
    ESTATUS_CHOICES = [
        (ESTATUS_BORRADOR, "Borrador"),
        (ESTATUS_TIMBRADA, "Timbrada"),
        (ESTATUS_CANCELADA, "Cancelada"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="facturas_sat")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, related_name="facturas_sat")
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="facturas_sat")

    paciente = models.ForeignKey("Paciente", on_delete=models.SET_NULL, null=True, blank=True, related_name="facturas_sat")
    venta = models.ForeignKey("Venta", on_delete=models.SET_NULL, null=True, blank=True, related_name="facturas_sat")

    folio = models.CharField(max_length=80, blank=True, null=True)
    uuid = models.CharField(max_length=80, blank=True, null=True, help_text="UUID SAT (cuando esté timbrada)")
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default=ESTATUS_BORRADOR)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Factura SAT"
        verbose_name_plural = "Facturas SAT"
        ordering = ["-fecha_creacion"]


# ==============================================================================
# 7. MÓDULO DE DEVOLUCIONES Y AUDITORÍA DE ERRORES
# ==============================================================================
class SalesReturn(models.Model):
    """Registro de devoluciones con auditoría completa de quién cometió el error."""
    TIPOS_DEVOLUCION = [
        ('PARCIAL', 'Devolución Parcial'),
        ('TOTAL', 'Devolución Total'),
    ]
    ACCIONES_STOCK = [
        ('RETORNO_ALMACEN', 'Retorno al Almacén (Reutilizable)'),
        ('MERMA_DESECHO', 'Merma / Desecho (No Reutilizable)'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='devoluciones')
    venta_original = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name='devoluciones', verbose_name="Venta Original")
    tipo_devolucion = models.CharField(max_length=10, choices=TIPOS_DEVOLUCION, verbose_name="Tipo de Devolución")

    monto_reembolsado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Reembolsado")

    motivo_error = models.TextField(verbose_name="Motivo del Error / Razón de Devolución")
    usuario_error_origen = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True,
        related_name='errores_cometidos',
        verbose_name="¿Quién cometió el error original? (Cajero/Químico)"
    )
    usuario_autorizo = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True,
        related_name='devoluciones_autorizadas',
        verbose_name="¿Quién autoriza la devolución? (Gerente/Nancy)"
    )

    accion_stock = models.CharField(max_length=20, choices=ACCIONES_STOCK, verbose_name="Acción con el Stock")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones Adicionales")
    fecha_devolucion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Devolución")

    class Meta:
        app_label = 'core'
        verbose_name = "Devolución de Venta"
        verbose_name_plural = "Devoluciones de Ventas"
        ordering = ['-fecha_devolucion']

    def __str__(self):
        return f"Devolución #{self.id} - Venta #{self.venta_original.id} - ${self.monto_reembolsado}"


class MetaVenta(models.Model):
    """Metas de venta diarias por sucursal."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='metas_venta', verbose_name='Empresa')
    monto_objetivo = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto Objetivo')
    fecha = models.DateField(default=timezone.now, verbose_name='Fecha de Meta')
    sucursal = models.CharField(max_length=100, blank=True, null=True, verbose_name='Sucursal')
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, verbose_name='Creado por')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Meta de Venta'
        verbose_name_plural = 'Metas de Venta'
        unique_together = ['empresa', 'fecha', 'sucursal']

    def __str__(self):
        return f"Meta {self.fecha} - ${self.monto_objetivo}"


# ==============================================================================
# BLOQUE: CUENTAS POR COBRAR (CREDITOS A EMPRESAS)
# ==============================================================================
class CuentaPorCobrar(models.Model):
    """Registro de credito otorgado a una empresa/convenio."""
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de Cobro'),
        ('PARCIAL', 'Pago Parcial'),
        ('COBRADO', 'Cobrado Totalmente'),
        ('VENCIDO', 'Vencido'),
        ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cuentas_por_cobrar')
    convenio = models.ForeignKey('Convenio', on_delete=models.PROTECT, related_name='cuentas', verbose_name='Empresa / Convenio')
    orden = models.ForeignKey('OrdenDeServicio', on_delete=models.PROTECT, null=True, blank=True,
                               related_name='cuentas_por_cobrar', verbose_name='Orden de Servicio')
    venta = models.ForeignKey('Venta', on_delete=models.PROTECT, null=True, blank=True,
                               related_name='cuentas_por_cobrar', verbose_name='Venta')

    folio = models.CharField(max_length=50, unique=True, verbose_name='Folio CxC')
    concepto = models.CharField(max_length=500, verbose_name='Concepto')
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto Total')
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Monto Pagado')
    saldo_pendiente = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Saldo Pendiente')

    fecha_emision = models.DateField(auto_now_add=True, verbose_name='Fecha de Emision')
    fecha_vencimiento = models.DateField(verbose_name='Fecha de Vencimiento')
    fecha_cobro = models.DateField(null=True, blank=True, verbose_name='Fecha de Cobro')

    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PENDIENTE')
    notas = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Cuenta por Cobrar'
        verbose_name_plural = 'Cuentas por Cobrar'
        ordering = ['-fecha_vencimiento']
        indexes = [
            models.Index(fields=['empresa', 'estado', '-fecha_vencimiento'], name='core_cuentap_empresa_idx'),
            models.Index(fields=['convenio', 'estado'], name='core_cuentap_convenio_idx'),
        ]

    def __str__(self):
        return f'CxC {self.folio} - {self.convenio.nombre} - ${self.saldo_pendiente}'

    @property
    def esta_vencida(self):
        from django.utils import timezone
        return self.estado == 'PENDIENTE' and self.fecha_vencimiento < timezone.now().date()

    @property
    def dias_vencida(self):
        from django.utils import timezone
        if self.esta_vencida:
            return (timezone.now().date() - self.fecha_vencimiento).days
        return 0


class PagoCuentaPorCobrar(models.Model):
    """Registro de pagos parciales o totales a una cuenta por cobrar."""
    cuenta = models.ForeignKey(CuentaPorCobrar, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(max_length=30, choices=[
        ('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'),
        ('CHEQUE', 'Cheque'), ('DEPOSITO', 'Deposito'),
    ], default='TRANSFERENCIA')
    referencia = models.CharField(max_length=200, blank=True, null=True, help_text='Numero de transferencia, cheque, etc.')
    fecha_pago = models.DateField(auto_now_add=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Pago de Cuenta por Cobrar'
        verbose_name_plural = 'Pagos de Cuentas por Cobrar'
        ordering = ['-fecha_pago']

    def __str__(self):
        return f'Pago ${self.monto} → {self.cuenta.folio}'


class NotaCredito(models.Model):
    """Nota de credito fiscal para devoluciones o ajustes."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='notas_credito')
    folio = models.CharField(max_length=50, unique=True, verbose_name='Folio Nota de Credito')
    venta_original = models.ForeignKey('Venta', on_delete=models.PROTECT, null=True, blank=True, related_name='notas_credito')
    orden_original = models.ForeignKey('OrdenDeServicio', on_delete=models.PROTECT, null=True, blank=True, related_name='notas_credito')
    devolucion = models.ForeignKey('DevolucionVenta', on_delete=models.SET_NULL, null=True, blank=True, related_name='notas_credito')

    monto = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto de la Nota')
    motivo = models.CharField(max_length=50, choices=[
        ('DEVOLUCION', 'Devolucion de producto'),
        ('ERROR_COBRO', 'Error de cobro'),
        ('DESCUENTO_POST', 'Descuento posterior'),
        ('CANCELACION', 'Cancelacion de servicio'),
        ('OTRO', 'Otro'),
    ])
    descripcion = models.TextField(verbose_name='Descripcion detallada')
    aplicada = models.BooleanField(default=False, verbose_name='Aplicada al saldo')

    emitida_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Nota de Credito'
        verbose_name_plural = 'Notas de Credito'
        ordering = ['-fecha_emision']

    def __str__(self):
        return f'NC {self.folio} - ${self.monto} ({self.get_motivo_display()})'