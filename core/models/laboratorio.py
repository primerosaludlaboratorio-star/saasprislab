"""
core/models/laboratorio.py
Módulo de laboratorio clínico: Órdenes, Resultados, Toma de Muestra, Maquila.
Depende de: base.py, catalogos.py, pacientes.py
FKs a Paciente, Medico y modelos lims (Analito, PerfilLims, PaqueteLims).
"""
from django.db import models
import uuid

from core.tenant import TenantModel
from core.validators import validate_image_upload, validate_document_upload
from .base import Empresa, Sucursal, Usuario, get_google_drive_storage


# ==============================================================================
# 9. LABORATORIO - TOMA DE MUESTRA / MAQUILA / BITÁCORAS
# ==============================================================================
class TomaMuestra(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="tomas_muestra")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, related_name="tomas_muestra")
    orden = models.OneToOneField("OrdenDeServicio", on_delete=models.CASCADE, related_name="toma_muestra")
    tomada_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="tomas_muestra_realizadas")
    fecha_toma = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True, null=True)

    # ── Flujo de cubículo (Preparación + Extracción) ──────────────────────
    hora_inicio_extraccion = models.DateTimeField(
        null=True, blank=True, verbose_name="Hora Inicio Extracción",
        help_text="Timestamp en que el flebotomista pulsó INICIAR TOMA")
    hora_fin_extraccion = models.DateTimeField(
        null=True, blank=True, verbose_name="Hora Fin Extracción",
        help_text="Timestamp en que se pulsó FINALIZAR Y ENVIAR")
    duracion_extraccion_seg = models.IntegerField(
        null=True, blank=True, verbose_name="Duración Extracción (seg)")

    # ── Checklist de seguridad ────────────────────────────────────────────
    identidad_verificada = models.BooleanField(
        default=False, verbose_name="Identidad Verificada",
        help_text="Flebotomista confirmó identidad del paciente antes de la extracción")
    ayuno_confirmado = models.BooleanField(
        default=False, verbose_name="Ayuno Confirmado",
        help_text="Paciente confirmó condición de ayuno cuando aplica")
    consentimiento_firmado = models.BooleanField(
        default=False, verbose_name="Consentimiento Firmado",
        help_text="Consentimiento informado firmado digitalmente")

    # ── Notas generadas por PRIS-IA ───────────────────────────────────────
    notas_ia = models.TextField(
        blank=True, null=True, verbose_name="Notas PRIS-IA",
        help_text="Observaciones clínicas generadas automáticamente durante la grabación")

    class Meta:
        app_label = 'core'
        verbose_name = "Toma de Muestra"
        verbose_name_plural = "Tomas de Muestra"
        ordering = ["-fecha_toma"]


class AudioTomaMuestra(models.Model):
    """
    Grabación de audio de la sesión de toma de muestra (Caja Negra Flebotomía).
    El audio se cifra con AES-256 (Fernet) en el backend antes de persistirse.
    Acceso restringido: solo rol DIRECTOR_QC bajo motivo documentado.
    """
    toma = models.OneToOneField(
        TomaMuestra, on_delete=models.CASCADE, related_name='audio',
        verbose_name="Toma de Muestra")
    # Audio almacenado cifrado (Fernet). BinaryField evita accidentalmente
    # exponer el contenido a través del ORM en queries de texto.
    audio_cifrado = models.BinaryField(
        null=True, blank=True, verbose_name="Audio Cifrado (Fernet/AES-256)")
    hash_sha256 = models.CharField(
        max_length=64, blank=True, verbose_name="Hash SHA-256 del audio original",
        help_text="Integridad forense: hash del audio ANTES de cifrar")
    duracion_segundos = models.IntegerField(default=0, verbose_name="Duración (seg)")
    formato = models.CharField(max_length=10, default='webm', verbose_name="Formato")
    timestamp_inicio = models.DateTimeField(null=True, blank=True, verbose_name="Inicio Grabación")
    timestamp_fin = models.DateTimeField(null=True, blank=True, verbose_name="Fin Grabación")
    transcripcion_ia = models.TextField(
        blank=True, verbose_name="Transcripción PRIS-IA",
        help_text="Texto transcrito en tiempo real por el motor NLP")
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    # ── Auditoría de acceso ───────────────────────────────────────────────
    accedido_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audios_toma_accedidos',
        verbose_name="Último acceso por")
    fecha_ultimo_acceso = models.DateTimeField(null=True, blank=True)
    motivo_acceso = models.TextField(
        blank=True, verbose_name="Motivo de Acceso Justificado",
        help_text="Solo DIRECTOR_QC. Debe registrar el motivo antes de descargar")

    class Meta:
        app_label = 'core'
        verbose_name = "Audio Toma de Muestra"
        verbose_name_plural = "Audios Toma de Muestra"
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"Audio toma — Orden {self.toma.orden_id}"


class EnvioMaquila(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="envios_maquila")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, related_name="envios_maquila")
    laboratorio_externo = models.CharField(max_length=255)
    guia_rastreo = models.CharField(max_length=120, blank=True, null=True)
    ordenes = models.ManyToManyField("OrdenDeServicio", related_name="envios_maquila", blank=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Envío a Maquila"
        verbose_name_plural = "Envíos a Maquila"
        ordering = ["-fecha_envio"]


class BitacoraTemperatura(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="bitacoras_temperatura")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, related_name="bitacoras_temperatura")
    area = models.CharField(max_length=120, help_text="Ej: Refrigerador, Congelador, Área de Reactivos")
    temperatura_c = models.DecimalField(max_digits=5, decimal_places=2)
    registrada_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="temperaturas_registradas")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Bitácora de Temperatura"
        verbose_name_plural = "Bitácoras de Temperatura"
        ordering = ["-fecha_registro"]


class MantenimientoEquipo(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="mantenimientos_equipo")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, related_name="mantenimientos_equipo")
    equipo = models.CharField(max_length=255, help_text="Equipo/analizador (ej. Mindray BC-6000)")
    tipo = models.CharField(max_length=120, help_text="Ej: Preventivo, Correctivo, Calibración")
    realizada_por = models.CharField(max_length=255, blank=True, null=True)
    evidencia_foto = models.ImageField(upload_to="mantenimiento_equipo/", blank=True, null=True, validators=[validate_image_upload])
    fecha_registro = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Mantenimiento de Equipo"
        verbose_name_plural = "Mantenimientos de Equipo"
        ordering = ["-fecha_registro"]


# ==============================================================================
# MODELO: HISTORIAL DE RESULTADOS (TRAZABILIDAD FORENSE)
# ==============================================================================
class HistorialResultados(models.Model):
    """Trazabilidad forense completa de modificaciones en resultados."""
    resultado_parametro = models.ForeignKey(
        'ResultadoParametro', on_delete=models.PROTECT,
        related_name='historial_cambios', verbose_name="Resultado Modificado"
    )
    valor_anterior_numerico = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    valor_anterior_texto = models.CharField(max_length=500, blank=True, null=True)
    valor_nuevo_numerico = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    valor_nuevo_texto = models.CharField(max_length=500, blank=True, null=True)
    modificado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='modificaciones_resultados')
    fecha_modificacion = models.DateTimeField(auto_now_add=True)
    razon_cambio = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    cambio_aprobado_por_supervisor = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cambios_aprobados'
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Historial de Modificación de Resultado"
        verbose_name_plural = "Historial de Modificaciones de Resultados"
        ordering = ['-fecha_modificacion']
        indexes = [
            models.Index(fields=['resultado_parametro', '-fecha_modificacion']),
            models.Index(fields=['modificado_por', '-fecha_modificacion']),
        ]

    def __str__(self):
        return f"Modificación {self.id} - {self.resultado_parametro}"


# ==============================================================================
# MODELO: RESULTADO DE PARÁMETRO (Captura de Laboratorio con IA)
# ==============================================================================
class ResultadoParametro(models.Model):
    """Resultados capturados por analito LIMS v7.5 (fuente unica de verdad)."""
    orden = models.ForeignKey(
        'OrdenDeServicio',
        on_delete=models.PROTECT,
        related_name='resultados',
        verbose_name="Orden de Servicio"
    )
    analito = models.ForeignKey(
        'lims.Analito',
        on_delete=models.PROTECT,
        related_name='resultados_core',
        verbose_name="Analito LIMS",
    )
    valor = models.CharField(max_length=500, help_text="Valor capturado del resultado (numérico o texto)")

    capturado_por = models.ForeignKey(
        'Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='resultados_capturados',
        verbose_name="Capturado por"
    )
    fecha_captura = models.DateTimeField(auto_now_add=True)
    metodo_captura = models.CharField(
        max_length=20,
        choices=[
            ('MANUAL', 'Captura Manual'),
            ('VOZ', 'Dictado por Voz'),
            ('OCR', 'Escaneado OCR'),
            ('INTERFAZ', 'Interfaz Automática'),
            ('IA_BORRADOR', 'Sugerencia IA (pendiente aprobación clínica)'),
        ],
        default='MANUAL',
        verbose_name="Método de Captura"
    )

    aprobado_por_humano = models.BooleanField(
        default=False,
        verbose_name="Aprobación humana formal",
        help_text=(
            "True cuando un profesional autorizado validó el resultado en captura "
            "(acción «validar»). La IA nunca puede fijar este campo en True."
        ),
    )

    validado = models.BooleanField(default=False, verbose_name="Resultado Validado")
    validado_por = models.ForeignKey(
        'Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parametros_validados',
        verbose_name="Validado por"
    )
    fecha_validacion = models.DateTimeField(null=True, blank=True)

    fuera_rango = models.BooleanField(default=False, verbose_name="Fuera de Rango", help_text="True si el valor está fuera del rango de referencia")
    es_critico = models.BooleanField(default=False, verbose_name="Valor Crítico (Pánico)", help_text="True si el valor está en rango de pánico")

    observaciones = models.TextField(blank=True, verbose_name="Observaciones", help_text="Notas del químico sobre este resultado")

    imagen_microscopio = models.ImageField(
        upload_to='core.utils.paths.generar_ruta_drive',
        storage=get_google_drive_storage,
        blank=True,
        null=True,
        verbose_name="Imagen de Microscopio",
        help_text="Evidencia fotográfica del microscopio o equipo (se almacena en Google Drive)",
        validators=[validate_image_upload],
    )

    class Meta:
        app_label = 'core'
        unique_together = ('orden', 'analito')
        verbose_name = 'Resultado de Parámetro'
        verbose_name_plural = 'Resultados de Parámetros'
        ordering = ['analito__nombre']

    def validar_contra_rango(self, edad=None, sexo=None, edad_dias=None, edad_desconocida=False):
        """
        Valida contra lims.ValorReferenciaAnalito (DIAS / ANOS).
        Escudo clínico v1.14: pánico vía umbrales LIMS (valor_critico_*, es_critico_si_fuera_de_rango).
        """
        if not self.valor:
            return {
                'estado': 'SIN_VALOR',
                'fuera_rango': False,
                'es_critico': False,
                'mensaje_critico': '',
            }

        try:
            valor_num = float(str(self.valor).replace(',', '.'))
        except (ValueError, TypeError):
            return {
                'estado': 'NO_NUMERICO',
                'fuera_rango': False,
                'es_critico': False,
                'mensaje_critico': '',
            }

        if edad_desconocida or (edad is None and edad_dias is None):
            return {
                'estado': 'EDAD_DESCONOCIDA',
                'fuera_rango': False,
                'es_critico': False,
                'mensaje_critico': '',
            }

        from lims.models import ValorReferenciaAnalito
        from django.db.models import Q

        qs = ValorReferenciaAnalito.objects.filter(analito_id=self.analito_id)
        if sexo and sexo in ('M', 'F'):
            qs = qs.filter(sexo__in=[sexo, 'I'])
        else:
            qs = qs.filter(sexo='I')

        if edad_dias is not None and edad_dias < 365:
            qs = qs.filter(
                unidad_edad='DIAS',
                edad_minima__lte=edad_dias,
                edad_maxima__gte=edad_dias,
            )
        elif edad is not None:
            edad_anos = int(edad) if edad >= 1 else 1
            qs = qs.filter(
                unidad_edad='ANOS',
                edad_minima__lte=edad_anos,
                edad_maxima__gte=edad_anos,
            )
        else:
            return {
                'estado': 'SIN_RANGO',
                'fuera_rango': False,
                'es_critico': False,
                'mensaje_critico': '',
            }

        rango = qs.order_by('edad_minima').first()
        if not rango:
            return {'estado': 'SIN_RANGO', 'fuera_rango': False, 'es_critico': False, 'mensaje_critico': ''}

        ev = rango.evaluar_valor_numerico(valor_num)
        self.fuera_rango = ev['fuera_rango']
        self.es_critico = ev['es_critico']
        self.save(update_fields=['fuera_rango', 'es_critico'])
        return {
            'estado': ev['estado'],
            'fuera_rango': ev['fuera_rango'],
            'es_critico': ev['es_critico'],
            'mensaje_critico': ev.get('mensaje_critico') or '',
        }

    def __str__(self):
        return f"{self.analito.nombre}: {self.valor}"


class OrdenDeServicio(TenantModel):
    """Orden de servicio de laboratorio (equivalente a Venta en farmacia)."""
    ESTADO_CHOICES = [
        ('PENDIENTE_PAGO', 'Pendiente de Pago'),
        ('PAGADO', 'Pagado'),
        ('EN_PROCESO', 'En Proceso'),
        ('RESULTADOS_LISTOS', 'Resultados Listos'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    ]

    TIPO_SERVICIO_CHOICES = [
        ('RUTINA',   'Rutina'),
        ('URGENTE',  'Urgente'),
        ('STAT',     'STAT — Inmediato'),
        ('CONTROL',  'Control de Calidad'),
        ('MAQUILA',  'Maquila (Externo)'),
        ('URGENCIA', 'Urgencia'),  # legacy — mantener compatibilidad
    ]

    ESTADO_PAGO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PARCIAL', 'Parcial'),
        ('PAGADO', 'Pagado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ordenes_lab')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sucursal")
    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='ordenes_lab', verbose_name="Paciente")

    paciente_nombre_snapshot = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre del paciente al momento de la orden", help_text="Copia al crear la orden; usado en PDF y reportes históricos")
    paciente_edad_snapshot = models.IntegerField(null=True, blank=True, verbose_name="Edad al momento de la orden", help_text="Edad en años al crear la orden; usada para rangos de referencia")
    paciente_sexo_snapshot = models.CharField(
        max_length=1,
        choices=[('M', 'Masculino'), ('F', 'Femenino'), ('I', 'Indeterminado')],
        null=True, blank=True,
        verbose_name="Sexo al momento de la orden",
        help_text="Sexo al crear la orden; usado para rangos de referencia"
    )

    medico_referente = models.ForeignKey(
        'Medico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_referidas',
        verbose_name="Médico Referente",
        help_text="Médico que solicita los estudios"
    )

    ORIGEN_CHOICES = [
        ('PUBLICO_GENERAL', 'Público General / Walk-in'),
        ('MEDICO_EXTERNO', 'Médico Externo / Referencia'),
        ('URGENCIA', 'Urgencia Hospitalaria'),
        ('CONVENIO', 'Convenio Institucional'),
    ]
    origen_orden = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default='PUBLICO_GENERAL', verbose_name="Origen de la Orden", help_text="¿De dónde proviene esta orden?")

    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE_PAGO', verbose_name="Estado")
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total")
    anticipo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Anticipo Pagado")
    responsable_ingreso = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='ordenes_ingresadas', verbose_name="Responsable de Ingreso")
    folio_orden = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Folio de Orden")

    tipo_servicio = models.CharField(max_length=10, choices=TIPO_SERVICIO_CHOICES, default='RUTINA', verbose_name="Tipo de Servicio")
    tarifa = models.CharField(max_length=50, default='PUBLICO_GENERAL', verbose_name="Tarifa", help_text="Ej: Público General, Convenio A, etc.")
    descuento_monto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Descuento Aplicado")
    folio_cliente_externo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Folio Cliente Externo")
    diagnostico = models.TextField(blank=True, null=True, verbose_name="Diagnóstico Clínico")
    notas_internas = models.TextField(blank=True, null=True, verbose_name="Notas Internas")
    requiere_factura = models.BooleanField(default=False, verbose_name="Requiere Factura CFDI",
                                           help_text="Indica si el paciente solicitó factura al momento del ingreso")
    hora_toma_muestra = models.DateTimeField(null=True, blank=True, verbose_name="Hora de Toma de Muestra")
    hora_entrega_prometida = models.DateTimeField(null=True, blank=True, verbose_name="Hora de Entrega Prometida")
    estado_pago = models.CharField(max_length=10, choices=ESTADO_PAGO_CHOICES, default='PENDIENTE', verbose_name="Estado de Pago")

    # ── Abono Parcial / Cuenta por Cobrar (Fase 2-C) ─────────────────────────
    es_cxc = models.BooleanField(default=False, verbose_name="Es Cuenta por Cobrar",
                                  help_text="Orden confirmada con saldo pendiente registrado")
    motivo_cxc = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name="Motivo CxC",
        choices=[
            ('CONVENIO',             'Convenio / Empresa'),
            ('CREDITO_DIRECTOR',     'Crédito Autorizado por Director'),
            ('COMPLEMENTO_POSTERIOR','Complemento Posterior'),
            ('PACIENTE_VIP',         'Paciente Frecuente / VIP'),
            ('OTRO',                 'Otro'),
        ]
    )
    nota_cxc = models.TextField(blank=True, null=True, verbose_name="Nota CxC")

    es_cortesia = models.BooleanField(default=False, verbose_name="Es Cortesía / Beca", help_text="Indica si esta orden es un apoyo social (sin cobro)")
    motivo_cortesia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Motivo de Cortesía",
                                        choices=[
                                            ('MEDICO', 'Médico / Personal de Salud'),
                                            ('COLABORADOR', 'Colaborador Interno'),
                                            ('VULNERABILIDAD', 'Vulnerabilidad Alta'),
                                            ('OTRO', 'Otro')
                                        ])
    autorizado_por_cortesia = models.CharField(max_length=200, blank=True, null=True, verbose_name="Autorizado por (Cortesía)")
    total_original = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         verbose_name="Total Original",
                                         help_text="Valor original antes de aplicar cortesía (para estadísticas)")

    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Latitud")
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Longitud")

    url_drive_backup = models.URLField(blank=True, null=True, verbose_name="URL Backup en Google Drive", help_text="Link de visualización del PDF en Drive")
    drive_file_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="ID de Archivo en Drive")
    drive_sync_pending = models.BooleanField(default=False, verbose_name="Sincronización Pendiente", help_text="True si el archivo aún no se ha sincronizado a Drive")
    drive_status = models.CharField(max_length=20, choices=[('PENDIENTE', 'Pendiente'), ('SINCRONIZADO', 'Sincronizado'), ('ERROR', 'Error')], default='PENDIENTE', verbose_name="Estado de Sincronización")
    drive_last_error = models.TextField(blank=True, null=True, verbose_name="Último Error de Drive", help_text="Mensaje de error para debug")

    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Eliminación", help_text="Para Soft Delete - no borrar físicamente")
    motivo_eliminacion = models.TextField(blank=True, null=True, verbose_name="Motivo de Eliminación")

    ESTADO_CLINICO_CHOICES = [
        ('PENDIENTE_TOMA', 'Pendiente de Toma de Muestra'),
        ('EN_EXTRACCION', 'En Proceso de Extracción'),
        ('TOMA_REALIZADA', 'Toma de Muestra Realizada'),
        ('EN_PROCESO', 'En Proceso de Análisis'),
        ('VALIDADO_PARCIAL', 'Validado Parcialmente'),
        ('COMPLETO', 'Completo - Todos los Resultados Validados'),
        ('ENTREGADO', 'Entregado al Paciente'),
    ]
    estado_clinico = models.CharField(max_length=20, choices=ESTADO_CLINICO_CHOICES, default='PENDIENTE_TOMA', verbose_name="Estado Clínico", help_text="Estado del análisis clínico (independiente del pago)")

    requiere_maquila = models.BooleanField(default=False, verbose_name="Requiere Maquila Externa", help_text="True si algún estudio debe enviarse a laboratorio externo")

    token_acceso = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        verbose_name="Token de Acceso",
        help_text="UUID único para acceso seguro vía QR y WhatsApp"
    )

    client_mutation_id = models.UUIDField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
        verbose_name="Idempotencia cliente (offline)",
        help_text="UUID enviado por el cliente para deduplicar creación al sincronizar sin red.",
    )

    fecha_toma_muestra = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Toma de Muestra", help_text="Timestamp de cuando se tomó la muestra (NOM-007-SSA3-2011)")

    usuario_tomo_muestra = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='muestras_tomadas',
        verbose_name="Usuario que Tomó la Muestra"
    )

    observaciones_clinicas = models.TextField(blank=True, null=True, verbose_name="Observaciones Clínicas", help_text="Notas del químico o técnico de laboratorio")

    archivo_resultado = models.FileField(
        upload_to='core.utils.paths.generar_ruta_drive_laboratorio',
        storage=get_google_drive_storage,
        blank=True,
        null=True,
        verbose_name="PDF de Resultados",
        help_text="PDF final con resultados de laboratorio (se almacena en Google Drive)",
        validators=[validate_document_upload],
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Orden de Servicio"
        verbose_name_plural = "Órdenes de Servicio"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['fecha_creacion']),
            models.Index(fields=['estado']),
            models.Index(fields=['empresa', 'fecha_creacion']),
            models.Index(fields=['empresa', 'estado']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'client_mutation_id'],
                condition=models.Q(client_mutation_id__isnull=False),
                name='unique_orden_client_mutation_per_empresa',
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if self.estado in ('RESULTADOS_LISTOS', 'ENTREGADO'):
            has_pdf = bool(self.archivo_resultado and getattr(self.archivo_resultado, 'name', None))
            if not has_pdf:
                # Trabajo clínico desacoplado del cobro: en RESULTADOS_LISTOS con saldo
                # pendiente el PDF no se genera hasta liquidar (Portero en extracción).
                if self.estado == 'RESULTADOS_LISTOS':
                    from core.utils.candado_financiero import tiene_saldo_pendiente

                    if tiene_saldo_pendiente(self):
                        return
                raise ValidationError({
                    'estado': 'No se puede marcar la orden como lista o entregada si el documento PDF de resultados no está adjunto.'
                })

    def save(self, *args, **kwargs):
        """Rellena snapshot de paciente y genera folio si falta."""
        if self.estado in ('RESULTADOS_LISTOS', 'ENTREGADO'):
            self.full_clean()
        if not self.folio_orden:
            from datetime import datetime
            ahora = datetime.now()
            prefijo = f'LAB-{ahora.strftime("%Y%m")}-'
            ultimos = OrdenDeServicio.objects.filter(folio_orden__startswith=prefijo).count()
            self.folio_orden = f'{prefijo}{str(ultimos + 1).zfill(5)}'
        if self.paciente_id and (
            not self.paciente_nombre_snapshot
            or self.paciente_edad_snapshot is None
            or not self.paciente_sexo_snapshot
        ):
            self.paciente_nombre_snapshot = self.paciente_nombre_snapshot or (self.paciente.nombre_completo if self.paciente_id else '')
            if self.paciente_edad_snapshot is None and self.paciente_id:
                self.paciente_edad_snapshot = self.paciente.edad
            if not self.paciente_sexo_snapshot and self.paciente_id:
                self.paciente_sexo_snapshot = self.paciente.sexo or ''
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Orden #{self.folio_orden or self.id} - {self.paciente.nombre_completo}"


class DetalleOrden(models.Model):
    """Linea de pedido de laboratorio vinculada al catalogo LIMS v7.5."""
    orden = models.ForeignKey(OrdenDeServicio, on_delete=models.CASCADE, related_name='detalles', verbose_name="Orden de Servicio")
    analito = models.ForeignKey(
        'lims.Analito', on_delete=models.PROTECT, null=True, blank=True,
        related_name='detalles_ordenes_core', verbose_name="Analito",
    )
    perfil_lims = models.ForeignKey(
        'lims.PerfilLims', on_delete=models.PROTECT, null=True, blank=True,
        related_name='detalles_ordenes_core', verbose_name="Perfil LIMS",
    )
    paquete_lims = models.ForeignKey(
        'lims.PaqueteLims', on_delete=models.PROTECT, null=True, blank=True,
        related_name='detalles_ordenes_core', verbose_name="Paquete LIMS",
    )
    descripcion_linea = models.CharField(
        max_length=300, blank=True, default='',
        verbose_name="Descripcion (snapshot)",
        help_text="Texto mostrado en ticket/PDF si el item es perfil o paquete.",
    )
    precio_momento = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio al Momento de la Orden")

    resultado = models.TextField(blank=True, null=True, help_text="Texto libre o JSON del resultado", verbose_name="Resultado del Estudio")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones del Químico")
    validado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='resultados_validados', verbose_name="Validado por")
    fecha_validacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Validación")

    ESTADO_PROCESAMIENTO_CHOICES = [
        ('PENDIENTE_TOMA', 'Pendiente de Toma'),
        ('TOMA_REALIZADA', 'Toma Realizada'),
        ('EN_PROCESO', 'En Proceso'),
        ('RESULTADO_LISTO', 'Resultado Listo'),
        ('MUESTRA_RECHAZADA', 'Muestra Rechazada'),
    ]
    estado_procesamiento = models.CharField(max_length=20, choices=ESTADO_PROCESAMIENTO_CHOICES, default='PENDIENTE_TOMA', verbose_name="Estado de Procesamiento")
    motivo_rechazo = models.TextField(blank=True, null=True, verbose_name="Motivo de Rechazo", help_text="Ej: Muestra Insuficiente, Hemolizada, Coagulada")
    valor_critico_confirmado = models.BooleanField(default=False, verbose_name="Valor Crítico Confirmado", help_text="Indica si se confirmó un valor de pánico")

    class Meta:
        app_label = 'core'
        verbose_name = "Detalle de Orden"
        verbose_name_plural = "Detalles de Ordenes"

    def __str__(self):
        label = (
            self.descripcion_linea
            or (self.analito.nombre if self.analito_id else '')
            or (self.perfil_lims.nombre if self.perfil_lims_id else '')
            or (self.paquete_lims.nombre if self.paquete_lims_id else '')
            or '?'
        )
        return f"{self.orden.folio_orden or self.orden.id} - {label}"


class PreOrdenLaboratorio(models.Model):
    """Pre-orden generada desde Consultorio para solicitar estudios de laboratorio."""
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de Cobro'),
        ('COBRADA', 'Cobrada - Orden Creada'),
        ('CANCELADA', 'Cancelada'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='preordenes_lab')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sucursal")
    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='preordenes_lab', verbose_name="Paciente")
    medico_solicitante = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='preordenes_solicitadas', verbose_name="Médico Solicitante")
    consulta_medica = models.ForeignKey('core.ConsultaMedica', on_delete=models.SET_NULL, null=True, blank=True, related_name='preordenes', verbose_name="Consulta Médica")

    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE', verbose_name="Estado")

    orden_vinculada = models.ForeignKey(OrdenDeServicio, on_delete=models.SET_NULL, null=True, blank=True, related_name='preorden_origen', verbose_name="Orden Vinculada")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones del Médico")

    class Meta:
        app_label = 'core'
        verbose_name = "Pre-Orden de Laboratorio"
        verbose_name_plural = "Pre-Órdenes de Laboratorio"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Pre-Orden {self.id} - {self.paciente.nombre_completo}"


class DetallePreOrden(models.Model):
    """Detalle solicitado en pre-orden (catalogo LIMS v7.5)."""
    preorden = models.ForeignKey(PreOrdenLaboratorio, on_delete=models.CASCADE, related_name='detalles', verbose_name="Pre-Orden")
    analito = models.ForeignKey(
        'lims.Analito', on_delete=models.PROTECT, null=True, blank=True,
        related_name='detalles_preordenes_core', verbose_name="Analito",
    )
    perfil_lims = models.ForeignKey(
        'lims.PerfilLims', on_delete=models.PROTECT, null=True, blank=True,
        related_name='detalles_preordenes_core', verbose_name="Perfil LIMS",
    )
    paquete_lims = models.ForeignKey(
        'lims.PaqueteLims', on_delete=models.PROTECT, null=True, blank=True,
        related_name='detalles_preordenes_core', verbose_name="Paquete LIMS",
    )
    descripcion_linea = models.CharField(max_length=300, blank=True, default='')
    observaciones_medico = models.TextField(blank=True, null=True, verbose_name="Observaciones del Médico")

    class Meta:
        app_label = 'core'
        verbose_name = "Detalle de Pre-Orden"
        verbose_name_plural = "Detalles de Pre-Órdenes"

    def __str__(self):
        label = self.descripcion_linea or (self.analito and self.analito.nombre) or (self.perfil_lims and self.perfil_lims.nombre) or (self.paquete_lims and self.paquete_lims.nombre) or '?'
        return f"{self.preorden.id} - {label}"
