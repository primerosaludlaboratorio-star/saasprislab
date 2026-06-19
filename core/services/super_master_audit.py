from django.core.exceptions import PermissionDenied

from core.models import AuditLog


def es_super_master(user) -> bool:
    """True solo para superusuarios marcados como Auditor Supremo."""
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_superuser", False)
        and getattr(user, "es_auditor_supremo", False)
    )


def obtener_logs_auditoria_global(user):
    """Devuelve la bitacora global solo al Super Master."""
    if not es_super_master(user):
        raise PermissionDenied("Solo Super Master puede auditar todos los tenants.")
    return AuditLog.objects.select_related("empresa", "usuario").all()
