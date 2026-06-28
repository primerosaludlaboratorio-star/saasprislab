from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from core.models import OrdenDeServicio, Paciente
from marketing.models import CampanaMarketing, CuponMarketing, CuponUso
from marketing.utils import generar_codigo_cupon, generar_cupon_imagen_jpg

logger = logging.getLogger("marketing.cupones")


@login_required
@require_http_methods(["POST"])
def api_generar_cupon(request):
    """Genera un cupón de descuento vía API."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        return JsonResponse({"ok": False, "error": "Usuario sin empresa asignada."}, status=403)

    sucursal = getattr(request.user, "sucursal", None)
    paciente_id = request.POST.get("paciente_id")
    porcentaje = (request.POST.get("porcentaje") or "0").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()

    try:
        porcentaje_dec = Decimal(porcentaje)
    except InvalidOperation:
        porcentaje_dec = Decimal("0.00")

    paciente = None
    if paciente_id:
        paciente = Paciente.objects.filter(id=paciente_id, empresa=empresa).first()

    codigo = generar_codigo_cupon()
    payload = f"PRISVALLE|EMPRESA:{getattr(empresa, 'id', 'NA')}|CUPON:{codigo}|PCT:{porcentaje_dec}"

    ruta_rel = generar_cupon_imagen_jpg(
        empresa_nombre=getattr(empresa, "nombre", "PRISLAB"),
        paciente_nombre=getattr(paciente, "nombre_completo", "") if paciente else "",
        payload_qr=payload,
    )

    cupon = CuponMarketing.objects.create(
        empresa=empresa,
        sucursal=sucursal,
        paciente=paciente,
        codigo=codigo,
        porcentaje_descuento=porcentaje_dec,
        descripcion=descripcion or None,
        creado_por=request.user,
        imagen=ruta_rel,
    )

    return JsonResponse(
        {"ok": True, "codigo": cupon.codigo, "imagen": cupon.imagen.url if cupon.imagen else None}
    )


@login_required
@require_http_methods(["POST"])
def api_aplicar_cupon(request):
    """
    Registra uso de cupón (paciente + orden). Mitiga dobles clics vía Idempotency-Key.
    El PDV con venta registra el uso en farmacia.services.venta_farmacia_service (misma clave).
    """
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        return JsonResponse({"status": "error", "mensaje": "Sin empresa"}, status=403)

    idem = (request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY") or "").strip()
    if len(idem) < 8:
        return JsonResponse(
            {
                "status": "error",
                "mensaje": "Encabezado Idempotency-Key es obligatorio (mínimo 8 caracteres).",
            },
            status=400,
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "mensaje": "JSON inválido"}, status=400)

    codigo = (data.get("codigo") or "").strip().upper()
    paciente_id = data.get("paciente_id")
    orden_id = data.get("orden_id")

    if not codigo:
        return JsonResponse({"status": "error", "mensaje": "código de cupón requerido"}, status=400)

    existente = CuponUso.objects.filter(idempotency_key=idem[:128]).first()
    if existente:
        return JsonResponse(
            {
                "status": "success",
                "reintento": True,
                "cupon_uso_id": existente.id,
                "cupon_id": existente.cupon_id,
            }
        )

    cupon = CuponMarketing.objects.filter(empresa=empresa, codigo=codigo).first()
    if not cupon:
        return JsonResponse({"status": "error", "mensaje": "Cupón no encontrado"}, status=404)

    paciente = None
    if paciente_id:
        paciente = Paciente.objects.filter(id=paciente_id, empresa=empresa).first()
        if not paciente:
            return JsonResponse({"status": "error", "mensaje": "Paciente inválido"}, status=400)

    if not orden_id:
        return JsonResponse(
            {"status": "error", "mensaje": "orden_id es obligatorio para este endpoint."},
            status=400,
        )

    orden = OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa).first()
    if not orden:
        return JsonResponse({"status": "error", "mensaje": "Orden inválida"}, status=400)

    if paciente and orden.paciente_id != paciente.id:
        return JsonResponse(
            {"status": "error", "mensaje": "La orden no corresponde al paciente"},
            status=400,
        )
    if not paciente:
        paciente = orden.paciente

    try:
        with transaction.atomic():
            uso = CuponUso.objects.create(
                empresa=empresa,
                cupon=cupon,
                paciente=paciente,
                orden=orden,
                venta=None,
                idempotency_key=idem[:128],
            )
    except IntegrityError:
        prev = CuponUso.objects.filter(idempotency_key=idem[:128]).first()
        if prev:
            return JsonResponse(
                {
                    "status": "success",
                    "reintento": True,
                    "cupon_uso_id": prev.id,
                    "cupon_id": prev.cupon_id,
                }
            )
        return JsonResponse(
            {"status": "error", "mensaje": "Cupón ya aplicado a esta orden o paciente"},
            status=409,
        )

    return JsonResponse(
        {
            "status": "success",
            "cupon_uso_id": uso.id,
            "codigo": cupon.codigo,
            "porcentaje_descuento": float(cupon.porcentaje_descuento),
        }
    )


@login_required
def lista_cupones(request):
    """Lista de todos los cupones."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    estado = request.GET.get('estado', 'todos')
    cupones = CuponMarketing.objects.filter(empresa=empresa)

    if estado == 'activos':
        cupones = cupones.filter(usos__isnull=True)
    elif estado == 'usados':
        cupones = cupones.filter(usos__isnull=False).distinct()

    cupones = cupones.order_by('-fecha_creacion')[:100]

    return render(request, "marketing/cupones/lista.html", {
        "cupones": cupones,
        "empresa": empresa,
        "filtro_estado": estado,
    })


@login_required
def generar_cupon(request):
    """Generar nuevo cupón de descuento."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    if request.method == 'POST':
        paciente_id = request.POST.get('paciente_id')
        porcentaje = request.POST.get('porcentaje', '0').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        try:
            cantidad = int(request.POST.get('cantidad', 1))
            if cantidad < 1 or cantidad > 1000:
                raise ValueError("Cantidad fuera de rango")
        except ValueError:
            messages.error(request, 'Cantidad debe ser un número entre 1 y 1000.')
            return redirect('marketing:generar_cupon')

        try:
            porcentaje_dec = Decimal(str(porcentaje))
            if porcentaje_dec <= 0 or porcentaje_dec > 100:
                raise ValueError("Porcentaje inválido")
        except (InvalidOperation, ValueError):
            messages.error(request, 'Porcentaje debe ser entre 1 y 100.')
            return redirect('marketing:generar_cupon')

        for _ in range(cantidad):
            paciente = None
            if paciente_id:
                paciente = Paciente.objects.filter(id=paciente_id, empresa=empresa).first()

            codigo = generar_codigo_cupon()
            payload = f"PRISVALLE|EMPRESA:{empresa.id}|CUPON:{codigo}|PCT:{porcentaje_dec}"

            ruta_rel = generar_cupon_imagen_jpg(
                empresa_nombre=empresa.nombre,
                paciente_nombre=paciente.nombre_completo if paciente else "",
                payload_qr=payload,
            )

            CuponMarketing.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, "sucursal", None),
                paciente=paciente,
                codigo=codigo,
                porcentaje_descuento=porcentaje_dec,
                descripcion=descripcion or None,
                creado_por=request.user,
                imagen=ruta_rel,
            )

        messages.success(request, f'{cantidad} cupón(es) generado(s) exitosamente.')
        return redirect('marketing:lista_cupones')

    pacientes = Paciente.objects.filter(empresa=empresa).order_by('nombre_completo')[:200]
    return render(request, "marketing/cupones/generar.html", {
        "empresa": empresa,
        "pacientes": pacientes,
    })
