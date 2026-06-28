"""
laboratorio/services/unificacion.py
Servicios de paciente y orden: fuente canónica `core.Paciente` / `core.OrdenDeServicio`.
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.utils import timezone

logger = logging.getLogger('laboratorio.unificacion')

# ─── Constante de mapeo origen legacy → core ─────────────────────────────────
_ORIGEN_MAP = {
    'PUBLICO_GENERAL': 'PUBLICO_GENERAL',
    'CONVENIO':        'CONVENIO',
    'SEGURO':          'MEDICO_EXTERNO',
    'OTRO':            'PUBLICO_GENERAL',
}


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 1 — PACIENTE
# ══════════════════════════════════════════════════════════════════════════════

def _split_apellidos(apellidos_combined: str) -> tuple[str, str]:
    """
    Divide el campo 'apellidos' (formato legacy 'PATERNO MATERNO') en dos.
    Retorna (apellido_paterno, apellido_materno).
    """
    partes = (apellidos_combined or '').strip().split(maxsplit=1)
    paterno = partes[0] if partes else ''
    materno = partes[1] if len(partes) > 1 else ''
    return paterno, materno


def crear_paciente_unificado(empresa, sucursal, datos: dict):
    """
    Crea un paciente en core.Paciente (única tabla operativa).

    datos: nombres, apellidos (paterno+materno en un string), fecha_nacimiento,
            sexo, telefono (opt), email (opt).

    Retorna: {'core': core.Paciente, 'creado_core': True}
    """
    from core.models import Paciente as CorePaciente

    paterno, materno = _split_apellidos(datos['apellidos'])
    with transaction.atomic():
        core_pax = CorePaciente.objects.create(
            empresa=empresa,
            sucursal=sucursal,
            nombres=datos['nombres'],
            apellido_paterno=paterno,
            apellido_materno=materno,
            fecha_nacimiento=datos['fecha_nacimiento'],
            sexo=datos['sexo'],
            telefono=datos.get('telefono'),
            email=datos.get('email'),
            tipo='GENERAL',
        )
    return {'core': core_pax, 'creado_core': True}


def buscar_pacientes_unificado(empresa, query: str, limit: int = 20) -> list[dict]:
    """
    Búsqueda en core.Paciente (multi-tenant).
    Retorna dicts compatibles con Select2/autocomplete.
    """
    from django.db.models import Q
    try:
        from core.models import Paciente as CorePaciente

        core_qs = CorePaciente.objects.filter(
            empresa=empresa,
            activo=True,
        ).filter(
            Q(nombre_completo__icontains=query) |
            Q(telefono__icontains=query) |
            Q(nombres__icontains=query) |
            Q(apellido_paterno__icontains=query)
        ).order_by('nombre_completo')[:limit]

        resultados = []
        for p in core_qs:
            resultados.append({
                'id': p.id,
                'fuente': 'core',
                'codigo': '',
                'nombre_completo': p.nombre_completo,
                'nombres': p.nombres,
                'apellidos': f'{p.apellido_paterno} {p.apellido_materno}'.strip(),
                'fecha_nacimiento': p.fecha_nacimiento.strftime('%Y-%m-%d') if p.fecha_nacimiento else '',
                'sexo': p.get_sexo_display() if p.sexo else '',
                'edad': p.calcular_edad() or '',
                'telefono': p.telefono or '',
            })

        return resultados

    except (DatabaseError, ValidationError) as exc:
        logger.error(f"buscar_pacientes_unificado error: {exc}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 2 — ORDEN
# ══════════════════════════════════════════════════════════════════════════════

def _generar_folio(empresa) -> str:
    """Genera folio único PRIS-YYYYMMDD-XXXX para core.OrdenDeServicio."""
    from core.models import OrdenDeServicio
    prefijo = timezone.now().strftime('PRIS-%Y%m%d')
    ultimo = OrdenDeServicio.objects.filter(
        empresa=empresa,
        folio_orden__startswith=prefijo,
    ).order_by('folio_orden').last()

    if ultimo and ultimo.folio_orden:
        try:
            num = int(ultimo.folio_orden.split('-')[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    return f'{prefijo}-{num:04d}'


def _encontrar_core_medico(empresa, medico_legacy=None, medico_texto: str = ''):
    """
    Encuentra o crea un core.Medico equivalente.
    Prioriza medico_legacy (laboratorio.Medico), fallback a medico_texto.
    Retorna core.Medico o None.
    """
    try:
        from core.models import Medico as CoreMedico

        if medico_legacy:
            hit = CoreMedico.objects.filter(
                empresa=empresa,
                nombre_completo__icontains=medico_legacy.nombre[:10],
            ).first()
            if hit:
                return hit
            # Crear en core
            import uuid as _u
            return CoreMedico.objects.create(
                empresa=empresa,
                nombre_completo=medico_legacy.nombre,
                cedula_profesional=f'PEND-{_u.uuid4().hex[:8].upper()}',
                especialidad=medico_legacy.especialidad or 'Médico General',
            )

        if medico_texto:
            hit = CoreMedico.objects.filter(
                empresa=empresa,
                nombre_completo__icontains=medico_texto[:10],
            ).first()
            if hit:
                return hit
            import uuid as _u
            return CoreMedico.objects.create(
                empresa=empresa,
                nombre_completo=medico_texto,
                cedula_profesional=f'PEND-{_u.uuid4().hex[:8].upper()}',
                especialidad='Médico General',
            )
    except (DatabaseError, ValidationError) as exc:
        logger.warning(f"_encontrar_core_medico error: {exc}")
    return None


def crear_orden_core_desde_legacy(orden_legacy, empresa, sucursal, usuario) -> 'core.OrdenDeServicio | None':
    """
    DEPRECADO (v7.5): el flujo canónico crea solo core.OrdenDeServicio.
    Se mantiene por compatibilidad con scripts que aún pasen laboratorio.Orden.
    """
    try:
        from core.models import OrdenDeServicio

        core_paciente = orden_legacy.paciente

        # 2. Calcular total desde detalles legacy
        total = Decimal('0')
        try:
            for det in orden_legacy.detalles.all():
                total += det.subtotal
        except (AttributeError, TypeError):
            total = Decimal('0')

        # 3. Mapear origen
        origen_core = _ORIGEN_MAP.get(orden_legacy.origen, 'PUBLICO_GENERAL')

        # 4. Médico
        medico_core = _encontrar_core_medico(
            empresa,
            medico_legacy=getattr(orden_legacy, 'medico', None),
            medico_texto=getattr(orden_legacy, 'medico_texto', '') or '',
        )

        # 5. Snapshots del paciente en el momento de la orden
        pax = orden_legacy.paciente
        pax_edad = pax.calcular_edad() if hasattr(pax, 'calcular_edad') else None
        pax_nombre = pax.nombre_completo or str(pax)
        pax_sexo = getattr(pax, 'sexo', None) or 'M'

        # 6. Crear core.OrdenDeServicio
        folio = _generar_folio(empresa)
        core_orden = OrdenDeServicio.objects.create(
            empresa=empresa,
            sucursal=sucursal,
            paciente=core_paciente,
            paciente_nombre_snapshot=pax_nombre,
            paciente_edad_snapshot=pax_edad,
            paciente_sexo_snapshot=pax_sexo,
            medico_referente=medico_core,
            origen_orden=origen_core,
            folio_orden=folio,
            total=total,
            responsable_ingreso=usuario,
            estado='PENDIENTE_PAGO',
            estado_pago='PENDIENTE',
            estado_clinico='PENDIENTE_TOMA',
        )

        logger.info(
            f"[UNIF] core.OrdenDeServicio #{core_orden.id} folio={folio} "
            f"creada desde legacy.Orden #{orden_legacy.id}"
        )
        return core_orden

    except (DatabaseError, ValidationError) as exc:
        logger.error(
            f"crear_orden_core_desde_legacy FALLÓ para legacy.Orden #{orden_legacy.id}: {exc}",
            exc_info=True,
        )
        return None
