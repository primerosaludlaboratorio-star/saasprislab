"""Endpoints para leer facturas/notas y preparar una compra revisable."""

import base64
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Producto
from core.services.ocr_documental import analizar_compra_farmacia
from farmacia.models import LecturaCompraFarmacia
from farmacia.services.compra_ocr import conciliar_compra
from farmacia.views.pdv import _empresa_desde_request, _verificar_acceso


def _data_url(archivo):
    archivo.seek(0)
    contenido = archivo.read()
    archivo.seek(0)
    return f"data:{archivo.content_type};base64,{base64.b64encode(contenido).decode('ascii')}"


def _acceso(request):
    return _empresa_desde_request(request), _verificar_acceso(
        request.user, ["FARMACIA", "ADMIN", "ADMINISTRADOR", "GERENTE"]
    )


@login_required
@require_POST
def api_analizar_compra(request):
    empresa, permitido = _acceso(request)
    if not empresa or not permitido:
        return JsonResponse({"ok": False, "error": "Sin permisos para inventario de Farmacia."}, status=403)
    archivo = request.FILES.get("documento_compra")
    if not archivo:
        return JsonResponse({"ok": False, "error": "Adjunte una foto de factura o nota de venta."}, status=400)
    lectura = LecturaCompraFarmacia.objects_all.create(empresa=empresa, usuario=request.user, imagen=archivo)
    resultado = analizar_compra_farmacia(_data_url(archivo), empresa, request.user)
    if resultado.get("error") or not resultado.get("activo", True):
        lectura.estado = "ERROR"
        lectura.error = resultado.get("error") or resultado.get("mensaje") or "No fue posible procesar el documento."
        lectura.save(update_fields=["estado", "error"])
        return JsonResponse({"ok": False, "lectura_id": lectura.id, "error": lectura.error}, status=422)
    datos = resultado.get("datos_extraidos") or {}
    lectura.texto_extraido = resultado.get("texto_extraido", "")
    lectura.datos_extraidos = datos
    lectura.sugerencias = conciliar_compra(empresa, datos)
    lectura.confianza = Decimal(str(resultado.get("confianza") or 0))
    lectura.save(update_fields=["texto_extraido", "datos_extraidos", "sugerencias", "confianza"])
    return JsonResponse({
        "ok": True,
        "lectura_id": lectura.id,
        "datos": datos,
        "sugerencias": lectura.sugerencias,
        "requiere_revision_humana": True,
    })


@login_required
@require_POST
def api_confirmar_compra(request):
    empresa, permitido = _acceso(request)
    if not empresa or not permitido:
        return JsonResponse({"ok": False, "error": "Sin permisos para inventario de Farmacia."}, status=403)
    try:
        payload = json.loads(request.body or "{}")
        lectura = LecturaCompraFarmacia.objects_all.get(pk=payload.get("lectura_id"), empresa=empresa)
        proveedor = str(payload.get("proveedor") or "").strip()
        documento = str(payload.get("documento_compra") or "").strip()
        fecha_compra = str(payload.get("fecha_compra") or "").strip()
        items = payload.get("items") or []
    except (ValueError, TypeError, LecturaCompraFarmacia.DoesNotExist):
        return JsonResponse({"ok": False, "error": "Lectura o datos inválidos."}, status=400)
    if not proveedor or not documento or not fecha_compra or not items:
        return JsonResponse({"ok": False, "error": "Confirme proveedor, folio, fecha y al menos una línea."}, status=400)
    try:
        datetime.strptime(fecha_compra, "%Y-%m-%d")
    except ValueError:
        return JsonResponse({"ok": False, "error": "La fecha de compra no es válida."}, status=400)
    ids = {int(item.get("producto_id")) for item in items if str(item.get("producto_id", "")).isdigit()}
    productos = {p.id: p for p in Producto.objects_all.filter(empresa=empresa, id__in=ids)}
    confirmados = []
    for item in items:
        producto = productos.get(int(item.get("producto_id"))) if str(item.get("producto_id", "")).isdigit() else None
        if not producto:
            return JsonResponse({"ok": False, "error": "Producto fuera del catálogo de la empresa."}, status=400)
        try:
            cantidad = Decimal(str(item.get("cantidad")))
            costo = Decimal(str(item.get("costo_unitario")))
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "Cantidad o costo inválido."}, status=400)
        lote = str(item.get("numero_lote") or "").strip().upper()
        caducidad = str(item.get("fecha_caducidad") or "").strip()
        if cantidad <= 0 or costo <= 0 or not lote or not caducidad:
            return JsonResponse({"ok": False, "error": f"Complete cantidad, costo, lote y caducidad para {producto.nombre}."}, status=400)
        try:
            datetime.strptime(caducidad, "%Y-%m-%d")
        except ValueError:
            return JsonResponse({"ok": False, "error": f"Caducidad inválida para {producto.nombre}."}, status=400)
        confirmados.append({
            "producto_id": producto.id, "producto_nombre": producto.nombre,
            "cantidad": str(cantidad), "costo_unitario": str(costo),
            "subtotal": str(cantidad * costo),
            "numero_lote": lote, "fecha_caducidad": caducidad,
            "marca": str(item.get("marca") or producto.marca_laboratorio or "GENERICO").strip(),
        })
    # La confirmación solo prepara la compra existente en sesión. El Kardex se genera
    # únicamente cuando el usuario revisa y guarda la compra completa.
    request.session["items_compra_temp"] = confirmados
    request.session["items_compra_ocr"] = {
        "lectura_id": lectura.id, "proveedor_texto": proveedor,
        "documento_compra": documento, "fecha_compra": fecha_compra,
    }
    request.session.modified = True
    lectura.items_confirmados = confirmados
    lectura.estado = "CONFIRMADA"
    lectura.confirmado_en = timezone.now()
    lectura.confirmado_por = request.user
    lectura.save(update_fields=["items_confirmados", "estado", "confirmado_en", "confirmado_por"])
    return JsonResponse({"ok": True, "redirect": reverse("farmacia:registrar_compra"), "mensaje": "Compra preparada para revisión final. Todavía no se modificó el inventario."})
