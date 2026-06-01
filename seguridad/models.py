"""
Modelos para el módulo de Seguridad Física, Botón de Pánico y Seguridad Lógica (2FA, Auditoría).
Cumplimiento: ISO 27001, GDPR, LFPDPPP (Ley Federal de Protección de Datos Personales)
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
import pyotp
import qrcode
from io import BytesIO
import base64
import hashlib
import secrets


class ConfiguracionSeguridad(models.Model):
    """
    Configuración global de seguridad del sistema.
    Almacena números de emergencia y configuraciones del botón de pánico.
    """
    empresa = models.OneToOneField(
        'core.Empresa',
        on_delete=models.CASCADE,
        related_name='configuracion_seguridad'
    )
    
    # Números de emergencia (formato: +521234567890)
    telefono_director = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Teléfono del director para alertas de pánico (formato: +521234567890)'
    )
    telefono_seguridad = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Teléfono de seguridad privada para alertas de pánico'
    )
    telegram_chat_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Chat ID de Telegram para alertas'
    )
    
    # Configuración del botón de pánico
    boton_panico_activo = models.BooleanField(
        default=True,
        help_text='Activar/desactivar el botón de pánico'
    )
    atajo_teclado = models.CharField(
        max_length=50,
        default='Ctrl+Alt+P',
        help_text='Atajo de teclado para activar el botón de pánico'
    )
    
    # Método de notificación preferido
    METODO_WHATSAPP = 'WHATSAPP'
    METODO_TELEGRAM = 'TELEGRAM'
    METODO_AMBOS = 'AMBOS'
    METODO_CHOICES = [
        (METODO_WHATSAPP, 'WhatsApp'),
        (METODO_TELEGRAM, 'Telegram'),
        (METODO_AMBOS, 'Ambos'),
    ]
    metodo_notificacion = models.CharField(
        max_length=20,
        choices=METODO_CHOICES,
        default=METODO_WHATSAPP,
        help_text='Método preferido para enviar alertas'
    )
    
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración de Seguridad'
        verbose_name_plural = 'Configuraciones de Seguridad'
    
    def __str__(self):
        return f"Configuración Seguridad - {self.empresa.nombre}"


class AlertaPanico(models.Model):
    """
    Registro de alertas de pánico activadas por usuarios.
    """
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_EN_PROCESO = 'EN_PROCESO'
    ESTADO_RESUELTA = 'RESUELTA'
    ESTADO_FALSA_ALARMA = 'FALSA_ALARMA'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_EN_PROCESO, 'En Proceso'),
        (ESTADO_RESUELTA, 'Resuelta'),
        (ESTADO_FALSA_ALARMA, 'Falsa Alarma'),
    ]
    
    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        related_name='alertas_panico'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='alertas_panico_activadas',
        help_text='Usuario que activó la alerta'
    )
    
    fecha_activacion = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha y hora en que se activó la alerta'
    )
    
    ubicacion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Ubicación física donde se activó (IP, estación de trabajo, etc.)'
    )
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
        help_text='Estado actual de la alerta'
    )
    
    notas = models.TextField(
        blank=True,
        null=True,
        help_text='Notas adicionales sobre la resolución de la alerta'
    )
    
    usuario_resolucion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_panico_resueltas',
        help_text='Usuario que resolvió la alerta'
    )
    
    fecha_resolucion = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora en que se resolvió la alerta'
    )
    
    # Información de notificaciones enviadas
    whatsapp_enviado = models.BooleanField(default=False)
    telegram_enviado = models.BooleanField(default=False)
    mensajes_enviados = models.JSONField(
        default=list,
        help_text='Registro de mensajes enviados con timestamps'
    )
    
    class Meta:
        verbose_name = 'Alerta de Pánico'
        verbose_name_plural = 'Alertas de Pánico'
        ordering = ['-fecha_activacion']
    
    def __str__(self):
        return f"Alerta Pánico - {self.usuario} - {self.fecha_activacion.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def marcar_resuelta(self, usuario_resolucion, notas=''):
        """Marca la alerta como resuelta."""
        self.estado = self.ESTADO_RESUELTA
        self.usuario_resolucion = usuario_resolucion
        self.fecha_resolucion = timezone.now()
        if notas:
            self.notas = notas
        self.save()


# ============================================================================
# MÓDULO DE AUTENTICACIÓN DE DOS FACTORES (2FA)
# ============================================================================

class DispositivoTOTP(models.Model):
    """
    Dispositivo de autenticación TOTP (Time-based One-Time Password) para 2FA.
    Compatible con Google Authenticator, Microsoft Authenticator, Authy, etc.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dispositivos_totp',
        verbose_name="Usuario"
    )
    
    nombre = models.CharField(
        max_length=100,
        help_text='Nombre descriptivo del dispositivo (ej: iPhone 13, Google Authenticator)'
    )
    
    llave_secreta = models.CharField(
        max_length=32,
        unique=True,
        help_text='Llave secreta TOTP (Base32)'
    )
    
    activo = models.BooleanField(
        default=False,
        help_text='El dispositivo está activado y validado'
    )
    
    confirmado = models.BooleanField(
        default=False,
        help_text='El usuario confirmó el dispositivo ingresando un código válido'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    fecha_ultimo_uso = models.DateTimeField(null=True, blank=True)
    
    # Contador de usos (para auditoría)
    contador_usos = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Dispositivo TOTP (2FA)'
        verbose_name_plural = 'Dispositivos TOTP (2FA)'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        estado = "✓ Activo" if self.activo else "✗ Inactivo"
        return f"{self.usuario.username} - {self.nombre} ({estado})"
    
    def generar_llave_secreta(self):
        """Genera una nueva llave secreta TOTP"""
        self.llave_secreta = pyotp.random_base32()
        self.save()
        return self.llave_secreta
    
    def obtener_uri_provisioning(self):
        """
        Genera la URI de provisioning para códigos QR.
        Compatible con Google Authenticator y similares.
        """
        totp = pyotp.TOTP(self.llave_secreta)
        empresa_nombre = "PRISLAB"
        return totp.provisioning_uri(
            name=self.usuario.username,
            issuer_name=empresa_nombre
        )
    
    def generar_qr_code(self):
        """Genera un código QR en formato Base64 para el frontend"""
        uri = self.obtener_uri_provisioning()
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}"
    
    def verificar_codigo(self, codigo):
        """
        Verifica un código TOTP ingresado por el usuario.
        Retorna True si el código es válido.
        """
        totp = pyotp.TOTP(self.llave_secreta)
        es_valido = totp.verify(codigo, valid_window=1)  # Ventana de 30 segundos
        
        if es_valido:
            self.fecha_ultimo_uso = timezone.now()
            self.contador_usos += 1
            self.save()
        
        return es_valido
    
    def confirmar_dispositivo(self, codigo):
        """
        Confirma el dispositivo después de verificar el primer código.
        """
        if self.verificar_codigo(codigo):
            self.confirmado = True
            self.activo = True
            self.fecha_confirmacion = timezone.now()
            self.save()
            return True
        return False


class DispositivoSMS(models.Model):
    """
    Dispositivo de autenticación SMS para 2FA.
    Envía códigos de verificación vía SMS usando Twilio.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dispositivos_sms',
        verbose_name="Usuario"
    )
    
    telefono = models.CharField(
        max_length=20,
        help_text='Número de teléfono en formato E.164 (ej: +5215512345678)'
    )
    
    activo = models.BooleanField(default=False)
    confirmado = models.BooleanField(default=False)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    fecha_ultimo_uso = models.DateTimeField(null=True, blank=True)
    
    contador_usos = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Dispositivo SMS (2FA)'
        verbose_name_plural = 'Dispositivos SMS (2FA)'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        estado = "✓ Activo" if self.activo else "✗ Inactivo"
        return f"{self.usuario.username} - {self.telefono} ({estado})"


class CodigoBackup2FA(models.Model):
    """
    Códigos de respaldo para 2FA.
    Generados cuando el usuario pierde acceso a su dispositivo.
    Cada código es de un solo uso.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='codigos_backup_2fa',
        verbose_name="Usuario"
    )
    
    codigo = models.CharField(
        max_length=12,
        unique=True,
        help_text='Código de respaldo (formato: XXXX-XXXX-XXXX)'
    )
    
    codigo_hash = models.CharField(
        max_length=64,
        help_text='Hash SHA256 del código para verificación segura'
    )
    
    usado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_uso = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Código de Respaldo 2FA'
        verbose_name_plural = 'Códigos de Respaldo 2FA'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        estado = "✗ Usado" if self.usado else "✓ Disponible"
        return f"{self.usuario.username} - {self.codigo} ({estado})"
    
    @staticmethod
    def generar_codigo():
        """Genera un código de respaldo aleatorio"""
        parte1 = secrets.token_hex(2).upper()
        parte2 = secrets.token_hex(2).upper()
        parte3 = secrets.token_hex(2).upper()
        return f"{parte1}-{parte2}-{parte3}"
    
    def save(self, *args, **kwargs):
        """Genera el hash del código antes de guardar"""
        if not self.codigo_hash:
            self.codigo_hash = hashlib.sha256(self.codigo.encode()).hexdigest()
        super().save(*args, **kwargs)
    
    def verificar(self, codigo_ingresado):
        """Verifica si el código ingresado es correcto y no ha sido usado"""
        if self.usado:
            return False
        
        codigo_hash_ingresado = hashlib.sha256(codigo_ingresado.encode()).hexdigest()
        if codigo_hash_ingresado == self.codigo_hash:
            self.usado = True
            self.fecha_uso = timezone.now()
            self.save()
            return True
        return False


# ============================================================================
# MÓDULO DE GESTIÓN DE SESIONES
# ============================================================================

class SesionActiva(models.Model):
    """
    Registro de sesiones activas de usuarios.
    Permite cerrar sesiones remotamente y detectar accesos sospechosos.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sesiones_activas',
        verbose_name="Usuario"
    )
    
    session_key = models.CharField(
        max_length=40,
        unique=True,
        help_text='Key de la sesión de Django'
    )
    
    # Información del dispositivo
    user_agent = models.TextField(
        blank=True,
        help_text='User agent del navegador'
    )
    
    dispositivo_tipo = models.CharField(
        max_length=50,
        blank=True,
        help_text='Tipo de dispositivo (Desktop, Mobile, Tablet)'
    )
    
    navegador = models.CharField(
        max_length=100,
        blank=True,
        help_text='Navegador utilizado'
    )
    
    sistema_operativo = models.CharField(
        max_length=100,
        blank=True,
        help_text='Sistema operativo'
    )
    
    # Información de ubicación
    ip_address = models.GenericIPAddressField(
        help_text='Dirección IP del cliente'
    )
    
    ubicacion_ciudad = models.CharField(
        max_length=100,
        blank=True,
        help_text='Ciudad (obtenida por GeoIP)'
    )
    
    ubicacion_pais = models.CharField(
        max_length=100,
        blank=True,
        help_text='País (obtenido por GeoIP)'
    )
    
    # Timestamps
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_ultima_actividad = models.DateTimeField(auto_now=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    
    activa = models.BooleanField(
        default=True,
        help_text='La sesión está activa'
    )
    
    # Seguridad
    es_sospechosa = models.BooleanField(
        default=False,
        help_text='Marcada como sospechosa por el sistema'
    )
    
    razon_sospecha = models.TextField(
        blank=True,
        help_text='Razón por la que se marcó como sospechosa'
    )
    
    class Meta:
        verbose_name = 'Sesión Activa'
        verbose_name_plural = 'Sesiones Activas'
        ordering = ['-fecha_ultima_actividad']
        indexes = [
            models.Index(fields=['usuario', 'activa']),
            models.Index(fields=['session_key']),
        ]
    
    def __str__(self):
        return f"{self.usuario.username} - {self.dispositivo_tipo} - {self.ip_address}"
    
    def cerrar_sesion(self):
        """Marca la sesión como cerrada"""
        self.activa = False
        self.fecha_cierre = timezone.now()
        self.save()


# ============================================================================
# MÓDULO DE AUDITORÍA DE SEGURIDAD
# ============================================================================

class LogAccionSensible(models.Model):
    """
    Log de acciones sensibles del sistema.
    Cumplimiento: ISO 27001, GDPR artículo 30 (registro de actividades de tratamiento)
    """
    ACCION_LOGIN = 'LOGIN'
    ACCION_LOGOUT = 'LOGOUT'
    ACCION_LOGIN_FALLIDO = 'LOGIN_FALLIDO'
    ACCION_CAMBIO_PASSWORD = 'CAMBIO_PASSWORD'
    ACCION_2FA_ACTIVADO = '2FA_ACTIVADO'
    ACCION_2FA_DESACTIVADO = '2FA_DESACTIVADO'
    ACCION_VER_EXPEDIENTE = 'VER_EXPEDIENTE'
    ACCION_EDITAR_EXPEDIENTE = 'EDITAR_EXPEDIENTE'
    ACCION_ELIMINAR_REGISTRO = 'ELIMINAR_REGISTRO'
    ACCION_EXPORTAR_DATOS = 'EXPORTAR_DATOS'
    ACCION_CAMBIO_PERMISOS = 'CAMBIO_PERMISOS'
    ACCION_ACCESO_ADMINISTRACION = 'ACCESO_ADMIN'
    ACCION_MODIFICAR_RESULTADO_LAB = 'MODIFICAR_RESULTADO_LAB'
    ACCION_CANCELAR_FACTURA = 'CANCELAR_FACTURA'
    
    ACCION_CHOICES = [
        (ACCION_LOGIN, 'Inicio de Sesión'),
        (ACCION_LOGOUT, 'Cierre de Sesión'),
        (ACCION_LOGIN_FALLIDO, 'Intento Fallido de Login'),
        (ACCION_CAMBIO_PASSWORD, 'Cambio de Contraseña'),
        (ACCION_2FA_ACTIVADO, '2FA Activado'),
        (ACCION_2FA_DESACTIVADO, '2FA Desactivado'),
        (ACCION_VER_EXPEDIENTE, 'Ver Expediente Clínico'),
        (ACCION_EDITAR_EXPEDIENTE, 'Editar Expediente Clínico'),
        (ACCION_ELIMINAR_REGISTRO, 'Eliminar Registro'),
        (ACCION_EXPORTAR_DATOS, 'Exportar Datos'),
        (ACCION_CAMBIO_PERMISOS, 'Cambio de Permisos'),
        (ACCION_ACCESO_ADMINISTRACION, 'Acceso a Administración'),
        (ACCION_MODIFICAR_RESULTADO_LAB, 'Modificar Resultado de Laboratorio'),
        (ACCION_CANCELAR_FACTURA, 'Cancelar Factura'),
    ]
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='logs_acciones_sensibles',  # Cambiado para evitar conflicto
        verbose_name="Usuario"
    )
    
    accion = models.CharField(
        max_length=50,
        choices=ACCION_CHOICES,
        help_text='Tipo de acción realizada'
    )
    
    descripcion = models.TextField(
        help_text='Descripción detallada de la acción'
    )
    
    # Información contextual
    modelo_afectado = models.CharField(
        max_length=100,
        blank=True,
        help_text='Modelo de Django afectado (ej: Paciente, OrdenDeServicio)'
    )
    
    objeto_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID del objeto afectado'
    )
    
    objeto_repr = models.CharField(
        max_length=255,
        blank=True,
        help_text='Representación del objeto afectado'
    )
    
    # Datos antes/después (para cambios)
    datos_anteriores = models.JSONField(
        null=True,
        blank=True,
        help_text='Datos antes de la modificación (JSON)'
    )
    
    datos_nuevos = models.JSONField(
        null=True,
        blank=True,
        help_text='Datos después de la modificación (JSON)'
    )
    
    # Información técnica
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='Dirección IP del cliente'
    )
    
    user_agent = models.TextField(
        blank=True,
        default='',
        help_text='User agent del navegador'
    )
    
    ruta_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Ruta URL de la acción'
    )
    
    metodo_http = models.CharField(
        max_length=10,
        blank=True,
        help_text='Método HTTP (GET, POST, etc.)'
    )
    
    # Timestamp
    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='Fecha y hora de la acción'
    )
    
    # Severidad
    SEVERIDAD_INFO = 'INFO'
    SEVERIDAD_WARNING = 'WARNING'
    SEVERIDAD_CRITICAL = 'CRITICAL'
    SEVERIDAD_CHOICES = [
        (SEVERIDAD_INFO, 'Informativa'),
        (SEVERIDAD_WARNING, 'Advertencia'),
        (SEVERIDAD_CRITICAL, 'Crítica'),
    ]
    
    severidad = models.CharField(
        max_length=20,
        choices=SEVERIDAD_CHOICES,
        default=SEVERIDAD_INFO,
        help_text='Severidad de la acción'
    )
    
    # Resultado
    exitosa = models.BooleanField(
        default=True,
        help_text='La acción fue exitosa'
    )
    
    mensaje_error = models.TextField(
        blank=True,
        help_text='Mensaje de error si la acción falló'
    )
    
    class Meta:
        verbose_name = 'Log de Acción Sensible'
        verbose_name_plural = 'Logs de Acciones Sensibles'
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['usuario', 'fecha_hora']),
            models.Index(fields=['accion', 'fecha_hora']),
            models.Index(fields=['severidad', 'fecha_hora']),
        ]
    
    def save(self, *args, **kwargs):
        if self.user_agent is None:
            self.user_agent = ''
        if self.ruta_url is None:
            self.ruta_url = ''
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario} - {self.get_accion_display()} - {self.fecha_hora.strftime('%Y-%m-%d %H:%M:%S')}"

    @staticmethod
    def registrar(usuario, accion, descripcion, **kwargs):
        """
        Método helper para registrar acciones de forma rápida.
        
        Uso:
        LogAccionSensible.registrar(
            usuario=request.user,
            accion=LogAccionSensible.ACCION_VER_EXPEDIENTE,
            descripcion="Accedió al expediente del paciente Juan Pérez",
            modelo_afectado="Paciente",
            objeto_id=paciente.id,
            objeto_repr=str(paciente),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            ruta_url=request.path,
            metodo_http=request.method
        )
        """
        kwargs['user_agent'] = kwargs.get('user_agent') or ''
        kwargs['ruta_url'] = kwargs.get('ruta_url') or ''
        return LogAccionSensible.objects.create(
            usuario=usuario,
            accion=accion,
            descripcion=descripcion,
            **kwargs
        )
