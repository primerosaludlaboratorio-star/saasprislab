"""
MÓDULO DE LABORATORIO - Equipos, maquila, mantenimiento y precursores celulares.
"""
from django.db import models


class Equipo(models.Model):
    """
    Equipo de laboratorio con capacidad de interfaz HL7/ASTM.
    Preparado para integración futura con equipos físicos.
    """
    PROTOCOLO_ASTM = 'ASTM'
    PROTOCOLO_HL7 = 'HL7'
    PROTOCOLO_SERIAL = 'SERIAL'
    PROTOCOLO_CHOICES = [
        (PROTOCOLO_ASTM, 'ASTM'),
        (PROTOCOLO_HL7, 'HL7'),
        (PROTOCOLO_SERIAL, 'Serial/RS232'),
    ]

    nombre = models.CharField(
        max_length=200,
        help_text='Nombre del equipo (ej: "Mindray BC-6000").',
    )
    marca = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Marca del equipo (ej: "Mindray", "Roche", "Abbott").',
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text='Dirección IP del equipo para conexión TCP/IP (opcional).',
    )
    puerto = models.IntegerField(
        blank=True,
        null=True,
        help_text='Puerto TCP/IP para conexión (opcional).',
    )
    protocolo = models.CharField(
        max_length=20,
        choices=PROTOCOLO_CHOICES,
        default=PROTOCOLO_ASTM,
        help_text='Protocolo de comunicación del equipo.',
    )
    activo = models.BooleanField(
        default=True,
        help_text='Indica si el equipo está activo y disponible para uso.',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento_calibracion = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha límite de validez metrológica/calibración. Si vence, el receptor HL7 puede bloquear integración.',
    )
    notas = models.TextField(
        blank=True,
        null=True,
        help_text='Notas adicionales sobre configuración o uso del equipo.',
    )

    class Meta:
        verbose_name = 'Equipo de Laboratorio'
        verbose_name_plural = 'Equipos de Laboratorio'
        ordering = ['marca', 'nombre']

    def __str__(self) -> str:
        marca_str = f'{self.marca} - ' if self.marca else ''
        return f'{marca_str}{self.nombre}'


class CodigoParametroEquipo(models.Model):
    """
    Mapeo entre el código de un parámetro en el equipo (ej: 'WBC')
    y el Parametro del sistema PRISLAB.
    Requerido para integración HL7/ASTM automática.
    """
    equipo = models.ForeignKey(
        Equipo, on_delete=models.CASCADE, related_name='mapeos_codigos',
        verbose_name='Equipo',
    )
    codigo_equipo = models.CharField(
        max_length=50,
        help_text='Código interno del equipo (ej: WBC, HGB, GLU).',
    )
    parametro = models.ForeignKey(
        'laboratorio.Parametro', on_delete=models.CASCADE, related_name='mapeos_equipo',
        verbose_name='Parámetro PRISLAB',
    )
    factor_conversion = models.DecimalField(
        max_digits=12, decimal_places=6, default=1.0,
        help_text='Factor de conversión de unidades (ej: 1.0 si las unidades coinciden).',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Mapeo Código Equipo'
        verbose_name_plural = 'Mapeos Códigos Equipos'
        unique_together = ('equipo', 'codigo_equipo')
        ordering = ['equipo__nombre', 'codigo_equipo']

    def __str__(self):
        return f'{self.equipo.nombre}: {self.codigo_equipo} → {self.parametro.nombre}'


class EnvioMaquila(models.Model):
    """Envío a laboratorio externo (maquila) con guía de rastreo (placeholder)."""
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="maquila_laboratorio")
    laboratorio_externo = models.CharField(max_length=255)
    guia_rastreo = models.CharField(max_length=120, blank=True, null=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Envío Maquila"
        verbose_name_plural = "Envíos Maquila"
        ordering = ["-fecha_envio"]


class BitacoraMantenimiento(models.Model):
    """Bitácora de mantenimiento de equipos (placeholder)."""
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="mantenimiento_laboratorio")
    equipo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bitácora de Mantenimiento"
        verbose_name_plural = "Bitácoras de Mantenimiento"
        ordering = ["-fecha_registro"]


class PrecursorCellular(models.Model):
    """Precursores celulares (Bandas, Mielocitos, Metamielocitos, Blastos)."""
    estudio = models.ForeignKey(
        'laboratorio.Estudio',
        on_delete=models.CASCADE,
        related_name='precursores_celulares',
        verbose_name="Estudio"
    )
    
    # Precursores Celulares
    bandas = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Bandas (%)")
    mielocitos = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Mielocitos (%)")
    metamielocitos = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Metamielocitos (%)")
    blastos = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Blastos (%)")
    
    # Valores de Referencia (normalmente 0% para precursores)
    valor_maximo_normal = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Valor Máximo Normal (%)",
        help_text="Normalmente 0% para precursores celulares"
    )

    class Meta:
        verbose_name = 'Precursor Celular'
        verbose_name_plural = 'Precursores Celulares'
        ordering = ['estudio__nombre']

    def __str__(self) -> str:
        return f'Precursores Celulares - {self.estudio.nombre}'
