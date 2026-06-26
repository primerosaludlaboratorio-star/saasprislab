"""
PRIS-JARVIS — Gemini Bridge (Auditoría Externa Tier 3)
======================================================
Genera un paquete de auditoría ultra-comprimido para análisis externo con Gemini.
SIN datos sensibles de pacientes (anonimizado).
Listo para que el Químico lo copie y comparta con su asistente IA.

Uso:
    python manage.py generar_auditoria_gemini
    python manage.py generar_auditoria_gemini --formato json
    python manage.py generar_auditoria_gemini --salida auditoria_20260228.md
"""
import json
import logging
import os
import platform
from datetime import datetime, timedelta
from io import StringIO

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

logger = logging.getLogger('core')


class Command(BaseCommand):
    help = 'Genera paquete de auditoría para análisis externo con Gemini (anonimizado)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--formato',
            choices=['md', 'json'],
            default='md',
            help='Formato de salida: md (Markdown) o json',
        )
        parser.add_argument(
            '--salida',
            type=str,
            default='',
            help='Ruta del archivo de salida (default: auditoria_gemini_YYYYMMDD_HHMM.md)',
        )
        parser.add_argument(
            '--errores',
            type=int,
            default=50,
            help='Cantidad de errores críticos a incluir (default: 50)',
        )

    def handle(self, *args, **options):
        formato = options['formato']
        salida = options['salida']
        n_errores = min(max(options['errores'], 1), 100)

        self.stdout.write(self.style.WARNING('Generando auditoria Gemini Bridge...'))

        data = self._recopilar_todo(n_errores)

        if not salida:
            ts = datetime.now().strftime('%Y%m%d_%H%M')
            salida = f'auditoria_gemini_{ts}.{formato}'

        if formato == 'json':
            contenido = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        else:
            contenido = self._formatear_markdown(data)

        with open(salida, 'w', encoding='utf-8') as f:
            f.write(contenido)

        self.stdout.write(self.style.SUCCESS(f'Auditoria guardada: {salida}'))
        self.stdout.write(f'  Tamanio: {len(contenido)} caracteres')

    def _recopilar_todo(self, n_errores: int) -> dict:
        """Recopila todas las métricas sin datos sensibles."""
        return {
            "meta": {
                "timestamp": timezone.now().isoformat(),
                "sistema": "PRISLAB v5",
                "entorno": "produccion" if not settings.DEBUG else "desarrollo",
            },
            "sistema": self._estadisticas_sistema(),
            "base_datos": self._metricas_bd(),
            "errores_criticos": self._errores_sentinel(n_errores),
            "drive": self._estado_drive(),
        }

    def _estadisticas_sistema(self) -> dict:
        """CPU/RAM y datos del host (sin info sensible)."""
        out = {
            "plataforma": platform.system(),
            "python": platform.python_version(),
            "debug": settings.DEBUG,
        }
        try:
            import psutil
            out["cpu_percent"] = psutil.cpu_percent(interval=1)
            out["memoria_total_mb"] = round(psutil.virtual_memory().total / (1024 * 1024), 1)
            out["memoria_disponible_mb"] = round(psutil.virtual_memory().available / (1024 * 1024), 1)
            out["memoria_usada_percent"] = psutil.virtual_memory().percent
        except ImportError:
            out["psutil"] = "No instalado (pip install psutil para metricas CPU/RAM)"
        return out

    def _metricas_bd(self) -> dict:
        """Tiempos de query y estado de conexión."""
        out = {"engine": settings.DATABASES.get("default", {}).get("ENGINE", "?")}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                out["conexion"] = "OK"
                if connection.connection:
                    out["conexion_id"] = id(connection.connection)
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _metricas_bd (generar_auditoria_gemini.py)")
            out["conexion"] = "ERROR"
            out["error"] = str(e)[:200]

        # Queries lentos: Django no los guarda por defecto; reportamos que no hay log
        out["queries_lentos"] = "Sin registro (habilitar django.db.backends en LOGGING para capturar)"

        return out

    def _errores_sentinel(self, limite: int) -> list:
        """Últimos N errores críticos (tracebacks anonimizados)."""
        try:
            from consultorio.models import IncidenciaSentinel
            qs = IncidenciaSentinel.objects.filter(
                severidad__in=['CRITICA', 'ALTA']
            ).order_by('-fecha_creacion')[:limite]
            items = []
            for inc in qs:
                tb = (inc.traceback_completo or "")[:2000]
                # Anonimizar posibles IDs/emails en traceback
                tb = tb.replace("@", "[at]")
                items.append({
                    "id": inc.id,
                    "fecha": timezone.localtime(inc.fecha_creacion).isoformat() if inc.fecha_creacion else None,
                    "tipo": inc.tipo_excepcion or "",
                    "url": (inc.url_afectada or "")[:200],
                    "codigo_http": inc.codigo_http,
                    "severidad": inc.severidad,
                    "traceback": tb[:1500],
                })
            return items
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _errores_sentinel (generar_auditoria_gemini.py)")
            return [{"error_import": str(e)[:200]}]

    def _estado_drive(self) -> dict:
        """Estado de conexión a Google Drive."""
        out = {}
        try:
            default_storage = getattr(settings, 'DEFAULT_FILE_STORAGE', '')
            out["storage_backend"] = str(default_storage)
            out["drive_folder_id"] = bool(getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', None))
            if hasattr(settings, '_DRIVE_STORAGE_ACTIVO'):
                out["drive_activo"] = getattr(settings, '_DRIVE_STORAGE_ACTIVO', False)
            else:
                out["drive_activo"] = "GoogleDriveStorage" in str(default_storage)
            # Test rápido de escritura (opcional, puede fallar si no hay creds)
            try:
                from django.core.files.base import ContentFile
                from django.core.files.storage import default_storage as storage
                name = f"audit_test_{datetime.now().strftime('%Y%m%d%H%M')}.txt"
                storage.save(name, ContentFile(b"test"))
                storage.delete(name)
                out["test_escritura"] = "OK"
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en _estado_drive (generar_auditoria_gemini.py)")
                out["test_escritura"] = str(e)[:150]
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _estado_drive (generar_auditoria_gemini.py)")
            out["error"] = str(e)[:200]
        return out

    def _formatear_markdown(self, data: dict) -> str:
        """Convierte el dict a Markdown legible."""
        buf = StringIO()
        buf.write("# PRISLAB - Auditoria para Gemini (Tier 3)\n\n")
        buf.write(f"**Generado:** {data['meta']['timestamp']}\n")
        buf.write(f"**Entorno:** {data['meta']['entorno']}\n\n")

        buf.write("## Sistema\n")
        for k, v in data["sistema"].items():
            buf.write(f"- {k}: {v}\n")

        buf.write("\n## Base de datos\n")
        for k, v in data["base_datos"].items():
            buf.write(f"- {k}: {v}\n")

        buf.write("\n## Google Drive\n")
        for k, v in data["drive"].items():
            buf.write(f"- {k}: {v}\n")

        buf.write("\n## Errores criticos (ultimos)\n")
        for i, err in enumerate(data["errores_criticos"][:20], 1):
            buf.write(f"\n### Error {i}\n")
            buf.write(f"- Fecha: {err.get('fecha', 'N/A')}\n")
            buf.write(f"- Tipo: {err.get('tipo', 'N/A')}\n")
            buf.write(f"- URL: {err.get('url', 'N/A')}\n")
            buf.write(f"- Severidad: {err.get('severidad', 'N/A')}\n")
            tb = err.get("traceback", "")
            if tb:
                buf.write("```\n")
                buf.write(tb[:800])
                buf.write("\n```\n")

        return buf.getvalue()