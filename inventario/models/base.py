"""
INVENTARIO V8.0 — Modelos base y choices compartidos
"""
from django.db import models
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CHOICES COMPARTIDAS (evitan duplicación entre silos)
# =============================================================================

UNIDAD_CHOICES = [
    # Volumen analítico
    ('ML',    'Mililitros (mL)'),
    ('UL',    'Microlitros (µL)'),
    ('L',     'Litros (L)'),
    # Masa
    ('G',     'Gramos (g)'),
    ('MG',    'Miligramos (mg)'),
    # Unidades discretas
    ('UNIDAD', 'Unidad (pza)'),
    ('KIT',    'Kit completo'),
    ('CAJA',   'Caja'),
    ('PAQUETE','Paquete'),
    ('ROLLO',  'Rollo'),
    ('PAR',    'Par'),
    ('SOBRE',  'Sobre'),
    ('TIRA',   'Tira / Strip'),
    # Especiales
    ('LITRO_L','Litro (L)'),
    ('OTRO',   'Otra unidad'),
]

AREA_CHOICES = [
    ('LABORATORIO',    'Laboratorio'),
    ('CONSULTORIO',    'Consultorio'),
    ('FARMACIA',       'Farmacia'),
    ('RECEPCION',      'Recepción'),
    ('ADMINISTRACION', 'Administración'),
    ('INTENDENCIA',    'Intendencia / Limpieza'),
    ('GENERAL',        'General / Toda la instalación'),
]


# =============================================================================
# PARTE 0: PROVEEDOR COMPARTIDO (3 silos nuevos)
# =============================================================================

class ProveedorCompras(models.Model):
    """
    Catálogo de proveedores para los silos de Laboratorio, Consultorio e
    Insumos Generales.

    Aislado del modelo farmacia.Proveedor (que cumple regulación COFEPRIS).
    Este modelo cumple los requisitos de trazabilidad de la ISO 15189 para
    proveedores de reactivos y materiales analíticos.
    """
    TIPO_CHOICES = [
        ('REACTIVOS',         'Distribuidor de Reactivos / IVD'),
        ('MATERIAL_MEDICO',   'Distribuidor de Material Médico'),
        ('PAPELERIA',         'Proveedor de Papelería / Oficina'),
        ('LIMPIEZA',          'Proveedor de Limpieza / Higiene'),
        ('INFORMATICA',       'Proveedor de Informática / Tecnología'),
        ('INFRAESTRUCTURA',   'Proveedor de Infraestructura'),
        ('OTRO',              'Otro'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="proveedores_compras",
        verbose_name="Empresa",
    )
    razon_social = models.CharField(max_length=255, verbose_name="Razón Social")
    nombre_comercial = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Nombre Comercial"
    )
    rfc = models.CharField(max_length=13, verbose_name="RFC")
    tipo = models.CharField(
        max_length=20, choices=TIPO_CHOICES, default="OTRO",
        verbose_name="Tipo de Proveedor",
    )
    telefono   = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email      = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    contacto_nombre = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Nombre del Contacto"
    )
    dias_credito = models.IntegerField(
        default=0, verbose_name="Días de Crédito",
        help_text="0 = Contado. 30 = 30 días, etc."
    )
    activo     = models.BooleanField(default=True, verbose_name="Proveedor Activo")
    notas      = models.TextField(blank=True, null=True, verbose_name="Notas Internas")
    fecha_alta = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Alta")

    class Meta:
        verbose_name = "Proveedor (Inventario)"
        verbose_name_plural = "Proveedores (Inventario)"
        ordering = ["razon_social"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "rfc"],
                name="inventario_proveedor_empresa_rfc_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "activo"]),
        ]

    def __str__(self):
        return f"{self.razon_social} ({self.rfc})"
