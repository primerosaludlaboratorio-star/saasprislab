"""Ventana D — Precios: lista dinámica + ajuste masivo de inflación."""
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, CharField, F, Q, Value, When
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from core.tenant import tenant_protected_get
from core.utils.empresa_request import get_empresa_usuario
from lims.models import Analito, PerfilLims, PaqueteLims, PrecioItem
from lims.views.tenant_lims import empresa_lims


def _check_perm(user):
    # PATRÓN CORRECTO: Validar empresa siempre, pero permitir superuser/staff CON empresa válida
    if not get_empresa_usuario(user):
        return False

    # Superuser/staff con empresa válida pueden operar
    if user.is_superuser or user.is_staff:
        return True

    rol = (getattr(user, 'rol', '') or '').upper()
    if rol in ('ADMIN', 'ADMINISTRADOR', 'LABORATORIO', 'LIMS'):
        return True
    return user.groups.filter(name__in=['LABORATORIO', 'LIMS', 'ADMIN']).exists()


def _get_o_crear_precio(tipo, obj):
    """Obtiene o crea un PrecioItem; precio inicial desde costo_lista (CSV) si existe."""
    co = getattr(obj, 'costo_lista', None)
    if co is None:
        co = Decimal('0.00')
    else:
        co = Decimal(co).quantize(Decimal('0.01'))
    if tipo == 'A':
        precio, _ = PrecioItem.objects.get_or_create(
            analito=obj,
            defaults={
                'empresa': obj.empresa,
                'tipo': 'A', 'precio_venta': co,
                'perfil': None, 'paquete': None,
            },
        )
    elif tipo == 'P':
        precio, _ = PrecioItem.objects.get_or_create(
            perfil=obj,
            defaults={
                'empresa': obj.empresa,
                'tipo': 'P', 'precio_venta': co,
                'analito': None, 'paquete': None,
            },
        )
    else:
        precio, _ = PrecioItem.objects.get_or_create(
            paquete=obj,
            defaults={
                'empresa': obj.empresa,
                'tipo': 'Q', 'precio_venta': co,
                'analito': None, 'perfil': None,
            },
        )
    return precio


def _fila_precio_ui(precio: PrecioItem) -> dict:
    """Arma una fila para la tabla a partir del registro real en BD (Nivel 4)."""
    codigo = ''
    nombre = '(sin asignar)'
    subtitulo = ''
    if precio.tipo == 'A':
        a = precio.analito
        if a:
            nombre = a.nombre
            codigo = a.codigo or ''
            subtitulo = a.departamento or ''
    elif precio.tipo == 'P':
        p = precio.perfil
        if p:
            nombre = p.nombre
            codigo = p.id_perfil_legacy or ''
            subtitulo = f'{p.analitos.count()} analitos'
    else:
        qo = precio.paquete
        if qo:
            nombre = qo.nombre
            codigo = qo.id_paquete_legacy or ''
            desc = (qo.descripcion or '').strip()
            subtitulo = desc[:60] + ('…' if len(desc) > 60 else '')
    return {
        'tipo': precio.tipo,
        'tipo_label': precio.get_tipo_display(),
        'codigo': codigo,
        'nombre': nombre,
        'subtitulo': subtitulo,
        'precio_id': precio.pk,
        'precio_venta': precio.precio_venta,
        'activo': precio.activo,
    }


@login_required
def lista(request):
    if not _check_perm(request.user):
        return redirect('home')

    empresa = empresa_lims(request)
    if not empresa:
        messages.error(request, 'No hay empresa activa para precios LIMS.')
        return redirect('home')

    q = (request.GET.get('q') or '').strip()
    tipo_filtro = request.GET.get('tipo', '')  # A, P, Q, ''

    # Lista directamente desde PrecioItem (ensamblaje / sincronizar_precios_lims)
    # FIX V8.2 LIMS TENANT: filtro explícito por empresa (superusuario sin ORM tenant)
    qs = PrecioItem.objects.select_related(
        'analito', 'perfil', 'paquete',
    ).filter(empresa=empresa, activo=True).exclude(
        tipo='A',
        analito__es_vendible_individualmente=False,
    )

    if tipo_filtro in ('A', 'P', 'Q'):
        qs = qs.filter(tipo=tipo_filtro)

    if q:
        qs = qs.filter(
            Q(analito__nombre__icontains=q)
            | Q(analito__codigo__icontains=q)
            | Q(analito__abreviatura__icontains=q)
            | Q(perfil__nombre__icontains=q)
            | Q(perfil__id_perfil_legacy__icontains=q)
            | Q(paquete__nombre__icontains=q)
            | Q(paquete__id_paquete_legacy__icontains=q)
        )

    qs = qs.annotate(
        _ord_nombre=Case(
            When(tipo='A', then=Coalesce(F('analito__nombre'), Value(''))),
            When(tipo='P', then=Coalesce(F('perfil__nombre'), Value(''))),
            When(tipo='Q', then=Coalesce(F('paquete__nombre'), Value(''))),
            default=Value(''),
            output_field=CharField(),
        )
    ).order_by('tipo', '_ord_nombre')

    items = [_fila_precio_ui(p) for p in qs]

    return render(request, 'lims/precios.html', {
        'items': items,
        'total': len(items),
        'q': q,
        'tipo_filtro': tipo_filtro,
    })


@login_required
@require_http_methods(['POST'])
def actualizar_precio(request, precio_pk):
    """AJAX: actualiza el precio_venta de un PrecioItem individual."""
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    precio = tenant_protected_get(PrecioItem, pk=precio_pk)
    try:
        body = json.loads(request.body)
        nuevo_precio = Decimal(str(body.get('precio_venta', 0)))
    except (InvalidOperation, Exception):
        return JsonResponse({'error': 'Precio inválido'}, status=400)
    # FIX CONCURRENCIA: persistencia atómica del renglón de precio
    with transaction.atomic():
        precio.precio_venta = nuevo_precio
        precio.save(update_fields=['precio_venta', 'fecha_actualiz'])
        # Mantener costo_lista del catálogo alineado (update() no dispara señales → sin bucles)
        co = nuevo_precio.quantize(Decimal('0.01'))
        if precio.analito_id:
            Analito.objects_all.filter(pk=precio.analito_id).update(costo_lista=co)
        elif precio.perfil_id:
            PerfilLims.objects_all.filter(pk=precio.perfil_id).update(costo_lista=co)
        elif precio.paquete_id:
            PaqueteLims.objects_all.filter(pk=precio.paquete_id).update(costo_lista=co)
    return JsonResponse({'ok': True, 'precio_venta': str(precio.precio_venta)})


@login_required
@require_http_methods(['POST'])
def ajuste_masivo(request):
    """
    POST JSON: { "ids": [1,2,3], "porcentaje": 5 }
    Aplica precio_venta *= (1 + porcentaje/100) en bulk.
    Porcentaje puede ser negativo para reducción.
    """
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)

    try:
        body = json.loads(request.body)
        ids = [int(i) for i in body.get('ids', [])]
        porcentaje = Decimal(str(body.get('porcentaje', 0)))
    except (InvalidOperation, ValueError, Exception) as e:
        return JsonResponse({'error': f'Datos inválidos: {e}'}, status=400)

    if not ids:
        return JsonResponse({'error': 'No se seleccionaron precios'}, status=400)

    factor = Decimal('1') + (porcentaje / Decimal('100'))
    if factor <= 0:
        return JsonResponse({'error': 'El factor resultante sería ≤ 0'}, status=400)

    empresa = empresa_lims(request)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa activa para ajuste de precios.'}, status=403)

    # FIX V8.2 LIMS TENANT: siempre acotar IDs al tenant (sin bypass por superusuario)
    pk_qs = PrecioItem.objects.filter(id__in=ids, empresa=empresa)
    ids_safe = list(pk_qs.values_list('id', flat=True))
    if not ids_safe:
        return JsonResponse({'error': 'Ningún precio pertenece a su empresa o los IDs no son válidos.'}, status=403)

    # FIX CONCURRENCIA: bulk completo o rollback
    with transaction.atomic():
        PrecioItem.aplicar_inflacion_bulk(ids_safe, factor)

    return JsonResponse({
        'ok': True,
        'actualizados': len(ids_safe),
        'factor': str(factor),
        'mensaje': f'{len(ids_safe)} precios ajustados {porcentaje:+.2f}%',
    })


# ── Ventana D: búsqueda y alta manual de analito (con interruptor venta directa) ─

@login_required
def api_buscar_analitos_precios(request):
    """
    Busca cualquier analito activo (incluye técnicos sin venta directa).
    La decisión de permitir precio se valida en api_agregar_analito_precio.
    """
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos', 'resultados': []}, status=403)

    empresa = empresa_lims(request)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa activa', 'resultados': []}, status=403)

    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return JsonResponse({'resultados': []})
    # FIX V8.2 LIMS TENANT
    qs = (
        Analito.objects.filter(empresa=empresa, activo=True)
        .filter(Q(codigo__icontains=q) | Q(abreviatura__icontains=q) | Q(nombre__icontains=q))
        .values('id', 'codigo', 'abreviatura', 'nombre', 'es_vendible_individualmente')[:30]
    )
    out = []
    for row in qs:
        d = dict(row)
        d['tiene_precio'] = PrecioItem.objects.filter(
            empresa=empresa, analito_id=d['id']
        ).exists()
        out.append(d)
    return JsonResponse({'resultados': out})


@login_required
@require_http_methods(['POST'])
def api_agregar_analito_precio(request):
    """
    Crea PrecioItem tipo A solo si es_vendible_individualmente=True.
    Si el analito es técnico, responde 422 con aviso preventivo (no altera BD).
    """
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    try:
        body = json.loads(request.body)
        aid = int(body.get('analito_id', 0))
    except (ValueError, TypeError, json.JSONDecodeError):
        aid = 0
    if not aid:
        return JsonResponse({'error': 'analito_id requerido'}, status=400)

    analito = tenant_protected_get(Analito, pk=aid)

    if not analito.es_vendible_individualmente:
        return JsonResponse(
            {
                'codigo': 'NO_VENTA_INDIVIDUAL',
                'titulo': 'Analito no vendible individualmente',
                'mensaje': (
                    'Este analito no está marcado como vendible individualmente. Forma parte de perfiles '
                    'o resultados conjuntos; no debe aparecer en catálogo de venta ni en lista de precios '
                    'hasta que un responsable active «Vendible individualmente» en Ventana A (Editar analito).'
                ),
                'analito': {
                    'id': analito.pk,
                    'codigo': analito.codigo,
                    'nombre': analito.nombre,
                },
            },
            status=422,
        )

    if PrecioItem.objects.filter(empresa=analito.empresa_id, analito=analito).exists():
        return JsonResponse({
            'ok': True,
            'ya_existia': True,
            'mensaje': 'Este analito ya tiene fila de precio.',
        })

    _get_o_crear_precio('A', analito)
    return JsonResponse({
        'ok': True,
        'ya_existia': False,
        'mensaje': 'Analito agregado al listado de precios.',
    })
