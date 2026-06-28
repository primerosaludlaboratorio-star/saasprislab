"""
INVENTARIO V8.2 — Motor de Compras
OrdenDeCompra · LineaOrdenCompra · Recepción automática de mercancía → lotes
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q, Count, Sum, Value, DecimalField
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import date
from decimal import Decimal
import logging

from inventario.models import (
    OrdenDeCompra, LineaOrdenCompra, ProveedorCompras,
    CatalogoReactivoLab, LoteReactivoLab,
    CatalogoInsumoConsultorio, LoteInsumoConsultorio,
    CatalogoInsumoGeneral, LoteInsumoGeneral,
)
from .helpers import _empresa_required

logger = logging.getLogger(__name__)

# ContentType lookups por silo
SILO_CT_MAP = {
    'LAB':         ('inventario', 'catalogoreactivolab'),
    'CONSULTORIO': ('inventario', 'catalogoinsumoconsultorio'),
    'GENERAL':     ('inventario', 'catalogoinsumogeneral'),
}
SILO_LOTE_MODEL_MAP = {
    'LAB':         LoteReactivoLab,
    'CONSULTORIO': LoteInsumoConsultorio,
    'GENERAL':     LoteInsumoGeneral,
}
SILO_CAT_MODEL_MAP = {
    'LAB':         CatalogoReactivoLab,
    'CONSULTORIO': CatalogoInsumoConsultorio,
    'GENERAL':     CatalogoInsumoGeneral,
}


def _get_ct(silo):
    app, model = SILO_CT_MAP[silo]
    return ContentType.objects.get(app_label=app, model=model)


def _folio_oc(empresa):
    n = OrdenDeCompra.objects.filter(empresa=empresa).count() + 1
    return f"OC-{date.today().year}-{n:04d}"


# =============================================================================
# DASHBOARD / LISTA DE OCs
# =============================================================================

@_empresa_required
def lista_ordenes_compra(request, empresa):
    estado_f = request.GET.get('estado', '')
    qs = (
        OrdenDeCompra.objects
        .filter(empresa=empresa)
        .select_related('proveedor', 'generada_por', 'aprobada_por')
        .annotate(total_lineas=Count('lineas'))
        .order_by('-fecha_generacion')
    )
    if estado_f:
        qs = qs.filter(estado=estado_f)

    # Artículos con stock crítico (para sugerir OC automática)
    criticos_lab = (
        CatalogoReactivoLab.objects
        .filter(empresa=empresa, activo=True)
        .extra(where=["inventario_catalogoreactivolab.stock_minimo > 0"])[:5]
    )

    ctx = {
        'titulo': 'Motor de Compras — Órdenes de Compra',
        'ocs': qs[:80],
        'estado_f': estado_f,
        'estado_choices': OrdenDeCompra.ESTADO_CHOICES,
    }
    return render(request, 'inventario/compras/lista_ocs.html', ctx)


@_empresa_required
def crear_orden_compra(request, empresa):
    """Formulario multi-línea para crear una OC manual."""
    if request.method == 'POST':
        d = request.POST
        silos_linea    = request.POST.getlist('linea_silo')
        articulo_ids   = request.POST.getlist('linea_articulo_id')
        cantidades     = request.POST.getlist('linea_cantidad')
        precios        = request.POST.getlist('linea_precio')
        unidades       = request.POST.getlist('linea_unidad')
        descripciones  = request.POST.getlist('linea_descripcion')

        if not articulo_ids or not any(articulo_ids):
            messages.error(request, 'Debes agregar al menos una línea.')
        else:
            try:
                with transaction.atomic():
                    oc = OrdenDeCompra.objects.create(
                        empresa=empresa,
                        folio=_folio_oc(empresa),
                        proveedor_id=d['proveedor'],
                        estado='BORRADOR',
                        origen='MANUAL',
                        generada_por=request.user,
                        notas_director=d.get('notas_director', ''),
                    )
                    for i, art_id in enumerate(articulo_ids):
                        if not art_id:
                            continue
                        silo = silos_linea[i] if i < len(silos_linea) else 'LAB'
                        ct   = _get_ct(silo)
                        cant = float(cantidades[i] or 0)
                        precio = float(precios[i] or 0)
                        LineaOrdenCompra.objects.create(
                            empresa=empresa,
                            orden=oc,
                            silo=silo,
                            content_type=ct,
                            object_id=int(art_id),
                            descripcion_snapshot=descripciones[i] if i < len(descripciones) else '',
                            cantidad_solicitada=cant,
                            unidad_medida=unidades[i] if i < len(unidades) else '',
                            precio_unitario_estimado=precio,
                            subtotal=round(cant * precio, 4),
                        )
                    oc.recalcular_totales()
                messages.success(request, f'OC {oc.folio} creada en borrador.')
                return redirect('inventario:detalle_oc', pk=oc.pk)
            except (DatabaseError, ValidationError) as exc:
                logger.error("Error crear OC: %s", exc, exc_info=True)
                messages.error(request, f'Error: {exc}')

    proveedores = ProveedorCompras.objects.filter(empresa=empresa, activo=True).order_by('razon_social')
    # Artículos de los 3 silos para el selector dinámico
    reactivos    = CatalogoReactivoLab.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    insumos_con  = CatalogoInsumoConsultorio.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    insumos_gen  = CatalogoInsumoGeneral.objects.filter(empresa=empresa, activo=True).order_by('nombre')

    ctx = {
        'titulo': 'Nueva Orden de Compra',
        'proveedores': proveedores,
        'reactivos': reactivos,
        'insumos_con': insumos_con,
        'insumos_gen': insumos_gen,
    }
    return render(request, 'inventario/compras/form_oc.html', ctx)


@_empresa_required
def detalle_oc(request, empresa, pk):
    oc = get_object_or_404(OrdenDeCompra, pk=pk, empresa=empresa)
    lineas = oc.lineas.select_related('content_type').order_by('pk')

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'enviar_aprobacion' and oc.estado == 'BORRADOR':
            oc.estado = 'PENDIENTE_DIRECTOR'
            oc.save(update_fields=['estado'])
            messages.info(request, 'OC enviada al Director para aprobación.')

        elif accion == 'aprobar' and oc.estado == 'PENDIENTE_DIRECTOR':
            oc.estado = 'APROBADA'
            oc.aprobada_por = request.user
            oc.fecha_aprobacion = timezone.now()
            oc.save(update_fields=['estado', 'aprobada_por', 'fecha_aprobacion'])
            messages.success(request, f'OC {oc.folio} aprobada.')

        elif accion == 'marcar_enviada' and oc.estado == 'APROBADA':
            oc.estado = 'ENVIADA'
            oc.fecha_envio = timezone.now()
            oc.save(update_fields=['estado', 'fecha_envio'])
            messages.info(request, f'OC {oc.folio} marcada como enviada al proveedor.')

        elif accion == 'recibir_mercancia' and oc.estado in ('ENVIADA', 'PARCIALMENTE_RECIBIDA'):
            _recibir_mercancia(request, oc, empresa)
            return redirect('inventario:detalle_oc', pk=pk)

        elif accion == 'cancelar' and oc.estado not in ('COMPLETADA', 'CANCELADA'):
            oc.estado = 'CANCELADA'
            oc.notas_director = request.POST.get('razon_cancelacion', '')
            oc.save(update_fields=['estado', 'notas_director'])
            messages.warning(request, f'OC {oc.folio} cancelada.')

        return redirect('inventario:detalle_oc', pk=pk)

    ctx = {
        'titulo': f'Orden de Compra: {oc.folio}',
        'oc': oc,
        'lineas': lineas,
        'puede_recibir': oc.estado in ('ENVIADA', 'PARCIALMENTE_RECIBIDA'),
    }
    return render(request, 'inventario/compras/detalle_oc.html', ctx)


def _recibir_mercancia(request, oc, empresa):
    """
    Lógica de recepción de mercancía con firma obligatoria del receptor.
    Por cada línea recibida, crea automáticamente el Lote en el silo correspondiente.
    Si hay discrepancia entre pedido y recibido, genera NotificacionDiscrepancia al Director.
    """
    from ..models import NotificacionDiscrepancia
    from django.contrib.auth import authenticate

    d = request.POST

    # ── Verificación obligatoria del receptor (firma digital) ─────────────────
    receptor_username = d.get('receptor_username', '').strip()
    receptor_password = d.get('receptor_password', '').strip()
    if not receptor_username or not receptor_password:
        messages.error(request, 'Firma del receptor obligatoria: ingresa usuario y contraseña.')
        return
    receptor = authenticate(request, username=receptor_username, password=receptor_password)
    if not receptor:
        messages.error(request, 'Credenciales del receptor incorrectas. Recepción no registrada.')
        return

    errores = []
    discrepancias_texto = []
    lotes_creados = 0

    with transaction.atomic():
        for linea in oc.lineas.all():
            key_cant  = f'recibido_{linea.pk}_cantidad'
            key_lote  = f'recibido_{linea.pk}_numero_lote'
            key_cad   = f'recibido_{linea.pk}_caducidad'
            key_precio = f'recibido_{linea.pk}_precio_real'

            cantidad_rec = float(d.get(key_cant, 0) or 0)
            if cantidad_rec <= 0:
                continue

            precio_real = float(d.get(key_precio, 0) or linea.precio_unitario_estimado)
            numero_lote = d.get(key_lote, '').strip() or None
            caducidad   = d.get(key_cad, '') or None

            LoteModel = SILO_LOTE_MODEL_MAP[linea.silo]
            CatModel  = SILO_CAT_MODEL_MAP[linea.silo]

            try:
                catalogo_item = CatModel.objects.get(pk=linea.object_id, empresa=empresa)

                # Campos comunes para todos los modelos de lote
                # Detectar discrepancia entre pedido y recibido
                cant_pedida = float(linea.cantidad_solicitada) - float(linea.cantidad_recibida)
                if abs(cantidad_rec - cant_pedida) > 0.001 and cant_pedida > 0:
                    discrepancias_texto.append(
                        f'{linea.descripcion_snapshot}: '
                        f'pedido {cant_pedida:.2f}, recibido {cantidad_rec:.2f}'
                    )

                lote_data = {
                    'empresa': empresa,
                    'cantidad_inicial': cantidad_rec,
                    'cantidad_actual': cantidad_rec,
                    'precio_unitario_compra': precio_real,
                    'orden_compra': oc,
                    'recibido_por': receptor,
                }

                if linea.silo == 'LAB':
                    if not numero_lote:
                        errores.append(f'{linea.descripcion_snapshot}: número de lote requerido para LAB.')
                        continue
                    if not caducidad:
                        errores.append(f'{linea.descripcion_snapshot}: fecha de caducidad requerida para LAB.')
                        continue
                    lote_data.update({
                        'reactivo': catalogo_item,
                        'numero_lote': numero_lote,
                        'fecha_caducidad': caducidad,
                        'estado': 'CUARENTENA',
                    })
                elif linea.silo == 'CONSULTORIO':
                    lote_data.update({
                        'insumo': catalogo_item,
                        'numero_lote': numero_lote,
                        'fecha_caducidad': caducidad,
                    })
                elif linea.silo == 'GENERAL':
                    lote_data['insumo'] = catalogo_item

                LoteModel.objects.create(**lote_data)

                # Actualizar precio última compra en catálogo
                catalogo_item.precio_ultima_compra = precio_real
                catalogo_item.save(update_fields=['precio_ultima_compra'])

                # Actualizar cantidad recibida en la línea
                linea.cantidad_recibida = float(linea.cantidad_recibida) + cantidad_rec
                linea.precio_unitario_real = precio_real
                linea.subtotal = round(float(linea.cantidad_solicitada) * precio_real, 4)
                linea.save(update_fields=['cantidad_recibida', 'precio_unitario_real', 'subtotal'])
                lotes_creados += 1

            except (DatabaseError, ValidationError) as exc:
                errores.append(f'{linea.descripcion_snapshot}: {exc}')
                logger.error("Error recibir línea %s: %s", linea.pk, exc, exc_info=True)

        # Actualizar estado OC
        todas_recibidas = all(
            float(l.cantidad_recibida) >= float(l.cantidad_solicitada)
            for l in oc.lineas.all()
        )
        oc.estado = 'COMPLETADA' if todas_recibidas else 'PARCIALMENTE_RECIBIDA'
        if todas_recibidas:
            oc.fecha_cierre = timezone.now()
        oc.save(update_fields=['estado', 'fecha_cierre'])
        oc.recalcular_totales()

    # Generar NotificacionDiscrepancia si hubo diferencias
    if discrepancias_texto:
        try:
            NotificacionDiscrepancia.objects.create(
                empresa=empresa,
                tipo='OC_DISCREPANCIA',
                nivel='ADVERTENCIA' if lotes_creados > 0 else 'CRITICO',
                titulo=f'Discrepancia en recepción OC {oc.folio}',
                detalle='\n'.join(discrepancias_texto),
                oc=oc,
            )
        except (DatabaseError, ValidationError) as exc:
            logger.error("Error creando NotificacionDiscrepancia: %s", exc, exc_info=True)

    if errores:
        messages.warning(request, f'{lotes_creados} lotes creados. Errores: {"; ".join(errores)}')
    elif discrepancias_texto:
        messages.warning(
            request,
            f'✅ {lotes_creados} lotes creados. ⚠️ Discrepancias detectadas y notificadas al Director.'
        )
    else:
        messages.success(request, f'✅ {lotes_creados} lotes creados por {receptor.get_full_name() or receptor.username}.')


# =============================================================================
# PROVEEDOR CRUD (básico)
# =============================================================================

@_empresa_required
def lista_proveedores(request, empresa):
    qs = ProveedorCompras.objects.filter(empresa=empresa).order_by('razon_social')
    ctx = {'titulo': 'Proveedores de Compras', 'proveedores': qs}
    return render(request, 'inventario/compras/lista_proveedores.html', ctx)


@_empresa_required
def crear_proveedor(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            ProveedorCompras.objects.create(
                empresa=empresa,
                razon_social=d['razon_social'].strip(),
                rfc=d.get('rfc', '').strip() or '',
                contacto_nombre=d.get('contacto_nombre', ''),
                email=d.get('email', '') or d.get('contacto_email', ''),
                telefono=d.get('telefono', '') or d.get('contacto_telefono', ''),
                dias_credito=int(d.get('dias_credito', 0) or 0),
                notas=d.get('notas', ''),
            )
            messages.success(request, 'Proveedor creado.')
            return redirect('inventario:lista_proveedores')
        except (DatabaseError, ValidationError) as exc:
            messages.error(request, f'Error: {exc}')
    ctx = {'titulo': 'Nuevo Proveedor'}
    return render(request, 'inventario/compras/form_proveedor.html', ctx)


# =============================================================================
# API: artículos críticos para sugerir OC automática
# =============================================================================

@login_required
def api_articulos_criticos(request):
    from .helpers import _get_empresa
    empresa = _get_empresa(request)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa'}, status=403)

    criticos = []

    for Model, silo_key, nombre_campo in [
        (CatalogoReactivoLab, 'LAB', 'reactivo'),
        (CatalogoInsumoConsultorio, 'CONSULTORIO', 'insumo'),
        (CatalogoInsumoGeneral, 'GENERAL', 'insumo'),
    ]:
        items = (
            Model.objects
            .filter(empresa=empresa, activo=True, stock_minimo__gt=0)
            .annotate(
                stock_total=Coalesce(
                    Sum(f'lotes__cantidad_actual',
                        filter=Q(lotes__cantidad_actual__gt=0)),
                    Value(Decimal('0'), output_field=DecimalField())
                )
            )
        )
        for item in items:
            if float(item.stock_total) <= float(item.stock_minimo):
                criticos.append({
                    'silo': silo_key,
                    'id': item.pk,
                    'nombre': item.nombre,
                    'codigo': item.codigo_interno,
                    'stock': float(item.stock_total),
                    'minimo': float(item.stock_minimo),
                    'unidad': item.unidad_medida,
                    'precio_ultima_compra': float(item.precio_ultima_compra),
                })

    return JsonResponse({'criticos': criticos, 'total': len(criticos)})
