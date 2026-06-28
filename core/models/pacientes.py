"""
core/models/pacientes.py
Modelo Paciente y relacionados.
Depende de: base.py
"""
from django.db import models
import uuid

from core.tenant import TenantModel
from core.validators import validate_fecha_nacimiento_razonable
from .base import Empresa, Sucursal


# ==============================================================================
# MODELO PACIENTE
# ==============================================================================
class Paciente(TenantModel):
    """Modelo híbrido: Pacientes ambulatorios (Lab) con datos completos vs. Externos (Farmacia) sin expediente."""

    TIPOS_PACIENTE = [
        ('EMPLEADO', 'Empleado / Staff'),
        ('FAMILIA', 'Familia Directa'),
        ('INAPAM', 'INAPAM / Tercera Edad'),
        ('GENERAL', 'Cliente General'),
    ]

    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='pacientes')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sucursal de Registro")

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        null=True,
        verbose_name="UUID del Paciente",
        help_text="Identificador único universal (inmutable) para trazabilidad entre módulos"
    )

    nombres = models.CharField(max_length=150, blank=True, default='', verbose_name="Nombre(s)",
        help_text="Nombre(s) de pila del paciente")
    apellido_paterno = models.CharField(max_length=100, blank=True, default='', verbose_name="Apellido Paterno")
    apellido_materno = models.CharField(max_length=100, blank=True, default='', verbose_name="Apellido Materno")
    nombre_completo = models.CharField(max_length=255, verbose_name="Nombre Completo")
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Nacimiento",
        help_text="Obligatorio para pacientes ambulatorios (Lab)",
        validators=[validate_fecha_nacimiento_razonable])
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, null=True, blank=True, verbose_name="Sexo",
        help_text="Obligatorio para valores de referencia")

    telefono = models.CharField(max_length=20, null=True, blank=True, verbose_name="Teléfono",
        help_text="Para WhatsApp y contacto")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    consentimiento_marketing = models.BooleanField(
        default=False,
        verbose_name="Consentimiento de Marketing"
    )

    alergias = models.TextField(default='Ninguna', verbose_name="Alergias Conocidas",
        help_text="Lista de alergias o 'Ninguna'")

    tipo = models.CharField(max_length=20, choices=TIPOS_PACIENTE, default='GENERAL', verbose_name="Tipo de Paciente")
    es_externo = models.BooleanField(default=False, verbose_name="Paciente Externo",
        help_text="True si es referido de otro establecimiento")

    politica_descuento = models.ForeignKey(
        'DiscountPolicy',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Política de Descuento Asignada"
    )

    datos_fiscales = models.OneToOneField(
        'DatosFiscales',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paciente',
        verbose_name="Datos Fiscales (4.0)",
        help_text="Opcional: datos fiscales para facturación (CFDI) asociados al paciente."
    )

    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    activo = models.BooleanField(default=True, verbose_name="Paciente Activo")

    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Eliminación",
        help_text="Para Soft Delete - no borrar físicamente")
    motivo_eliminacion = models.TextField(blank=True, null=True, verbose_name="Motivo de Eliminación")

    class Meta:
        app_label = 'core'
        verbose_name = "Paciente / Cliente"
        verbose_name_plural = "Pacientes / Clientes"
        ordering = ['nombre_completo']
        indexes = [
            models.Index(fields=['nombre_completo'], name='core_pacien_nombre__382ec8_idx'),
            models.Index(fields=['telefono'], name='core_pacien_telefon_683de7_idx'),
            models.Index(fields=['nombres'], name='core_pacien_nombres_a2350b_idx'),
            models.Index(fields=['apellido_paterno'], name='core_pacien_apellid_950393_idx'),
        ]

    def calcular_edad(self):
        """Calcula la edad del paciente basándose en la fecha de nacimiento."""
        if not self.fecha_nacimiento:
            return None
        from datetime import date
        hoy = date.today()
        edad = hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )
        return edad

    @property
    def edad(self):
        """Propiedad para acceder a la edad calculada."""
        return self.calcular_edad()

    def generar_pris_id(self):
        """Genera un ID único para el paciente (PRIS-ID)."""
        import uuid as _uuid
        if not hasattr(self, '_pris_id') or not self._pris_id:
            fecha_str = self.fecha_registro.strftime('%Y%m%d')
            uuid_str = str(_uuid.uuid4())[:8].upper()
            return f"PRIS-{fecha_str}-{uuid_str}"
        return self._pris_id

    @staticmethod
    def _normalizar_nombre(valor):
        """Normaliza un campo de nombre: strip, colapsar espacios, title case."""
        if not valor:
            return valor
        import re
        valor = valor.strip()
        valor = re.sub(r'\s+', ' ', valor)
        valor = valor.title()
        return valor

    def save(self, *args, **kwargs):
        """Auto-genera nombre_completo a partir de campos separados con normalización."""
        self.nombres = self._normalizar_nombre(self.nombres) or ''
        self.apellido_paterno = self._normalizar_nombre(self.apellido_paterno) or ''
        self.apellido_materno = self._normalizar_nombre(self.apellido_materno) or ''

        if self.nombres or self.apellido_paterno or self.apellido_materno:
            partes = [p for p in [self.nombres, self.apellido_paterno, self.apellido_materno] if p]
            if partes:
                self.nombre_completo = ' '.join(partes)
                if len(self.nombre_completo) > 255:
                    self.nombre_completo = self.nombre_completo[:255]
        elif self.nombre_completo:
            self.nombre_completo = self._normalizar_nombre(self.nombre_completo) or self.nombre_completo

        if self.nombre_completo and not self.nombres and not self.apellido_paterno:
            partes = self.nombre_completo.strip().split()
            if len(partes) >= 3:
                self.apellido_materno = partes[-1]
                self.apellido_paterno = partes[-2]
                self.nombres = ' '.join(partes[:-2])
            elif len(partes) == 2:
                self.nombres = partes[0]
                self.apellido_paterno = partes[1]
            elif len(partes) == 1:
                self.nombres = partes[0]

        super().save(*args, **kwargs)

    def __str__(self):
        tipo_display = self.get_tipo_display()
        externo = " (Externo)" if self.es_externo else ""
        return f"{self.nombre_completo} - {tipo_display}{externo}"
