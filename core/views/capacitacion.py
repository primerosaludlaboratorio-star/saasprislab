"""
Módulo de Capacitación del Personal.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from core.models import Empresa, Usuario


@login_required
def capacitacion_personal(request):
    """Dashboard de capacitación para personal."""
    empresa = getattr(request.user, 'empresa', None)
    
    # Lista de empleados
    empleados = Usuario.objects.filter(empresa=empresa, is_active=True).order_by('first_name', 'last_name')
    
    # Búsqueda
    busqueda = request.GET.get('busqueda', '').strip()
    if busqueda:
        empleados = empleados.filter(
            Q(first_name__icontains=busqueda) |
            Q(last_name__icontains=busqueda) |
            Q(username__icontains=busqueda)
        )
    
    return render(request, 'core/capacitacion/personal.html', {
        'empleados': empleados,
        'busqueda': busqueda
    })


@login_required
def capacitacion_ejecutiva(request):
    """Módulo exclusivo de capacitación ejecutiva para el dueño."""
    # Solo accesible para superusuarios o usuarios con rol ADMIN
    if not (request.user.is_superuser or request.user.rol == 'ADMIN'):
        messages.error(request, 'Acceso restringido. Solo disponible para administradores.')
        return redirect('home')
    
    empresa = getattr(request.user, 'empresa', None)
    
    return render(request, 'core/capacitacion/ejecutiva.html', {
        'empresa': empresa
    })
