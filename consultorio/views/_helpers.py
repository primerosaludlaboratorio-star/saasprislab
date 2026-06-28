"""
Helpers y constantes compartidas del módulo consultorio.
"""
from decimal import Decimal, InvalidOperation

from core.utils.empresa_request import empresa_efectiva_request
from core.models import Medico


def _empresa_explicita_usuario(request):
    """Empresa del usuario para APIs tenant-sensitive; no usa fallback del middleware."""
    if not getattr(request, 'user', None) or not getattr(request.user, 'is_authenticated', False):
        return None
    if not getattr(request.user, 'empresa_id', None):
        return None
    return empresa_efectiva_request(request)


def _resolver_medico_usuario(request, empresa, *, medico_preferido=None, autocrear=False):
    """
    Resuelve el médico operativo del usuario actual sin caer en el "primer médico"
    de la empresa, para evitar certificados, recetas u órdenes firmadas por la
    persona equivocada.
    """
    if not empresa or not getattr(request, 'user', None) or not request.user.is_authenticated:
        return None

    if medico_preferido and getattr(medico_preferido, 'empresa_id', None) == empresa.id:
        return medico_preferido

    medico_profile = getattr(request.user, 'medico_profile', None)
    if medico_profile and getattr(medico_profile, 'empresa_id', None) == empresa.id:
        return medico_profile

    nombre_usuario = (request.user.get_full_name() or '').strip()
    if nombre_usuario:
        medico = Medico.objects.filter(
            empresa=empresa,
            activo=True,
            nombre_completo__iexact=nombre_usuario,
        ).first()
        if medico:
            return medico

    cedula_usuario = getattr(request.user, 'cedula_interna', None)
    if isinstance(cedula_usuario, str):
        cedula_usuario = cedula_usuario.strip()
    if cedula_usuario:
        medico = Medico.objects.filter(
            empresa=empresa,
            cedula_profesional=cedula_usuario,
        ).first()
        if medico:
            return medico

    if not autocrear:
        return None

    medico, _ = Medico.objects.get_or_create(
        empresa=empresa,
        cedula_profesional=cedula_usuario or f'USR-{request.user.id}',
        defaults={
            'nombre_completo': nombre_usuario or request.user.username,
            'especialidad': 'Médico General',
            'empresa': empresa,
        }
    )
    return medico


# =====================================================================
# HELPERS para conversión segura de POST values
# =====================================================================
def _int_or_none(val):
    """Convierte a int de forma segura. Retorna None si no es posible."""
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def _dec_or_none(val):
    """Convierte a Decimal de forma segura. Retorna None si no es posible."""
    try:
        if val is not None and isinstance(val, str):
            val = val.strip()
        return Decimal(val) if val else None
    except (ValueError, TypeError, InvalidOperation):
        return None


def _int_in_range(val, min_val, max_val):
    """Convierte a int y lo acota a [min_val, max_val]. Retorna None si no es posible."""
    n = _int_or_none(val)
    if n is None:
        return None
    if min_val is not None and n < min_val:
        return None
    if max_val is not None and n > max_val:
        return None
    return n


def _dec_in_range(val, min_val, max_val):
    """Convierte a Decimal y lo acota a [min_val, max_val]. Retorna None si no es posible."""
    d = _dec_or_none(val)
    if d is None:
        return None
    if min_val is not None and d < min_val:
        return None
    if max_val is not None and d > max_val:
        return None
    return d


# Rangos clínicamente razonables para signos vitales (CICLO 6)
_SV_PA_SIS_MIN, _SV_PA_SIS_MAX = 50, 300
_SV_PA_DIA_MIN, _SV_PA_DIA_MAX = 30, 200
_SV_FC_MIN, _SV_FC_MAX = 20, 300
_SV_FR_MIN, _SV_FR_MAX = 5, 60
_SV_TEMP_MIN, _SV_TEMP_MAX = Decimal('32'), Decimal('45')
_SV_PESO_MIN, _SV_PESO_MAX = Decimal('2'), Decimal('500')
_SV_TALLA_MIN, _SV_TALLA_MAX = Decimal('0.3'), Decimal('2.5')
_SV_SPO2_MIN, _SV_SPO2_MAX = 0, 100
_SV_GLUC_MIN, _SV_GLUC_MAX = Decimal('0'), Decimal('600')
