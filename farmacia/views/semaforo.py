"""
PRISLAB V5 - Vista del Semáforo de Caducidad (Farmacia)
Dashboard visual con alertas por proximidad de caducidad
"""

import logging
from datetime import date, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.db.models import F, Sum

from core.models import Lote, Producto
from core.utils.empresa_request import get_empresa_usuario

logger = logging.getLogger(__name__)

# Leer umbrales desde settings (configurables por entorno)
_DIAS_CRITICO = getattr(settings, 'FARMACIA_DIAS_CADUCIDAD_CRITICO', 30)
_DIAS_ALERTA = getattr(settings, 'FARMACIA_DIAS_CADUCIDAD_ALERTA', 90)


def es_farmacia_o_director(user):
    """Verifica si el usuario tiene permisos de farmacia o es director."""
    if not get_empresa_usuario(user):
        return False
    return (
        user.is_superuser or 
        user.groups.filter(name__in=['FARMACIA', 'DIRECTOR']).exists()
    )


@login_required
@user_passes_test(es_farmacia_o_director)
def dashboard_semaforo_caducidad(request):
    """
    Dashboard visual del Semáforo de Caducidad.
    
    Clasificación (umbrales configurables vía FARMACIA_DIAS_CADUCIDAD_CRITICO/ALERTA en settings):
    - ROJO   (CRITICO): Caduca en < FARMACIA_DIAS_CADUCIDAD_CRITICO días (default 30)
    - AMARILLO (ALERTA): Caduca en entre CRITICO y FARMACIA_DIAS_CADUCIDAD_ALERTA días (default 90)
    - VERDE  (NORMAL):  Caduca en > FARMACIA_DIAS_CADUCIDAD_ALERTA días (default 90)
    """
    hoy = date.today()
    fecha_critico = hoy + timedelta(days=_DIAS_CRITICO)
    fecha_alerta = hoy + timedelta(days=_DIAS_ALERTA)

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    # Lotes YA VENCIDOS con stock > 0 — BAJA INMEDIATA REQUERIDA
    lotes_vencidos = Lote.objects.filter(
        producto__empresa=empresa,
        cantidad__gt=0,
        fecha_caducidad__lt=hoy
    ).select_related('producto').order_by('fecha_caducidad')

    lotes_activos = Lote.objects.filter(
        producto__empresa=empresa,
        cantidad__gt=0,
        fecha_caducidad__gte=hoy
    ).select_related('producto')

    # CRITICOS: < DIAS_CRITICO días
    lotes_criticos = lotes_activos.filter(
        fecha_caducidad__lt=fecha_critico
    ).order_by('fecha_caducidad')

    # ALERTA: entre DIAS_CRITICO y DIAS_ALERTA días
    lotes_alerta = lotes_activos.filter(
        fecha_caducidad__gte=fecha_critico,
        fecha_caducidad__lt=fecha_alerta
    ).order_by('fecha_caducidad')

    # NORMALES: > DIAS_ALERTA días (solo contar, no listar todos)
    count_normales = lotes_activos.filter(
        fecha_caducidad__gte=fecha_alerta
    ).count()
    
    # Calcular totales
    total_lotes = lotes_activos.count()
    count_criticos = lotes_criticos.count()
    count_alerta = lotes_alerta.count()
    
    # Valor en riesgo (suma del costo de los lotes críticos)
    valor_en_riesgo = sum(
        float(lote.cantidad) * float(lote.costo_adquisicion) 
        for lote in lotes_criticos
    )
    
    # Productos más urgentes (top 10 por proximidad de caducidad)
    productos_urgentes = lotes_criticos[:10]
    
    valor_vencidos = sum(
        float(l.cantidad) * float(l.costo_adquisicion)
        for l in lotes_vencidos
    )

    context = {
        'lotes_vencidos': lotes_vencidos,
        'count_vencidos': lotes_vencidos.count(),
        'valor_vencidos': valor_vencidos,
        'lotes_criticos': lotes_criticos,
        'lotes_alerta': lotes_alerta,
        'count_criticos': count_criticos,
        'count_alerta': count_alerta,
        'count_normales': count_normales,
        'total_lotes': total_lotes,
        'valor_en_riesgo': valor_en_riesgo,
        'productos_urgentes': productos_urgentes,
        'fecha_hoy': hoy,
    }
    
    return render(request, 'farmacia/semaforo_caducidad.html', context)


@login_required
@user_passes_test(es_farmacia_o_director)
def dashboard_stock_critico(request):
    """
    Dashboard de productos con stock bajo (por debajo del stock mínimo).
    Complementario al semáforo de caducidad.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    # Productos con stock bajo (por debajo de su propio stock_minimo configurado)
    productos_criticos = Producto.objects.filter(
        empresa=empresa,
        stock__gt=0,
        stock__lt=F('stock_minimo'),
    ).order_by('stock')
    
    # Productos agotados
    productos_agotados = Producto.objects.filter(
        empresa=empresa,
        stock=0
    ).order_by('nombre')
    
    context = {
        'productos_criticos': productos_criticos,
        'productos_agotados': productos_agotados,
        'count_criticos': productos_criticos.count(),
        'count_agotados': productos_agotados.count(),
    }
    
    return render(request, 'farmacia/stock_critico.html', context)
