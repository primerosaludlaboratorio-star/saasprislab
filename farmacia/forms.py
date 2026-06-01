"""
MÓDULO FARMACIA - FORMULARIOS DE ALTA INGENIERÍA
Sistema de Compras, Corte de Caja y Gestión Avanzada
"""
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date

from core.models import Producto, Lote
from farmacia.models import Proveedor, MovimientoInventario, MotivoAjuste


# ==============================================================================
# FORMULARIO DE REGISTRO DE COMPRA (CON CÁLCULO DE CPP)
# ==============================================================================
class RegistrarCompraForm(forms.Form):
    """
    Formulario para registrar compras a proveedores.
    
    Flujo:
    1. Seleccionar proveedor
    2. Agregar producto(s) con cantidad, costo unitario, lote y caducidad
    3. Al guardar:
       - Crea MovimientoInventario tipo ENTRADA_COMPRA
       - Crea o actualiza Lote
       - Recalcula el Costo Promedio Ponderado (CPP)
       - Actualiza el stock
    """
    
    # Información de la Compra
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.none(),  # Se filtra en __init__
        label="Proveedor",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        help_text="Selecciona el proveedor de esta compra"
    )
    
    documento_compra = forms.CharField(
        max_length=100,
        label="Documento de Compra",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: FACT-12345',
            'required': True
        }),
        help_text="Número de factura o remisión"
    )
    
    fecha_compra = forms.DateField(
        label="Fecha de Compra",
        initial=date.today,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'required': True
        })
    )
    
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Notas adicionales sobre la compra...'
        })
    )
    
    def __init__(self, empresa, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar proveedores por empresa y activos
        self.fields['proveedor'].queryset = Proveedor.objects.filter(
            empresa=empresa,
            activo=True
        ).order_by('razon_social')


# ==============================================================================
# FORMULARIO DE DETALLE DE COMPRA (PRODUCTOS EN LA COMPRA)
# ==============================================================================
class DetalleCompraForm(forms.Form):
    """
    Formulario para agregar productos a una compra.
    Se usa en conjunto con RegistrarCompraForm.
    Soporta multi-lote: múltiples lotes por producto en una sola factura.
    """
    
    producto = forms.ModelChoiceField(
        queryset=Producto.objects_all.none(),
        label="Producto",
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'required': True,
            'data-placeholder': 'Buscar producto...'
        })
    )
    
    marca = forms.CharField(
        max_length=150,
        required=False,
        label="Marca / Laboratorio",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Bayer, Pfizer, GENERICO',
        }),
        help_text="Marca o laboratorio fabricante del lote"
    )
    
    cantidad = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        label="Unidades",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'required': True,
            'placeholder': '0.00'
        }),
        help_text="Cantidad de unidades en este lote"
    )
    
    costo_unitario = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        label="Costo Neto",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'required': True,
            'placeholder': '0.00'
        }),
        help_text="Costo de compra real por unidad (SIN IVA)"
    )
    
    numero_lote = forms.CharField(
        max_length=50,
        label="Lote",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'required': True,
            'placeholder': 'Ej: LOTE-2026-001',
            'style': 'text-transform: uppercase;'
        }),
        help_text="Identificador unico por lote de produccion"
    )
    
    fecha_caducidad = forms.DateField(
        label="Fecha de Caducidad",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'required': True
        }),
        help_text="Fecha de vencimiento del lote (FEFO)"
    )
    
    def __init__(self, empresa, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar productos por empresa
        self.fields['producto'].queryset = Producto.objects.filter(
            empresa=empresa
        ).order_by('nombre')
    
    def clean_fecha_caducidad(self):
        """Validar que la fecha de caducidad sea futura."""
        fecha_cad = self.cleaned_data.get('fecha_caducidad')
        if fecha_cad and fecha_cad < date.today():
            raise ValidationError(
                "La fecha de caducidad no puede ser anterior a hoy. "
                "Si el producto ya esta vencido, no deberia comprarse."
            )
        return fecha_cad
    
    def clean_numero_lote(self):
        """Convertir a mayusculas y validar formato."""
        lote = self.cleaned_data.get('numero_lote', '').strip().upper()
        if not lote:
            raise ValidationError("El numero de lote es obligatorio.")
        return lote


# ==============================================================================
# FORMULARIO DE CORTE DE CAJA (ARQUEO CIEGO)
# ==============================================================================
class CorteCajaFarmaciaForm(forms.Form):
    """
    Formulario para realizar el corte de caja al final del turno.
    
    ARQUEO CIEGO: El cajero NO ve cuánto espera el sistema.
    Solo ingresa el dinero real que tiene en mano.
    
    El sistema luego compara:
    - Total Declarado (por el cajero)
    - Total Sistema (suma de ventas del turno)
    - Diferencia (sobrante o faltante)
    """
    
    # Montos Declarados por el Cajero
    efectivo_declarado = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Efectivo en Mano",
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'step': '0.01',
            'min': '0',
            'required': True,
            'placeholder': '0.00',
            'autofocus': True,
            'style': 'font-size: 1.5rem; font-weight: bold;'
        }),
        help_text="💵 Cuenta el dinero en efectivo y escribe el total"
    )
    
    tarjeta_declarada = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Total Tarjetas (Suma de Vouchers)",
        required=False,
        initial=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'placeholder': '0.00'
        }),
        help_text="💳 Suma los vouchers de tarjeta"
    )
    
    transferencia_declarada = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Total Transferencias/SPEI",
        required=False,
        initial=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'placeholder': '0.00'
        }),
        help_text="🏦 Suma las transferencias recibidas"
    )
    
    # Observaciones
    observaciones_corte = forms.CharField(
        required=False,
        label="Observaciones del Cajero",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ej: Hubo un reembolso de $50 que explica la diferencia...'
        }),
        help_text="Explica cualquier diferencia o situación especial"
    )
    
    # Validación
    acepto_responsabilidad = forms.BooleanField(
        label="Confirmo que los montos declarados son correctos y bajo mi responsabilidad",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': True
        }),
        help_text="⚠️ El corte es un documento legal inmutable"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que al menos haya efectivo o tarjeta
        efectivo = cleaned_data.get('efectivo_declarado', Decimal('0'))
        tarjeta = cleaned_data.get('tarjeta_declarada', Decimal('0'))
        transferencia = cleaned_data.get('transferencia_declarada', Decimal('0'))
        
        total_declarado = efectivo + tarjeta + transferencia
        
        if total_declarado <= 0:
            raise ValidationError(
                "Debe declarar al menos un monto mayor a cero en algún método de pago."
            )
        
        return cleaned_data


# ==============================================================================
# FORMULARIO DE AJUSTE MANUAL DE INVENTARIO
# ==============================================================================
class AjusteInventarioForm(forms.Form):
    """
    Formulario para registrar ajustes manuales de inventario.
    Requiere motivo del catálogo y observaciones.
    """
    
    producto = forms.ModelChoiceField(
        queryset=Producto.objects_all.none(),
        label="Producto",
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'required': True
        })
    )
    
    lote = forms.ModelChoiceField(
        queryset=Lote.objects_all.none(),
        required=False,
        label="Lote (Opcional)",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Si el ajuste es de un lote específico"
    )
    
    tipo_ajuste = forms.ChoiceField(
        choices=[
            ('ENTRADA_AJUSTE', 'Ajuste Positivo (Aumentar Stock)'),
            ('SALIDA_AJUSTE', 'Ajuste Negativo (Reducir Stock)'),
            ('SALIDA_MERMA', 'Merma por Caducidad'),
            ('SALIDA_ROBO', 'Robo/Faltante'),
        ],
        label="Tipo de Ajuste",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        })
    )
    
    cantidad = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        label="Cantidad",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'required': True
        }),
        help_text="Cantidad a ajustar (siempre positivo)"
    )
    
    motivo = forms.ModelChoiceField(
        queryset=MotivoAjuste.objects.none(),
        label="Motivo del Ajuste",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        help_text="Selecciona el motivo del catálogo"
    )
    
    observaciones = forms.CharField(
        label="Observaciones Detalladas",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'required': True,
            'placeholder': 'Describe detalladamente el motivo del ajuste...'
        }),
        help_text="⚠️ Campo obligatorio para trazabilidad forense"
    )
    
    evidencia = forms.ImageField(
        required=False,
        label="Evidencia Fotográfica",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        help_text="Foto del producto dañado, vencido, etc."
    )
    
    def __init__(self, empresa, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.filter(
            empresa=empresa
        ).order_by('nombre')
        
        self.fields['motivo'].queryset = MotivoAjuste.objects.filter(
            empresa=empresa,
            activo=True
        ).order_by('codigo')


# ==============================================================================
# FORMULARIO DE GENERACIÓN DE ETIQUETAS
# ==============================================================================
class GenerarEtiquetasForm(forms.Form):
    """
    Formulario para generar etiquetas con código de barras.
    Permite seleccionar productos y cantidad de etiquetas a imprimir.
    """
    
    productos = forms.ModelMultipleChoiceField(
        queryset=Producto.objects_all.none(),
        label="Productos a Etiquetar",
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        help_text="Selecciona los productos para generar sus etiquetas"
    )
    
    incluir_precio = forms.BooleanField(
        initial=True,
        required=False,
        label="Incluir Precio en la Etiqueta",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    incluir_caducidad = forms.BooleanField(
        initial=True,
        required=False,
        label="Incluir Fecha de Caducidad",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    tamaño_etiqueta = forms.ChoiceField(
        choices=[
            ('zebra_4x6', 'Zebra 4x6 pulgadas (10x15 cm)'),
            ('dymo_2x1', 'Dymo 2x1 pulgadas (5x2.5 cm)'),
            ('a4', 'Hoja A4 (múltiples etiquetas)'),
        ],
        initial='zebra_4x6',
        label="Tamaño de Etiqueta",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    cantidad_por_producto = forms.IntegerField(
        initial=1,
        min_value=1,
        max_value=100,
        label="Cantidad de Etiquetas por Producto",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '100'
        })
    )
    
    def __init__(self, empresa, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['productos'].queryset = Producto.objects.filter(
            empresa=empresa
        ).order_by('nombre')
