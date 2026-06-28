"""
Bankguard v1.14 — Modelos de Control Financiero y Cierre de Día
Nivel 2: Políticas de Límites | Nivel 3: Cierre Consolidado con Hash
"""
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
import hashlib

from core.models.base import Empresa, Usuario


class PoliticaLimitesCaja(models.Model):
    """
    NIVEL 2: Matriz de riesgos financieros por empresa.
    
    Define umbrales de autorización para gastos de caja:
    - Zona Verde (≤ limite_verde): Auto-aprobado
    - Zona Amarilla (≤ limite_amarillo): Requiere comprobante
    - Zona Roja (> limite_amarillo): Requiere autorización del Director
    """
    empresa = models.OneToOneField(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='politica_caja',
        verbose_name="Empresa"
    )
    
    # Umbrales de riesgo
    limite_verde = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('100.00'),
        verbose_name="Límite Zona Verde ($)",
        help_text="Gastos ≤ este monto: auto-aprobados"
    )
    
    limite_amarillo = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('500.00'),
        verbose_name="Límite Zona Amarilla ($)",
        help_text="Gastos entre verde y amarillo: requieren comprobante"
    )
    
    # Nota: Todo lo superior a limite_amarillo es Zona Roja (requiere autorización Director)
    
    # Auditoría
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='politicas_caja_creadas',
        verbose_name="Creado por"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'core'
        verbose_name = "Política de Límites de Caja"
        verbose_name_plural = "Políticas de Límites de Caja"
    
    def __str__(self):
        return f"Política {self.empresa.nombre} — Verde:${self.limite_verde} / Amarillo:${self.limite_amarillo}"
    
    def clean(self):
        """Validar que amarillo > verde."""
        if self.limite_amarillo <= self.limite_verde:
            raise ValidationError("El límite amarillo debe ser mayor que el límite verde.")
    
    def evaluar_gasto(self, monto):
        """
        Evalúa un monto contra la política.
        
        Returns:
            dict: {'zona': 'verde'|'amarillo'|'roja', 'requiere_comprobante': bool, 'requiere_autorizacion': bool}
        """
        monto = Decimal(str(monto))
        
        if monto <= self.limite_verde:
            return {
                'zona': 'verde',
                'requiere_comprobante': False,
                'requiere_autorizacion': False,
                'limite': self.limite_verde
            }
        elif monto <= self.limite_amarillo:
            return {
                'zona': 'amarillo',
                'requiere_comprobante': True,
                'requiere_autorizacion': False,
                'limite': self.limite_amarillo
            }
        else:
            return {
                'zona': 'roja',
                'requiere_comprobante': True,
                'requiere_autorizacion': True,
                'limite': self.limite_amarillo
            }


class GastoCajaEndurecido(models.Model):
    """
    Gasto de caja con validación de políticas (Nivel 2).
    
    Reemplaza/extiende el modelo GastoCaja existente con:
    - Comprobante obligatorio para zona amarilla
    - Autorización explícita para zona roja
    - Auditoría de quién autorizó
    """
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE,
        related_name='gastos_caja_endurecidos'
    )
    usuario_registro = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='gastos_caja_registrados',
        verbose_name="Registrado por"
    )
    
    concepto = models.CharField(max_length=255, verbose_name="Concepto")
    monto = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Monto ($)"
    )
    
    # Comprobante (obligatorio para zona amarilla+)
    comprobante = models.FileField(
        upload_to='gastos_caja/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Comprobante (PDF/Foto)",
        help_text="Obligatorio para gastos superiores al límite verde"
    )
    
    # Autorización (requerida para zona roja)
    autorizado = models.BooleanField(
        default=False,
        verbose_name="Autorizado",
        help_text="Requerido para gastos en Zona Roja (>$500)"
    )
    autorizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gastos_caja_autorizados',
        verbose_name="Autorizado por"
    )
    fecha_autorizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Autorización"
    )
    
    # Metadatos
    fecha_registro = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    class Meta:
        app_label = 'core'
        verbose_name = "Gasto de Caja (Endurecido)"
        verbose_name_plural = "Gastos de Caja (Endurecidos)"
        ordering = ['-fecha_registro']
    
    def __str__(self):
        return f"-{self.monto} | {self.concepto} | {self.usuario_registro}"
    
    def clean(self):
        """Validación de políticas de límites."""
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        
        # Obtener política de la empresa
        politica = getattr(self.empresa, 'politica_caja', None)
        if not politica:
            raise ValidationError(
                f"La empresa {self.empresa.nombre} no tiene política de límites configurada. "
                "Contacte al administrador."
            )
        
        evaluacion = politica.evaluar_gasto(self.monto)
        
        # Zona Amarilla: comprobante obligatorio
        if evaluacion['zona'] in ['amarillo', 'roja'] and not self.comprobante:
            raise ValidationError(
                f"Gastos superiores a ${politica.limite_verde} requieren comprobante obligatorio. "
                f"(Zona {evaluacion['zona'].upper()})"
            )
        
        # Zona Roja: autorización obligatoria
        if evaluacion['zona'] == 'roja' and not self.autorizado:
            raise ValidationError(
                f"🚫 ZONA ROJA: Este gasto de ${self.monto} supera el límite de ${politica.limite_amarillo}. "
                f"Requiere autorización explícita del Director."
            )
        
        # Si está autorizado, debe tener autorizado_por
        if self.autorizado and not self.autorizado_por:
            raise ValidationError("El campo 'Autorizado por' es obligatorio si está marcado como autorizado.")
        
        if self.autorizado and not self.fecha_autorizacion:
            self.fecha_autorizacion = timezone.now()
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class CierreDiaConsolidado(models.Model):
    """
    NIVEL 3: Cierre de día con hash SHA-256 de integridad.
    
    Almacena el consolidado financiero del día y genera un hash
    que detecta cualquier alteración posterior.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='cierres_dia',
        verbose_name="Empresa"
    )
    sucursal = models.ForeignKey(
        'core.Sucursal',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cierres_dia',
        verbose_name="Sucursal"
    )
    
    fecha = models.DateField(db_index=True, verbose_name="Fecha de Cierre")
    
    # Totales del día
    total_ingresos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Total Ingresos ($)"
    )
    total_egresos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Total Egresos ($)"
    )
    neto_dia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Neto del Día ($)"
    )
    
    # Conteos para auditoría
    num_ventas = models.PositiveIntegerField(default=0, verbose_name="Número de Ventas")
    num_devoluciones = models.PositiveIntegerField(default=0, verbose_name="Número de Devoluciones")
    num_gastos = models.PositiveIntegerField(default=0, verbose_name="Número de Gastos")
    
    # Hash de integridad (sello digital)
    hash_integridad = models.CharField(
        max_length=64,
        editable=False,
        verbose_name="Hash SHA-256",
        help_text="Firma digital del cierre. Cualquier modificación altera este valor."
    )
    
    # Auditoría
    generado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cierres_dia_generados',
        verbose_name="Generado por"
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    
    # Flags de validación
    validado = models.BooleanField(default=False, verbose_name="Validado")
    fecha_validacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Validación")
    
    class Meta:
        app_label = 'core'
        verbose_name = "Cierre de Día Consolidado"
        verbose_name_plural = "Cierres de Día Consolidados"
        unique_together = ['empresa', 'sucursal', 'fecha']
        ordering = ['-fecha']
    
    def __str__(self):
        sucursal_str = f" | {self.sucursal.nombre}" if self.sucursal else ""
        return f"Cierre {self.fecha}{sucursal_str} — Neto: ${self.neto_dia}"
    
    def generar_hash(self):
        """
        Genera hash SHA-256 de los datos del cierre.
        
        El hash incluye:
        - empresa_id, sucursal_id, fecha
        - total_ingresos, total_egresos, neto_dia
        - num_ventas, num_devoluciones, num_gastos
        """
        # Concatenar datos relevantes en string determinista
        data = (
            f"empresa:{self.empresa_id}|"
            f"sucursal:{self.sucursal_id or 'NULL'}|"
            f"fecha:{self.fecha}|"
            f"ingresos:{self.total_ingresos}|"
            f"egresos:{self.total_egresos}|"
            f"neto:{self.neto_dia}|"
            f"ventas:{self.num_ventas}|"
            f"devs:{self.num_devoluciones}|"
            f"gastos:{self.num_gastos}"
        )
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    def verificar_integridad(self):
        """
        Verifica que el hash actual coincida con los datos.
        
        Returns:
            bool: True si la integridad es válida
        """
        return self.hash_integridad == self.generar_hash()
    
    def save(self, *args, **kwargs):
        """Regenerar hash antes de guardar; ticket si consolidado vs kardex > 1 %."""
        skip_ticket = kwargs.pop('skip_discrepancia_ticket', False)
        self.neto_dia = self.total_ingresos - self.total_egresos
        self.hash_integridad = self.generar_hash()
        super().save(*args, **kwargs)
        if not skip_ticket and self.pk:
            from core.services.bankguard_cierre import verificar_discrepancia_cierre_y_ticket

            verificar_discrepancia_cierre_y_ticket(self)


class TicketInvestigacionCaja(models.Model):
    """
    Ticket de investigación para discrepancias detectadas.
    """
    TIPO_DISCREPANCIA = [
        ('HASH_INVALIDO', 'Hash de Cierre Alterado'),
        ('PAGO_SIN_MOVIMIENTO', 'Pago sin MovimientoCaja'),
        ('MOVIMIENTO_SIN_PAGO', 'MovimientoCaja sin Pago'),
        ('DIFERENCIA_MONTO', 'Diferencia de Monto (Pago vs Movimiento)'),
        ('Doble_Descuento', 'Posible Doble Descuento Inventario'),
        ('OTRO', 'Otro / Especificar'),
    ]
    
    ESTADO_TICKET = [
        ('ABIERTO', 'Abierto'),
        ('EN_INVESTIGACION', 'En Investigación'),
        ('RESUELTO', 'Resuelto'),
        ('FRAUDE_CONFIRMADO', 'Fraude Confirmado'),
    ]
    
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='tickets_investigacion'
    )
    
    # Referencias
    cierre_dia = models.ForeignKey(
        CierreDiaConsolidado,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tickets'
    )
    venta = models.ForeignKey(
        'core.Venta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_investigacion'
    )
    
    # Datos del ticket
    tipo_discrepancia = models.CharField(
        max_length=30,
        choices=TIPO_DISCREPANCIA,
        verbose_name="Tipo de Discrepancia"
    )
    descripcion = models.TextField(verbose_name="Descripción del Hallazgo")
    
    # Montos involucrados (snapshot)
    monto_esperado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto Esperado ($)"
    )
    monto_real = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto Real ($)"
    )
    diferencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Diferencia ($)"
    )
    
    # Workflow
    estado = models.CharField(
        max_length=30,
        choices=ESTADO_TICKET,
        default='ABIERTO',
        verbose_name="Estado"
    )
    asignado_a = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_asignados',
        verbose_name="Asignado a"
    )
    
    # Resolución
    resolucion = models.TextField(blank=True, verbose_name="Resolución")
    resuelto_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_resueltos',
        verbose_name="Resuelto por"
    )
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    
    # Metadatos
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tickets_creados',
        verbose_name="Creado por (automático)"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'core'
        verbose_name = "Ticket de Investigación Caja"
        verbose_name_plural = "Tickets de Investigación Caja"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"#{self.id} | {self.get_tipo_discrepancia_display()} | {self.estado}"
