"""
Servicio de Cadena de Frío ISO 15189
═════════════════════════════════════
Valida la temperatura de traslado de muestras entre sucursales.
Rango aceptado: 2°C – 8°C (refrigeración estándar de muestras biológicas).
Si sale del rango → bloqueo + alerta al Químico Jefe.
"""
import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger('core.cadena_frio')

TEMP_MIN = Decimal('2.0')
TEMP_MAX = Decimal('8.0')


def validar_temperatura(temperatura: float | str | Decimal) -> dict[str, Any]:
    """
    Valida si una temperatura está dentro del rango aceptado para
    traslado de muestras biológicas (2-8°C).
    Retorna dict con: valida, temperatura, mensaje, nivel.
    """
    try:
        temp = Decimal(str(temperatura))
    except Exception:
        return {
            'valida': False,
            'temperatura': None,
            'mensaje': 'Temperatura inválida. Ingrese un valor numérico.',
            'nivel': 'ERROR',
        }

    if temp < TEMP_MIN:
        return {
            'valida': False,
            'temperatura': float(temp),
            'mensaje': (
                f'ALERTA: Temperatura demasiado BAJA ({temp}°C). '
                f'Rango aceptado: {TEMP_MIN}°C – {TEMP_MAX}°C. '
                'Riesgo de congelación de muestras.'
            ),
            'nivel': 'CRITICO',
        }

    if temp > TEMP_MAX:
        return {
            'valida': False,
            'temperatura': float(temp),
            'mensaje': (
                f'ALERTA: Temperatura demasiado ALTA ({temp}°C). '
                f'Rango aceptado: {TEMP_MIN}°C – {TEMP_MAX}°C. '
                'Las muestras pueden estar comprometidas.'
            ),
            'nivel': 'CRITICO',
        }

    return {
        'valida': True,
        'temperatura': float(temp),
        'mensaje': f'Temperatura correcta ({temp}°C). Cadena de frío certificada.',
        'nivel': 'OK',
    }


def registrar_lectura_temperatura(
    transferencia_id: int,
    temperatura: float,
    usuario,
    metodo: str = 'MANUAL',
    sensor_id: str = ''
) -> dict[str, Any]:
    """
    Registra una lectura de temperatura en una TransferenciaInventario.
    Guarda en el campo metadata_json (o crea log de auditoría).
    Retorna el resultado de la validación.
    """
    from django.utils import timezone
    import json

    resultado_validacion = validar_temperatura(temperatura)

    try:
        from logistica.models import TransferenciaInventario, LogTransferencia

        transferencia = TransferenciaInventario.objects.get(id=transferencia_id)

        # Guardar en campo de temperatura si existe, o en observaciones_origen
        comentario = (
            f'[CADENA FRIO] Temp: {temperatura}°C | Metodo: {metodo} | '
            f'Sensor: {sensor_id or "manual"} | '
            f'Resultado: {resultado_validacion["nivel"]} | '
            f'Usuario: {usuario} | '
            f'Hora: {timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")}'
        )

        LogTransferencia.objects.create(
            transferencia=transferencia,
            usuario=usuario,
            estado_anterior=transferencia.estado,
            estado_nuevo=transferencia.estado,
            comentario=comentario,
        )

        if not resultado_validacion['valida']:
            _alertar_quimico_jefe(transferencia, temperatura, resultado_validacion, usuario)

    except Exception as exc:
        logger.error(f'cadena_frio - registrar_lectura: {exc}')
        resultado_validacion['error'] = str(exc)

    return resultado_validacion


def _alertar_quimico_jefe(transferencia, temperatura, resultado, usuario):
    """Genera notificación urgente al Químico Jefe cuando la cadena de frío se rompe."""
    try:
        from core.models import NotificacionSistema, Usuario
        quimicos = Usuario.objects.filter(
            empresa=transferencia.empresa,
            rol__in=['QUIMICO', 'ADMIN', 'DIRECTOR'],
            is_active=True,
        )
        mensaje = (
            f'ALERTA CADENA FRIO: Traslado {transferencia.folio} — '
            f'Temperatura {temperatura}°C fuera de rango (2-8°C). '
            f'Reportado por: {usuario}. '
            f'{resultado["mensaje"]}'
        )
        for quimico in quimicos[:5]:
            NotificacionSistema.objects.create(
                empresa=transferencia.empresa,
                destinatario=quimico,
                tipo='CRITICO',
                modulo='LABORATORIO',
                titulo='CADENA DE FRIO COMPROMETIDA',
                mensaje=mensaje,
                enlace=f'/logistica/transferencias/{transferencia.id}/',
            )
        logger.warning(f'Alerta cadena frio enviada: {transferencia.folio} — {temperatura}°C')
    except Exception as exc:
        logger.error(f'cadena_frio - _alertar_quimico_jefe: {exc}')
