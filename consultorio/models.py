"""
MODELOS DEL MÓDULO DE CONSULTORIO MÉDICO
=========================================
Sistema de "Isla Independiente" para el Médico.
Incluye: Agenda, Vademécum, Archivos Adjuntos, Configuración,
Lista de Espera, Encuestas NPS, Seguimiento, Análisis de Patrones.
"""
from django.conf import settings
from django.db import models
from decimal import Decimal

from core.validators import validate_document_upload


# ==============================================================================
# MODELOS LEGACY (MANTENER POR COMPATIBILIDAD)
# ==============================================================================

class AgendaCita(models.Model):
    ESTATUS_PROGRAMADA = "PROGRAMADA"
    ESTATUS_EN_SALA = "EN_SALA"
    ESTATUS_TERMINADA = "TERMINADA"
    ESTATUS_CHOICES = [
        (ESTATUS_PROGRAMADA, "Programada"),
        (ESTATUS_EN_SALA, "En sala"),
        (ESTATUS_TERMINADA, "Terminada"),
    ]

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="citas_consultorio")
    sucursal = models.ForeignKey("core.Sucursal", on_delete=models.SET_NULL, null=True, blank=True, related_name="citas_consultorio")

    paciente = models.ForeignKey("core.Paciente", on_delete=models.PROTECT, related_name="citas_consultorio")
    medico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="citas_asignadas")

    fecha = models.DateField()
    hora = models.TimeField()
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default=ESTATUS_PROGRAMADA)

    notas = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita (Agenda)"
        verbose_name_plural = "Citas (Agenda)"
        ordering = ["-fecha", "-hora"]

    def __str__(self) -> str:
        return f"{self.paciente} {self.fecha} {self.hora} ({self.estatus})"


class ConsultaMedica(models.Model):
    """
    DEPRECATED: Este modelo es LEGACY. NO usar para nuevas funcionalidades.
    El modelo activo es core.ConsultaMedica (con campos SOAP completos).
    Se mantiene únicamente para compatibilidad con migraciones existentes.
    Todas las vistas del consultorio usan core.ConsultaMedica.
    """
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="consultas_medicas")
    sucursal = models.ForeignKey("core.Sucursal", on_delete=models.SET_NULL, null=True, blank=True, related_name="consultas_medicas")

    cita = models.OneToOneField(AgendaCita, on_delete=models.CASCADE, related_name="consulta", null=True, blank=True)
    paciente = models.ForeignKey("core.Paciente", on_delete=models.PROTECT, related_name="consultas_medicas")
    medico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="consultas_realizadas")

    motivo = models.TextField(blank=True, null=True)
    exploracion_fisica = models.TextField(blank=True, null=True)
    diagnostico_cie10 = models.CharField(max_length=30, blank=True, null=True, help_text="Código CIE-10 (ej. E11)")
    diagnostico_texto = models.TextField(blank=True, null=True)
    tratamiento = models.TextField(blank=True, null=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Consulta Médica (LEGACY)"
        verbose_name_plural = "Consultas Médicas (LEGACY)"
        ordering = ["-fecha_creacion"]

    def __str__(self) -> str:
        return f"[LEGACY] Consulta {self.paciente} ({self.fecha_creacion:%Y-%m-%d})"


class Somatometria(models.Model):
    consulta = models.OneToOneField(ConsultaMedica, on_delete=models.CASCADE, related_name="somatometria")

    peso = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    talla = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="En metros o cm (definir estándar).")
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    presion_arterial = models.CharField(max_length=20, null=True, blank=True, help_text="Ej: 120/80")
    sato2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Somatometría"
        verbose_name_plural = "Somatometrías"
        ordering = ["-fecha_registro"]

    def __str__(self) -> str:
        return f"Somatometría ({self.consulta_id})"


class NotaMedica(models.Model):
    """Nota médica / historia clínica (placeholder inicial)."""
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="notas_medicas")
    sucursal = models.ForeignKey("core.Sucursal", on_delete=models.SET_NULL, null=True, blank=True, related_name="notas_medicas")
    paciente = models.ForeignKey("core.Paciente", on_delete=models.PROTECT, related_name="notas_medicas")
    medico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="notas_medicas")

    titulo = models.CharField(max_length=200, default="Nota médica")
    contenido = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nota Médica"
        verbose_name_plural = "Notas Médicas"
        ordering = ["-fecha_creacion"]


# ==============================================================================
# NUEVOS MODELOS: ISLA INDEPENDIENTE DEL MÉDICO
# ==============================================================================

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


class ListaEspera(models.Model):
    """
    Lista de espera inteligente.
    Cuando se cancela una cita, se notifica automáticamente al siguiente en la lista.
    """
    PRIORIDAD_CHOICES = [
        (1, 'Urgente'),
        (3, 'Alta'),
        (5, 'Normal'),
        (7, 'Baja'),
    ]

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="lista_espera")
    paciente = models.ForeignKey("core.Paciente", on_delete=models.PROTECT, related_name="espera_consultorio")
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="lista_espera_consultorio"
    )

    motivo = models.TextField(blank=True, verbose_name="Motivo de consulta")
    fecha_preferida = models.DateField(null=True, blank=True, verbose_name="Fecha preferida")
    hora_preferida = models.TimeField(null=True, blank=True, verbose_name="Hora preferida")
    prioridad = models.IntegerField(
        default=5, choices=PRIORIDAD_CHOICES,
        verbose_name="Prioridad"
    )

    # Control de notificación
    notificado = models.BooleanField(default=False)
    fecha_notificacion = models.DateTimeField(null=True, blank=True)
    respuesta_paciente = models.CharField(
        max_length=20, blank=True,
        choices=[('ACEPTA', 'Acepta'), ('RECHAZA', 'Rechaza'), ('SIN_RESPUESTA', 'Sin respuesta')],
    )

    # Estado
    activo = models.BooleanField(default=True)
    atendido = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paciente en Lista de Espera"
        verbose_name_plural = "Lista de Espera"
        ordering = ['prioridad', 'fecha_registro']

    def __str__(self):
        return f"{self.paciente} - Prioridad {self.get_prioridad_display()}"


class EncuestaSatisfaccion(models.Model):
    """
    Encuesta NPS (Net Promoter Score) post-consulta.
    Mide: Satisfacción general, atención médica, tiempo espera, instalaciones.
    Se envía automáticamente tras finalizar la consulta.
    """
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE)
    consulta = models.OneToOneField(
        "core.ConsultaMedica", on_delete=models.PROTECT,
        related_name='encuesta_satisfaccion_consultorio'
    )
    paciente = models.ForeignKey("core.Paciente", on_delete=models.PROTECT)

    # NPS Core (0-10)
    puntuacion_nps = models.IntegerField(
        verbose_name="¿Qué tan probable es que nos recomiende? (0-10)"
    )

    # Dimensiones (1-5 estrellas)
    atencion_medico = models.IntegerField(
        null=True, blank=True,
        verbose_name="Calidad de atención del médico"
    )
    tiempo_espera = models.IntegerField(
        null=True, blank=True,
        verbose_name="Tiempo de espera"
    )
    instalaciones = models.IntegerField(
        null=True, blank=True,
        verbose_name="Estado de las instalaciones"
    )
    explicacion_tratamiento = models.IntegerField(
        null=True, blank=True,
        verbose_name="Claridad en explicación del tratamiento"
    )

    comentarios = models.TextField(blank=True, verbose_name="Comentarios libres")
    recomendaria = models.BooleanField(default=True, verbose_name="¿Nos recomendaría?")

    # Estado del envío
    token_encuesta = models.CharField(
        max_length=64, unique=True, blank=True,
        verbose_name="Token único de acceso"
    )
    enviada = models.BooleanField(default=False)
    respondida = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Encuesta de Satisfacción"
        verbose_name_plural = "Encuestas de Satisfacción"
        ordering = ['-fecha_respuesta']

    def __str__(self):
        return f"NPS: {self.puntuacion_nps}/10 - {self.paciente}"

    @property
    def clasificacion_nps(self):
        """Clasifica: Promotor (9-10), Pasivo (7-8), Detractor (0-6)."""
        if self.puntuacion_nps >= 9:
            return 'PROMOTOR'
        elif self.puntuacion_nps >= 7:
            return 'PASIVO'
        return 'DETRACTOR'

    def save(self, *args, **kwargs):
        if not self.token_encuesta:
            import secrets
            self.token_encuesta = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)


class SeguimientoTratamiento(models.Model):
    """
    Sistema de seguimiento post-consulta.
    Genera alertas automáticas sobre: medicación, próximas citas, estudios pendientes.
    """
    TIPO_CHOICES = [
        ('MEDICACION', 'Recordatorio de Medicación'),
        ('PROXIMA_CITA', 'Recordatorio de Próxima Cita'),
        ('ESTUDIOS', 'Estudios Pendientes'),
        ('EVOLUCION', 'Seguimiento de Evolución'),
        ('CONTROL', 'Control de Seguimiento'),
    ]

    CANAL_CHOICES = [
        ('WHATSAPP', 'WhatsApp'),
        ('SMS', 'SMS'),
        ('EMAIL', 'Correo Electrónico'),
        ('SISTEMA', 'Notificación en el Sistema'),
    ]

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE)
    consulta = models.ForeignKey(
        "core.ConsultaMedica", on_delete=models.PROTECT,
        related_name='seguimientos_consultorio'
    )
    paciente = models.ForeignKey(
        "core.Paciente", on_delete=models.PROTECT,
        related_name="seguimientos_tratamiento"
    )

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    canal = models.CharField(max_length=20, choices=CANAL_CHOICES, default='WHATSAPP')

    mensaje = models.TextField(verbose_name="Mensaje del recordatorio")
    fecha_programada = models.DateTimeField(verbose_name="Fecha y hora programada")

    # Estado de envío
    enviado = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(null=True, blank=True)

    # Recurrencia (para medicación)
    recurrente = models.BooleanField(default=False)
    intervalo_horas = models.IntegerField(
        null=True, blank=True,
        verbose_name="Cada cuántas horas",
        help_text="Ej: 8 para cada 8 horas"
    )
    fecha_fin = models.DateField(
        null=True, blank=True,
        verbose_name="Última fecha del tratamiento"
    )

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Seguimiento de Tratamiento"
        verbose_name_plural = "Seguimientos de Tratamiento"
        ordering = ['fecha_programada']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.paciente} ({self.fecha_programada})"


class AnalisisPatron(models.Model):
    """
    Análisis de patrones de consulta con IA (CONFIDENCIAL Y ANÓNIMO).
    Los datos se anonimizan: no se vinculan a pacientes individuales.
    Solo contiene métricas agregadas y insights para mejora continua.
    """
    TIPO_CHOICES = [
        ('DIAGNOSTICO', 'Patrones de Diagnóstico'),
        ('TRATAMIENTO', 'Eficacia de Tratamientos'),
        ('CONVERSION', 'Conversión de Servicios (Cirugías, Procedimientos)'),
        ('RETENCION', 'Retención de Pacientes'),
        ('PRODUCTIVIDAD', 'Productividad del Consultorio'),
        ('FINANCIERO', 'Análisis Financiero Anónimo'),
    ]

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    periodo_inicio = models.DateField(verbose_name="Inicio del período")
    periodo_fin = models.DateField(verbose_name="Fin del período")

    # Datos ANONIMIZADOS (no vinculan pacientes)
    total_consultas = models.IntegerField(default=0)
    datos_json = models.JSONField(
        default=dict,
        verbose_name="Datos anónimos del análisis",
        help_text="Estructura JSON con métricas agregadas"
    )

    # Resultado IA
    analisis_ia = models.TextField(
        blank=True,
        verbose_name="Análisis generado por IA",
        help_text="Insights y patrones detectados"
    )
    recomendaciones = models.TextField(
        blank=True,
        verbose_name="Recomendaciones de mejora"
    )

    # Control
    confidencial = models.BooleanField(
        default=True,
        verbose_name="Datos confidenciales",
        help_text="Siempre True: los datos son anónimos y confidenciales"
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='analisis_patrones_generados'
    )

    class Meta:
        verbose_name = "Análisis de Patrón"
        verbose_name_plural = "Análisis de Patrones"
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f"{self.get_tipo_display()} ({self.periodo_inicio} - {self.periodo_fin})"


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


# ==============================================================================
# PRIS SENTINEL: TELEMETRÍA INTELIGENTE Y GESTIÓN DE INCIDENCIAS
# ==============================================================================

class IncidenciaSentinel(models.Model):
    """
    Registro de incidencias detectadas automáticamente (middleware) o reportadas
    por el usuario (botón de queja). Incluye análisis de IA y estado de reparación.
    Modelo central del sistema PRIS SENTINEL.
    Diferente de core.IncidenciaOperativa (auditoría de negocio);
    este es para telemetría técnica del módulo consultorio.
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_REPARACION', 'En Reparación'),
        ('SOLUCIONADO', 'Solucionado'),
    ]
    ORIGEN_CHOICES = [
        ('MIDDLEWARE', 'Captura Automática (Middleware)'),
        ('FEEDBACK', 'Reporte del Usuario (Feedback)'),
        ('MANUAL', 'Registro Manual'),
    ]
    SEVERIDAD_CHOICES = [
        ('CRITICA', 'Crítica (500 / DB Error)'),
        ('ALTA', 'Alta (404 / Lógica rota)'),
        ('MEDIA', 'Media (Warning / UX)'),
        ('BAJA', 'Baja (Cosmético / Informativo)'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="incidencias_sentinel"
    )

    # === ORIGEN Y CONTEXTO ===
    origen = models.CharField(
        max_length=20, choices=ORIGEN_CHOICES, default='MIDDLEWARE',
        verbose_name="Origen de la incidencia"
    )
    usuario_reporta = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='incidencias_reportadas',
        verbose_name="Usuario que experimentó el error"
    )
    url_afectada = models.CharField(
        max_length=500, blank=True, default='',
        verbose_name="URL donde ocurrio el error"
    )
    metodo_http = models.CharField(
        max_length=10, blank=True,
        verbose_name="Método HTTP (GET/POST)"
    )
    namespace = models.CharField(
        max_length=100, blank=True, default='consultorio',
        verbose_name="Namespace del módulo afectado"
    )

    # === DATOS TÉCNICOS ===
    codigo_http = models.IntegerField(
        default=500,
        verbose_name="Código HTTP del error"
    )
    tipo_excepcion = models.CharField(
        max_length=255, blank=True,
        verbose_name="Tipo de excepción (class name)"
    )
    traceback_completo = models.TextField(
        blank=True,
        verbose_name="Traceback técnico completo"
    )
    datos_request = models.JSONField(
        default=dict, blank=True,
        verbose_name="Datos del request (sanitizados)",
        help_text="GET/POST params sin datos sensibles (passwords, tokens)"
    )
    tag = models.CharField(
        max_length=50, default='#BUG_CONSULTA',
        verbose_name="Tag de clasificación"
    )

    # === FEEDBACK DEL USUARIO ===
    descripcion_usuario = models.TextField(
        blank=True,
        verbose_name="Descripción en lenguaje natural",
        help_text="Lo que el usuario describió que falló"
    )

    # === ANÁLISIS IA ===
    analisis_ia = models.TextField(
        blank=True,
        verbose_name="Análisis generado por Gemini",
        help_text="Resumen ejecutivo del error para el Director"
    )
    contexto_cursor = models.TextField(
        blank=True,
        verbose_name="Contexto técnico para Cursor",
        help_text="Bloque exportable para pegar en Cursor y corregir el bug"
    )
    contexto_reparacion = models.JSONField(
        default=dict, blank=True,
        verbose_name="Contexto de autocuración (JSON)",
        help_text="Datos estructurados generados por IA: archivo, línea, código propuesto, instrucciones SSH"
    )

    # === ESTADO Y SEVERIDAD ===
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE',
        verbose_name="Estado de la incidencia"
    )
    severidad = models.CharField(
        max_length=10, choices=SEVERIDAD_CHOICES, default='ALTA',
        verbose_name="Severidad"
    )

    # === RESOLUCIÓN ===
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='incidencias_resueltas',
        verbose_name="Resuelto por"
    )
    notas_resolucion = models.TextField(
        blank=True,
        verbose_name="Notas de resolución"
    )
    fecha_resolucion = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de resolución"
    )

    # === AUDITORÍA ===
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Incidencia Sentinel"
        verbose_name_plural = "Incidencias Sentinel"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', '-fecha_creacion']),
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['severidad', '-fecha_creacion']),
        ]

    def __str__(self):
        return f"[{self.get_severidad_display()}] {self.tipo_excepcion or 'Reporte'} - {self.url_afectada} ({self.get_estado_display()})"


# ==============================================================================
# ULTRASONIDO MÉDICO
# ==============================================================================
class ReporteUltrasonido(models.Model):
    """Informe de estudio de ultrasonido generado por el médico."""
    TIPO_ABDOMINAL    = 'ABDOMINAL'
    TIPO_OBSTETRICO   = 'OBSTETRICO'
    TIPO_PELVICO      = 'PELVICO'
    TIPO_TIROIDES     = 'TIROIDES'
    TIPO_RENAL        = 'RENAL'
    TIPO_CARDIACO     = 'CARDIACO'
    TIPO_PARTES_BLANDAS = 'PARTES_BLANDAS'
    TIPO_OTRO         = 'OTRO'
    TIPO_CHOICES      = [
        (TIPO_ABDOMINAL,    'Ultrasonido Abdominal'),
        (TIPO_OBSTETRICO,   'Ultrasonido Obstétrico'),
        (TIPO_PELVICO,      'Ultrasonido Pélvico'),
        (TIPO_TIROIDES,     'Ultrasonido de Tiroides'),
        (TIPO_RENAL,        'Ultrasonido Renal'),
        (TIPO_CARDIACO,     'Ecocardiograma'),
        (TIPO_PARTES_BLANDAS, 'Partes Blandas'),
        (TIPO_OTRO,         'Otro'),
    ]

    ESTADO_BORRADOR   = 'BORRADOR'
    ESTADO_FIRMADO    = 'FIRMADO'
    ESTADO_ENTREGADO  = 'ENTREGADO'
    ESTADO_CHOICES    = [
        (ESTADO_BORRADOR,  'Borrador'),
        (ESTADO_FIRMADO,   'Firmado'),
        (ESTADO_ENTREGADO, 'Entregado al paciente'),
    ]

    empresa     = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='reportes_usg')
    paciente    = models.ForeignKey('core.Paciente', on_delete=models.CASCADE, related_name='reportes_usg')
    medico      = models.ForeignKey('core.Medico', on_delete=models.SET_NULL, null=True, related_name='reportes_usg')
    orden       = models.ForeignKey('core.OrdenDeServicio', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='reportes_usg', verbose_name="Orden de servicio vinculada")
    tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES, default=TIPO_ABDOMINAL)
    estado      = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ESTADO_BORRADOR)

    semanas_gestacion = models.PositiveSmallIntegerField(null=True, blank=True,
                                                          verbose_name="Semanas de gestación (si aplica)")
    hallazgos   = models.TextField(verbose_name="Hallazgos / descripción del estudio")
    conclusion  = models.TextField(verbose_name="Conclusión / diagnóstico")
    recomendaciones = models.TextField(blank=True, verbose_name="Recomendaciones")

    fecha_estudio = models.DateTimeField(auto_now_add=True)
    fecha_firma   = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'consultorio'
        verbose_name = 'Reporte de Ultrasonido'
        verbose_name_plural = 'Reportes de Ultrasonido'
        ordering = ['-fecha_estudio']
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['paciente', '-fecha_estudio']),
        ]

    def __str__(self):
        return f"USG {self.get_tipo_display()} — {self.paciente} ({self.fecha_estudio:%Y-%m-%d})"


class ImagenUltrasonido(models.Model):
    """Imagen capturada durante un estudio de ultrasonido."""
    reporte     = models.ForeignKey(ReporteUltrasonido, on_delete=models.CASCADE, related_name='imagenes')
    imagen      = models.ImageField(upload_to='ultrasonido/', verbose_name="Imagen")
    descripcion = models.CharField(max_length=200, blank=True, verbose_name="Descripción de la imagen")
    orden_display = models.PositiveSmallIntegerField(default=1, verbose_name="Orden de visualización")
    fecha_captura = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'consultorio'
        verbose_name = 'Imagen de Ultrasonido'
        verbose_name_plural = 'Imágenes de Ultrasonido'
        ordering = ['reporte', 'orden_display']

    def __str__(self):
        return f"Imagen {self.orden_display} — {self.reporte}"
