"""Puentes legacy hacia el inventario operativo V8."""

import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

logger = logging.getLogger('inventario')


@login_required
def dashboard_inventario(request):
    """Dashboard principal de inventario: usa el silo de laboratorio activo."""
    logger.info("Usuario %s accedio al puente legacy de Inventario", request.user.username)
    return redirect('inventario:dashboard_reactivos')


@login_required
def lista_productos(request):
    """Catalogo operativo de reactivos e insumos de laboratorio."""
    logger.info("Usuario %s accedio al puente legacy de productos", request.user.username)
    return redirect('inventario:lista_reactivos')


@login_required
def movimientos_inventario(request):
    """Movimientos reales de inventario: salidas tecnicas y consumo."""
    logger.info("Usuario %s accedio al puente legacy de movimientos", request.user.username)
    return redirect('inventario:lista_salidas_tecnicas')


@login_required
def alertas_inventario(request):
    """Alertas operativas de stock bajo y caducidades."""
    logger.info("Usuario %s accedio al puente legacy de alertas", request.user.username)
    return redirect('inventario:dashboard_reactivos')
