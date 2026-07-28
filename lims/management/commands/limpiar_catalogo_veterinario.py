"""Retira el catálogo veterinario del catálogo operativo humano.

No borra registros con posible valor histórico. Desactiva analitos, perfiles,
paquetes, precios y estudios veterinarios para que no aparezcan en LIMS ni en
venta, y elimina sus relaciones de composición. El modo de simulación es el
predeterminado; usar ``--apply`` para aplicar.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.tenant import tenant_bypass
from laboratorio.models import Estudio
from lims.models import Analito, PaqueteLims, PerfilAnalito, PerfilLims, PrecioItem
from lims.veterinary_catalog import is_veterinary_catalog_text


class Command(BaseCommand):
    help = 'Desactiva del catálogo operativo los estudios y entidades LIMS veterinarias.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Aplicar la limpieza; sin esto solo simula.')

    def handle(self, *args, **options):
        apply = options['apply']
        with tenant_bypass():
            return self._handle_all_tenants(apply)

    def _handle_all_tenants(self, apply):
        analitos = list(Analito.objects.all())
        perfiles = list(PerfilLims.objects.all())
        paquetes = list(PaqueteLims.objects.all())
        estudios = list(Estudio.objects.all())

        analito_ids = {
            item.pk for item in analitos
            if is_veterinary_catalog_text(
                item.codigo, item.abreviatura, item.nombre, item.departamento,
                item.tipo_muestra, item.metodologia, item.notas,
            )
        }
        perfil_ids = {
            item.pk for item in perfiles
            if is_veterinary_catalog_text(
                item.id_perfil_legacy, item.nombre, item.descripcion,
            )
        }
        paquete_ids = {
            item.pk for item in paquetes
            if is_veterinary_catalog_text(
                item.id_paquete_legacy, item.nombre, item.descripcion,
            )
        }
        estudio_ids = {
            item.pk for item in estudios
            if is_veterinary_catalog_text(
                item.codigo, item.nombre, item.categoria.nombre if item.categoria_id else '',
            )
        }

        self.stdout.write(
            f'Analitos: {len(analito_ids)} | Perfiles: {len(perfil_ids)} | '
            f'Paquetes: {len(paquete_ids)} | Estudios legacy: {len(estudio_ids)}'
        )
        if not apply:
            self.stdout.write(self.style.WARNING('[DRY-RUN] No se modificó la base de datos. Use --apply para aplicar.'))
            return

        with transaction.atomic():
            # Se conservan entidades para no romper resultados/historiales.
            Analito.objects.filter(pk__in=analito_ids).update(activo=False)
            PerfilLims.objects.filter(pk__in=perfil_ids).update(activo=False)
            PaqueteLims.objects.filter(pk__in=paquete_ids).update(activo=False, venta_publico=False)
            PerfilAnalito.objects.filter(
                perfil_id__in=perfil_ids,
            ).delete()
            PerfilAnalito.objects.filter(analito_id__in=analito_ids).delete()
            PaqueteLims.analitos.through.objects.filter(
                analito_id__in=analito_ids,
            ).delete()
            PaqueteLims.perfiles.through.objects.filter(
                perfil_id__in=perfil_ids,
            ).delete()

            # PrecioItem tiene referencias polimórficas; se desactiva sin borrar.
            PrecioItem.objects.filter(
                analito_id__in=analito_ids,
            ).update(activo=False)
            PrecioItem.objects.filter(
                perfil_id__in=perfil_ids,
            ).update(activo=False)
            PrecioItem.objects.filter(
                paquete_id__in=paquete_ids,
            ).update(activo=False)

            # Estudio legacy no tiene bandera activo; se conserva para historial.
            self.stdout.write(self.style.WARNING(
                f'Estudios legacy veterinarios detectados y preservados: {len(estudio_ids)}'
            ))

        self.stdout.write(self.style.SUCCESS('Catálogo veterinario retirado del catálogo operativo LIMS/venta.'))
