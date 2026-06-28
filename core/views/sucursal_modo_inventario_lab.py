"""
Modo ágil v1.49 — interruptor de gestión de inventario (FEFO lab) por sucursal, UI staff.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.models import Sucursal


def _acceso_director_o_admin(user):
    if user.is_superuser or user.is_staff:
        return True
    rol = (getattr(user, 'rol', '') or '').upper().strip()
    if rol in ('ADMIN', 'ADMINISTRADOR', 'GERENTE', 'DIRECTOR'):
        return True
    return user.groups.filter(name__in=['GERENCIA', 'GERENCIA_OPERATIVA', 'DIRECTOR']).exists()


@login_required
def sucursales_modo_inventario_lab(request):
    """
    Lista sucursales de la empresa y permite activar/desactivar
    gestion_inventario_activa (bypass FEFO al validar resultados de laboratorio).
    """
    if not _acceso_director_o_admin(request.user):
        messages.warning(request, 'No tienes permisos para acceder a esta configuración.')
        return redirect('home')

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')

    if request.method == 'POST':
        for s in Sucursal.objects.filter(empresa=empresa):
            on = request.POST.get(f'gestion_{s.pk}') == 'on'
            if s.gestion_inventario_activa != on:
                s.gestion_inventario_activa = on
                s.save(update_fields=['gestion_inventario_activa'])
        messages.success(request, 'Configuración de inventario por sucursal guardada.')
        return redirect('sucursales_modo_inventario_lab')

    sucursales = Sucursal.objects.filter(empresa=empresa).order_by('nombre')
    return render(
        request,
        'core/sucursales_modo_inventario_lab.html',
        {'sucursales': sucursales, 'empresa': empresa},
    )
