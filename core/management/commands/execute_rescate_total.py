"""
Rescate estructural LIMS + inventario + recepción: empresa_id → PRISLAB y stock desde lotes.

  python manage.py execute_rescate_total
  python manage.py execute_rescate_total --empresa-id=1 --dry-run
"""
from django.core.management.base import BaseCommand

from core.rescate_total_prislab import run_rescate_total


class Command(BaseCommand):
    help = 'Asigna empresa principal a registros huérfanos (LIMS, productos, pacientes, órdenes) y sincroniza stock.'

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, default=1, help='PK de core.Empresa (default: 1).')
        parser.add_argument('--dry-run', action='store_true', help='Solo conteos, sin escritura.')

    def handle(self, *args, **options):
        eid = options['empresa_id']
        dry = options['dry_run']
        self.stdout.write(self.style.WARNING(f'=== execute_rescate_total empresa_id={eid} dry_run={dry} ==='))

        result = run_rescate_total(empresa_id=eid, dry_run=dry)
        if result.get('error'):
            self.stdout.write(self.style.ERROR(result['error']))
            return

        self.stdout.write(f"Empresa: {result.get('empresa_nombre')} (id={result.get('empresa_id')})")
        if dry:
            self.stdout.write('Filas con empresa_id NULL (antes):')
            for k, v in sorted(result['antes'].items()):
                self.stdout.write(f'  {k}: {v}')
            self.stdout.write(
                f"  [DRY] productos con suma lotes vigentes > 0: "
                f"{result.get('stock', {}).get('productos_con_suma_lotes_positiva', '—')}"
            )
            self.stdout.write(self.style.WARNING('[DRY-RUN] Sin cambios en BD.'))
            return

        self.stdout.write(self.style.SUCCESS('Filas actualizadas (UPDATE empresa_id):'))
        total_rows = 0
        for k, v in sorted(result.get('actualizados', {}).items()):
            self.stdout.write(f'  {k}: {v}')
            total_rows += int(v or 0)
        self.stdout.write(f'  TOTAL filas con empresa asignada en esta pasada: {total_rows}')

        st = result.get('stock', {})
        self.stdout.write(self.style.SUCCESS(
            f"Stock: productos tocados={st.get('productos_actualizados', '—')} | "
            f"con stock>0 tras sync={st.get('productos_con_stock_positivo', '—')}"
        ))
