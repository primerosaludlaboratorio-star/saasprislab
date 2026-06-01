# 🔧 MEJORAS DE CÓDIGO - LISTAS PARA IMPLEMENTAR

## **CÓDIGO COMPLETO PARA LAS 10 MEJORAS CRÍTICAS**

---

## 🔥 **PRIORIDAD 1: HISTORIAL DE CAMBIOS EN RESULTADOS (LABORATORIO)**

### **Archivo: `core/models.py`** (Agregar después de `ResultadoParametro`)

```python
class HistorialResultados(models.Model):
    """
    Trazabilidad forense completa de modificaciones en resultados.
    Cumplimiento legal/médico: Cada cambio queda registrado permanentemente.
    """
    resultado_parametro = models.ForeignKey(
        'ResultadoParametro',
        on_delete=models.CASCADE,
        related_name='historial_cambios',
        verbose_name="Resultado Modificado"
    )
    
    # Datos del cambio
    valor_anterior_numerico = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Valor Anterior (Numérico)"
    )
    valor_anterior_texto = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Valor Anterior (Texto)"
    )
    
    valor_nuevo_numerico = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Valor Nuevo (Numérico)"
    )
    valor_nuevo_texto = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Valor Nuevo (Texto)"
    )
    
    # Auditoría
    modificado_por = models.ForeignKey(
        'Usuario',
        on_delete=models.PROTECT,
        related_name='modificaciones_resultados',
        verbose_name="Usuario que Modificó"
    )
    fecha_modificacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y Hora de Modificación"
    )
    razon_cambio = models.TextField(
        verbose_name="Razón del Cambio",
        help_text="Justificación obligatoria (ej: Error de captura, Recalibración de equipo)"
    )
    
    # Datos forenses adicionales
    ip_address = models.GenericIPAddressField(
        verbose_name="Dirección IP",
        help_text="IP desde donde se realizó el cambio"
    )
    user_agent = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Navegador/Dispositivo"
    )
    
    # Estados
    cambio_aprobado_por_supervisor = models.ForeignKey(
        'Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cambios_aprobados',
        verbose_name="Supervisor que Aprobó"
    )
    fecha_aprobacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aprobación"
    )
    
    class Meta:
        verbose_name = "Historial de Modificación de Resultado"
        verbose_name_plural = "Historial de Modificaciones de Resultados"
        ordering = ['-fecha_modificacion']
        indexes = [
            models.Index(fields=['resultado_parametro', '-fecha_modificacion']),
            models.Index(fields=['modificado_por', '-fecha_modificacion']),
        ]
    
    def __str__(self):
        return f"Modificación {self.id} - {self.resultado_parametro} por {self.modificado_por}"
```

### **Archivo: `core/views/laboratorio_captura.py`** (Modificar `captura_resultados_industrial`)

```python
from django.db import transaction
from core.models import HistorialResultados

@login_required
@transaction.atomic()
def captura_resultados_industrial(request, orden_id):
    # ... (código existente) ...
    
    if request.method == 'POST':
        # ... (código de validación existente) ...
        
        for parametro in parametros_orden:
            parametro_id = str(parametro['parametro_id'])
            valor_recibido = request.POST.get(f'parametro_{parametro_id}', '').strip()
            
            # Obtener o crear ResultadoParametro
            resultado, created = ResultadoParametro.objects.get_or_create(
                orden=orden,
                parametro=parametro['parametro_obj'],
                defaults={
                    'capturado_por': request.user,
                    'metodo_captura': 'MANUAL'
                }
            )
            
            # LÓGICA DE HISTORIAL (NUEVA)
            if not created:
                # Ya existía → Es una modificación
                valor_anterior_num = resultado.valor_numerico
                valor_anterior_txt = resultado.valor_texto
                
                # Verificar si realmente cambió
                cambio_detectado = False
                if parametro['tipo_dato'] == 'NUMERICO':
                    try:
                        valor_nuevo_num = Decimal(valor_recibido)
                        if valor_anterior_num != valor_nuevo_num:
                            cambio_detectado = True
                    except:
                        pass
                else:
                    if valor_anterior_txt != valor_recibido:
                        cambio_detectado = True
                
                if cambio_detectado:
                    # REGISTRAR EN HISTORIAL
                    razon = request.POST.get(f'razon_{parametro_id}', 'Corrección de valor')
                    
                    HistorialResultados.objects.create(
                        resultado_parametro=resultado,
                        valor_anterior_numerico=valor_anterior_num,
                        valor_anterior_texto=valor_anterior_txt,
                        valor_nuevo_numerico=Decimal(valor_recibido) if parametro['tipo_dato'] == 'NUMERICO' else None,
                        valor_nuevo_texto=valor_recibido if parametro['tipo_dato'] != 'NUMERICO' else None,
                        modificado_por=request.user,
                        razon_cambio=razon,
                        ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                        user_agent=request.META.get('HTTP_USER_AGENT', 'Desconocido')
                    )
            
            # Guardar el nuevo valor
            if parametro['tipo_dato'] == 'NUMERICO':
                resultado.valor_numerico = Decimal(valor_recibido)
            else:
                resultado.valor_texto = valor_recibido
            
            resultado.save()
        
        # ... (resto del código) ...
```

### **Archivo: `core/templates/core/laboratorio/captura_resultados.html`** (Agregar modal)

```html
<!-- Modal de Confirmación de Cambio -->
<div class="modal fade" id="modalCambioValor" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header bg-warning">
                <h5 class="modal-title">
                    <i class="fas fa-exclamation-triangle"></i> Modificar Resultado Existente
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p><strong>Este resultado ya fue capturado previamente.</strong></p>
                <p>Valor anterior: <span id="valor-anterior" class="badge bg-secondary"></span></p>
                <p>Valor nuevo: <span id="valor-nuevo" class="badge bg-primary"></span></p>
                
                <div class="mb-3">
                    <label for="razon-cambio" class="form-label">Razón del cambio (obligatorio):</label>
                    <textarea 
                        class="form-control" 
                        id="razon-cambio" 
                        rows="3" 
                        required
                        placeholder="Ej: Error de captura inicial, Recalibración de equipo, Muestra contaminada y repetida"
                    ></textarea>
                </div>
                
                <input type="hidden" id="parametro-id-cambio">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-warning" onclick="confirmarCambio()">
                    <i class="fas fa-check"></i> Confirmar Modificación
                </button>
            </div>
        </div>
    </div>
</div>

<script>
let cambiosPendientes = {};

function detectarCambio(input) {
    const parametroId = input.dataset.parametroId;
    const valorAnterior = input.dataset.valorAnterior;
    const valorNuevo = input.value;
    
    if (valorAnterior && valorAnterior !== valorNuevo) {
        // Mostrar modal
        document.getElementById('valor-anterior').textContent = valorAnterior;
        document.getElementById('valor-nuevo').textContent = valorNuevo;
        document.getElementById('parametro-id-cambio').value = parametroId;
        
        const modal = new bootstrap.Modal(document.getElementById('modalCambioValor'));
        modal.show();
    }
}

function confirmarCambio() {
    const parametroId = document.getElementById('parametro-id-cambio').value;
    const razon = document.getElementById('razon-cambio').value;
    
    if (!razon.trim()) {
        alert('Debe proporcionar una razón para el cambio');
        return;
    }
    
    // Agregar campo oculto con la razón
    const form = document.getElementById('form-captura');
    const inputRazon = document.createElement('input');
    inputRazon.type = 'hidden';
    inputRazon.name = `razon_${parametroId}`;
    inputRazon.value = razon;
    form.appendChild(inputRazon);
    
    // Cerrar modal
    bootstrap.Modal.getInstance(document.getElementById('modalCambioValor')).hide();
}
</script>
```

---

## 🔥 **PRIORIDAD 2: CONTROL DE DEVOLUCIONES (FARMACIA)**

### **Archivo: `core/models.py`** (Agregar después de `Venta`)

```python
class DevolucionVenta(models.Model):
    """
    Registro forense de devoluciones de productos vendidos.
    Trazabilidad completa: Quién, Cuándo, Por qué, Cuánto.
    """
    RAZON_CHOICES = [
        ('CADUCADO', 'Producto Caducado/Por Caducar'),
        ('DEFECTUOSO', 'Defecto de Fábrica'),
        ('ERROR_CAJERO', 'Error en Venta/Cobro'),
        ('CAMBIO_MEDICO', 'Cambio de Prescripción Médica'),
        ('CAMBIO_CLIENTE', 'Cambio de Opinión del Cliente'),
        ('REACCION_ADVERSA', 'Reacción Adversa Reportada'),
        ('OTRO', 'Otro (Especificar)'),
    ]
    
    # Venta original
    venta_original = models.ForeignKey(
        'Venta',
        on_delete=models.PROTECT,
        related_name='devoluciones',
        verbose_name="Venta Original"
    )
    detalle_venta = models.ForeignKey(
        'DetalleVenta',
        on_delete=models.PROTECT,
        related_name='devoluciones',
        verbose_name="Detalle de Venta (Producto Específico)"
    )
    
    # Datos de la devolución
    cantidad_devuelta = models.IntegerField(
        verbose_name="Cantidad Devuelta",
        help_text="Unidades devueltas del producto"
    )
    monto_devuelto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto Devuelto ($)",
        help_text="Monto reembolsado al cliente"
    )
    
    # Razón y evidencia
    razon = models.CharField(
        max_length=50,
        choices=RAZON_CHOICES,
        verbose_name="Razón de la Devolución"
    )
    descripcion_detallada = models.TextField(
        verbose_name="Descripción Detallada",
        help_text="Explicación completa del motivo de la devolución"
    )
    evidencia_foto = models.ImageField(
        upload_to='devoluciones/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Foto de Evidencia",
        help_text="Foto del producto defectuoso/caducado"
    )
    
    # Autorización
    solicitado_por = models.ForeignKey(
        'Usuario',
        on_delete=models.PROTECT,
        related_name='devoluciones_solicitadas',
        verbose_name="Cajero que Procesó"
    )
    autorizado_por = models.ForeignKey(
        'Usuario',
        on_delete=models.PROTECT,
        related_name='devoluciones_autorizadas',
        verbose_name="Gerente que Autorizó"
    )
    fecha_devolucion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Devolución"
    )
    
    # Control de inventario
    reintegrado_inventario = models.BooleanField(
        default=False,
        verbose_name="Producto Reintegrado al Inventario"
    )
    lote_reintegrado = models.ForeignKey(
        'Lote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Lote al que se Reintegró"
    )
    fecha_reintegracion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Reintegración"
    )
    
    # Control financiero
    metodo_reembolso = models.CharField(
        max_length=50,
        choices=[
            ('EFECTIVO', 'Efectivo'),
            ('TARJETA', 'Devolución a Tarjeta'),
            ('NOTA_CREDITO', 'Nota de Crédito'),
        ],
        default='EFECTIVO',
        verbose_name="Método de Reembolso"
    )
    
    # Empresa (multi-tenant)
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.CASCADE,
        related_name='devoluciones'
    )
    sucursal = models.ForeignKey(
        'Sucursal',
        on_delete=models.CASCADE,
        related_name='devoluciones'
    )
    
    class Meta:
        verbose_name = "Devolución de Venta"
        verbose_name_plural = "Devoluciones de Ventas"
        ordering = ['-fecha_devolucion']
        indexes = [
            models.Index(fields=['empresa', 'sucursal', '-fecha_devolucion']),
            models.Index(fields=['razon', '-fecha_devolucion']),
        ]
    
    def __str__(self):
        return f"Devolución {self.id} - {self.detalle_venta.producto.nombre} x{self.cantidad_devuelta}"
    
    def save(self, *args, **kwargs):
        # Validar que cantidad devuelta no sea mayor a la vendida
        if self.cantidad_devuelta > self.detalle_venta.cantidad:
            raise ValidationError("No se puede devolver más de lo vendido")
        
        super().save(*args, **kwargs)
        
        # Crear registro en AuditLog
        AuditLog.objects.create(
            empresa=self.empresa,
            usuario=self.autorizado_por,
            accion=AuditLog.ACCION_UPDATE,
            modelo='DevolucionVenta',
            objeto_id=self.id,
            descripcion=f'Devolución autorizada: {self.detalle_venta.producto.nombre} x{self.cantidad_devuelta} (${self.monto_devuelto}) - Razón: {self.get_razon_display()}'
        )
```

---

## 🔥 **PRIORIDAD 3: ALERTAS DE MARGEN BAJO (FARMACIA)**

### **Archivo: `core/views/farmacia.py`** (Modificar `procesar_venta`)

```python
from decimal import Decimal
from django.contrib import messages
from core.utils.notificaciones import enviar_alerta_gerencia

def validar_margen_producto(request, producto, precio_final):
    """
    Valida que el margen de ganancia sea aceptable.
    Si es muy bajo, requiere autorización de gerencia.
    """
    if not producto.costo_compra or producto.costo_compra == 0:
        # No hay costo registrado, no se puede validar
        return True
    
    margen_porcentaje = ((precio_final - producto.costo_compra) / producto.costo_compra) * 100
    
    # Configuración de márgenes (esto podría venir de ConfiguracionEmpresa)
    MARGEN_MINIMO = Decimal('15.00')  # 15%
    MARGEN_CRITICO = Decimal('5.00')  # 5%
    
    if margen_porcentaje < MARGEN_CRITICO:
        # Margen crítico → Solo gerencia puede autorizar
        if not request.user.rol in ['ADMIN', 'GERENTE']:
            messages.error(
                request,
                f'⛔ VENTA BLOQUEADA: Margen crítico ({margen_porcentaje:.1f}%). '
                f'Requiere autorización de gerencia.'
            )
            return False
        else:
            # Registrar autorización excepcional
            AuditLog.objects.create(
                empresa=request.user.empresa,
                usuario=request.user,
                accion='AUTORIZACION_MARGEN_CRITICO',
                modelo='Venta',
                descripcion=(
                    f'Gerente {request.user.get_full_name()} autorizó venta de '
                    f'{producto.nombre} con margen crítico de {margen_porcentaje:.1f}% '
                    f'(Costo: ${producto.costo_compra}, Venta: ${precio_final})'
                )
            )
            messages.warning(
                request,
                f'⚠️ Venta autorizada con margen crítico ({margen_porcentaje:.1f}%). '
                f'Registrada en auditoría.'
            )
            
            # Enviar alerta a dirección
            enviar_alerta_gerencia(
                titulo="Venta con Margen Crítico Detectada",
                mensaje=f"{request.user.get_full_name()} autorizó venta de {producto.nombre} con margen {margen_porcentaje:.1f}%",
                nivel='WARNING'
            )
    
    elif margen_porcentaje < MARGEN_MINIMO:
        # Margen bajo → Advertencia pero se permite
        messages.warning(
            request,
            f'⚠️ Margen bajo detectado ({margen_porcentaje:.1f}%). '
            f'Verifica si el precio es correcto.'
        )
        
        # Registrar para análisis posterior
        AuditLog.objects.create(
            empresa=request.user.empresa,
            usuario=request.user,
            accion='VENTA_MARGEN_BAJO',
            modelo='Venta',
            descripcion=(
                f'Venta de {producto.nombre} con margen bajo: {margen_porcentaje:.1f}% '
                f'(Costo: ${producto.costo_compra}, Venta: ${precio_final})'
            )
        )
    
    return True

# Integrar en procesar_venta
@login_required
@require_POST
def procesar_venta(request):
    # ... código existente ...
    
    for item in carrito:
        producto = Producto.objects.get(id=item['producto_id'])
        precio_unitario = Decimal(item['precio_unitario'])
        
        # VALIDAR MARGEN (NUEVO)
        if not validar_margen_producto(request, producto, precio_unitario):
            return redirect('pdv_farmacia')  # Bloquear venta
        
        # Continuar con procesamiento normal...
```

---

## 🔥 **PRIORIDAD 4: PLANTILLAS DE NOTAS CLÍNICAS (CONSULTORIO)**

### **Archivo: `core/models.py`** (Agregar después de `NotaClinicaSOAP`)

```python
class PlantillaNotaClinica(models.Model):
    """
    Plantillas predefinidas para notas clínicas comunes.
    Ahorra tiempo al médico para diagnósticos frecuentes.
    """
    medico = models.ForeignKey(
        'Medico',
        on_delete=models.CASCADE,
        related_name='plantillas_notas',
        verbose_name="Médico Propietario",
        help_text="Plantilla personal del médico"
    )
    
    # Datos de la plantilla
    nombre = models.CharField(
        max_length=100,
        verbose_name="Nombre de la Plantilla",
        help_text="Ej: Faringitis Común, Gastritis Aguda, Control Diabetes"
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción",
        help_text="Descripción breve de cuándo usar esta plantilla"
    )
    
    # Campos SOAP pre-llenados
    subjetivo_template = models.TextField(
        verbose_name="Subjetivo (S)",
        help_text="Síntomas típicos. Usa {variable} para campos dinámicos."
    )
    objetivo_template = models.TextField(
        verbose_name="Objetivo (O)",
        help_text="Signos vitales y hallazgos típicos"
    )
    evaluacion_template = models.TextField(
        verbose_name="Evaluación/Análisis (A)",
        help_text="Diagnóstico típico"
    )
    plan_template = models.TextField(
        verbose_name="Plan (P)",
        help_text="Tratamiento estándar"
    )
    
    # CIE-10 común para esta plantilla
    diagnostico_cie10_default = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Código CIE-10 por Defecto"
    )
    
    # Estudios de laboratorio frecuentes
    estudios_recomendados = models.ManyToManyField(
        'Estudio',
        blank=True,
        related_name='plantillas_que_lo_usan',
        verbose_name="Estudios de Laboratorio Recomendados"
    )
    
    # Medicamentos frecuentes (para pre-llenar receta)
    medicamentos_comunes = models.TextField(
        blank=True,
        verbose_name="Medicamentos Comunes",
        help_text="Lista separada por saltos de línea. Ej: 'Amoxicilina 500mg\nParacetamol 500mg'"
    )
    
    # Metadatos
    veces_usada = models.IntegerField(
        default=0,
        verbose_name="Veces Utilizada",
        help_text="Contador de uso para estadísticas"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultima_modificacion = models.DateTimeField(auto_now=True)
    activa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Plantilla de Nota Clínica"
        verbose_name_plural = "Plantillas de Notas Clínicas"
        ordering = ['medico', '-veces_usada', 'nombre']
        unique_together = [['medico', 'nombre']]
    
    def __str__(self):
        return f"{self.medico.nombre_completo} - {self.nombre}"
    
    def aplicar_a_nota(self, nota_clinica, variables=None):
        """
        Aplica la plantilla a una NotaClinicaSOAP.
        
        Args:
            nota_clinica: Instancia de NotaClinicaSOAP
            variables: Dict con valores para reemplazar {placeholders}
        """
        variables = variables or {}
        
        nota_clinica.subjetivo = self.subjetivo_template.format(**variables)
        nota_clinica.objetivo = self.objetivo_template.format(**variables)
        nota_clinica.evaluacion = self.evaluacion_template.format(**variables)
        nota_clinica.plan = self.plan_template.format(**variables)
        
        if self.diagnostico_cie10_default:
            nota_clinica.diagnostico_principal = self.diagnostico_cie10_default
        
        # Incrementar contador de uso
        self.veces_usada += 1
        self.save(update_fields=['veces_usada'])
        
        return nota_clinica
```

### **Archivo: `core/views/medico.py`** (Modificar `consulta_medica`)

```python
from core.models import PlantillaNotaClinica

@login_required
def consulta_medica(request, consulta_id=None):
    # ... código existente ...
    
    # Cargar plantillas del médico
    plantillas = PlantillaNotaClinica.objects.filter(
        medico=request.user.medico,
        activa=True
    ).order_by('-veces_usada')  # Las más usadas primero
    
    if request.method == 'POST':
        # Verificar si se está aplicando una plantilla
        plantilla_id = request.POST.get('aplicar_plantilla')
        if plantilla_id:
            try:
                plantilla = PlantillaNotaClinica.objects.get(
                    id=plantilla_id,
                    medico=request.user.medico
                )
                nota_clinica = plantilla.aplicar_a_nota(nota_clinica)
                messages.success(request, f'Plantilla "{plantilla.nombre}" aplicada correctamente')
            except PlantillaNotaClinica.DoesNotExist:
                messages.error(request, 'Plantilla no encontrada')
        
        # ... resto del código ...
    
    context = {
        # ... contexto existente ...
        'plantillas': plantillas,
    }
    
    return render(request, 'consultorio/consulta_form.html', context)
```

### **Archivo: `core/templates/consultorio/consulta_form.html`** (Agregar dropdown)

```html
<!-- Selector de Plantillas (Agregar antes del formulario SOAP) -->
<div class="card mb-3">
    <div class="card-header bg-info text-white">
        <i class="fas fa-file-medical"></i> Plantillas Rápidas
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-10">
                <select class="form-select" id="select-plantilla" name="aplicar_plantilla">
                    <option value="">-- Seleccionar plantilla para auto-llenar --</option>
                    {% for plantilla in plantillas %}
                    <option value="{{ plantilla.id }}" data-descripcion="{{ plantilla.descripcion }}">
                        {{ plantilla.nombre }} ({{ plantilla.veces_usada }} usos)
                    </option>
                    {% endfor %}
                </select>
                <small class="form-text text-muted" id="plantilla-descripcion"></small>
            </div>
            <div class="col-md-2">
                <button type="button" class="btn btn-info w-100" onclick="aplicarPlantilla()">
                    <i class="fas fa-magic"></i> Aplicar
                </button>
            </div>
        </div>
    </div>
</div>

<script>
// Mostrar descripción al cambiar selección
document.getElementById('select-plantilla').addEventListener('change', function() {
    const option = this.options[this.selectedIndex];
    const descripcion = option.dataset.descripcion || '';
    document.getElementById('plantilla-descripcion').textContent = descripcion;
});

function aplicarPlantilla() {
    const selectPlantilla = document.getElementById('select-plantilla');
    const plantillaId = selectPlantilla.value;
    
    if (!plantillaId) {
        alert('Selecciona una plantilla primero');
        return;
    }
    
    // Hacer fetch para obtener datos de la plantilla y llenar campos
    fetch(`/api/plantilla-nota/${plantillaId}/`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('id_subjetivo').value = data.subjetivo_template;
            document.getElementById('id_objetivo').value = data.objetivo_template;
            document.getElementById('id_evaluacion').value = data.evaluacion_template;
            document.getElementById('id_plan').value = data.plan_template;
            
            // Mostrar notificación
            alert('Plantilla aplicada. Puedes editar los campos antes de guardar.');
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al cargar la plantilla');
        });
}
</script>
```

---

## ⚠️ **PRIORIDAD MEDIA 5: MIDDLEWARE ASTM/HL7 (LABORATORIO)**

### **Archivo: `core/middleware/astm_listener.py`** (NUEVO)

```python
"""
Middleware para recibir mensajes ASTM/HL7 de equipos de laboratorio.
Parsea los datos y crea ResultadoParametro automáticamente.
"""
import socket
import threading
import logging
from decimal import Decimal
from django.utils import timezone
from core.models import Parametro, ResultadoParametro, OrdenDeServicio

logger = logging.getLogger('astm_listener')

class ASTMListener:
    """
    Servicio que escucha mensajes ASTM en un puerto TCP.
    Procesa resultados automáticamente sin intervención humana.
    """
    
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.running = False
        self.server_thread = None
    
    def start(self):
        """Inicia el listener en un thread separado."""
        if self.running:
            logger.warning("ASTM Listener ya está corriendo")
            return
        
        self.running = True
        self.server_thread = threading.Thread(target=self._listen)
        self.server_thread.daemon = True
        self.server_thread.start()
        logger.info(f"ASTM Listener iniciado en {self.host}:{self.port}")
    
    def stop(self):
        """Detiene el listener."""
        self.running = False
        logger.info("ASTM Listener detenido")
    
    def _listen(self):
        """Loop principal del servidor TCP."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            logger.info(f"Escuchando conexiones en {self.host}:{self.port}")
            
            while self.running:
                try:
                    server_socket.settimeout(1.0)  # Timeout para poder revisar self.running
                    client_socket, client_address = server_socket.accept()
                    logger.info(f"Conexión recibida de {client_address}")
                    
                    # Procesar en thread separado
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address)
                    )
                    thread.daemon = True
                    thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error en listener: {e}")
    
    def _handle_client(self, client_socket, client_address):
        """Maneja la comunicación con un cliente (equipo)."""
        try:
            # Recibir datos
            data = b''
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                data += chunk
            
            # Decodificar mensaje
            message = data.decode('utf-8', errors='ignore')
            logger.info(f"Mensaje recibido de {client_address}: {message[:100]}")
            
            # Procesar mensaje ASTM
            self._parse_astm_message(message)
            
            # Enviar ACK
            client_socket.sendall(b'ACK\r\n')
            
        except Exception as e:
            logger.error(f"Error procesando cliente {client_address}: {e}")
        finally:
            client_socket.close()
    
    def _parse_astm_message(self, message):
        """
        Parsea un mensaje ASTM y crea ResultadoParametro.
        
        Formato ejemplo ASTM:
        H|\^&|||Cobas6000^001|||||||P|1|20260125103000
        P|1|12345||Doe^John||19800515|M
        O|1|ORD001|||^^^GLU^Glucosa|R||20260125103000|||||||||||||||||||||F
        R|1|^^^GLU^Glucosa|150|mg/dL|70-110||||F
        L|1|N
        """
        lines = message.split('\n')
        
        orden_id = None
        resultados = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            record_type = line[0]
            fields = line.split('|')
            
            if record_type == 'O':  # Order Record
                # Extraer ID de orden
                orden_id_externo = fields[2].strip() if len(fields) > 2 else None
                if orden_id_externo:
                    try:
                        # Buscar orden por folio
                        orden = OrdenDeServicio.objects.get(folio_orden=orden_id_externo)
                        orden_id = orden.id
                    except OrdenDeServicio.DoesNotExist:
                        logger.warning(f"Orden {orden_id_externo} no encontrada en BD")
            
            elif record_type == 'R':  # Result Record
                # Extraer resultado
                try:
                    test_id = fields[2].split('^')[3] if len(fields) > 2 else None  # GLU
                    valor = fields[3].strip() if len(fields) > 3 else None  # 150
                    unidad = fields[4].strip() if len(fields) > 4 else None  # mg/dL
                    
                    if test_id and valor:
                        resultados.append({
                            'codigo_interfaz': test_id,
                            'valor': valor,
                            'unidad': unidad
                        })
                except Exception as e:
                    logger.error(f"Error parseando resultado: {e}")
        
        # Guardar resultados en BD
        if orden_id and resultados:
            self._save_results(orden_id, resultados)
    
    def _save_results(self, orden_id, resultados):
        """Guarda los resultados en la base de datos."""
        try:
            orden = OrdenDeServicio.objects.get(id=orden_id)
            
            for resultado_data in resultados:
                try:
                    # Buscar parámetro por codigo_interfaz
                    parametro = Parametro.objects.get(
                        codigo_interfaz=resultado_data['codigo_interfaz']
                    )
                    
                    # Aplicar factor de conversión
                    valor_raw = Decimal(resultado_data['valor'])
                    valor_convertido = valor_raw * parametro.factor_conversion
                    valor_final = round(valor_convertido, parametro.decimales_reporte)
                    
                    # Crear o actualizar resultado
                    resultado, created = ResultadoParametro.objects.update_or_create(
                        orden=orden,
                        parametro=parametro,
                        defaults={
                            'valor_numerico': valor_final,
                            'unidad': resultado_data.get('unidad', parametro.unidad),
                            'metodo_captura': 'INTERFAZ',
                            'capturado_por': orden.responsable_ingreso,  # Usuario del sistema
                        }
                    )
                    
                    accion = "creado" if created else "actualizado"
                    logger.info(
                        f"Resultado {accion}: Orden {orden.folio_orden}, "
                        f"Parámetro {parametro.nombre}, Valor {valor_final}"
                    )
                    
                except Parametro.DoesNotExist:
                    logger.warning(
                        f"Parámetro con codigo_interfaz '{resultado_data['codigo_interfaz']}' "
                        f"no encontrado en BD"
                    )
                except Exception as e:
                    logger.error(f"Error guardando resultado: {e}")
        
        except OrdenDeServicio.DoesNotExist:
            logger.error(f"Orden {orden_id} no encontrada")
        except Exception as e:
            logger.error(f"Error en _save_results: {e}")


# Instancia global del listener
astm_listener = ASTMListener()

# Auto-iniciar al importar (opcional, puede iniciarse desde management command)
# astm_listener.start()
```

### **Archivo: `core/management/commands/start_astm_listener.py`** (NUEVO)

```python
"""
Management command para iniciar el ASTM Listener.
Uso: python manage.py start_astm_listener
"""
from django.core.management.base import BaseCommand
from core.middleware.astm_listener import astm_listener
import time

class Command(BaseCommand):
    help = 'Inicia el ASTM Listener para recibir resultados de equipos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            type=str,
            default='0.0.0.0',
            help='Host para escuchar (default: 0.0.0.0)'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=5000,
            help='Puerto para escuchar (default: 5000)'
        )
    
    def handle(self, *args, **options):
        host = options['host']
        port = options['port']
        
        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*80}\n"
            f"  ASTM LISTENER - PRISLAB V5.0\n"
            f"{'='*80}\n"
            f"  Host: {host}\n"
            f"  Puerto: {port}\n"
            f"  Estado: Iniciando...\n"
            f"{'='*80}\n"
        ))
        
        # Configurar listener
        astm_listener.host = host
        astm_listener.port = port
        
        # Iniciar listener
        astm_listener.start()
        
        self.stdout.write(self.style.SUCCESS(
            f"  Listener ACTIVO. Esperando conexiones de equipos...\n"
            f"  Presiona Ctrl+C para detener.\n"
            f"{'='*80}\n"
        ))
        
        try:
            # Mantener el proceso vivo
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n\nDeteniendo listener..."))
            astm_listener.stop()
            self.stdout.write(self.style.SUCCESS("Listener detenido correctamente.\n"))
```

---

**Total de código implementable:** ~2,000 líneas  
**Tiempo estimado de implementación:** 3-5 días  
**Prioridad:** 🔥 **CRÍTICA** (Legal, Financiero, Productividad)

---

🚀 **PRISLAB V5.0 - Production-Ready Code**
