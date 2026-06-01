"""
core/models/catalogos.py
Catálogo maestro: Productos, Lotes, Médicos, Estudios, Parámetros, Convenios.
Depende de: base.py
"""
from django.db import models
from datetime import date

from core.tenant import TenantModel
from core.validators import validate_image_upload
from .base import AuditoriaModel, Empresa, Sucursal, Usuario, get_google_drive_storage


# ==============================================================================
# 2. CATÁLOGO MAESTRO: FICHA TÉCNICA DETALLADA (Rigor Nancy)
# ==============================================================================
class Producto(TenantModel):
    FRACCION_CHOICES = [
        ('I', 'Fracción I (Estupefacientes)'),
        ('II', 'Fracción II (Psicotrópicos)'),
        ('III', 'Fracción III (Psicotrópicos)'),
        ('IV', 'Fracción IV (Antibióticos)'),
        ('V', 'Fracción V (Venta en Farmacias)'),
        ('VI', 'Fracción VI (Venta Libre)'),
    ]

    CATEGORIAS = [
        ('ANTIBIOTICO', 'Antibiótico'),
        ('PATENTE', 'Patente / Marca'),
        ('GENERICO', 'Genérico'),
        ('CURACION', 'Material de Curación'),
        ('OTRO', 'Otros / Suplementos'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='productos')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sucursal")

    marca_laboratorio = models.CharField(max_length=150, default='GENÉRICO', verbose_name="Marca / Laboratorio Fabricante")
    linea = models.CharField(max_length=100, blank=True, null=True, verbose_name="Línea de Producto")
    sublinea = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sublínea")

    nombre = models.CharField(max_length=255, verbose_name="Nombre Comercial", db_index=True)
    sustancia_activa = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre Genérico / Sustancia")
    codigo_barras = models.CharField(max_length=100, unique=True, verbose_name="Código de Barras / VIN")

    forma_farmaceutica = models.CharField(max_length=100, verbose_name="Forma (Tabletas, Jarabe, etc.)")
    concentracion = models.CharField(max_length=100, verbose_name="Concentración (ej. 500mg, 1g)")
    presentacion = models.CharField(max_length=100, verbose_name="Presentación (unidades por empaque)")
    clasificacion_sanitaria = models.CharField(max_length=5, choices=FRACCION_CHOICES, default='VI', verbose_name="Clasificación Ley de Salud")

    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='GENERICO', verbose_name="Categoría de Producto")
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio de Compra (Costo)")
    precio_publico = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio Base (Sin Impuestos)")
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="% IVA Aplicable (0 o 16)")
    stock = models.IntegerField(default=0, verbose_name="Existencia Total")
    stock_minimo = models.IntegerField(default=5, verbose_name="Stock Mínimo (Alerta)",
                                       help_text="Se genera alerta cuando el stock baje de este nivel")

    es_antibiotico = models.BooleanField(default=False, verbose_name="Requiere Receta (Antibiótico)")
    es_servicio = models.BooleanField(default=False, verbose_name="Es un Servicio Médico / Consulta")

    # ── SPRINT 2.1: Control sanitario ampliado ──────────────────────────────
    requiere_receta = models.BooleanField(
        default=False,
        verbose_name="Requiere Receta Médica",
        db_index=True,
        help_text=(
            "Activa validación obligatoria para Fracciones I, II, III (controlados) y "
            "cualquier medicamento que requiera prescripción. "
            "Cubre casos más allá de es_antibiotico."
        ),
    )

    # ── SPRINT 2.2: Motor de fraccionamiento ────────────────────────────────
    unidad_compra = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name="Unidad de Compra",
        help_text="Ej: Caja, Frasco, Ampolleta",
    )
    unidad_venta = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name="Unidad de Venta al Menudeo",
        help_text="Ej: Tableta, mL, Blíster",
    )
    factor_conversion = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name="Factor de Conversión",
        help_text="Cuántas unidades de venta contiene 1 unidad de compra. Ej: 30 tabletas/caja",
    )
    precio_venta_fraccion = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name="Precio de Venta por Fracción",
        help_text=(
            "Precio unitario al menudeo (tableta, mL). "
            "Si es None se calcula como precio_publico / factor_conversion."
        ),
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Producto / Servicio"
        verbose_name_plural = "Productos y Servicios"

    def precio_por_fraccion_efectivo(self):
        """
        Retorna el precio real de venta al menudeo.
        Prioridad: precio_venta_fraccion explícito → precio_publico / factor_conversion → precio_publico.
        """
        from decimal import Decimal as _D
        if self.precio_venta_fraccion:
            return self.precio_venta_fraccion
        if self.factor_conversion and self.factor_conversion > 0 and self.precio_publico:
            return (_D(str(self.precio_publico)) / _D(str(self.factor_conversion))).quantize(_D('0.0001'))
        return self.precio_publico

    def necesita_receta(self):
        """True si el producto requiere prescripción médica por cualquier razón."""
        return self.requiere_receta or self.es_antibiotico

    def __str__(self):
        return f"{self.nombre} - {self.sustancia_activa} ({self.concentracion})"


# ==============================================================================
# 3. TRAZABILIDAD DE ACTIVOS: LOTES Y PEPS
# ==============================================================================
class Lote(TenantModel):
    """
    Trazabilidad por lote. El tenant se denormaliza en `empresa` (misma que producto.empresa)
    para consultas indexadas y blindaje frente a inconsistencias de FK.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="lotes_inventario",
        verbose_name="Empresa (tenant)",
    )
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='lotes')
    numero_lote = models.CharField(max_length=100, verbose_name="Número de Serie / Lote")
    fecha_fabricacion = models.DateField(null=True, blank=True, verbose_name="Fecha de Fabricación")
    fecha_caducidad = models.DateField(verbose_name="Fecha de Caducidad", db_index=True)
    ubicacion_fisica = models.CharField(max_length=150, blank=True, null=True, verbose_name="Ubicación Física (Estante/Pasillo)")

    cantidad = models.IntegerField(verbose_name="Cantidad Disponible en este Lote")
    costo_adquisicion = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo de Adquisición Unitario")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        ordering = ['fecha_caducidad']
        verbose_name = "Lote / Caducidad"
        verbose_name_plural = "Lotes de Inventario"
        indexes = [
            models.Index(fields=['empresa', 'fecha_caducidad'], name='core_lote_empresa_cad_idx'),
            models.Index(fields=['producto', 'fecha_caducidad'], name='core_lote_prod_caducidad_idx'),
            models.Index(fields=['producto', 'cantidad'], name='core_lote_prod_cantidad_idx'),
        ]

    def clean(self):
        """Validación QC: BLOQUEAR ingreso de lotes ya caducados."""
        from django.core.exceptions import ValidationError

        if self.fecha_caducidad and self.fecha_caducidad < date.today():
            raise ValidationError({
                'fecha_caducidad': f'No se puede ingresar un lote ya caducado. '
                                   f'Fecha de caducidad: {self.fecha_caducidad}. '
                                   f'Fecha actual: {date.today()}.'
            })

        if self.fecha_fabricacion and self.fecha_caducidad:
            if self.fecha_fabricacion >= self.fecha_caducidad:
                raise ValidationError({
                    'fecha_fabricacion': 'La fecha de fabricación debe ser anterior a la fecha de caducidad.'
                })

    def save(self, *args, **kwargs):
        if self.producto_id:
            self.empresa_id = (
                Producto.objects.filter(pk=self.producto_id).values_list("empresa_id", flat=True).first()
            )
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def dias_para_caducar(self):
        """Retorna los días restantes hasta la caducidad."""
        from datetime import date as _date
        if self.fecha_caducidad:
            delta = self.fecha_caducidad - _date.today()
            return delta.days
        return None

    @property
    def estado_caducidad(self):
        """Retorna el estado del lote según su proximidad a caducar."""
        dias = self.dias_para_caducar
        if dias is None:
            return 'DESCONOCIDO'
        if dias < 0:
            return 'CADUCADO'
        if dias < 30:
            return 'CRITICO'
        if dias < 90:
            return 'ALERTA'
        return 'NORMAL'

    def __str__(self):
        return f"Lote: {self.numero_lote} | Exp: {self.fecha_caducidad}"


# ==============================================================================
# 4. CONTROL NORMADO: MÉDICOS (COFEPRIS)
# ==============================================================================
class Medico(models.Model):
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, null=True, blank=True,
        related_name='medicos', verbose_name="Empresa"
    )
    nombre_completo = models.CharField(max_length=255, verbose_name="Nombre del Médico")
    cedula_profesional = models.CharField(max_length=50, unique=True, verbose_name="Cédula Profesional")
    especialidad = models.CharField(max_length=150, default="Médico General", verbose_name="Especialidad")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    # 🔒 Capa de Blindaje v2.0 — PIN de validación LAB (no almacenar en texto plano)
    lab_validation_pin_hash = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Hash del PIN-LAB",
        help_text="SHA256 del PIN de validación para firmar notas. NUNCA almacenar el PIN en texto plano."
    )
    pin_configurado_en = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="PIN Configurado En"
    )
    
    # Certificación de cédula para recetas
    cedula_validada = models.BooleanField(
        default=False,
        verbose_name="Cédula Profesional Validada",
        help_text="La cédula ha sido verificada ante COFEPRIS/instancia correspondiente"
    )
    fecha_validacion_cedula = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Validación de Cédula"
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Médico"
        verbose_name_plural = "Médicos"
        ordering = ['nombre_completo']

    def save(self, *args, **kwargs):
        if self.nombre_completo:
            import re
            self.nombre_completo = self.nombre_completo.strip()
            self.nombre_completo = re.sub(r'\s+', ' ', self.nombre_completo)
            self.nombre_completo = self.nombre_completo.title()
        if self.cedula_profesional:
            self.cedula_profesional = self.cedula_profesional.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Dr. {self.nombre_completo} ({self.cedula_profesional})"


# ==============================================================================
# 6. MÓDULO DE DESCUENTOS AUTOMATIZADOS
# ==============================================================================
class DiscountPolicy(models.Model):
    """Políticas de descuento configurables (Staff, Familia, INAPAM, etc.)."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='politicas_descuento')
    nombre = models.CharField(max_length=50, verbose_name="Nombre de la Política")
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Porcentaje de Descuento")
    requiere_autorizacion = models.BooleanField(default=True, verbose_name="¿Requiere Autorización del Gerente?")
    activa = models.BooleanField(default=True, verbose_name="Política Activa")

    class Meta:
        app_label = 'core'
        verbose_name = "Política de Descuento"
        verbose_name_plural = "Políticas de Descuento"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.porcentaje_descuento}%)"


# ==============================================================================
# 8. MÓDULO DE LABORATORIO CLÍNICO — catálogo unificado en app lims (v7.5).
# Modelos core Estudio / Parametro / RangoReferencia eliminados (ver migración 0052).
# ==============================================================================

# ==============================================================================
# BLOQUE: CONVENIOS CON EMPRESAS / ASEGURADORAS
# ==============================================================================
class Convenio(models.Model):
    """Convenio comercial con empresa o aseguradora."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='convenios')
    nombre = models.CharField(max_length=255, verbose_name='Nombre de la Empresa/Aseguradora')
    rfc = models.CharField(max_length=13, blank=True, null=True, verbose_name='RFC')
    contacto = models.CharField(max_length=255, blank=True, null=True, verbose_name='Persona de Contacto')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    TIPO_CHOICES = [
        ('EMPRESA', 'Empresa Privada'),
        ('ASEGURADORA', 'Aseguradora'),
        ('GOBIERNO', 'Gobierno / Dependencia'),
        ('ONG', 'ONG / Fundacion'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='EMPRESA')

    dias_credito = models.IntegerField(default=15, verbose_name='Dias de Credito', help_text='Plazo en dias para el pago (15, 30, 45, etc.)')
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Descuento General %')
    limite_credito = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Limite de Credito ($)')
    activo = models.BooleanField(default=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    notas = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Convenio'
        verbose_name_plural = 'Convenios'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.get_tipo_display()}) - {self.dias_credito} dias'


class ConvenioPrecioLims(models.Model):
    """Precio convenio sobre item del catalogo LIMS v7.5 (uno de analito / perfil / paquete)."""
    convenio = models.ForeignKey(Convenio, on_delete=models.CASCADE, related_name='precios_lims')
    analito = models.ForeignKey(
        'lims.Analito', on_delete=models.CASCADE, null=True, blank=True,
        related_name='precios_convenio',
    )
    perfil_lims = models.ForeignKey(
        'lims.PerfilLims', on_delete=models.CASCADE, null=True, blank=True,
        related_name='precios_convenio',
    )
    paquete_lims = models.ForeignKey(
        'lims.PaqueteLims', on_delete=models.CASCADE, null=True, blank=True,
        related_name='precios_convenio',
    )
    precio_convenio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio Convenio')

    class Meta:
        app_label = 'core'
        verbose_name = 'Precio LIMS por Convenio'
        verbose_name_plural = 'Precios LIMS por Convenio'

    def __str__(self):
        item = self.analito or self.perfil_lims or self.paquete_lims
        return f'{self.convenio.nombre} - {item}: ${self.precio_convenio}'
