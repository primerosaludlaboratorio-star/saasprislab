"""
MÓDULO DE LABORATORIO - Estudios clínicos y valores de referencia.
"""
from django.db import models

from .catalogo import CategoriaExamen
from .hardware import Equipo


class Estudio(models.Model):
    """
    Estudio de laboratorio (p. ej. Glucosa, Urea).
    Incluye rangos de referencia generales y unidades.
    """
    categoria = models.ForeignKey(
        CategoriaExamen,
        on_delete=models.PROTECT,
        related_name='estudios',
    )
    nombre = models.CharField(max_length=150)
    codigo = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Código interno o de aseguradora (opcional).',
    )
    precio_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Precio de lista del estudio al día de hoy.',
    )

    # Rangos de referencia generales
    valor_minimo = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor mínimo de referencia (general).',
    )
    valor_maximo = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor máximo de referencia (general).',
    )
    # Rangos de Pánico (V 5.0 - Valores Críticos)
    rango_panico_min = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor mínimo de pánico (crítico). Si el resultado está por debajo, requiere doble validación.',
    )
    rango_panico_max = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor máximo de pánico (crítico). Si el resultado está por encima, requiere doble validación.',
    )
    unidades = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Unidades de medición (ej. 'mg/dL', 'mmol/L').",
    )

    # Campos adicionales para compatibilidad con CSV de tarifas
    dias_entrega = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Tiempo de proceso (ej: "2 días", "24 horas").',
    )
    indicaciones = models.TextField(
        blank=True,
        null=True,
        help_text='Indicaciones especiales para el estudio.',
    )
    instrucciones_paciente = models.TextField(
        blank=True,
        null=True,
        help_text='Instrucciones de preparación para el paciente (ej: "Ayuno de 8 horas", "Recoger primera orina").',
    )
    muestra_requerida = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Tipo de muestra requerida (ej: "Sangre", "Orina").',
    )
    descripcion_interna = models.TextField(
        blank=True,
        null=True,
        help_text='Descripción interna o estudios incluidos (para paquetes).',
    )
    es_perfil = models.BooleanField(
        default=False,
        help_text='Indica si es un perfil/paquete (True) o estudio individual (False).',
    )
    equipo_default = models.ForeignKey(
        Equipo,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='estudios',
        help_text='Equipo de laboratorio por defecto para este estudio (para envío automático a Worklist).',
    )
    
    # BLOQUE 8: Campo de búsqueda optimizada
    keywords = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Palabras Clave de Búsqueda",
        help_text="Sinónimos y términos alternativos para búsqueda rápida (ej: 'glucosa,azucar,glicemia,blood sugar'). Separados por comas.",
        db_index=True
    )

    # BLOQUE 9: Metadatos clínicos del catálogo original (importados desde LIMS)
    SEXO_CHOICES = [('Ambos', 'Ambos'), ('Masculino', 'Masculino'), ('Femenino', 'Femenino')]
    abreviatura = models.CharField(
        max_length=30, blank=True, null=True,
        help_text='Abreviatura del estudio usada en etiquetas ZPL y HL7 (ej: CH, BH, GLU).',
        db_index=True,
    )
    metodo = models.CharField(
        max_length=255, blank=True, null=True,
        help_text='Método analítico (ej: Citometría de flujo, Colorimétrico Automatizado).',
    )
    titulo_reporte = models.CharField(
        max_length=200, blank=True, null=True,
        help_text='Título a mostrar en el reporte PDF (puede diferir del nombre clínico).',
    )
    titulo_color = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='Color HEX del título en el reporte PDF (ej: #cc1212).',
    )
    titulo_alineacion = models.CharField(
        max_length=30, blank=True, null=True,
        help_text='Alineación del título en el reporte (Izquierda, Centro, Derecha).',
    )
    sexo_aplicable = models.CharField(
        max_length=20, choices=SEXO_CHOICES, default='Ambos',
        help_text='Sexo al que aplica este estudio.',
    )
    permite_venta_directa = models.BooleanField(
        default=True,
        help_text='Si True, puede venderse como prueba individual desde recepción/PDV.',
    )
    activo = models.BooleanField(
        default=True,
        help_text='Si False, el estudio existe pero no aparece en catálogo de venta.',
    )
    notas_internas = models.TextField(
        blank=True, null=True,
        help_text='Notas visibles solo para el personal (no se imprimen al paciente).',
    )
    tiempo_proceso = models.CharField(
        max_length=50, blank=True, null=True,
        help_text='Tiempo de procesamiento (ej: "2 horas", "24 horas").',
    )

    class Meta:
        verbose_name = 'Estudio'
        verbose_name_plural = 'Estudios'
        ordering = ['categoria__nombre', 'nombre']
        unique_together = ('categoria', 'nombre')
        indexes = [
            models.Index(fields=['codigo'], name='lab_estudio_codigo_idx'),
            models.Index(fields=['activo', 'categoria'], name='lab_estudio_activo_cat_idx'),
            models.Index(fields=['nombre'], name='lab_estudio_nombre_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.nombre} ({self.categoria.nombre})'


# ==============================================================================
# BLOQUE 1: VALORES DE REFERENCIA DINÁMICOS (POR SEXO Y EDAD)
# ==============================================================================

class ValorReferencia(models.Model):
    """Valores de referencia dinámicos por sexo y edad para estudios de laboratorio."""
    SEXO_MASCULINO = 'M'
    SEXO_FEMENINO = 'F'
    SEXO_CHOICES = [
        (SEXO_MASCULINO, 'Masculino'),
        (SEXO_FEMENINO, 'Femenino'),
    ]
    
    EDAD_NEONATO = 'NEONATO'
    EDAD_INFANTE = 'INFANTE'
    EDAD_ADULTO = 'ADULTO'
    EDAD_ADULTO_MAYOR = 'ADULTO_MAYOR'
    EDAD_CHOICES = [
        (EDAD_NEONATO, 'Neonato (0-30 días)'),
        (EDAD_INFANTE, 'Infante (1 mes - 18 años)'),
        (EDAD_ADULTO, 'Adulto (19-64 años)'),
        (EDAD_ADULTO_MAYOR, 'Adulto Mayor (65+ años)'),
    ]
    
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='valores_referencia',
        verbose_name="Estudio"
    )
    sexo = models.CharField(
        max_length=1,
        choices=SEXO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Sexo",
        help_text="Si está vacío, aplica a ambos sexos"
    )
    edad = models.CharField(
        max_length=20,
        choices=EDAD_CHOICES,
        blank=True,
        null=True,
        verbose_name="Rango de Edad",
        help_text="Si está vacío, aplica a todas las edades"
    )
    valor_minimo = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Valor Mínimo de Referencia"
    )
    valor_maximo = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Valor Máximo de Referencia"
    )
    unidades = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Unidades",
        help_text="Si está vacío, usa las unidades del estudio"
    )

    class Meta:
        verbose_name = 'Valor de Referencia'
        verbose_name_plural = 'Valores de Referencia'
        ordering = ['estudio__nombre', 'sexo', 'edad']
        unique_together = ('estudio', 'sexo', 'edad')

    def __str__(self) -> str:
        sexo_str = f" {self.get_sexo_display()}" if self.sexo else ""
        edad_str = f" - {self.get_edad_display()}" if self.edad else ""
        return f'{self.estudio.nombre}{sexo_str}{edad_str}: {self.valor_minimo}-{self.valor_maximo}'


# ==============================================================================
# BLOQUE 1: ESPECIFICACIONES DE HEMATOLOGÍA
# ==============================================================================

class IndiceEritrocitario(models.Model):
    """Índices eritrocitarios (VGM, HCM, CMHC, RDW) para estudios de hematología."""
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='indices_eritrocitarios',
        verbose_name="Estudio",
        help_text="Estudio de Hematología Completa"
    )
    
    # Índices Eritrocitarios
    vgm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="VGM (Volumen Globular Medio)",
        help_text="fl (femtolitros)"
    )
    hcm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="HCM (Hemoglobina Corpuscular Media)",
        help_text="pg (picogramos)"
    )
    cmhc = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="CMHC (Concentración Media de Hemoglobina Corpuscular)",
        help_text="g/dL"
    )
    rdw = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="RDW (Red Cell Distribution Width)",
        help_text="%"
    )
    
    # Valores de Referencia para Índices
    vgm_min = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="VGM Mínimo")
    vgm_max = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="VGM Máximo")
    hcm_min = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="HCM Mínimo")
    hcm_max = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="HCM Máximo")
    cmhc_min = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="CMHC Mínimo")
    cmhc_max = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="CMHC Máximo")
    rdw_min = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="RDW Mínimo")
    rdw_max = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="RDW Máximo")

    class Meta:
        verbose_name = 'Índice Eritrocitario'
        verbose_name_plural = 'Índices Eritrocitarios'
        ordering = ['estudio__nombre']

    def __str__(self) -> str:
        return f'Índices Eritrocitarios - {self.estudio.nombre}'


class DiferencialLeucocitario(models.Model):
    """Diferencial leucocitaria en porcentaje y valor absoluto."""
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='diferencial_leucocitario',
        verbose_name="Estudio",
        help_text="Estudio de Hematología Completa"
    )
    
    # Diferencial en Porcentaje (%)
    neutrofilos_pct = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Neutrófilos %")
    linfocitos_pct = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Linfocitos %")
    monocitos_pct = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Monocitos %")
    eosinofilos_pct = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Eosinófilos %")
    basofilos_pct = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Basófilos %")
    
    # Diferencial en Valor Absoluto (10³/μL)
    neutrofilos_abs = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Neutrófilos Absoluto (10³/μL)")
    linfocitos_abs = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Linfocitos Absoluto (10³/μL)")
    monocitos_abs = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Monocitos Absoluto (10³/μL)")
    eosinofilos_abs = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Eosinófilos Absoluto (10³/μL)")
    basofilos_abs = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Basófilos Absoluto (10³/μL)")
    
    # Valores de Referencia
    neutrofilos_pct_min = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    neutrofilos_pct_max = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    linfocitos_pct_min = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    linfocitos_pct_max = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Diferencial Leucocitario'
        verbose_name_plural = 'Diferenciales Leucocitarios'
        ordering = ['estudio__nombre']

    def __str__(self) -> str:
        return f'Diferencial Leucocitario - {self.estudio.nombre}'


# ==============================================================================
# FASE 6 — ISO 15189: RANGOS DE REFERENCIA DINÁMICOS
# ==============================================================================

class RangoReferenciaParametro(models.Model):
    """
    Rango de referencia dinámico por parámetro, segmentado por sexo y edad.
    Cumple ISO 15189:2022 §7.3.7 (intervalos de referencia verificados).
    Fuentes válidas: CLSI EP28-A3c, Harrison's, valores propios verificados.
    """
    SEXO_CHOICES = [('M', 'Masculino'), ('F', 'Femenino'), ('A', 'Ambos')]
    FUENTE_CHOICES = [
        ('CLSI', 'CLSI EP28-A3c'),
        ('HARRISON', "Harrison's Principles"),
        ('OPS', 'OPS/OMS Valores de Referencia'),
        ('PRISLAB', 'Verificado por PRISLAB'),
        ('OTRO', 'Otra fuente bibliográfica'),
    ]

    parametro = models.ForeignKey(
        'laboratorio.Parametro', on_delete=models.CASCADE,
        related_name='rangos_referencia_dinamicos',
        verbose_name='Parámetro'
    )
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, default='A')
    edad_min_anios = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Edad mínima (años). 0 = recién nacido.'
    )
    edad_max_anios = models.DecimalField(
        max_digits=5, decimal_places=2, default=999,
        help_text='Edad máxima (años). 999 = sin límite.'
    )
    valor_minimo = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        help_text='Límite inferior del rango normal.'
    )
    valor_maximo = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        help_text='Límite superior del rango normal.'
    )
    valor_critico_bajo = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        help_text='Valor crítico inferior. Activa alerta de pánico a PRIS y QC.'
    )
    valor_critico_alto = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        help_text='Valor crítico superior. Activa alerta de pánico a PRIS y QC.'
    )
    unidad = models.CharField(max_length=30, blank=True, default='')
    fuente = models.CharField(max_length=20, choices=FUENTE_CHOICES, default='PRISLAB')
    referencia_bibliografica = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)
    fecha_verificacion = models.DateField(null=True, blank=True)

    class Meta:
        app_label = 'laboratorio'
        verbose_name = 'Rango de Referencia Dinámico'
        verbose_name_plural = 'Rangos de Referencia Dinámicos'
        ordering = ['parametro', 'sexo', 'edad_min_anios']
        unique_together = [['parametro', 'sexo', 'edad_min_anios', 'edad_max_anios']]
        indexes = [
            models.Index(fields=['parametro', 'activo'], name='lab_rango_param_activo_idx'),
            models.Index(
                fields=['parametro', 'activo', 'edad_min_anios', 'edad_max_anios'],
                name='lab_rango_lookup_idx',
            ),
        ]

    def __str__(self):
        return (f'{self.parametro.nombre} | {self.get_sexo_display()} | '
                f'{self.edad_min_anios}-{self.edad_max_anios} años')
