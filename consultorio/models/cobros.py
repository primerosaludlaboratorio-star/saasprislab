"""
Modelos de caja, cobros y vales de liquidación del consultorio.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models


# ==============================================================================
# FASE 10: BLINDAJE DE COBROS - CAJA INDEPENDIENTE DEL MÉDICO
# ==============================================================================

class CajaConsultorio(models.Model):
    """
    Caja virtual segregada por médico.
    Cada médico tiene su propio 'libro contable' independiente de la caja
    general del laboratorio/recepción.
    Permite ver acumulados diarios, semanales y mensuales.
    """
    ESTADO_CHOICES = [
        ('ABIERTA', 'Abierta'),
        ('CERRADA', 'Cerrada'),
        ('LIQUIDADA', 'Liquidada'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="cajas_consultorio"
    )
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="cajas_consultorio",
        verbose_name="Médico titular"
    )

    fecha = models.DateField(verbose_name="Fecha de la caja")
    estado = models.CharField(
        max_length=15, choices=ESTADO_CHOICES, default='ABIERTA',
        verbose_name="Estado de la caja"
    )

    # Totales calculados (denormalizados para velocidad)
    total_efectivo = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Total Efectivo"
    )
    total_tarjeta = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Total Tarjeta"
    )
    total_transferencia = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Total Transferencia"
    )

    # Dinero en tránsito (cobrado por recepción)
    total_en_transito = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Dinero en Tránsito (cobrado por recepción)",
        help_text="Monto cobrado por recepción pendiente de entregar al médico"
    )
    total_liquidado = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Total Liquidado",
        help_text="Monto ya entregado al médico"
    )

    # Conteos
    consultas_cobradas = models.IntegerField(default=0)
    consultas_pendientes = models.IntegerField(default=0)

    notas_cierre = models.TextField(blank=True, verbose_name="Notas de cierre")
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Caja de Consultorio"
        verbose_name_plural = "Cajas de Consultorio"
        ordering = ['-fecha']
        unique_together = ['medico', 'fecha']

    def __str__(self):
        return f"Caja {self.fecha} - {self.medico.get_full_name()} ({self.estado})"

    @property
    def total_general(self):
        return self.total_efectivo + self.total_tarjeta + self.total_transferencia

    @property
    def pendiente_liquidar(self):
        return self.total_en_transito - self.total_liquidado


class CobroConsulta(models.Model):
    """
    Registro individual de cobro de consulta o servicio médico.
    Soporta cobros mixtos (divididos entre efectivo/tarjeta/transferencia).
    Solo maneja conceptos de Servicio Profesional (NO inventario).
    """
    CONCEPTO_CHOICES = [
        ('CONSULTA', 'Consulta Médica'),
        ('ULTRASONIDO', 'Ultrasonido'),
        ('CERTIFICADO', 'Certificado Médico'),
        ('PROCEDIMIENTO', 'Procedimiento Menor'),
        ('OTRO', 'Otro Servicio'),
    ]

    METODO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('MIXTO', 'Pago Mixto'),
    ]

    COBRADO_POR_CHOICES = [
        ('MEDICO', 'Cobrado por el Médico'),
        ('RECEPCION', 'Cobrado en Recepción'),
    ]

    ESTADO_CHOICES = [
        ('PAGADO', 'Pagado'),
        ('PENDIENTE', 'Pendiente'),
        ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="cobros_consultorio"
    )
    caja = models.ForeignKey(
        CajaConsultorio, on_delete=models.CASCADE,
        related_name="cobros",
        verbose_name="Caja del día"
    )

    # Vinculación al folio de consulta
    consulta = models.ForeignKey(
        "core.ConsultaMedica", on_delete=models.PROTECT,
        related_name="cobros_consultorio",
        verbose_name="Consulta vinculada"
    )
    paciente = models.ForeignKey(
        "core.Paciente", on_delete=models.PROTECT,
        related_name="cobros_consultorio"
    )
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="cobros_realizados"
    )

    # Concepto (solo servicios, NO inventario)
    concepto = models.CharField(
        max_length=20, choices=CONCEPTO_CHOICES, default='CONSULTA',
        verbose_name="Concepto del servicio"
    )
    descripcion = models.CharField(
        max_length=255, blank=True,
        verbose_name="Descripción adicional"
    )

    # Montos
    monto_total = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Monto Total del servicio"
    )

    # Cobro Mixto: desglose por método de pago
    monto_efectivo = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Pagado en Efectivo"
    )
    monto_tarjeta = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Pagado con Tarjeta"
    )
    monto_transferencia = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Pagado por Transferencia"
    )

    # Método principal (o MIXTO si se usaron varios)
    metodo_pago = models.CharField(
        max_length=15, choices=METODO_CHOICES, default='EFECTIVO',
        verbose_name="Método de pago"
    )

    # Quién cobró
    cobrado_por = models.CharField(
        max_length=15, choices=COBRADO_POR_CHOICES, default='MEDICO',
        verbose_name="Cobrado por"
    )
    usuario_cobro = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cobros_procesados",
        verbose_name="Usuario que procesó el cobro"
    )

    # Estado
    estado = models.CharField(
        max_length=15, choices=ESTADO_CHOICES, default='PAGADO'
    )

    # Referencia de pago (para tarjeta/transferencia)
    referencia_pago = models.CharField(
        max_length=100, blank=True,
        verbose_name="Referencia/Aprobación",
        help_text="Número de aprobación de tarjeta o referencia de transferencia"
    )

    notas = models.TextField(blank=True, verbose_name="Notas del cobro")

    # Auditoría
    fecha_cobro = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cobro de Consulta"
        verbose_name_plural = "Cobros de Consultorio"
        ordering = ['-fecha_cobro']

    def __str__(self):
        return f"Cobro #{self.id} - {self.consulta.folio_consulta} - ${self.monto_total} ({self.get_estado_display()})"

    @property
    def es_mixto(self):
        """Verifica si el cobro usó más de un método de pago."""
        metodos_usados = sum([
            1 for m in [self.monto_efectivo, self.monto_tarjeta, self.monto_transferencia]
            if m > 0
        ])
        return metodos_usados > 1

    def save(self, *args, **kwargs):
        # Determinar si es pago mixto
        metodos = sum([
            1 for m in [self.monto_efectivo, self.monto_tarjeta, self.monto_transferencia]
            if m > 0
        ])
        if metodos > 1:
            self.metodo_pago = 'MIXTO'
        elif self.monto_tarjeta > 0:
            self.metodo_pago = 'TARJETA'
        elif self.monto_transferencia > 0:
            self.metodo_pago = 'TRANSFERENCIA'
        else:
            self.metodo_pago = 'EFECTIVO'
        super().save(*args, **kwargs)


class ValeLiquidacion(models.Model):
    """
    Vale Digital de Adeudo: Cuando el paciente paga en recepción,
    se genera un vale que indica que recepción le debe ese dinero al médico.
    Al final del día, el reporte muestra: "Recepción debe entregarle $X al médico".
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de entrega'),
        ('LIQUIDADO', 'Liquidado (entregado al médico)'),
        ('PARCIAL', 'Parcialmente liquidado'),
        ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="vales_liquidacion"
    )
    cobro = models.OneToOneField(
        CobroConsulta, on_delete=models.CASCADE,
        related_name="vale_liquidacion",
        verbose_name="Cobro asociado"
    )
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="vales_pendientes",
        verbose_name="Médico acreedor"
    )

    # Montos
    monto_adeudado = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Monto que recepción debe entregar"
    )
    monto_liquidado = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Monto ya entregado"
    )

    # Estado
    estado = models.CharField(
        max_length=15, choices=ESTADO_CHOICES, default='PENDIENTE'
    )

    # Quién procesó la liquidación
    liquidado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="liquidaciones_procesadas"
    )
    fecha_liquidacion = models.DateTimeField(null=True, blank=True)

    # Comprobante
    folio_vale = models.CharField(
        max_length=50, unique=True,
        verbose_name="Folio del vale"
    )
    notas = models.TextField(blank=True)

    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vale de Liquidación"
        verbose_name_plural = "Vales de Liquidación"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Vale {self.folio_vale} - ${self.monto_adeudado} ({self.get_estado_display()})"

    @property
    def saldo_pendiente(self):
        return self.monto_adeudado - self.monto_liquidado

    def save(self, *args, **kwargs):
        if not self.folio_vale:
            from django.utils import timezone as _tz
            año = _tz.localtime(_tz.now()).year
            ultimos = ValeLiquidacion.objects.filter(
                folio_vale__startswith=f'VALE-{año}-'
            ).count()
            self.folio_vale = f'VALE-{año}-{str(ultimos + 1).zfill(5)}'
        super().save(*args, **kwargs)
