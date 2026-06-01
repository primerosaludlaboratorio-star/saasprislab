"""
Verificación de señales operativas en datos reales (sin marcar OK ficticio).

Muchas instalaciones nuevas tendrán ADVERTENCIAS hasta poblar catálogos;
eso es esperado: el comando debe reflejar la verdad, no consolar.

Uso:
    python manage.py verificar_funcionalidades
    python manage.py verificar_funcionalidades --strict   # exit code != 0 si falla algún [WARN]
"""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = 'Comprueba datos clave; los WARN son informativos salvo --strict.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Termina con error si alguna verificación devuelve advertencia.',
        )

    def handle(self, *args, **options):
        strict = options['strict']

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('VERIFICACIÓN DE FUNCIONALIDADES (datos reales)'))
        self.stdout.write(self.style.SUCCESS('=' * 80 + '\n'))

        verificaciones = [
            ('Multi-Tenant', self._verificar_multi_tenant),
            ('FEFO / Lotes', self._verificar_fefo),
            ('Auditoría Forense (30 días)', self._verificar_auditoria),
            ('Órdenes LIMS / servicio', self._verificar_ordenes_servicio),
            ('Perfiles Laboratorio', self._verificar_perfiles),
            ('Backup completado', self._verificar_backup),
            ('Recetas registradas', self._verificar_receta),
            ('RH Bitácora 39-A', self._verificar_rh),
        ]

        resultados = {}
        warnings_count = 0

        for nombre, funcion in verificaciones:
            try:
                resultado = funcion()
                resultados[nombre] = resultado
                if resultado.get('ok'):
                    self.stdout.write(self.style.SUCCESS(f'[OK] {nombre}'))
                    if resultado.get('detalle'):
                        self.stdout.write(f'      → {resultado["detalle"]}')
                else:
                    warnings_count += 1
                    self.stdout.write(self.style.WARNING(
                        f'[WARN] {nombre}: {resultado.get("mensaje", "Revisar")}'
                    ))
                    if resultado.get('detalle'):
                        self.stdout.write(f'       → {resultado["detalle"]}')
            except Exception as e:
                warnings_count += 1
                resultados[nombre] = {'ok': False, 'error': str(e)}
                self.stdout.write(self.style.ERROR(f'[ERROR] {nombre}: {e}'))

        exitosos = sum(1 for r in resultados.values() if r.get('ok'))
        total = len(verificaciones)

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS(f'RESUMEN: {exitosos}/{total} comprobaciones OK'))
        if warnings_count:
            self.stdout.write(self.style.WARNING(
                f'{warnings_count} ítem(es) requieren datos o configuración (normal en BD vacía o recién migrada).'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('Todas las comprobaciones de datos cumplen umbral.'))
        self.stdout.write(self.style.SUCCESS('=' * 80 + '\n'))

        if strict and warnings_count > 0:
            raise CommandError(
                f'Modo --strict: {warnings_count} advertencia(s). Corrija datos o ejecute sin --strict para solo informar.'
            )

    def _verificar_multi_tenant(self):
        from core.models import Empresa

        empresas = Empresa.objects.filter(activa=True).count()
        ok = empresas > 0
        return {
            'ok': ok,
            'mensaje': 'No hay empresas activas.',
            'detalle': f'Empresas activas: {empresas}',
        }

    def _verificar_fefo(self):
        from core.models import Lote

        lotes = Lote.objects.count()
        ok = lotes > 0
        return {
            'ok': ok,
            'mensaje': 'Sin lotes en inventario (FEFO no ejercitado aún).',
            'detalle': f'Lotes en sistema: {lotes}',
        }

    def _verificar_auditoria(self):
        from core.models import AuditLog

        logs = AuditLog.objects.filter(
            fecha_cierta__gte=timezone.now() - timedelta(days=30)
        ).count()
        ok = logs > 0
        return {
            'ok': ok,
            'mensaje': 'Sin registros de auditoría en los últimos 30 días.',
            'detalle': f'Eventos auditoría (30 d): {logs}',
        }

    def _verificar_ordenes_servicio(self):
        from core.models import OrdenDeServicio

        ordenes = OrdenDeServicio.objects.count()
        ok = ordenes > 0
        return {
            'ok': ok,
            'mensaje': 'Sin órdenes de servicio (flujo laboratorio no demostrado en datos).',
            'detalle': f'Órdenes totales: {ordenes}',
        }

    def _verificar_perfiles(self):
        from laboratorio.models import PerfilLaboratorio

        perfiles = PerfilLaboratorio.objects.count()
        ok = perfiles > 0
        return {
            'ok': ok,
            'mensaje': 'Sin perfiles de laboratorio cargados.',
            'detalle': f'Perfiles: {perfiles}',
        }

    def _verificar_backup(self):
        from core.models import BackupRegistro

        desde = timezone.now() - timedelta(days=90)
        backups = BackupRegistro.objects.filter(estado='COMPLETADO', fecha_backup__gte=desde).count()
        ok = backups > 0
        return {
            'ok': ok,
            'mensaje': 'No hay backups COMPLETADO en los últimos 90 días.',
            'detalle': f'Backups completados (90 d): {backups}',
        }

    def _verificar_receta(self):
        from core.models import Receta

        recetas = Receta.objects.count()
        ok = recetas > 0
        return {
            'ok': ok,
            'mensaje': 'Sin recetas digitales registradas.',
            'detalle': f'Recetas: {recetas}',
        }

    def _verificar_rh(self):
        from core.models import Bitacora39A

        evaluaciones = Bitacora39A.objects.count()
        ok = evaluaciones > 0
        return {
            'ok': ok,
            'mensaje': 'Sin evaluaciones NOM-035 / bitácora 39-A.',
            'detalle': f'Registros: {evaluaciones}',
        }
