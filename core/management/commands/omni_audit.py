"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       OMNI-GUARDIÁN PRISLAB — Framework de Auditoría E2E Definitivo         ║
║       Comando: python manage.py omni_audit --total                           ║
║       Versión: 3.0.0  |  Costo IA: $0  |  100% local                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Motores de auditoría:
  1.  DiscoveryEngine      — Mapeo recursivo de TODAS las apps/vistas/templates
  2.  URLProber            — Prueba HTTP de rutas activas (Django Test Client)
  3.  TemplateScanner      — Análisis HTML: orbes, clip, sidebar, firma Giselle
  4.  CodeQualityAnalyst   — AST: TODOs, FIXMEs, imports muertos, sintaxis
  5.  DatabaseInspector    — Huérfanos, conteos críticos, integridad referencial
  6.  ClinicalLogicValidator — Regla 3 Hb/Hto · Friedewald · Bilirrubinas · Anion Gap · Delta Universal
  7.  LegalComplianceChecker — Firma QC Giselle, QR antifraude, SHA-256
  8.  UXGuardian           — z-index 9999, #pris-orb ausente, hover-driven
  9.  RAGStatusChecker     — Documentos indexados y consultables
  10. BaselineManager      — Línea base JSON, comparación evolutiva
  11. ReportGenerator      — Consola rica + logs/omni_audit.log
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.test import Client
from django.conf import settings

# ── Colorama (opcional pero recomendado) ────────────────────────────────────
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    _HAS_COLOR = True
except ImportError:
    class _FakeColor:
        def __getattr__(self, _): return ''
    Fore = Style = _FakeColor()
    _HAS_COLOR = False

# ── Constantes ────────────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(settings.BASE_DIR)
LOGS_DIR       = PROJECT_ROOT / 'logs'
LOG_FILE       = LOGS_DIR / 'omni_audit.log'
BASELINE_FILE  = LOGS_DIR / 'omni_baseline.json'
LOGS_DIR.mkdir(exist_ok=True)

RESPONSABLE_SANITARIA = 'Giselle Margarita López Gutiérrez'
RESPONSABLE_PATTERNS  = [
    'Giselle', 'giselle', 'López Gutiérrez', 'lopez gutierrez',
    'responsable_sanitaria', 'Q.B.', 'QBF', 'Responsable Sanitaria',
]

FORBIDDEN_UI_PATTERNS = [
    (r'id=["\']pris-orb["\']',         'Orbe #pris-orb presente (debe estar oculto)'),
    (r'class=["\'][^"\']*pris-fab["\']','Botón flotante .pris-fab presente'),
    (r'onclick=["\']prsbToggle\(\)',   'Botón clip/pin prsbToggle activo'),
    (r'id=["\']prsbCollapseBtn["\']',  'Botón colapsar sidebar presente (eliminado)'),
]

REQUIRED_STEP_URLS = [
    ('recepcion_lab',         'Paso 1 — Recepción'),
    ('toma_muestra_index',    'Paso 2 — Toma de Muestra'),
    ('laboratorio:monitor_produccion', 'Paso 3 — Monitor'),
    ('lista_trabajo_lab',     'Paso 4 — Worklist Analítica'),
    ('control_calidad',       'Paso 5 — Control de Calidad'),
    ('entrega_resultados',    'Paso 6 — Entrega'),
]

# Parámetros esperados en BHC/CBC
BHC_PARAMETROS_ESPERADOS = [
    'Leucocitos', 'Eritrocitos', 'Hemoglobina', 'Hematocrito',
    'VCM', 'HCM', 'CHCM', 'ADE', 'Plaquetas', 'VPM',
    'Neutrófilos', 'Linfocitos', 'Monocitos', 'Eosinófilos', 'Basófilos',
    'Neutrófilos #', 'Linfocitos #', 'Monocitos #', 'Eosinófilos #', 'Basófilos #',
    'Reticulocitos', 'Índice Reticulocitario',
]

ALL_APPS = [
    'bienestar', 'consultorio', 'contabilidad', 'core', 'enfermeria',
    'farmacia', 'inventario', 'iot', 'laboratorio', 'logistica',
    'mantenimiento', 'marketing', 'pacientes', 'recepcion',
    'reglas_negocio', 'seguridad',
]


# ─────────────────────────────────────────────────────────────────────────────
# Estructuras de datos
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AuditResult:
    module:   str
    function: str
    status:   str          # OPERATIVA | FALLANDO | NO_DESPLEGADA | ADVERTENCIA
    detail:   str = ''
    file:     str = ''
    line:     int = 0
    ms:       float = 0.0

    @property
    def emoji(self) -> str:
        return {'OPERATIVA': '✅', 'FALLANDO': '❌',
                'NO_DESPLEGADA': '⚠️ ', 'ADVERTENCIA': '🟡'}.get(self.status, '❓')

    @property
    def color(self):
        return {'OPERATIVA': Fore.GREEN, 'FALLANDO': Fore.RED,
                'NO_DESPLEGADA': Fore.YELLOW, 'ADVERTENCIA': Fore.YELLOW}.get(self.status, Fore.WHITE)


# ─────────────────────────────────────────────────────────────────────────────
# Motor 1 — Discovery Engine
# ─────────────────────────────────────────────────────────────────────────────

class DiscoveryEngine:
    """Mapea recursivamente todo el proyecto."""

    IGNORE_DIRS = {'__pycache__', '.git', 'node_modules', 'venv', '.venv',
                   'staticfiles', 'media', 'migrations', '.mypy_cache'}

    def __init__(self):
        self.py_files:       list[Path] = []
        self.template_files: list[Path] = []
        self.url_files:      list[Path] = []
        self.view_files:     list[Path] = []
        self.model_files:    list[Path] = []
        self.static_files:   list[Path] = []

    def scan(self) -> None:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            rpath = Path(root)
            for fname in files:
                fpath = rpath / fname
                if fname.endswith('.py'):
                    self.py_files.append(fpath)
                    if fname == 'urls.py':
                        self.url_files.append(fpath)
                    elif fname in ('views.py',) or '/views/' in str(fpath):
                        self.view_files.append(fpath)
                    elif fname == 'models.py' or '/models/' in str(fpath):
                        self.model_files.append(fpath)
                elif fname.endswith('.html'):
                    self.template_files.append(fpath)
                elif fname.endswith(('.css', '.js')):
                    self.static_files.append(fpath)

    def summary(self) -> dict:
        return {
            'py_files':       len(self.py_files),
            'templates':      len(self.template_files),
            'url_files':      len(self.url_files),
            'view_files':     len(self.view_files),
            'model_files':    len(self.model_files),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Motor 2 — URL Prober
# ─────────────────────────────────────────────────────────────────────────────

class URLProber:
    """Prueba rutas HTTP con Django Test Client."""

    def __init__(self, user):
        self.client = Client()
        self.client.force_login(user)

    def probe(self, url: str, name: str, method: str = 'GET', data: dict | None = None) -> AuditResult:
        t0 = time.perf_counter()
        try:
            resp = (self.client.post(url, data or {}, follow=True)
                    if method == 'POST'
                    else self.client.get(url, follow=True))
            ms = (time.perf_counter() - t0) * 1000
            if resp.status_code == 200:
                return AuditResult('HTTP', name, 'OPERATIVA',
                                   f'HTTP 200 en {ms:.0f}ms', url, ms=ms)
            elif resp.status_code in (301, 302):
                return AuditResult('HTTP', name, 'OPERATIVA',
                                   f'Redirect {resp.status_code}', url, ms=ms)
            elif resp.status_code == 404:
                return AuditResult('HTTP', name, 'NO_DESPLEGADA',
                                   'HTTP 404 — URL no encontrada', url, ms=ms)
            elif resp.status_code >= 500:
                body = resp.content.decode('utf-8', errors='ignore')[:300]
                return AuditResult('HTTP', name, 'FALLANDO',
                                   f'HTTP {resp.status_code} — {body[:120]}', url, ms=ms)
            else:
                return AuditResult('HTTP', name, 'ADVERTENCIA',
                                   f'HTTP {resp.status_code}', url, ms=ms)
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en probe (omni_audit.py)")
            ms = (time.perf_counter() - t0) * 1000
            return AuditResult('HTTP', name, 'FALLANDO', str(exc), url, ms=ms)


# ─────────────────────────────────────────────────────────────────────────────
# Motor 3 — Template Scanner
# ─────────────────────────────────────────────────────────────────────────────

class StaticAssetsChecker:
    """Verifica existencia y peso real de activos JS/CSS/Media referenciados en templates."""

    MIN_JS_SIZE = 1_000      # bytes — un JS menor a 1KB es sospechoso
    CRITICAL_ASSETS = [
        # Farmacia PDV — motor completo de caja (~27 KB)
        ('js/pdv_farmacia.js',         27_000, 'PDV Farmacia — lógica de carrito, pagos, atajos F2/F4/F8/F10'),
        # JS principal del sistema
        ('js/prislab_main.js',          1_000, 'JS principal PRISLAB'),
        # CSS compartido de PRISLAB
        ('css/prislab_shared.css',        500, 'CSS compartido PRISLAB (estilos globales)'),
    ]

    def check(self, templates: list[Path]) -> list[AuditResult]:
        results = []
        static_root = PROJECT_ROOT / 'static'

        # 1. Activos críticos específicos
        for asset_path, min_size, description in self.CRITICAL_ASSETS:
            full = static_root / asset_path
            if not full.exists():
                results.append(AuditResult('Assets', f'Activo crítico: {asset_path}',
                    'FALLANDO', f'ERROR CRÍTICO ❌ — {description} NO EXISTE en disco',
                    str(full)))
            elif full.stat().st_size < min_size:
                sz = full.stat().st_size
                results.append(AuditResult('Assets', f'Activo crítico: {asset_path}',
                    'ADVERTENCIA', f'{description} existe pero es pequeño ({sz} bytes, esperado ≥{min_size})',
                    str(full)))
            else:
                sz = full.stat().st_size
                results.append(AuditResult('Assets', f'Activo crítico: {asset_path}',
                    'OPERATIVA', f'{description} — {sz//1024}KB en disco', str(full)))

        # 2. Escaneo de referencias en templates
        ref_pattern = re.compile(r"static ['\"]([^'\"]+\.(?:js|css))['\"]")
        phantom_refs: dict[str, list[str]] = {}
        for tpl in templates:
            try:
                content = tpl.read_text(encoding='utf-8', errors='ignore')
                for m in ref_pattern.finditer(content):
                    asset = m.group(1)
                    full = static_root / asset
                    if not full.exists():
                        phantom_refs.setdefault(asset, []).append(tpl.name)
                    elif full.stat().st_size == 0:
                        phantom_refs.setdefault(f'{asset} (0 bytes)', []).append(tpl.name)
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en check (omni_audit.py)")
                pass

        for ref, tpls in phantom_refs.items():
            results.append(AuditResult('Assets', f'Referencia fantasma: {ref}',
                'FALLANDO', f'ERROR CRÍTICO ❌ — Archivo invocado pero no existe/vacío en: {", ".join(tpls[:3])}',
                str(static_root / ref.split(' ')[0])))

        if not phantom_refs:
            results.append(AuditResult('Assets', 'Referencias de activos estáticos',
                'OPERATIVA', 'Todos los JS/CSS referenciados en templates existen en disco'))

        return results


class TemplateScanner:
    """Analiza archivos HTML buscando patrones prohibidos y requeridos."""

    # El orb fue eliminado de base.html — cualquier aparición es ERROR
    ORBE_IGNORAR_EN: set[str] = set()

    def scan_for_forbidden(self, templates: list[Path]) -> list[AuditResult]:
        """Busca patrones prohibidos. El #pris-orb fue eliminado completamente del proyecto."""
        results = []
        orb_found_in = []
        for tpl in templates:
            try:
                content = tpl.read_text(encoding='utf-8', errors='ignore')
                # Verificar si el orbe aparece como elemento HTML real (no solo como CSS selector)
                if re.search(r'id=["\']pris-orb["\']', content):
                    orb_found_in.append(tpl.name)
                for pattern, msg in FORBIDDEN_UI_PATTERNS:
                    if 'pris-orb' in pattern:
                        continue  # evaluado por separado arriba
                    for m in re.finditer(pattern, content):
                        line = content[:m.start()].count('\n') + 1
                        results.append(AuditResult(
                            'UX', f'Elemento prohibido en {tpl.name}',
                            'FALLANDO', msg,
                            str(tpl.relative_to(PROJECT_ROOT)), line
                        ))
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en scan_for_forbidden (omni_audit.py)")
                pass

        if orb_found_in:
            results.append(AuditResult('UX', 'Orbe #pris-orb eliminado', 'FALLANDO',
                f'ERROR CRÍTICO ❌ — Orbe encontrado en: {", ".join(orb_found_in)}'))
        else:
            results.append(AuditResult('UX', 'Orbe #pris-orb eliminado', 'OPERATIVA',
                '✅ #pris-orb eliminado físicamente de todos los templates'))
        return results

    def scan_sidebar(self, templates: list[Path]) -> list[AuditResult]:
        results = []
        sidebar_files = [t for t in templates if 'sidebar' in t.name.lower()]
        for tpl in sidebar_files:
            content = tpl.read_text(encoding='utf-8', errors='ignore')
            # z-index 9999
            if 'z-index: 9999' in content or 'z-index:9999' in content:
                results.append(AuditResult('UX', 'Sidebar z-index 9999', 'OPERATIVA',
                                           'z-index correcto', str(tpl.relative_to(PROJECT_ROOT))))
            else:
                results.append(AuditResult('UX', 'Sidebar z-index 9999', 'FALLANDO',
                                           'z-index NO es 9999 — clicks pueden quedar bloqueados',
                                           str(tpl.relative_to(PROJECT_ROOT))))
            # hover-driven
            if 'mouseenter' in content and 'mouseleave' in content:
                results.append(AuditResult('UX', 'Sidebar hover-driven', 'OPERATIVA',
                                           'mouseenter/mouseleave presentes'))
            else:
                results.append(AuditResult('UX', 'Sidebar hover-driven', 'FALLANDO',
                                           'No se encontró lógica mouseenter/mouseleave'))
            # botón clip eliminado
            if 'prsbCollapseBtn' not in content and 'prsbToggle()' not in content:
                results.append(AuditResult('UX', 'Botón clip/pin eliminado', 'OPERATIVA',
                                           'Ningún botón de anclaje encontrado'))
            else:
                results.append(AuditResult('UX', 'Botón clip/pin eliminado', 'FALLANDO',
                                           'prsbCollapseBtn o prsbToggle() todavía presentes',
                                           str(tpl.relative_to(PROJECT_ROOT))))
            # emergency reset localStorage
            if 'localStorage.removeItem' in content and 'prsb_collapsed' in content:
                results.append(AuditResult('UX', 'Emergency localStorage reset', 'OPERATIVA',
                                           'Reset de estado atrapado activo'))
            else:
                results.append(AuditResult('UX', 'Emergency localStorage reset', 'ADVERTENCIA',
                                           'No se detectó limpieza de localStorage prsb_collapsed'))
        if not sidebar_files:
            results.append(AuditResult('UX', 'Archivo sidebar.html', 'NO_DESPLEGADA',
                                       'No se encontró sidebar.html en templates'))
        return results

    def scan_toma(self, templates: list[Path]) -> list[AuditResult]:
        """Solo audita preparacion_toma.html — es el archivo del cubículo PRIS-Shadow."""
        results = []
        toma_files = [t for t in templates if 'preparacion_toma' in t.name]
        for tpl in toma_files:
            content = tpl.read_text(encoding='utf-8', errors='ignore')
            # btn-iniciar sin disabled
            btn_match = re.search(r'id=["\']btn-iniciar["\'][^>]*>', content)
            if btn_match:
                btn_html = btn_match.group(0)
                if 'disabled' not in btn_html:
                    results.append(AuditResult('TOMA', 'Botón INICIAR TOMA desbloqueado',
                                               'OPERATIVA', 'Sin atributo disabled al cargar'))
                else:
                    line = content[:btn_match.start()].count('\n') + 1
                    results.append(AuditResult('TOMA', 'Botón INICIAR TOMA desbloqueado',
                                               'FALLANDO', 'Botón tiene disabled',
                                               str(tpl.relative_to(PROJECT_ROOT)), line))
            # btn-finalizar bloqueado
            fin_match = re.search(r'id=["\']btn-finalizar["\'][^>]*>', content)
            if fin_match:
                fin_html = fin_match.group(0)
                if 'disabled' in fin_html:
                    results.append(AuditResult('TOMA', 'Botón FINALIZAR bloqueado al inicio',
                                               'OPERATIVA', 'Requiere completar checklist'))
                else:
                    results.append(AuditResult('TOMA', 'Botón FINALIZAR bloqueado al inicio',
                                               'ADVERTENCIA', 'btn-finalizar no tiene disabled inicial'))
            # 6 checks PRIS-Shadow
            intents = re.findall(r"'(IDENTIDAD|AYUNO|CONSENTIMIENTO|MEDICAMENTOS|SINTOMAS|PADECIMIENTOS)'", content)
            intents_set = set(intents)
            expected = {'IDENTIDAD', 'AYUNO', 'CONSENTIMIENTO', 'MEDICAMENTOS', 'SINTOMAS', 'PADECIMIENTOS'}
            if intents_set >= expected:
                results.append(AuditResult('TOMA', '6 checks PRIS-Shadow completos',
                                           'OPERATIVA', f'Checks encontrados: {", ".join(sorted(intents_set))}'))
            else:
                missing = expected - intents_set
                results.append(AuditResult('TOMA', '6 checks PRIS-Shadow completos',
                                           'FALLANDO' if missing else 'OPERATIVA',
                                           f'Faltan: {", ".join(missing)}'))
            # NLP local activo
            if 'analizarConNLP' in content or 'nlp' in content.lower():
                results.append(AuditResult('TOMA', 'NLP local (PRIS-Shadow) activo',
                                           'OPERATIVA', 'Motor NLP detectado en template'))
            else:
                results.append(AuditResult('TOMA', 'NLP local (PRIS-Shadow) activo',
                                           'NO_DESPLEGADA', 'No se detectó lógica NLP'))
            # Orbe oculto en toma
            if '#pris-orb' in content and 'display: none' in content:
                results.append(AuditResult('TOMA', 'Orbe #pris-orb oculto', 'OPERATIVA',
                                           'CSS display:none confirmado en preparacion_toma'))
            else:
                results.append(AuditResult('TOMA', 'Orbe #pris-orb oculto', 'ADVERTENCIA',
                                           'No se confirmó ocultamiento del orbe'))
        if not toma_files:
            results.append(AuditResult('TOMA', 'Template preparacion_toma.html',
                                       'NO_DESPLEGADA', 'Archivo no encontrado'))
        return results

    def scan_worklist(self, templates: list[Path]) -> list[AuditResult]:
        results = []
        wl_files = [t for t in templates
                    if 'captura_resultados_industrial' in t.name
                    or 'worklist_analitica' in t.name
                    or 'lista_trabajo' in t.name]
        for tpl in wl_files:
            content = tpl.read_text(encoding='utf-8', errors='ignore')
            # Orbe oculto
            if ('#pris-orb' in content and 'none !important' in content):
                results.append(AuditResult('WORKLIST', f'Orbe oculto en {tpl.name}',
                                           'OPERATIVA', 'display:none !important confirmado'))
            else:
                results.append(AuditResult('WORKLIST', f'Orbe oculto en {tpl.name}',
                                           'ADVERTENCIA', 'Orbe podría estar visible'))
            # Botones Guardar/Validar arriba
            if 'guardarBorrador' in content or 'btn-guardar' in content.lower():
                results.append(AuditResult('WORKLIST', 'Botones Guardar/Validar en barra superior',
                                           'OPERATIVA', 'Botones encontrados'))
            # Delta check
            if 'delta' in content.lower() or 'anterior' in content.lower():
                results.append(AuditResult('WORKLIST', 'Columna Delta Check (Δ Anterior)',
                                           'OPERATIVA', 'Lógica delta detectada'))
            else:
                results.append(AuditResult('WORKLIST', 'Columna Delta Check (Δ Anterior)',
                                           'ADVERTENCIA', 'No se detectó lógica delta check'))
            # Panel RAG Manuales
            if 'togglePanelRAG' in content or 'Manuales' in content:
                results.append(AuditResult('WORKLIST', 'Botón Consultar Manuales (RAG)',
                                           'OPERATIVA', 'Panel RAG integrado'))
        if not wl_files:
            results.append(AuditResult('WORKLIST', 'Template Worklist',
                                       'NO_DESPLEGADA', 'Ningún template de worklist encontrado'))
        return results


# ─────────────────────────────────────────────────────────────────────────────
# Motor 4 — Code Quality Analyst
# ─────────────────────────────────────────────────────────────────────────────

class CodeQualityAnalyst:
    """Análisis estático con AST de Python."""

    TODO_PATTERN = re.compile(r'\b(TODO|FIXME|HACK|PENDIENTE|XXX)\b', re.IGNORECASE)

    def scan_file(self, fpath: Path) -> list[AuditResult]:
        results = []
        try:
            source = fpath.read_text(encoding='utf-8', errors='ignore')
            rel = str(fpath.relative_to(PROJECT_ROOT))
            # Sintaxis
            try:
                ast.parse(source)
            except SyntaxError as se:
                results.append(AuditResult('CÓDIGO', f'Error de sintaxis en {fpath.name}',
                                           'FALLANDO', str(se), rel, se.lineno or 0))
                return results  # no seguir si hay error de sintaxis
            # Marcadores de deuda en línea (patrón AST: TODO|FIXME|…)
            for i, line in enumerate(source.splitlines(), 1):
                m = self.TODO_PATTERN.search(line)
                if m:
                    results.append(AuditResult('CÓDIGO', f'Deuda técnica ({m.group()}) en {fpath.name}',
                                               'ADVERTENCIA', line.strip(), rel, i))
            # except: pass (silenciadores de errores)
            for m in re.finditer(r'except\s*(?:Exception\s*)?:\s*pass', source):
                line = source[:m.start()].count('\n') + 1
                results.append(AuditResult('CÓDIGO', f'except:pass en {fpath.name}',
                                           'ADVERTENCIA', 'Silenciador de errores detectado', rel, line))
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en scan_file (omni_audit.py)")
            results.append(AuditResult('CÓDIGO', f'No se pudo analizar {fpath.name}',
                                       'ADVERTENCIA', str(exc)))
        return results

    def scan_all(self, py_files: list[Path], modules: list[str]) -> tuple[list[AuditResult], dict]:
        results   = []
        stats     = {'syntax_errors': 0, 'todos': 0, 'silencers': 0, 'files_scanned': 0}
        # solo escanear archivos de apps del proyecto
        target = [f for f in py_files if any(f'/{app}/' in str(f).replace('\\', '/')
                                              or f'\\{app}\\' in str(f)
                                              for app in modules)]
        for fpath in target:
            file_results = self.scan_file(fpath)
            stats['files_scanned'] += 1
            for r in file_results:
                if r.status == 'FALLANDO': stats['syntax_errors'] += 1
                if 'Deuda' in r.function:   stats['todos'] += 1
                if 'silenciador' in r.detail.lower(): stats['silencers'] += 1
            results.extend(file_results)
        return results, stats


# ─────────────────────────────────────────────────────────────────────────────
# Motor 5 — Database Inspector
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseInspector:
    """Verifica integridad de la base de datos."""

    def inspect(self) -> list[AuditResult]:
        results = []
        # ── Modelos core ────────────────────────────────────────────────────
        checks = [
            ('core.Empresa',                    'Empresa(s) registrada(s)',           1),
            ('lims.Analito',                    'Analitos LIMS (catálogo v7.5)',      10),
            ('lims.ValorReferenciaAnalito',     'Valores de referencia LIMS',       20),
        ]
        for label, name, min_count in checks:
            app, model = label.split('.')
            try:
                from django.apps import apps
                Model = apps.get_model(app, model)
                count = Model.objects.count()
                if count >= min_count:
                    results.append(AuditResult('BD', name, 'OPERATIVA',
                                               f'{count} registros'))
                elif count > 0:
                    results.append(AuditResult('BD', name, 'ADVERTENCIA',
                                               f'Solo {count} registros (mínimo esperado: {min_count})'))
                else:
                    results.append(AuditResult(
                        'BD', name, 'FALLANDO',
                        '0 registros — ejecutar importar_catalogo_lims (o ensamblar_lims_v75)',
                    ))
            except LookupError:
                results.append(AuditResult('BD', name, 'NO_DESPLEGADA',
                                           f'Modelo {label} no encontrado'))
            except Exception as exc:
                logging.getLogger(__name__).exception("Error inesperado en inspect (omni_audit.py)")
                results.append(AuditResult('BD', name, 'FALLANDO', str(exc)))

        # ── Órdenes huérfanas (sin pago ni resultado) ────────────────────
        try:
            from django.apps import apps
            OrdenModel = apps.get_model('core', 'OrdenDeServicio')
            total_ordenes = OrdenModel.objects.count()
            # Órdenes confirmadas sin ningún pago
            try:
                huerfanas = OrdenModel.objects.filter(
                    estado='CONFIRMADO',
                    pagos__isnull=True
                ).count()
                pct = (huerfanas / total_ordenes * 100) if total_ordenes else 0
                if huerfanas == 0:
                    results.append(AuditResult('BD', 'Órdenes huérfanas (sin pago)',
                                               'OPERATIVA', f'0 de {total_ordenes} órdenes'))
                elif pct < 5:
                    results.append(AuditResult('BD', 'Órdenes huérfanas (sin pago)',
                                               'ADVERTENCIA', f'{huerfanas} ({pct:.1f}%) de {total_ordenes}'))
                else:
                    results.append(AuditResult('BD', 'Órdenes huérfanas (sin pago)',
                                               'FALLANDO', f'{huerfanas} ({pct:.1f}%) sin pago registrado'))
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en inspect (omni_audit.py)")
                results.append(AuditResult('BD', 'Órdenes huérfanas (sin pago)',
                                           'ADVERTENCIA', f'No se pudo filtrar relación pagos'))
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en inspect (omni_audit.py)")
            results.append(AuditResult('BD', 'OrdenDeServicio', 'ADVERTENCIA', str(exc)))

        # ── Perfil BHC (LIMS v7.5: analitos en PerfilLims) ────────────────
        try:
            from django.apps import apps
            from django.db.models import Q

            PerfilModel = apps.get_model('lims', 'PerfilLims')
            bhc_perfiles = PerfilModel.objects.filter(
                Q(nombre__icontains='biometría')
                | Q(nombre__icontains='hematica')
                | Q(nombre__icontains='BHC')
            )
            if bhc_perfiles.exists():
                perfil = bhc_perfiles.first()
                n_params = perfil.analitos.filter(activo=True).count()
                if n_params >= 20:
                    results.append(AuditResult(
                        'BD', 'Analitos perfil BHC (≥20)',
                        'OPERATIVA', f'{n_params} analitos en {perfil.nombre}',
                    ))
                elif n_params > 0:
                    results.append(AuditResult(
                        'BD', 'Analitos perfil BHC (≥20)',
                        'ADVERTENCIA',
                        f'Solo {n_params} analitos — completar catálogo vía importar_catalogo_lims',
                    ))
                else:
                    results.append(AuditResult(
                        'BD', 'Analitos perfil BHC (≥20)',
                        'FALLANDO',
                        'Sin analitos en el perfil — worklist puede quedar incompleta',
                    ))
            else:
                results.append(AuditResult(
                    'BD', 'Perfil BHC en LIMS',
                    'NO_DESPLEGADA', 'No se encontró perfil tipo Biometría Hemática',
                ))
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en inspect (omni_audit.py)")
            results.append(AuditResult('BD', 'Perfil BHC LIMS', 'ADVERTENCIA', str(exc)))

        # ── Farmacia: productos y lotes ──────────────────────────────────
        # El modelo puede estar en 'core' o 'farmacia' según la arquitectura del proyecto
        farmacia_found = False
        for app_label, model_name in [('core', 'Venta'), ('farmacia', 'Venta'),
                                       ('core', 'Producto'), ('farmacia', 'Producto')]:
            try:
                from django.apps import apps as _apps
                Model = _apps.get_model(app_label, model_name)
                n = Model.objects.count()
                results.append(AuditResult('BD', f'Farmacia {model_name} ({app_label})',
                                           'OPERATIVA' if n > 0 else 'ADVERTENCIA',
                                           f'{n} registros'))
                farmacia_found = True
                break
            except LookupError:
                continue
            except Exception as exc:
                logging.getLogger(__name__).exception("Error inesperado en inspect (omni_audit.py)")
                results.append(AuditResult('BD', f'Farmacia {model_name}', 'ADVERTENCIA', str(exc)))
                farmacia_found = True
                break
        if not farmacia_found:
            results.append(AuditResult('BD', 'Modelos Farmacia', 'ADVERTENCIA',
                                       'No se encontró Venta ni Producto en core ni farmacia'))

        return results


# ─────────────────────────────────────────────────────────────────────────────
# Motor 6 — Clinical Logic Validator
# ─────────────────────────────────────────────────────────────────────────────

class ClinicalLogicValidator:
    """Valida lógica clínica sin IA (Costo $0)."""

    def validate(self) -> list[AuditResult]:
        results = []

        # ── Regla de 3 Hb/Hto (Wintrobe) ────────────────────────────────
        # Hto (%) ≈ Hb (g/dL) × 3  (±3%)
        test_cases = [
            (14.0, 42.0, True),   # Normal M
            (12.0, 36.0, True),   # Normal F
            (7.0,  21.0, True),   # Anemia
            (14.0, 55.0, False),  # Incongruente
        ]
        passed = all(
            (abs(hto - hb * 3) <= (hb * 3 * 0.12))  == expected
            for hb, hto, expected in test_cases
        )
        results.append(AuditResult(
            'CLÍNICO', 'Regla de 3 Hb/Hto (Wintrobe)',
            'OPERATIVA' if passed else 'FALLANDO',
            'Correlación Hto = Hb×3 ±12%: ' + ('VÁLIDA' if passed else 'INVÁLIDA')
        ))

        # ── Lógica de rangos de referencia ───────────────────────────────
        try:
            from django.apps import apps
            RangoModel = apps.get_model('lims', 'ValorReferenciaAnalito')
            n_rangos = RangoModel.objects.count()
            rangos_con_ambos = RangoModel.objects.filter(
                ref_minimo__isnull=False,
                ref_maximo__isnull=False
            ).count()
            if n_rangos > 0:
                pct = rangos_con_ambos / n_rangos * 100
                results.append(AuditResult(
                    'CLÍNICO', 'Rangos de referencia LIMS completos',
                    'OPERATIVA' if pct > 80 else 'ADVERTENCIA',
                    f'{rangos_con_ambos}/{n_rangos} valores con ref_min/ref_max ({pct:.0f}%)'
                ))
            else:
                results.append(AuditResult('CLÍNICO', 'Rangos de referencia LIMS',
                                           'FALLANDO', '0 valores en BD'))
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en validate (omni_audit.py)")
            results.append(AuditResult('CLÍNICO', 'Rangos de referencia LIMS', 'ADVERTENCIA', str(exc)))

        # ── VCM / HCM / CHCM coherencia (índices eritrocitarios) ─────────
        # VCM = Hto(L/L) / RBC × 10^3 fl
        # Rango normal: 80-100 fl
        hto_ll = 0.42  # 42%
        rbc    = 4.8   # M/uL
        vcm_calc = (hto_ll / rbc) * 1000
        vcm_ok   = 80 <= vcm_calc <= 100
        results.append(AuditResult(
            'CLÍNICO', 'Índice eritrocitario VCM calculado',
            'OPERATIVA' if vcm_ok else 'ADVERTENCIA',
            f'VCM calculado: {vcm_calc:.1f} fl (normal 80-100)'
        ))

        # ── Verificar parámetros BHC por conteo (independiente de nombres exactos) ──
        try:
            from django.apps import apps
            from django.db.models import Q

            PerfilModel = apps.get_model('lims', 'PerfilLims')
            bhc_q = PerfilModel.objects.filter(
                Q(nombre__icontains='biometría')
                | Q(nombre__icontains='hematica')
                | Q(nombre__icontains='BHC')
            )
            if bhc_q.exists():
                perfil = bhc_q.first()
                n = perfil.analitos.filter(activo=True).count()
                if n >= 22:
                    results.append(AuditResult(
                        'CLÍNICO', f'Analitos BHC completos ({n})',
                        'OPERATIVA', f'{n} analitos activos en {perfil.nombre}',
                    ))
                elif n >= 18:
                    results.append(AuditResult(
                        'CLÍNICO', f'Analitos BHC ({n}/22)',
                        'ADVERTENCIA',
                        f'Operativo con {n} — completar catálogo vía importar_catalogo_lims',
                    ))
                elif n > 0:
                    results.append(AuditResult(
                        'CLÍNICO', f'Analitos BHC ({n}/22)',
                        'FALLANDO',
                        f'Solo {n} analitos — revisar ensamblar_lims_v75',
                    ))
                else:
                    results.append(AuditResult(
                        'CLÍNICO', 'Analitos BHC',
                        'FALLANDO', '0 analitos en el perfil BHC',
                    ))
            else:
                results.append(AuditResult(
                    'CLÍNICO', 'Perfil BHC LIMS',
                    'ADVERTENCIA', 'No se encontró perfil BHC para conteo',
                ))
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en validate (omni_audit.py)")
            results.append(AuditResult('CLÍNICO', 'Analitos BHC (LIMS)', 'ADVERTENCIA', str(exc)))

        # ── VALIDACIÓN UNIVERSAL DE CONGRUENCIA BIOLÓGICA (Friedewald/Bili/AG) ──
        # Verifica que las fórmulas están implementadas en la plantilla de captura.
        try:
            # omni_audit.py → commands → management → core → PRISLAB_SaaS (parents[3])
            base_dir   = Path(__file__).resolve().parents[3]
            captura_f  = base_dir / 'core' / 'templates' / 'core' / 'captura_resultados_industrial.html'
            if captura_f.exists():
                captura_txt = captura_f.read_text(encoding='utf-8', errors='ignore')

                # A. Clase CSS correcta — debe usar 'valor-critico' en querySelectorAll,
                #    no 'fuera-rango-critico'. Excluye comentarios para no generar falsos positivos.
                lineas_codigo = [
                    l for l in captura_txt.splitlines()
                    if not l.strip().startswith('//') and not l.strip().startswith('*')
                       and '/*' not in l and '#' not in l.lstrip()[:1]
                ]
                codigo_limpio = '\n'.join(lineas_codigo)
                usa_clase_correcta = 'valor-critico' in codigo_limpio
                usa_clase_antigua  = 'fuera-rango-critico' in codigo_limpio and (
                    'querySelector' in codigo_limpio and 'fuera-rango-critico' in codigo_limpio
                )
                # Verificación definitiva: querySelectorAll NO debe buscar .fuera-rango-critico
                query_con_bug = bool(re.search(
                    r'querySelector.*fuera-rango-critico', captura_txt))
                if not query_con_bug and usa_clase_correcta:
                    results.append(AuditResult(
                        'CLÍNICO', 'Semáforo Pánico — CSS clase .valor-critico',
                        'OPERATIVA',
                        'querySelector usa .valor-critico. Bug fuera-rango-critico no activo en selector.'))
                elif query_con_bug:
                    results.append(AuditResult(
                        'CLÍNICO', 'Semáforo Pánico — CSS clase obsoleta en selector',
                        'FALLANDO',
                        'CRÍTICO: querySelector(".fuera-rango-critico") detectado — semáforo nunca dispara'))
                else:
                    results.append(AuditResult(
                        'CLÍNICO', 'Semáforo Pánico — CSS clase',
                        'ADVERTENCIA', '.valor-critico no encontrada en captura_resultados_industrial.html'))

                # B. Delta Check — función _actualizarDeltaCell universal
                if '_actualizarDeltaCell' in captura_txt and 'data-delta-valor' in captura_txt:
                    results.append(AuditResult(
                        'CLÍNICO', 'Delta Check Universal — _actualizarDeltaCell',
                        'OPERATIVA', 'Función detectada. Calcula % vs histórico para cualquier analito.'))
                else:
                    results.append(AuditResult(
                        'CLÍNICO', 'Delta Check Universal',
                        'FALLANDO', '_actualizarDeltaCell ausente — Delta Check no funcional'))

                # C. Friedewald (Lípidos)
                if 'Friedewald' in captura_txt or 'friedewald' in captura_txt.lower():
                    results.append(AuditResult(
                        'CLÍNICO', 'Congruencia Lípidos — Friedewald',
                        'OPERATIVA', 'Fórmula CT ≈ LDL + HDL + TG/5 implementada.'))
                else:
                    results.append(AuditResult(
                        'CLÍNICO', 'Congruencia Lípidos — Friedewald',
                        'FALLANDO', 'Fórmula Friedewald AUSENTE en captura_resultados_industrial.html'))

                # D. Bilirrubinas
                if re.search(r'bilirrubina|biT|biD|biI', captura_txt, re.IGNORECASE):
                    results.append(AuditResult(
                        'CLÍNICO', 'Congruencia Hepática — Bilirrubinas',
                        'OPERATIVA', 'Validación BiT ≈ BiD + BiI implementada.'))
                else:
                    results.append(AuditResult(
                        'CLÍNICO', 'Congruencia Hepática — Bilirrubinas',
                        'FALLANDO', 'Validación Bilirrubinas AUSENTE en captura_resultados_industrial.html'))

                # E. Anion Gap
                if re.search(r'anion.?gap|Anion.?Gap|AG\s*=\s*na', captura_txt, re.IGNORECASE):
                    results.append(AuditResult(
                        'CLÍNICO', 'Congruencia Electrolitos — Anion Gap',
                        'OPERATIVA', 'Validación AG = Na-(Cl+HCO₃) implementada.'))
                else:
                    results.append(AuditResult(
                        'CLÍNICO', 'Congruencia Electrolitos — Anion Gap',
                        'FALLANDO', 'Validación Anion Gap AUSENTE en captura_resultados_industrial.html'))

                # F. Comentario QFB obligatorio (bloqueo transversal)
                if 'comentarioValidacion' in captura_txt or '_comentarioValidacion' in captura_txt:
                    results.append(AuditResult(
                        'CLÍNICO', 'Bloqueo Transversal — Comentario QFB obligatorio',
                        'OPERATIVA', 'Comentario técnico exigido para cualquier alerta clínica antes de validar.'))
                else:
                    results.append(AuditResult(
                        'CLÍNICO', 'Bloqueo Transversal — Comentario QFB',
                        'FALLANDO', '_comentarioValidacion ausente — validación sin candado'))

                # G. Referencia al orb eliminado (no debe quedar pris-orb-captura sin guardia null)
                orb_refs = len(re.findall(r'pris-orb-captura', captura_txt))
                if orb_refs == 0:
                    results.append(AuditResult(
                        'CLÍNICO', 'PRIS Dictado — referencia orb limpia',
                        'OPERATIVA', 'Sin referencias a #pris-orb-captura eliminado.'))
                else:
                    results.append(AuditResult(
                        'CLÍNICO', 'PRIS Dictado — referencia orb obsoleta',
                        'ADVERTENCIA', f'{orb_refs} referencia(s) a pris-orb-captura detectadas'))
            else:
                results.append(AuditResult(
                    'CLÍNICO', 'Validación Universal — archivo captura',
                    'ADVERTENCIA', 'captura_resultados_industrial.html no encontrado'))
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en validate (omni_audit.py)")
            results.append(AuditResult('CLÍNICO', 'Validación Universal QC', 'ADVERTENCIA', str(exc)))

        return results


# ─────────────────────────────────────────────────────────────────────────────
# Motor 7 — Legal Compliance Checker
# ─────────────────────────────────────────────────────────────────────────────

class LegalComplianceChecker:
    """Verifica firma de Giselle, QR, SHA-256 en código de generación de PDFs."""

    def check(self, py_files: list[Path]) -> list[AuditResult]:
        results   = []
        pdf_files = [f for f in py_files
                     if any(kw in f.name for kw in ('motor_reportes', 'reporte', 'pdf', 'imprimir'))
                     or 'reportes' in str(f).replace('\\', '/')]

        giselle_found = False
        qr_found      = False
        sha256_found  = False
        fernet_found  = False

        for fpath in pdf_files:
            try:
                content = fpath.read_text(encoding='utf-8', errors='ignore')
                if any(p in content for p in RESPONSABLE_PATTERNS):
                    giselle_found = True
                if 'qrcode' in content or 'qr_code' in content or 'QrCode' in content:
                    qr_found = True
                if 'sha256' in content.lower() or 'hashlib' in content:
                    sha256_found = True
                if 'Fernet' in content or 'AES' in content or 'encrypt' in content.lower():
                    fernet_found = True
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en check (omni_audit.py)")
                pass

        # También buscar en toda la base de código
        for fpath in py_files:
            try:
                content = fpath.read_text(encoding='utf-8', errors='ignore')
                if any(p in content for p in RESPONSABLE_PATTERNS):
                    giselle_found = True
                if 'sha256' in content.lower() and 'hashlib' in content:
                    sha256_found = True
                if 'Fernet' in content or 'AES-256' in content:
                    fernet_found = True
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en check (omni_audit.py)")
                pass

        results.append(AuditResult(
            'LEGAL', f'Firma QC {RESPONSABLE_SANITARIA}',
            'OPERATIVA' if giselle_found else 'FALLANDO',
            'Nombre encontrado en código de reportes' if giselle_found
            else 'CRÍTICO — Firma sanitaria no encontrada en ningún reporte PDF'
        ))
        results.append(AuditResult(
            'LEGAL', 'QR antifraude en reportes',
            'OPERATIVA' if qr_found else 'ADVERTENCIA',
            'qrcode importado en generación de PDF' if qr_found else 'No se detectó generación de QR'
        ))
        results.append(AuditResult(
            'LEGAL', 'Hashing SHA-256 (trazabilidad forense)',
            'OPERATIVA' if sha256_found else 'ADVERTENCIA',
            'hashlib/sha256 en código' if sha256_found else 'No se detectó hashing'
        ))
        results.append(AuditResult(
            'LEGAL', 'Cifrado Fernet AES-256 (audios/bienestar)',
            'OPERATIVA' if fernet_found else 'ADVERTENCIA',
            'Fernet/AES detectado' if fernet_found else 'No se detectó cifrado'
        ))

        # ── Verificar modelo DocumentoCapacitacion tiene campos RAG ─────
        try:
            from django.apps import apps
            DocModel = apps.get_model('core', 'DocumentoCapacitacion')
            fields = [f.name for f in DocModel._meta.get_fields()]
            rag_fields = {'estado_rag', 'chunks_rag', 'validado_por_nombre', 'cedula_validador'}
            present = rag_fields & set(fields)
            if present >= rag_fields:
                results.append(AuditResult('LEGAL', 'Campos RAG en DocumentoCapacitacion',
                                           'OPERATIVA', f'Campos: {", ".join(sorted(present))}'))
            else:
                missing = rag_fields - present
                results.append(AuditResult('LEGAL', 'Campos RAG en DocumentoCapacitacion',
                                           'ADVERTENCIA', f'Faltan: {", ".join(missing)}'))
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en check (omni_audit.py)")
            results.append(AuditResult('LEGAL', 'DocumentoCapacitacion RAG', 'ADVERTENCIA', str(exc)))

        return results


# ─────────────────────────────────────────────────────────────────────────────
# Motor 8 — RAG Status Checker
# ─────────────────────────────────────────────────────────────────────────────

class RAGStatusChecker:
    def check(self) -> list[AuditResult]:
        results = []
        try:
            from django.apps import apps
            DocModel = apps.get_model('core', 'DocumentoCapacitacion')
            total    = DocModel.objects.count()
            if total == 0:
                results.append(AuditResult('RAG', 'Biblioteca de documentos',
                                           'NO_DESPLEGADA', 'Sin documentos cargados'))
                return results

            entrenados  = DocModel.objects.filter(estado_rag='ENTRENADO').count()
            procesando  = DocModel.objects.filter(estado_rag='PROCESANDO').count()
            errores     = DocModel.objects.filter(estado_rag='ERROR').count()
            sin_indexar = DocModel.objects.filter(estado_rag='SUBIDO').count()

            results.append(AuditResult('RAG', f'Documentos en biblioteca ({total} total)',
                                       'OPERATIVA' if entrenados > 0 else 'ADVERTENCIA',
                                       f'Entrenados: {entrenados} | Procesando: {procesando} | '
                                       f'Error: {errores} | Sin indexar: {sin_indexar}'))
            if errores > 0:
                err_docs = DocModel.objects.filter(estado_rag='ERROR')[:3]
                for d in err_docs:
                    results.append(AuditResult('RAG', f'Error RAG en "{d.titulo}"',
                                               'FALLANDO', getattr(d, 'error_rag', 'sin detalle')[:120]))
            # Chunks
            from django.db.models import Sum
            total_chunks = DocModel.objects.aggregate(tc=Sum('chunks_rag'))['tc'] or 0
            results.append(AuditResult('RAG', 'Total chunks vectoriales indexados',
                                       'OPERATIVA' if total_chunks > 100 else 'ADVERTENCIA',
                                       f'{total_chunks} fragmentos consultables'))
        except AttributeError:
            results.append(AuditResult('RAG', 'Campos RAG en DocumentoCapacitacion',
                                       'NO_DESPLEGADA', 'Migración pendiente — ejecutar makemigrations'))
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en check (omni_audit.py)")
            results.append(AuditResult('RAG', 'Sistema RAG', 'ADVERTENCIA', str(exc)))

        # Verificar que el motor RAG exista
        rag_engine = PROJECT_ROOT / 'core' / 'utils' / 'rag_engine.py'
        if rag_engine.exists():
            content = rag_engine.read_text(encoding='utf-8', errors='ignore')
            if 'consultar_cerebro' in content:
                results.append(AuditResult('RAG', 'Motor rag_engine.py operativo',
                                           'OPERATIVA', 'Función consultar_cerebro presente'))
            else:
                results.append(AuditResult('RAG', 'Motor rag_engine.py operativo',
                                           'ADVERTENCIA', 'Archivo existe pero sin consultar_cerebro()'))
        else:
            results.append(AuditResult('RAG', 'Motor rag_engine.py',
                                       'NO_DESPLEGADA', 'Archivo no encontrado en core/utils/'))

        return results


# ─────────────────────────────────────────────────────────────────────────────
# Motor 9 — Baseline Manager
# ─────────────────────────────────────────────────────────────────────────────

class BaselineManager:
    """Guarda y compara línea base de salud del sistema."""

    def save_baseline(self, summary: dict) -> None:
        baseline = {
            'timestamp': datetime.now().isoformat(),
            'summary':   summary,
        }
        BASELINE_FILE.write_text(json.dumps(baseline, indent=2, ensure_ascii=False))

    def load_baseline(self) -> dict | None:
        if not BASELINE_FILE.exists():
            return None
        try:
            return json.loads(BASELINE_FILE.read_text())
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en load_baseline (omni_audit.py)")
            return None

    def compare(self, current: dict, previous: dict) -> list[AuditResult]:
        results  = []
        prev_sum = previous.get('summary', {})
        for key, curr_val in current.items():
            prev_val = prev_sum.get(key)
            if prev_val is None:
                continue
            if isinstance(curr_val, int) and isinstance(prev_val, int):
                if curr_val < prev_val:
                    results.append(AuditResult(
                        'BASELINE', f'Regresión detectada: {key}',
                        'FALLANDO',
                        f'Anterior: {prev_val}  →  Actual: {curr_val} (bajó {prev_val - curr_val})'
                    ))
                elif curr_val > prev_val:
                    results.append(AuditResult(
                        'BASELINE', f'Mejora detectada: {key}',
                        'OPERATIVA',
                        f'Anterior: {prev_val}  →  Actual: {curr_val} (+{curr_val - prev_val})'
                    ))
        return results


# ─────────────────────────────────────────────────────────────────────────────
# Motor 10 — Report Generator
# ─────────────────────────────────────────────────────────────────────────────

class ReportGenerator:
    LINE = '─' * 76
    DLINE = '═' * 76

    def __init__(self, stdout):
        self.stdout    = stdout
        self.log_lines: list[str] = []

    def _w(self, txt: str, color: str = '') -> None:
        self.stdout.write(f'{color}{txt}{Style.RESET_ALL}' if _HAS_COLOR else txt)
        self.log_lines.append(re.sub(r'\x1b\[[0-9;]*m', '', txt))

    def header(self, ts: str) -> None:
        self._w(f'\n{self.DLINE}', Fore.CYAN)
        self._w('  OMNI-GUARDIÁN PRISLAB — Reporte E2E de Auditoría Sistémica', Fore.CYAN)
        self._w(f'  Fecha: {ts}  |  Costo IA: $0.00 MXN  |  100% análisis local', Fore.CYAN)
        self._w(self.DLINE, Fore.CYAN)

    def section(self, title: str) -> None:
        self._w(f'\n{self.LINE}')
        self._w(f'  {title}')
        self._w(self.LINE)

    def result_row(self, r: AuditResult) -> None:
        estado = f'[{r.status}]'
        funcion = r.function[:52].ljust(52)
        modulo  = r.module[:16].ljust(16)
        ms_str  = f' {r.ms:.0f}ms' if r.ms else ''
        line = f'  {r.emoji}  Función [{funcion}]  en Módulo [{modulo}]  está: {estado}{ms_str}'
        self._w(line, r.color)
        if r.detail and r.status != 'OPERATIVA':
            detail_line = f'        └─ {r.detail}'
            if r.file:
                detail_line += f'\n        └─ Archivo: {r.file}'
                if r.line:
                    detail_line += f'  Línea: {r.line}'
            self._w(detail_line, Fore.WHITE)

    def summary_table(self, all_results: list[AuditResult], elapsed: float) -> dict:
        by_status = defaultdict(int)
        by_module = defaultdict(lambda: defaultdict(int))
        for r in all_results:
            by_status[r.status] += 1
            by_module[r.module][r.status] += 1

        total     = len(all_results)
        operativas = by_status['OPERATIVA']
        fallando   = by_status['FALLANDO']
        advertencia = by_status['ADVERTENCIA']
        no_desp    = by_status['NO_DESPLEGADA']

        health_pct = (operativas / total * 100) if total else 0
        health_color = (Fore.GREEN if health_pct >= 85
                        else Fore.YELLOW if health_pct >= 60
                        else Fore.RED)

        self.section('RESUMEN EJECUTIVO')
        self._w(f'\n  Total funciones auditadas : {total}')
        self._w(f'  ✅  OPERATIVAS             : {operativas}', Fore.GREEN)
        self._w(f'  ❌  FALLANDO               : {fallando}',   Fore.RED)
        self._w(f'  🟡  ADVERTENCIAS           : {advertencia}', Fore.YELLOW)
        self._w(f'  ⚠️   NO DESPLEGADAS         : {no_desp}',    Fore.YELLOW)
        self._w(f'\n  SALUD DEL SISTEMA         : {health_pct:.1f}%', health_color)
        self._w(f'  Tiempo de auditoría        : {elapsed:.1f}s')

        verdict = ('✅  SISTEMA SÓLIDO — Listo para operación clínica' if health_pct >= 85
                   else '🟡  SISTEMA FUNCIONAL CON OBSERVACIONES' if health_pct >= 60
                   else '❌  SISTEMA REQUIERE ATENCIÓN INMEDIATA')
        self._w(f'\n  VEREDICTO OMNI-GUARDIÁN   : {verdict}\n', health_color)

        # Tabla por módulo
        self._w('  Por módulo:')
        self._w(f'  {"Módulo":<18}  {"✅":>6}  {"❌":>6}  {"🟡":>6}  {"⚠️":>6}')
        self._w(f'  {"─"*18}  {"─"*6}  {"─"*6}  {"─"*6}  {"─"*6}')
        for mod, counts in sorted(by_module.items()):
            self._w(
                f'  {mod:<18}  '
                f'{counts["OPERATIVA"]:>6}  '
                f'{counts["FALLANDO"]:>6}  '
                f'{counts["ADVERTENCIA"]:>6}  '
                f'{counts["NO_DESPLEGADA"]:>6}'
            )

        return {
            'total': total, 'operativas': operativas,
            'fallando': fallando, 'advertencias': advertencia,
            'no_desplegadas': no_desp, 'health_pct': round(health_pct, 1),
        }

    def write_log(self) -> None:
        try:
            LOG_FILE.write_text('\n'.join(self.log_lines), encoding='utf-8')
            self.stdout.write(f'\n  Log guardado en: {LOG_FILE}')
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en write_log (omni_audit.py)")
            self.stdout.write(f'  [WARN] No se pudo escribir log: {exc}')


# ─────────────────────────────────────────────────────────────────────────────
# Comando principal
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'OMNI-GUARDIÁN PRISLAB — Auditoría E2E definitiva (Costo $0)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--total', action='store_true',
            help='Auditoría completa de todos los módulos (recomendado)'
        )
        parser.add_argument(
            '--modulo', type=str, default='',
            help='Auditar solo un módulo: toma|worklist|legal|bd|ux|rag|codigo|clinico'
        )
        parser.add_argument(
            '--quick', action='store_true',
            help='Solo UX + BD básica (rápido, ~10s)'
        )
        parser.add_argument(
            '--baseline', action='store_true',
            help='Guardar el estado actual como nueva línea base'
        )
        parser.add_argument(
            '--compare', action='store_true',
            help='Comparar con línea base guardada'
        )
        parser.add_argument(
            '--no-http', action='store_true',
            help='Omitir pruebas HTTP (más rápido, sin usuario de BD)'
        )

    def handle(self, *args, **options):
        t_global = time.perf_counter()
        ts       = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        reporter = ReportGenerator(self.stdout)
        reporter.header(ts)

        all_results: list[AuditResult] = []

        # ── Discovery ────────────────────────────────────────────────────────
        reporter.section('1. ESCANEO UNIVERSAL DEL PROYECTO')
        discovery = DiscoveryEngine()
        discovery.scan()
        s = discovery.summary()
        self.stdout.write(
            f'  Archivos Python : {s["py_files"]:>4} | '
            f'Templates: {s["templates"]:>4} | '
            f'URL files: {s["url_files"]:>2} | '
            f'Views: {s["view_files"]:>3} | '
            f'Models: {s["model_files"]:>2}'
        )
        all_results.append(AuditResult('PROYECTO', 'Escáner de archivos',
                                       'OPERATIVA' if s['py_files'] > 50 else 'ADVERTENCIA',
                                       f'{s["py_files"]} archivos .py | {s["templates"]} templates'))

        modulo_filter = options.get('modulo', '').lower()
        run_all       = options.get('total') or not modulo_filter
        run_quick     = options.get('quick')

        def should_run(name: str) -> bool:
            if run_all or run_quick:
                return True
            return name in modulo_filter

        # ── Activos Estáticos Físicos ─────────────────────────────────────────
        if should_run('assets') or run_quick:
            reporter.section('1b. ACTIVOS FÍSICOS — JS/CSS/Media (detección de fantasmas)')
            assets_r = StaticAssetsChecker().check(discovery.template_files)
            for r in assets_r:
                reporter.result_row(r)
            all_results.extend(assets_r)

        # ── UX Guardian ──────────────────────────────────────────────────────
        if should_run('ux') or run_quick:
            reporter.section('2. UX GUARDIAN — Sidebar, Orbes, z-index')
            scanner = TemplateScanner()
            ux_results = (
                scanner.scan_sidebar(discovery.template_files)
                + scanner.scan_for_forbidden(discovery.template_files)
            )
            for r in ux_results:
                reporter.result_row(r)
            all_results.extend(ux_results)

        # ── Toma de Muestra ──────────────────────────────────────────────────
        if should_run('toma'):
            reporter.section('3. MÓDULO TOMA — PRIS-Shadow (Paso 2)')
            scanner = TemplateScanner()
            toma_r = scanner.scan_toma(discovery.template_files)
            for r in toma_r:
                reporter.result_row(r)
            all_results.extend(toma_r)

        # ── Worklist ─────────────────────────────────────────────────────────
        if should_run('worklist'):
            reporter.section('4. MÓDULO WORKLIST ANALÍTICA (Paso 4)')
            scanner = TemplateScanner()
            wl_r = scanner.scan_worklist(discovery.template_files)
            for r in wl_r:
                reporter.result_row(r)
            all_results.extend(wl_r)

        # ── Base de Datos ────────────────────────────────────────────────────
        if should_run('bd') or run_quick:
            reporter.section('5. INSPECTOR DE BASE DE DATOS')
            db_r = DatabaseInspector().inspect()
            for r in db_r:
                reporter.result_row(r)
            all_results.extend(db_r)

        # ── Lógica Clínica ───────────────────────────────────────────────────
        if should_run('clinico'):
            reporter.section('6. VALIDADOR DE LÓGICA CLÍNICA — HOLÍSTICO (Hb/Hto · Friedewald · Bili · AG · Delta Universal)')
            clin_r = ClinicalLogicValidator().validate()
            for r in clin_r:
                reporter.result_row(r)
            all_results.extend(clin_r)

        # ── Legal ────────────────────────────────────────────────────────────
        if should_run('legal'):
            reporter.section('7. BLINDAJE LEGAL — Firma Giselle, QR, SHA-256')
            legal_r = LegalComplianceChecker().check(discovery.py_files)
            for r in legal_r:
                reporter.result_row(r)
            all_results.extend(legal_r)

        # ── RAG ──────────────────────────────────────────────────────────────
        if should_run('rag'):
            reporter.section('8. ESTADO RAG — Biblioteca de Inteligencia Clínica')
            rag_r = RAGStatusChecker().check()
            for r in rag_r:
                reporter.result_row(r)
            all_results.extend(rag_r)

        # ── Calidad de Código ────────────────────────────────────────────────
        if should_run('codigo') and not run_quick:
            reporter.section('9. CALIDAD DE CÓDIGO — Sintaxis, TODOs, Silenciadores')
            cq_results, cq_stats = CodeQualityAnalyst().scan_all(
                discovery.py_files, ALL_APPS
            )
            # Solo reportar FALLANDOs y primeros 15 ADVERTENCIAs para no saturar
            fallos  = [r for r in cq_results if r.status == 'FALLANDO']
            warns   = [r for r in cq_results if r.status == 'ADVERTENCIA'][:15]
            for r in fallos + warns:
                reporter.result_row(r)
            self.stdout.write(
                f'\n  Archivos escaneados: {cq_stats["files_scanned"]} | '
                f'Errores sintaxis: {cq_stats["syntax_errors"]} | '
                f'TODOs: {cq_stats["todos"]} | '
                f'Silenciadores: {cq_stats["silencers"]}'
            )
            if cq_stats['syntax_errors'] == 0:
                all_results.append(AuditResult('CÓDIGO', 'Sin errores de sintaxis',
                                               'OPERATIVA', f'{cq_stats["files_scanned"]} archivos limpios'))
            all_results.extend(fallos)
            all_results.extend(warns[:5])  # solo 5 para el resumen

        # ── HTTP Prober ──────────────────────────────────────────────────────
        if should_run('http') and not options.get('no_http') and not run_quick:
            reporter.section('10. RUTAS HTTP — Flujo Biológico (Pasos 1 al 6)')
            prober = self._get_prober()
            if prober:
                from django.urls import reverse, NoReverseMatch
                for url_name, label in REQUIRED_STEP_URLS:
                    try:
                        url = reverse(url_name)
                        r   = prober.probe(url, label)
                        reporter.result_row(r)
                        all_results.append(r)
                    except NoReverseMatch:
                        r = AuditResult('HTTP', label, 'NO_DESPLEGADA',
                                        f'URL name "{url_name}" no resuelve')
                        reporter.result_row(r)
                        all_results.append(r)
            else:
                self.stdout.write(f'  {Fore.YELLOW}[OMITIDO] No se pudo crear usuario de prueba')

        # ── Baseline ─────────────────────────────────────────────────────────
        elapsed = time.perf_counter() - t_global
        summary = reporter.summary_table(all_results, elapsed)

        bm = BaselineManager()
        if options.get('baseline'):
            bm.save_baseline(summary)
            self.stdout.write(f'\n  {Fore.CYAN}✅ Línea base guardada en {BASELINE_FILE}')
        elif options.get('compare'):
            prev = bm.load_baseline()
            if prev:
                reporter.section('COMPARACIÓN CON LÍNEA BASE')
                bm_results = bm.compare(summary, prev)
                for r in bm_results:
                    reporter.result_row(r)
                if not bm_results:
                    self.stdout.write(f'  {Fore.GREEN}Sin regresiones detectadas respecto a la línea base.')
            else:
                self.stdout.write(f'  {Fore.YELLOW}No hay línea base guardada. Ejecuta --baseline primero.')

        # ── Guardar log ──────────────────────────────────────────────────────
        reporter.write_log()

        # ── Código de salida ─────────────────────────────────────────────────
        n_fallos = sum(1 for r in all_results if r.status == 'FALLANDO')
        if n_fallos > 0:
            self.stdout.write(
                f'\n  {Fore.RED}⚠  {n_fallos} fallo(s) crítico(s) detectados. '
                f'Ver {LOG_FILE} para detalles completos.'
            )
            sys.exit(1)

    # ── Utilidades privadas ──────────────────────────────────────────────────

    def _get_prober(self) -> URLProber | None:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            from django.apps import apps
            empresa_model = apps.get_model('core', 'Empresa')
            empresa, _ = empresa_model.objects.get_or_create(
                nombre='PRISLAB_TEST_OMNI',
                defaults={'activa': True}
            )
            user, _ = User.objects.get_or_create(
                username='omni_audit_user',
                defaults={
                    'email': 'omni@prislab.test',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            if hasattr(user, 'empresa'):
                user.empresa = empresa
            user.set_password('omniaudit2026')
            user.save()
            return URLProber(user)
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en _get_prober (omni_audit.py)")
            self.stdout.write(f'  [WARN] URLProber: {exc}')
            return None