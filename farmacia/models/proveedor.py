import re
from django.db import models
from django.core.exceptions import ValidationError
from core.models import Empresa

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
