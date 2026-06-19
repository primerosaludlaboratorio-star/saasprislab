"""
core/models/base.py
Capa SaaS: Identidad institucional, usuarios y modelos fundacionales.
Sin dependencias internas a otros fragmentos de core/models/.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import date
import uuid

from core.validators import (
    validate_image_upload,
    validate_document_upload,
    validate_audio_upload,
    validate_backup_upload,
    validate_fecha_nacimiento_razonable,
)


# ==============================================================================
# FUNCIÓN HELPER PARA STORAGE BACKEND (Drive / Local)
# ==============================================================================
def get_google_drive_storage():
    """
    Retorna el storage backend apropiado (Drive → local).
    Prioridad: Google Drive → FileSystem (dev).
    """
    from django.conf import settings

    # Prioridad 1: Drive activo
    if getattr(settings, '_DRIVE_STORAGE_ACTIVO', False):
        try:
            from config.storage_backends import TenantDriveStorage
            return TenantDriveStorage()
        except Exception:
            pass

    # Prioridad 2: Local (desarrollo o VPS sin Drive)
    from django.core.files.storage import default_storage
    return default_storage


# ==============================================================================
# 0. MODELO BASE ABSTRACTO DE AUDITORÍA
# ==============================================================================
class AuditoriaModel(models.Model):
    """
    Modelo abstracto con campos de auditoría estándar.
    Heredar en catálogos (SeccionLaboratorio, PerfilLaboratorio) y entidades LIMS (`lims.Analito`, etc.) y
    cualquier entidad nueva que requiera trazabilidad de creación/modificación.
    Campos con null=True permiten retrocompatibilidad con registros legacy ya existentes.
    """
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True, blank=True,
        verbose_name="Creado el",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True, blank=True,
        verbose_name="Actualizado el",
    )
    class Meta:
        abstract = True


# ==============================================================================
# 1. CAPA SaaS: IDENTIDAD INSTITUCIONAL
# ==============================================================================
class Empresa(models.Model):
    """Define la identidad de la clínica o farmacia (ej. PRISLAB, Clínica del Valle)."""
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la Institución")
    rfc = models.CharField(max_length=20, blank=True, null=True, verbose_name="RFC")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección Fiscal")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    periodo_vigencia = models.CharField(max_length=50, default="2024-2030", verbose_name="Periodo de Vigencia Actual")
    farmacia_dias_max_antiguedad_receta = models.PositiveSmallIntegerField(
        default=30,
        verbose_name="Farmacia: antigüedad máxima de receta (días)",
        help_text="Rechazo de dispensación si la receta supera estos días (política COFEPRIS / institucional).",
    )
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, verbose_name="Logotipo Oficial", validators=[validate_image_upload])

    color_primario = models.CharField(max_length=7, default="#D9230F", verbose_name="Color Primario", help_text="Color principal de la marca (hex)")
    color_secundario = models.CharField(max_length=7, default="#2B3A42", verbose_name="Color Secundario", help_text="Color secundario Oxford Grey (hex)")
    color_fondo = models.CharField(max_length=7, default="#FFFFFF", verbose_name="Color de Fondo", help_text="Color de fondo predeterminado (hex)")
    css_personalizado = models.TextField(blank=True, null=True, verbose_name="CSS Personalizado", help_text="Estilos CSS adicionales para personalización avanzada")
    activa = models.BooleanField(default=True, verbose_name="Empresa Activa")

    # ── Responsable Sanitario (ISO 15189 / COFEPRIS) — datos dinámicos ────────
    responsable_sanitaria_nombre = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name="Nombre Responsable Sanitario",
        help_text="Nombre completo con título profesional (ej. Q.B. Nombre Apellido). Aparece en todos los reportes.",
    )
    responsable_sanitaria_cedula = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name="Cédula Prof. Responsable",
        help_text="Cédula profesional del Responsable Sanitario registrada ante SEP/COFEPRIS.",
    )
    responsable_sanitaria_cofepris = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name="Registro COFEPRIS",
        help_text="Número de registro COFEPRIS del Responsable Sanitario (si aplica).",
    )

    # ── BYOK: Bring Your Own Key (API Key Gemini por tenant) ──────────────────
    byok_gemini_api_key_enc = models.TextField(
        blank=True, null=True,
        verbose_name="API Key Gemini (cifrada)",
        help_text=(
            "Clave API de Google Gemini propia del laboratorio, cifrada con Fernet. "
            "Si está configurada, los costos de IA los asume directamente el cliente. "
            "Si vacía, se usa la MASTER_API_KEY de PRISLAB y se descuenta de la cuota contratada."
        ),
    )

    # ── BYOD: Google Drive por tenant ─────────────────────────────────────────
    drive_client_config_enc = models.TextField(
        blank=True, null=True,
        verbose_name="Drive Config (JSON cifrado)",
        help_text="JSON de Service Account de Google Drive del laboratorio, cifrado con Fernet.",
    )
    drive_folder_id = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name="Google Drive Folder ID",
        help_text="ID de la carpeta raíz en Google Drive donde se guardarán audios, PDFs y respaldos.",
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Empresa / Institución"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return f"{self.nombre} ({self.periodo_vigencia})"

    # ── Helpers de cifrado ────────────────────────────────────────────────────
    def _fernet(self):
        from cryptography.fernet import Fernet
        from django.conf import settings
        key = getattr(settings, 'FERNET_KEY', None)
        if not key:
            raise ValueError("FERNET_KEY no configurada en settings/entorno.")
        return Fernet(key.encode() if isinstance(key, str) else key)

    def set_byok_gemini_key(self, plain_key: str):
        """Cifra y guarda la API Key de Gemini."""
        if plain_key:
            self.byok_gemini_api_key_enc = self._fernet().encrypt(plain_key.encode()).decode()
        else:
            self.byok_gemini_api_key_enc = None

    def get_byok_gemini_key(self) -> str | None:
        """Descifra y retorna la API Key de Gemini; None si no está configurada."""
        if not self.byok_gemini_api_key_enc:
            return None
        try:
            return self._fernet().decrypt(self.byok_gemini_api_key_enc.encode()).decode()
        except Exception:
            return None

    def set_drive_config(self, json_str: str):
        if json_str:
            self.drive_client_config_enc = self._fernet().encrypt(json_str.encode()).decode()
        else:
            self.drive_client_config_enc = None

    def get_drive_config(self) -> str | None:
        if not self.drive_client_config_enc:
            return None
        try:
            return self._fernet().decrypt(self.drive_client_config_enc.encode()).decode()
        except Exception:
            return None

    def tiene_byok_gemini(self) -> bool:
        return bool(self.get_byok_gemini_key())

    def tiene_drive_propio(self) -> bool:
        return bool(self.drive_folder_id and self.get_drive_config())


class Sucursal(models.Model):
    """Sucursal o punto de atención de una empresa (multi-tenant)."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='sucursales')
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la Sucursal")
    codigo_sucursal = models.CharField(max_length=50, unique=True, verbose_name="Código de Sucursal", help_text="Código único identificador (ej: SUC-001)")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    responsable = models.CharField(max_length=255, blank=True, null=True, verbose_name="Responsable")
    activa = models.BooleanField(default=True, verbose_name="Sucursal Activa")
    gestion_inventario_activa = models.BooleanField(
        default=True,
        verbose_name="Gestión de inventario (laboratorio)",
        help_text=(
            "Si está desactivado (modo ágil / pruebas), no se descuentan reactivos por FEFO al validar "
            "resultados de laboratorio para órdenes de esta sucursal. Si está activado, aplican las reglas "
            "estrictas de consumo y lotes."
        ),
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        app_label = 'core'
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.codigo_sucursal})"


class ConfiguracionModulos(models.Model):
    """Feature Toggles: Interruptores de módulos según contrato de la empresa."""
    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name='configuracion_modulos',
        verbose_name="Empresa"
    )

    modulo_laboratorio = models.BooleanField(default=True, verbose_name="Módulo Laboratorio", help_text="Activar/desactivar módulo de laboratorio clínico")
    modulo_farmacia = models.BooleanField(default=True, verbose_name="Módulo Farmacia", help_text="Activar/desactivar módulo de farmacia y PDV")
    modulo_expediente_clinico = models.BooleanField(default=False, verbose_name="Módulo Expediente Clínico", help_text="Activar/desactivar expediente clínico electrónico (ECE)")
    modulo_consulta_externa = models.BooleanField(default=False, verbose_name="Módulo Consulta Externa", help_text="Activar/desactivar módulo de consulta externa")
    modulo_hospitalizacion = models.BooleanField(default=False, verbose_name="Módulo Hospitalización", help_text="Activar/desactivar módulo de hospitalización")
    modulo_citas = models.BooleanField(default=False, verbose_name="Módulo Citas", help_text="Activar/desactivar módulo de agendamiento de citas")
    modulo_rrhh = models.BooleanField(default=False, verbose_name="Módulo Recursos Humanos", help_text="Activar/desactivar módulo de RRHH (Reloj Checador, Evaluaciones)")
    modulo_contabilidad = models.BooleanField(default=False, verbose_name="Módulo Contabilidad", help_text="Activar/desactivar módulo de contabilidad avanzada")
    modulo_ia = models.BooleanField(default=True, verbose_name="Módulo Inteligencia Artificial", help_text="Activar/desactivar funciones de IA (OCR, Voz)")
    modulo_iot = models.BooleanField(default=False, verbose_name="Módulo IoT", help_text="Activar/desactivar módulo IoT (Kioscos, sensores)")

    # ── Modo de consumo de IA ─────────────────────────────────────────────────
    MODO_IA_APRENDIZAJE = 'APRENDIZAJE'
    MODO_IA_PRODUCCION  = 'PRODUCCION'
    MODO_IA_AHORRO      = 'AHORRO_EXTREMO'
    MODO_IA_CHOICES = [
        (MODO_IA_APRENDIZAJE, '🧠 Aprendizaje — IA activa para poblar la base de reglas locales'),
        (MODO_IA_PRODUCCION,  '🚀 Producción — IA completa con caché de reglas activo'),
        (MODO_IA_AHORRO,      '💡 Ahorro Extremo — Solo RAG local y checklist. Sin IA generativa'),
    ]
    modo_ia = models.CharField(
        max_length=20, choices=MODO_IA_CHOICES, default=MODO_IA_PRODUCCION,
        verbose_name="Modo de Consumo de IA",
        help_text="Controla el nivel de uso de la API de Gemini.",
    )

    # ── Cuota mensual de tokens (solo aplica cuando usa la MASTER_KEY) ────────
    limite_mensual_tokens_ia = models.PositiveIntegerField(
        default=50_000,
        verbose_name="Límite Mensual de Tokens IA",
        help_text="Tokens mensuales contratados cuando el lab usa la API Key maestra de PRISLAB.",
    )
    alerta_consumo_80_enviada = models.BooleanField(
        default=False, verbose_name="Alerta 80% enviada",
        help_text="Se resetea automáticamente al inicio de cada mes.",
    )
    alerta_consumo_90_enviada = models.BooleanField(
        default=False, verbose_name="Alerta 90% enviada",
    )

    pin_precio_neto = models.CharField(
        max_length=10, default='1234',
        verbose_name="PIN Precio Neto (Staff)",
        help_text="PIN numérico para autorizar descuento a precio de costo. Default: 1234"
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")

    class Meta:
        app_label = 'core'
        verbose_name = "Configuración de Módulos"
        verbose_name_plural = "Configuraciones de Módulos"

    def __str__(self):
        return f"Configuración Módulos - {self.empresa.nombre}"


class Usuario(AbstractUser):
    """Usuario personalizado con roles y pertenencia a empresa SaaS."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='usuarios', null=True, blank=True)
    sucursal = models.ForeignKey('Sucursal', on_delete=models.SET_NULL, related_name='usuarios', null=True, blank=True, verbose_name="Sucursal de Trabajo")
    rol = models.CharField(
        max_length=50,
        choices=[
            ('ADMIN', 'Administrador'),
            ('DIRECTOR', 'Director General / Dueño'),
            ('CAJERO', 'Cajero'),
            ('MEDICO', 'Médico'),
            ('QUIMICO', 'Químico'),
            ('RECEPCION', 'Recepción'),
            ('GERENTE', 'Gerente'),
        ],
        default='CAJERO',
        verbose_name="Rol de Usuario"
    )
    puede_usar_ia = models.BooleanField(
        default=False,
        verbose_name="Puede usar IA Prislab",
        help_text="Permite acceso a funciones de inteligencia artificial"
    )
    tiempo_actividad_inicio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Inicio de Sesión Activa",
        help_text="Timestamp de inicio de sesión activa para rastrear tiempo continuo y sugerir descansos"
    )
    nivel_ia = models.CharField(
        max_length=20,
        choices=[
            ('IA_BASICA', 'IA Básica (Solo lectura de estudios y precios)'),
            ('IA_TECNICA', 'IA Técnica (Resultados de laboratorio y valores de referencia)'),
            ('IA_MASTER', 'IA Master (Acceso completo: costos, compras, márgenes)'),
        ],
        default='IA_BASICA',
        verbose_name="Nivel de Acceso a IA",
        help_text="Define qué información puede consultar la IA según el nivel del usuario"
    )
    departamento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Departamento / Área")
    cedula_interna = models.CharField(max_length=50, blank=True, null=True, verbose_name="ID Interno / Cédula")

    totp_secret = models.CharField(
        max_length=64, blank=True, default='',
        verbose_name="TOTP Secret (2FA)",
        help_text="Clave secreta TOTP para autenticación de dos factores"
    )
    mfa_activo = models.BooleanField(
        default=False,
        verbose_name="2FA Activado",
        help_text="Si True, se requiere código TOTP en cada inicio de sesión"
    )

    es_auditor_supremo = models.BooleanField(
        default=False,
        verbose_name="Auditor Supremo / Super Master",
        help_text="Flag adicional para superusuarios con auditoria total sobre Prisci y el sistema.",
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Usuario del Sistema"
        verbose_name_plural = "Usuarios"

    def save(self, *args, **kwargs):
        # Solo inyectar empresa por defecto en guardado completo. Los saves parciales
        # (p. ej. last_login tras login) no deben reasignar tenant si empresa_id es NULL.
        update_fields = kwargs.get('update_fields')
        if update_fields is None and self.empresa_id is None:
            from core.utils.default_empresa import resolve_default_empresa_sistema

            de = resolve_default_empresa_sistema()
            if de is not None:
                self.empresa = de
        super().save(*args, **kwargs)

    def tiene_permiso_ia_master(self):
        """Verifica si el usuario tiene acceso de nivel MASTER a la IA."""
        return self.nivel_ia == 'IA_MASTER' or self.is_superuser or self.rol == 'ADMIN'

    def puede_ver_ia_negocios(self):
        """Verifica si el usuario puede ver el botón de 'Consultar IA de Negocios'."""
        return self.tiene_permiso_ia_master() or self.rol in ['ADMIN']


# ==============================================================================
# 1B. CEREBRO PRISLAB (RAG): Bóveda de Documentos de Conocimiento
# ==============================================================================
class DocumentoConocimiento(models.Model):
    """
    Bóveda de Documentos para RAG (Manual Operativo, Biblioteca Médica, Guías, etc.).
    Se ingestan PDFs a una base vectorial local (Chroma) para consulta experta.
    """
    CATEGORIA_MANUAL = "MANUAL"
    CATEGORIA_LIBRO = "LIBRO_MEDICO"
    CATEGORIA_GUIA = "GUIA"
    CATEGORIA_VENTAS_ETICAS = "VENTAS_ETICAS"
    CATEGORIA_ATENCION_DISNEY = "ATENCION_DISNEY"
    CATEGORIA_LIDERAZGO = "LIDERAZGO"
    CATEGORIA_CHOICES = [
        (CATEGORIA_MANUAL, "Manual Operativo"),
        (CATEGORIA_LIBRO, "Biblioteca Médica"),
        (CATEGORIA_GUIA, "Guía"),
        (CATEGORIA_VENTAS_ETICAS, "Academy: Ventas Éticas"),
        (CATEGORIA_ATENCION_DISNEY, "Academy: Atención Disney"),
        (CATEGORIA_LIDERAZGO, "Academy: Liderazgo"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="documentos_conocimiento")
    sucursal = models.ForeignKey(
        "Sucursal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_conocimiento",
        help_text="Opcional: si el documento aplica solo a una sucursal.",
    )
    titulo = models.CharField(max_length=255)
    archivo_pdf = models.FileField(upload_to="conocimiento/%Y/%m/%d/", validators=[validate_document_upload])
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default=CATEGORIA_MANUAL)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    procesado = models.BooleanField(default=False, help_text="True si ya fue ingerido a la base vectorial.")
    error_procesado = models.TextField(blank=True, null=True, help_text="Error de ingesta si ocurrió.")
    drive_file_id = models.CharField(max_length=200, blank=True, null=True, help_text="ID del archivo en Google Drive si fue archivado.")
    drive_folder_id = models.CharField(max_length=200, blank=True, null=True, help_text="ID de carpeta Drive usada para archivado.")

    class Meta:
        app_label = 'core'
        verbose_name = "Documento de Conocimiento"
        verbose_name_plural = "Documentos de Conocimiento"
        ordering = ["-fecha_carga"]

    def __str__(self) -> str:
        return f"{self.titulo} [{self.get_categoria_display()}]"


# ==============================================================================
# 10. MÓDULOS "COHETE" (Estructura inicial)
# ==============================================================================
class DatosFiscales(models.Model):
    """Datos fiscales para Facturación 4.0 (estructura base)."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='datos_fiscales')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, related_name='datos_fiscales')

    razon_social = models.CharField(max_length=255)
    rfc = models.CharField(max_length=20)
    regimen_fiscal = models.CharField(max_length=100, blank=True, null=True)
    uso_cfdi = models.CharField(max_length=50, blank=True, null=True)
    domicilio_fiscal = models.TextField(blank=True, null=True)
    email_facturacion = models.EmailField(blank=True, null=True)

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Datos Fiscales"
        verbose_name_plural = "Datos Fiscales"
        ordering = ['-fecha_creacion']

    def __str__(self) -> str:
        return f"{self.razon_social} ({self.rfc})"


class ControlCalidad(models.Model):
    """Registro de control de calidad (base) para Levey-Jennings."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='controles_calidad')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, related_name='controles_calidad')

    equipo = models.CharField(max_length=255, help_text="Equipo/analizador (ej. Fuji, Wondfo)")
    lote = models.CharField(max_length=100, help_text="Lote del control/reactivo")
    nivel = models.CharField(max_length=50, blank=True, null=True, help_text="Nivel de control (ej. Bajo/Normal/Alto)")
    parametro = models.CharField(max_length=255, help_text="Parámetro medido (ej. Glucosa)")
    valor = models.DecimalField(max_digits=12, decimal_places=4)
    desviacion = models.DecimalField(max_digits=12, decimal_places=4, help_text="Desviación vs media/target")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Control de Calidad"
        verbose_name_plural = "Controles de Calidad"
        ordering = ['-fecha_registro']

    def __str__(self) -> str:
        return f"{self.parametro} {self.valor} ({self.equipo})"


class RutaLogistica(models.Model):
    """Rastreo/logística (estructura base) para entregas y traslados."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='rutas_logisticas')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, related_name='rutas_logisticas')

    chofer = models.CharField(max_length=255)
    latitud = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Ruta Logística"
        verbose_name_plural = "Rutas Logísticas"
        ordering = ['-timestamp']

    def __str__(self) -> str:
        return f"{self.chofer} @ {self.timestamp:%Y-%m-%d %H:%M}"
