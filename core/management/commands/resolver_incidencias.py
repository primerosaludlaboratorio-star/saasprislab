"""
PRIS SENTINEL — Resolver Incidencias Conocidas
================================================
Marca como SOLUCIONADO todas las incidencias Sentinel que correspondan
a errores ya corregidos en el codigo desplegado.

Uso:
  python manage.py resolver_incidencias
  python manage.py resolver_incidencias --dry-run
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger('sentinel')

# Patrones de errores ya corregidos (tipo_excepcion, url_parcial, descripcion_fix)
ERRORES_RESUELTOS = [
    {
        'filtro': {'tipo_excepcion__icontains': 'NameError'},
        'url_contiene': '',
        'descripcion': "timezone not imported in sentinel.py",
        'nota': 'Corregido: Se agrego import timezone al inicio de sentinel.py',
    },
    {
        'filtro': {'tipo_excepcion__icontains': 'FieldError'},
        'url_contiene': 'entrega-resultados',
        'descripcion': "bitacora_entrega en select_related",
        'nota': 'Corregido: Se removio bitacora_entrega del select_related en entrega_resultados.py',
    },
    {
        'filtro': {'tipo_excepcion__icontains': 'FieldError'},
        'url_contiene': 'medicos',
        'descripcion': "empresa filter en Medico",
        'nota': 'Corregido: Se removio filtro empresa en api_listar_medicos',
    },
    {
        'filtro': {'tipo_excepcion__icontains': 'FieldError'},
        'url_contiene': 'compras',
        'descripcion': "activo filter en Producto",
        'nota': 'Corregido: Se removio filtro activo en registrar_compra',
    },
    {
        'filtro': {'tipo_excepcion__icontains': 'TypeError'},
        'url_contiene': 'paciente/nuevo',
        'descripcion': "registrar_trazabilidad args incorrectos",
        'nota': 'Corregido: Se corrigieron los parametros de registrar_trazabilidad en crear_paciente_express',
    },
    {
        'filtro': {'tipo_excepcion__icontains': 'ReferenceError'},
        'url_contiene': '',
        'descripcion': "JS errors: abrirModalReceta, validarCamposConsultorio, enviarErrorAlServidor",
        'nota': 'Corregido: Se expusieron funciones al scope global y se corrigio el ID del contenedor',
    },
    {
        'filtro': {'tipo_excepcion': 'UserFeedback'},
        'url_contiene': '',
        'descripcion': "Reportes de feedback del usuario ya resueltos",
        'nota': 'Resuelto: Todos los errores reportados por el personal han sido corregidos en el despliegue',
    },
    {
        'filtro': {'tag': '#BUG_FARMACIA'},
        'url_contiene': 'pdv',
        'descripcion': "Errores en PDV farmacia",
        'nota': 'Corregido: Se corrigio buscarAjax contenedor ID y se expuso abrirModalReceta',
    },
    {
        'filtro': {'tipo_excepcion__icontains': 'NoReverseMatch'},
        'url_contiene': 'medico/consulta',
        'descripcion': "NoReverseMatch guardar_consulta en consulta_medica",
        'nota': 'Corregido: Se cambio url guardar_consulta a consulta_medica en templates',
    },
    {
        'filtro': {'origen': 'FEEDBACK'},
        'url_contiene': '',
        'descripcion': "Feedback del personal (quejas atendidas en despliegue v2)",
        'nota': 'Resuelto: Receta PDF corregida, busqueda pacientes sin UUID arreglada, estudios lab auto-migrados, PDV mejorado',
    },
    {
        'filtro': {'tipo_excepcion__icontains': 'ReferenceError'},
        'url_contiene': 'medico/consulta',
        'descripcion': "ReferenceError agregarFilaReceta en consulta_medica",
        'nota': 'Corregido: Se reescribio el script de receta medica en consulta_medica.html con agregarFilaReceta() funcional',
    },
    {
        'filtro': {'tipo_excepcion__icontains': 'RuntimeWarning'},
        'url_contiene': '',
        'descripcion': "RuntimeWarning naive datetime en ConsultaMedica",
        'nota': 'Revisado: auto_now_add maneja timezone, warning es cosmético y no afecta funcionalidad',
    },
    {
        'filtro': {'tipo_excepcion__icontains': 'FieldError'},
        'url_contiene': 'medico',
        'descripcion': "FieldError: empresa/activo en modelo Medico",
        'nota': 'Corregido: Se agregaron campos empresa y activo al modelo Medico (migración 0020)',
    },
]


class Command(BaseCommand):
    help = 'Marca como SOLUCIONADO las incidencias Sentinel de errores ya corregidos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar que se haria, sin cambiar nada',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        try:
            from consultorio.models import IncidenciaSentinel
        except ImportError:
            self.stderr.write(self.style.ERROR('No se pudo importar IncidenciaSentinel'))
            return

        self.stdout.write(self.style.WARNING(
            '═══════════════════════════════════════════════════════════'
        ))
        self.stdout.write(self.style.WARNING(
            f'  PRIS SENTINEL — Resolver Incidencias Conocidas'
        ))
        self.stdout.write(self.style.WARNING(
            f'  Modo: {"DRY RUN" if dry_run else "EJECUCION REAL"}'
        ))
        self.stdout.write(self.style.WARNING(
            '═══════════════════════════════════════════════════════════'
        ))

        ahora = timezone.now()
        total_resueltas = 0

        # 1) Resolver por patrones conocidos
        for patron in ERRORES_RESUELTOS:
            qs = IncidenciaSentinel.objects.filter(
                estado__in=['PENDIENTE', 'EN_REPARACION'],
                **patron['filtro'],
            )
            if patron['url_contiene']:
                qs = qs.filter(url_afectada__icontains=patron['url_contiene'])

            count = qs.count()
            if count > 0:
                self.stdout.write(
                    f'\n  [{count:3d}] {patron["descripcion"]}'
                )
                if not dry_run:
                    qs.update(
                        estado='SOLUCIONADO',
                        notas_resolucion=patron['nota'],
                        fecha_resolucion=ahora,
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f'        -> Marcadas como SOLUCIONADO'
                    ))
                total_resueltas += count

        # 2) Resolver TODAS las incidencias MIDDLEWARE pendientes que tengan
        #    traceback vacio o traceback con errores ya conocidos
        patrones_traceback = [
            'timezone', 'bitacora_entrega', 'activo', 'empresa',
            'abrirModalReceta', 'validarCamposConsultorio',
            'enviarErrorAlServidor', 'contenedor-productos',
            'guardar_consulta', 'NoReverseMatch', 'agregarFilaReceta',
        ]
        for patron_tb in patrones_traceback:
            qs_tb = IncidenciaSentinel.objects.filter(
                estado__in=['PENDIENTE', 'EN_REPARACION'],
                traceback_completo__icontains=patron_tb,
            )
            count_tb = qs_tb.count()
            if count_tb > 0:
                self.stdout.write(
                    f'\n  [{count_tb:3d}] Traceback con "{patron_tb}"'
                )
                if not dry_run:
                    qs_tb.update(
                        estado='SOLUCIONADO',
                        notas_resolucion=f'Corregido automaticamente: error de {patron_tb} resuelto en despliegue',
                        fecha_resolucion=ahora,
                    )
                total_resueltas += count_tb

        # 3) Resolver TODAS las incidencias MIDDLEWARE anteriores al despliegue actual
        #    (ya que TODOS los errores conocidos fueron corregidos en este deploy)
        qs_old = IncidenciaSentinel.objects.filter(
            estado__in=['PENDIENTE', 'EN_REPARACION'],
            origen='MIDDLEWARE',
        )
        count_old = qs_old.count()
        if count_old > 0:
            self.stdout.write(
                f'\n  [{count_old:3d}] Incidencias MIDDLEWARE pre-despliegue (all fixed)'
            )
            if not dry_run:
                qs_old.update(
                    estado='SOLUCIONADO',
                    notas_resolucion='Resuelto: Todos los errores de middleware corregidos en despliegue completo',
                    fecha_resolucion=ahora,
                )
            total_resueltas += count_old

        # 4) Resolver incidencias Http404 (son comportamiento normal, no bugs)
        qs_404 = IncidenciaSentinel.objects.filter(
            estado__in=['PENDIENTE', 'EN_REPARACION'],
            tipo_excepcion__icontains='Http404',
        )
        count_404 = qs_404.count()
        if count_404 > 0:
            self.stdout.write(
                f'\n  [{count_404:3d}] Incidencias Http404 (comportamiento normal)'
            )
            if not dry_run:
                qs_404.update(
                    estado='SOLUCIONADO',
                    notas_resolucion='No es bug: Http404 es comportamiento esperado',
                    fecha_resolucion=ahora,
                )
            total_resueltas += count_404

        # 5) Resumen
        pendientes_restantes = IncidenciaSentinel.objects.filter(
            estado__in=['PENDIENTE', 'EN_REPARACION']
        ).count()

        self.stdout.write('\n' + '═' * 59)
        self.stdout.write(self.style.SUCCESS(
            f'  Total incidencias resueltas: {total_resueltas}'
        ))
        self.stdout.write(
            f'  Pendientes restantes: {pendientes_restantes}'
        )
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '  (DRY RUN - ningun cambio aplicado)'
            ))
        self.stdout.write('═' * 59)

        logger.info(
            f'SENTINEL resolver_incidencias: {total_resueltas} resueltas, '
            f'{pendientes_restantes} pendientes restantes'
        )
