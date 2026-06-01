"""
Vista de Cotización Flash (UI Móvil)
Diseñada para tablets/móviles con flujo rápido de cotización.
"""
import json
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from core.models import Empresa, Paciente
from laboratorio.models import Estudio as LabEstudio, PerfilLaboratorio
from core.utils.whatsapp_sender import generar_enlace_whatsapp, generar_mensaje_cotizacion


@login_required
def cotizacion_rapida(request):
    """Vista de Cotización Flash - UI Móvil para tablets/móviles."""
    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    
    return render(request, 'core/cotizacion_rapida.html', {
        'empresa': empresa,
    })


@login_required
@require_http_methods(["POST"])
def api_buscar_paciente_cotizacion(request):
    """API para buscar/crear paciente en cotización rápida."""
    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario no tiene empresa asignada'}, status=400)
    
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({'status': 'error', 'mensaje': 'Búsqueda vacía'}, status=400)
        
        # Buscar pacientes existentes
        pacientes = Paciente.objects.filter(
            empresa=empresa,
            nombre_completo__icontains=query
        )[:10]
        
        resultados = [{
            'id': p.id,
            'nombre': p.nombre_completo,
            'telefono': p.telefono or '',
            'email': p.email or '',
            'fecha_nacimiento': p.fecha_nacimiento.strftime('%d/%m/%Y') if p.fecha_nacimiento else ''
        } for p in pacientes]
        
        return JsonResponse({
            'status': 'success',
            'pacientes': resultados
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_crear_paciente_rapido(request):
    """API para crear paciente rápido desde cotización."""
    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario no tiene empresa asignada'}, status=400)
    
    try:
        data = json.loads(request.body)
        
        paciente = Paciente.objects.create(
            empresa=empresa,
            sucursal=request.user.sucursal,
            nombre_completo=data.get('nombre_completo', ''),
            telefono=data.get('telefono', ''),
            email=data.get('email', ''),
            fecha_nacimiento=data.get('fecha_nacimiento') if data.get('fecha_nacimiento') else None,
        )
        
        return JsonResponse({
            'status': 'success',
            'paciente': {
                'id': paciente.id,
                'nombre': paciente.nombre_completo,
                'telefono': paciente.telefono or '',
                'email': paciente.email or '',
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_buscar_estudios_cotizacion(request):
    """API para buscar estudios con autocompletado del Catálogo 163."""
    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario no tiene empresa asignada'}, status=400)
    
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip().lower()
        
        if not query:
            return JsonResponse({'status': 'error', 'mensaje': 'Búsqueda vacía'}, status=400)
        
        # Catálogo clínico local (laboratorio.Estudio); órdenes operativas usan LIMS v7.5 en recepción.
        try:
            estudios = LabEstudio.objects.select_related('categoria').filter(
                Q(nombre__icontains=query) | Q(codigo__icontains=query) | Q(keywords__icontains=query)
            ).order_by('nombre')[:20]
        except Exception:
            estudios = []

        perfiles = PerfilLaboratorio.objects.filter(
            empresa=empresa,
            nombre__icontains=query
        )[:10]

        resultados_estudios = []
        for e in estudios:
            precio = float(getattr(e, 'precio_base', 0) or getattr(e, 'precio', 0) or 0)
            seccion = ''
            if hasattr(e, 'categoria') and e.categoria:
                seccion = e.categoria.nombre
            elif hasattr(e, 'seccion') and e.seccion:
                seccion = e.seccion.nombre
            resultados_estudios.append({
                'id': e.id,
                'nombre': e.nombre,
                'codigo': e.codigo or '',
                'tipo': 'estudio',
                'precio': precio,
                'seccion': seccion,
            })
        
        resultados_perfiles = [{
            'id': p.id,
            'nombre': p.nombre,
            'tipo': 'perfil',
            'precio': float(p.precio),
            'descripcion': p.descripcion or '',
            'pruebas_incluidas': p.pruebas.count()
        } for p in perfiles]
        
        return JsonResponse({
            'status': 'success',
            'estudios': resultados_estudios,
            'perfiles': resultados_perfiles
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_calcular_total_cotizacion(request):
    """API para calcular total en tiempo real de la cotización."""
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        
        total = Decimal('0.00')
        
        for item in items:
            precio = Decimal(str(item.get('precio', 0)))
            cantidad = int(item.get('cantidad', 1))
            total += precio * cantidad
        
        return JsonResponse({
            'status': 'success',
            'total': float(total),
            'total_formateado': f'${total:,.2f}'
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_enviar_whatsapp_cotizacion(request):
    """API para enviar cotización por WhatsApp."""
    try:
        data = json.loads(request.body)
        
        paciente_nombre = data.get('paciente_nombre', '')
        paciente_telefono = data.get('paciente_telefono', '')
        estudios = data.get('estudios', [])
        total = Decimal(str(data.get('total', 0)))
        
        if not paciente_telefono:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Teléfono del paciente requerido'
            }, status=400)
        
        # Generar mensaje
        mensaje = generar_mensaje_cotizacion(paciente_nombre, estudios, total)
        
        # Generar enlace WhatsApp
        enlace = generar_enlace_whatsapp(paciente_telefono, mensaje)
        
        return JsonResponse({
            'status': 'success',
            'enlace_whatsapp': enlace,
            'mensaje': mensaje
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def convertir_cotizacion_orden(request):
    """Convierte cotización a orden de servicio y redirige a recepción."""
    try:
        data = json.loads(request.body)
        
        paciente_id = data.get('paciente_id')
        estudios_ids = data.get('estudios_ids', [])
        perfiles_ids = data.get('perfiles_ids', [])
        
        if not paciente_id:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Paciente requerido'
            }, status=400)
        
        # Guardar en sesión para precargar en recepción
        request.session['cotizacion_flash'] = {
            'paciente_id': paciente_id,
            'estudios_ids': estudios_ids,
            'perfiles_ids': perfiles_ids,
        }
        
        return JsonResponse({
            'status': 'success',
            'redirect_url': '/laboratorio/recepcion/'
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=400)
