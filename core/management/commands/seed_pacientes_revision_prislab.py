"""
Inserta 5 pacientes persistentes + 1 orden de laboratorio c/u para revisión integral (UI/PDF/flujo).

Idempotente: si ya existen 5 pacientes con la etiqueta [DEMO-PRISLAB-V1-REVISION] en la empresa,
solo imprime sus IDs sin duplicar.

Uso:
  python manage.py seed_pacientes_revision_prislab
  python manage.py seed_pacientes_revision_prislab --empresa-id 1
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()

TAG = '[DEMO-PRISLAB-V1-REVISION]'

PACIENTES = [
    ('Ana Lucía', 'Martínez', 'Ríos', date(1992, 5, 14), 'F', '5551002001'),
    ('Carlos', 'Hernández', 'Vega', date(1978, 11, 3), 'M', '5551002002'),
    ('Rosa Elena', 'Jiménez', 'Soto', date(2001, 8, 22), 'F', '5551002003'),
    ('Jorge Luis', 'Paredes', 'Núñez', date(1965, 1, 30), 'M', '5551002004'),
    ('Fernanda', 'Castillo', 'Moral', date(2010, 12, 7), 'F', '5551002005'),
]


class Command(BaseCommand):
    help = 'Crea 5 pacientes demo persistentes con orden EN_PROCESO pagada (1 analito).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            default=None,
            help='ID de empresa (default: primera empresa por pk).',
        )

    def handle(self, *args, **options):
        from core.models import DetalleOrden, Empresa, OrdenDeServicio, Paciente, Sucursal
        from lims.models import Analito

        eid = options.get('empresa_id')
        if eid:
            empresa = Empresa.objects.filter(pk=eid).first()
            if not empresa:
                raise CommandError(f'No existe Empresa id={eid}')
        else:
            empresa = Empresa.objects.order_by('pk').first()
            if not empresa:
                raise CommandError('No hay ninguna Empresa. Cree una en admin u onboarding.')

        user = User.objects.filter(empresa=empresa).order_by('pk').first()
        if not user:
            raise CommandError(
                f'No hay usuario con empresa_id={empresa.id}. Asigne empresa a un usuario staff.'
            )

        suc = Sucursal.objects.filter(empresa=empresa, activa=True).order_by('pk').first()

        qs_exist = Paciente.objects.filter(empresa=empresa, nombre_completo__contains=TAG).order_by('pk')
        if qs_exist.count() >= 5:
            self.stdout.write(self.style.WARNING(
                f'Ya existen ≥5 pacientes con etiqueta {TAG}. Listado actual:'
            ))
            self._imprimir_filas(qs_exist[:5])
            return

        analito = (
            Analito.objects.filter(activo=True)
            .exclude(codigo='__PRISLAB_MIG_0058__')
            .order_by('pk')
            .first()
        )
        if not analito:
            analito = Analito.objects.filter(activo=True).order_by('pk').first()
        if not analito:
            raise CommandError('No hay lims.Analito activo. Ejecute ensamblar_lims_v75 primero.')

        precio = Decimal('150.00')
        creados = []

        for idx, (nom, ap_pat, ap_mat, fnac, sexo, tel) in enumerate(PACIENTES, start=1):
            email = f'persist.demo.v1.{idx}.emp{empresa.id}@prislab-seed.invalid'
            nc = f'{TAG} {nom} {ap_pat} {ap_mat}'
            paciente, p_created = Paciente.objects.get_or_create(
                empresa=empresa,
                email=email,
                defaults={
                    'nombres': nom,
                    'apellido_paterno': ap_pat,
                    'apellido_materno': ap_mat,
                    'nombre_completo': nc,
                    'fecha_nacimiento': fnac,
                    'sexo': sexo,
                    'telefono': tel,
                    'tipo': 'GENERAL',
                },
            )
            if not p_created and TAG not in (paciente.nombre_completo or ''):
                paciente.nombre_completo = nc
                paciente.nombres = nom
                paciente.apellido_paterno = ap_pat
                paciente.apellido_materno = ap_mat
                paciente.fecha_nacimiento = fnac
                paciente.sexo = sexo
                paciente.telefono = tel
                paciente.save()

            orden = OrdenDeServicio.objects.create(
                empresa=empresa,
                sucursal=suc,
                paciente=paciente,
                total=precio,
                anticipo=precio,
                estado='EN_PROCESO',
                estado_pago='PAGADO',
                responsable_ingreso=user,
                origen_orden='PUBLICO_GENERAL',
                tipo_servicio='RUTINA',
            )
            DetalleOrden.objects.create(
                orden=orden,
                analito=analito,
                precio_momento=precio,
            )
            creados.append((paciente, orden))

        self.stdout.write(self.style.SUCCESS(
            f'Creados {len(creados)} pacientes y órdenes en empresa «{empresa.nombre}» (id={empresa.id}). '
            f'Analito línea: {analito.codigo} — {analito.nombre}'
        ))
        self._imprimir_filas([p for p, _ in creados], ordenes=[o for _, o in creados])

    def _imprimir_filas(self, pacientes, ordenes=None):
        from core.models import OrdenDeServicio

        self.stdout.write('')
        self.stdout.write(f'{"#":<3} {"PACIENTE_ID":<12} {"ORDEN_ID":<10} Nombre')
        self.stdout.write('-' * 72)
        if ordenes is None:
            for i, p in enumerate(pacientes, 1):
                oid = (
                    OrdenDeServicio.objects.filter(paciente=p)
                    .order_by('-pk')
                    .values_list('id', flat=True)
                    .first()
                )
                self.stdout.write(f'{i:<3} {p.pk:<12} {oid or "-":<10} {p.nombre_completo[:42]}')
        else:
            for i, (p, o) in enumerate(zip(pacientes, ordenes), 1):
                self.stdout.write(f'{i:<3} {p.pk:<12} {o.pk:<10} {p.nombre_completo[:42]}')
        self.stdout.write('')
