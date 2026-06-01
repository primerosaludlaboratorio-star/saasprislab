import os
import sys
import json
from datetime import datetime


def _iso():
    return datetime.utcnow().isoformat() + "Z"


def main():
    # Asegura que el repo root esté en sys.path (ejecución desde tools/).
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings"))
    try:
        import django

        django.setup()
    except Exception as e:
        print(
            json.dumps(
                {
                    "protocol": "PRISLAB_DATA_INTEGRITY",
                    "timestamp": _iso(),
                    "ok": False,
                    "fatal": str(e),
                },
                indent=2,
            )
        )
        raise

    from django.db.models import Count
    from core.models.catalogos import Producto
    from core.models.laboratorio import OrdenDeServicio
    from core.models.base import Empresa, Usuario

    empresas = list(Empresa.objects.values("id", "nombre")[:50])

    productos_total = Producto.objects.count()
    productos_por_empresa = list(
        Producto.objects.values("empresa_id").annotate(c=Count("id")).order_by("empresa_id")
    )

    # Candado Sentinel: orden en LISTO/ENTREGADO debe tener PDF
    ordenes_listas_sin_pdf = list(
        OrdenDeServicio.objects.filter(estado__in=["RESULTADOS_LISTOS", "ENTREGADO"])
        .filter(archivo_resultado__isnull=True)
        .values("id", "folio_orden", "estado", "empresa_id")[:500]
    )

    # Multi-tenant: usuarios sin empresa causan vacíos/403 en varios módulos
    usuarios_sin_empresa = list(
        Usuario.objects.filter(empresa__isnull=True)
        .values("id", "username", "rol", "is_active")[:500]
    )

    ok = len(ordenes_listas_sin_pdf) == 0

    print(
        json.dumps(
            {
                "protocol": "PRISLAB_DATA_INTEGRITY",
                "timestamp": _iso(),
                "ok": ok,
                "empresas": empresas,
                "productos": {
                    "total": productos_total,
                    "by_empresa": productos_por_empresa,
                },
                "ordenes_listas_sin_pdf": ordenes_listas_sin_pdf,
                "usuarios_sin_empresa": usuarios_sin_empresa,
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
