"""
═══════════════════════════════════════════════════════════════════════════════
MIDDLEWARE DE BLINDAJE v2.0 — Expediente Médico Legalmente Inexpugnable
═══════════════════════════════════════════════════════════════════════════════

Este middleware implementa la Capa de Inmutabilidad:
- Captura snapshots JSONB de cada cambio en notas SOAP
- Mantiene encadenamiento SHA256 tipo blockchain
- Bloquea modificaciones a notas selladas

Fórmula de hash: SHA256(Snapshot + Hash_Anterior + Timestamp)
═══════════════════════════════════════════════════════════════════════════════
"""

import hashlib
import json
import logging
from datetime import datetime
from django.utils import timezone

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from core.models import NotaClinicaSOAP, ExpedienteNotaSHA, NotaClinicaSellar

logger = logging.getLogger(__name__)


class BlindajeExpedienteMiddleware:
    """
    Middleware de Django para proteger el expediente médico.
    
    Intercepta requests de modificación a notas SOAP selladas
    y verifica la integridad de la cadena de hashes.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Verificar si es un intento de modificar nota sellada
        if request.method in ['POST', 'PUT', 'PATCH']:
            self._verificar_permiso_modificacion(request)
        
        response = self.get_response(request)
        return response
    
    def _verificar_permiso_modificacion(self, request):
        """
        Verifica que no se intente modificar una nota sellada.
        Solo permite modificaciones si el usuario tiene permiso especial
        de "desbloqueo forense" (con auditoría completa).
        """
        # Detectar si es una URL de edición de nota SOAP
        path = request.path
        if '/nota/' in path or '/soap/' in path or '/consulta/' in path:
            nota_id = self._extraer_nota_id(path, request)
            if nota_id:
                try:
                    sello = NotaClinicaSellar.objects.filter(
                        nota_soap_id=nota_id
                    ).first()
                    
                    if sello and sello.estado_sello == 'SELLADA':
                        # Verificar si tiene permiso de desbloqueo forense
                        if not request.user.has_perm('core.desbloquear_nota_sellada'):
                            logger.warning(
                                f"[BLINDAJE] Intento de modificación de nota sellada #{nota_id} "
                                f"por usuario {request.user.username} SIN PERMISO"
                            )
                            raise PermissionDenied(
                                "Esta nota está sellada e inmutable. "
                                "Contacte al administrador para desbloqueo forense."
                            )
                        else:
                            logger.info(
                                f"[BLINDAJE] Desbloqueo forense de nota #{nota_id} "
                                f"por {request.user.username}"
                            )
                except Exception as e:
                    logger.error(f"[BLINDAJE] Error verificando permisos: {e}")
    
    def _extraer_nota_id(self, path, request):
        """Extrae el ID de la nota de la URL o del body."""
        import re
        
        # Intentar extraer de la URL /nota/<id>/
        match = re.search(r'/(?:nota|soap|consulta)/(\d+)', path)
        if match:
            return int(match.group(1))
        
        # Intentar extraer del POST
        if request.method in ('POST', 'PUT', 'PATCH'):
            nota_id = request.POST.get('nota_id') or request.POST.get('soap_id')
            if nota_id:
                try:
                    return int(nota_id)
                except (ValueError, TypeError):
                    return None
        
        return None


class SnapshotMiddleware:
    """
    Middleware para capturar metadatos de request (IP, User-Agent)
    para incluirlos en los snapshots SHA.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Almacenar metadatos en el request para uso posterior
        request._blindaje_metadata = {
            'ip_origen': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            'timestamp_middleware': timezone.localtime(timezone.now()).isoformat(),
        }
        
        response = self.get_response(request)
        return response
    
    def _get_client_ip(self, request):
        """
        Obtiene la IP real del cliente. Usa REMOTE_ADDR (la IP que Nginx
        ve directamente, no falsificable por el cliente) porque este valor
        se usa como evidencia forense/legal (NOM-004) — no debe depender
        de un header que el cliente puede manipular.
        """
        return request.META.get('REMOTE_ADDR', '')


# =============================================================================
# SEÑALES DE BLINDAJE — Snapshots Automáticos
# =============================================================================

@receiver(pre_save, sender=NotaClinicaSOAP)
def verificar_inmutabilidad_pre_save(sender, instance, **kwargs):
    """
    Señal pre_save: Verifica que no se modifique una nota sellada.
    """
    if instance.pk:
        try:
            sello = NotaClinicaSellar.objects.filter(nota_soap=instance).first()
            if sello and sello.estado_sello == 'SELLADA':
                # Obtener valores actuados de la BD
                actual = NotaClinicaSOAP.objects.get(pk=instance.pk)
                
                # Comparar campos críticos
                campos_criticos = ['subjetivo', 'objetivo', 'analisis', 'plan', 
                                   'diagnostico_principal', 'diagnosticos_secundarios']
                
                cambios = []
                for campo in campos_criticos:
                    old = getattr(actual, campo, None)
                    new = getattr(instance, campo, None)
                    if old != new:
                        cambios.append(campo)
                
                if cambios:
                    logger.error(
                        f"[BLINDAJE] Intento de modificar nota sellada #{instance.pk} "
                        f"en campos: {', '.join(cambios)}"
                    )
                    raise PermissionDenied(
                        f"No se puede modificar una nota sellada. "
                        f"Campos bloqueados: {', '.join(cambios)}"
                    )
        except NotaClinicaSellar.DoesNotExist:
            pass
        except NotaClinicaSOAP.DoesNotExist:
            pass


@receiver(post_save, sender=NotaClinicaSOAP)
def crear_snapshot_automatico(sender, instance, created, **kwargs):
    """
    Señal post_save: Crea automáticamente un ExpedienteNotaSHA
    cada vez que se guarda una nota SOAP.
    """
    try:
        # Verificar si la nota está sellada
        sello = getattr(instance, 'sello_firma', None)
        if sello and sello.estado_sello == 'SELLADA':
            logger.info(f"[BLINDAJE] Nota #{instance.pk} sellada, no se crea snapshot adicional")
            return
        
        # Obtener metadatos del request si existen
        from django.http import HttpRequest
        request = kwargs.get('request', None)
        
        ip_origen = None
        user_agent = None
        
        # Intentar obtener de thread-local si está disponible
        try:
            from threading import local
            _thread_locals = local()
            if hasattr(_thread_locals, 'request'):
                request = _thread_locals.request
                ip_origen = _get_ip_from_request(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        except Exception:
            pass
        
        # Determinar estado
        estado = 'BORRADOR' if created else 'PRELIMINAR'
        
        # Calcular siguiente versión
        ultima_version = ExpedienteNotaSHA.objects.filter(
            nota_soap=instance
        ).order_by('-version').first()
        
        version = (ultima_version.version + 1) if ultima_version else 1
        hash_anterior = ultima_version.hash_sha256 if ultima_version else None
        
        # Generar snapshot
        snapshot = _generar_snapshot_jsonb(instance)
        
        # Crear expediente SHA
        expediente = ExpedienteNotaSHA.objects.create(
            nota_soap=instance,
            empresa=instance.empresa,
            paciente=instance.paciente,
            medico=instance.medico,
            version=version,
            snapshot_jsonb=snapshot,
            estado_nota=estado,
            hash_anterior=hash_anterior,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
        
        logger.info(
            f"[BLINDAJE] Snapshot creado para nota #{instance.pk} "
            f"v{version} hash={expediente.hash_sha256[:16]}..."
        )
        
    except Exception as e:
        logger.error(f"[BLINDAJE] Error creando snapshot: {e}", exc_info=True)


def _generar_snapshot_jsonb(nota):
    """
    Genera un snapshot JSONB completo de la nota SOAP.
    
    ⚠️ SERIALIZACIÓN CANÓNICA: Usamos sort_keys=True y separators=(',', ':')
    para garantizar que el hash sea idéntico independientemente del orden
    de inserción de las claves en el diccionario.
    """
    snapshot = {
        'id': nota.id,
        'paciente_id': nota.paciente_id,
        'empresa_id': nota.empresa_id,
        'medico_id': nota.medico_id,
        'subjetivo': nota.subjetivo,
        'objetivo': nota.objetivo,
        'analisis': nota.analisis,
        'plan': nota.plan,
        'diagnostico_principal': nota.diagnostico_principal,
        'diagnosticos_secundarios': nota.diagnosticos_secundarios,
        'archivos_adjuntos': nota.archivos_adjuntos,
        'fecha_consulta': nota.fecha_consulta.isoformat() if nota.fecha_consulta else None,
        'ultima_modificacion': nota.ultima_modificacion.isoformat() if nota.ultima_modificacion else None,
        'snapshot_generado_en': timezone.localtime(timezone.now()).isoformat(),
        'version_snapshot': '2.0',
    }
    
    # Serialización canónica: orden consistente de claves y separadores mínimos
    return json.loads(
        json.dumps(snapshot, sort_keys=True, separators=(',', ':'), default=str)
    )


def _get_ip_from_request(request):
    """Utility para obtener IP del request. Usa REMOTE_ADDR (no falsificable) — este valor es evidencia forense."""
    if not request:
        return None
    return request.META.get('REMOTE_ADDR')


# =============================================================================
# API DE VERIFICACIÓN DE INTEGRIDAD
# =============================================================================

def verificar_cadena_integridad(nota_soap_id):
    """
    Verifica la integridad completa de la cadena de hashes de una nota.
    Retorna dict con resultado de auditoría.
    """
    expedientes = ExpedienteNotaSHA.objects.filter(
        nota_soap_id=nota_soap_id
    ).order_by('version')
    
    if not expedientes:
        return {
            'valido': False,
            'error': 'No hay expedientes para esta nota',
            'versiones_verificadas': 0,
        }
    
    resultados = []
    hash_esperado = None
    todas_validas = True
    
    for exp in expedientes:
        # Verificar hash individual
        hash_valido = exp.verificar_integridad()
        
        # Verificar encadenamiento
        if exp.version == 1:
            cadena_valida = exp.hash_anterior is None
        else:
            cadena_valida = exp.hash_anterior == hash_esperado
        
        resultado = {
            'version': exp.version,
            'hash': exp.hash_sha256[:16] + '...',
            'hash_valido': hash_valido,
            'cadena_valida': cadena_valida,
            'timestamp': exp.timestamp_creacion.isoformat(),
        }
        resultados.append(resultado)
        
        if not hash_valido or not cadena_valida:
            todas_validas = False
        
        hash_esperado = exp.hash_sha256
    
    return {
        'valido': todas_validas,
        'nota_soap_id': nota_soap_id,
        'total_versiones': len(expedientes),
        'versiones_verificadas': len(resultados),
        'detalle': resultados,
    }


def api_verificar_integridad(request, nota_id):
    """
    API endpoint para verificar integridad de una nota.
    """
    from django.http import JsonResponse
    
    if not request.user.has_perm('core.ver_historial_cambios'):
        return JsonResponse({'error': 'Sin permiso'}, status=403)
    
    resultado = verificar_cadena_integridad(nota_id)
    return JsonResponse(resultado)
