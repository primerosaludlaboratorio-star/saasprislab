"""
Normaliza clasificación LIMS para datos existentes.

Agrega marcador en Estudio.descripcion_interna:
- TIPO_LIMS=PAQUETE
- TIPO_LIMS=PERFIL

Uso:
    python manage.py normalizar_tipo_lims
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


def _set_marker(estudio, tipo):
    lineas = (estudio.descripcion_interna or "").splitlines()
    limpias = [ln for ln in lineas if not ln.strip().upper().startswith("TIPO_LIMS=")]
    limpias.append(f"TIPO_LIMS={tipo}")
    estudio.descripcion_interna = "\n".join([ln for ln in limpias if ln.strip()])


def _es_paquete(estudio):
    codigo = (estudio.codigo or "").upper()
    nombre = (estudio.nombre or "").upper()
    # Regla conservadora:
    # - código PAQ*
    # - nombre menciona paquete
    # - contenedor de otros perfiles (anidación típica de paquete)
    tiene_perfiles = estudio.componentes.filter(es_perfil=True).exists()
    return codigo.startswith("PAQ") or "PAQUETE" in nombre or tiene_perfiles


class Command(BaseCommand):
    help = "Normaliza TIPO_LIMS para estudios/perfiles/paquetes existentes."

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        perfiles = Estudio.objects.filter(es_perfil=True).prefetch_related("componentes")
        actualizados = 0
        marcados_paquete = 0
        marcados_perfil = 0

        with transaction.atomic():
            for estudio in perfiles:
                tipo = "PAQUETE" if _es_paquete(estudio) else "PERFIL"
                before = (estudio.descripcion_interna or "").strip()
                _set_marker(estudio, tipo)
                after = (estudio.descripcion_interna or "").strip()
                if after != before:
                    estudio.save(update_fields=["descripcion_interna"])
                    actualizados += 1
                if tipo == "PAQUETE":
                    marcados_paquete += 1
                else:
                    marcados_perfil += 1

        self.stdout.write(self.style.SUCCESS("=" * 72))
        self.stdout.write(self.style.SUCCESS("NORMALIZACIÓN TIPO_LIMS COMPLETADA"))
        self.stdout.write(self.style.SUCCESS(f"Perfiles/paquetes evaluados: {perfiles.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Marcados como PERFIL: {marcados_perfil}"))
        self.stdout.write(self.style.SUCCESS(f"Marcados como PAQUETE: {marcados_paquete}"))
        self.stdout.write(self.style.SUCCESS(f"Registros actualizados: {actualizados}"))
        self.stdout.write(self.style.SUCCESS("=" * 72))
