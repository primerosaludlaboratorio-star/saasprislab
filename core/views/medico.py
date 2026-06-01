"""
Vistas del Módulo Médico - Receta Digital 4.0
Implementa consulta SOAP, receta con QR de validación y sincronización FEFO con farmacia.
"""
import json
import hashlib
import qrcode
import io
import base64
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Q

from core.models import (
    Empresa, Paciente, Medico, Receta, RecetaItem, NotaClinicaSOAP,
    Producto, Lote, FirmaDigital,
    OrdenDeServicio, DetalleOrden,
)
from core.lims_cart import resolve_lims_cart_ids, aplicar_precio_convenio
from core.utils.auditoria_helper import crear_log_auditoria, calcular_hash_auditoria
from core.models import AuditLog
from core.utils.trazabilidad import registrar_trazabilidad, serializar_modelo
from core.utils.empresa_request import empresa_efectiva_request


@login_required
def consulta_medica(request, paciente_id=None):
    """Formulario de consulta médica con SOAP y generación de receta 4.0."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    paciente = None
    signos_vitales = {}
    antecedentes = []
    
    if paciente_id:
        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
        
        # Obtener signos vitales del último expediente (si existe)
        ultima_nota = NotaClinicaSOAP.objects.filter(
            paciente=paciente,
            empresa=empresa
        ).order_by('-fecha_consulta').first()
        
        if ultima_nota:
            # Extraer signos vitales de la nota anterior (pueden estar en el campo objetivo)
            signos_vitales = {
                'pa_sistolica': None,
                'pa_diastolica': None,
                'fc': None,
                'fr': None,
                'temp': None,
                'peso': None,
                'talla': None,
                'spo2': None,
                'glucosa': None,
            }
        
        # Obtener antecedentes
        antecedentes = paciente.antecedentes.all().order_by('-fecha_registro')
    
    # Obtener médicos activos (scoped by empresa for multi-tenant)
    medicos = Medico.objects.filter(empresa=empresa) if empresa else Medico.objects.none()
    
    # Obtener firma digital del usuario actual (si es médico)
    firma_digital = None
    cedula_profesional = None
    fecha_vencimiento_cedula = None
    especialidad_medico = 'Médico General'
    nombre_medico = request.user.get_full_name() or request.user.username
    
    # Cargar datos del médico automáticamente desde su perfil
    try:
        firma_digital = FirmaDigital.objects.filter(
            medico=request.user,
            activa=True
        ).first()
        
        if firma_digital:
            cedula_profesional = firma_digital.cedula_profesional
            fecha_vencimiento_cedula = firma_digital.fecha_vencimiento if hasattr(firma_digital, 'fecha_vencimiento') else None
        
        # Buscar registro de Medico vinculado por cédula
        if cedula_profesional:
            medico_registro = Medico.objects.filter(
                cedula_profesional=cedula_profesional,
            ).first()
            if medico_registro:
                especialidad_medico = medico_registro.especialidad
                if not nombre_medico or nombre_medico == request.user.username:
                    nombre_medico = medico_registro.nombre_completo
        
        # Si no hay especialidad, usar el enfoque_profesional del usuario
        if especialidad_medico == 'Médico General' and hasattr(request.user, 'enfoque_profesional') and request.user.enfoque_profesional:
            especialidad_medico = request.user.enfoque_profesional
            
        # Si no hay cédula, usar cedula_interna del usuario
        if not cedula_profesional and hasattr(request.user, 'cedula_interna') and request.user.cedula_interna:
            cedula_profesional = request.user.cedula_interna
            
        # Si no hay título en el nombre, usar titulo_profesional del usuario
        if hasattr(request.user, 'titulo_profesional') and request.user.titulo_profesional:
            if not nombre_medico.startswith(request.user.titulo_profesional):
                nombre_medico = f"{request.user.titulo_profesional} {nombre_medico}"
                
    except Exception:
        pass
    
    if request.method == 'POST':
        # Procesar formulario de consulta
        try:
            data = request.POST
            
            # Validar paciente
            paciente_id_post = data.get('paciente_id')
            if paciente_id_post:
                paciente = get_object_or_404(Paciente, id=paciente_id_post, empresa=empresa)
            
            # ORQUESTACIÓN TRANSACCIONAL: Crear Nota SOAP y Orden de Servicio (si aplica)
            with transaction.atomic():
                # Crear nota SOAP
                nota_soap = NotaClinicaSOAP.objects.create(
                    paciente=paciente,
                    empresa=empresa,
                    sucursal=getattr(request.user, 'sucursal', None),
                    medico=request.user,
                    subjetivo=data.get('subjetivo', ''),
                    objetivo=data.get('objetivo', ''),
                    analisis=data.get('analisis', ''),
                    plan=data.get('plan', '')
                )
                
                # VERIFICAR ESTUDIOS SOLICITADOS Y CREAR ORDEN DE SERVICIO AUTOMÁTICAMENTE
                estudios_solicitados = data.get('estudios_solicitados', '')
                estudios_ids = data.getlist('estudios_ids')  # Para formularios con múltiples checkboxes
                
                # Si viene como string JSON, parsearlo
                if estudios_solicitados and isinstance(estudios_solicitados, str):
                    try:
                        estudios_ids = json.loads(estudios_solicitados)
                    except json.JSONDecodeError:
                        # Si no es JSON, intentar como lista separada por comas
                        estudios_ids = [e.strip() for e in estudios_solicitados.split(',') if e.strip()]
                
                # Si hay estudios, crear OrdenDeServicio automáticamente
                if estudios_ids:
                    # Obtener o crear médico para la orden (usar datos del médico precargados)
                    medico_orden = None
                    medico_cedula_orden = data.get('medico_cedula', cedula_profesional or '')
                    medico_nombre_orden = data.get('medico_nombre', nombre_medico)
                    medico_especialidad_orden = data.get('medico_especialidad', especialidad_medico)
                    
                    if medico_cedula_orden:
                        medico_orden, _ = Medico.objects.get_or_create(
                            cedula_profesional=medico_cedula_orden,
                            defaults={
                                'nombre_completo': medico_nombre_orden,
                                'empresa': empresa,
                                'especialidad': medico_especialidad_orden
                            }
                        )
                    
                    from decimal import ROUND_HALF_UP

                    lineas = resolve_lims_cart_ids(list(estudios_ids))
                    if lineas:
                        total_orden = Decimal('0.00')
                        for row in lineas:
                            total_orden += aplicar_precio_convenio(
                                row['precio_base'], row['precio_key'], {}, Decimal('0')
                            )
                        total_orden = total_orden.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                        folio_orden = f"ORD-{timestamp}-{hashlib.md5(f'{empresa.id}-{request.user.id}'.encode()).hexdigest()[:4].upper()}"

                        orden_servicio = OrdenDeServicio.objects.create(
                            empresa=empresa,
                            sucursal=getattr(request.user, 'sucursal', None),
                            paciente=paciente,
                            medico_referente=medico_orden,
                            estado='PENDIENTE_PAGO',
                            total=total_orden,
                            responsable_ingreso=request.user,
                            folio_orden=folio_orden,
                            diagnostico=data.get('analisis', '') or data.get('diagnostico_principal', ''),
                            tipo_servicio='RUTINA',
                        )

                        for row in lineas:
                            precio_momento = aplicar_precio_convenio(
                                row['precio_base'], row['precio_key'], {}, Decimal('0')
                            )
                            desc = (row.get('descripcion_linea') or '')[:300]
                            DetalleOrden.objects.create(
                                orden=orden_servicio,
                                analito=row['analito'],
                                perfil_lims=row['perfil_lims'],
                                paquete_lims=row['paquete_lims'],
                                descripcion_linea=desc,
                                precio_momento=precio_momento,
                                estado_procesamiento='PENDIENTE_TOMA',
                            )

                        nombres_linea = [
                            (r.get('descripcion_linea') or r['precio_key'] or '').strip()
                            for r in lineas
                        ]
                        registrar_trazabilidad(
                            tipo_operacion='CREAR_ORDEN_DESDE_CONSULTA',
                            modulo='CONSULTORIO',
                            referencia_id=orden_servicio.id,
                            referencia_tipo='OrdenDeServicio',
                            accion='CREAR',
                            descripcion=(
                                'Orden de servicio generada automáticamente desde consulta médica. '
                                f"Líneas LIMS: {', '.join(nombres_linea)}"
                            ),
                            usuario=request.user,
                            empresa=empresa,
                            sucursal=getattr(request.user, 'sucursal', None),
                            datos_nuevos={
                                'folio_orden': folio_orden,
                                'total': str(total_orden),
                                'estudios_count': len(lineas),
                                'estudios': nombres_linea,
                            },
                            request=request
                        )
            
            # Si hay indicaciones (tratamiento), crear receta 4.0
            indicaciones = data.get('indicaciones', '')
            if indicaciones:
                # Usar datos precargados del médico (automáticos)
                medico_nombre = data.get('medico_nombre', nombre_medico)
                medico_cedula = data.get('medico_cedula', cedula_profesional or '')
                medico_especialidad = data.get('medico_especialidad', especialidad_medico)
                
                if medico_cedula:
                    medico, _ = Medico.objects.get_or_create(
                        cedula_profesional=medico_cedula,
                        defaults={
                            'nombre_completo': medico_nombre,
                            'empresa': empresa,
                            'especialidad': medico_especialidad
                        }
                    )
                    # Actualizar si cambió el nombre o especialidad
                    if medico.nombre_completo != medico_nombre or medico.especialidad != medico_especialidad:
                        medico.nombre_completo = medico_nombre
                        medico.especialidad = medico_especialidad
                        medico.save()
                else:
                    medico = None
                
                # Generar folio único
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                folio_receta = f"REC-{timestamp}-{hashlib.md5(f'{empresa.id}-{request.user.id}'.encode()).hexdigest()[:4].upper()}"
                
                # Crear receta 4.0
                receta = Receta.objects.create(
                    medico=medico,
                    paciente=paciente,
                    empresa=empresa,
                    sucursal=getattr(request.user, 'sucursal', None),
                    folio_receta=folio_receta,
                    fecha_emision=django_timezone.now(),
                    # Signos vitales
                    presion_arterial_sistolica=int(data.get('pa_sistolica')) if data.get('pa_sistolica') else None,
                    presion_arterial_diastolica=int(data.get('pa_diastolica')) if data.get('pa_diastolica') else None,
                    frecuencia_cardiaca=int(data.get('fc')) if data.get('fc') else None,
                    frecuencia_respiratoria=int(data.get('fr')) if data.get('fr') else None,
                    temperatura=Decimal(str(data.get('temp'))) if data.get('temp') else None,
                    peso=Decimal(str(data.get('peso'))) if data.get('peso') else None,
                    talla=Decimal(str(data.get('talla'))) if data.get('talla') else None,
                    saturacion_oxigeno=int(data.get('spo2')) if data.get('spo2') else None,
                    glucosa=Decimal(str(data.get('glucosa'))) if data.get('glucosa') else None,
                    # Diagnóstico e Indicaciones
                    diagnostico_principal=data.get('diagnostico_principal', ''),
                    diagnostico_secundario=data.get('diagnostico_secundario', ''),
                    indicaciones=indicaciones,
                    # Datos del Médico (precargados automáticamente)
                    medico_nombre_completo=medico_nombre,
                    medico_cedula=medico_cedula or '',
                    medico_especialidad=data.get('medico_especialidad', especialidad_medico),
                    medico_firma_digital=firma_digital.imagen_firma if firma_digital else None,
                    fecha_vencimiento_cedula=fecha_vencimiento_cedula,
                    cedula_vigente=fecha_vencimiento_cedula is None or fecha_vencimiento_cedula >= date.today()
                )
                
                # LÓGICA NUEVA: Procesar items de receta (medicamentos) como SUGERIDOS
                # Capturar items de la tabla dinámica del template
                receta_items_data = []
                for key in data.keys():
                    if key.startswith('receta_items[') and '][producto_id]' in key:
                        # Extraer índice del item
                        idx_str = key.split('[')[1].split(']')[0]
                        producto_id = data.get(f'receta_items[{idx_str}][producto_id]')
                        texto_libre = data.get(f'receta_items[{idx_str}][texto_libre]', '').strip()
                        cantidad_str = data.get(f'receta_items[{idx_str}][cantidad]', '1')
                        
                        try:
                            cantidad = int(cantidad_str)
                        except (ValueError, TypeError):
                            cantidad = 1
                        
                        receta_items_data.append({
                            'producto_id': producto_id,
                            'texto_libre': texto_libre,
                            'cantidad': cantidad
                        })
                
                # Crear RecetaItem con estado SUGERIDO
                for item_data in receta_items_data:
                    producto_id = item_data['producto_id']
                    texto_libre = item_data['texto_libre']
                    cantidad = item_data['cantidad']
                    
                    if producto_id:
                        # Medicamento del catálogo
                        try:
                            producto = Producto.objects.get(id=producto_id, empresa=empresa)
                            RecetaItem.objects.create(
                                receta=receta,
                                medicamento=producto,
                                texto_libre=None,
                                cantidad=cantidad,
                                precio_momento=producto.precio_publico if hasattr(producto, 'precio_publico') else Decimal('0.00'),
                                estado='SUGERIDO'
                            )
                        except Producto.DoesNotExist:
                            pass
                    elif texto_libre:
                        # Medicamento en texto libre (no catalogado)
                        RecetaItem.objects.create(
                            receta=receta,
                            medicamento=None,
                            texto_libre=texto_libre,
                            cantidad=cantidad,
                            precio_momento=Decimal('0.00'),
                            estado='SUGERIDO'
                        )
                
                # Calcular IMC
                receta.calcular_imc()
                receta.save()
                
                # Generar QR de validación
                qr_data = {
                    'folio': receta.folio_receta,
                    'medico_cedula': receta.medico_cedula,
                    'fecha_emision': receta.fecha_emision.isoformat(),
                    'hash': calcular_hash_verificacion_receta(receta)
                }
                
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(json.dumps(qr_data))
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                receta.qr_verificacion = base64.b64encode(buffer.read()).decode('utf-8')
                receta.hash_verificacion = calcular_hash_verificacion_receta(receta)
                receta.save()
                
                # Crear log de auditoría
                crear_log_auditoria(
                    empresa=empresa,
                    usuario=request.user,
                    accion=AuditLog.ACCION_CREATE,
                    modelo='Receta',
                    objeto_id=receta.id,
                    datos_anterior=None,
                    datos_nuevo={
                        'folio': receta.folio_receta,
                        'medico_cedula': receta.medico_cedula,
                        'paciente': paciente.nombre_completo if paciente else 'Externo',
                        'diagnostico': receta.diagnostico_principal
                    },
                    sucursal=request.user.sucursal,
                    request=request
                )
                
                return redirect('ver_receta_medica', receta_id=receta.id)
            
            return redirect('consulta_medica', paciente_id=paciente.id if paciente else None)
            
        except Exception as e:
            return render(request, 'core/consulta_medica.html', {
                'empresa': empresa,
                'paciente': paciente,
                'signos_vitales': signos_vitales,
                'antecedentes': antecedentes,
                'medicos': medicos,
                'firma_digital': firma_digital,
                'cedula_profesional': cedula_profesional,
                'fecha_vencimiento_cedula': fecha_vencimiento_cedula,
                'error': f'Error al crear consulta: {str(e)}'
            })
    
    return render(request, 'core/consulta_medica.html', {
        'paciente': paciente,
        'signos_vitales': signos_vitales,
        'antecedentes': antecedentes,
        'medicos': medicos,
        'firma_digital': firma_digital,
        'cedula_profesional': cedula_profesional,
        'fecha_vencimiento_cedula': fecha_vencimiento_cedula,
        'especialidad_medico': especialidad_medico,
        'nombre_medico': nombre_medico,
        'fecha_actual': date.today(),
        'empresa': empresa,
    })


@login_required
@require_http_methods(["POST"])
def verificar_existencia_farmacia(request):
    """API para verificar existencia de medicamentos en farmacia (FEFO)."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'medicamentos_encontrados': [], 'mensaje': 'Usuario sin empresa asignada'})
    
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'medicamentos_encontrados': [], 'mensaje': f'JSON inválido: {e}'}, status=400)
        indicaciones = data.get('indicaciones', '').lower()
        
        # Extraer nombres de medicamentos del texto de indicaciones
        medicamentos_encontrados = []
        productos_farmacia = Producto.objects.filter(empresa=empresa).select_related().prefetch_related('lotes')
        
        hoy = date.today()
        fecha_limite = hoy + timedelta(days=30)
        
        for producto in productos_farmacia:
            # Buscar coincidencias en nombre comercial o sustancia activa
            nombre_producto = producto.nombre.lower()
            sustancia = (producto.sustancia_activa or '').lower()
            
            # Verificar si el nombre del producto aparece en las indicaciones
            if nombre_producto in indicaciones or sustancia in indicaciones:
                # Obtener lote más próximo a vencer (FEFO)
                lote_proximo = producto.lotes.filter(cantidad__gt=0).order_by('fecha_caducidad').first()
                
                stock_total = sum(l.cantidad for l in producto.lotes.filter(cantidad__gt=0))
                
                dias_restantes = None
                es_critico = False
                if lote_proximo:
                    dias_restantes = (lote_proximo.fecha_caducidad - hoy).days
                    es_critico = dias_restantes <= 7
                
                medicamentos_encontrados.append({
                    'producto': producto.nombre,
                    'sustancia_activa': producto.sustancia_activa or '',
                    'stock': stock_total,
                    'disponible': stock_total > 0,
                    'precio': float(producto.precio_publico),
                    'lote_proximo': lote_proximo.numero_lote if lote_proximo else None,
                    'fecha_caducidad': lote_proximo.fecha_caducidad.strftime('%d/%m/%Y') if lote_proximo else None,
                    'dias_restantes': dias_restantes,
                    'es_critico': es_critico,
                    'estado': 'disponible' if stock_total > 0 and dias_restantes and dias_restantes > 7 else ('critico' if es_critico else 'agotado')
                })
        
        return JsonResponse({
            'status': 'success',
            'medicamentos': medicamentos_encontrados
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=400)


@login_required
def ver_receta_medica(request, receta_id):
    """Ver receta médica 4.0 con QR de validación."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    receta = get_object_or_404(Receta, id=receta_id, empresa=empresa)
    
    return render(request, 'core/ver_receta_medica.html', {
        'empresa': empresa,
        'receta': receta
    })


@login_required
def generar_pdf_receta(request, receta_id):
    """Genera PDF de receta médica 4.0 con QR de validación."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        from django.http import HttpResponse
        return HttpResponse('Usuario sin empresa asignada', status=403)
    receta = get_object_or_404(Receta, id=receta_id, empresa=empresa)

    try:
        receta.validar_items_antes_de_emitir()
    except Exception as e:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, str(e))
        return redirect('ver_receta_medica', receta_id=receta.id)

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    import io
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header con identidad de empresa
    color_primario = empresa.color_primario or '#D9230F'
    
    # Título
    p.setFillColor(color_primario)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, "RECETA MÉDICA")
    
    # Datos del paciente
    p.setFont("Helvetica", 10)
    p.setFillColor("black")
    y = height - 100
    
    if receta.paciente:
        p.drawString(50, y, f"Paciente: {receta.paciente.nombre_completo}")
        y -= 20
        if receta.paciente.fecha_nacimiento:
            edad = (date.today() - receta.paciente.fecha_nacimiento).days // 365
            p.drawString(50, y, f"Edad: {edad} años")
            y -= 20
        if receta.paciente.telefono:
            p.drawString(50, y, f"Teléfono: {receta.paciente.telefono}")
            y -= 20
    
    # Signos vitales
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Signos Vitales:")
    p.setFont("Helvetica", 10)
    y -= 20
    
    if receta.presion_arterial_sistolica and receta.presion_arterial_diastolica:
        p.drawString(50, y, f"PA: {receta.presion_arterial_sistolica}/{receta.presion_arterial_diastolica} mmHg")
        y -= 15
    if receta.frecuencia_cardiaca:
        p.drawString(50, y, f"FC: {receta.frecuencia_cardiaca} lat/min")
        y -= 15
    if receta.temperatura:
        p.drawString(50, y, f"Temp: {receta.temperatura}°C")
        y -= 15
    if receta.peso and receta.talla:
        p.drawString(50, y, f"Peso: {receta.peso} kg | Talla: {receta.talla} m | IMC: {receta.imc:.2f if receta.imc else 'N/A'}")
        y -= 15
    
    # Diagnóstico
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Diagnóstico:")
    p.setFont("Helvetica", 10)
    y -= 20
    p.drawString(50, y, receta.diagnostico_principal)
    y -= 15
    if receta.diagnostico_secundario:
        p.drawString(50, y, receta.diagnostico_secundario)
        y -= 15
    
    # Indicaciones (IDX) - Parsear como lista de medicamentos
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "MEDICAMENTOS PRESCRITOS:")
    p.setFont("Helvetica", 10)
    y -= 25
    
    # Parsear indicaciones: buscar líneas que parezcan medicamentos
    # Formatos soportados:
    # 1. "Medicamento - Dosis - Frecuencia"
    # 2. "Medicamento, Dosis, Frecuencia"
    # 3. "Medicamento: Dosis - Frecuencia"
    # 4. Líneas numeradas (1. Medicamento...)
    # 5. Líneas simples con salto de línea
    
    indicaciones_lines = receta.indicaciones.split('\n')
    medicamento_num = 1
    
    for line in indicaciones_lines:
        if not line.strip():
            continue
        
        # Verificar si hay espacio suficiente
        if y < 120:
            p.showPage()
            y = height - 50
        
        # Intentar detectar formato estructurado
        line_clean = line.strip()
        
        # Formato 1: "Medicamento - Dosis - Frecuencia"
        if ' - ' in line_clean:
            partes = line_clean.split(' - ')
            if len(partes) >= 2:
                medicamento = partes[0].strip()
                dosis = partes[1].strip() if len(partes) > 1 else ''
                frecuencia = partes[2].strip() if len(partes) > 2 else ''
                
                p.setFont("Helvetica-Bold", 10)
                p.drawString(50, y, f"{medicamento_num}. {medicamento}")
                y -= 16
                p.setFont("Helvetica", 9)
                if dosis:
                    p.drawString(70, y, f"• Dosis: {dosis}")
                    y -= 14
                if frecuencia:
                    p.drawString(70, y, f"• Frecuencia: {frecuencia}")
                    y -= 14
                medicamento_num += 1
                y -= 5  # Espacio entre medicamentos
                continue
        
        # Formato 2: "Medicamento, Dosis, Frecuencia"
        if ',' in line_clean and line_clean.count(',') >= 2:
            partes = [p.strip() for p in line_clean.split(',')]
            if len(partes) >= 2:
                medicamento = partes[0]
                dosis = partes[1] if len(partes) > 1 else ''
                frecuencia = partes[2] if len(partes) > 2 else ''
                
                p.setFont("Helvetica-Bold", 10)
                p.drawString(50, y, f"{medicamento_num}. {medicamento}")
                y -= 16
                p.setFont("Helvetica", 9)
                if dosis:
                    p.drawString(70, y, f"• Dosis: {dosis}")
                    y -= 14
                if frecuencia:
                    p.drawString(70, y, f"• Frecuencia: {frecuencia}")
                    y -= 14
                medicamento_num += 1
                y -= 5
                continue
        
        # Formato 3: "Medicamento: Dosis - Frecuencia"
        if ':' in line_clean and ' - ' in line_clean:
            partes_colon = line_clean.split(':', 1)
            if len(partes_colon) == 2:
                medicamento = partes_colon[0].strip()
                resto = partes_colon[1].strip()
                if ' - ' in resto:
                    partes_dash = resto.split(' - ', 1)
                    dosis = partes_dash[0].strip()
                    frecuencia = partes_dash[1].strip() if len(partes_dash) > 1 else ''
                else:
                    dosis = resto
                    frecuencia = ''
                
                p.setFont("Helvetica-Bold", 10)
                p.drawString(50, y, f"{medicamento_num}. {medicamento}")
                y -= 16
                p.setFont("Helvetica", 9)
                if dosis:
                    p.drawString(70, y, f"• Dosis: {dosis}")
                    y -= 14
                if frecuencia:
                    p.drawString(70, y, f"• Frecuencia: {frecuencia}")
                    y -= 14
                medicamento_num += 1
                y -= 5
                continue
        
        # Formato 4: Línea numerada (1. Medicamento...)
        if line_clean[0].isdigit() and (line_clean[1] == '.' or line_clean[1:3] == '. '):
            # Remover numeración existente
            line_clean = line_clean.split('.', 1)[1].strip() if '.' in line_clean else line_clean
        
        # Formato 5: Línea simple - mostrar como está
        p.setFont("Helvetica", 10)
        # Si la línea es muy larga, dividirla
        if len(line_clean) > 75:
            # Dividir en palabras
            palabras = line_clean.split()
            linea_actual = f"{medicamento_num}. "
            for palabra in palabras:
                if len(linea_actual + palabra) > 75:
                    p.drawString(50, y, linea_actual)
                    y -= 15
                    linea_actual = "   " + palabra + " "
                else:
                    linea_actual += palabra + " "
            if linea_actual.strip():
                p.drawString(50, y, linea_actual)
                y -= 15
        else:
            p.drawString(50, y, f"{medicamento_num}. {line_clean}")
            y -= 15
        
        medicamento_num += 1
        y -= 5  # Espacio entre medicamentos
        
        if medicamento_num > 25:  # Límite de medicamentos
            break
    
    # Si no hay espacio suficiente, nueva página
    if y < 250:
        p.showPage()
        y = height - 50
    
    # Datos del médico y firma
    y -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "DATOS DEL MÉDICO:")
    p.setFont("Helvetica", 10)
    y -= 20
    
    # Nombre del médico
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, f"Dr. {receta.medico_nombre_completo}")
    y -= 18
    
    # Cédula Profesional
    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Cédula Profesional: {receta.medico_cedula}")
    y -= 18
    
    # Universidad
    if receta.medico_universidad:
        p.drawString(50, y, f"Universidad: {receta.medico_universidad}")
        y -= 18
    else:
        # Espacio reservado si no hay universidad
        p.setFont("Helvetica-Oblique", 9)
        p.setFillColor("gray")
        p.drawString(50, y, "Universidad: [No especificada]")
        p.setFillColor("black")
        y -= 18
    
    # Especialidad
    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Especialidad: {receta.medico_especialidad}")
    y -= 30
    
    # Firma digital - Espacio reservado siempre
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Firma del Médico:")
    y -= 5
    
    # Dibujar recuadro para firma
    firma_x = 50
    firma_y = y - 50
    firma_width = 150
    firma_height = 50
    p.rect(firma_x, firma_y, firma_width, firma_height)
    
    # Intentar cargar y mostrar firma digital
    if receta.medico_firma_digital:
        try:
            from PIL import Image
            import os
            from django.conf import settings
            
            # Obtener ruta de la firma
            if hasattr(receta.medico_firma_digital, 'path'):
                firma_path = receta.medico_firma_digital.path
            else:
                firma_path = os.path.join(settings.MEDIA_ROOT, str(receta.medico_firma_digital))
            
            if os.path.exists(firma_path):
                firma_image = ImageReader(firma_path)
                # Ajustar tamaño manteniendo proporción
                p.drawImage(firma_image, firma_x + 5, firma_y + 5, width=firma_width - 10, height=firma_height - 10, preserveAspectRatio=True)
        except Exception as e:
            # Si falla, dejar espacio en blanco
            p.setFont("Helvetica-Oblique", 8)
            p.setFillColor("gray")
            p.drawString(firma_x + 10, firma_y + 20, "[Firma no disponible]")
            p.setFillColor("black")
    else:
        # Espacio reservado sin firma
        p.setFont("Helvetica-Oblique", 8)
        p.setFillColor("gray")
        p.drawString(firma_x + 10, firma_y + 20, "[Espacio para firma]")
        p.setFillColor("black")
    
    # Fecha de emisión - Más visible
    y = firma_y - 30
    p.setFont("Helvetica-Bold", 10)
    # Formatear fecha en español
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
             'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    fecha_str = f"{receta.fecha_emision.day} de {meses[receta.fecha_emision.month - 1]} de {receta.fecha_emision.year}"
    p.drawString(50, y, f"Fecha de Emisión: {fecha_str}")
    y -= 15
    p.setFont("Helvetica", 9)
    p.drawString(50, y, f"Folio: {receta.folio_receta}")
    
    # QR de validación (si existe) - En la esquina superior derecha
    if receta.qr_verificacion:
        try:
            qr_image = ImageReader(io.BytesIO(base64.b64decode(receta.qr_verificacion)))
            qr_size = 60
            qr_x = width - qr_size - 50
            qr_y = height - qr_size - 50
            p.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)
            p.setFont("Helvetica", 7)
            p.drawString(qr_x, qr_y - 15, "Validar QR")
        except Exception:
            pass
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    from django.http import HttpResponse
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receta_{receta.folio_receta}.pdf"'
    return response


def calcular_hash_verificacion_receta(receta):
    """Calcula hash SHA-256 para verificación de autenticidad de receta."""
    datos = {
        'folio': receta.folio_receta,
        'medico_cedula': receta.medico_cedula,
        'fecha_emision': receta.fecha_emision.isoformat(),
        'diagnostico': receta.diagnostico_principal,
        'paciente': receta.paciente.nombre_completo if receta.paciente else ''
    }
    return calcular_hash_auditoria(datos)


@login_required
def verificar_qr_receta(request):
    """API para verificar autenticidad de receta mediante QR."""
    if request.method == 'POST':
        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'status': 'error', 'mensaje': 'Cuerpo JSON inválido'}, status=400)
            raw_qr = data.get('qr_data') or '{}'
            if isinstance(raw_qr, str):
                try:
                    qr_data = json.loads(raw_qr)
                except json.JSONDecodeError:
                    return JsonResponse({'status': 'error', 'mensaje': 'qr_data inválido'}, status=400)
            else:
                qr_data = raw_qr if isinstance(raw_qr, dict) else {}
            
            folio = qr_data.get('folio')
            if not folio:
                return JsonResponse({'status': 'error', 'mensaje': 'Folio no válido'}, status=400)
            
            receta = Receta.objects.filter(folio_receta=folio).first()
            if not receta:
                return JsonResponse({
                    'status': 'error',
                    'mensaje': 'Receta no encontrada',
                    'autentica': False
                })
            
            # Verificar hash
            hash_calculado = calcular_hash_verificacion_receta(receta)
            hash_recibido = qr_data.get('hash')
            
            autentica = hash_calculado == hash_recibido == receta.hash_verificacion
            
            # Verificar vigencia de cédula
            cedula_vigente = receta.cedula_vigente
            if receta.fecha_vencimiento_cedula:
                cedula_vigente = receta.fecha_vencimiento_cedula >= date.today()
            
            return JsonResponse({
                'status': 'success',
                'autentica': autentica,
                'receta': {
                    'folio': receta.folio_receta,
                    'medico': receta.medico_nombre_completo,
                    'cedula': receta.medico_cedula,
                    'fecha_emision': receta.fecha_emision.isoformat(),
                    'paciente': receta.paciente.nombre_completo if receta.paciente else 'Paciente Externo',
                    'diagnostico': receta.diagnostico_principal
                },
                'cedula_vigente': cedula_vigente,
                'fecha_vencimiento_cedula': receta.fecha_vencimiento_cedula.isoformat() if receta.fecha_vencimiento_cedula else None
            })
        
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'mensaje': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error'}, status=405)


# ==============================================================================
# ==============================================================================
# MÓDULO MÉDICO: ULTRASONIDO
# ==============================================================================
from django.utils import timezone as django_timezone
import os


@login_required
def lista_trabajo_usg(request):
    """Lista de reportes de ultrasonido de la empresa."""
    from consultorio.models import ReporteUltrasonido
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    estado = request.GET.get('estado', '')
    qs = ReporteUltrasonido.objects.filter(empresa=empresa).select_related('paciente', 'medico')
    if estado:
        qs = qs.filter(estado=estado)

    from django.core.paginator import Paginator
    paginator = Paginator(qs.order_by('-fecha_estudio'), 25)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'core/medico/lista_trabajo_usg.html', {
        'empresa': empresa,
        'page_obj': page_obj,
        'estado_filtro': estado,
        'estados': ReporteUltrasonido.ESTADO_CHOICES,
    })




@login_required
def captura_reporte_usg(request, paciente_id=None):
    """Vista para capturar/crear un nuevo reporte de ultrasonido."""
    from consultorio.models import ReporteUltrasonido
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('lista_trabajo_usg')

    paciente = None
    if paciente_id:
        from core.models import Paciente
        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    if request.method == 'POST':
        try:
            from core.models import Paciente
            pac_id = request.POST.get('paciente_id')
            paciente = get_object_or_404(Paciente, id=pac_id, empresa=empresa)
            medico = getattr(request.user, 'medico', None)
            reporte = ReporteUltrasonido.objects.create(
                empresa=empresa,
                paciente=paciente,
                medico=medico,
                tipo_estudio=request.POST.get('tipo_estudio', 'GENERAL'),
                hallazgos=request.POST.get('hallazgos', ''),
                conclusion=request.POST.get('conclusion', ''),
                estado='PENDIENTE',
            )
            messages.success(request, f'Reporte USG creado: {reporte.id}')
            return redirect('lista_trabajo_usg')
        except Exception as e:
            messages.error(request, f'Error al crear reporte: {e}')

    from core.models import Paciente as PacienteModel
    pacientes = PacienteModel.objects.filter(empresa=empresa).order_by('nombres')[:50]
    return render(request, 'core/medico/captura_reporte_usg.html', {
        'empresa': empresa,
        'paciente': paciente,
        'pacientes': pacientes,
    })


@login_required
def descargar_pdf_ultrasonido(request, reporte_id):
    """Genera y descarga el PDF de un reporte de ultrasonido."""
    from consultorio.models import ReporteUltrasonido
    from core.utils.pdf_generator import render_to_pdf
    from django.http import HttpResponse
    from django.contrib import messages
    empresa = empresa_efectiva_request(request)
    reporte = get_object_or_404(ReporteUltrasonido, id=reporte_id, empresa=empresa)
    pdf = render_to_pdf('core/medico/reporte_usg_pdf.html', {'reporte': reporte, 'empresa': empresa})
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=usg_{reporte.id}.pdf'
        return response
    messages.error(request, 'No se pudo generar el PDF.')
    return redirect('lista_trabajo_usg')

