"""
core/services/bienestar_pris_hooks.py
════════════════════════════════════════════════════════════════════════════════
FASE 9 — Hooks de PRIS para el Módulo Bienestar Staff

REGLA DE ORO (INMUTABLE):
  PRIS solo puede ALERTAR a RRHH sobre riesgos detectados (nivel, tipo, fecha).
  PRIS NUNCA puede leer ni transmitir el contenido privado de:
    - DiarioEmocionalStaff.contenido
    - SesionCoachingStaff.notas_privadas
    - EvaluacionNOM035.respuestas_json

  Solo puede leer metadatos no sensibles:
    - humor_general (número 1-5)
    - nivel_estres (número 1-10)
    - nivel_riesgo (número 1-5)
    - fechas y conteos

Activación:
  Estos hooks se llaman automáticamente desde las vistas cuando se guarda
  una entrada del diario, se completa una evaluación, o hay patrón de ausencias.
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations
import logging

logger = logging.getLogger('core.bienestar.pris')

# Umbrales para alertas automáticas
UMBRAL_HUMOR_BAJO = 2          # humor ≤ 2 por N días consecutivos
UMBRAL_DIAS_HUMOR_BAJO = 5     # N días consecutivos
UMBRAL_ESTRES = 7              # estres ≥ 7 por N días
UMBRAL_DIAS_ESTRES = 5


def verificar_patrones_burnout(empleado_id: int, empresa_id: int):
    """
    Analiza metadatos del diario del empleado para detectar patrones de burnout.
    Llama a crear_alerta_burnout si se detecta riesgo.
    NO lee contenido cifrado.

    Ejecutar en background (thread o Celery) para no bloquear la vista.
    """
    import threading
    threading.Thread(
        target=_analizar_patrones_bg,
        args=(empleado_id, empresa_id),
        daemon=True,
    ).start()


def _analizar_patrones_bg(empleado_id: int, empresa_id: int):
    """Ejecutado en hilo daemon. Analiza solo metadatos."""
    try:
        from django.utils import timezone
        from datetime import timedelta

        # Los modelos solo estarán disponibles post-migración
        # Usar try/except para no crashear pre-migración
        try:
            DiarioEmocionalStaff = _get_model('DiarioEmocionalStaff')
        except LookupError:
            return  # Modelos no migrados aún

        fecha_limite = timezone.now().date() - timedelta(days=UMBRAL_DIAS_HUMOR_BAJO)
        entradas = (
            DiarioEmocionalStaff.objects
            .filter(empleado_id=empleado_id, fecha__gte=fecha_limite)
            .values('humor_general', 'nivel_estres', 'fecha')
            .order_by('-fecha')
        )

        if not entradas.exists():
            return

        lista = list(entradas)
        dias = len(lista)

        # ── Patrón 1: Humor bajo sostenido ───────────────────────────────────
        if dias >= UMBRAL_DIAS_HUMOR_BAJO:
            humor_prom = sum(e['humor_general'] for e in lista) / dias
            if humor_prom <= UMBRAL_HUMOR_BAJO:
                _crear_alerta_si_no_existe(
                    empleado_id, empresa_id,
                    tipo='HUMOR_BAJO', nivel=3,
                )

        # ── Patrón 2: Estrés elevado sostenido ───────────────────────────────
        if dias >= UMBRAL_DIAS_ESTRES:
            estres_prom = sum(e['nivel_estres'] for e in lista) / dias
            if estres_prom >= UMBRAL_ESTRES:
                _crear_alerta_si_no_existe(
                    empleado_id, empresa_id,
                    tipo='ESTRES_ALTO', nivel=4,
                )

    except Exception as exc:
        logger.warning(f'[Bienestar] _analizar_patrones_bg error: {exc}')


def notificar_riesgo_nom035(
    empleado_id: int,
    empresa_id: int,
    nivel_riesgo: int,
    periodo: str,
):
    """
    Llamar cuando se completa una EvaluacionNOM035 con riesgo ≥ 3.
    Crea AlertaBurnout y notifica al RRHH.
    """
    if nivel_riesgo < 3:
        return

    _crear_alerta_si_no_existe(
        empleado_id, empresa_id,
        tipo='NOM035_RIESGO', nivel=nivel_riesgo,
    )
    _notificar_rrhh(empleado_id, empresa_id, 'NOM035_RIESGO', nivel_riesgo)


def _crear_alerta_si_no_existe(
    empleado_id: int,
    empresa_id: int,
    tipo: str,
    nivel: int,
):
    """Crea AlertaBurnout evitando duplicados recientes (última semana)."""
    try:
        from django.utils import timezone
        from datetime import timedelta
        AlertaBurnout = _get_model('AlertaBurnout')

        semana_atras = timezone.now() - timedelta(days=7)
        existe = AlertaBurnout.objects.filter(
            empleado_id=empleado_id,
            tipo=tipo,
            fecha__gte=semana_atras,
        ).exists()

        if not existe:
            AlertaBurnout.objects.create(
                empleado_id=empleado_id,
                empresa_id=empresa_id,
                tipo=tipo,
                nivel_riesgo=nivel,
            )
            logger.info(f'[Bienestar] AlertaBurnout creada: tipo={tipo} nivel={nivel} empleado={empleado_id}')
            _notificar_rrhh(empleado_id, empresa_id, tipo, nivel)

    except LookupError:
        pass  # Modelos no disponibles aún
    except Exception as exc:
        logger.warning(f'[Bienestar] Error creando alerta: {exc}')


def _notificar_rrhh(empleado_id: int, empresa_id: int, tipo: str, nivel: int):
    """
    Notifica al RRHH sobre una alerta de burnout.
    El mensaje solo contiene: tipo de riesgo y nivel.
    NUNCA revela contenido privado.
    """
    try:
        from core.views.autenticacion_2fa import _notificar_telegram
        from core.models import Usuario

        empleado = Usuario.objects.filter(pk=empleado_id).select_related('empresa').first()
        if not empleado:
            return

        nombre_privado = empleado.get_full_name() or empleado.username
        empresa_nombre = getattr(empleado.empresa, 'nombre', 'Empresa') if empleado.empresa else ''

        mensaje = (
            f'🟡 *ALERTA BIENESTAR STAFF — NOM-035*\n'
            f'Empresa: {empresa_nombre}\n'
            f'Tipo: {tipo}\n'
            f'Nivel de riesgo: {nivel}/5\n'
            f'_El contenido privado está protegido. RRHH debe contactar al empleado._'
        )
        _notificar_telegram(mensaje)
    except Exception as exc:
        logger.warning(f'[Bienestar] Error notificando RRHH: {exc}')


def _get_model(nombre: str):
    """Lazy import para modelos que pueden no estar migrados."""
    from django.apps import apps
    return apps.get_model('core', nombre)
