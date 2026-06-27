"""
INVENTARIO V8.3 — Vistas de Logística Inter-Sedes
TraspasoInventario: mueve stock entre sucursales con firma PIN del receptor.

Flujo:
  BORRADOR → EN_TRANSITO (despacha origen, stock sale) → RECIBIDO (PIN receptor, stock entra)
                                                        → RECHAZADO (stock regresa al origen)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import date
import logging

from inventario.models import (
    TraspasoInventario, LineaTraspasoInventario, NotificacionDiscrepancia,
    LoteReactivoLab, LoteInsumoConsultorio, LoteInsumoGeneral,
)
from .helpers import _empresa_required, _get_empresa
from core.models import Empresa

logger = logging.getLogger(__name__)

# Mapa silo → modelo de lote
LOTE_MODEL = {
    'LAB':         LoteReactivoLab,
    'CONSULTORIO': LoteInsumoConsultorio,
    'GENERAL':     LoteInsumoGeneral,
}

# Campo nombre en cada catálogo
def _nombre_articulo(lote, silo):
    if silo == 'LAB':
        return lote.reactivo.nombre
    return lote.insumo.nombre

def _numero_lote(lote, silo):
    if silo == 'LAB':
        return lote.numero_lote or 'S/L'
    return getattr(lote, 'numero_lote', None) or 'S/L'


def _folio_traspaso(empresa):
    n = TraspasoInventario.objects.filter(empresa_origen=empresa).count() + 1
    return f"TRP-{date.today().year}-{n:04d}"


# =============================================================================
# LISTA
# =============================================================================

@_empresa_required
def lista_traspasos(request, empresa):
    estado_f = request.GET.get('estado', '')
    direccion = request.GET.get('dir', 'enviados')

    if direccion == 'recibidos':
        qs = TraspasoInventario.objects.filter(empresa_destino=empresa)
    else:
        qs = TraspasoInventario.objects.filter(empresa_origen=empresa)

    if estado_f:
        qs = qs.filter(estado=estado_f)

    qs = qs.select_related('empresa_origen', 'empresa_destino',
                           'solicitado_por', 'receptor').order_by('-fecha_solicitud')[:100]

    # Contar pendientes de recepción para este usuario
    pendientes_recibir = TraspasoInventario.objects.filter(
        empresa_destino=empresa, estado='EN_TRANSITO'
    ).count()

    ctx = {
        'titulo': 'Traspasos de Inventario',
        'traspasos': qs,
        'estado_f': estado_f,
        'direccion': direccion,
        'estado_choices': TraspasoInventario.ESTADO_CHOICES,
        'pendientes_recibir': pendientes_recibir,
    }
    return render(request, 'inventario/traspasos/lista.html', ctx)


# =============================================================================
# CREAR TRASPASO
# =============================================================================

@_empresa_required
def crear_traspaso(request, empresa):
    silo = request.GET.get('silo', 'LAB')

    if request.method == 'POST':
        d = request.POST
        silo     = d.get('silo', 'LAB')
        lote_ids = request.POST.getlist('lote_id')
        cantidades = request.POST.getlist('cantidad_enviada')
        empresa_destino_id = d.get('empresa_destino')

        if not lote_ids:
            messages.error(request, 'Agrega al menos un lote.')
        elif empresa_destino_id == str(empresa.pk):
            messages.error(request, 'El destino no puede ser la misma empresa origen.')
        else:
            try:
                empresa_destino = Empresa.objects.get(pk=empresa_destino_id)
                LoteModel = LOTE_MODEL[silo]

                with transaction.atomic():
                    traspaso = TraspasoInventario.objects.create(
                        empresa_origen=empresa,
                        empresa_destino=empresa_destino,
                        silo=silo,
                        folio=_folio_traspaso(empresa),
                        estado='BORRADOR',
                        motivo=d.get('motivo', ''),
                        solicitado_por=request.user,
                        observaciones=d.get('observaciones', ''),
                    )
                    for i, lid in enumerate(lote_ids):
                        if not lid:
                            continue
                        lote = get_object_or_404(LoteModel, pk=lid, empresa=empresa)
                        cant = float(cantidades[i] or 0)
                        if cant <= 0:
                            continue
                        from django.contrib.contenttypes.models import ContentType
                        ct = ContentType.objects.get_for_model(LoteModel)
                        LineaTraspasoInventario.objects.create(
                            traspaso=traspaso,
                            empresa_origen=empresa,
                            silo=silo,
                            lote_content_type=ct,
                            lote_object_id=lote.pk,
                            nombre_articulo_snapshot=_nombre_articulo(lote, silo),
                            numero_lote_snapshot=_numero_lote(lote, silo),
                            cantidad_enviada=cant,
                        )
                messages.success(request, f'Traspaso {traspaso.folio} creado en borrador.')
                return redirect('inventario:detalle_traspaso', pk=traspaso.pk)
            except (DatabaseError, ValidationError) as exc:
                logger.error('Error crear traspaso: %s', exc, exc_info=True)
                messages.error(request, f'Error: {exc}')

    # Lotes disponibles del silo seleccionado
    LoteModel = LOTE_MODEL.get(silo, LoteReactivoLab)
    lotes = LoteModel.objects.filter(empresa=empresa, cantidad_actual__gt=0).order_by('pk')

    empresas_destino = Empresa.objects.exclude(pk=empresa.pk).order_by('nombre')
    ctx = {
        'titulo': 'Nuevo Traspaso de Inventario',
        'silo': silo,
        'silo_choices': TraspasoInventario.SILO_CHOICES,
        'lotes': lotes,
        'empresas_destino': empresas_destino,
    }
    return render(request, 'inventario/traspasos/form.html', ctx)


# =============================================================================
# DETALLE + ACCIONES (despachar, recibir PIN, rechazar, cancelar)
# =============================================================================

@_empresa_required
def detalle_traspaso(request, empresa, pk):
    # Permite ver si es origen o destino
    traspaso = TraspasoInventario.objects.filter(
        Q(empresa_origen=empresa) | Q(empresa_destino=empresa), pk=pk
    ).select_related('empresa_origen', 'empresa_destino',
                     'solicitado_por', 'despachado_por', 'receptor').first()

    if not traspaso:
        messages.error(request, 'Traspaso no encontrado o sin acceso.')
        return redirect('inventario:lista_traspasos')

    lineas = traspaso.lineas.all()
    es_origen  = (traspaso.empresa_origen_id == empresa.pk)
    es_destino = (traspaso.empresa_destino_id == empresa.pk)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # ── Despachar: stock sale de origen ──────────────────────────────────
        if accion == 'despachar' and es_origen and traspaso.estado == 'BORRADOR':
            _ejecutar_despacho(traspaso, request.user, lineas)
            return redirect('inventario:detalle_traspaso', pk=pk)

        # ── Recibir con PIN: stock entra en destino ──────────────────────────
        elif accion == 'recibir' and es_destino and traspaso.estado == 'EN_TRANSITO':
            pin = request.POST.get('pin_receptor', '')
            usuario_autenticado = authenticate(
                request,
                username=request.user.username,
                password=pin,
            )
            if not usuario_autenticado:
                messages.error(request, '🔐 PIN incorrecto. No se confirmó la recepción.')
            else:
                _ejecutar_recepcion(traspaso, request.user, lineas, request.POST)
            return redirect('inventario:detalle_traspaso', pk=pk)

        # ── Rechazar: stock regresa a origen ─────────────────────────────────
        elif accion == 'rechazar' and es_destino and traspaso.estado == 'EN_TRANSITO':
            razon = request.POST.get('razon_rechazo', 'Sin motivo especificado')
            _ejecutar_rechazo(traspaso, razon, request.user, lineas)
            return redirect('inventario:detalle_traspaso', pk=pk)

        # ── Cancelar (solo origen, solo BORRADOR) ────────────────────────────
        elif accion == 'cancelar' and es_origen and traspaso.estado == 'BORRADOR':
            traspaso.estado = 'CANCELADO'
            traspaso.save(update_fields=['estado'])
            messages.warning(request, f'Traspaso {traspaso.folio} cancelado.')
            return redirect('inventario:lista_traspasos')

    ctx = {
        'titulo': f'Traspaso {traspaso.folio}',
        'traspaso': traspaso,
        'lineas': lineas,
        'es_origen': es_origen,
        'es_destino': es_destino,
    }
    return render(request, 'inventario/traspasos/detalle.html', ctx)


# =============================================================================
# LÓGICA DE NEGOCIO (separada para claridad)
# =============================================================================

def _ejecutar_despacho(traspaso, usuario, lineas):
    """
    Cambia estado a EN_TRANSITO y descuenta stock del silo origen.
    Usa select_for_update() para evitar condiciones de carrera.
    """
    LoteModel = LOTE_MODEL[traspaso.silo]
    errores = []

    with transaction.atomic():
        for linea in lineas:
            lote = LoteModel.objects.select_for_update().filter(
                pk=linea.lote_object_id, empresa=traspaso.empresa_origen
            ).first()
            if not lote:
                errores.append(f'Lote #{linea.lote_object_id} no encontrado.')
                continue
            if float(lote.cantidad_actual) < float(linea.cantidad_enviada):
                errores.append(
                    f'{linea.nombre_articulo_snapshot}: stock insuficiente '
                    f'(disponible: {lote.cantidad_actual}).'
                )
                continue
            lote.cantidad_actual = float(lote.cantidad_actual) - float(linea.cantidad_enviada)
            lote.save(update_fields=['cantidad_actual'])

        if errores:
            raise ValidationError(' | '.join(errores))

        traspaso.estado = 'EN_TRANSITO'
        traspaso.despachado_por = usuario
        traspaso.fecha_despacho = timezone.now()
        traspaso.save(update_fields=['estado', 'despachado_por', 'fecha_despacho'])

    logger.info('TRASPASO %s despachado por %s', traspaso.folio, usuario)


def _ejecutar_recepcion(traspaso, usuario, lineas, post_data):
    """
    Confirma recepción con PIN. Crea nuevos lotes en el silo destino.
    Si hay discrepancia, genera NotificacionDiscrepancia al Director.
    """
    LoteModel = LOTE_MODEL[traspaso.silo]
    discrepancias = []

    with transaction.atomic():
        for linea in lineas:
            key = f'recibido_{linea.pk}'
            cant_recibida = float(post_data.get(key, linea.cantidad_enviada) or linea.cantidad_enviada)
            linea.cantidad_recibida = cant_recibida
            linea.save(update_fields=['cantidad_recibida'])

            # Crear lote en destino
            lote_origen = LoteModel.objects.filter(pk=linea.lote_object_id).first()
            lote_data = {
                'empresa': traspaso.empresa_destino,
                'cantidad_inicial': cant_recibida,
                'cantidad_actual': cant_recibida,
                'precio_unitario_compra': getattr(lote_origen, 'precio_unitario_compra', 0) if lote_origen else 0,
                'recibido_por': usuario,
            }
            if traspaso.silo == 'LAB' and lote_origen:
                lote_data.update({
                    'reactivo': lote_origen.reactivo,
                    'numero_lote': lote_origen.numero_lote,
                    'fecha_caducidad': lote_origen.fecha_caducidad,
                    'estado': 'ACTIVO',
                })
            elif traspaso.silo == 'CONSULTORIO' and lote_origen:
                lote_data.update({
                    'insumo': lote_origen.insumo,
                    'numero_lote': getattr(lote_origen, 'numero_lote', None),
                    'fecha_caducidad': getattr(lote_origen, 'fecha_caducidad', None),
                })
            elif traspaso.silo == 'GENERAL' and lote_origen:
                lote_data['insumo'] = lote_origen.insumo

            LoteModel.objects.create(**lote_data)

            # Detectar discrepancia
            if abs(cant_recibida - float(linea.cantidad_enviada)) > 0.001:
                discrepancias.append({
                    'articulo': linea.nombre_articulo_snapshot,
                    'enviado': float(linea.cantidad_enviada),
                    'recibido': cant_recibida,
                    'diferencia': cant_recibida - float(linea.cantidad_enviada),
                })

        traspaso.estado = 'RECIBIDO'
        traspaso.receptor = usuario
        traspaso.fecha_recepcion = timezone.now()
        traspaso.save(update_fields=['estado', 'receptor', 'fecha_recepcion'])

        # Generar notificación si hay discrepancias
        if discrepancias:
            detalle_lines = [
                f"  • {d['articulo']}: enviado {d['enviado']}, recibido {d['recibido']} "
                f"(diferencia: {d['diferencia']:+.2f})"
                for d in discrepancias
            ]
            NotificacionDiscrepancia.objects.create(
                empresa=traspaso.empresa_destino,
                tipo='TRASPASO_DISCREPANCIA',
                nivel='ADVERTENCIA',
                titulo=f'Discrepancia en traspaso {traspaso.folio}',
                detalle=(
                    f'Traspaso: {traspaso.folio}\n'
                    f'Origen: {traspaso.empresa_origen}\n'
                    f'Receptor: {usuario}\n\n'
                    'Diferencias encontradas:\n' + '\n'.join(detalle_lines)
                ),
                traspaso=traspaso,
            )
            logger.warning('TRASPASO %s recibido con %d discrepancias.',
                           traspaso.folio, len(discrepancias))

    logger.info('TRASPASO %s confirmado por %s (PIN verificado)', traspaso.folio, usuario)


def _ejecutar_rechazo(traspaso, razon, usuario, lineas):
    """
    Rechaza el traspaso y regresa el stock al silo origen.
    """
    LoteModel = LOTE_MODEL[traspaso.silo]

    with transaction.atomic():
        for linea in lineas:
            lote = LoteModel.objects.select_for_update().filter(
                pk=linea.lote_object_id
            ).first()
            if lote:
                lote.cantidad_actual = float(lote.cantidad_actual) + float(linea.cantidad_enviada)
                lote.save(update_fields=['cantidad_actual'])

        traspaso.estado = 'RECHAZADO'
        traspaso.razon_rechazo = razon
        traspaso.receptor = usuario
        traspaso.save(update_fields=['estado', 'razon_rechazo', 'receptor'])

    logger.info('TRASPASO %s RECHAZADO por %s. Razón: %s', traspaso.folio, usuario, razon)


# =============================================================================
# NOTIFICACIONES DIRECTOR
# =============================================================================

@_empresa_required
def lista_notificaciones(request, empresa):
    qs = (
        NotificacionDiscrepancia.objects
        .filter(empresa=empresa)
        .select_related('resuelta_por', 'oc', 'traspaso')
        .order_by('-generada_en')[:100]
    )
    pendientes = qs.filter(resuelta=False).count()
    ctx = {
        'titulo': 'Notificaciones de Discrepancia',
        'notificaciones': qs,
        'pendientes': pendientes,
    }
    return render(request, 'inventario/traspasos/notificaciones.html', ctx)


@_empresa_required
@require_POST
def resolver_notificacion(request, empresa, pk):
    notif = get_object_or_404(NotificacionDiscrepancia, pk=pk, empresa=empresa)
    notif.resuelta = True
    notif.resuelta_por = request.user
    notif.resuelta_en = timezone.now()
    notif.notas_resolucion = request.POST.get('notas', '')
    notif.save(update_fields=['resuelta', 'resuelta_por', 'resuelta_en', 'notas_resolucion'])
    messages.success(request, f'Notificación marcada como resuelta.')
    return redirect('inventario:lista_notificaciones')


# =============================================================================
# API: lotes disponibles por silo (para el form dinámico)
# =============================================================================


@login_required
def api_lotes_silo(request):
    empresa = _get_empresa(request)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa'}, status=403)

    silo = request.GET.get('silo', 'LAB')
    LoteModel = LOTE_MODEL.get(silo, LoteReactivoLab)
    lotes = LoteModel.objects.filter(empresa=empresa, cantidad_actual__gt=0)

    data = []
    for l in lotes[:200]:
        if silo == 'LAB':
            nombre = l.reactivo.nombre
            num_lote = l.numero_lote or 'S/L'
        else:
            nombre = l.insumo.nombre
            num_lote = getattr(l, 'numero_lote', 'S/L') or 'S/L'
        data.append({
            'id': l.pk,
            'nombre': nombre,
            'lote': num_lote,
            'disponible': float(l.cantidad_actual),
        })

    return JsonResponse({'lotes': data, 'silo': silo})
