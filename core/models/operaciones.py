"""
core/models/operaciones.py
Auditoría forense, Backups, Comunicación, Incidencias, Notificaciones Push, Voice Log.
Depende de: base.py
"""
from django.db import models
import uuid

from core.validators import validate_backup_upload, validate_audio_upload
from .base import Empresa, Sucursal, Usuario


# ==============================================================================
# BLOQUE: AUDITORIA FORENSE
# ==============================================================================
class AuditLog(models.Model):
    """Log de auditoría forense inalterable (Bitácora de Espías)."""
    ACCION_CREATE = 'CREATE'
    ACCION_UPDATE = 'UPDATE'
    ACCION_DELETE = 'DELETE'
    ACCION_VIEW = 'VIEW'
    ACCION_PRINT = 'PRINT'
    ACCION_CHOICES = [
        (ACCION_CREATE, 'Crear'),
        (ACCION_UPDATE, 'Actualizar'),
        (ACCION_DELETE, 'Eliminar'),
        (ACCION_VIEW, 'Ver'),
        (ACCION_PRINT, 'Imprimir'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='logs_auditoria')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Sucursal")
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='acciones_auditadas', verbose_name="Usuario")

    accion = models.CharField(max_length=20, choices=ACCION_CHOICES, verbose_name="Acción Realizada")
    modelo_afectado = models.CharField(max_length=100, verbose_name="Modelo Afectado", help_text="Nombre del modelo Django")
    objeto_id = models.CharField(max_length=100, verbose_name="ID del Objeto")

    datos_anteriores = models.JSONField(null=True, blank=True, verbose_name="Valor Anterior")
    datos_nuevos = models.JSONField(null=True, blank=True, verbose_name="Valor Nuevo")

    fecha_cierta = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Cierta (Timestamp)")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="Dirección IP")
    user_agent = models.CharField(max_length=255, blank=True, null=True, verbose_name="User Agent")
    hash_verificacion = models.CharField(max_length=64, blank=True, null=True, verbose_name="Hash SHA-256", help_text="Para prevenir alteraciones")

    class Meta:
        app_label = 'core'
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"
        ordering = ['-fecha_cierta']
        indexes = [
            models.Index(fields=['empresa', '-fecha_cierta']),
            models.Index(fields=['usuario', '-fecha_cierta']),
            models.Index(fields=['modelo_afectado', 'objeto_id']),
        ]

    def __str__(self):
        return f"{self.get_accion_display()} {self.modelo_afectado} #{self.objeto_id} - {self.usuario} - {self.fecha_cierta.strftime('%Y-%m-%d %H:%M')}"


# ==============================================================================
# BLOQUE 5: RESILIENCIA DE DATOS - BACKUP NOCTURNO 3:00 AM
# ==============================================================================
class BackupRegistro(models.Model):
    """Registro de backups nocturnos con cifrado AES-256 y rotación automática."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='backups', verbose_name="Empresa")

    fecha_backup = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora del Backup")
    tipo_backup = models.CharField(
        max_length=20,
        choices=[
            ('DIARIO', 'Backup Diario'),
            ('SEMANAL', 'Backup Semanal'),
            ('MENSUAL', 'Backup Mensual'),
        ],
        default='DIARIO',
        verbose_name="Tipo de Backup"
    )

    archivo_backup = models.FileField(upload_to='backups/', verbose_name="Archivo de Backup Comprimido y Encriptado", validators=[validate_backup_upload])
    ruta_completa = models.CharField(max_length=500, blank=True, null=True, verbose_name="Ruta Completa del Archivo")
    tamanio_bytes = models.BigIntegerField(default=0, verbose_name="Tamaño del Archivo (Bytes)")
    tamanio_mb = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Tamaño del Archivo (MB)")

    archivado_en_drive = models.BooleanField(default=False, verbose_name="Archivado en Google Drive")
    drive_file_id = models.CharField(max_length=200, blank=True, null=True, verbose_name="ID de archivo en Drive")
    drive_folder_id = models.CharField(max_length=200, blank=True, null=True, verbose_name="ID de carpeta Drive")
    fecha_archivado_drive = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de archivado en Drive")
    drive_error = models.TextField(blank=True, null=True, verbose_name="Error de Drive (si aplica)")

    hash_verificacion = models.CharField(max_length=64, blank=True, null=True, verbose_name="Hash SHA-256 del Backup")
    encriptado_aes256 = models.BooleanField(default=True, verbose_name="Encriptado con AES-256")
    clave_encriptacion_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID de Clave de Encriptación")

    estado = models.CharField(
        max_length=20,
        choices=[
            ('EN_PROGRESO', 'En Progreso'),
            ('COMPLETADO', 'Completado Exitosamente'),
            ('FALLIDO', 'Fallido'),
        ],
        default='EN_PROGRESO',
        verbose_name="Estado del Backup"
    )
    mensaje_error = models.TextField(blank=True, null=True, verbose_name="Mensaje de Error (si aplica)")

    incluye_base_datos = models.BooleanField(default=True, verbose_name="Incluye Base de Datos")
    incluye_media = models.BooleanField(default=True, verbose_name="Incluye Archivos Multimedia")
    incluye_parametros_lab = models.BooleanField(default=True, verbose_name="Incluye Parámetros de Laboratorio (163)")
    incluye_auditoria_sha256 = models.BooleanField(default=True, verbose_name="Incluye Bitácoras de Auditoría SHA-256")
    incluye_expedientes_medicos = models.BooleanField(default=True, verbose_name="Incluye Expedientes Médicos")
    incluye_firmas_digitales = models.BooleanField(default=True, verbose_name="Incluye Firmas Digitales")
    incluye_pdfs_rh = models.BooleanField(default=True, verbose_name="Incluye PDFs de RH")

    registros_base_datos = models.IntegerField(default=0, verbose_name="Registros en Base de Datos")
    archivos_media_incluidos = models.IntegerField(default=0, verbose_name="Archivos Multimedia Incluidos")

    notificacion_enviada = models.BooleanField(default=False, verbose_name="Notificación Enviada al Director")
    fecha_notificacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Notificación")

    class Meta:
        app_label = 'core'
        verbose_name = "Registro de Backup"
        verbose_name_plural = "Registros de Backups"
        ordering = ['-fecha_backup']
        indexes = [
            models.Index(fields=['empresa', '-fecha_backup']),
            models.Index(fields=['tipo_backup', '-fecha_backup']),
            models.Index(fields=['estado', '-fecha_backup']),
        ]

    def __str__(self):
        estado_icon = '✅' if self.estado == 'COMPLETADO' else '❌' if self.estado == 'FALLIDO' else '⏳'
        return f"{estado_icon} Backup {self.get_tipo_backup_display()} - {self.fecha_backup.strftime('%Y-%m-%d %H:%M')} - {self.tamanio_mb} MB"

    def marcar_notificacion_enviada(self):
        """Marca la notificación como enviada."""
        from django.utils import timezone
        self.notificacion_enviada = True
        self.fecha_notificacion = timezone.now()
        self.save(update_fields=['notificacion_enviada', 'fecha_notificacion'])


class BackupInmutableLog(models.Model):
    """
    Huella WORM (append-only) de backups completados; complementa BackupRegistro
    para auditoría de integridad sin modificar el archivo de respaldo.
    """
    backup_registro = models.ForeignKey(
        BackupRegistro,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='logs_inmutables',
        verbose_name='Backup asociado',
    )
    sha256_manifest = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name='SHA-256 (pre-cifrado, mismo que BackupRegistro.hash_verificacion)',
    )
    ruta_archivo = models.CharField(max_length=500, blank=True, default='', verbose_name='Ruta del .encrypted')
    registrado_en = models.DateTimeField(auto_now_add=True, verbose_name='Registrado en')

    class Meta:
        app_label = 'core'
        verbose_name = 'Log de backup inmutable'
        verbose_name_plural = 'Logs de backup inmutable'
        ordering = ['-registrado_en']

    def __str__(self):
        return f'IMM {self.sha256_manifest[:16]}… @ {self.registrado_en:%Y-%m-%d}'


# ==============================================================================
# MÓDULO DE COMUNICACIÓN INTERNA (INTER-CHAT)
# ==============================================================================
class MensajeInterno(models.Model):
    """PRIS-Chat: Sistema de mensajeria interna estilo WhatsApp."""
    TIPO_CHOICES = [
        ('texto', 'Texto'),
        ('audio', 'Nota de Voz'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='mensajes_internos', verbose_name="Empresa")
    remitente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensajes_enviados', verbose_name="Remitente")
    destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensajes_recibidos', verbose_name="Destinatario")
    mensaje = models.TextField(blank=True, default='', verbose_name="Mensaje")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='texto', verbose_name="Tipo")
    audio = models.FileField(upload_to='chat_audios/%Y/%m/', blank=True, null=True, verbose_name="Nota de Voz", validators=[validate_audio_upload])
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    leido = models.BooleanField(default=False, verbose_name="Leido")

    class Meta:
        app_label = 'core'
        verbose_name = "Mensaje Interno"
        verbose_name_plural = "Mensajes Internos"
        ordering = ['fecha']
        indexes = [
            models.Index(fields=['empresa', 'remitente', 'destinatario']),
            models.Index(fields=['empresa', '-fecha']),
        ]


# ==============================================================================
# MÓDULO DE AUTORIZACIONES EN TIEMPO REAL
# ==============================================================================
class SolicitudAutorizacion(models.Model):
    """Sistema de autorizaciones para acciones sensibles."""
    TIPO_ACCION_CHOICES = [
        ('DESCUENTO', 'Descuento Mayor'),
        ('CANCELACION', 'Cancelación de Orden/Venta'),
        ('EDICION_RESULTADO', 'Edición de Resultado de Laboratorio'),
        ('DEVOLUCION', 'Devolución de Producto'),
        ('AJUSTE_INVENTARIO', 'Ajuste Mayor de Inventario'),
        ('OTRO', 'Otro'),
    ]

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    usuario_solicita = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='solicitudes_enviadas', verbose_name="Usuario que Solicita")
    tipo_accion = models.CharField(max_length=50, choices=TIPO_ACCION_CHOICES, verbose_name="Tipo de Acción")
    descripcion = models.TextField(verbose_name="Motivo/Descripción", help_text="Explica por qué se requiere esta autorización")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE', verbose_name="Estado")
    token_aprobacion = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="Token Único de Aprobación")

    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_resolucion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Resolución")
    resuelto_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='autorizaciones_resueltas', verbose_name="Resuelto por")
    comentario_rechazo = models.TextField(blank=True, null=True, verbose_name="Comentario de Rechazo", help_text="Razón del rechazo (si aplica)")

    datos_contexto = models.JSONField(default=dict, blank=True, verbose_name="Datos Contextuales", help_text="Información adicional de la solicitud (IDs de orden, montos, etc.)")

    class Meta:
        app_label = 'core'
        verbose_name = "Solicitud de Autorización"
        verbose_name_plural = "Solicitudes de Autorización"
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f"{self.get_tipo_accion_display()} - {self.usuario_solicita.get_full_name()} ({self.estado})"


# ==============================================================================
# MÓDULO DE REGISTRO DE INCIDENCIAS POR EXCEPCIÓN DE POLÍTICA
# ==============================================================================
class IncidenciaOperativa(models.Model):
    """Registro de incidencias cuando un empleado realiza acciones fuera de la política estándar."""
    TIPO_INCIDENCIA_CHOICES = [
        ('PAGO_PARCIAL', 'Pago Parcial en Farmacia'),
        ('DESCUENTO_ELEVADO', 'Descuento Elevado'),
        ('EDICION_TICKET', 'Edición de Ticket Post-Venta'),
        ('CANCELACION_SIN_CLAVE', 'Cancelación sin Autorización'),
        ('RESULTADO_EDITADO', 'Resultado de Laboratorio Editado'),
        ('MUESTRA_RECHAZADA', 'Muestra Rechazada'),
        ('VENTA_SIN_STOCK', 'Venta con Stock Insuficiente'),
        ('DEVOLUCION_MANUAL', 'Devolución Manual'),
        ('AJUSTE_INVENTARIO', 'Ajuste Mayor de Inventario'),
        ('OTRO', 'Otro'),
    ]

    ESTADO_REVISION_CHOICES = [
        ('PENDIENTE', 'Pendiente de Revisión'),
        ('JUSTIFICADA', 'Justificada'),
        ('SANCIONADA', 'Requiere Acción Correctiva'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='incidencias_operativas', verbose_name="Empresa")
    usuario_responsable = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='incidencias_registradas', verbose_name="Usuario Responsable")
    tipo_incidencia = models.CharField(max_length=50, choices=TIPO_INCIDENCIA_CHOICES, verbose_name="Tipo de Incidencia")
    justificacion = models.TextField(verbose_name="Justificación", help_text="Motivo por el cual se realizó esta excepción (mínimo 15 caracteres)")
    monto_afectado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto Afectado", help_text="Si aplica (ej: descuento aplicado, monto de pago parcial)")
    estado_revision = models.CharField(max_length=20, choices=ESTADO_REVISION_CHOICES, default='PENDIENTE', verbose_name="Estado de Revisión")
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")

    revisado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias_revisadas', verbose_name="Revisado por")
    fecha_revision = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Revisión")
    comentario_revision = models.TextField(blank=True, null=True, verbose_name="Comentario de Revisión", help_text="Notas del Director sobre esta incidencia")

    datos_contexto = models.JSONField(default=dict, blank=True, verbose_name="Datos Contextuales", help_text="Información adicional (IDs de venta, orden, etc.)")

    class Meta:
        app_label = 'core'
        verbose_name = "Incidencia Operativa"
        verbose_name_plural = "Incidencias Operativas"
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"{self.get_tipo_incidencia_display()} - {self.usuario_responsable.get_full_name()} ({self.fecha_hora.strftime('%d/%m/%Y %H:%M')})"


# ==============================================================================
# MÓDULO DE CRECIMIENTO Y CONTROL GERENCIAL (BUZÓN DE LA VERDAD)
# ==============================================================================
class BuzonQuejas(models.Model):
    """Buzón de quejas, sugerencias y felicitaciones para el Director."""
    TIPO_CHOICES = [
        ('QUEJA', 'Queja'),
        ('SUGERENCIA', 'Sugerencia'),
        ('FELICITACION', 'Felicitación'),
    ]

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_REVISION', 'En Revisión'),
        ('RESUELTO', 'Resuelto'),
        ('DESCARTADO', 'Descartado'),
    ]

    SENTIMIENTO_CHOICES = [
        ('POSITIVO', 'Positivo'),
        ('NEUTRO', 'Neutro'),
        ('NEGATIVO', 'Negativo'),
        ('CRITICO', 'Crítico'),
    ]

    CATEGORIA_CHOICES = [
        ('TIEMPOS', 'Tiempos'),
        ('TRATO', 'Trato'),
        ('PRECIOS', 'Precios'),
        ('INSTALACIONES', 'Instalaciones'),
        ('LIMPIEZA', 'Limpieza'),
        ('PROCESO', 'Proceso'),
        ('OTRO', 'Otro'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='quejas', verbose_name="Empresa")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='QUEJA', verbose_name="Tipo")
    mensaje = models.TextField(verbose_name="Mensaje")
    nombre_remitente = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre del Remitente", help_text="Opcional si es anónimo")
    contacto = models.CharField(max_length=255, blank=True, null=True, verbose_name="Contacto", help_text="Email o teléfono (opcional)")
    anonimo = models.BooleanField(default=True, verbose_name="Anónimo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    sentimiento_ia = models.CharField(max_length=20, choices=SENTIMIENTO_CHOICES, blank=True, null=True, verbose_name="Sentimiento IA")
    categoria_ia = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, blank=True, null=True, verbose_name="Categoría IA")
    resumen_causa = models.TextField(blank=True, null=True, verbose_name="Resumen de Causa", help_text="Breve análisis de por qué pasó")
    plan_accion_sugerido = models.TextField(blank=True, null=True, verbose_name="Plan de Acción Sugerido", help_text="Lista de pasos recomendados")
    analizado_ia = models.BooleanField(default=False, verbose_name="Analizado por IA")
    fecha_analisis = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Análisis IA")

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE', verbose_name="Estado")
    notas_seguimiento = models.TextField(blank=True, null=True, verbose_name="Notas de Seguimiento", help_text="Notas internas del director")
    fecha_resolucion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Resolución")
    fecha_cierre = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Cierre")
    resuelto_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='quejas_resueltas', verbose_name="Resuelto por")
    notas_resolucion = models.TextField(blank=True, null=True, verbose_name="Notas de Resolución")

    class Meta:
        app_label = 'core'
        verbose_name = "Queja/Sugerencia/Felicitación"
        verbose_name_plural = "Buzón de Calidad"
        ordering = ['-fecha_creacion']

    def __str__(self):
        tipo_icon = {'QUEJA': '🔴', 'SUGERENCIA': '💡', 'FELICITACION': '⭐'}
        sentimiento_icon = {'CRITICO': '🔴', 'NEGATIVO': '🟠', 'NEUTRO': '🟡', 'POSITIVO': '🟢'}
        icono = sentimiento_icon.get(self.sentimiento_ia, '⚪') if self.sentimiento_ia else tipo_icon.get(self.tipo, '📝')
        return f"{icono} {self.get_tipo_display()} - {self.fecha_creacion.strftime('%d/%m/%Y %H:%M')}"


# ==============================================================================
# MÓDULO DE BIBLIOTECA DE LIDERAZGO
# ==============================================================================
class LibroLiderazgo(models.Model):
    """Biblioteca de libros recomendados para el Director."""
    ESTADO_LECTURA_CHOICES = [
        ('POR_LEER', 'Por Leer'),
        ('LEYENDO', 'Leyendo'),
        ('TERMINADO', 'Terminado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='libros_liderazgo', verbose_name="Empresa")
    titulo = models.CharField(max_length=255, verbose_name="Título del Libro")
    autor = models.CharField(max_length=255, verbose_name="Autor")
    portada_url = models.URLField(blank=True, null=True, verbose_name="URL de Portada", help_text="Link a imagen de la portada")
    resumen_ejecutivo = models.TextField(verbose_name="Resumen Ejecutivo", help_text="Lo que el líder debe aprender de este libro")
    aplicacion_practica = models.TextField(verbose_name="Aplicación Práctica", help_text="Cómo aplicar estas enseñanzas en la empresa")
    estado_lectura = models.CharField(max_length=20, choices=ESTADO_LECTURA_CHOICES, default='POR_LEER', verbose_name="Estado de Lectura")
    fecha_agregado = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Agregado")
    fecha_inicio_lectura = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Inicio")
    fecha_fin_lectura = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Fin")
    notas_personales = models.TextField(blank=True, null=True, verbose_name="Notas Personales", help_text="Notas del director sobre el libro")

    class Meta:
        app_label = 'core'
        verbose_name = "Libro de Liderazgo"
        verbose_name_plural = "Biblioteca de Liderazgo"
        ordering = ['-fecha_agregado']

    def __str__(self):
        estado_icon = {'POR_LEER': '📚', 'LEYENDO': '📖', 'TERMINADO': '✅'}
        icono = estado_icon.get(self.estado_lectura, '📚')
        return f"{icono} {self.titulo} - {self.autor}"


# ==============================================================================
# PRIS SENTINEL V4: WEB PUSH NOTIFICATIONS
# ==============================================================================
class PushSubscription(models.Model):
    """Almacena las suscripciones de Web Push Notifications para cada usuario/dispositivo."""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='push_subscriptions', verbose_name="Usuario")

    endpoint = models.URLField(max_length=500, unique=True, verbose_name="Endpoint de Push")
    p256dh = models.CharField(max_length=255, verbose_name="Clave Pública (p256dh)", help_text="Clave de cifrado del cliente")
    auth = models.CharField(max_length=255, verbose_name="Token de Autenticación", help_text="Token de autenticación del cliente")

    user_agent = models.CharField(max_length=500, blank=True, verbose_name="User Agent", help_text="Navegador y sistema operativo del dispositivo")
    nombre_dispositivo = models.CharField(max_length=100, blank=True, verbose_name="Nombre del Dispositivo", help_text="Ej: iPhone de Jonathan, Chrome en Desktop")

    activa = models.BooleanField(default=True, verbose_name="Suscripción Activa")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_ultima_notificacion = models.DateTimeField(null=True, blank=True, verbose_name="Última Notificación Enviada")

    notificar_errores_500 = models.BooleanField(default=True, verbose_name="Notificar Errores 500")
    notificar_solo_criticos = models.BooleanField(default=False, verbose_name="Solo Errores Críticos", help_text="Si está marcado, solo notifica severidad CRITICA/ALTA")

    class Meta:
        app_label = 'core'
        verbose_name = 'Suscripción Push'
        verbose_name_plural = 'Suscripciones Push'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['usuario', 'activa']),
            models.Index(fields=['endpoint']),
        ]

    def __str__(self):
        dispositivo = self.nombre_dispositivo or 'Dispositivo'
        return f"{self.usuario.username} - {dispositivo} ({'Activa' if self.activa else 'Inactiva'})"


# ==============================================================================
# PRIS VOICE COMMANDER: CONTROL POR VOZ & AUDITORÍA
# ==============================================================================
class VoiceAuditLog(models.Model):
    """Log de auditoría de comandos de voz."""
    TIPO_COMANDO = [
        ('BUSQUEDA', 'Búsqueda de Información'),
        ('ACCION', 'Acción / Comando'),
        ('NAVEGACION', 'Navegación'),
        ('COMUNICACION', 'Comunicación (Walkie-Talkie)'),
        ('CONSULTA', 'Consulta a IA'),
        ('CRITICO', 'Comando Crítico (Requiere Auth)'),
    ]

    ESTADO_EJECUCION = [
        ('EXITOSO', 'Ejecutado Exitosamente'),
        ('BLOQUEADO', 'Bloqueado por Permisos'),
        ('ERROR', 'Error en Ejecución'),
        ('CANCELADO', 'Cancelado por Usuario'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='voice_commands', verbose_name="Usuario")
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, verbose_name="Empresa")

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha/Hora del Comando")
    url_actual = models.CharField(max_length=500, verbose_name="URL Donde se Emitió el Comando", help_text="Contexto visual del usuario")
    datos_pantalla = models.TextField(blank=True, null=True, verbose_name="Datos de Pantalla (Contexto)", help_text="JSON o texto con contexto de lo que el usuario ve")

    transcripcion = models.TextField(verbose_name="Transcripción del Comando de Voz", help_text="Texto reconocido por Web Speech API")
    tipo_comando = models.CharField(max_length=20, choices=TIPO_COMANDO, verbose_name="Tipo de Comando")
    intencion_detectada = models.CharField(max_length=255, verbose_name="Intención Detectada por IA", help_text="Ej: 'buscar_paciente', 'surtir_receta', 'cerrar_caja'")
    parametros_extraidos = models.JSONField(default=dict, blank=True, verbose_name="Parámetros Extraídos", help_text="JSON con parámetros del comando. Ej: {'folio': '554', 'paciente': 'Juan'}")

    respuesta_ia = models.TextField(blank=True, null=True, verbose_name="Respuesta de la IA", help_text="Respuesta de Gemini al comando")
    accion_ejecutada = models.CharField(max_length=255, blank=True, null=True, verbose_name="Acción Ejecutada", help_text="Vista/función que se ejecutó. Ej: 'farmacia.views.surtir_receta'")
    estado = models.CharField(max_length=20, choices=ESTADO_EJECUCION, default='EXITOSO', verbose_name="Estado de Ejecución")
    mensaje_error = models.TextField(blank=True, null=True, verbose_name="Mensaje de Error", help_text="Si el comando falló, detalles del error")

    requiere_autenticacion = models.BooleanField(default=False, verbose_name="Requirió Autenticación Adicional", help_text="True si requirió WebAuthn / Huella")
    autenticacion_exitosa = models.BooleanField(default=False, verbose_name="Autenticación Exitosa")
    nivel_autorizado = models.CharField(max_length=50, default='STAFF', verbose_name="Nivel de Autorización del Usuario", help_text="STAFF, DIRECTOR, etc.")

    audio_file = models.FileField(
        upload_to='voice_commands/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Archivo de Audio",
        help_text="Audio original del comando (opcional)",
        validators=[validate_audio_upload],
    )
    duracion_segundos = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Duración del Audio (segundos)")

    tiempo_procesamiento_ms = models.IntegerField(null=True, blank=True, verbose_name="Tiempo de Procesamiento (ms)", help_text="Latencia desde transcripción hasta respuesta")

    class Meta:
        app_label = 'core'
        verbose_name = 'Log de Comando de Voz'
        verbose_name_plural = 'Logs de Comandos de Voz'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['usuario', '-timestamp']),
            models.Index(fields=['tipo_comando', '-timestamp']),
            models.Index(fields=['estado', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
        permissions = [
            ("view_all_voice_logs", "Puede ver todos los logs de voz"),
            ("delete_voice_logs", "Puede eliminar logs de voz"),
        ]

    def __str__(self):
        return f"{self.usuario.username} - {self.intencion_detectada} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    @property
    def es_critico(self):
        """Indica si el comando es de nivel crítico."""
        return self.tipo_comando == 'CRITICO'

    @property
    def fue_bloqueado(self):
        """Indica si el comando fue bloqueado por permisos."""
        return self.estado == 'BLOQUEADO'


# ==============================================================================
# BLOQUE: NOTIFICACIONES DEL SISTEMA
# ==============================================================================
class NotificacionSistema(models.Model):
    """
    Centro de notificaciones internas de PRISLAB.
    Permite enviar alertas a usuarios específicos o a todos los usuarios de una empresa.
    Compatible con el sistema de PushSubscription para notificaciones web.
    """
    TIPO_CHOICES = [
        ('INFO',     'Información'),
        ('ALERTA',   'Alerta'),
        ('CRITICO',  'Crítico'),
        ('EXITO',    'Éxito'),
        ('SISTEMA',  'Sistema'),
    ]
    MODULO_CHOICES = [
        ('LABORATORIO', 'Laboratorio'),
        ('FARMACIA',    'Farmacia'),
        ('CONSULTORIO', 'Consultorio'),
        ('FINANZAS',    'Finanzas'),
        ('RH',          'Recursos Humanos'),
        ('SISTEMA',     'Sistema'),
        ('GENERAL',     'General'),
    ]

    empresa  = models.ForeignKey(Empresa,  on_delete=models.CASCADE, related_name='notificaciones', verbose_name="Empresa")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Sucursal")

    # Destinatario: si es None, la notificación aplica a todos los usuarios de la empresa
    destinatario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notificaciones_recibidas',
        verbose_name="Destinatario (null = todos)"
    )
    remitente = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='notificaciones_enviadas',
        verbose_name="Remitente"
    )

    tipo    = models.CharField(max_length=10, choices=TIPO_CHOICES, default='INFO', verbose_name="Tipo")
    modulo  = models.CharField(max_length=20, choices=MODULO_CHOICES, default='GENERAL', verbose_name="Módulo origen")

    titulo  = models.CharField(max_length=200, verbose_name="Título")
    mensaje = models.TextField(verbose_name="Mensaje")
    enlace  = models.CharField(max_length=500, blank=True, verbose_name="URL de acción (opcional)")

    leida   = models.BooleanField(default=False, verbose_name="Leída")
    fecha_lectura = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de lectura")
    creada  = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    # Metadatos opcionales para notificaciones automáticas
    objeto_tipo = models.CharField(max_length=100, blank=True, verbose_name="Tipo de objeto relacionado")
    objeto_id   = models.CharField(max_length=50,  blank=True, verbose_name="ID de objeto relacionado")

    class Meta:
        app_label = 'core'
        verbose_name = 'Notificación del Sistema'
        verbose_name_plural = 'Notificaciones del Sistema'
        ordering = ['-creada']
        indexes = [
            models.Index(fields=['destinatario', 'leida', '-creada']),
            models.Index(fields=['empresa', '-creada']),
            models.Index(fields=['modulo', '-creada']),
        ]

    def __str__(self):
        dest = self.destinatario.username if self.destinatario else 'Todos'
        return f"[{self.get_tipo_display()}] {self.titulo} → {dest}"

    def marcar_leida(self):
        """Marca la notificación como leída."""
        if not self.leida:
            from django.utils import timezone
            self.leida = True
            self.fecha_lectura = timezone.now()
            self.save(update_fields=['leida', 'fecha_lectura'])

    @classmethod
    def crear(cls, empresa, titulo, mensaje, tipo='INFO', modulo='GENERAL',
              destinatario=None, enlace='', remitente=None, objeto_tipo='', objeto_id=''):
        """
        Atajo para crear una notificación de forma limpia.

        Ejemplo:
            NotificacionSistema.crear(
                empresa=user.empresa,
                titulo='Resultado de pánico',
                mensaje='El paciente Juan Pérez tiene glucosa crítica (650 mg/dL)',
                tipo='CRITICO',
                modulo='LABORATORIO',
                enlace='/laboratorio/orden/123/',
                destinatario=medico_user,
            )
        """
        return cls.objects.create(
            empresa=empresa,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo,
            modulo=modulo,
            destinatario=destinatario,
            remitente=remitente,
            enlace=enlace,
            objeto_tipo=objeto_tipo,
            objeto_id=str(objeto_id),
        )


# ==============================================================================
# BLOQUE: BITÁCORA ENTREGA DE RESULTADOS
# ==============================================================================
class BitacoraEntregaResultados(models.Model):
    """
    Registro inmutable de cada entrega de resultados de laboratorio al paciente.
    Cumple con NOM-007-SSA3-2011 (trazabilidad de la cadena de custodia).

    Cada vez que se entrega un resultado (digital o físico) se crea un registro
    aquí: quién lo entregó, a quién, a qué hora y por qué canal.
    """
    CANAL_CHOICES = [
        ('PRESENCIAL', 'Presencial'),
        ('WHATSAPP',   'WhatsApp'),
        ('EMAIL',      'Correo electrónico'),
        ('PORTAL',     'Portal del paciente'),
        ('IMPRESO',    'Impreso en mostrador'),
    ]
    ESTADO_CHOICES = [
        ('ENTREGADO',  'Entregado'),
        ('RECHAZADO',  'Rechazado por paciente'),
        ('PENDIENTE',  'Pendiente de entrega'),
        ('REIMPRESION','Reimpresión solicitada'),
    ]

    empresa  = models.ForeignKey(Empresa,  on_delete=models.PROTECT, verbose_name="Empresa")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Sucursal")
    usuario_entrega = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='entregas_realizadas', verbose_name="Personal que entregó"
    )

    # Referencia a la orden de laboratorio (string para evitar importación circular)
    orden_id    = models.PositiveIntegerField(verbose_name="ID de Orden de Laboratorio")
    folio_orden = models.CharField(max_length=40, blank=True, verbose_name="Folio de Orden")

    # Referencia al paciente
    paciente_nombre = models.CharField(max_length=200, verbose_name="Nombre del Paciente")
    paciente_id     = models.PositiveIntegerField(null=True, blank=True, verbose_name="ID Paciente")

    canal   = models.CharField(max_length=20, choices=CANAL_CHOICES, default='PRESENCIAL', verbose_name="Canal de Entrega")
    estado  = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='ENTREGADO', verbose_name="Estado")

    fecha_entrega   = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Entrega")
    firma_digital   = models.TextField(blank=True, null=True, verbose_name="Firma Digital (base64)")
    observaciones   = models.TextField(blank=True, verbose_name="Observaciones")

    # Para WhatsApp / Email: número o correo al que se envió
    destino_envio   = models.CharField(max_length=200, blank=True, verbose_name="Destino del Envío")
    confirmado_lectura = models.BooleanField(default=False, verbose_name="Confirmado por el destinatario")

    class Meta:
        app_label = 'core'
        verbose_name = 'Bitácora de Entrega de Resultados'
        verbose_name_plural = 'Bitácora de Entregas de Resultados'
        ordering = ['-fecha_entrega']
        indexes = [
            models.Index(fields=['empresa', '-fecha_entrega']),
            models.Index(fields=['orden_id']),
            models.Index(fields=['paciente_id', '-fecha_entrega']),
        ]
        permissions = [
            ('view_bitacora_entregas', 'Puede ver bitácora de entregas'),
            ('reprint_resultados', 'Puede solicitar reimpresión de resultados'),
        ]

    def __str__(self):
        return (
            f"Entrega #{self.pk} — Orden {self.folio_orden or self.orden_id} "
            f"a {self.paciente_nombre} ({self.get_canal_display()}) {self.fecha_entrega:%Y-%m-%d %H:%M}"
        )


# ==============================================================================
# BLOQUE: BIENESTAR EMOCIONAL AVANZADO
# ==============================================================================
class ConversacionBienestar(models.Model):
    """Mensajes del chat de bienestar emocional entre usuario y PRIS."""
    ROL_USUARIO = 'USUARIO'
    ROL_PRIS    = 'PRIS'
    ROL_CHOICES = [(ROL_USUARIO, 'Usuario'), (ROL_PRIS, 'PRIS IA')]

    ESTADO_NORMAL  = 'NORMAL'
    ESTADO_ATENCION = 'ATENCION'
    ESTADO_ALERTA  = 'ALERTA'
    ESTADO_CHOICES = [
        (ESTADO_NORMAL,   'Normal'),
        (ESTADO_ATENCION, 'Requiere atención'),
        (ESTADO_ALERTA,   'Alerta roja — riesgo'),
    ]

    usuario      = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='conversaciones_bienestar')
    empresa      = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='conversaciones_bienestar')
    rol          = models.CharField(max_length=10, choices=ROL_CHOICES, default=ROL_USUARIO)
    mensaje      = models.TextField(verbose_name="Mensaje")
    estado_salud = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ESTADO_NORMAL,
                                     verbose_name="Estado detectado por IA")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    privado      = models.BooleanField(default=True, help_text="Solo visible para el propio usuario y dirección ante alerta roja")

    class Meta:
        app_label = 'core'
        verbose_name = 'Conversación de Bienestar'
        verbose_name_plural = 'Conversaciones de Bienestar'
        ordering = ['fecha_creacion']
        indexes = [models.Index(fields=['usuario', 'fecha_creacion'])]

    def __str__(self):
        return f"{self.get_rol_display()} ({self.usuario.username}): {self.mensaje[:60]}"


class AlertaBienestar(models.Model):
    """Alertas de riesgo detectadas por PRIS en las conversaciones de bienestar."""
    NIVEL_BAJO    = 'BAJO'
    NIVEL_MEDIO   = 'MEDIO'
    NIVEL_ALTO    = 'ALTO'
    NIVEL_CRITICO = 'CRITICO'
    NIVEL_CHOICES = [
        (NIVEL_BAJO,    'Bajo'),
        (NIVEL_MEDIO,   'Medio'),
        (NIVEL_ALTO,    'Alto'),
        (NIVEL_CRITICO, 'Crítico — protocolo de crisis'),
    ]

    ESTADO_NUEVA    = 'NUEVA'
    ESTADO_VISTA    = 'VISTA'
    ESTADO_RESUELTA = 'RESUELTA'
    ESTADO_CHOICES  = [
        (ESTADO_NUEVA,    'Nueva'),
        (ESTADO_VISTA,    'Vista por dirección'),
        (ESTADO_RESUELTA, 'Resuelta'),
    ]

    usuario    = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='alertas_bienestar')
    empresa    = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='alertas_bienestar')
    nivel      = models.CharField(max_length=10, choices=NIVEL_CHOICES, default=NIVEL_MEDIO)
    estado     = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ESTADO_NUEVA)
    descripcion = models.TextField(verbose_name="Descripción de la alerta")
    accion_tomada = models.TextField(blank=True, verbose_name="Acción tomada")
    fecha_alerta  = models.DateTimeField(auto_now_add=True)
    fecha_vista   = models.DateTimeField(null=True, blank=True)
    visto_por     = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='alertas_vistas')

    class Meta:
        app_label = 'core'
        verbose_name = 'Alerta de Bienestar'
        verbose_name_plural = 'Alertas de Bienestar'
        ordering = ['-fecha_alerta']
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['usuario', '-fecha_alerta']),
        ]

    def __str__(self):
        return f"Alerta {self.get_nivel_display()} — {self.usuario.username} ({self.fecha_alerta:%Y-%m-%d})"


# ==============================================================================
# BLOQUE: CAPACITACIÓN RAG
# ==============================================================================
class DocumentoCapacitacion(models.Model):
    """
    Manual, política o documento de capacitación interno.
    Sirve como fuente de verdad de PRIS-IA (RAG).
    """
    TIPO_MANUAL     = 'MANUAL'
    TIPO_POLITICA   = 'POLITICA'
    TIPO_PROCESO    = 'PROCESO'
    TIPO_NORMATIVA  = 'NORMATIVA'
    TIPO_OTRO       = 'OTRO'
    TIPO_CHOICES    = [
        (TIPO_MANUAL,    'Manual operativo'),
        (TIPO_POLITICA,  'Política interna'),
        (TIPO_PROCESO,   'Procedimiento'),
        (TIPO_NORMATIVA, 'Normativa / NOM'),
        (TIPO_OTRO,      'Otro'),
    ]

    # Semáforo de Inteligencia RAG
    ESTADO_SUBIDO       = 'SUBIDO'
    ESTADO_PROCESANDO   = 'PROCESANDO'
    ESTADO_ENTRENADO    = 'ENTRENADO'
    ESTADO_ERROR        = 'ERROR'
    ESTADO_RAG_CHOICES  = [
        (ESTADO_SUBIDO,     '🔴 Subido — pendiente de indexar'),
        (ESTADO_PROCESANDO, '🟡 Procesando — extrayendo vectores'),
        (ESTADO_ENTRENADO,  '🟢 Entrenado — IA puede citar este documento'),
        (ESTADO_ERROR,      '❌ Error — revisar log'),
    ]

    MODULO_LABORATORIO  = 'LABORATORIO'
    MODULO_FARMACIA     = 'FARMACIA'
    MODULO_CONSULTORIO  = 'CONSULTORIO'
    MODULO_CALIDAD      = 'CALIDAD'
    MODULO_GENERAL      = 'GENERAL'
    MODULO_CHOICES = [
        (MODULO_LABORATORIO,  'Laboratorio Clínico'),
        (MODULO_FARMACIA,     'Farmacia'),
        (MODULO_CONSULTORIO,  'Consultorio Médico'),
        (MODULO_CALIDAD,      'Control de Calidad / ISO 15189'),
        (MODULO_GENERAL,      'General / Todos los módulos'),
    ]

    empresa   = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='documentos_capacitacion')
    token_acceso = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name='Token de Acceso')
    titulo    = models.CharField(max_length=200, verbose_name="Título del documento")
    # Alias tipo_documento → mapea al campo interno 'tipo' para compatibilidad con vistas
    tipo      = models.CharField(
        max_length=20, choices=TIPO_CHOICES, default=TIPO_MANUAL,
        verbose_name="Tipo de documento",
    )
    modulo_relacionado = models.CharField(
        max_length=20, choices=MODULO_CHOICES, default=MODULO_GENERAL,
        verbose_name="Módulo relacionado",
        db_index=True,
    )
    archivo   = models.FileField(upload_to='capacitacion/', verbose_name="Archivo PDF/DOCX")
    descripcion = models.TextField(blank=True, verbose_name="Descripción / resumen")
    contenido_texto = models.TextField(blank=True, verbose_name="Texto extraído (para búsqueda RAG)")
    version   = models.CharField(max_length=20, blank=True, default='1.0')
    activo    = models.BooleanField(default=True)

    # ── RAG: Estado de procesamiento ─────────────────────────────────────────
    estado_rag   = models.CharField(
        max_length=20, choices=ESTADO_RAG_CHOICES, default=ESTADO_SUBIDO,
        verbose_name="Estado de Entrenamiento IA",
        db_index=True,
    )
    chunks_rag   = models.PositiveIntegerField(
        default=0,
        verbose_name="Fragmentos indexados",
        help_text="Número de chunks vectoriales creados en la base RAG.",
    )
    error_rag    = models.TextField(blank=True, verbose_name="Detalle de error RAG")

    # ── Blindaje Legal ────────────────────────────────────────────────────────
    validado_por_nombre = models.CharField(
        max_length=200, blank=True,
        default='Q.B. Giselle Margarita López Gutiérrez',
        verbose_name="Responsable sanitaria (validadora)",
    )
    cedula_validador = models.CharField(
        max_length=50, blank=True,
        verbose_name="Cédula profesional del validador",
    )

    subido_por  = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True,
        related_name='documentos_subidos',
        verbose_name="Subido por",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Documento de Capacitación'
        verbose_name_plural = 'Documentos de Capacitación'
        ordering = ['-fecha_creacion']
        indexes = [models.Index(fields=['empresa', 'tipo', 'activo', 'estado_rag'])]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo} v{self.version}"

    # Alias para compatibilidad con templates y vistas que usen tipo_documento
    @property
    def tipo_documento(self):
        return self.tipo

    def get_tipo_documento_display(self):
        return self.get_tipo_display()

    @property
    def semaforo_emoji(self):
        return {'SUBIDO': '🔴', 'PROCESANDO': '🟡', 'ENTRENADO': '🟢', 'ERROR': '❌'}.get(self.estado_rag, '⚪')

    @property
    def semaforo_class(self):
        return {'SUBIDO': 'danger', 'PROCESANDO': 'warning', 'ENTRENADO': 'success', 'ERROR': 'secondary'}.get(self.estado_rag, 'secondary')


class CapsulaSabiduria(models.Model):
    """Cápsula de conocimiento generada por PRIS a partir de documentos."""
    empresa   = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='capsulas_sabiduria')
    titulo    = models.CharField(max_length=200)
    contenido = models.TextField(verbose_name="Contenido de la cápsula")
    documento_fuente = models.ForeignKey(DocumentoCapacitacion, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='capsulas')
    tags      = models.CharField(max_length=300, blank=True, help_text="Etiquetas separadas por comas")
    activo    = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    veces_consultada = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'core'
        verbose_name = 'Cápsula de Sabiduría'
        verbose_name_plural = 'Cápsulas de Sabiduría'
        ordering = ['-veces_consultada', '-fecha_creacion']

    def __str__(self):
        return self.titulo

