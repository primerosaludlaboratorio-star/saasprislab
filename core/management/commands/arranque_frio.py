"""
Protocolo de Arranque en Frío — PRISLAB v5.0
============================================
Uso:
    # Solo ver qué se borraría (modo simulación):
    python manage.py arranque_frio

    # Borrar todos los datos de prueba:
    python manage.py arranque_frio --confirmar

    # También configurar desde qué número arrancan los folios:
    python manage.py arranque_frio --confirmar --folio-consulta 15420 --folio-venta 8300

    # Solo configurar folios sin limpiar datos:
    python manage.py arranque_frio --solo-folios --folio-consulta 15420

REGLA DE ORO:
    - Usuarios, catálogos de estudios y productos NO se borran nunca.
    - Pacientes con nombre que contenga 'prueba', 'test', 'demo', 'dummy' se borran
      solo con --incluir-pacientes-prueba.
    - Solo se borran pacientes reales si se usa --todos-los-pacientes (acción extrema).
"""
from django.core.management.base import BaseCommand
from django.db import transaction
import logging


class Command(BaseCommand):
    help = 'Protocolo de arranque en frío: limpia datos de prueba y configura folios iniciales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Ejecuta la limpieza real (sin este flag solo muestra qué se borraría)',
        )
        parser.add_argument(
            '--incluir-pacientes-prueba',
            action='store_true',
            help='También borra pacientes con nombre tipo "Prueba", "Test", "Demo", "Dummy"',
        )
        parser.add_argument(
            '--todos-los-pacientes',
            action='store_true',
            help='PELIGROSO: borra TODOS los pacientes. Solo para reset total de entorno.',
        )
        parser.add_argument(
            '--solo-folios',
            action='store_true',
            help='Solo configura folios iniciales, no borra datos',
        )
        parser.add_argument(
            '--folio-consulta',
            type=int,
            default=None,
            help='Número desde el que arrancan los folios de consulta (ej: 15420)',
        )
        parser.add_argument(
            '--folio-venta',
            type=int,
            default=None,
            help='Número desde el que arrancan los folios de venta/farmacia',
        )
        parser.add_argument(
            '--folio-orden',
            type=int,
            default=None,
            help='Número desde el que arrancan los folios de órdenes de laboratorio',
        )

    def handle(self, *args, **options):
        confirmar = options['confirmar']
        solo_folios = options['solo_folios']
        incluir_prueba = options['incluir_pacientes_prueba']
        todos_pacientes = options['todos_los_pacientes']

        self.stdout.write(self.style.MIGRATE_HEADING('\n╔══════════════════════════════════════════════╗'))
        self.stdout.write(self.style.MIGRATE_HEADING('║    PRISLAB v5 — PROTOCOLO ARRANQUE EN FRÍO  ║'))
        self.stdout.write(self.style.MIGRATE_HEADING('╚══════════════════════════════════════════════╝\n'))

        if not confirmar and not solo_folios:
            self.stdout.write(self.style.WARNING(
                '  MODO SIMULACIÓN — No se modificará nada.\n'
                '  Use --confirmar para ejecutar la limpieza real.\n'
            ))

        if not solo_folios:
            self._limpiar_datos(confirmar, incluir_prueba, todos_pacientes)

        if any([options.get('folio_consulta'), options.get('folio_venta'), options.get('folio_orden')]):
            self._configurar_folios(
                confirmar or solo_folios,
                options.get('folio_consulta'),
                options.get('folio_venta'),
                options.get('folio_orden'),
            )

        self.stdout.write(self.style.SUCCESS('\n✓ Protocolo de arranque en frío completado.\n'))

    # ─── Limpieza de datos ────────────────────────────────────────────────────

    def _limpiar_datos(self, confirmar, incluir_prueba, todos_pacientes):
        self.stdout.write(self.style.MIGRATE_LABEL('\n── INVENTARIO DE DATOS A LIMPIAR ──'))

        try:
            from core.models import (
                OrdenDeServicio, DetalleOrden, ResultadoParametro,
                Venta, DetalleVenta, Pago, PagoOrden,
                TomaMuestra, EnvioMaquila, BitacoraConsultaIA,
                CorteTurno,
            )
        except ImportError as e:
            self.stdout.write(self.style.WARNING(f'  Algunos modelos no disponibles (normal): {e}'))
            from core.models import OrdenDeServicio, DetalleOrden, Venta, DetalleVenta, Pago
            PagoOrden = TomaMuestra = EnvioMaquila = BitacoraConsultaIA = CorteTurno = None
            ResultadoParametro = None

        from core.models import Paciente

        # Intentar importar modelos opcionales del consultorio
        ConsultaMedica = Receta = CertificadoMedico = SignosVitales = None
        try:
            from core.models import ConsultaMedica, Receta, CertificadoMedico
        except ImportError:
            pass
        try:
            from consultorio.models import ConsultaMedica as CM, Receta as R, CertificadoMedico as CM2
            if ConsultaMedica is None:
                ConsultaMedica = CM
            if Receta is None:
                Receta = R
            if CertificadoMedico is None:
                CertificadoMedico = CM2
        except ImportError:
            pass

        conteos = {
            'Órdenes de Laboratorio': OrdenDeServicio.objects.count(),
            'Detalles de Orden': DetalleOrden.objects.count(),
            'Ventas Farmacia': Venta.objects.count(),
            'Detalles de Venta': DetalleVenta.objects.count(),
            'Pagos': Pago.objects.count(),
        }

        if PagoOrden:
            conteos['Pagos de Orden'] = PagoOrden.objects.count()
        if TomaMuestra:
            conteos['Tomas de Muestra'] = TomaMuestra.objects.count()
        if EnvioMaquila:
            conteos['Envíos Maquila'] = EnvioMaquila.objects.count()
        if BitacoraConsultaIA:
            conteos['Bitácoras IA'] = BitacoraConsultaIA.objects.count()
        if CorteTurno:
            conteos['Cortes de Turno'] = CorteTurno.objects.count()
        if ConsultaMedica:
            conteos['Consultas Médicas'] = ConsultaMedica.objects.count()
        if Receta:
            conteos['Recetas'] = Receta.objects.count()
        if CertificadoMedico:
            conteos['Certificados'] = CertificadoMedico.objects.count()

        # Pacientes de prueba
        pacientes_prueba = Paciente.objects.filter(
            nombre_completo__iregex=r'(?i)(prueba|test|demo|dummy|ejemplo|ficticio)'
        )
        conteos[f'Pacientes de PRUEBA ({"se borrarán" if incluir_prueba else "NO se borrarán"})'] = (
            pacientes_prueba.count()
        )

        self.stdout.write(self.style.WARNING('\n  DATOS QUE SE BORRARÁN:'))
        total = 0
        for nombre, cantidad in conteos.items():
            if cantidad > 0:
                self.stdout.write(f'    {nombre:40s} {cantidad:>6,}')
                total += cantidad

        self.stdout.write(self.style.WARNING(f'\n  Total de registros a eliminar: {total:,}'))

        # Datos que se conservan
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.stdout.write(self.style.SUCCESS('\n  DATOS QUE SE CONSERVAN SIEMPRE:'))
        self.stdout.write(f'    {"Usuarios del sistema":40s} {User.objects.count():>6,}')
        self.stdout.write(f'    {"Estudios de laboratorio":40s} {self._contar("laboratorio.models.Estudio"):>6,}')
        self.stdout.write(f'    {"Productos de farmacia":40s} {self._contar("core.models.Producto"):>6,}')
        self.stdout.write(f'    {"Pacientes reales":40s} {Paciente.objects.exclude(nombre_completo__iregex=r"(?i)(prueba|test|demo|dummy)").count():>6,}')

        if not confirmar:
            self.stdout.write(self.style.WARNING(
                '\n  ─── Ejecuta con --confirmar para proceder ───'
            ))
            return

        self.stdout.write(self.style.ERROR(
            '\n  ⚠  INICIANDO LIMPIEZA — Esta operación NO se puede deshacer\n'
        ))

        with transaction.atomic():
            # Orden correcto respetando FK (hijos antes que padres)
            self._borrar(ResultadoParametro, 'Resultados de parámetros') if ResultadoParametro else None
            self._borrar(ConsultaMedica, 'Consultas médicas')
            self._borrar(Receta, 'Recetas')
            self._borrar(CertificadoMedico, 'Certificados médicos')
            self._borrar(TomaMuestra, 'Tomas de muestra')
            self._borrar(EnvioMaquila, 'Envíos maquila')
            self._borrar(BitacoraConsultaIA, 'Bitácoras IA')
            self._borrar(DetalleOrden, 'Detalles de orden')
            self._borrar(PagoOrden, 'Pagos de orden')
            self._borrar(OrdenDeServicio, 'Órdenes de laboratorio')
            self._borrar(DetalleVenta, 'Detalles de venta')
            self._borrar(Pago, 'Pagos de venta')
            self._borrar(CorteTurno, 'Cortes de turno')
            self._borrar(Venta, 'Ventas')

            if incluir_prueba:
                n = pacientes_prueba.count()
                pacientes_prueba.delete()
                self.stdout.write(self.style.SUCCESS(f'  [OK] Pacientes de prueba eliminados: {n}'))
            elif todos_pacientes:
                n = Paciente.objects.count()
                Paciente.objects.all().delete()
                self.stdout.write(self.style.ERROR(f'  [!!] TODOS los pacientes eliminados: {n}'))

        self.stdout.write(self.style.SUCCESS('\n  ✓ Limpieza completada. Catálogos y usuarios intactos.'))

    # ─── Configuración de folios iniciales ────────────────────────────────────

    def _configurar_folios(self, ejecutar, folio_consulta, folio_venta, folio_orden):
        self.stdout.write(self.style.MIGRATE_LABEL('\n── CONFIGURACIÓN DE FOLIOS INICIALES ──'))

        if not ejecutar:
            self.stdout.write(self.style.WARNING('  (Modo simulación — no se guardarán cambios)'))

        configuraciones = []
        if folio_consulta:
            configuraciones.append(('folio_inicio_consulta', folio_consulta, 'Folio inicial de Consultas'))
        if folio_venta:
            configuraciones.append(('folio_inicio_venta', folio_venta, 'Folio inicial de Ventas/Farmacia'))
        if folio_orden:
            configuraciones.append(('folio_inicio_orden', folio_orden, 'Folio inicial de Órdenes de Lab'))

        for clave, valor, descripcion in configuraciones:
            self.stdout.write(f'  {descripcion}: {valor:,}')
            if ejecutar:
                try:
                    from core.models import ConfiguracionSistema
                    obj, created = ConfiguracionSistema.objects.get_or_create(
                        clave=clave,
                        defaults={'valor': str(valor), 'descripcion': descripcion}
                    )
                    if not created:
                        obj.valor = str(valor)
                        obj.save()
                    action = 'Creado' if created else 'Actualizado'
                    self.stdout.write(self.style.SUCCESS(f'    [{action}] {clave} = {valor}'))
                except Exception as e:
                    logging.getLogger(__name__).exception("Error inesperado en _configurar_folios (arranque_frio.py)")
                    self.stdout.write(self.style.WARNING(
                        f'    ConfiguracionSistema no disponible ({e}).\n'
                        f'    Agrega manualmente: {clave}={valor} en el panel de administración.'
                    ))

    # ─── Utilidades ──────────────────────────────────────────────────────────

    def _borrar(self, model_class, nombre):
        if model_class is None:
            return
        try:
            n = model_class.objects.count()
            if n > 0:
                model_class.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'  [OK] {nombre}: {n:,} eliminados'))
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _borrar (arranque_frio.py)")
            self.stdout.write(self.style.ERROR(f'  [ERROR] {nombre}: {e}'))

    def _contar(self, model_path):
        try:
            app, model = model_path.rsplit('.', 1)
            module = __import__(app, fromlist=[model])
            klass = getattr(module, model)
            return klass.objects.count()
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en _contar (arranque_frio.py)")
            return 0