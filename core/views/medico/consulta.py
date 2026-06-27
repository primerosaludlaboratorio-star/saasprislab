"""
core/views/medico/consulta.py
Consulta médica SOAP y verificación de existencia en farmacia.
"""
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.models import (
    AuditLog, DetalleOrden, Empresa, FirmaDigital, Lote, Medico,
    NotaClinicaSOAP, OrdenDeServicio, Paciente, Producto, Receta, RecetaItem,
)
from core.lims_cart import resolve_lims_cart_ids, aplicar_precio_convenio
from core.utils.auditoria_helper import crear_log_auditoria, calcular_hash_auditoria
from core.utils.trazabilidad import registrar_trazabilidad, serializar_modelo
from core.utils.empresa_request import empresa_efectiva_request
import logging


@login_required
def consulta_medica(request, paciente_id=None):
    """Formulario de consulta médica con SOAP y generación de receta 4.0."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    paciente = None
    signos_vitales = {}
    antecedentes = []
    
    if paciente_id:
        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
        
        ultima_nota = NotaClinicaSOAP.objects.filter(
            paciente=paciente,
            empresa=empresa
        ).order_by('-fecha_consulta').first()
        
        if ultima_nota:
            signos_vitales = {
                'pa_sistolica': None,
                'pa_diastolica': None,
                'fc': None,
                'fr': None,
            }
    
    medicos = Medico.objects.filter(empresa=empresa, activo=True).order_by('nombre_completo')
    
    return render(request, 'core/consulta_medica.html', {
        'empresa': empresa,
        'paciente': paciente,
        'medicos': medicos,
        'signos_vitales': signos_vitales,
        'antecedentes': antecedentes,
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
        
        medicamentos_encontrados = []
        productos_farmacia = Producto.objects.filter(empresa=empresa).select_related().prefetch_related('lotes')
        
        hoy = date.today()
        fecha_limite = hoy + timedelta(days=30)
        
        for producto in productos_farmacia:
            nombre_producto = producto.nombre.lower()
            sustancia = (producto.sustancia_activa or '').lower()
            
            if nombre_producto in indicaciones or sustancia in indicaciones:
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
        logging.getLogger(__name__).exception("Error inesperado en verificar_existencia_farmacia (consulta.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=400)