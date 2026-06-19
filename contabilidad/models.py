"""
Modelos del Módulo de Contabilidad y Facturación Electrónica
PRISLAB V5.0 - Cumplimiento SAT México CFDI 4.0
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

from contabilidad.validators_cfdi40 import (
    clean_nombre_fiscal,
    validate_codigo_postal_sat40,
    validate_rfc_sat40,
)


class ClienteFacturacion(models.Model):
    """
    Datos fiscales del cliente para facturación electrónica
    """
    # Relación con entidades existentes
    paciente = models.ForeignKey(
        'core.Paciente',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='clientes_facturacion'
    )
    
    # FK empresa — necesaria para multi-tenancy
    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='clientes_facturacion',
    )

    # Datos Fiscales Obligatorios
    # unique=True eliminado: la unicidad se aplica por empresa vía UniqueConstraint
    rfc = models.CharField(max_length=13, db_index=True)
    razon_social = models.CharField(max_length=300)
    email = models.EmailField()
    
    # Domicilio Fiscal
    codigo_postal = models.CharField(max_length=5)
    
    # Régimen Fiscal (Catálogo SAT - simplificado)
    REGIMEN_CHOICES = [
        ('612', '612 - Personas Físicas con Actividades Empresariales'),
        ('616', '616 - Sin obligaciones fiscales'),
        ('626', '626 - Régimen Simplificado de Confianza'),
        ('601', '601 - General de Ley Personas Morales'),
    ]
    regimen_fiscal = models.CharField(max_length=3, choices=REGIMEN_CHOICES, default='616')
    
    # Uso de CFDI por defecto
    USO_CFDI_CHOICES = [
        ('G03', 'G03 - Gastos en general'),
        ('D01', 'D01 - Honorarios médicos y gastos hospitalarios'),
        ('S01', 'S01 - Sin efectos fiscales'),
    ]
    uso_cfdi_default = models.CharField(max_length=4, choices=USO_CFDI_CHOICES, default='D01')
    
    # Auditoría
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Cliente de Facturación'
        verbose_name_plural = 'Clientes de Facturación'
        ordering = ['razon_social']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'rfc'],
                name='unique_rfc_por_empresa',
            )
        ]
    
    def __str__(self):
        return f"{self.rfc} - {self.razon_social}"

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if not self.empresa_id:
            raise ValidationError({'empresa': 'La empresa es obligatoria para ClienteFiscal (multi-tenant).'})
        if self.rfc:
            self.rfc = self.rfc.strip().upper()
            validate_rfc_sat40(self.rfc)
        if self.codigo_postal:
            self.codigo_postal = self.codigo_postal.strip()
            validate_codigo_postal_sat40(self.codigo_postal)
        if self.razon_social:
            self.razon_social = clean_nombre_fiscal(self.razon_social)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class FacturaCFDI(models.Model):
    """
    Factura Electrónica CFDI 4.0
    """
    # Identificadores
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    uuid_sat = models.CharField(max_length=36, blank=True, null=True, unique=True, db_index=True)
    folio_interno = models.CharField(max_length=50, unique=True)
    serie = models.CharField(max_length=10, default='A')
    folio = models.IntegerField()
    
    # Cliente
    cliente = models.ForeignKey(ClienteFacturacion, on_delete=models.PROTECT, related_name='facturas')
    
    # Fechas
    fecha_emision = models.DateTimeField(default=timezone.now)
    fecha_timbrado = models.DateTimeField(null=True, blank=True)
    
    # Tipo y Forma de Pago
    TIPO_CHOICES = [('I', 'Ingreso'), ('E', 'Egreso'), ('P', 'Pago')]
    tipo_comprobante = models.CharField(max_length=1, choices=TIPO_CHOICES, default='I')
    
    FORMA_PAGO_CHOICES = [
        ('01', '01 - Efectivo'),
        ('03', '03 - Transferencia'),
        ('04', '04 - Tarjeta de crédito'),
        ('28', '28 - Tarjeta de débito'),
    ]
    forma_pago = models.CharField(max_length=2, choices=FORMA_PAGO_CHOICES, default='01')
    
    METODO_PAGO_CHOICES = [
        ('PUE', 'Pago en una sola exhibición'),
        ('PPD', 'Pago en parcialidades o diferido'),
    ]
    metodo_pago = models.CharField(max_length=3, choices=METODO_PAGO_CHOICES, default='PUE')
    
    # Montos
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    total_impuestos_trasladados = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Estado
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('PENDIENTE', 'Pendiente de timbrar'),
        ('FACTURANDO', 'Timbrado en curso (PAC)'),
        ('TIMBRADO', 'Timbrado'),
        ('CANCELADO', 'Cancelado'),
        ('ERROR', 'Error'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR', db_index=True)
    
    # XML
    xml_timbrado = models.TextField(blank=True)
    
    # Relaciones con operaciones
    orden_laboratorio = models.ForeignKey(
        'core.OrdenDeServicio',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='facturas'
    )

    # Puente fiscal Hito 16: trazabilidad cobro Lab / ticket PDV (core.Venta usado por farmacia).
    pago_orden = models.ForeignKey(
        'core.PagoOrden',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='facturas_cfdi',
        verbose_name='Pago de orden (laboratorio)',
    )
    venta_farmacia = models.ForeignKey(
        'core.Venta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='facturas_cfdi',
        verbose_name='Venta (farmacia / PDV)',
    )

    # Auditoría
    usuario_creo = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # H-001/H-002: evita timbrados concurrentes duplicados ante el SAT (además de select_for_update)
    timbrando_en_proceso = models.BooleanField(default=False, db_index=True)
    timbrado_intento_en = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Inicio intento timbrado',
        help_text='Marca de tiempo al entrar en FACTURANDO; usado por reconciliar_facturas_pendientes.',
    )
    ultimo_error_pac = models.TextField(
        blank=True,
        default='',
        verbose_name='Último mensaje del PAC / error',
        help_text='Texto devuelto por Facturama/SAT o error interno al timbrar.',
    )

    class Meta:
        verbose_name = 'Factura CFDI 4.0'
        verbose_name_plural = 'Facturas CFDI 4.0'
        ordering = ['-fecha_emision']
        indexes = [
            models.Index(fields=['cliente', 'estado']),
            models.Index(fields=['fecha_emision']),
        ]
    
    def __str__(self):
        return f"{self.folio_interno} - {self.cliente.rfc} - ${self.total}"

    def cfdi_empresa_scope_id(self) -> int | None:
        """ID empresa para Idempotency-Key (cliente.empresa o usuario_creo.empresa). Sin PHI."""
        if self.cliente_id and getattr(self.cliente, 'empresa_id', None):
            return self.cliente.empresa_id
        return getattr(self.usuario_creo, 'empresa_id', None)

    def save(self, *args, **kwargs):
        if not self.folio_interno:
            ultimo = FacturaCFDI.objects.filter(serie=self.serie).order_by('-folio').first()
            self.folio = (ultimo.folio + 1) if ultimo else 1
            self.folio_interno = f"FAC-{self.serie}-{timezone.now().year}-{self.folio:05d}"
        super().save(*args, **kwargs)


class ConceptoFactura(models.Model):
    """
    Conceptos/líneas de detalle de una factura
    """
    factura = models.ForeignKey(FacturaCFDI, on_delete=models.CASCADE, related_name='conceptos')
    numero_linea = models.IntegerField()
    
    # Clave del SAT (simplificado)
    clave_producto_servicio = models.CharField(max_length=10, default='85121801')  # Servicios de laboratorio
    clave_unidad = models.CharField(max_length=10, default='E48')  # Unidad de servicio
    
    # Descripción
    descripcion = models.TextField()
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    importe = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Objeto de Impuesto
    OBJETO_IMP_CHOICES = [
        ('01', 'No objeto de impuesto'),
        ('02', 'Sí objeto de impuesto'),
    ]
    objeto_impuesto = models.CharField(max_length=2, choices=OBJETO_IMP_CHOICES, default='02')
    
    class Meta:
        verbose_name = 'Concepto de Factura'
        verbose_name_plural = 'Conceptos de Factura'
        ordering = ['factura', 'numero_linea']
    
    def __str__(self):
        return f"{self.factura.folio_interno} - Línea {self.numero_linea}"
    
    def save(self, *args, **kwargs):
        self.importe = self.cantidad * self.valor_unitario
        super().save(*args, **kwargs)


class ImpuestoConcepto(models.Model):
    """
    Impuestos aplicados a cada concepto
    """
    concepto = models.ForeignKey(ConceptoFactura, on_delete=models.CASCADE, related_name='impuestos')
    
    # Tipo
    TIPO_CHOICES = [('TRASLADO', 'Traslado'), ('RETENCION', 'Retención')]
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    
    # Impuesto
    IMPUESTO_CHOICES = [('001', 'ISR'), ('002', 'IVA'), ('003', 'IEPS')]
    impuesto = models.CharField(max_length=3, choices=IMPUESTO_CHOICES, default='002')
    
    # Tasa
    tasa_o_cuota = models.DecimalField(max_digits=10, decimal_places=6, default=0.160000)
    tipo_factor = models.CharField(max_length=10, default='Tasa')
    
    # Montos
    base = models.DecimalField(max_digits=12, decimal_places=2)
    importe = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        verbose_name = 'Impuesto de Concepto'
        verbose_name_plural = 'Impuestos de Conceptos'
    
    def __str__(self):
        return f"{self.get_impuesto_display()} - ${self.importe}"
    
    def save(self, *args, **kwargs):
        if self.tipo_factor != 'Exento':
            self.importe = self.base * self.tasa_o_cuota
        else:
            self.importe = 0
        super().save(*args, **kwargs)
