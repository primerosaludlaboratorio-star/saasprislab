from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import PlanSaaS, SuscripcionTenant


def lista_planes(request):
    """Vista pública de planes de suscripción disponibles."""
    planes = PlanSaaS.objects.all().order_by('precio_mensual')
    return render(request, 'suscripciones/planes.html', {'planes': planes})


@login_required
def lista_suscripciones(request):
    """Vista de suscripciones activas (requiere login de staff)."""
    if not request.user.is_staff:
        return redirect('/admin/suscripciones/suscripciontenant/')
    suscripciones = SuscripcionTenant.objects.select_related('empresa', 'plan').order_by('-fecha_inicio')
    return render(request, 'suscripciones/lista.html', {'suscripciones': suscripciones})
