"""
core/views/cron_tasks.py
━━━━━━━━━━━━━━━━━━━━━━━━
Endpoints HTTP para tareas programadas externas o internas.
Cada ruta llama a un management command interno.
Protección: cabecera X-Cron-Secret debe coincidir con la variable de entorno CRON_SECRET.
Si CRON_SECRET no está configurada, solo se aceptan peticiones con cabeceras de cron conocidas.
"""
import logging
import os
import secrets

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('core.cron')

_CRON_SECRET = os.environ.get('CRON_SECRET', '')


def _verificar_cron(request) -> bool:
    """Valida que la petición venga de un scheduler autorizado (por header secreto)."""
    if _CRON_SECRET:
        provided_secret = request.headers.get('X-Cron-Secret', '')
        return secrets.compare_digest(provided_secret, _CRON_SECRET)

    if not settings.DEBUG:
        logger.error(
            'Cron rechazado: CRON_SECRET no configurado en entorno no-debug para %s',
            request.path,
        )
        return False

    # Solo en desarrollo permitimos el fallback por headers conocidos del scheduler.
    return bool(request.headers.get('X-CloudScheduler-JobName') or
                request.headers.get('X-Appengine-Cron'))


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def cron_check_metrologia(request):
    """
    Cron diario → 08:00 AM.
    Ejecuta: python manage.py check_certificados_metrologicos
    Alerta al Director 30 días antes del vencimiento de certificados ISO/IQ/OQ/PQ.
    """
    if not _verificar_cron(request):
        logger.warning('cron_check_metrologia: acceso no autorizado desde %s', request.META.get('REMOTE_ADDR'))
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=403)

    resultados = []
    errores = []
    try:
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command('check_certificados_metrologicos', stdout=out, stderr=out)
        output = out.getvalue()
        resultados.append(output[:500] if output else 'Completado sin output.')
        logger.info('cron_check_metrologia ejecutado correctamente. Output: %s', output[:200])
    except Exception as e:
        logger.error('cron_check_metrologia error: %s', e, exc_info=True)
        errores.append(str(e))

    return JsonResponse({
        'ok': len(errores) == 0,
        'tarea': 'check_certificados_metrologicos',
        'resultados': resultados,
        'errores': errores,
    })


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def cron_check_stock_critico(request):
    """
    Cron diario → 07:00 AM.
    Detecta silos con stock por debajo del mínimo y genera notificaciones al Director.
    """
    if not _verificar_cron(request):
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=403)

    alertas = []
    errores = []
    try:
        from core.models import Empresa

        # Silos: (modelo catálogo, filtro Q sobre lotes, etiqueta)
        # Campo real en lotes: cantidad_actual (no existe cantidad_disponible).
        # LAB: solo ACTIVO — coherente con descuento FEFO (`inventario.signals`).
        from django.db.models import Q

        SILOS_CONFIG = []
        try:
            from inventario.models import CatalogoReactivoLab

            SILOS_CONFIG.append((CatalogoReactivoLab, Q(lotes__estado='ACTIVO'), 'LAB'))
        except ImportError:
            pass
        try:
            from inventario.models import CatalogoInsumoConsultorio

            SILOS_CONFIG.append(
                (CatalogoInsumoConsultorio, Q(lotes__cantidad_actual__gt=0), 'CONSULTORIO')
            )
        except ImportError:
            pass
        try:
            from inventario.models import CatalogoInsumoGeneral

            SILOS_CONFIG.append(
                (CatalogoInsumoGeneral, Q(lotes__cantidad_actual__gt=0), 'GENERAL')
            )
        except ImportError:
            pass

        from inventario.services.critical_stock import queryset_items_bajo_stock_minimo

        empresas = Empresa.objects.filter(activa=True)
        for empresa in empresas:
            for ModeloCatalogo, filtro_lotes, nombre_silo in SILOS_CONFIG:
                try:
                    criticos = queryset_items_bajo_stock_minimo(
                        empresa, ModeloCatalogo, filtro_lotes
                    )
                    for item in criticos:
                        stock_actual = float(item.stock_total or 0)
                        stock_min = float(item.stock_minimo or 0)
                        alertas.append({
                            'empresa': empresa.nombre,
                            'silo': nombre_silo,
                            'item': item.nombre,
                            'stock': stock_actual,
                            'minimo': stock_min,
                        })

                        # Crear NotificacionDiscrepancia para el War Room
                        # Solo si no existe ya una alerta activa para este mismo ítem
                        try:
                            from inventario.models import NotificacionDiscrepancia
                            titulo_alerta = f'[{nombre_silo}] Stock crítico: {item.nombre}'
                            existe = NotificacionDiscrepancia.objects.filter(
                                empresa=empresa,
                                tipo='STOCK_CRITICO',
                                titulo=titulo_alerta,
                                resuelta=False,
                            ).exists()
                            if not existe:
                                NotificacionDiscrepancia.objects.create(
                                    empresa=empresa,
                                    tipo='STOCK_CRITICO',
                                    nivel='CRITICO',
                                    titulo=titulo_alerta,
                                    detalle=(
                                        f'Stock actual: {stock_actual:.1f} | '
                                        f'Mínimo requerido: {stock_min:.1f} | '
                                        f'Generado por cron automático.'
                                    ),
                                    resuelta=False,
                                )
                        except Exception as e_notif:
                            logger.debug(
                                'cron_check_stock: no se pudo crear NotificacionDiscrepancia: %s', e_notif
                            )
                except Exception as e:
                    logger.warning(
                        'cron_check_stock_critico silo-%s empresa %s: %s',
                        nombre_silo, empresa.id, e
                    )

        logger.info('cron_check_stock_critico: %d alertas en %d silos', len(alertas), len(SILOS_CONFIG))
    except Exception as e:
        logger.error('cron_check_stock_critico error global: %s', e, exc_info=True)
        errores.append(str(e))

    return JsonResponse({
        'ok': len(errores) == 0,
        'tarea': 'check_stock_critico',
        'alertas': alertas[:100],
        'errores': errores,
        'timestamp': __import__('django.utils.timezone', fromlist=['timezone']).timezone.now().isoformat(),
    })


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def cron_verify_escudo_clinico(request):
    """
    Cron diario — verifica PRISLAB_ESCUDO_USUARIO_ID (pánico / NotificacionPanico).
    Respuesta 503 si el usuario no existe o está inactivo (alertas en Cloud Monitoring).
    """
    if not _verificar_cron(request):
        logger.warning(
            'cron_verify_escudo_clinico: acceso no autorizado desde %s',
            request.META.get('REMOTE_ADDR'),
        )
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=403)

    from core.utils.escudo_clinico_check import verificar_escudo_clinico

    ok, msg = verificar_escudo_clinico()
    if ok:
        logger.info('cron_verify_escudo_clinico: %s', msg)
        return JsonResponse({'ok': True, 'mensaje': msg})

    logger.error('cron_verify_escudo_clinico FALLO: %s', msg)
    return JsonResponse({'ok': False, 'error': msg}, status=503)
