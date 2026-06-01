"""
Vistas para Trazabilidad Legal (Consentimientos).
REGLA: Ninguna orden puede pasar a 'Validada' sin el check de firma de consentimiento.
"""
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json

from core.models import OrdenDeServicio, ConsentimientoInformado, RegistroAuditoriaConsentimiento


@login_required
@require_http_methods(["POST"])
def api_guardar_consentimiento(request, orden_id):
    """API para guardar consentimiento firmado."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    try:
        orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)
        data = json.loads(request.body)

        firma_digital = data.get('firma_digital', '')
        acepta_privacidad = data.get('acepta_privacidad', False)
        acepta_procesamiento = data.get('acepta_procesamiento', False)

        if not firma_digital:
            return JsonResponse({'status': 'error', 'mensaje': 'Debe proporcionar una firma digital'}, status=400)
        if not acepta_privacidad or not acepta_procesamiento:
            return JsonResponse({'status': 'error', 'mensaje': 'Debe aceptar privacidad y procesamiento'}, status=400)

        with transaction.atomic():
            consentimiento, creado = ConsentimientoInformado.objects.get_or_create(
                orden=orden,
                defaults={
                    'empresa': empresa,
                    'paciente': orden.paciente,
                    'firma_digital': firma_digital,
                    'acepta_privacidad': acepta_privacidad,
                    'acepta_procesamiento': acepta_procesamiento,
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                }
            )

            if not creado:
                consentimiento.firma_digital = firma_digital
                consentimiento.acepta_privacidad = acepta_privacidad
                consentimiento.acepta_procesamiento = acepta_procesamiento
                consentimiento.ip_address = request.META.get('REMOTE_ADDR')
                consentimiento.user_agent = request.META.get('HTTP_USER_AGENT', '')

            consentimiento.hash_firma = consentimiento.calcular_hash()
            consentimiento.save()

            RegistroAuditoriaConsentimiento.objects.create(
                consentimiento=consentimiento,
                accion='CREADO' if creado else 'MODIFICADO',
                usuario=request.user,
                descripcion=f'Consentimiento {"creado" if creado else "modificado"} para orden {orden.folio_orden}',
                datos_nuevos={
                    'acepta_privacidad': acepta_privacidad,
                    'acepta_procesamiento': acepta_procesamiento,
                    'hash_firma': consentimiento.hash_firma
                },
                ip_address=request.META.get('REMOTE_ADDR')
            )

        return JsonResponse({
            'status': 'success',
            'mensaje': 'Consentimiento guardado correctamente',
            'consentimiento_id': consentimiento.id,
            'hash_firma': consentimiento.hash_firma
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_verificar_consentimiento(request, orden_id):
    """API para verificar si una orden tiene consentimiento firmado."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    try:
        orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)
        try:
            c = ConsentimientoInformado.objects.get(orden=orden)
            return JsonResponse({
                'status': 'success',
                'tiene_consentimiento': True,
                'fecha_firma': c.fecha_firma.isoformat(),
                'integridad_verificada': c.verificar_integridad(),
                'acepta_privacidad': c.acepta_privacidad,
                'acepta_procesamiento': c.acepta_procesamiento
            })
        except ConsentimientoInformado.DoesNotExist:
            return JsonResponse({
                'status': 'success',
                'tiene_consentimiento': False,
                'mensaje': 'La orden no tiene consentimiento firmado'
            })
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


def validar_consentimiento_requerido(orden):
    """Helper: valida que una orden tenga consentimiento antes de validar."""
    try:
        c = ConsentimientoInformado.objects.get(orden=orden)
        if not c.firma_digital:
            return False, 'La orden no tiene firma digital registrada'
        if not c.acepta_privacidad:
            return False, 'El paciente no ha aceptado el aviso de privacidad'
        if not c.acepta_procesamiento:
            return False, 'El paciente no ha aceptado el procesamiento de datos'
        if not c.verificar_integridad():
            return False, 'La firma digital ha sido alterada. Integridad comprometida.'
        return True, 'Consentimiento valido'
    except ConsentimientoInformado.DoesNotExist:
        return False, 'La orden no tiene consentimiento informado firmado'
