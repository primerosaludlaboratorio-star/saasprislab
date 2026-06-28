from django.db import models
from django.core.exceptions import ValidationError
from core.models import Empresa, Sucursal, Usuario, Producto, Lote, Venta

class RegistroAntibiotico(models.Model):
    """
    Libro de control obligatorio para venta de antibióticos (Fracción IV).
    """
    folio = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Folio de Registro",
        help_text="Generado automáticamente. Ej: ATB-2026-00001"
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
    
    medico_cedula = models.CharField(
        max_length=50,
        verbose_name="Cédula Profesional del Médico",
        help_text="OBLIGATORIO para antibióticos"
    )
    medico_nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre del Médico Prescriptor"
    )
    
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
        if not self.medico_cedula or not self.medico_nombre:
            raise ValidationError(
                "Para venta de antibióticos es OBLIGATORIO registrar Cédula y Nombre del Médico Prescriptor (NOM-072)."
            )
        
        if not self.paciente and not self.paciente_nombre:
            raise ValidationError(
                "Se requiere nombre del paciente para registro COFEPRIS."
            )
    
    def save(self, *args, **kwargs):
        if not self.folio:
            from django.utils import timezone as _tz
            año = _tz.localtime(_tz.now()).year
            ultimo = RegistroAntibiotico.objects.filter(
                folio__startswith=f'ATB-{año}'
            ).count()
            self.folio = f'ATB-{año}-{(ultimo + 1):06d}'
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.folio} | {self.producto.nombre} | {self.paciente_nombre} | Dr. {self.medico_nombre}"
