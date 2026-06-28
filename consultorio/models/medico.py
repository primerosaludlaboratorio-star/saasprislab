"""
Modelos de configuración médica, vademécum y archivos adjuntos.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from core.validators import validate_document_upload


class ConfiguracionMedico(models.Model):
    """
    Configuración personalizada por médico.
    Controla: agenda ON/OFF, modo de cobro, marketing propio, especialidad.
    Cada médico tiene su "isla independiente" de trabajo.
    """
    MODO_COBRO_CHOICES = [
        ('MEDICO', 'Cobro directo por el médico'),
        ('RECEPCION', 'Cobro centralizado en recepción'),
    ]

    medico = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='config_consultorio',
        verbose_name="Médico"
    )
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="configs_medicos"
    )

    # === AGENDA (DESACTIVABLE) ===
    agenda_activa = models.BooleanField(
        default=True,
        verbose_name="Agenda Activa",
        help_text="Si es False, el médico trabaja por orden de llegada"
    )
    duracion_consulta_default = models.IntegerField(
        default=30,
        verbose_name="Duración default (min)"
    )
    horario_inicio = models.TimeField(
        default='08:00',
        verbose_name="Inicio de atención"
    )
    horario_fin = models.TimeField(
        default='20:00',
        verbose_name="Fin de atención"
    )
    dias_atencion = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Días de atención",
        help_text="[1,2,3,4,5] = Lunes a Viernes"
    )
    reserva_online_activa = models.BooleanField(
        default=False,
        verbose_name="Reserva en línea 24/7",
        help_text="Permite que pacientes agenden desde el portal externo"
    )

    # === COBROS ===
    modo_cobro = models.CharField(
        max_length=20,
        choices=MODO_COBRO_CHOICES,
        default='RECEPCION',
        verbose_name="Modo de cobro"
    )
    precio_consulta_default = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Precio consulta general"
    )

    # === MARKETING ===
    marketing_propio = models.BooleanField(
        default=False,
        verbose_name="Marketing independiente",
        help_text="Permite al médico manejar sus propias campañas"
    )

    # === ESPECIALIDAD ===
    especialidad_principal = models.CharField(
        max_length=150, default='Médico General',
        verbose_name="Especialidad"
    )
    subespecialidad = models.CharField(
        max_length=150, blank=True,
        verbose_name="Subespecialidad"
    )

    # === CONFIRMACIONES ===
    whatsapp_confirmaciones = models.BooleanField(
        default=False,
        verbose_name="Confirmaciones por WhatsApp"
    )
    telefono_whatsapp = models.CharField(
        max_length=20, blank=True,
        verbose_name="Teléfono WhatsApp del consultorio"
    )

    # === TRIAJE PRE-CITA ===
    triaje_precita_activo = models.BooleanField(
        default=False,
        verbose_name="Triaje digital pre-cita",
        help_text="Envía formulario automático al paciente tras agendar"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Médico"
        verbose_name_plural = "Configuraciones de Médicos"

    def __str__(self):
        return f"Config: {self.medico.get_full_name()} ({self.especialidad_principal})"


class Vademecum(models.Model):
    """
    Base de datos de medicamentos para verificación en tiempo real.
    Permite buscar dosis, contraindicaciones e interacciones durante prescripción.
    """
    VIA_CHOICES = [
        ('ORAL', 'Oral'),
        ('SUBLINGUAL', 'Sublingual'),
        ('TOPICA', 'Tópica'),
        ('OFTALMICA', 'Oftálmica'),
        ('OTICA', 'Ótica'),
        ('NASAL', 'Nasal'),
        ('INHALADA', 'Inhalada'),
        ('RECTAL', 'Rectal'),
        ('VAGINAL', 'Vaginal'),
        ('IM', 'Intramuscular'),
        ('IV', 'Intravenosa'),
        ('SC', 'Subcutánea'),
        ('ID', 'Intradérmica'),
        ('OTRA', 'Otra'),
    ]

    EMBARAZO_CHOICES = [
        ('A', 'A - Sin riesgo'),
        ('B', 'B - Sin riesgo aparente'),
        ('C', 'C - Riesgo no descartable'),
        ('D', 'D - Riesgo demostrado'),
        ('X', 'X - Contraindicado'),
    ]

    # Identificación
    nombre_generico = models.CharField(
        max_length=255,
        verbose_name="Nombre Genérico",
        help_text="Ej: Paracetamol"
    )
    nombre_comercial = models.CharField(
        max_length=255, blank=True,
        verbose_name="Nombre Comercial",
        help_text="Ej: Tylenol, Tempra"
    )
    principio_activo = models.CharField(
        max_length=255,
        verbose_name="Principio Activo"
    )

    # Presentación
    presentacion = models.CharField(
        max_length=255,
        verbose_name="Presentación",
        help_text="Ej: Tabletas 500mg caja c/20"
    )
    concentracion = models.CharField(
        max_length=100,
        verbose_name="Concentración",
        help_text="Ej: 500mg, 250mg/5ml"
    )
    via_administracion = models.CharField(
        max_length=20, choices=VIA_CHOICES,
        default='ORAL',
        verbose_name="Vía de Administración"
    )

    # Dosificación
    dosis_adulto = models.TextField(
        blank=True,
        verbose_name="Dosis Adulto",
        help_text="Ej: 500-1000mg cada 6-8 horas"
    )
    dosis_pediatrica = models.TextField(
        blank=True,
        verbose_name="Dosis Pediátrica",
        help_text="Ej: 10-15mg/kg cada 6-8 horas"
    )
    dosis_maxima = models.CharField(
        max_length=100, blank=True,
        verbose_name="Dosis Máxima",
        help_text="Ej: 4g/día en adultos"
    )

    # Seguridad Farmacológica
    contraindicaciones = models.TextField(
        blank=True,
        verbose_name="Contraindicaciones",
        help_text="Condiciones donde NO debe usarse"
    )
    efectos_adversos = models.TextField(
        blank=True,
        verbose_name="Efectos Adversos",
        help_text="Efectos secundarios conocidos"
    )
    interacciones = models.TextField(
        blank=True,
        verbose_name="Interacciones Medicamentosas",
        help_text="Medicamentos con los que interactúa"
    )
    embarazo_categoria = models.CharField(
        max_length=2, choices=EMBARAZO_CHOICES,
        blank=True,
        verbose_name="Categoría en Embarazo"
    )

    # Clasificación
    grupo_terapeutico = models.CharField(
        max_length=200, blank=True,
        verbose_name="Grupo Terapéutico",
        help_text="Ej: Analgésico, Antipirético"
    )
    requiere_receta = models.BooleanField(
        default=True,
        verbose_name="Requiere Receta"
    )
    controlado = models.BooleanField(
        default=False,
        verbose_name="Medicamento Controlado"
    )

    # Vinculación con farmacia (si lo tienen en stock)
    producto_farmacia = models.ForeignKey(
        "core.Producto", on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="vademecum_entry",
        verbose_name="Producto en Farmacia",
        help_text="Link al inventario de la farmacia"
    )

    # Multi-tenant
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="vademecum",
        help_text="NULL = medicamento global disponible para todos"
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Medicamento (Vademécum)"
        verbose_name_plural = "Vademécum"
        ordering = ['nombre_generico', 'presentacion']
        indexes = [
            models.Index(fields=['nombre_generico']),
            models.Index(fields=['principio_activo']),
        ]

    def __str__(self):
        return f"{self.nombre_generico} ({self.concentracion}) - {self.presentacion}"


class ArchivoAdjuntoConsulta(models.Model):
    """
    Archivos externos adjuntos a consulta o expediente del paciente.
    Permite subir radiografías, tomografías, documentos de otros lugares,
    fotos de evolución, videos de ultrasonido, etc.
    """
    TIPO_CHOICES = [
        ('RADIOGRAFIA', 'Radiografía'),
        ('TOMOGRAFIA', 'Tomografía'),
        ('RESONANCIA', 'Resonancia Magnética'),
        ('ULTRASONIDO', 'Ultrasonido'),
        ('LABORATORIO_EXTERNO', 'Resultados de Lab Externo'),
        ('RECETA_EXTERNA', 'Receta Externa'),
        ('REFERENCIA', 'Referencia/Contrarreferencia'),
        ('FOTO_EVOLUCION', 'Foto de Evolución'),
        ('VIDEO', 'Video'),
        ('CONSENTIMIENTO', 'Consentimiento Firmado'),
        ('DOCUMENTO', 'Documento General'),
        ('OTRO', 'Otro'),
    ]

    # Relaciones
    consulta = models.ForeignKey(
        "core.ConsultaMedica", on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='archivos_adjuntos_consultorio',
        verbose_name="Consulta asociada"
    )
    paciente = models.ForeignKey(
        "core.Paciente", on_delete=models.PROTECT,
        related_name='archivos_adjuntos',
        verbose_name="Paciente"
    )
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="archivos_adjuntos"
    )

    # Archivo
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, verbose_name="Tipo de Archivo")
    titulo = models.CharField(max_length=255, verbose_name="Título / Descripción corta")
    descripcion = models.TextField(blank=True, verbose_name="Notas adicionales")
    archivo = models.FileField(
        upload_to='adjuntos_consulta/%Y/%m/',
        verbose_name="Archivo",
        validators=[validate_document_upload],
    )

    # Metadatos
    fecha_documento = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha del documento",
        help_text="Fecha en que se realizó el estudio/documento original"
    )
    origen = models.CharField(
        max_length=255, blank=True,
        verbose_name="Institución de origen",
        help_text="Ej: Hospital ABC, Laboratorio XYZ"
    )

    # Auditoría
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='archivos_subidos_consultorio'
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Archivo Adjunto"
        verbose_name_plural = "Archivos Adjuntos"
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo} ({self.paciente})"

    @property
    def es_imagen(self):
        """Verifica si el archivo es una imagen (para preview)."""
        if self.archivo and self.archivo.name:
            ext = self.archivo.name.lower().split('.')[-1]
            return ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
        return False

    @property
    def es_pdf(self):
        if self.archivo and self.archivo.name:
            return self.archivo.name.lower().endswith('.pdf')
        return False
