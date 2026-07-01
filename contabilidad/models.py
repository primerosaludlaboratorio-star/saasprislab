"""
Modelos del Módulo de Contabilidad y Facturación Electrónica
PRISLAB V5.0 - Cumplimiento SAT México CFDI 4.0
"""

from decimal import Decimal

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

from contabilidad.validators_cfdi40 import (
    clean_nombre_fiscal,
    validate_codigo_postal_sat40,
    validate_rfc_sat40,
)
from core.tenant import TenantModel


class ClienteFacturacion(TenantModel):
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


class FacturaCFDI(TenantModel):
    """
    Factura Electrónica CFDI 4.0
    """
    # Identificadores
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    uuid_sat = models.CharField(max_length=36, blank=True, null=True, unique=True, db_index=True)
    folio_interno = models.CharField(max_length=50, unique=True)
    serie = models.CharField(max_length=10, default='A')
    folio = models.IntegerField()

    # Empresa — FK directa para multi-tenancy y scoping de folios
    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        related_name='facturas_cfdi',
        help_text='Empresa emisora del CFDI (denormalizada de cliente.empresa para integridad y performance)',
    )
    
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
            models.Index(fields=['empresa', 'serie', 'folio']),
            models.Index(fields=['cliente', 'estado']),
            models.Index(fields=['fecha_emision']),
        ]
    
    def __str__(self):
        return f"{self.folio_interno} - {self.cliente.rfc} - ${self.total}"

    def cfdi_empresa_scope_id(self) -> int | None:
        """ID empresa para Idempotency-Key (empresa directa o usuario_creo.empresa). Sin PHI."""
        return self.empresa_id or getattr(self.usuario_creo, 'empresa_id', None)

    def save(self, *args, **kwargs):
        if not self.empresa_id and self.cliente_id:
            self.empresa = self.cliente.empresa
        if not self.folio_interno:
            empresa_id = self.empresa_id or (self.cliente.empresa_id if self.cliente_id else None)
            qs = FacturaCFDI.objects.filter(serie=self.serie)
            if empresa_id:
                qs = qs.filter(empresa_id=empresa_id)
            ultimo = qs.order_by('-folio').first()
            self.folio = (ultimo.folio + 1) if ultimo else 1
            scope = f"E{empresa_id}" if empresa_id else "EGLOBAL"
            self.folio_interno = (
                f"FAC-{scope}-{self.serie}-{timezone.localdate().year}-{self.folio:05d}"
            )
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


# =============================================================================
# CONTABILIDAD GENERAL (Catálogo de cuentas, pólizas y asientos)
# =============================================================================

class CuentaContable(TenantModel):
    """Catálogo de cuentas contables por empresa."""
    TIPO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('PASIVO', 'Pasivo'),
        ('CAPITAL', 'Capital'),
        ('INGRESO', 'Ingreso'),
        ('COSTO', 'Costo'),
        ('GASTO', 'Gasto'),
    ]
    NATURALEZA_CHOICES = [
        ('DEUDOR', 'Deudor'),
        ('ACREEDOR', 'Acreedor'),
    ]

    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='cuentas_contables')
    codigo = models.CharField(max_length=20, db_index=True)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    naturaleza = models.CharField(max_length=10, choices=NATURALEZA_CHOICES, default='DEUDOR')
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cuenta contable'
        verbose_name_plural = 'Cuentas contables'
        ordering = ['codigo']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'codigo'], name='unique_cuenta_por_empresa'),
        ]

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class Poliza(TenantModel):
    """Póliza contable: agrupa asientos de un período / concepto."""
    TIPO_CHOICES = [
        ('INGRESOS', 'Ingresos'),
        ('EGRESOS', 'Egresos'),
        ('DIARIO', 'Diario'),
        ('AJUSTE', 'Ajuste'),
        ('CIERRE', 'Cierre'),
    ]
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('AUTORIZADA', 'Autorizada'),
        ('CANCELADA', 'Cancelada'),
    ]

    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='polizas')
    folio = models.CharField(max_length=30, db_index=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='DIARIO')
    concepto = models.TextField()
    fecha = models.DateField(default=timezone.localdate)
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='BORRADOR')
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='polizas_creadas')
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='polizas_autorizadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Póliza contable'
        verbose_name_plural = 'Pólizas contables'
        ordering = ['-fecha', '-fecha_creacion']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'folio'], name='unique_folio_poliza_empresa'),
        ]

    def __str__(self):
        return f'{self.folio} - {self.concepto[:50]}'

    def save(self, *args, **kwargs):
        if not self.folio:
            prefix = self.tipo[:3]
            count = Poliza.objects.filter(empresa=self.empresa, tipo=self.tipo).count() + 1
            self.folio = f'POL-{prefix}-{timezone.localdate().year}-{count:05d}'
        super().save(*args, **kwargs)


class AsientoContable(models.Model):
    """Asiento individual dentro de una póliza."""
    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE, related_name='asientos')
    cuenta = models.ForeignKey(CuentaContable, on_delete=models.PROTECT, related_name='asientos')
    concepto = models.CharField(max_length=255, blank=True)
    cargo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    abono = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'Asiento contable'
        verbose_name_plural = 'Asientos contables'

    def __str__(self):
        return f'{self.cuenta.codigo} C:{self.cargo} A:{self.abono}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.cargo < 0 or self.abono < 0:
            raise ValidationError('Cargo y abono deben ser positivos.')
        if self.cargo == 0 and self.abono == 0:
            raise ValidationError('Debe tener cargo o abono.')
