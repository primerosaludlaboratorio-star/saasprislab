"""
CMMS PRISLAB V8.2 — Sistema de Gestión de Mantenimiento de Equipos
====================================================================
Normativas: ISO 15189 §6.4, COFEPRIS, NOM-007-SSA3-2011

AJUSTES APROBADOS V8.2:
  Ajuste 1: Refacciones multi-silo via GenericForeignKey.
            Un mantenimiento de centrífuga descuenta del Silo Lab;
            un A/C descuenta del Silo Generales. Sin restricción de silo.
  Ajuste 2: Wizard de Carga Visual incluido (ProtocoloEquipo + ArbolDiagnostico
            se construyen desde la interfaz del Director, no el admin crudo).
  Ajuste 3: BypassChecklistAutorizacion — experto autoriza a novato con PIN,
            dejando registro forense completo.

ARQUITECTURA:
  Subsistema A: Biblioteca Técnica  (Protocolos, Procedimientos, Árbol Diagnóstico)
  Subsistema B: Ejecución/Trazabilidad (Checklist, Tickets, Bypass)
  Subsistema C: Gemelo Digital (ExpedienteEquipo, QR)
  Subsistema D: TCO y War Room (RegistroTCO)
"""
import uuid
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

import hashlib
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CHOICES COMPARTIDAS
# =============================================================================

SILO_ORIGEN_CHOICES = [
    ('LAB',        'Silo Laboratorio (Reactivos / Refacciones analíticas)'),
    ('CONSULTORIO','Silo Consultorio (Material médico / Enfermería)'),
    ('GENERAL',    'Silo Insumos Generales (Infraestructura / Admin)'),
]

TIPO_EQUIPO_CHOICES = [
    ('ANALIZADOR',     'Analizador Clínico'),
    ('CENTRIFUGA',     'Centrífuga'),
    ('MICROSCOPIO',    'Microscopio'),
    ('REFRIGERADOR',   'Refrigerador / Congelador'),
    ('AUTOCLAVE',      'Autoclave'),
    ('PC_MEDICA',      'PC / Tablet Médica'),
    ('INFRAESTRUCTURA','Infraestructura (A/C, UPS, Planta, Iluminación)'),
    ('MOBILIARIO',     'Mobiliario Clínico (Camilla, Mesa, Silla)'),
    ('OTRO',           'Otro'),
]

NIVEL_AUTORIZACION_CHOICES = [
    ('TODOS',         'Todos los usuarios'),
    ('QUIMICO',       'Químico / Enfermería'),
    ('TECNICO',       'Técnico de Mantenimiento'),
    ('QUIMICO_JEFE',  'Químico Jefe / Responsable Sanitario'),
    ('DIRECTOR',      'Director / Admin'),
]

TIPO_VALIDACION_PASO_CHOICES = [
    ('CHECKBOX', 'Confirmación (Sí/No)'),
    ('FOTO',     'Fotografía requerida'),
    ('NUMERO',   'Valor numérico'),
    ('TEXTO',    'Texto libre'),
]

TIPO_PROTOCOLO_CHOICES = [
    ('ARRANQUE',           'Protocolo de Arranque / Inicio de Turno'),
    ('APAGADO',            'Protocolo de Apagado / Fin de Turno'),
    ('LIMPIEZA_DIARIA',    'Limpieza Diaria'),
    ('MANTENIMIENTO_PREV', 'Mantenimiento Preventivo (Periódico)'),
    ('CALIBRACION',        'Calibración'),
    ('EMERGENCIA',         'Procedimiento de Emergencia'),
]

TIPO_NODO_CHOICES = [
    ('PREGUNTA',      'Pregunta diagnóstica'),
    ('ACCION',        'Acción / Procedimiento'),
    ('ESCALAMIENTO',  'Escalamiento'),
    ('SOLUCIONADO',   'Problema Resuelto'),
]

NIVEL_ESCALAMIENTO_CHOICES = [
    ('QUIMICO',          'Químico (resolución propia)'),
    ('TECNICO_INTERNO',  'Ingeniería Interna'),
    ('DIRECTOR',         'Dirección — requiere autorización'),
    ('PROVEEDOR',        'Proveedor Externo — requiere firma de Director'),
]

TIPO_COMPONENTE_CHOICES = [
    ('BOMBA',       'Bomba peristáltica'),
    ('FILTRO',      'Filtro (agua, aire, reactivo)'),
    ('LAMPARA',     'Lámpara / Fuente de luz'),
    ('INYECTOR',    'Inyector / Aguja / Sonda'),
    ('MANGUERA',    'Manguera / Tubing'),
    ('VALVULA',     'Válvula'),
    ('ELECTRODO',   'Electrodo'),
    ('TARJETA',     'Tarjeta electrónica'),
    ('REFACCION_GEN','Refacción General'),
    ('OTRO',        'Otro'),
]

ESTADO_TICKET_CHOICES = [
    ('ABIERTO',       'Abierto'),
    ('EN_PROCESO',    'En Proceso'),
    ('ESPERANDO',     'Esperando Refacción / Autorización'),
    ('RESUELTO',      'Resuelto'),
    ('ESCALADO',      'Escalado a Proveedor'),
    ('CERRADO',       'Cerrado'),
]


# =============================================================================
# SUBSISTEMA C — GEMELO DIGITAL (Debe ir primero por dependencias)
# =============================================================================

class ExpedienteEquipo(models.Model):
    """
    Gemelo Digital del equipo físico.
    QR único → landing informativa + acceso rápido a protocolos.
    """
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="expedientes_equipo", verbose_name="Empresa",
    )
    equipo = models.ForeignKey(
        "laboratorio.Equipo", on_delete=models.CASCADE,
        related_name="expediente_cmms", verbose_name="Equipo",
    )
    tipo_equipo   = models.CharField(
        max_length=20, choices=TIPO_EQUIPO_CHOICES, default='ANALIZADOR',
        verbose_name="Tipo de Equipo",
    )
    silo_refacciones = models.CharField(
        max_length=15, choices=SILO_ORIGEN_CHOICES, default='LAB',
        verbose_name="Silo de Refacciones por Defecto",
        help_text="Silo de inventario del que se descontarán las refacciones. "
                  "Se puede cambiar manualmente en cada ticket.",
    )

    # Identificación física
    numero_serie     = models.CharField(max_length=120, blank=True, verbose_name="N° de Serie")
    modelo           = models.CharField(max_length=200, blank=True, verbose_name="Modelo")
    fabricante       = models.CharField(max_length=150, blank=True, verbose_name="Fabricante")
    foto_equipo      = models.ImageField(
        upload_to="mantenimiento/equipos/", blank=True, null=True,
        verbose_name="Foto del Equipo",
    )
    manual_pdf       = models.FileField(
        upload_to="mantenimiento/manuales/", blank=True, null=True,
        verbose_name="Manual PDF del Fabricante",
    )

    # Fechas clave
    fecha_instalacion        = models.DateField(null=True, blank=True, verbose_name="Fecha de Instalación")
    garantia_hasta           = models.DateField(null=True, blank=True, verbose_name="Garantía Hasta")
    fecha_ultima_calibracion = models.DateField(null=True, blank=True, verbose_name="Última Calibración")
    proxima_calibracion      = models.DateField(null=True, blank=True, verbose_name="Próxima Calibración")
    proxima_verificacion_prev= models.DateField(null=True, blank=True, verbose_name="Próximo Mant. Preventivo")

    # QR / NFC para acceso físico rápido
    qr_uid  = models.UUIDField(default=uuid.uuid4, unique=True, editable=False,
                               verbose_name="UID del código QR")
    codigo_nfc = models.CharField(max_length=120, blank=True, null=True,
                                  verbose_name="Código NFC (opcional)")

    # Estado operativo
    en_servicio = models.BooleanField(default=True, verbose_name="En Servicio")
    notas       = models.TextField(blank=True, verbose_name="Notas / Observaciones")

    class Meta:
        verbose_name = "Expediente de Equipo"
        verbose_name_plural = "Expedientes de Equipos"
        unique_together = [('empresa', 'equipo')]
        ordering = ['empresa', 'equipo__nombre']

    def __str__(self):
        return f"Expediente: {self.equipo} [{self.empresa}]"

    def get_qr_url(self):
        from django.urls import reverse
        return reverse('mantenimiento:qr_equipo', args=[str(self.qr_uid)])


# =============================================================================
# SUBSISTEMA A — BIBLIOTECA TÉCNICA
# =============================================================================

class ProtocoloEquipo(models.Model):
    """
    Protocolo de operación para un equipo específico.
    Se construye mediante el Wizard de Carga Visual del Director.
    """
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="protocolos_equipo", verbose_name="Empresa",
        null=True, blank=True,
        help_text="Null = protocolo global PRISLAB (plantilla para todos los tenants).",
    )
    equipo = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.CASCADE,
        related_name="protocolos", verbose_name="Equipo",
        null=True, blank=True,
        help_text="Null = protocolo aplica a todos los equipos del mismo modelo.",
    )
    modelo_equipo = models.CharField(
        max_length=200, blank=True,
        help_text="Si equipo=None, aplica a todos los equipos con este modelo.",
    )
    tipo_protocolo = models.CharField(
        max_length=25, choices=TIPO_PROTOCOLO_CHOICES,
        verbose_name="Tipo de Protocolo",
    )
    nombre       = models.CharField(max_length=250, verbose_name="Nombre del Protocolo")
    descripcion  = models.TextField(blank=True, verbose_name="Descripción")
    version      = models.CharField(max_length=20, default="1.0", verbose_name="Versión")
    activo       = models.BooleanField(default=True)
    nivel_requerido = models.CharField(
        max_length=20, choices=NIVEL_AUTORIZACION_CHOICES, default='TODOS',
        verbose_name="Nivel mínimo para ejecutar",
    )
    aplica_a_perfil = models.CharField(
        max_length=20, choices=NIVEL_AUTORIZACION_CHOICES, default='TODOS',
        verbose_name="Perfil al que aplica el BLOQUEO",
        help_text="Usuarios en este perfil o inferior serán bloqueados si no "
                  "completan este protocolo antes de acceder a la Worklist.",
    )
    bloquea_worklist = models.BooleanField(
        default=False, verbose_name="Bloquea Worklist si no se completa",
        help_text="Activo = Worklist bloqueada hasta completar este checklist hoy.",
    )
    periodicidad_dias = models.PositiveIntegerField(
        default=1, verbose_name="Periodicidad (días)",
        help_text="1=diario, 7=semanal, 30=mensual. 0=sin periodicidad.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Protocolo de Equipo"
        verbose_name_plural = "Protocolos de Equipos"
        ordering = ['equipo__equipo__nombre', 'tipo_protocolo', 'nombre']

    def __str__(self):
        equipo_str = str(self.equipo) if self.equipo else self.modelo_equipo or "Global"
        return f"[{self.get_tipo_protocolo_display()}] {self.nombre} — {equipo_str}"


class PasoProtocolo(models.Model):
    """
    Paso individual dentro de un ProtocoloEquipo.
    Construido desde el Wizard visual.
    """
    protocolo      = models.ForeignKey(
        ProtocoloEquipo, on_delete=models.CASCADE,
        related_name="pasos", verbose_name="Protocolo",
    )
    orden          = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")
    titulo         = models.CharField(max_length=250, verbose_name="Título del Paso")
    instruccion    = models.TextField(verbose_name="Instrucción Detallada")
    tipo_validacion= models.CharField(
        max_length=15, choices=TIPO_VALIDACION_PASO_CHOICES, default='CHECKBOX',
        verbose_name="Tipo de Validación",
    )
    valor_esperado = models.CharField(
        max_length=100, blank=True,
        help_text="Ej: '36-38°C', '>500 rpm'. Si el usuario registra otro valor, se genera alerta.",
    )
    imagen         = models.ImageField(
        upload_to="mantenimiento/pasos/", blank=True, null=True,
        verbose_name="Imagen / Captura del Manual",
    )
    video_url      = models.URLField(blank=True, null=True, verbose_name="URL de video (YouTube/Drive)")
    es_critico     = models.BooleanField(
        default=False, verbose_name="Es Crítico",
        help_text="Si falla, bloquea la ejecución del protocolo.",
    )
    tiempo_estimado_seg = models.PositiveIntegerField(
        default=30, verbose_name="Tiempo estimado (segundos)",
    )
    nota_seguridad = models.CharField(
        max_length=500, blank=True, verbose_name="Nota de Seguridad",
        help_text="EPP requerido, riesgo eléctrico, etc.",
    )

    class Meta:
        verbose_name = "Paso de Protocolo"
        verbose_name_plural = "Pasos de Protocolo"
        ordering = ['protocolo', 'orden']
        unique_together = [('protocolo', 'orden')]

    def __str__(self):
        return f"Paso {self.orden}: {self.titulo}"


class ArbolDiagnostico(models.Model):
    """
    Árbol de decisión para diagnóstico y resolución de fallas.
    Construido desde el Wizard visual del Director.
    """
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="arboles_diagnostico", null=True, blank=True,
    )
    expediente = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.CASCADE,
        related_name="arboles_diagnostico", verbose_name="Equipo",
        null=True, blank=True,
        help_text="Null = árbol genérico aplicable a cualquier equipo.",
    )
    falla_descripcion = models.CharField(
        max_length=300, verbose_name="Falla / Síntoma",
        help_text="Ej: 'Alarma E-023', 'CVs de QC elevados', 'No aspira muestra'",
    )
    falla_codigo      = models.CharField(
        max_length=50, blank=True, verbose_name="Código de Error (si aplica)",
    )
    activo    = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True,
        related_name="arboles_creados",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Árbol de Diagnóstico"
        verbose_name_plural = "Árboles de Diagnóstico"
        ordering = ['falla_descripcion']

    def __str__(self):
        return f"Diag: {self.falla_descripcion}"

    def get_nodo_raiz(self):
        return self.nodos.filter(padre__isnull=True).first()


class ProcedimientoReparacion(models.Model):
    """
    Procedimiento paso a paso para una reparación o intervención técnica.
    Referenciado desde NodoDiagnostico cuando se llega a una acción concreta.
    """
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="procedimientos_reparacion", null=True, blank=True,
    )
    expediente = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="procedimientos",
    )
    titulo          = models.CharField(max_length=300, verbose_name="Título")
    tipo_componente = models.CharField(
        max_length=20, choices=TIPO_COMPONENTE_CHOICES, default='OTRO',
        verbose_name="Componente a Intervenir",
    )
    descripcion_tecnica = models.TextField(blank=True, verbose_name="Descripción Técnica")
    nivel_requerido     = models.CharField(
        max_length=20, choices=NIVEL_AUTORIZACION_CHOICES, default='QUIMICO',
        verbose_name="Nivel mínimo para ejecutar",
    )
    tiempo_estimado_min = models.PositiveIntegerField(
        default=30, verbose_name="Tiempo estimado (minutos)",
    )
    requiere_paro_equipo = models.BooleanField(
        default=True, verbose_name="Requiere paro del equipo",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Procedimiento de Reparación"
        verbose_name_plural = "Procedimientos de Reparación"
        ordering = ['titulo']

    def __str__(self):
        return self.titulo


class PasoReparacion(models.Model):
    """Paso individual dentro de un ProcedimientoReparacion."""
    procedimiento = models.ForeignKey(
        ProcedimientoReparacion, on_delete=models.CASCADE,
        related_name="pasos",
    )
    orden       = models.PositiveSmallIntegerField(default=1)
    instruccion = models.TextField(verbose_name="Instrucción")
    imagen      = models.ImageField(
        upload_to="mantenimiento/reparacion/", blank=True, null=True,
    )
    video_url   = models.URLField(blank=True, null=True)
    nota_seguridad = models.CharField(max_length=500, blank=True)

    # ── Ajuste 1: Refacción requerida — multi-silo GenericFK ──────────────
    silo_refaccion = models.CharField(
        max_length=15, choices=SILO_ORIGEN_CHOICES, blank=True, null=True,
        verbose_name="Silo de la Refacción",
    )
    refaccion_content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Tipo de Catálogo",
        help_text="Catálogo del silo: CatalogoReactivoLab, CatalogoInsumoConsultorio o CatalogoInsumoGeneral",
    )
    refaccion_object_id = models.PositiveIntegerField(null=True, blank=True)
    refaccion_item      = GenericForeignKey('refaccion_content_type', 'refaccion_object_id')
    cantidad_refaccion  = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        verbose_name="Cantidad requerida",
    )
    unidad_refaccion    = models.CharField(max_length=20, blank=True, verbose_name="Unidad")

    class Meta:
        verbose_name = "Paso de Reparación"
        verbose_name_plural = "Pasos de Reparación"
        ordering = ['procedimiento', 'orden']
        unique_together = [('procedimiento', 'orden')]

    def __str__(self):
        return f"Paso {self.orden}: {self.instruccion[:60]}"


class NodoDiagnostico(models.Model):
    """
    Nodo dentro de un ArbolDiagnostico.
    Estructura de árbol con FK a sí mismo (padre/hijo).
    """
    arbol    = models.ForeignKey(
        ArbolDiagnostico, on_delete=models.CASCADE, related_name="nodos",
    )
    padre    = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name="hijos", verbose_name="Nodo Padre",
    )
    tipo_nodo  = models.CharField(
        max_length=15, choices=TIPO_NODO_CHOICES, default='PREGUNTA',
    )
    texto      = models.TextField(
        verbose_name="Pregunta / Instrucción / Descripción",
    )
    condicion_de_padre = models.CharField(
        max_length=200, blank=True,
        help_text="Respuesta del nodo padre que lleva aquí. Ej: 'Sí', 'No', 'Error persiste'",
    )
    nivel_requerido = models.CharField(
        max_length=20, choices=NIVEL_AUTORIZACION_CHOICES, default='TODOS',
    )
    lleva_a_procedimiento = models.ForeignKey(
        ProcedimientoReparacion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="nodos_referencia",
        verbose_name="Procedimiento a ejecutar",
    )
    nivel_escalamiento = models.CharField(
        max_length=20, choices=NIVEL_ESCALAMIENTO_CHOICES, blank=True,
        help_text="Solo para nodos tipo ESCALAMIENTO.",
    )
    imagen  = models.ImageField(upload_to="mantenimiento/nodos/", blank=True, null=True)
    orden   = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Nodo de Diagnóstico"
        verbose_name_plural = "Nodos de Diagnóstico"
        ordering = ['arbol', 'padre', 'orden']

    def __str__(self):
        return f"[{self.get_tipo_nodo_display()}] {self.texto[:80]}"

    def get_hijos_ordenados(self):
        return self.hijos.all().order_by('orden')


# =============================================================================
# SUBSISTEMA B — EJECUCIÓN Y TRAZABILIDAD
# =============================================================================

class EjecucionProtocolo(models.Model):
    """
    Instancia de ejecución de un ProtocoloEquipo por un usuario específico.
    Registro forense completo: quién, cuándo, desde qué IP.
    """
    ESTADO_CHOICES = [
        ('EN_PROGRESO', 'En Progreso'),
        ('COMPLETADO',  'Completado'),
        ('ABANDONADO',  'Abandonado'),
        ('BYPASS',      'Completado con Bypass de Supervisor'),
    ]

    protocolo    = models.ForeignKey(
        ProtocoloEquipo, on_delete=models.PROTECT,
        related_name="ejecuciones",
    )
    expediente   = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.PROTECT,
        related_name="ejecuciones",
    )
    empresa      = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="ejecuciones_protocolo",
    )
    ejecutado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="ejecuciones_protocolo",
    )
    fecha_inicio  = models.DateTimeField(auto_now_add=True)
    fecha_fin     = models.DateTimeField(null=True, blank=True)
    estado        = models.CharField(
        max_length=15, choices=ESTADO_CHOICES, default='EN_PROGRESO',
    )
    ip_address    = models.GenericIPAddressField(null=True, blank=True)
    duracion_real_seg = models.PositiveIntegerField(
        default=0, verbose_name="Duración real (segundos)",
    )

    class Meta:
        verbose_name = "Ejecución de Protocolo"
        verbose_name_plural = "Ejecuciones de Protocolos"
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['empresa', '-fecha_inicio']),
            models.Index(fields=['ejecutado_por', '-fecha_inicio']),
            models.Index(fields=['expediente', '-fecha_inicio']),
        ]

    def __str__(self):
        return f"{self.protocolo.nombre} — {self.ejecutado_por} [{self.get_estado_display()}]"

    def completar(self):
        self.fecha_fin = timezone.now()
        delta = self.fecha_fin - self.fecha_inicio
        self.duracion_real_seg = int(delta.total_seconds())
        self.estado = 'COMPLETADO'
        self.save(update_fields=['fecha_fin', 'duracion_real_seg', 'estado'])


class RespuestaPasoProtocolo(models.Model):
    """Respuesta capturada para un PasoProtocolo dentro de una EjecucionProtocolo."""
    ejecucion      = models.ForeignKey(
        EjecucionProtocolo, on_delete=models.CASCADE,
        related_name="respuestas",
    )
    paso           = models.ForeignKey(
        PasoProtocolo, on_delete=models.CASCADE,
        related_name="respuestas",
    )
    validado       = models.BooleanField(default=False)
    respuesta_texto = models.CharField(max_length=500, blank=True)
    respuesta_valor = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True,
    )
    foto           = models.ImageField(
        upload_to="mantenimiento/respuestas/", blank=True, null=True,
    )
    observacion    = models.CharField(max_length=500, blank=True)
    timestamp      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Respuesta de Paso"
        verbose_name_plural = "Respuestas de Pasos"
        unique_together = [('ejecucion', 'paso')]

    def __str__(self):
        return f"Paso {self.paso.orden} — {'✓' if self.validado else '✗'}"


class BypassChecklistAutorizacion(models.Model):
    """
    ── Ajuste 3: BOTÓN DE EMERGENCIA / SUPERVISIÓN DIRECTA ──
    Permite a un experto (supervisor) autorizar que un novato
    omita el checklist completo, registrando quién autorizó.
    El nivel del autorizante debe ser mayor al del ejecutante.
    """
    ejecucion    = models.OneToOneField(
        EjecucionProtocolo, on_delete=models.CASCADE,
        related_name="bypass_autorizacion",
    )
    ejecutado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="bypasses_recibidos", verbose_name="Novato / Ejecutante",
    )
    autorizado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="bypasses_otorgados", verbose_name="Supervisor Autorizante",
    )
    motivo        = models.TextField(
        verbose_name="Motivo de la omisión",
        help_text="Ej: 'Urgencia clínica', 'Paciente crítico en espera'",
    )
    pin_verificado = models.BooleanField(
        default=False, verbose_name="PIN del supervisor verificado",
    )
    fecha         = models.DateTimeField(auto_now_add=True)
    ip_autorizacion = models.GenericIPAddressField(null=True, blank=True)
    pasos_omitidos  = models.PositiveSmallIntegerField(
        default=0, verbose_name="Cantidad de pasos omitidos",
    )

    class Meta:
        verbose_name = "Bypass de Checklist (Supervisión Directa)"
        verbose_name_plural = "Bypasses de Checklists"
        ordering = ['-fecha']

    def __str__(self):
        return (f"Bypass: {self.ejecutado_por} autorizado por "
                f"{self.autorizado_por} [{self.fecha.date()}]")


class TicketMantenimientoCMMS(models.Model):
    """
    Ticket central del CMMS.
    Creado automáticamente desde: checklist, árbol diagnóstico,
    alerta QC (Westgard), o manualmente por el Director.
    """
    TIPO_ORIGEN_CHOICES = [
        ('CHECKLIST',    'Detectado en Checklist Diario'),
        ('DIAGNOSTICO',  'Diagnóstico por Árbol de Decisión'),
        ('QC_TRIGGERED', 'Disparado por Falla en QC (Westgard)'),
        ('MANUAL',       'Creado Manualmente'),
        ('PREVENTIVO',   'Mantenimiento Preventivo Programado'),
    ]

    empresa       = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="tickets_cmms",
    )
    expediente    = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.PROTECT,
        related_name="tickets",
    )
    tipo_origen   = models.CharField(
        max_length=15, choices=TIPO_ORIGEN_CHOICES, default='MANUAL',
    )
    titulo        = models.CharField(max_length=300, verbose_name="Título / Síntoma")
    descripcion   = models.TextField(blank=True, verbose_name="Descripción Detallada")
    estado        = models.CharField(
        max_length=15, choices=ESTADO_TICKET_CHOICES, default='ABIERTO',
    )
    nivel_escalamiento_actual = models.CharField(
        max_length=20, choices=NIVEL_ESCALAMIENTO_CHOICES,
        default='QUIMICO', verbose_name="Nivel de Escalamiento Actual",
    )
    autorizado_por_director = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets_autorizados_director",
        verbose_name="Director que autorizó escalamiento externo",
        help_text="Requerido solo si nivel_escalamiento = PROVEEDOR.",
    )

    # Vínculos a ejecuciones
    ejecucion_protocolo    = models.ForeignKey(
        EjecucionProtocolo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets_generados",
    )
    nodo_diagnostico_final = models.ForeignKey(
        NodoDiagnostico, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets_generados",
        verbose_name="Nodo final del árbol de diagnóstico",
    )

    creado_por    = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="tickets_cmms_creados",
    )
    asignado_a    = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets_cmms_asignados",
    )
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre   = models.DateTimeField(null=True, blank=True)
    tiempo_resolucion_min = models.PositiveIntegerField(
        default=0, verbose_name="Tiempo de resolución (minutos)",
    )
    resolucion_descripcion = models.TextField(
        blank=True, verbose_name="Descripción de la Resolución",
    )

    class Meta:
        verbose_name = "Ticket de Mantenimiento (CMMS)"
        verbose_name_plural = "Tickets de Mantenimiento (CMMS)"
        ordering = ['-fecha_apertura']
        indexes = [
            models.Index(fields=['empresa', '-fecha_apertura']),
            models.Index(fields=['expediente', 'estado']),
        ]

    def __str__(self):
        return f"Ticket #{self.pk} — {self.titulo[:80]} [{self.get_estado_display()}]"

    def clean(self):
        # Regla de Autonomía: escalar a proveedor requiere firma de Director
        if self.nivel_escalamiento_actual == 'PROVEEDOR' and not self.autorizado_por_director_id:
            raise ValidationError(
                "No se puede escalar a Proveedor Externo sin autorización del Director."
            )

    def cerrar(self, descripcion_resolucion=""):
        self.estado = 'CERRADO'
        self.fecha_cierre = timezone.now()
        delta = self.fecha_cierre - self.fecha_apertura
        self.tiempo_resolucion_min = int(delta.total_seconds() / 60)
        self.resolucion_descripcion = descripcion_resolucion
        self.save(update_fields=[
            'estado', 'fecha_cierre',
            'tiempo_resolucion_min', 'resolucion_descripcion',
        ])


class SalidaRefaccionMantenimiento(models.Model):
    """
    ── Ajuste 1: MULTI-SILO via GenericForeignKey ──
    Descuento de refacción/insumo de CUALQUIER silo de inventario
    al ejecutar un mantenimiento.

    content_type puede apuntar a:
      - inventario.LoteReactivoLab      → Silo Lab
      - inventario.LoteInsumoConsultorio → Silo Consultorio
      - inventario.LoteInsumoGeneral    → Silo Generales

    La señal post_save descuenta automáticamente el stock del lote correcto.
    """
    empresa      = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="salidas_refaccion_mantenimiento",
    )
    ticket       = models.ForeignKey(
        TicketMantenimientoCMMS, on_delete=models.PROTECT,
        related_name="salidas_refaccion",
    )
    silo_origen  = models.CharField(
        max_length=15, choices=SILO_ORIGEN_CHOICES,
        verbose_name="Silo de Inventario",
    )

    # GenericFK al lote del silo correspondiente
    lote_content_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT,
        verbose_name="Tipo de Lote",
    )
    lote_object_id    = models.PositiveIntegerField(verbose_name="ID del Lote")
    lote              = GenericForeignKey('lote_content_type', 'lote_object_id')

    cantidad_usada    = models.DecimalField(
        max_digits=10, decimal_places=4,
        verbose_name="Cantidad Utilizada",
    )
    unidad            = models.CharField(max_length=20, blank=True)
    paso_reparacion   = models.ForeignKey(
        PasoReparacion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="salidas_registradas",
        verbose_name="Paso de reparación origen",
    )
    registrado_por    = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="salidas_refaccion_registradas",
    )
    fecha             = models.DateTimeField(auto_now_add=True)
    observacion       = models.CharField(max_length=300, blank=True)
    costo_unitario_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name="Costo Unitario Congelado"
    )
    costo_total_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Costo Total Congelado"
    )
    stock_anterior_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        verbose_name="Stock Anterior Congelado"
    )
    stock_resultante_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        verbose_name="Stock Resultante Congelado"
    )

    class Meta:
        verbose_name = "Salida de Refacción (Mantenimiento)"
        verbose_name_plural = "Salidas de Refacciones (Mantenimiento)"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['empresa', '-fecha']),
            models.Index(fields=['ticket']),
        ]

    def __str__(self):
        return (f"Refacción {self.cantidad_usada} [{self.silo_origen}] "
                f"— Ticket #{self.ticket_id}")


# =============================================================================
# SUBSISTEMA D — TCO Y WAR ROOM
# =============================================================================

class RegistroTCO(models.Model):
    """
    Registro mensual de Costo Total de Propiedad por equipo.
    Generado por management command mensual (o Celery).
    Alimenta el panel del War Room del Director.
    """
    empresa      = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="registros_tco",
    )
    expediente   = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.PROTECT,
        related_name="registros_tco",
    )
    periodo_mes  = models.PositiveSmallIntegerField(verbose_name="Mes")
    periodo_anio = models.PositiveSmallIntegerField(verbose_name="Año")

    # Métricas del período
    costo_refacciones   = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name="Costo en Refacciones ($)",
    )
    horas_inactividad   = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="Horas de Inactividad",
    )
    pruebas_procesadas  = models.PositiveIntegerField(
        default=0, verbose_name="Pruebas procesadas en el período",
    )
    tickets_abiertos    = models.PositiveSmallIntegerField(default=0)
    tickets_resueltos   = models.PositiveSmallIntegerField(default=0)
    tiempo_resolucion_promedio_min = models.PositiveIntegerField(default=0)

    # Métrica calculada
    costo_por_prueba    = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        verbose_name="Costo por Prueba ($)",
        help_text="costo_refacciones / pruebas_procesadas",
    )

    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro TCO"
        verbose_name_plural = "Registros TCO"
        unique_together = [('empresa', 'expediente', 'periodo_mes', 'periodo_anio')]
        ordering = ['-periodo_anio', '-periodo_mes']

    def __str__(self):
        return (f"TCO {self.expediente.equipo} — "
                f"{self.periodo_mes:02d}/{self.periodo_anio}")

    def calcular_costo_por_prueba(self):
        if self.pruebas_procesadas > 0:
            self.costo_por_prueba = self.costo_refacciones / self.pruebas_procesadas
        else:
            self.costo_por_prueba = 0
        self.save(update_fields=['costo_por_prueba'])


# =============================================================================
# SUBSISTEMA E — METROLOGÍA: Certificados de Calibración / Calificación IQ/OQ/PQ
# =============================================================================

class CertificadoMetrologia(models.Model):
    """
    Repositorio legal de certificados de calibración, calificación (IQ/OQ/PQ)
    y verificación de equipos de laboratorio.

    ISO 15189 §6.4.3 — Los equipos deben calibrarse o verificarse con intervalos
    definidos. Este modelo garantiza la trazabilidad documental exigida por
    COFEPRIS e ISO 15189 durante auditorías.

    Alertas automáticas: el management command `check_certificados_metrologicos`
    revisa diariamente y dispara NotificacionDiscrepancia al Director 30 días
    antes del vencimiento.
    """
    TIPO_CHOICES = [
        ('CALIBRACION',    'Calibración Metrológica'),
        ('CALIFICACION_IQ','Calificación de Instalación (IQ)'),
        ('CALIFICACION_OQ','Calificación de Operación (OQ)'),
        ('CALIFICACION_PQ','Calificación de Desempeño (PQ)'),
        ('VERIFICACION',   'Verificación Periódica'),
        ('MANTENIMIENTO_PREVENTIVO', 'Mantenimiento Preventivo Certificado'),
    ]
    ESTADO_CHOICES = [
        ('VIGENTE',  'Vigente'),
        ('POR_VENCER','Por Vencer (≤30 días)'),
        ('VENCIDO',  'Vencido'),
        ('RENOVADO', 'Renovado / Sustituido'),
    ]

    empresa    = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="certificados_metrologia", verbose_name="Empresa",
    )
    expediente = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.CASCADE,
        related_name="certificados", verbose_name="Equipo",
    )
    tipo           = models.CharField(max_length=30, choices=TIPO_CHOICES,
                                       verbose_name="Tipo de Certificado")
    numero_certificado = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Número / Folio del Certificado",
    )
    laboratorio_emisor = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Laboratorio / Entidad Emisora",
    )
    fecha_emision  = models.DateField(verbose_name="Fecha de Emisión")
    fecha_vencimiento = models.DateField(verbose_name="Fecha de Vencimiento")
    estado         = models.CharField(max_length=15, choices=ESTADO_CHOICES,
                                       default="VIGENTE", verbose_name="Estado")

    # Documento PDF del certificado
    archivo_pdf    = models.FileField(
        upload_to="metrologia/certificados/",
        blank=True, null=True, verbose_name="Archivo PDF del Certificado",
    )
    observaciones  = models.TextField(blank=True, null=True)

    # Trazabilidad
    registrado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="certificados_registrados", verbose_name="Registrado por",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Flag: ¿ya se envió la alerta de próximo vencimiento?
    alerta_30d_enviada = models.BooleanField(
        default=False,
        verbose_name="Alerta 30 días enviada",
        help_text="Marca automática del cron para evitar alertas duplicadas.",
    )

    class Meta:
        verbose_name = "Certificado de Metrología"
        verbose_name_plural = "Certificados de Metrología"
        ordering = ["fecha_vencimiento"]
        indexes = [
            models.Index(fields=["empresa", "estado", "fecha_vencimiento"]),
            models.Index(fields=["expediente", "tipo"]),
        ]

    def __str__(self):
        return (f"{self.get_tipo_display()} — {self.expediente.equipo} "
                f"| Vence: {self.fecha_vencimiento:%d/%m/%Y}")

    def actualizar_estado(self):
        """Actualiza el campo estado según fecha de vencimiento vs hoy."""
        from datetime import date
        hoy = date.today()
        if self.fecha_vencimiento < hoy:
            self.estado = 'VENCIDO'
        elif (self.fecha_vencimiento - hoy).days <= 30:
            self.estado = 'POR_VENCER'
        else:
            self.estado = 'VIGENTE'
        self.save(update_fields=['estado'])


# =============================================================================
# SUBSISTEMA F — TELEMETRÍA IoT: Sensores de Temperatura / Humedad
# =============================================================================

class SensorIoT(models.Model):
    """
    Registro de un sensor físico (Temp/Hum/CO2) vinculado a un equipo
    o área de la instalación.

    Los sensores envían lecturas vía API REST (/api/iot/lectura/) o pueden
    cargarse manualmente. El campo `activo` sirve como kill-switch.
    """
    TIPO_CHOICES = [
        ('TEMPERATURA',         'Temperatura (°C)'),
        ('HUMEDAD',             'Humedad Relativa (%)'),
        ('TEMPERATURA_HUMEDAD', 'Temperatura + Humedad'),
        ('CO2',                 'CO2 (ppm)'),
    ]

    empresa    = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="sensores_iot", verbose_name="Empresa",
    )
    expediente = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sensores", verbose_name="Equipo Vinculado",
        help_text="Equipo al que está físicamente instalado este sensor.",
    )
    codigo     = models.CharField(max_length=50, verbose_name="Código / Serial del Sensor")
    nombre     = models.CharField(max_length=150, verbose_name="Nombre / Ubicación")
    tipo       = models.CharField(max_length=25, choices=TIPO_CHOICES, verbose_name="Tipo")
    activo     = models.BooleanField(default=True, verbose_name="Activo")

    # Rangos de operación aceptables (ISO 15189 §6.4)
    temp_min_aceptable  = models.DecimalField(
        max_digits=5, decimal_places=1, default=2.0,
        verbose_name="Temperatura Mínima Aceptable (°C)",
    )
    temp_max_aceptable  = models.DecimalField(
        max_digits=5, decimal_places=1, default=8.0,
        verbose_name="Temperatura Máxima Aceptable (°C)",
    )
    hum_min_aceptable   = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        verbose_name="Humedad Mínima Aceptable (%)",
    )
    hum_max_aceptable   = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        verbose_name="Humedad Máxima Aceptable (%)",
    )

    fecha_instalacion = models.DateField(null=True, blank=True)
    notas             = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Sensor IoT"
        verbose_name_plural = "Sensores IoT"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo"],
                name="mantenimiento_sensoriot_empresa_codigo_uniq",
            )
        ]

    def __str__(self):
        return f"{self.codigo} — {self.nombre} ({self.get_tipo_display()})"


class LecturaSensorIoT(models.Model):
    """
    Lectura individual de un SensorIoT.

    Lógica de alerta automática (ejecutada en el signal post_save):
      Si temperatura > temp_max_aceptable OR temperatura < temp_min_aceptable:
        → Se crea automáticamente un TicketMantenimientoCMMS de PRIORIDAD CRITICA.
        → Se genera una NotificacionDiscrepancia al Director.
        → El flag `fuera_de_rango` se marca True para trazabilidad forense.
    """
    sensor      = models.ForeignKey(
        SensorIoT, on_delete=models.PROTECT,
        related_name="lecturas", verbose_name="Sensor",
    )
    empresa     = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="lecturas_sensor", verbose_name="Empresa",
    )
    timestamp   = models.DateTimeField(default=timezone.now, verbose_name="Fecha/Hora Lectura",
                                        db_index=True)

    temperatura = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        verbose_name="Temperatura (°C)",
    )
    humedad     = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        verbose_name="Humedad Relativa (%)",
    )

    fuera_de_rango    = models.BooleanField(default=False, verbose_name="Fuera de Rango",
                                             db_index=True)
    ticket_generado   = models.ForeignKey(
        "mantenimiento.TicketMantenimientoCMMS",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lecturas_detonadoras",
        verbose_name="Ticket Generado por esta Lectura",
    )
    origen      = models.CharField(
        max_length=10,
        choices=[('API', 'API REST (IoT)'), ('MANUAL', 'Captura Manual')],
        default='API', verbose_name="Origen",
    )

    class Meta:
        verbose_name = "Lectura de Sensor IoT"
        verbose_name_plural = "Lecturas de Sensores IoT"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["sensor", "-timestamp"]),
            models.Index(fields=["empresa", "fuera_de_rango", "-timestamp"]),
        ]

    def __str__(self):
        t = f"{self.temperatura}°C" if self.temperatura is not None else "—"
        h = f"{self.humedad}%" if self.humedad is not None else "—"
        return f"{self.sensor.codigo} @ {self.timestamp:%d/%m %H:%M} | T:{t} H:{h}"


# =============================================================================
# SUBSISTEMA G — INTERFACES LIS: InCCA (CSV Folder Drop)
# =============================================================================


class InCCAInterfaceConfig(models.Model):
    """Configuración de conectividad InCCA por carpetas (CSV bidireccional)."""

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="incca_configs",
        verbose_name="Empresa",
    )
    expediente = models.OneToOneField(
        ExpedienteEquipo,
        on_delete=models.CASCADE,
        related_name="incca_config",
        verbose_name="Equipo (Expediente)",
    )

    habilitado = models.BooleanField(default=False, verbose_name="Habilitado")

    # InCCA Registry defaults:
    # INPUTFILTER (*.csv) / INPUTPATH (input) / OUTPUTPATH (output) / OUTPUTPREFIX (hostq_)
    input_path = models.CharField(max_length=500, blank=True, default="input", verbose_name="Carpeta INPUT")
    output_path = models.CharField(max_length=500, blank=True, default="output", verbose_name="Carpeta OUTPUT")
    input_filter = models.CharField(max_length=100, blank=True, default="*.csv", verbose_name="Filtro INPUT")
    output_prefix = models.CharField(max_length=100, blank=True, default="hostq_", verbose_name="Prefijo OUTPUT")
    dont_delete_input = models.BooleanField(default=True, verbose_name="No borrar INPUT")

    # Operación
    poll_interval_sec = models.PositiveIntegerField(default=60, verbose_name="Intervalo de polling (seg)")
    last_inputdate_seen = models.DateTimeField(null=True, blank=True, verbose_name="Último INPUTDATE observado")
    last_output_scan = models.DateTimeField(null=True, blank=True, verbose_name="Último escaneo OUTPUT")

    # Trazabilidad
    creado_por = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incca_configs_creadas",
        verbose_name="Creado por",
    )
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Config InCCA (CSV)"
        verbose_name_plural = "Configs InCCA (CSV)"
        indexes = [
            models.Index(fields=["empresa", "habilitado"]),
        ]

    def __str__(self):
        return f"InCCA: {self.expediente.equipo} [{self.empresa}]"


class InCCAFileEvent(models.Model):
    """Bitácora de archivos procesados para idempotencia y auditoría forense."""

    DIRECTION_CHOICES = [
        ("IN", "Input (LIS→InCCA)"),
        ("OUT", "Output (InCCA→LIS)"),
    ]
    STATUS_CHOICES = [
        ("DETECTADO", "Detectado"),
        ("PROCESADO", "Procesado"),
        ("ERROR", "Error"),
        ("IGNORADO", "Ignorado"),
    ]

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="incca_file_events",
        verbose_name="Empresa",
    )
    config = models.ForeignKey(
        InCCAInterfaceConfig,
        on_delete=models.CASCADE,
        related_name="file_events",
        verbose_name="Config",
    )

    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES, default="OUT")
    filename = models.CharField(max_length=260, verbose_name="Archivo")
    full_path = models.CharField(max_length=800, blank=True, default="", verbose_name="Ruta completa")
    file_mtime = models.DateTimeField(null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)

    sha256 = models.CharField(max_length=64, blank=True, default="", db_index=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="DETECTADO")
    error = models.TextField(blank=True, default="")
    raw_preview = models.TextField(blank=True, default="")

    detected_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Evento InCCA (archivo)"
        verbose_name_plural = "Eventos InCCA (archivos)"
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["empresa", "direction", "status", "-detected_at"]),
            models.Index(fields=["config", "direction", "filename"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["config", "direction", "filename", "sha256"],
                name="mantenimiento_incca_fileevent_config_dir_file_hash_uniq",
            )
        ]

    def __str__(self):
        return f"{self.get_direction_display()} {self.filename} ({self.status})"

    @staticmethod
    def compute_sha256_bytes(b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()


class InCCAOutputRowStaging(models.Model):
    """Staging de filas de salida InCCA (CSV) aún no mapeadas 1:1 a Orden/Estudio."""

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="incca_output_rows",
        verbose_name="Empresa",
    )
    file_event = models.ForeignKey(
        InCCAFileEvent,
        on_delete=models.CASCADE,
        related_name="rows",
        verbose_name="Archivo",
    )

    row_index = models.PositiveIntegerField(default=0)
    process_number = models.CharField(max_length=80, blank=True, default="")
    order_number = models.CharField(max_length=80, blank=True, default="", db_index=True)
    method_name = models.CharField(max_length=200, blank=True, default="")
    pid = models.CharField(max_length=120, blank=True, default="")
    report = models.TextField(blank=True, default="")
    raw_fields_json = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fila InCCA (staging)"
        verbose_name_plural = "Filas InCCA (staging)"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["empresa", "order_number", "-created_at"]),
        ]

    def __str__(self):
        return f"InCCA row order={self.order_number} method={self.method_name}"
