from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Plan, Suscripcion


def lista_planes(request):
    """Vista pública de planes de suscripción disponibles."""
    planes = Plan.objects.filter(activo=True).order_by('precio_mensual')
    return render(request, 'suscripciones/planes.html', {'planes': planes})


@login_required
def lista_suscripciones(request):
    """Vista de suscripciones activas (requiere login de admin)."""
    from django.contrib.admin.views.decorators import staff_member_required
    if not request.user.is_staff:
        return redirect('/admin/suscripciones/')
    suscripciones = Suscripcion.objects.select_related('empresa', 'plan').order_by('-fecha_inicio')
    return render(request, 'suscripciones/lista.html', {'suscripciones': suscripciones})
