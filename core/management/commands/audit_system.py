"""
PRISLAB SENTINEL 2.0 - Comando de Auditoria de Sistema Completa
================================================================
python manage.py audit_system

Revisa la integridad de TODAS las conexiones, servicios y datos:
- Base de datos (PostgreSQL / SQLite)
- Almacenamiento externo / Drive
- APIs externas (Gemini, GitHub, Email)
- Integridad de modelos criticos
- Estado de archivos estaticos y templates
- Latencias de consultas clave
- Estado de migraciones pendientes
"""

import time
import logging
from io import StringIO

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection

logger = logging.getLogger('sentinel')


class Command(BaseCommand):
    help = 'SENTINEL 2.0: Auditoria completa del sistema PRISLAB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--details',
            action='store_true',
            dest='verbose',
            help='Mostrar detalles completos de cada check',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        self.stdout.write(self.style.SUCCESS(
            '\n' + '=' * 70 +
            '\n  PRISLAB SENTINEL 2.0 - AUDITORIA DE SISTEMA' +
            '\n' + '=' * 70
        ))

        resultados = []
        inicio_total = time.time()

        # ── 1. BASE DE DATOS ──
        resultados.append(self._check_database(verbose))

        # ── 2. MIGRACIONES PENDIENTES ──
        resultados.append(self._check_migrations(verbose))

        # ── 3. ALMACENAMIENTO EXTERNO ──
        resultados.append(self._check_gcs(verbose))

        # ── 4. API GEMINI (IA) ──
        resultados.append(self._check_gemini(verbose))

        # ── 5. EMAIL ──
        resultados.append(self._check_email(verbose))

        # ── 6. INTEGRIDAD DE MODELOS ──
        resultados.append(self._check_models_integrity(verbose))

        # ── 7. TEMPLATES CRITICOS ──
        resultados.append(self._check_templates(verbose))

        # ── 8. LATENCIA DE QUERIES ──
        resultados.append(self._check_query_latency(verbose))

        # ── 9. SERVICIOS INTERNOS ──
        resultados.append(self._check_internal_services(verbose))

        # ── 10. PARIDAD LEGADO VS SAAS ──
        resultados.append(self._check_migration_readiness(verbose))

        # ── RESUMEN ──
        elapsed = time.time() - inicio_total
        ok_count = sum(1 for r in resultados if r['status'] == 'OK')
        warn_count = sum(1 for r in resultados if r['status'] == 'WARN')
        fail_count = sum(1 for r in resultados if r['status'] == 'FAIL')

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(f'  RESULTADO: {ok_count} OK | {warn_count} WARN | {fail_count} FAIL')
        self.stdout.write(f'  Tiempo total: {elapsed:.2f}s')
        self.stdout.write('=' * 70)

        if fail_count == 0 and warn_count == 0:
            self.stdout.write(self.style.SUCCESS(
                '\n  SISTEMA PRISLAB OPERATIVO AL 100% SIN ADVERTENCIAS.\n'
            ))
        elif fail_count == 0:
            self.stdout.write(self.style.WARNING(
                f'\n  SISTEMA OPERATIVO CON {warn_count} ADVERTENCIA(S) NO BLOQUEANTE(S).\n'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'\n  ATENCION: {fail_count} componente(s) requieren revision.\n'
            ))

        # Registrar en AuditLog
        try:
            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='VIEW',
                modelo='Sistema',
                objeto_id='audit_system',
                datos_nuevos={
                    'ok': ok_count,
                    'warn': warn_count,
                    'fail': fail_count,
                    'elapsed_seconds': round(elapsed, 2),
                    'checks': [r['name'] for r in resultados],
                },
            )
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en handle (audit_system.py)")
            pass

    def _print_check(self, name, status, detail=''):
        icons = {'OK': 'OK', 'WARN': 'WARN', 'FAIL': 'FAIL'}
        styles = {
            'OK': self.style.SUCCESS,
            'WARN': self.style.WARNING,
            'FAIL': self.style.ERROR,
        }
        icon = icons.get(status, '?')
        style = styles.get(status, self.style.NOTICE)
        line = f'  [{icon}] {name}'
        if detail:
            line += f' — {detail}'
        self.stdout.write(style(line))
        return {'name': name, 'status': status, 'detail': detail}

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CHECKS INDIVIDUALES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _check_database(self, verbose):
        self.stdout.write('\n[BASE DE DATOS]')
        try:
            t0 = time.time()
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            latency = (time.time() - t0) * 1000
            engine = settings.DATABASES['default']['ENGINE']
            db_name = settings.DATABASES['default'].get('NAME', 'unknown')
            detail = f'{engine.split(".")[-1]} | {db_name} | {latency:.1f}ms'
            if latency > 500:
                return self._print_check('Conexion DB', 'WARN', detail + ' (lenta)')
            return self._print_check('Conexion DB', 'OK', detail)
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _check_database (audit_system.py)")
            return self._print_check('Conexion DB', 'FAIL', str(e))

    def _check_migrations(self, verbose):
        try:
            from django.core.management import call_command
            out = StringIO()
            call_command('showmigrations', '--plan', stdout=out)
            content = out.getvalue()
            pending = [l for l in content.split('\n') if l.strip().startswith('[ ]')]
            if pending:
                return self._print_check(
                    'Migraciones', 'WARN',
                    f'{len(pending)} pendiente(s)'
                )
            return self._print_check('Migraciones', 'OK', 'Todas aplicadas')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _check_migrations (audit_system.py)")
            return self._print_check('Migraciones', 'WARN', str(e))

    def _check_gcs(self, verbose):
        self.stdout.write('\n[ALMACENAMIENTO EXTERNO]')
        try:
            bucket_name = getattr(settings, 'GS_BUCKET_NAME', '')
            if not bucket_name:
                return self._print_check('GCS Bucket', 'WARN', 'No configurado (local)')

            from google.cloud import storage
            client = storage.Client()
            bucket = client.get_bucket(bucket_name)
            blobs = list(bucket.list_blobs(max_results=1))
            return self._print_check(
                'GCS Bucket', 'OK',
                f'"{bucket_name}" accesible ({len(blobs)}+ objetos)'
            )
        except ImportError:
            return self._print_check('GCS Bucket', 'WARN', 'google-cloud-storage no instalado')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _check_gcs (audit_system.py)")
            return self._print_check('GCS Bucket', 'FAIL', str(e)[:100])

    def _check_gemini(self, verbose):
        self.stdout.write('\n[APIS EXTERNAS]')
        try:
            api_key = getattr(settings, 'GOOGLE_API_KEY', '')
            if not api_key:
                return self._print_check('Gemini API', 'WARN', 'GOOGLE_API_KEY no configurada')

            from core.utils.gemini_client import test_gemini_connection
            result = test_gemini_connection()
            if result.get('success'):
                return self._print_check('Gemini API', 'OK', result.get('message', ''))
            return self._print_check('Gemini API', 'FAIL', result.get('message', ''))
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _check_gemini (audit_system.py)")
            return self._print_check('Gemini API', 'FAIL', str(e)[:100])

    def _check_email(self, verbose):
        try:
            backend = getattr(settings, 'EMAIL_BACKEND', '')
            director = getattr(settings, 'DIRECTOR_EMAIL', '')
            if 'console' in backend.lower():
                return self._print_check('Email', 'WARN', 'Backend consola (no envia)')
            if not director:
                return self._print_check('Email', 'WARN', 'DIRECTOR_EMAIL no configurado')
            return self._print_check('Email', 'OK', f'SMTP → {director}')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _check_email (audit_system.py)")
            return self._print_check('Email', 'FAIL', str(e)[:100])

    def _check_models_integrity(self, verbose):
        self.stdout.write('\n[INTEGRIDAD DE DATOS]')
        checks = []
        try:
            from core.models import Empresa, Paciente, OrdenDeServicio, Producto
            emp_count = Empresa.objects.count()
            pac_count = Paciente.objects.count()
            ord_count = OrdenDeServicio.objects.count()
            prod_count = Producto.objects.count()
            detail = f'Empresas:{emp_count} Pacientes:{pac_count} Ordenes:{ord_count} Productos:{prod_count}'
            checks.append(self._print_check('Modelos Core', 'OK', detail))
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _check_models_integrity (audit_system.py)")
            checks.append(self._print_check('Modelos Core', 'FAIL', str(e)[:100]))

        try:
            from laboratorio.models import Estudio, InsumoEstudio
            est_count = Estudio.objects.count()
            ins_count = InsumoEstudio.objects.count()
            detail = f'Estudios:{est_count} Insumos vinculados:{ins_count}'
            checks.append(self._print_check('Modelos Lab', 'OK', detail))
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _check_models_integrity (audit_system.py)")
            checks.append(self._print_check('Modelos Lab', 'WARN', str(e)[:100]))

        try:
            from core.models import AuditLog
            from consultorio.models import IncidenciaSentinel
            al_count = AuditLog.objects.count()
            is_count = IncidenciaSentinel.objects.count()
            detail = f'AuditLogs:{al_count} Incidencias Sentinel:{is_count}'
            checks.append(self._print_check('Sentinel Data', 'OK', detail))
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _check_models_integrity (audit_system.py)")
            checks.append(self._print_check('Sentinel Data', 'WARN', str(e)[:100]))

        return checks[-1] if checks else self._print_check('Integridad', 'WARN', 'Sin datos')

    def _check_templates(self, verbose):
        self.stdout.write('\n[TEMPLATES CRITICOS]')
        import os
        templates_criticos = [
            'core/ia_dashboard.html',
            'core/error_amable.html',
            'core/laboratorio/monitor_produccion.html',
            'core/corte_caja_dia.html',
            'base.html',
        ]
        missing = []
        for tpl in templates_criticos:
            found = False
            for tpl_dir_config in settings.TEMPLATES:
                for d in tpl_dir_config.get('DIRS', []):
                    if os.path.exists(os.path.join(d, tpl)):
                        found = True
                        break
            # Also check app template dirs
            if not found:
                for app in settings.INSTALLED_APPS:
                    app_name = app.split('.')[-1]
                    possible = os.path.join(
                        settings.BASE_DIR, app_name, 'templates', tpl
                    )
                    if os.path.exists(possible):
                        found = True
                        break
            if not found:
                missing.append(tpl)

        if missing:
            return self._print_check('Templates', 'WARN', f'Faltantes: {", ".join(missing)}')
        return self._print_check('Templates', 'OK', f'{len(templates_criticos)} verificados')

    def _check_query_latency(self, verbose):
        self.stdout.write('\n[LATENCIA DE QUERIES]')
        try:
            from core.models import OrdenDeServicio
            t0 = time.time()
            OrdenDeServicio.objects.filter(
                estado_clinico='PENDIENTE_TOMA'
            ).count()
            lat = (time.time() - t0) * 1000

            if lat > 300:
                return self._print_check('Query Ordenes', 'WARN', f'{lat:.1f}ms (lenta)')
            return self._print_check('Query Ordenes', 'OK', f'{lat:.1f}ms')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _check_query_latency (audit_system.py)")
            return self._print_check('Query Ordenes', 'FAIL', str(e)[:100])

    def _check_internal_services(self, verbose):
        self.stdout.write('\n[SERVICIOS INTERNOS]')
        services_ok = []
        services_fail = []

        # Motor PDF
        try:
            from core.services.motor_reportes_lab import generar_reporte_pdf
            services_ok.append('PDF')
        except ImportError:
            services_fail.append('PDF')

        # Motor Recetas
        try:
            from core.services.motor_recetas import generar_receta_pdf
            services_ok.append('Recetas')
        except ImportError:
            services_fail.append('Recetas')

        # Audit Service
        try:
            from core.services.audit_service import registrar_auditoria
            services_ok.append('AuditService')
        except ImportError:
            services_fail.append('AuditService')

        # IA Interpretacion
        try:
            from core.services.interpretacion_ia import generar_resumen_bienestar
            services_ok.append('IA-Bienestar')
        except ImportError:
            services_fail.append('IA-Bienestar')

        # GitHub Reporter
        try:
            from core.services.github_reporter import crear_github_issue
            services_ok.append('GitHub')
        except ImportError:
            services_fail.append('GitHub')

        detail = f'OK: {", ".join(services_ok)}'
        if services_fail:
            detail += f' | FAIL: {", ".join(services_fail)}'
            return self._print_check('Servicios', 'WARN', detail)
        return self._print_check('Servicios', 'OK', detail)

    def _check_migration_readiness(self, verbose):
        self.stdout.write('\n[PARIDAD LEGADO VS SAAS]')
        try:
            from core.services.migration_readiness import summarize_migration_readiness

            data = summarize_migration_readiness()
            summary = data.get('summary', {})
            ok = summary.get('OK', 0)
            warn = summary.get('WARN', 0)
            fail = summary.get('FAIL', 0)
            detail = f'OK:{ok} WARN:{warn} FAIL:{fail}'
            if fail > 0:
                return self._print_check('Paridad Legacy/SaaS', 'WARN', detail)
            if warn > 0:
                return self._print_check('Paridad Legacy/SaaS', 'WARN', detail)
            return self._print_check('Paridad Legacy/SaaS', 'OK', detail)
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _check_migration_readiness (audit_system.py)")
            return self._print_check('Paridad Legacy/SaaS', 'FAIL', str(e)[:100])