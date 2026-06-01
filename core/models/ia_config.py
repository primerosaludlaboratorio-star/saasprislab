"""
core/models/ia_config.py
Modelos de Gobernanza de IA para PRISLAB SaaS.

  UsoRecursosIA  — Contador forense de tokens consumidos por empresa y proceso.
  ReglaLocalIA   — Caché de inteligencia: reglas aprendidas y aprobadas por el QFB,
                   con costo $0 en consultas futuras (evita llamar a la API externa).
"""
from django.db import models
from django.utils import timezone


class UsoRecursosIA(models.Model):
    """
    Registra cada llamada a la API de Gemini por empresa.
    Permite calcular el consumo mensual, detectar anomalías y enviar alertas
    cuando se acerca al límite contratado.
    """
    TIPO_PROCESO_CHOICES = [
        ('NLP_TOMA',        'NLP Checklist — Toma de Muestra'),
        ('RESUMEN_CLINICO',  'Resumen Clínico (Dictado / SOAP)'),
        ('RAG_CONSULTA',     'RAG — Consulta de Manuales'),
        ('OCR_DOCUMENTO',    'OCR — Lectura de Documento'),
        ('MARKETING_IA',     'IA Marketing / Campañas'),
        ('WORKLIST_SUGERENCIA', 'Sugerencia Worklist / Delta Check'),
        ('QC_ANALISIS',      'Análisis QC / Westgard'),
        ('OTRO',             'Otro'),
    ]
    FUENTE_KEY_CHOICES = [
        ('BYOK',   'BYOK — API Key propia del laboratorio'),
        ('MASTER', 'MASTER — API Key compartida de PRISLAB'),
        ('LOCAL',  'LOCAL — Respuesta de caché / regla local (sin costo)'),
    ]

    empresa       = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        related_name='uso_recursos_ia', verbose_name="Empresa",
    )
    fecha         = models.DateField(default=timezone.localdate, db_index=True,
                                     verbose_name="Fecha")
    tipo_proceso  = models.CharField(max_length=30, choices=TIPO_PROCESO_CHOICES,
                                     default='OTRO', verbose_name="Tipo de Proceso")
    tokens_entrada = models.PositiveIntegerField(default=0, verbose_name="Tokens de Entrada")
    tokens_salida  = models.PositiveIntegerField(default=0, verbose_name="Tokens de Salida")
    tokens_total   = models.PositiveIntegerField(default=0, verbose_name="Tokens Totales",
                                                 help_text="Suma entrada + salida")
    fuente_key    = models.CharField(max_length=10, choices=FUENTE_KEY_CHOICES,
                                     default='MASTER', verbose_name="Fuente de API Key")
    modelo_usado  = models.CharField(max_length=60, blank=True, default='',
                                     verbose_name="Modelo Gemini usado")
    latencia_ms   = models.PositiveIntegerField(default=0, verbose_name="Latencia (ms)")
    usuario_id    = models.IntegerField(null=True, blank=True,
                                        verbose_name="ID Usuario que disparó la llamada")
    referencia    = models.CharField(max_length=200, blank=True, default='',
                                     verbose_name="Referencia (ID Orden / Estudio / etc.)")
    timestamp     = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp exacto")

    class Meta:
        app_label = 'core'
        verbose_name = "Uso de Recursos IA"
        verbose_name_plural = "Uso de Recursos IA"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['empresa', 'fecha'], name='ix_uso_ia_empresa_fecha'),
            models.Index(fields=['empresa', 'tipo_proceso'], name='ix_uso_ia_proceso'),
        ]

    def save(self, *args, **kwargs):
        self.tokens_total = self.tokens_entrada + self.tokens_salida
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.empresa.nombre} | {self.get_tipo_proceso_display()} | "
            f"{self.tokens_total} tok | {self.fecha}"
        )


class ReglaLocalIA(models.Model):
    """
    Caché de Inteligencia — Reglas aprendidas y aprobadas por el QFB.

    Flujo:
      1. PRIS analiza un proceso y genera una sugerencia (estado=PROPUESTA).
      2. El QFB revisa y da clic en "Aprobar Regla" (estado=APROBADA).
      3. Consultas futuras para el mismo proceso/contexto se resuelven desde
         esta tabla (costo $0 — fuente_key='LOCAL').
      4. El QFB puede desactivar o actualizar una regla en cualquier momento.
    """
    ESTADO_PROPUESTA  = 'PROPUESTA'
    ESTADO_APROBADA   = 'APROBADA'
    ESTADO_RECHAZADA  = 'RECHAZADA'
    ESTADO_OBSOLETA   = 'OBSOLETA'
    ESTADO_CHOICES = [
        (ESTADO_PROPUESTA, '⏳ Propuesta — Pendiente de revisión QFB'),
        (ESTADO_APROBADA,  '✅ Aprobada — Activa en producción'),
        (ESTADO_RECHAZADA, '❌ Rechazada — No usar'),
        (ESTADO_OBSOLETA,  '🗄️ Obsoleta — Reemplazada por versión más nueva'),
    ]
    AMBITO_CHOICES = [
        ('CHECKLIST_TOMA',    'Checklist Toma de Muestra'),
        ('DELTA_CHECK',       'Delta Check / Alerta de Resultado'),
        ('QC_WESTGARD',       'Control de Calidad Westgard'),
        ('DIAGNOSTICO_SUGERIDO', 'Diagnóstico Sugerido'),
        ('CROSS_SELLING',     'Venta Cruzada / Cross-selling'),
        ('OTRO',              'Otro'),
    ]

    empresa       = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        related_name='reglas_locales_ia', verbose_name="Empresa",
    )
    ambito        = models.CharField(max_length=30, choices=AMBITO_CHOICES,
                                     default='OTRO', verbose_name="Ámbito de la Regla")
    clave         = models.CharField(
        max_length=255, db_index=True,
        verbose_name="Clave de Búsqueda",
        help_text=(
            "Identificador canónico para matchear esta regla, p. ej. "
            "'CHECKLIST:AYUNO:GLUCOSA_EN_AYUNO' o 'DELTA:GLUCOSA:>500'. "
            "Se normaliza a lowercase sin tildes."
        ),
    )
    contexto_original = models.TextField(
        verbose_name="Contexto Original",
        help_text="Texto / transcripción que originó esta regla.",
    )
    respuesta_ia  = models.TextField(
        verbose_name="Respuesta IA Original",
        help_text="Texto que PRIS-IA generó y que el QFB aprobó.",
    )
    respuesta_local = models.TextField(
        blank=True,
        verbose_name="Respuesta Local (Override del QFB)",
        help_text="Si el QFB ajustó la respuesta, se guarda aquí. Tiene prioridad.",
    )
    estado        = models.CharField(max_length=15, choices=ESTADO_CHOICES,
                                     default=ESTADO_PROPUESTA, verbose_name="Estado")
    confianza     = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.80,
        verbose_name="Umbral de Confianza",
        help_text="Similarity score mínimo para aplicar esta regla automáticamente (0.0–1.0).",
    )
    veces_usada   = models.PositiveIntegerField(default=0, verbose_name="Veces usada en producción")
    tokens_ahorrados = models.PositiveIntegerField(
        default=0, verbose_name="Tokens Ahorrados",
        help_text="Acumulado de tokens que se habrían gastado sin esta regla.",
    )

    aprobado_por  = models.ForeignKey(
        'core.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reglas_aprobadas', verbose_name="Aprobado por (QFB)",
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True,
                                            verbose_name="Fecha de Aprobación")
    fecha_creacion   = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Regla Local IA"
        verbose_name_plural = "Reglas Locales IA"
        ordering = ['-fecha_modificacion']
        unique_together = [('empresa', 'ambito', 'clave')]
        indexes = [
            models.Index(fields=['empresa', 'ambito', 'estado'],
                         name='ix_regla_ia_empresa_ambito'),
        ]

    def aprobar(self, usuario):
        """Aprueba la regla para producción."""
        self.estado = self.ESTADO_APROBADA
        self.aprobado_por = usuario
        self.fecha_aprobacion = timezone.now()
        self.save(update_fields=['estado', 'aprobado_por', 'fecha_aprobacion', 'fecha_modificacion'])

    def registrar_uso(self, tokens_estimados: int = 500):
        """Incrementa el contador de uso y acumula tokens ahorrados."""
        ReglaLocalIA.objects.filter(pk=self.pk).update(
            veces_usada=models.F('veces_usada') + 1,
            tokens_ahorrados=models.F('tokens_ahorrados') + tokens_estimados,
        )

    def respuesta_efectiva(self) -> str:
        """Retorna la respuesta local si existe, sino la respuesta IA original."""
        return self.respuesta_local.strip() or self.respuesta_ia.strip()

    def __str__(self):
        return f"[{self.get_estado_display()}] {self.get_ambito_display()} — {self.clave[:60]}"
