"""
PORTAL DEL PACIENTE - MODELOS
Sistema de acceso web para que los pacientes consulten su información médica
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
import uuid
import secrets


class UsuarioPacienteManager(BaseUserManager):
    """Manager personalizado para UsuarioPaciente"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class UsuarioPaciente(AbstractBaseUser):
    """
    Usuario del portal del paciente (separado de Usuario del sistema).
    Permite a los pacientes acceder a su información médica.
    """
    # Relación con el paciente del sistema
    paciente = models.OneToOneField(
        'core.Paciente', 
        on_delete=models.CASCADE, 
        related_name='usuario_portal'
    )
    
    # Credenciales
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    
    # Estado de la cuenta
    is_active = models.BooleanField(default=True)
    email_verificado = models.BooleanField(default=False)
    
    # Tokens
    token_verificacion = models.UUIDField(default=uuid.uuid4, editable=False)
    token_recuperacion = models.CharField(max_length=100, blank=True)
    token_recuperacion_expira = models.DateTimeField(null=True, blank=True)
    
    # Fechas
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)
    
    # Configuración
    notificaciones_email = models.BooleanField(default=True)
    notificaciones_sms = models.BooleanField(default=False)
    
    objects = UsuarioPacienteManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'Usuario del Portal'
        verbose_name_plural = 'Usuarios del Portal'
    
    def __str__(self):
        return f"{self.email} - {self.paciente.nombre_completo}"
    
    def generar_token_recuperacion(self):
        """Genera un token de recuperación de contraseña"""
        self.token_recuperacion = secrets.token_urlsafe(32)
        self.token_recuperacion_expira = timezone.now() + timezone.timedelta(hours=24)
        self.save(update_fields=['token_recuperacion', 'token_recuperacion_expira'])
        return self.token_recuperacion
    
    def verificar_email(self):
        """Marca el email como verificado"""
        self.email_verificado = True
        self.save(update_fields=['email_verificado'])


class SolicitudAccesoPortal(models.Model):
    """
    Solicitud de un paciente para obtener acceso al portal.
    Requiere validación por parte del personal.
    """
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_APROBADA = 'APROBADA'
    ESTADO_RECHAZADA = 'RECHAZADA'
    
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_APROBADA, 'Aprobada'),
        (ESTADO_RECHAZADA, 'Rechazada'),
    ]
    
    # Información del solicitante
    nombre_completo = models.CharField(max_length=255)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)
    fecha_nacimiento = models.DateField()
    numero_identificacion = models.CharField(max_length=50, help_text="CURP o ID")
    
    # Relación con paciente existente (se asigna al aprobar)
    paciente = models.ForeignKey(
        'core.Paciente', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='solicitudes_portal'
    )
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    
    # Auditoría
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    respondido_por = models.ForeignKey(
        'core.Usuario', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    motivo_rechazo = models.TextField(blank=True)
    
    # IP tracking
    ip_solicitud = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Solicitud de Acceso al Portal'
        verbose_name_plural = 'Solicitudes de Acceso al Portal'
        ordering = ['-fecha_solicitud']
    
    def __str__(self):
        return f"{self.nombre_completo} - {self.get_estado_display()}"


class AccesoExpedientePortal(models.Model):
    """
    Log de accesos al expediente desde el portal (auditoría).
    """
    usuario_portal = models.ForeignKey(
        UsuarioPaciente, 
        on_delete=models.CASCADE,
        related_name='accesos_expediente'
    )
    fecha_acceso = models.DateTimeField(auto_now_add=True)
    seccion_consultada = models.CharField(
        max_length=100,
        help_text="Ej: consultas, laboratorio, recetas, etc."
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500, blank=True)
    
    class Meta:
        verbose_name = 'Acceso al Expediente (Portal)'
        verbose_name_plural = 'Accesos al Expediente (Portal)'
        ordering = ['-fecha_acceso']
    
    def __str__(self):
        return f"{self.usuario_portal.email} - {self.seccion_consultada} - {self.fecha_acceso}"
