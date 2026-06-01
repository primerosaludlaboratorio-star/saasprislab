"""
MÓDULO DE LABORATORIO - Sistema de Recepción, Procesamiento y Reportes.
PILAR 2: INMUTABILIDAD CLÍNICA (ISO 15189)
Incluye: Historial de Resultados para trazabilidad forense.
"""
from django.conf import settings
from django.db import models
import hashlib
import json

from core.validators import validate_image_upload


class CategoriaExamen(models.Model):
    """
    Agrupa estudios de laboratorio (p. ej. Química Clínica, Hematología).
    """
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Categoría de Examen'
        verbose_name_plural = 'Categorías de Examen'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre


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
        'Parametro', on_delete=models.CASCADE, related_name='mapeos_equipo',
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
        'Equipo',
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
# CEREBRO DE INVENTARIO: INSUMOS POR ESTUDIO (R107)
# ==============================================================================

class InsumoEstudio(models.Model):
    """
    Vincula un estudio de laboratorio con los insumos/materiales que consume.
    Al finalizar un estudio, el sistema descuenta automáticamente estos insumos.

    Ejemplo: Estudio "Glucosa" consume:
      - 1 Tubo rojo (Producto #42)
      - 1 Aguja vacutainer (Producto #15)
      - 0.5 mL Reactivo glucosa (Producto #88)
    """
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='insumos_requeridos',
        verbose_name='Estudio',
    )
    producto = models.ForeignKey(
        'core.Producto',
        on_delete=models.PROTECT,
        related_name='uso_en_estudios',
        verbose_name='Insumo / Reactivo',
        help_text='Producto del inventario que se consume al realizar este estudio.',
    )
    cantidad = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=1,
        verbose_name='Cantidad por estudio',
        help_text='Unidades consumidas por cada vez que se realiza este estudio.',
    )
    es_critico = models.BooleanField(
        default=False,
        verbose_name='Insumo Crítico',
        help_text='Si es True, el sistema alerta cuando este insumo está por agotarse.',
    )

    class Meta:
        verbose_name = 'Insumo de Estudio'
        verbose_name_plural = 'Insumos de Estudios'
        unique_together = ('estudio', 'producto')
        ordering = ['estudio__nombre', 'producto__nombre']

    def __str__(self):
        return f'{self.estudio.nombre} → {self.producto.nombre} x{self.cantidad}'


# ==============================================================================
# PERFILES DE LABORATORIO
# ==============================================================================

class PerfilLaboratorio(models.Model):
    """
    Perfil de laboratorio que agrupa múltiples estudios individuales.
    Permite ofrecer paquetes a precio especial independiente de la suma de estudios.
    """
    nombre = models.CharField(
        max_length=200,
        verbose_name="Nombre del Perfil",
        help_text="Ej: 'Química Básica', 'Perfil Hepático', 'Perfil de Lípidos'"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción del Perfil",
        help_text="Descripción detallada de qué incluye el perfil"
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Precio del Perfil",
        help_text="Precio del paquete (puede ser diferente a la suma de estudios individuales)"
    )
    area_pertenencia = models.ForeignKey(
        CategoriaExamen,
        on_delete=models.PROTECT,
        related_name='perfiles',
        verbose_name="Área de Pertenencia",
        help_text="Área principal del perfil (ej: Química Clínica, Hematología)"
    )
    pruebas = models.ManyToManyField(
        Estudio,
        related_name='perfiles',
        verbose_name="Pruebas Incluidas",
        help_text="Estudios individuales que incluye este perfil"
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Perfil Activo",
        help_text="Indica si el perfil está disponible para ordenar"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil de Laboratorio'
        verbose_name_plural = 'Perfiles de Laboratorio'
        ordering = ['area_pertenencia__nombre', 'nombre']

    def __str__(self) -> str:
        return f'{self.nombre} ({self.area_pertenencia.nombre})'

    def calcular_precio_total_individual(self):
        """Calcula el precio total si se cobraran las pruebas individuales."""
        return sum(prueba.precio_base for prueba in self.pruebas.all())

    def ahorro_porcentual(self):
        """Calcula el porcentaje de ahorro al comprar el perfil vs individual."""
        total_individual = self.calcular_precio_total_individual()
        if total_individual == 0:
            return 0
        ahorro = total_individual - self.precio
        return (ahorro / total_individual) * 100

    def agregar_estudios_a_orden(self, orden, precio_perfil=None):
        """
        Agrega todos los estudios del perfil a una orden.
        Si una prueba ya existe en la orden, no la duplica.
        
        Args:
            orden: Instancia de Orden
            precio_perfil: Precio total del perfil (opcional, usa self.precio si no se especifica)
            
        Returns:
            tuple: (estudios_agregados, estudios_duplicados, precio_distribuido)
        """
        if precio_perfil is None:
            precio_perfil = self.precio
        
        estudios_agregados = []
        estudios_duplicados = []
        estudios_perfil = self.pruebas.all()
        
        # Si no hay estudios, retornar
        if not estudios_perfil.exists():
            return estudios_agregados, estudios_duplicados, 0
        
        # Precio por estudio (distribución proporcional del precio del perfil)
        precio_por_estudio = precio_perfil / estudios_perfil.count()
        
        for estudio in estudios_perfil:
            # Verificar si el estudio ya existe en la orden (evitar duplicados)
            detalle_existente = DetalleOrden.objects.filter(orden=orden, estudio=estudio).first()
            
            if detalle_existente:
                # Ya existe, marcarlo pero no duplicarlo
                estudios_duplicados.append(estudio)
                # Actualizar el perfil de origen si no tiene uno
                if not detalle_existente.perfil:
                    detalle_existente.perfil = self
                    detalle_existente.save()
            else:
                # Crear nuevo detalle
                DetalleOrden.objects.create(
                    orden=orden,
                    estudio=estudio,
                    perfil=self,
                    precio_unitario=precio_por_estudio,
                    cantidad=1
                )
                estudios_agregados.append(estudio)
        
        return estudios_agregados, estudios_duplicados, precio_por_estudio


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
# MODELOS TÉCNICOS (Placeholders) - Arquitectura PRIS-VALLE
# ==============================================================================
class ControlCalidad(models.Model):
    """Control de calidad para Levey-Jennings (placeholder en app laboratorio)."""
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="qc_laboratorio")
    equipo = models.CharField(max_length=255)
    parametro = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=4)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Control de Calidad (QC)"
        verbose_name_plural = "Control de Calidad (QC)"
        ordering = ["-fecha_registro"]


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
        Estudio,
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


class Medico(models.Model):
    """
    Médico solicitante de estudios de laboratorio.
    """
    nombre = models.CharField(
        max_length=200,
        help_text='Nombre completo del médico.',
    )
    especialidad = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text='Especialidad médica (opcional).',
    )
    activo = models.BooleanField(
        default=True,
        help_text='Indica si el médico está activo en el sistema.',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Médico'
        verbose_name_plural = 'Médicos'
        ordering = ['nombre']

    def __str__(self) -> str:
        especialidad_str = f' ({self.especialidad})' if self.especialidad else ''
        return f'{self.nombre}{especialidad_str}'


class Orden(models.Model):
    """
    Orden de laboratorio (solicitud de estudios para un paciente).
    Multi-tenant: siempre filtrar por empresa. Preparada para PRIS.
    """
    ORIGEN_PUBLICO_GENERAL = 'PUBLICO_GENERAL'
    ORIGEN_CONVENIO = 'CONVENIO'
    ORIGEN_SEGURO = 'SEGURO'
    ORIGEN_OTRO = 'OTRO'
    ORIGEN_CHOICES = [
        (ORIGEN_PUBLICO_GENERAL, 'Público General'),
        (ORIGEN_CONVENIO, 'Convenio'),
        (ORIGEN_SEGURO, 'Seguro'),
        (ORIGEN_OTRO, 'Otro'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ordenes_laboratorio',
        help_text='Empresa/tenant dueño de esta orden (multi-tenant SaaS).',
    )
    paciente = models.ForeignKey(
        'core.Paciente',
        on_delete=models.PROTECT,
        related_name='ordenes_laboratorio',
    )
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ordenes_laboratorio_creadas',
        help_text='Usuario que registró la orden (para comisiones / auditoría).',
    )
    medico = models.ForeignKey(
        Medico,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='ordenes',
        help_text='Médico solicitante (opcional).',
    )
    medico_texto = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text='Nombre del médico en texto libre (si no está en el catálogo).',
    )
    origen = models.CharField(
        max_length=20,
        choices=ORIGEN_CHOICES,
        default=ORIGEN_PUBLICO_GENERAL,
        help_text='Origen de la orden (público general, convenio, seguro, etc.).',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado_pago = models.BooleanField(default=False, help_text='Indica si la orden está pagada.')

    # Control de Calidad y Validación
    ESTADO_ANALISIS_PENDIENTE = 'PENDIENTE'
    ESTADO_ANALISIS_EN_PROCESO = 'EN_PROCESO'
    ESTADO_ANALISIS_VALIDADO = 'VALIDADO'
    ESTADO_ANALISIS_CHOICES = [
        (ESTADO_ANALISIS_PENDIENTE, 'Pendiente'),
        (ESTADO_ANALISIS_EN_PROCESO, 'En Proceso'),
        (ESTADO_ANALISIS_VALIDADO, 'Validado'),
    ]
    estado_analisis = models.CharField(
        max_length=20,
        choices=ESTADO_ANALISIS_CHOICES,
        default=ESTADO_ANALISIS_PENDIENTE,
        help_text='Estado del análisis de laboratorio. Solo órdenes VALIDADAS pueden imprimirse.',
    )
    fecha_validacion = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Fecha y hora en que la orden fue validada.',
    )
    usuario_valido = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='ordenes_validadas',
        help_text='Usuario que validó la orden (control de calidad).',
    )

    # Campos para Inteligencia Artificial
    IA_STATUS_PENDIENTE = 'PENDIENTE'
    IA_STATUS_GENERADO = 'GENERADO'
    IA_STATUS_ERROR = 'ERROR'
    IA_STATUS_CHOICES = [
        (IA_STATUS_PENDIENTE, 'Pendiente'),
        (IA_STATUS_GENERADO, 'Generado'),
        (IA_STATUS_ERROR, 'Error'),
    ]
    interpretacion_ia = models.TextField(
        blank=True,
        null=True,
        help_text='Resumen clínico generado por AI basado en los resultados de la orden.',
    )
    ia_status = models.CharField(
        max_length=20,
        choices=IA_STATUS_CHOICES,
        default=IA_STATUS_PENDIENTE,
        help_text='Estado del análisis de inteligencia artificial para esta orden.',
    )

    # ── PRE-MIGRACIÓN MAESTRA: campo de enlace hacia core.OrdenDeServicio ────────
    # Estos campos se activarán en la Migración Unificada.
    # core_orden_id = models.PositiveIntegerField(
    #     null=True, blank=True, db_index=True,
    #     help_text='ID del core.OrdenDeServicio espejo. Activo tras Migración Maestra.',
    # )
    # core_paciente_id = models.PositiveIntegerField(
    #     null=True, blank=True, db_index=True,
    #     help_text='ID del core.Paciente canónico. Activo tras Migración Maestra.',
    # )
    # ─────────────────────────────────────────────────────────────────────────────

    class Meta:
        verbose_name = 'Orden de Laboratorio'
        verbose_name_plural = 'Órdenes de Laboratorio'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['empresa', 'estado_analisis'], name='lab_orden_empresa_estado_idx'),
            models.Index(fields=['empresa', '-fecha_creacion'], name='lab_orden_empresa_fecha_idx'),
            models.Index(fields=['estado_analisis'], name='lab_orden_estado_idx'),
        ]

    def __str__(self) -> str:
        return f'Orden #{self.id} - {self.paciente}'

    @property
    def total(self):
        from decimal import Decimal
        total = Decimal('0')
        for detalle in self.detalles.all():
            total += detalle.subtotal
        return total


class Parametro(models.Model):
    """
    Parámetro de un estudio con sus rangos de referencia.
    Permite múltiples parámetros por estudio (ej: Glucosa en ayunas, Glucosa postprandial).
    """
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='parametros',
        help_text='Estudio al que pertenece este parámetro.',
    )
    nombre = models.CharField(
        max_length=150,
        help_text='Nombre del parámetro (ej: "Glucosa", "Hemoglobina").',
    )
    codigo_interfaz = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Código que envía el equipo de laboratorio (ej: "GLU", "HGB"). Usado para mapeo automático de resultados.',
    )
    valor_ref_min = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor mínimo de referencia para este parámetro.',
    )
    valor_ref_max = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor máximo de referencia para este parámetro.',
    )
    unidades = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Unidades de medición (ej. 'mg/dL', 'mmol/L').",
    )

    # Metadatos del catálogo clínico original
    TIPO_RESULTADO_CHOICES = [
        ('Numerico', 'Numérico'),
        ('Texto', 'Texto'),
        ('Opciones', 'Opciones predefinidas'),
    ]
    TIPO_REFERENCIA_CHOICES = [
        ('Rango numerico', 'Rango numérico'),
        ('Texto libre', 'Texto libre'),
        ('Sin referencia', 'Sin referencia'),
    ]
    abreviatura = models.CharField(
        max_length=30, blank=True, null=True,
        help_text='Código corto del parámetro (ej: leuct, RBC, HGB). Clave en HL7/ASTM.',
        db_index=True,
    )
    departamento = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Sección de laboratorio (Hematología, Bioquímica Clínica, etc.).',
        db_index=True,
    )
    tipo_muestra = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Tipo de muestra requerida (ej: SANGRE TOTAL-TUBO LILA).',
    )
    tipo_resultado = models.CharField(
        max_length=20, choices=TIPO_RESULTADO_CHOICES, default='Numerico',
        help_text='Forma de captura del resultado.',
    )
    tipo_referencia = models.CharField(
        max_length=30, choices=TIPO_REFERENCIA_CHOICES, default='Rango numerico',
        help_text='Tipo de rango de referencia para este parámetro.',
    )
    decimales = models.SmallIntegerField(
        default=2,
        help_text='Número de decimales al reportar/validar el resultado.',
    )
    formula = models.CharField(
        max_length=500, blank=True, null=True,
        help_text='Fórmula de cálculo si el parámetro es derivado (ej: VCM = HCT/RBC*10).',
    )
    imprimir_en_negritas = models.BooleanField(
        default=False,
        help_text='Si True, el resultado se imprime en negritas en el reporte PDF.',
    )
    valor_normalidad_texto = models.TextField(
        blank=True, null=True,
        help_text='Rango de referencia en texto libre para parámetros cualitativos.',
    )
    resultado_opciones = models.CharField(
        max_length=500, blank=True, null=True,
        help_text='Opciones de resultado separadas por | (para tipo Opciones).',
    )
    es_antibiograma = models.BooleanField(
        default=False,
        help_text='Si True, el resultado es un antibiograma (sensibilidad a antibióticos).',
    )
    imprimir_metodo = models.BooleanField(
        default=False,
        help_text='Si True, el método analítico se imprime en el reporte PDF.',
    )
    notas = models.TextField(
        blank=True, null=True,
        help_text='Notas adicionales del parámetro para el reporte.',
    )
    indicaciones = models.TextField(
        blank=True, null=True,
        help_text='Instrucciones de preparación del paciente para este parámetro.',
    )
    orden_impresion = models.PositiveSmallIntegerField(
        default=0,
        help_text='Orden de aparición en el reporte PDF. Menor número = primero.',
    )
    etiqueta_interfaz = models.CharField(
        max_length=30, blank=True, null=True,
        help_text='Nombre de la etiqueta en el analizador (puede diferir del código interfaz).',
    )

    class Meta:
        verbose_name = 'Parámetro'
        verbose_name_plural = 'Parámetros'
        ordering = ['estudio__nombre', 'orden_impresion', 'nombre']
        indexes = [
            models.Index(fields=['codigo_interfaz'], name='lab_param_codigo_interfaz_idx'),
            models.Index(fields=['estudio', 'orden_impresion'], name='lab_param_estudio_orden_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.nombre} ({self.estudio.nombre})'


class Resultado(models.Model):
    """
    Resultado capturado para un estudio dentro de una orden.
    Soporta validación automática de valores anormales.
    """
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='resultados',
    )
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.PROTECT,
        related_name='resultados',
    )
    valor_obtenido = models.CharField(
        max_length=100,
        help_text='Valor reportado para este estudio (texto libre).',
    )
    valor = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Alias para valor_obtenido (compatibilidad).',
    )
    es_anormal = models.BooleanField(
        default=False,
        help_text='Marca si el resultado está fuera del rango de referencia (aparecerá con * en PDF).',
    )
    notas_ia = models.TextField(
        blank=True,
        null=True,
        help_text='Observación específica de la AI para este parámetro.',
    )
    # ── ISO 15189 — Campos de validación crítica ──────────────────────────────
    es_critico = models.BooleanField(
        default=False, db_index=True,
        help_text='True cuando el valor supera umbrales de pánico (ISO 15189).',
    )
    alerta_critica_enviada = models.BooleanField(
        default=False,
        help_text='True cuando ya se notificó al QC/médico sobre este valor crítico.',
    )
    rango_usado = models.ForeignKey(
        'laboratorio.RangoReferenciaParametro',
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='resultados_validados',
        help_text='Rango dinámico ISO 15189 que se usó para la validación.',
    )
    parametro_ref = models.ForeignKey(
        'laboratorio.Parametro',
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='resultados_parametro',
        help_text='Parámetro de referencia (para laboratorio detallado).',
    )
    origen_hl7 = models.ForeignKey(
        'laboratorio.ResultadoHL7',
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='resultados_integrados',
        help_text='Resultado HL7/ASTM origen si fue integrado desde equipo.',
    )

    class Meta:
        verbose_name = 'Resultado de Estudio'
        verbose_name_plural = 'Resultados de Estudios'
        ordering = ['orden_id', 'estudio__nombre']
        indexes = [
            models.Index(fields=['orden', 'parametro_ref'], name='lab_resultado_orden_param_idx'),
            models.Index(fields=['es_critico'], name='lab_resultado_critico_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.estudio.nombre} = {self.valor_obtenido} (Orden {self.orden_id})'

    def save(self, *args, **kwargs):
        """
        Auto-valida el resultado contra rangos dinámicos ISO 15189 (si existen)
        y fallback a rangos estáticos del Estudio.
        """
        # Sincronizar alias
        if self.valor_obtenido and not self.valor:
            self.valor = self.valor_obtenido

        if self.estudio and self.valor_obtenido:
            try:
                from laboratorio.services.iso15189 import validar_resultado, disparar_alerta_critica

                # Intentar obtener parametro_ref desde el estudio
                parametro_id = getattr(self.parametro_ref, 'id', None)

                # Obtener datos del paciente para rangos dinámicos
                edad = None
                sexo = None
                try:
                    orden = self.orden
                    if hasattr(orden, 'paciente') and orden.paciente:
                        from datetime import date
                        if orden.paciente.fecha_nacimiento:
                            hoy = date.today()
                            fn = orden.paciente.fecha_nacimiento
                            edad = (hoy - fn).days / 365.25
                        sexo = getattr(orden.paciente, 'sexo', None)
                except Exception:
                    pass

                if parametro_id:
                    validacion = validar_resultado(
                        parametro_id=parametro_id,
                        valor_str=self.valor_obtenido,
                        edad_paciente=edad,
                        sexo_paciente=sexo,
                    )
                    self.es_anormal = validacion.es_anormal
                    self.es_critico = validacion.es_critico

                    if validacion.es_critico and not self.alerta_critica_enviada:
                        orden_id = getattr(self, 'orden_id', None)
                        disparar_alerta_critica(
                            resultado_id=self.pk or 0,
                            validacion=validacion,
                            orden_id=orden_id,
                            parametro_nombre=getattr(self.parametro_ref, 'nombre', ''),
                        )
                        self.alerta_critica_enviada = True
                else:
                    # Fallback estático
                    valor_num = float(self.valor_obtenido.replace(',', '').strip())
                    est = self.estudio
                    if est.valor_minimo is not None and valor_num < float(est.valor_minimo):
                        self.es_anormal = True
                    elif est.valor_maximo is not None and valor_num > float(est.valor_maximo):
                        self.es_anormal = True
                    else:
                        self.es_anormal = False

            except (ValueError, AttributeError):
                pass
            except Exception:
                pass

        super().save(*args, **kwargs)


class DetalleOrden(models.Model):
    """
    Línea de detalle de una orden (estudios solicitados).
    Congela el precio del estudio al momento de la venta.
    Puede venir de un perfil o ser un estudio individual.
    """
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='detalles',
    )
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.PROTECT,
        related_name='detalles_orden',
    )
    perfil = models.ForeignKey(
        'PerfilLaboratorio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='detalles_orden',
        verbose_name="Perfil de Origen",
        help_text="Si este estudio viene de un perfil, se registra aquí para agrupación visual"
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Precio cobrado por este estudio en el momento de la venta.',
    )
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Detalle de Orden'
        verbose_name_plural = 'Detalles de Orden'
        # Evitar duplicados: mismo estudio en la misma orden (importante para perfiles que se solapan)
        unique_together = ('orden', 'estudio')

    def __str__(self) -> str:
        perfil_str = f' ({self.perfil.nombre})' if self.perfil else ''
        return f'{self.estudio.nombre} x{self.cantidad}{perfil_str} (Orden {self.orden_id})'

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


# ==============================================================================
# MODELOS DE CUMPLIMIENTO NORMATIVO (NOM-007 + ISO 15189)
# ==============================================================================

class ResponsableSanitario(models.Model):
    """
    Responsable Sanitario del Laboratorio Clínico.
    CRÍTICO NOM-007-SSA3-2011: El reporte debe incluir nombre, cédula y universidad.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='responsable_sanitario',
        verbose_name="Usuario del Sistema",
        help_text="Usuario vinculado al Responsable Sanitario"
    )
    
    # Datos Legales Obligatorios (NOM-007)
    cedula_profesional = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Cédula Profesional (DGP)",
        help_text="Número de cédula profesional emitida por la Dirección General de Profesiones"
    )
    universidad_titulo = models.CharField(
        max_length=255,
        verbose_name="Universidad que Expidió el Título",
        help_text="Nombre completo de la institución educativa"
    )
    
    # Datos Profesionales
    especialidad = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Especialidad",
        help_text="Ej: Químico Farmacobiólogo, Químico Clínico"
    )
    numero_autorizacion_sanitaria = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Número de Autorización Sanitaria",
        help_text="Número de licencia sanitaria del laboratorio (COFEPRIS)"
    )
    
    # Firma Digital
    firma_digital = models.ImageField(
        upload_to='firmas_sanitarias/%Y/',
        blank=True,
        null=True,
        verbose_name="Firma Digital",
        help_text="Imagen de la firma para incluir en reportes PDF",
        validators=[validate_image_upload],
    )
    
    # Control
    activo = models.BooleanField(
        default=True,
        verbose_name="Responsable Activo",
        help_text="Solo puede haber UN responsable activo a la vez"
    )
    fecha_alta = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Alta"
    )
    fecha_baja = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Baja"
    )
    
    class Meta:
        verbose_name = "Responsable Sanitario"
        verbose_name_plural = "Responsables Sanitarios"
        ordering = ['-activo', '-fecha_alta']
    
    def __str__(self) -> str:
        activo_str = " [ACTIVO]" if self.activo else ""
        return f"Q.F.B. {self.usuario.get_full_name()} - Céd. {self.cedula_profesional}{activo_str}"
    
    def save(self, *args, **kwargs):
        """
        Garantiza que solo haya un Responsable Sanitario activo a la vez.
        Si este se marca como activo, desactiva a los demás.
        """
        if self.activo:
            # Desactivar otros responsables activos
            ResponsableSanitario.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)
        super().save(*args, **kwargs)


class NotificacionPanico(models.Model):
    """
    Bitácora de Notificación de Valores Críticos (ISO 15189:2012, Punto 5.9).
    
    Requisito Internacional: Cuando se detecta un valor crítico, el laboratorio DEBE:
    - Notificar INMEDIATAMENTE al médico tratante
    - Registrar: ¿A quién? ¿Cuándo? ¿Por qué medio?
    
    Sin este registro, el laboratorio NO puede demostrar que cumplió con la notificación.
    """
    MEDIO_TELEFONO = 'TELEFONO'
    MEDIO_WHATSAPP = 'WHATSAPP'
    MEDIO_EMAIL = 'EMAIL'
    MEDIO_PRESENCIAL = 'PRESENCIAL'
    MEDIO_CHOICES = [
        (MEDIO_TELEFONO, 'Teléfono'),
        (MEDIO_WHATSAPP, 'WhatsApp'),
        (MEDIO_EMAIL, 'Correo Electrónico'),
        (MEDIO_PRESENCIAL, 'Presencial'),
    ]
    
    # Relación con Resultado
    resultado = models.ForeignKey(
        'core.ResultadoParametro',
        on_delete=models.PROTECT,
        related_name='notificaciones_panico',
        verbose_name="Resultado Crítico"
    )
    # v7.5: trazabilidad ISO 15189 enlazada a core.OrdenDeServicio (única orden operativa)
    orden = models.ForeignKey(
        'core.OrdenDeServicio',
        on_delete=models.PROTECT,
        related_name='notificaciones_panico_iso',
        verbose_name="Orden Asociada"
    )
    
    # Datos de la Notificación
    medico_notificado = models.CharField(
        max_length=255,
        verbose_name="Nombre del Médico Notificado",
        help_text="Nombre completo del médico o personal que recibió la notificación"
    )
    cargo_receptor = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Cargo del Receptor",
        help_text="Ej: Médico Tratante, Enfermera Jefe, Residente"
    )
    medio_notificacion = models.CharField(
        max_length=20,
        choices=MEDIO_CHOICES,
        verbose_name="Medio de Notificación"
    )
    numero_contacto = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Número de Contacto",
        help_text="Teléfono o correo usado para la notificación"
    )
    
    # Trazabilidad Forense
    fecha_hora_notificacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y Hora de Notificación"
    )
    usuario_notifico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='notificaciones_panico_realizadas',
        verbose_name="Usuario que Realizó la Notificación"
    )
    
    # Confirmación
    confirmacion_recepcion = models.BooleanField(
        default=False,
        verbose_name="Confirmación de Recepción",
        help_text="El receptor confirmó que recibió y entendió la información"
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones",
        help_text="Detalles adicionales de la notificación (ej: 'Médico indicó que revisará al paciente de inmediato')"
    )
    
    # Auditoría de Seguimiento
    seguimiento_realizado = models.BooleanField(
        default=False,
        verbose_name="Seguimiento Realizado",
        help_text="Se realizó seguimiento para verificar atención al paciente"
    )
    fecha_seguimiento = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Seguimiento"
    )
    resultado_seguimiento = models.TextField(
        blank=True,
        null=True,
        verbose_name="Resultado del Seguimiento"
    )
    
    class Meta:
        verbose_name = "Notificación de Valor Crítico (Pánico)"
        verbose_name_plural = "Notificaciones de Valores Críticos"
        ordering = ['-fecha_hora_notificacion']
        indexes = [
            models.Index(fields=['orden', '-fecha_hora_notificacion']),
            models.Index(fields=['usuario_notifico', '-fecha_hora_notificacion']),
        ]
    
    def __str__(self) -> str:
        an = getattr(self.resultado, 'analito', None)
        nom = an.nombre if an else '?'
        return f"Notificación Pánico - {nom} = {self.resultado.valor} - Notificado a: {self.medico_notificado}"


# ==============================================================================
# PILAR 2: INMUTABILIDAD CLÍNICA (ISO 15189)
# MODELO DE HISTORIAL DE RESULTADOS - LA CAJA NEGRA DEL LABORATORIO
# ==============================================================================

class HistorialResultados(models.Model):
    """
    Registro inmutable de cambios en resultados de laboratorio.
    
    Cumplimiento: ISO 15189 (Gestión de Calidad en Laboratorios Clínicos)
    Principio: La verdad original nunca se pierde. Todo cambio es rastreado.
    
    Casos de uso:
    - Corrección de errores de captura
    - Recalibración de equipos
    - Auditorías de COFEPRIS
    - Litigios médico-legales
    """
    
    # Relación con el resultado actual
    resultado_asociado = models.ForeignKey(
        'core.ResultadoParametro',
        on_delete=models.PROTECT,
        related_name='historial_cambios_lab',  # Changed to avoid clash
        verbose_name="Resultado Asociado",
        help_text="El resultado que fue modificado"
    )
    
    # Datos del cambio
    valor_anterior = models.TextField(
        verbose_name="Valor Anterior",
        help_text="Valor original antes del cambio (puede ser numérico o texto)"
    )
    valor_nuevo = models.TextField(
        verbose_name="Valor Nuevo",
        help_text="Valor después del cambio"
    )
    
    # Trazabilidad forense
    motivo_cambio = models.TextField(
        verbose_name="Motivo del Cambio",
        help_text="Explicación obligatoria del porqué se realizó la modificación"
    )
    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cambios_resultados_realizados',
        verbose_name="Usuario Responsable",
        help_text="Químico o supervisor que autorizó el cambio"
    )
    fecha_hora_cambio = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y Hora del Cambio",
        help_text="Timestamp inmutable del momento exacto del cambio"
    )
    
    # Contexto del cambio
    resultado_validado_previamente = models.BooleanField(
        default=False,
        verbose_name="Resultado Ya Validado",
        help_text="True si el resultado ya había sido validado antes del cambio (más crítico)"
    )
    resultado_entregado_previamente = models.BooleanField(
        default=False,
        verbose_name="Resultado Ya Entregado",
        help_text="True si el resultado ya fue entregado al paciente (altamente crítico)"
    )
    
    # Hash de integridad (opcional pero recomendado)
    hash_integridad = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name="Hash de Integridad",
        help_text="SHA-256 del cambio para verificación forense"
    )
    
    # Auditoría adicional
    ip_origen = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP de Origen",
        help_text="Dirección IP desde donde se realizó el cambio"
    )
    observaciones_supervisor = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones del Supervisor",
        help_text="Notas adicionales del supervisor que autorizó (si aplica)"
    )
    
    class Meta:
        verbose_name = "Historial de Resultado"
        verbose_name_plural = "Historial de Resultados"
        ordering = ['-fecha_hora_cambio']
        indexes = [
            models.Index(fields=['resultado_asociado', '-fecha_hora_cambio']),
            models.Index(fields=['usuario_responsable', '-fecha_hora_cambio']),
            models.Index(fields=['-fecha_hora_cambio']),
        ]
        permissions = [
            ("ver_historial_resultados", "Puede ver el historial completo de cambios de resultados"),
            ("modificar_resultados_validados", "Puede modificar resultados ya validados"),
        ]
    
    def __str__(self):
        return f"Cambio en Resultado #{self.resultado_asociado_id} por {self.usuario_responsable.username} el {self.fecha_hora_cambio.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe save() para generar hash de integridad automáticamente.
        """
        if not self.hash_integridad:
            self.hash_integridad = self.generar_hash_integridad()
        
        super().save(*args, **kwargs)
    
    def generar_hash_integridad(self):
        """
        Genera un hash SHA-256 del cambio para verificación forense.
        
        Componentes del hash:
        - ID del resultado
        - Valor anterior
        - Valor nuevo
        - Usuario responsable
        - Timestamp
        """
        datos_para_hash = {
            'resultado_id': self.resultado_asociado_id,
            'valor_anterior': self.valor_anterior,
            'valor_nuevo': self.valor_nuevo,
            'usuario_id': self.usuario_responsable_id,
            'timestamp': str(self.fecha_hora_cambio) if self.fecha_hora_cambio else ''
        }
        
        # Serializar a JSON ordenado (para consistencia)
        json_datos = json.dumps(datos_para_hash, sort_keys=True)
        
        # Generar hash SHA-256
        return hashlib.sha256(json_datos.encode('utf-8')).hexdigest()
    
    @classmethod
    def registrar_cambio(cls, resultado, valor_anterior, valor_nuevo, motivo, usuario, ip_origen=None):
        """
        Método de clase para registrar un cambio de forma segura.
        
        Args:
            resultado: Instancia de ResultadoParametro que cambia
            valor_anterior: Valor antes del cambio (string o número)
            valor_nuevo: Valor después del cambio
            motivo: Razón del cambio (obligatorio)
            usuario: Usuario responsable del cambio
            ip_origen: IP desde donde se realizó (opcional)
        
        Returns:
            Instancia de HistorialResultados creada
        """
        from core.models import OrdenDeServicio
        
        # Determinar si el resultado ya estaba validado o entregado
        orden = resultado.orden
        resultado_validado = resultado.validado
        resultado_entregado = orden.estado in ['ENTREGADO', 'RESULTADOS_LISTOS']
        
        # Crear registro histórico
        historial = cls(
            resultado_asociado=resultado,
            valor_anterior=str(valor_anterior),
            valor_nuevo=str(valor_nuevo),
            motivo_cambio=motivo,
            usuario_responsable=usuario,
            resultado_validado_previamente=resultado_validado,
            resultado_entregado_previamente=resultado_entregado,
            ip_origen=ip_origen
        )
        historial.save()
        
        return historial


# ==============================================================================
# FASE 6 — ISO 15189: MODELOS PENDIENTES (MIGRACIÓN MAESTRA)
# ==============================================================================
# Descomentar TODOS los bloques siguientes al ejecutar la Migración Unificada.
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
        'Parametro', on_delete=models.CASCADE,
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


class ResultadoHL7(models.Model):
    """
    Resultado recibido crudamente desde un analizador de laboratorio vía HL7/ASTM.
    Antes de integrarse a Resultado, pasa por validación QC y mapeo de parámetros.
    """
    ESTADO_CHOICES = [
        ('RECIBIDO', 'Recibido — Pendiente mapeo'),
        ('MAPEADO', 'Mapeado — Pendiente QC'),
        ('QC_OK', 'QC Aprobado — Listo para validar'),
        ('QC_FALLO', 'QC Fallido — Requiere revisión'),
        ('INTEGRADO', 'Integrado a Resultado'),
        ('RECHAZADO', 'Rechazado manualmente'),
    ]

    mensaje_crudo = models.TextField(help_text='Mensaje HL7/ASTM raw recibido del analizador')
    orden = models.ForeignKey(
        'Orden', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resultados_hl7'
    )
    parametro = models.ForeignKey(
        'Parametro', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resultados_hl7'
    )
    codigo_parametro_equipo = models.CharField(max_length=50, help_text='Código enviado por el equipo (ej: GLU, HGB)')
    valor_raw = models.CharField(max_length=100)
    unidad_raw = models.CharField(max_length=30, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='RECIBIDO', db_index=True)
    ip_equipo = models.GenericIPAddressField(null=True, blank=True)
    protocolo = models.CharField(
        max_length=10,
        choices=[
            ('HL7', 'HL7 v2.x'),
            ('ASTM', 'ASTM E1394'),
            ('JSON', 'JSON / API'),
        ],
        default='HL7',
    )
    fecha_recepcion = models.DateTimeField(auto_now_add=True)
    fecha_integracion = models.DateTimeField(null=True, blank=True)
    notas_qc = models.TextField(blank=True)

    class Meta:
        app_label = 'laboratorio'
        verbose_name = 'Resultado HL7/ASTM'
        verbose_name_plural = 'Resultados HL7/ASTM'
        ordering = ['-fecha_recepcion']
        indexes = [
            models.Index(fields=['estado', 'fecha_recepcion'], name='hl7_estado_fecha_idx'),
        ]


class ResultadoHL7Huerfano(models.Model):
    """
    Cola de cuarentena (dead letter) — Punto 13 v7.5.
    Resultados que no deben integrarse a ResultadoParametro hasta revisión QC:
    sin mapeo a Analito, unidad incompatible con catálogo, o valor no numérico.
    """
    MOTIVO_CHOICES = [
        ('SIN_MAPEO_ANALITO', 'Código equipo sin match en LIMS'),
        ('UNIDAD_INCOMPATIBLE', 'Unidad equipo distinta al catálogo'),
        ('VALOR_NO_NUMERICO', 'Valor no convertible a Decimal (analito numérico)'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='hl7_huerfanos',
    )
    motivo = models.CharField(max_length=40, choices=MOTIVO_CHOICES, db_index=True)
    codigo_equipo = models.CharField(max_length=80)
    valor_raw = models.CharField(max_length=200)
    unidad_equipo = models.CharField(max_length=80, blank=True)
    unidad_catalogo = models.CharField(max_length=120, blank=True)
    analito = models.ForeignKey(
        'lims.Analito',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hl7_huerfanos',
    )
    item_json = models.TextField(help_text='Ítem parseado + meta (JSON)')
    mensaje_contexto = models.TextField(blank=True, help_text='Extracto del mensaje crudo')
    ip_equipo = models.GenericIPAddressField(null=True, blank=True)
    protocolo = models.CharField(max_length=10, blank=True)
    numero_orden_equipo = models.CharField(max_length=80, blank=True)
    estado_revision = models.CharField(
        max_length=20,
        choices=[
            ('PENDIENTE', 'Pendiente revisión QC'),
            ('REVISADO', 'Revisado'),
        ],
        default='PENDIENTE',
        db_index=True,
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'laboratorio'
        verbose_name = 'HL7 — resultado en cuarentena'
        verbose_name_plural = 'HL7 — cola de cuarentena'
        ordering = ['-creado']
        indexes = [
            models.Index(fields=['empresa', 'estado_revision', '-creado'], name='hl7huerf_emp_est_idx'),
        ]

    def __str__(self):
        return f'{self.motivo} {self.codigo_equipo} @ {self.creado:%Y-%m-%d %H:%M}'


# Campos ISO 15189 en Resultado — ya activos vía AddField en la migración maestra

# CCI canónico (Punto 21) — módulo aparte para evitar paquete laboratorio/models/
from laboratorio.cci_models import (  # noqa: E402
    EstadoCanalAnalizador,
    LoteMaterialControl,
    MaterialControl,
    MedicionControlInterno,
)
