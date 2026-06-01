"""
PRISLAB V5.0 - VISTAS STUB: INVENTARIO
=======================================
Fecha: 2 de Febrero de 2026
Tipo: Stub View (Vista de Respaldo)

PROPÓSITO:
- Proveer una vista temporal para el módulo de Inventario
- Evitar errores 500 por referencias a vistas no implementadas
- Mostrar feedback amigable al usuario

ESTADO: EN DESARROLLO
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import logging

logger = logging.getLogger('inventario')


@login_required
def dashboard_inventario(request):
    """
    Dashboard principal del módulo de Inventario.
    
    ESTADO: Stub - Módulo en desarrollo
    
    Esta es una vista de respaldo temporal que muestra un mensaje
    amigable indicando que el módulo está en construcción.
    """
    logger.info(f"Usuario {request.user.username} accedió al módulo de Inventario (Stub)")
    
    context = {
        'modulo_nombre': 'Inventario',
        'modulo_icono': 'fas fa-boxes',
        'mensaje_principal': 'Módulo de Inventario',
        'mensaje_secundario': 'Este módulo está siendo preparado para ti',
        'descripcion': '''
            El módulo de Inventario incluirá:
            • Control de stock de insumos médicos
            • Alertas de productos por vencer
            • Gestión de proveedores
            • Reportes de consumo
            • Integración con compras
        ''',
        'fecha_estimada': 'Próximamente',
    }
    
    return render(request, 'general/construccion.html', context)


@login_required
def lista_productos(request):
    """
    Lista de productos del inventario.
    
    ESTADO: Stub
    """
    logger.info(f"Usuario {request.user.username} accedió a lista de productos (Stub)")
    
    messages.info(request, 'El módulo de Inventario está en desarrollo.')
    
    context = {
        'modulo_nombre': 'Gestión de Productos',
        'modulo_icono': 'fas fa-box-open',
        'mensaje_principal': 'Gestión de Productos',
        'mensaje_secundario': 'Funcionalidad en desarrollo',
    }
    
    return render(request, 'general/construccion.html', context)


@login_required
def movimientos_inventario(request):
    """
    Registro de movimientos de inventario.
    
    ESTADO: Stub
    """
    logger.info(f"Usuario {request.user.username} accedió a movimientos de inventario (Stub)")
    
    messages.info(request, 'El módulo de Movimientos está en desarrollo.')
    
    context = {
        'modulo_nombre': 'Movimientos de Inventario',
        'modulo_icono': 'fas fa-exchange-alt',
        'mensaje_principal': 'Movimientos de Inventario',
        'mensaje_secundario': 'Funcionalidad en desarrollo',
    }
    
    return render(request, 'general/construccion.html', context)


@login_required
def alertas_inventario(request):
    """
    Alertas de inventario (stock bajo, productos por vencer).
    
    ESTADO: Stub
    """
    logger.info(f"Usuario {request.user.username} accedió a alertas de inventario (Stub)")
    
    messages.warning(request, 'El módulo de Alertas está en desarrollo.')
    
    context = {
        'modulo_nombre': 'Alertas de Inventario',
        'modulo_icono': 'fas fa-exclamation-triangle',
        'mensaje_principal': 'Alertas de Inventario',
        'mensaje_secundario': 'Funcionalidad en desarrollo',
    }
    
    return render(request, 'general/construccion.html', context)
