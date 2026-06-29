"""
Certificación v1.50 — Datos operativos persistentes (lab + farmacia) vía servicios reales.

- Laboratorio: crear_orden_servicio + PagoOrden (anticipo total), api_guardar_resultados (validar)
  → generar_reporte_pdf + guardar_reporte_en_storage dentro de la API.
  Trazabilidad P18: tras la validación, se re-etiqueta metodo_captura=IA_BORRADOR (la API fuerza
  MANUAL en update_or_create; este paso deja el badge naranja auditable sin saltarse el motor).
- Farmacia: ejecutar_venta_pdv (Kardex, DetalleVentaLote, AuditLog).

Nota: Sucursal.gestion_inventario_activa aplica al bypass FEFO de laboratorio al validar;
  el PDV siempre descuenta vía MovimientoInventario cuando hay lotes con stock.

Uso:
  python manage.py generar_data_operativa_v150
  python manage.py generar_data_operativa_v150 --empresa-id 1 --force
  python manage.py generar_data_operativa_v150 --no-local-pdf   # Producción / credenciales Drive completas

Con DEBUG=True se fuerza guardar el PDF en media local (campo archivo_resultado) para evitar 403 de Drive
sin scopes; en producción use --no-local-pdf si el tenant escribe ya en GCS/Drive.

v1.52 — ``--con-adeudo``: los pacientes 1 y 2 (índices 0 y 1) quedan con orden **sin pago** (anticipo 0);
no se valida ni genera PDF (material para Muro de Pago / Octógono). Los otros 3 flujos completos.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from django.test import RequestFactory
from django.utils import timezone

from farmacia.services.venta_farmacia_service import ejecutar_venta_pdv
from lims.models import Analito, ValorReferenciaAnalito

from core.lims_cart import aplicar_precio_convenio, resolve_lims_cart_ids
from core.models import (
    DetalleVenta,
    DetalleVentaLote,
    Empresa,
    Lote,
    OrdenDeServicio,
    Producto,
    ResultadoParametro,
    Usuario,
)
from core.models.base import Sucursal
from core.services.ia_clinical_governance import METODO_IA_BORRADOR
from core.services.paciente_service import obtener_o_crear_paciente
from core.utils.referencia_lims_edad import contexto_edad_sexo_para_lims
from core.views.laboratorio import api_guardar_resultados, crear_orden_servicio
import logging

MIG_0058_CODIGO = '__PRISLAB_MIG_0058__'
V150_MARK = 'V150_SEED_DATA_OPERATIVA'

PACIENTES_V150 = [
    ('María Fernanda Castillo Ríos', 'F', date(1988, 3, 12)),
    ('Jorge Alberto Medina Solís', 'M', date(1992, 7, 25)),
    ('Lucía Hernández Paredes', 'F', date(1975, 11, 3)),
    ('Ricardo Núñez Delgado', 'M', date(2001, 1, 18)),
    ('Andrea Morales Vega', 'F', date(1990, 9, 30)),
]


def _parse_json_response(response) -> dict[str, Any]:
    return json.loads(response.content.decode('utf-8'))


def _storage_kind() -> str:
    try:
        st = OrdenDeServicio._meta.get_field('archivo_resultado').storage
        name = st.__class__.__name__
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _storage_kind (generar_data_operativa_v150.py)")
        name = default_storage.__class__.__name__
    if 'Google' in name or 'GCS' in name or 'S3' in name or 'Drive' in name:
        return 'GCS/Drive/S3'
    return 'Local'


def _swap_archivo_resultado_storage_to_default():
    """
    El FileField de OrdenDeServicio resuelve get_google_drive_storage() al cargar modelos.
    En dev, Drive puede estar activo pero sin scopes: forzamos default_storage solo durante este comando.
    """
    field = OrdenDeServicio._meta.get_field('archivo_resultado')
    orig = field.storage
    field.storage = default_storage
    return field, orig


def _restore_archivo_resultado_storage(field, orig):
    field.storage = orig


def _pick_quimico_user(empresa: Empresa) -> Usuario:
    u = (
        Usuario.objects.filter(empresa=empresa)
        .filter(rol__iexact='QUIMICO')
        .order_by('id')
        .first()
    )
    if u:
        return u
    u = (
        Usuario.objects.filter(empresa=empresa)
        .order_by('-is_staff', '-is_superuser', 'id')
        .first()
    )
    if u:
        return u
    raise CommandError(
        f'No hay usuario con empresa {empresa.pk}. Cree un staff/QUIMICO vinculado a la empresa.'
    )


def _ensure_actor_sucursal(user: Usuario, empresa: Empresa) -> Sucursal:
    # Obtener sucursal asignada actual (primaria) via M2M
    suc_actual = user.get_primary_sucursal()
    if suc_actual:
        return suc_actual

    suc = Sucursal.objects.filter(empresa=empresa, activa=True).order_by('id').first()
    if not suc:
        raise CommandError(f'La empresa {empresa.pk} no tiene sucursal activa.')

    # Asignar via M2M
    user.add_sucursal(suc)
    return suc


def _pick_two_analitos() -> tuple[Analito, Analito]:
    qs = (
        Analito.objects.filter(activo=True, es_calculado=False)
        .exclude(codigo=MIG_0058_CODIGO)
        .order_by('id')
    )
    two = list(qs[:2])
    if len(two) < 2:
        raise CommandError(
            'Se requieren ≥2 analitos activos (no calculados, sin placeholder 0058). '
            'Ejecute: python manage.py ensamblar_lims_v75'
        )
    return two[0], two[1]


def _lims_tokens(a1: Analito, a2: Analito) -> list[str]:
    return [f'analito:{a1.id}', f'analito:{a2.id}']


def _orden_total_desde_tokens(tokens: list[str]) -> Decimal:
    lineas = resolve_lims_cart_ids(list(tokens))
    if len(lineas) != len(tokens):
        raise CommandError('No se pudieron resolver los analitos del carrito LIMS.')
    total = Decimal('0.00')
    for row in lineas:
        total += aplicar_precio_convenio(
            row['precio_base'], row['precio_key'], {}, Decimal('0')
        )
    return total.quantize(Decimal('0.01'))


def _valor_captura_sugerido(analito: Analito, orden: OrdenDeServicio) -> str:
    if analito.tipo_resultado == 'TEXTO':
        return 'Negativo'
    if analito.tipo_resultado == 'OPCIONES':
        raw = (analito.opciones_texto or '').strip().splitlines()
        return (raw[0].strip() if raw else 'Ver informe')
    if analito.tipo_resultado != 'NUMERICO':
        return '0'

    ctx = contexto_edad_sexo_para_lims(orden, orden.paciente)
    sexo = ctx.get('sexo') or 'I'
    qs = ValorReferenciaAnalito.objects.filter(analito=analito).filter(sexo__in=[sexo, 'I'])
    rango = qs.order_by('edad_minima').first()
    if rango and rango.ref_minimo is not None and rango.ref_maximo is not None:
        mid = (rango.ref_minimo + rango.ref_maximo) / 2
        dec = int(analito.decimales or 2)
        return str(round(float(mid), dec))
    if rango and rango.ref_minimo is not None:
        dec = int(analito.decimales or 2)
        return str(round(float(rango.ref_minimo) + 0.01, dec))
    return '10.50'


def _build_resultados_payload(orden: OrdenDeServicio) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for det in orden.detalles.select_related('analito').all():
        an = det.analito
        if not an or getattr(an, 'es_calculado', False):
            continue
        val = _valor_captura_sugerido(an, orden)
        sid = str(det.id)
        aid = str(an.id)
        payload[sid] = {
            'resultado': val,
            'observaciones': '',
            'parametros': {aid: {'valor': val}},
        }
    return payload


def _ensure_productos_con_lote(empresa: Empresa, n: int = 5) -> list[Producto]:
    out: list[Producto] = []
    candidatos = list(
        Producto.objects.filter(empresa=empresa)
        .order_by('id')
        .distinct()[: max(n * 4, 20)]
    )
    hoy = timezone.now().date()
    cad = hoy + timedelta(days=400)
    for p in candidatos:
        if len(out) >= n:
            break
        disp = (
            p.lotes.filter(cantidad__gt=0, fecha_caducidad__gte=hoy)
            .order_by('fecha_caducidad')
            .first()
        )
        if disp:
            out.append(p)
            continue
        Lote.objects.create(
            empresa=empresa,
            producto=p,
            numero_lote=f'V150-{p.id}-{uuid.uuid4().hex[:8].upper()}',
            fecha_caducidad=cad,
            cantidad=50,
            costo_adquisicion=Decimal('10.00'),
        )
        out.append(p)
    if len(out) < n:
        raise CommandError(
            f'Se necesitan {n} productos con lote vendible. Cargue inventario o use seed_pdv_audit_20.'
        )
    return out[:n]


def _ensure_min_lote_stock(producto: Producto, empresa: Empresa, min_units: int = 30) -> None:
    """Garantiza stock PEPS vendible antes de cada venta (evita carreras con otros procesos)."""
    hoy = timezone.now().date()
    total = (
        producto.lotes.filter(fecha_caducidad__gte=hoy).aggregate(s=Sum('cantidad'))['s'] or 0
    )
    if int(total) >= min_units:
        return
    need = max(min_units - int(total), 10)
    Lote.objects.create(
        empresa=empresa,
        producto=producto,
        numero_lote=f'V150-BOOST-{producto.id}-{uuid.uuid4().hex[:8].upper()}',
        fecha_caducidad=hoy + timedelta(days=500),
        cantidad=need,
        costo_adquisicion=Decimal('10.00'),
    )


def _assert_venta_tiene_trazabilidad_lotes(venta_id: int) -> None:
    for dv in DetalleVenta.objects.filter(venta_id=venta_id):
        if not DetalleVentaLote.objects.filter(detalle_venta=dv).exists():
            raise CommandError(
                f'La venta {venta_id} no tiene DetalleVentaLote para el detalle {dv.id} '
                '(trazabilidad fiscal incompleta).'
            )


class Command(BaseCommand):
    help = (
        'Genera 5 órdenes de laboratorio (servicios reales + PDF en storage salvo --con-adeudo) '
        'y 5 ventas PDV con trazabilidad por lote. Opcional: --con-adeudo (2/5 sin pago lab, sin PDF).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            default=None,
            help='ID de empresa (default: primera activa)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Crear un lote adicional de 5+5 aunque ya existan órdenes marcadas V150.',
        )
        parser.add_argument(
            '--local-pdf',
            action='store_true',
            help='Forzar guardado del PDF en default_storage (media local) aunque Drive esté activo.',
        )
        parser.add_argument(
            '--no-local-pdf',
            action='store_true',
            help='No forzar media local: usar el storage configurado del FileField (producción).',
        )
        parser.add_argument(
            '--con-adeudo',
            action='store_true',
            help='2/5 órdenes de laboratorio sin cobro (índices 0–1): sin validación ni PDF; resto íntegro.',
        )

    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        force: bool = options.get('force')
        con_adeudo: bool = bool(options.get('con_adeudo'))
        local_pdf = bool(options.get('local_pdf'))
        if options.get('no_local_pdf'):
            local_pdf = False
        elif not local_pdf and getattr(settings, 'DEBUG', False):
            local_pdf = True

        field_pdf = orig_pdf = None
        if local_pdf:
            field_pdf, orig_pdf = _swap_archivo_resultado_storage_to_default()

        if empresa_id:
            empresa = Empresa.objects.filter(pk=empresa_id).first()
            if not empresa:
                raise CommandError(f'Empresa id={empresa_id} no existe.')
        else:
            empresa = Empresa.objects.filter(activa=True).order_by('id').first()
            if not empresa:
                raise CommandError('No hay empresa activa.')

        if not force:
            prev = OrdenDeServicio.objects.filter(
                deleted_at__isnull=True,
                empresa=empresa,
                notas_internas__icontains=V150_MARK,
            ).count()
            if prev >= 5:
                raise CommandError(
                    f'Ya existen ≥5 órdenes con marca {V150_MARK} para esta empresa. '
                    'Use --force para generar otro lote.'
                )

        user = _pick_quimico_user(empresa)
        sucursal = _ensure_actor_sucursal(user, empresa)
        a1, a2 = _pick_two_analitos()
        tokens = _lims_tokens(a1, a2)
        run_tag = f'{V150_MARK} run={uuid.uuid4().hex[:12]}'
        productos = _ensure_productos_con_lote(empresa, 5)
        rf = RequestFactory()

        try:
            self.stdout.write(
                self.style.NOTICE(
                    f'Empresa={empresa.pk} | Usuario={user.username} | '
                    f'Sucursal={sucursal.pk} ({sucursal.nombre}) | '
                    f'gestion_inventario_activa(lab)={sucursal.gestion_inventario_activa} | '
                    f'Storage PDF (efectivo)={_storage_kind()} | local_pdf_forzado={local_pdf} | '
                    f'con_adeudo={con_adeudo}'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    'Farmacia: el PDV usa Kardex/DetalleVentaLote cuando hay lotes; '
                    'gestion_inventario_activa solo gobierna FEFO de reactivos en validación de lab.'
                )
            )
            if con_adeudo:
                self.stdout.write(
                    self.style.WARNING(
                        'Modo --con-adeudo: filas 1–2 = orden lab sin pago (Muro de Pago); sin PDF ni validación.'
                    )
                )

            filas: list[tuple] = []

            for i, (nombre, sexo, fnac) in enumerate(PACIENTES_V150):
                email = f'v150.e{empresa.pk}.p{i + 1}.{uuid.uuid4().hex[:8]}@seed.prislab.invalid'
                tel = f'5551000{empresa.pk % 1000:03d}{i:02d}'
                paciente, _ = obtener_o_crear_paciente(
                    nombre_completo=nombre,
                    fecha_nacimiento=fnac,
                    sexo=sexo,
                    telefono=tel,
                    email=email,
                    empresa=empresa,
                    sucursal=sucursal,
                    buscar_duplicados=False,
                )

                total_ord = _orden_total_desde_tokens(tokens)
                es_fila_adeudo = con_adeudo and i < 2
                notas = run_tag + (' V150_ADEUDO' if es_fila_adeudo else '')
                body_ord = {
                    'paciente_id': paciente.id,
                    'estudio_ids': tokens,
                    'anticipo': '0' if es_fila_adeudo else str(total_ord),
                    'init_pago_efectivo': '0' if es_fila_adeudo else str(total_ord),
                    'init_pago_credito': '0',
                    'init_pago_debito': '0',
                    'init_pago_tarjeta': '0',
                    'init_pago_transferencia': '0',
                    'notas_internas': notas,
                    'diagnostico': (
                        'Certificación v1.52 — escenario adeudo (sin pago en recepción).'
                        if es_fila_adeudo
                        else 'Certificación operativa v1.50 (datos de prueba persistentes).'
                    ),
                }
                req_o = rf.post(
                    '/laboratorio/api/crear-orden-servicio/',
                    data=json.dumps(body_ord),
                    content_type='application/json',
                )
                req_o.user = user
                req_o.META['REMOTE_ADDR'] = '127.0.0.1'
                req_o.META['HTTP_USER_AGENT'] = 'generar_data_operativa_v150'
                resp_o = crear_orden_servicio(req_o)
                data_o = _parse_json_response(resp_o)
                if resp_o.status_code >= 400 or data_o.get('status') != 'success':
                    raise CommandError(f'crear_orden_servicio: {data_o}')
                orden_id = data_o.get('orden_id')
                if not orden_id:
                    raise CommandError(f'crear_orden_servicio sin orden_id: {data_o}')

                orden = OrdenDeServicio.objects.get(pk=orden_id)
                if not orden.sucursal_id:
                    orden.sucursal = sucursal
                    orden.save()

                if es_fila_adeudo:
                    pdf_url = '(adeudo: orden sin pago total — Muro de Pago / Octógono)'
                else:
                    payload_res = _build_resultados_payload(orden)
                    if not payload_res:
                        raise CommandError(f'Orden {orden_id} sin detalles capturables.')

                    req_g = rf.post(
                        f'/laboratorio/api/guardar-resultados/{orden.id}/',
                        data=json.dumps({'accion': 'validar', 'resultados': payload_res}),
                        content_type='application/json',
                    )
                    req_g.user = user
                    req_g.META['REMOTE_ADDR'] = '127.0.0.1'
                    req_g.META['HTTP_USER_AGENT'] = 'generar_data_operativa_v150'
                    resp_g = api_guardar_resultados(req_g, orden.id)
                    data_g = _parse_json_response(resp_g)
                    if resp_g.status_code >= 400 or data_g.get('status') != 'success':
                        raise CommandError(f'api_guardar_resultados orden={orden.id}: {data_g}')

                    ResultadoParametro.objects.filter(orden_id=orden.id).update(
                        metodo_captura=METODO_IA_BORRADOR
                    )

                    orden.refresh_from_db()
                    pdf_url = ''
                    if orden.archivo_resultado:
                        pdf_url = orden.archivo_resultado.url

                prod = Producto.objects.get(pk=productos[i].id)
                _ensure_min_lote_stock(prod, empresa, min_units=40)
                pu = Decimal(str(prod.precio_publico or 0)).quantize(Decimal('0.01'))
                if pu <= 0:
                    pu = Decimal('1.00')
                subtotal = pu
                total_v = subtotal
                venta_data = {
                    'cliente': paciente.nombre_completo,
                    'paciente_id': paciente.id,
                    'subtotal': str(subtotal),
                    'iva_total': '0.00',
                    'redondeo': '0.00',
                    'total_final': str(total_v),
                    'descuento_aplicado': '0.00',
                    'items': [
                        {
                            'producto_id': prod.id,
                            'cantidad': 1,
                            'precio_unitario': str(pu),
                            'subtotal': str(subtotal),
                            'iva_item': '0.00',
                        }
                    ],
                    'pagos': {'efectivo': str(total_v)},
                }
                req_v = rf.post(
                    '/farmacia/api/ejecutar-venta/',
                    data=json.dumps(venta_data),
                    content_type='application/json',
                )
                req_v.user = user
                req_v.META['REMOTE_ADDR'] = '127.0.0.1'
                req_v.META['HTTP_USER_AGENT'] = 'generar_data_operativa_v150'
                resp_v = ejecutar_venta_pdv(req_v, venta_data, empresa)
                data_v = _parse_json_response(resp_v)
                if resp_v.status_code >= 400 or data_v.get('status') != 'success':
                    raise CommandError(f'ejecutar_venta_pdv fila {i + 1}: {data_v}')
                venta_id = data_v.get('venta_id')
                if venta_id:
                    _assert_venta_tiene_trazabilidad_lotes(int(venta_id))

                filas.append(
                    (
                        paciente.id,
                        paciente.nombre_completo[:40],
                        orden.folio_orden or f'#{orden.id}',
                        venta_id,
                        pdf_url or '(sin archivo_resultado)',
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  [OK] Paciente {paciente.id} | Orden {orden.folio_orden} | Venta {venta_id}'
                    )
                )

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=== Tabla certificación v1.50 ==='))
            cw = (11, 36, 18, 9)
            hdr = ('ID Paciente', 'Nombre', 'Folio Orden', 'ID Venta')
            line = ' | '.join(h.ljust(w) for h, w in zip(hdr, cw)) + ' | URL PDF'
            self.stdout.write(line)
            self.stdout.write('-' * min(120, len(line) + 40))
            for pid, nom, folio, vid, url in filas:
                self.stdout.write(
                    f'{str(pid).ljust(cw[0])} | {nom[: cw[1]].ljust(cw[1])} | '
                    f'{str(folio)[:18].ljust(cw[2])} | {str(vid).ljust(cw[3])} | {url}'
                )
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    'Revisión sugerida: /laboratorio/lista-trabajo/ y /farmacia/ventas/'
                )
            )
        finally:
            if field_pdf is not None and orig_pdf is not None:
                _restore_archivo_resultado_storage(field_pdf, orig_pdf)