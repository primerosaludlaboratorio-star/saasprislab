"""
CICLO 11 — Reporte Semanal de Salud Sentinel
============================================
Genera un reporte de salud basado en IncidenciaSentinel de los últimos 7 días:
- Agrupación por tipo de error, módulo/URL y frecuencia
- Comparación con la semana anterior (tendencia)
- Top 5 errores más frecuentes
- Top 5 endpoints más lentos (SlowRequest)
- Tasa de error por módulo
- Puntuación de salud 0-100

Uso:
  python manage.py sentinel_reporte_semanal
  python manage.py sentinel_reporte_semanal --salvar
  python manage.py sentinel_reporte_semanal --dias 14
"""
import json
import re
from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


def _normalize_error_pattern(tipo_excepcion, traceback_completo):
    """
    Agrupa errores similares: quita números de línea y valores variables.
    """
    tipo = (tipo_excepcion or "").strip() or "Unknown"
    first_line = ""
    if traceback_completo:
        lines = traceback_completo.strip().split("\n")
        first_line = (lines[0] if lines else "")[:200]
        first_line = re.sub(r"\bline\s+\d+\b", "line N", first_line, flags=re.IGNORECASE)
        first_line = re.sub(r"\b\d{2,}\b", "#", first_line)
    return f"{tipo}|||{first_line}"


def _url_to_module(url):
    """Extrae módulo desde URL."""
    if not url or not url.strip():
        return "unknown"
    path = url.split("?")[0].strip("/")
    parts = path.split("/")
    return (parts[0].lower() if parts else "root") or "unknown"


def _extract_slow_ms(traceback_completo):
    """Extrae milisegundos de un traceback de SlowRequest."""
    if not traceback_completo:
        return None
    m = re.search(r"(\d+)\s*ms", traceback_completo, re.IGNORECASE)
    return int(m.group(1)) if m else None


# CICLO 11: Mapa URL/endpoint -> acción de usuario (botón o flujo)
URL_TO_ACTION_MAP = {
    "/farmacia/pdv/": "PDV Farmacia / Enviar Venta",
    "/farmacia/almacen/entradas/": "Entrada de Mercancía",
    "/farmacia/almacen/ajustes/": "Ajustes de Inventario",
    "/farmacia/devoluciones/": "Devoluciones Farmacia",
    "/farmacia/devoluciones/procesar/": "Procesar Devolución",
    "/laboratorio/recepcion/": "Recepción Lab",
    "/laboratorio/consulta-ordenes/": "Consulta de Órdenes",
    "/laboratorio/api/crear-orden/": "Crear Orden Lab",
    "/laboratorio/api/cobrar-orden/": "Cobrar Orden Lab",
    "/laboratorio/api/guardar-resultados/": "Guardar Resultados Lab",
    "/laboratorio/api/cancelar-orden/": "Cancelar Orden Lab",
    "/laboratorio/api/editar-paciente/": "Editar Paciente en Orden",
    "/laboratorio/api/eliminar-estudio/": "Eliminar Estudio de Orden",
    "/laboratorio/api/toma-muestra/": "Registrar Toma de Muestra",
    "/laboratorio/api/validar-valor-critico/": "Validar Valor Crítico",
    "/laboratorio/api/rechazar-muestra/": "Rechazar Muestra",
    "/laboratorio/captura/": "Captura de Resultados",
    "/laboratorio/monitor/": "Monitor de Producción",
    "/laboratorio/api/avanzar-estado/": "Avanzar Estado (Kanban)",
    "/consultorio/": "Consultorio",
    "/consultorio/nueva-consulta/": "Nueva Consulta SOAP",
    "/api/buscar-paciente": "Búsqueda Paciente",
    "/cotizacion/api/buscar-paciente/": "Búsqueda Paciente Cotización",
    "/director/": "Dashboard Director",
    "/seguridad/": "Seguridad / 2FA",
    "/admin/": "Admin Django",
    "/api/sentinel/": "Sentinel / Shield",
    "/ia/asistente/": "Asistente IA",
    "/finanzas/": "Finanzas / Corte",
    "/finanzas/api/registro-gasto/": "Registro Gasto",
    "/catalogos/estudios/": "Catálogo Estudios",
    "/lims/estudios/": "LIMS Estudios",
}


def _url_to_action(url):
    """
    Normaliza URL (quita query, reemplaza IDs por placeholder) y devuelve
    (nombre_accion, path_base) según URL_TO_ACTION_MAP (match por prefijo más largo).
    """
    if not url or not url.strip():
        return "Otra / Sin URL", ""
    path = url.split("?")[0].strip()
    if not path.startswith("/"):
        path = "/" + path
    path_base = re.sub(r"/\d+/", "/", path)  # /api/guardar-resultados/123/ -> /api/guardar-resultados/
    path_base = re.sub(r"/\d+$", "/", path_base)
    if path_base and not path_base.endswith("/"):
        path_base += "/"
    best_action = "Otra / Sin URL"
    best_path = path_base[:50] if path_base else ""
    best_len = 0
    for prefix, action in URL_TO_ACTION_MAP.items():
        if path_base.startswith(prefix.rstrip("/") + "/") or path_base == prefix or path_base.startswith(prefix):
            if len(prefix) >= best_len:
                best_len = len(prefix)
                best_action = action
                best_path = prefix
    if best_len == 0 and path_base:
        best_path = path_base[:60]
    return best_action, best_path


class Command(BaseCommand):
    help = "Reporte semanal de salud Sentinel (incidencias últimos 7 días)"

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=7, help="Ventana en días (default: 7)")
        parser.add_argument("--salvar", action="store_true", help="Guardar resumen (JSON)")

    def handle(self, *args, **options):
        try:
            from consultorio.models import IncidenciaSentinel
        except ImportError:
            self.stderr.write(self.style.ERROR("No se pudo importar IncidenciaSentinel (app consultorio)."))
            return

        dias = options["dias"]
        ahora = timezone.now()
        inicio_esta = ahora - timedelta(days=dias)
        inicio_anterior = ahora - timedelta(days=dias * 2)

        qs_esta = IncidenciaSentinel.objects.filter(
            fecha_creacion__gte=inicio_esta,
            fecha_creacion__lte=ahora,
        )
        qs_anterior = IncidenciaSentinel.objects.filter(
            fecha_creacion__gte=inicio_anterior,
            fecha_creacion__lt=inicio_esta,
        )

        total_esta = qs_esta.count()
        total_anterior = qs_anterior.count()

        by_pattern = defaultdict(lambda: {"count": 0, "urls": set(), "severidades": defaultdict(int)})
        by_module = defaultdict(int)
        by_action = defaultdict(lambda: {"count": 0, "last": None, "sample_message": None, "path": ""})
        slow_requests = []

        for inc in qs_esta.only(
            "id", "tipo_excepcion", "traceback_completo", "url_afectada",
            "codigo_http", "namespace", "severidad", "fecha_creacion",
        ):
            pattern = _normalize_error_pattern(inc.tipo_excepcion, inc.traceback_completo or "")
            by_pattern[pattern]["count"] += 1
            if inc.url_afectada:
                by_pattern[pattern]["urls"].add(inc.url_afectada[:200])
            by_pattern[pattern]["severidades"][inc.severidad] += 1

            mod = inc.namespace or _url_to_module(inc.url_afectada or "")
            by_module[mod] += 1

            action_name, path_base = _url_to_action(inc.url_afectada or "")
            key = (action_name, path_base)
            by_action[key]["count"] += 1
            by_action[key]["path"] = path_base
            if inc.fecha_creacion:
                if by_action[key]["last"] is None or inc.fecha_creacion > by_action[key]["last"]:
                    by_action[key]["last"] = inc.fecha_creacion
            if by_action[key]["sample_message"] is None and (inc.tipo_excepcion or inc.traceback_completo):
                sample = (inc.tipo_excepcion or "").strip()
                if inc.traceback_completo:
                    first_line = (inc.traceback_completo.strip().split("\n")[0] or "")[:120]
                    if first_line:
                        sample = first_line
                by_action[key]["sample_message"] = sample

            if (inc.tipo_excepcion or "").strip() == "SlowRequest":
                ms = _extract_slow_ms(inc.traceback_completo or "")
                if ms is not None:
                    slow_requests.append((inc.url_afectada or "", ms, inc.id))

        top5_errors = sorted(
            [
                (pattern, data["count"], list(data["urls"])[:3], dict(data["severidades"]))
                for pattern, data in by_pattern.items()
            ],
            key=lambda x: -x[1],
        )[:5]

        slow_requests.sort(key=lambda x: -x[1])
        top5_slow = slow_requests[:5]
        module_rates = dict(by_module)

        if total_anterior > 0:
            cambio_pct = ((total_esta - total_anterior) / total_anterior) * 100
            tendencia = "sube" if cambio_pct > 0 else "baja" if cambio_pct < 0 else "estable"
        else:
            cambio_pct = 100.0 if total_esta > 0 else 0.0
            tendencia = "sube" if total_esta > 0 else "estable"

        puntaje = 100
        if total_esta > 0:
            puntaje -= min(40, (total_esta // 10) * 2)
            crit = qs_esta.filter(severidad="CRITICA").count()
            alta = qs_esta.filter(severidad="ALTA").count()
            puntaje -= min(30, crit * 5 + alta * 2)
            puntaje -= min(15, len(slow_requests) * 3)
        puntaje = max(0, min(100, puntaje))

        self.stdout.write(self.style.WARNING("══════════════════════════════════════════════════════════════"))
        self.stdout.write(self.style.WARNING("  REPORTE SEMANAL DE SALUD — PRIS SENTINEL"))
        self.stdout.write(self.style.WARNING("  Ventana: últimos %d días" % dias))
        self.stdout.write(self.style.WARNING("══════════════════════════════════════════════════════════════"))
        self.stdout.write("")
        self.stdout.write("  MÉTRICAS GLOBALES")
        self.stdout.write("  -----------------")
        self.stdout.write("  Incidencias esta semana:  %d" % total_esta)
        self.stdout.write("  Incidencias semana anterior: %d" % total_anterior)
        self.stdout.write("  Tendencia: %s (%.1f%%)" % (tendencia, abs(cambio_pct)))
        self.stdout.write("  Puntuación de salud: %d/100" % puntaje)
        self.stdout.write("")
        self.stdout.write("  TOP 5 ERRORES MÁS FRECUENTES")
        self.stdout.write("  ----------------------------")
        for i, (pattern, count, urls, sev) in enumerate(top5_errors, 1):
            short = (pattern.split("|||")[0] or pattern)[:60]
            self.stdout.write("  %d. [%d veces] %s" % (i, count, short))
            for u in urls[:1]:
                self.stdout.write("      URL: %s" % (u[:70] + "..." if len(u) > 70 else u))
        self.stdout.write("")
        self.stdout.write("  TOP 5 ENDPOINTS MÁS LENTOS (>5s)")
        self.stdout.write("  --------------------------------")
        for i, (url, ms, _id) in enumerate(top5_slow, 1):
            self.stdout.write("  %d. %d ms — %s" % (i, ms, (url[:60] + "..." if len(url) > 60 else url) or "(sin URL)"))
        if not top5_slow:
            self.stdout.write("  (ninguno registrado)")
        self.stdout.write("")
        top10_actions = sorted(
            [
                (action_name, data["count"], data["path"], data["last"], data["sample_message"])
                for (action_name, path_base), data in by_action.items()
                if data["count"] > 0
            ],
            key=lambda x: -x[1],
        )[:10]
        self.stdout.write("  === TOP 10 BOTONES/ACCIONES QUE MÁS FALLAN ===")
        self.stdout.write("  -------------------------------------------------")
        for i, (action_name, count, path, last_ts, sample) in enumerate(top10_actions, 1):
            last_str = last_ts.strftime("%Y-%m-%d %H:%M") if last_ts else "—"
            self.stdout.write("  %d. [%d errores] %s (%s)" % (i, count, action_name, path or "(URL)"))
            self.stdout.write("      Última: %s" % last_str)
            if sample:
                self.stdout.write("      Ejemplo: %s" % (sample[:75] + "..." if len(sample) > 75 else sample))
        if not top10_actions:
            self.stdout.write("  (ninguna incidencia en ventana)")
        self.stdout.write("")
        self.stdout.write("  ERRORES POR MÓDULO / NAMESPACE")
        self.stdout.write("  ------------------------------")
        for mod, cnt in sorted(module_rates.items(), key=lambda x: -x[1]):
            self.stdout.write("  %s: %d" % (mod or "(sin módulo)", cnt))
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("══════════════════════════════════════════════════════════════"))

        if options.get("salvar"):
            payload = {
                "inicio_semana": timezone.localtime(inicio_esta).isoformat(),
                "total_incidencias": total_esta,
                "total_semana_anterior": total_anterior,
                "puntaje_salud": puntaje,
                "top5_errores": [
                    {"pattern": p[0][:100], "count": p[1], "urls_sample": p[2][:2]}
                    for p in top5_errors
                ],
                "top5_slow": [{"url": u[:200], "ms": ms} for u, ms, _ in top5_slow],
                "top10_acciones_fallan": [
                    {"accion": a[0], "count": a[1], "path": a[2], "ultima": a[3].isoformat() if a[3] else None, "sample": (a[4] or "")[:150]}
                    for a in top10_actions
                ],
                "por_modulo": module_rates,
            }
            self.stdout.write(self.style.SUCCESS("Resumen (--salvar):"))
            self.stdout.write(json.dumps(payload, indent=2, default=str)[:800] + "...")
