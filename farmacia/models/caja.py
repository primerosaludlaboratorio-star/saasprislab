from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from core.models import Empresa, Sucursal, Usuario

class CierreTurnoFarmacia(models.Model):
    """
    Cierre de turno y corte de caja para farmacia.
    """
    folio = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Folio de Cierre",
        help_text="Generado automáticamente. Ej: CIERRE-2026-00001"
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
    usuario_responsable = models.ForeignKey(
        Usuario, 
        on_delete=models.PROTECT,
        related_name='cierres_farmacia',
        verbose_name="Usuario que Cierra (Nancy)"
    )
    apertura_caja = models.OneToOneField(
        'farmacia.AperturaCaja',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cierre_asociado',
        verbose_name="Apertura de Caja Asociada",
        help_text="Vincula con la apertura para incluir fondo inicial"
    )
    
    fecha_apertura = models.DateTimeField(
        verbose_name="Fecha/Hora de Apertura del Turno"
    )
    fecha_cierre = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha/Hora de Cierre"
    )
    
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
        if self.fecha_apertura and self.fecha_cierre:
            if self.fecha_apertura >= self.fecha_cierre:
                raise ValidationError("La fecha de apertura debe ser anterior a la de cierre.")
        
        if self.apertura_caja and not self.apertura_caja.activa:
            raise ValidationError(
                "No se puede cerrar una caja que no está activa o ya fue cerrada. "
                f"Apertura {self.apertura_caja.folio} ya está cerrada."
            )
    
    def save(self, *args, **kwargs):
        if not self.folio:
            from django.utils import timezone as _tz
            año = _tz.localtime(_tz.now()).year
            ultimo = CierreTurnoFarmacia.objects.filter(
                folio__startswith=f'CIERRE-{año}'
            ).count()
            self.folio = f'CIERRE-{año}-{(ultimo + 1):06d}'
        
        efectivo_teorico_ajustado = self.efectivo_teorico
        if self.apertura_caja:
            efectivo_teorico_ajustado = self.apertura_caja.fondo_efectivo + self.efectivo_teorico
        
        self.diferencia_efectivo = self.efectivo_declarado - efectivo_teorico_ajustado
        self.diferencia_tarjeta = self.tarjeta_declarado - self.tarjeta_teorico
        self.diferencia_vales = self.vales_declarado - self.vales_teorico
        self.diferencia_total = (
            self.diferencia_efectivo + 
            self.diferencia_tarjeta + 
            self.diferencia_vales
        )
        
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
        
        if self.apertura_caja and self.apertura_caja.activa:
            self.apertura_caja.cerrar_caja()
            self.apertura_caja.cerrada_con = self
            self.apertura_caja.save(update_fields=['cerrada_con'])
    
    @property
    def total_declarado(self):
        return self.efectivo_declarado + self.tarjeta_declarado + self.vales_declarado
    
    @property
    def total_teorico(self):
        return self.efectivo_teorico + self.tarjeta_teorico + self.vales_teorico
    
    @property
    def estado_diferencia(self):
        if self.diferencia_total < 0:
            return f'FALTANTE (${abs(self.diferencia_total):.2f})'
        elif self.diferencia_total > 0:
            return f'SOBRANTE (${self.diferencia_total:.2f})'
        else:
            return 'EXACTO'
    
    def __str__(self):
        return f"{self.folio} | {self.usuario_responsable.get_full_name()} | {self.estado_diferencia}"


class AperturaCaja(models.Model):
    """
    Registro de apertura de caja al inicio del turno.
    """
    folio = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Folio de Apertura",
        help_text="Generado automáticamente. Ej: APERT-2026-00001"
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
    usuario_responsable = models.ForeignKey(
        Usuario, 
        on_delete=models.PROTECT,
        related_name='aperturas_caja',
        verbose_name="Usuario que Abre (Nancy)"
    )
    
    fecha_apertura = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha/Hora de Apertura"
    )
    
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
    
    activa = models.BooleanField(
        default=True,
        verbose_name="Caja Abierta",
        help_text="True mientras el turno está activo"
    )
    cerrada_con = models.OneToOneField(
        'farmacia.CierreTurnoFarmacia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='apertura',
        verbose_name="Cerrada Con"
    )
    
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
        if not self.folio:
            from django.utils import timezone as _tz
            año = _tz.localtime(_tz.now()).year
            ultimo = AperturaCaja.objects.filter(
                folio__startswith=f'APERT-{año}'
            ).count()
            self.folio = f'APERT-{año}-{(ultimo + 1):06d}'
        
        super().save(*args, **kwargs)
    
    def cerrar_caja(self):
        self.activa = False
        self.save(update_fields=['activa'])
    
    def __str__(self):
        estado = 'ABIERTA' if self.activa else 'CERRADA'
        return f"{self.folio} | {self.usuario_responsable.get_full_name()} | {estado}"
