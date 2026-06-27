from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.models import OrdenDeServicio, Paciente
from marketing.models import CampanaMarketing, CuponMarketing


# Segmentos y canales disponibles para campañas.
_SEGMENTOS = ['Todos', 'Diabéticos', 'Hipertensos', 'Pediatría', 'Adultos Mayores', 'VIP']
_CANALES = ['whatsapp', 'email', 'sms']


@login_required
def lista_campanas(request):
    """Lista de todas las campañas de marketing."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    estado = request.GET.get('estado', 'todas')
    tipo = request.GET.get('tipo', 'todos')

    campanas = CampanaMarketing.objects.filter(empresa=empresa)

    if estado == 'activas':
        campanas = campanas.filter(activa=True)
    elif estado == 'inactivas':
        campanas = campanas.filter(activa=False)

    if tipo != 'todos':
        campanas = campanas.filter(segmento=tipo)

    campanas = campanas.order_by('-fecha_creacion')[:100]

    return render(request, "marketing/campanas/lista.html", {
        "campanas": campanas,
        "empresa": empresa,
        "filtro_estado": estado,
        "filtro_tipo": tipo,
    })


@login_required
def crear_campana(request):
    """Crear nueva campaña de marketing."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        segmento = request.POST.get('segmento', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        canal = request.POST.get('canal', 'whatsapp')

        if not nombre or not segmento or not mensaje:
            messages.error(request, 'Nombre, segmento y mensaje son obligatorios.')
        else:
            campana = CampanaMarketing.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, "sucursal", None),
                nombre=nombre,
                segmento=segmento,
                mensaje_whatsapp=mensaje,
                canal_comunicacion=canal,
                creado_por=request.user,
                activa=True,
            )
            messages.success(request, f'Campaña "{campana.nombre}" creada exitosamente.')
            return redirect('marketing:lista_campanas')

    return render(request, "marketing/campanas/crear.html", {
        "empresa": empresa,
        "segmentos": _SEGMENTOS,
        "canales": _CANALES,
    })


@login_required
def editar_campana(request, campana_id):
    """Editar una campaña de marketing existente."""
    empresa = getattr(request.user, "empresa", None)
    campana = get_object_or_404(CampanaMarketing, id=campana_id, empresa=empresa)

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        segmento = request.POST.get('segmento', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        canal = request.POST.get('canal', campana.canal_comunicacion)

        if not nombre or not segmento or not mensaje:
            messages.error(request, 'Nombre, segmento y mensaje son obligatorios.')
        else:
            campana.nombre = nombre
            campana.segmento = segmento
            campana.mensaje_whatsapp = mensaje
            campana.canal_comunicacion = canal
            campana.activa = request.POST.get('activa') == 'on'
            campana.save(update_fields=['nombre', 'segmento', 'mensaje_whatsapp', 'canal_comunicacion', 'activa'])
            messages.success(request, f'Campaña "{campana.nombre}" actualizada exitosamente.')
            return redirect('marketing:lista_campanas')

    return render(request, "marketing/campanas/crear.html", {
        "empresa": empresa,
        "campana": campana,
        "segmentos": _SEGMENTOS,
        "canales": _CANALES,
        "editar": True,
    })


@login_required
def dashboard_campanas(request):
    """Dashboard con métricas de campañas."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    campanas = CampanaMarketing.objects.filter(empresa=empresa).order_by('-fecha_creacion')[:10]

    total_campanas = CampanaMarketing.objects.filter(empresa=empresa).count()
    campanas_activas = CampanaMarketing.objects.filter(empresa=empresa, activa=True).count()

    campanas_data = []
    for c in campanas:
        segmento = c.segmento or ''
        segmento_fragmento = segmento[:20]

        enviados = CuponMarketing.objects.filter(
            empresa=empresa,
            descripcion__icontains=segmento_fragmento,
        ).count() if segmento else 0

        abiertos = CuponMarketing.objects.filter(
            empresa=empresa,
            descripcion__icontains=segmento_fragmento,
            paciente__isnull=False,
        ).count() if segmento else 0

        ventana_fin = c.fecha_creacion + timedelta(days=7)
        conversiones = OrdenDeServicio.objects.filter(
            empresa=empresa,
            fecha_creacion__gte=c.fecha_creacion,
            fecha_creacion__lte=ventana_fin,
        ).values('paciente_id').distinct().count()

        campanas_data.append({
            'nombre': c.nombre or segmento,
            'canal': c.canal_comunicacion,
            'enviados': enviados,
            'abiertos': abiertos,
            'conversiones': conversiones,
            'fecha': c.fecha_creacion.strftime('%d/%m/%Y'),
        })

    return render(request, "marketing/campanas/dashboard.html", {
        "campanas": campanas,
        "empresa": empresa,
        "total_campanas": total_campanas,
        "campanas_activas": campanas_activas,
        "campanas_data": campanas_data,
    })


@login_required
@require_http_methods(["POST"])
def api_crear_campana(request):
    """API para crear campaña de marketing."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        return JsonResponse({"ok": False, "error": "Usuario sin empresa asignada."}, status=403)

    sucursal = getattr(request.user, "sucursal", None)
    segmento = (request.POST.get("segmento") or "").strip()
    mensaje = (request.POST.get("mensaje") or "").strip()

    if not segmento or not mensaje:
        return JsonResponse({"ok": False, "error": "Segmento y mensaje son obligatorios."}, status=400)

    c = CampanaMarketing.objects.create(
        empresa=empresa,
        sucursal=sucursal,
        segmento=segmento,
        mensaje_whatsapp=mensaje,
        creado_por=request.user,
    )
    return JsonResponse({"ok": True, "id": c.id})
