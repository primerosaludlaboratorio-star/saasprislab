"""
═══════════════════════════════════════════════════════════════════════════════
VISTAS DE BLINDAJE v2.0 — Firma PIN-LAB y Gestión de Sellos
═══════════════════════════════════════════════════════════════════════════════

Endpoints para:
1. Pre-sellar nota (marcar como pendiente de firma)
2. Sellar con PIN-LAB (firma electrónica simple)
3. Verificar integridad de nota
4. Desbloqueo forense (con permisos especiales)
═══════════════════════════════════════════════════════════════════════════════
"""

import hashlib
import json
import logging
from datetime import datetime
from django.utils import timezone

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings

from core.models import (
    NotaClinicaSOAP, NotaClinicaSellar, ExpedienteNotaSHA,
    Medico, Paciente, Receta, CatalogoCIE10
)
from core.middleware.blindaje_expediente import verificar_cadena_integridad
from core.utils.empresa_request import empresa_efectiva_request

logger = logging.getLogger(__name__)


# =============================================================================
# 1. PRE-SELLAR NOTA (Marcar como pendiente de firma)
# =============================================================================

@login_required
@require_POST
def pre_sellar_nota(request, nota_id):
    """
    Marca una nota como 'pre-sellada', pendiente de confirmación con PIN.
    Valida que el médico tenga cédula profesional configurada.
    """
    try:
        _emp = empresa_efectiva_request(request)
        nota = get_object_or_404(
            NotaClinicaSOAP.objects.select_related('medico', 'paciente'),
            id=nota_id,
            empresa=_emp,
        )
        
        # Verificar que el médico de la nota coincida con el usuario
        if nota.medico != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Solo el médico autor de la nota puede sellarla'
            }, status=403)
        
        # Obtener perfil de médico
        medico_profile = getattr(request.user, 'medico_profile', None)
        if not medico_profile:
            return JsonResponse({
                'success': False,
                'error': 'El usuario no tiene perfil de médico configurado'
            }, status=400)
        
        # Verificar que tenga PIN configurado
        if not medico_profile.lab_validation_pin_hash:
            return JsonResponse({
                'success': False,
                'error': 'Debe configurar su PIN-LAB antes de sellar notas',
                'requiere_configurar_pin': True
            }, status=400)
        
        # Verificar cédula validada (para recetas)
        if not medico_profile.cedula_validada:
            messages.warning(request, 
                'Advertencia: Su cédula profesional no está validada. '
                'No podrá generar recetas hasta completar la validación.')
        
        with transaction.atomic():
            # Obtener o crear sello
            sello, created = NotaClinicaSellar.objects.get_or_create(
                nota_soap=nota,
                defaults={
                    'estado_sello': 'PRE_SELLADA',
                    'medico_firmante': request.user,
                    'timestamp_pre_sellado': timezone.localtime(timezone.now()),
                    'cedula_profesional': medico_profile.cedula_profesional,
                    'especialidad': medico_profile.especialidad,
                }
            )
            
            if not created:
                if sello.estado_sello == 'SELLADA':
                    return JsonResponse({
                        'success': False,
                        'error': 'La nota ya está sellada e inmutable'
                    }, status=400)
                
                sello.estado_sello = 'PRE_SELLADA'
                sello.medico_firmante = request.user
                sello.timestamp_pre_sellado = timezone.localtime(timezone.now())
                sello.cedula_profesional = medico_profile.cedula_profesional
                sello.especialidad = medico_profile.especialidad
                sello.save()
            
            logger.info(f"[BLINDAJE] Nota #{nota_id} pre-sellada por {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': 'Nota pre-sellada. Ingrese su PIN para confirmar.',
                'estado': 'PRE_SELLADA',
                'folio_temporal': sello.token_verificacion.hex[:12]
            })
            
    except Exception as e:
        logger.error(f"[BLINDAJE] Error en pre_sellar_nota: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# 2. SELLAR CON PIN-LAB (Firma Electrónica Simple)
# =============================================================================

@login_required
@require_POST
def sellar_con_pin(request, nota_id):
    """
    Sella definitivamente la nota con el PIN-LAB del médico.
    Genera folio único, PDF firmado, y snapshot inmutable.
    """
    try:
        pin = request.POST.get('pin', '').strip()
        
        if not pin or len(pin) < 4:
            return JsonResponse({
                'success': False,
                'error': 'PIN inválido. Debe tener al menos 4 caracteres.'
            }, status=400)
        
        nota = get_object_or_404(
            NotaClinicaSOAP.objects.select_related('medico', 'paciente', 'empresa'),
            id=nota_id
        )
        
        # Verificar autoría
        if nota.medico != request.user:
            return JsonResponse({
                'success': False,
                'error': 'No autorizado'
            }, status=403)
        
        # Obtener sello preliminar
        sello = get_object_or_404(
            NotaClinicaSellar,
            nota_soap=nota,
            estado_sello='PRE_SELLADA'
        )
        
        # Validar PIN contra hash almacenado
        medico_profile = getattr(request.user, 'medico_profile', None)
        if not medico_profile or not medico_profile.lab_validation_pin_hash:
            return JsonResponse({
                'success': False,
                'error': 'PIN no configurado'
            }, status=400)
        
        pin_hash_input = hashlib.sha256(pin.encode()).hexdigest()
        if pin_hash_input != medico_profile.lab_validation_pin_hash:
            logger.warning(
                f"[BLINDAJE] Intento de sellado con PIN inválido "
                f"nota=#{nota_id} usuario={request.user.username}"
            )
            return JsonResponse({
                'success': False,
                'error': 'PIN incorrecto'
            }, status=400)
        
        with transaction.atomic():
            # 1. Generar folio único
            año = timezone.localtime(timezone.now()).year
            prefijo = f"EXP-{nota.empresa_id}-{año}-"
            count = NotaClinicaSellar.objects.filter(
                folio_unico__startswith=prefijo
            ).count()
            folio = f"{prefijo}{str(count + 1).zfill(6)}"
            
            # 2. Crear snapshot inmutable en ExpedienteNotaSHA
            from core.middleware.blindaje_expediente import _generar_snapshot_jsonb
            snapshot = _generar_snapshot_jsonb(nota)
            
            # Obtener hash anterior
            ultimo_exp = ExpedienteNotaSHA.objects.filter(
                nota_soap=nota
            ).order_by('-version').first()
            
            expediente = ExpedienteNotaSHA.objects.create(
                nota_soap=nota,
                empresa=nota.empresa,
                paciente=nota.paciente,
                medico=nota.medico,
                version=(ultimo_exp.version + 1) if ultimo_exp else 1,
                snapshot_jsonb=snapshot,
                estado_nota='SELLADA',
                hash_anterior=ultimo_exp.hash_sha256 if ultimo_exp else None,
                ip_origen=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                firmado_con_pin=True,
                pin_hash=pin_hash_input,
                timestamp_firma=timezone.localtime(timezone.now()),
            )
            
            # 3. Actualizar sello con metadatos forenses completos
            # ═══════════════════════════════════════════════════════════════════
            # 🔍 REPARACIÓN GRIETA #3: Evidencia Forense de Firma
            # Capturamos metadatos del entorno en el momento exacto del sellado
            # ═══════════════════════════════════════════════════════════════════
            
            # IP y red — REMOTE_ADDR (no falsificable); este valor es evidencia forense.
            ip_origen = request.META.get('REMOTE_ADDR')


            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            # Intentar extraer información del dispositivo del User-Agent
            dispositivo_id = None
            if 'iPad' in user_agent:
                dispositivo_tipo = 'iPad'
            elif 'iPhone' in user_agent:
                dispositivo_tipo = 'iPhone'
            elif 'Android' in user_agent:
                dispositivo_tipo = 'Android'
            elif 'Windows' in user_agent:
                dispositivo_tipo = 'Windows'
            elif 'Macintosh' in user_agent or 'Mac OS X' in user_agent:
                dispositivo_tipo = 'Mac'
            else:
                dispositivo_tipo = 'Desconocido'
            
            # Detectar ISP/país (en producción, usar servicio de geolocalización IP)
            pais_detectado = None
            isp_proveedor = None
            
            # Geolocalización (si el cliente la envía)
            latitud = request.POST.get('latitud')
            longitud = request.POST.get('longitud')
            precision = request.POST.get('precision')
            
            sello.estado_sello = 'SELLADA'
            sello.folio_unico = folio
            sello.pin_hash = pin_hash_input
            sello.timestamp_sellado = timezone.localtime(timezone.now())
            sello.expediente_sha = expediente
            sello.qr_verificacion = f"{getattr(settings, 'SITE_URL', 'https://prislab.app')}/verificar/{sello.token_verificacion}"
            
            # Guardar evidencia forense
            sello.ip_origen = ip_origen
            sello.user_agent = user_agent
            sello.dispositivo_id = dispositivo_tipo if dispositivo_tipo else None
            sello.ubicacion_latitud = float(latitud) if latitud else None
            sello.ubicacion_longitud = float(longitud) if longitud else None
            sello.ubicacion_precision = int(precision) if precision else None
            sello.pais_detectado = pais_detectado
            sello.isp_proveedor = isp_proveedor
            
            sello.save()
            
            # 4. Generar PDF (async via Celery o sync si es pequeño)
            try:
                from core.utils.pdf_generator import generar_pdf_nota_sellada
                pdf_path = generar_pdf_nota_sellada(nota, sello, expediente)
                sello.pdf_firmado = pdf_path
                sello.save(update_fields=['pdf_firmado'])
            except Exception as pdf_error:
                logger.error(f"[BLINDAJE] Error generando PDF: {pdf_error}")
                # No fallar el sellado por error en PDF
            
            logger.info(
                f"[BLINDAJE] Nota #{nota_id} SELLADA folio={folio} "
                f"hash={expediente.hash_sha256[:16]}... ip={ip_origen}"
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Nota sellada exitosamente',
                'folio_unico': folio,
                'hash_expediente': expediente.hash_sha256,
                'token_verificacion': str(sello.token_verificacion),
                'url_verificacion': sello.qr_verificacion,
                'timestamp_sellado': sello.timestamp_sellado.isoformat(),
                # 🔍 Evidencia forense incluida en la respuesta
                'evidencia_forense': {
                    'ip_origen': ip_origen,
                    'dispositivo': dispositivo_tipo,
                    'user_agent': user_agent[:100] + '...' if len(user_agent) > 100 else user_agent,
                    'geolocalizacion': {
                        'latitud': sello.ubicacion_latitud,
                        'longitud': sello.ubicacion_longitud,
                        'precision': sello.ubicacion_precision,
                    } if sello.ubicacion_latitud else None,
                }
            })
            
    except Exception as e:
        logger.error(f"[BLINDAJE] Error en sellar_con_pin: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# 3. VERIFICAR INTEGRIDAD DE NOTA
# =============================================================================

@login_required
@require_GET
def verificar_nota(request, nota_id):
    """
    Verifica la integridad completa de la cadena de hashes de una nota.
    """
    try:
        resultado = verificar_cadena_integridad(nota_id)
        
        # Agregar info del sello si existe
        sello = NotaClinicaSellar.objects.filter(nota_soap_id=nota_id).first()
        if sello:
            resultado['sello'] = {
                'estado': sello.estado_sello,
                'folio': sello.folio_unico,
                'medico_firmante': sello.medico_firmante.get_full_name() if sello.medico_firmante else None,
                'timestamp_sellado': sello.timestamp_sellado.isoformat() if sello.timestamp_sellado else None,
                'pdf_generado': bool(sello.pdf_firmado),
            }
        
        return JsonResponse(resultado)
        
    except Exception as e:
        logger.error(f"[BLINDAJE] Error en verificar_nota: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# 4. DESBLOQUEO FORENSE (Solo con permiso especial)
# =============================================================================

@login_required
@permission_required('core.desbloquear_nota_sellada', raise_exception=True)
@require_POST
def desbloqueo_forense(request, nota_id):
    """
    Desbloquea una nota sellada en casos excepcionales.
    REQUIERE: Permiso 'desbloquear_nota_sellada' + justificación escrita.
    """
    try:
        justificacion = request.POST.get('justificacion', '').strip()
        
        if len(justificacion) < 50:
            return JsonResponse({
                'success': False,
                'error': 'La justificación debe tener al menos 50 caracteres'
            }, status=400)
        
        nota = get_object_or_404(NotaClinicaSOAP, id=nota_id)
        sello = get_object_or_404(NotaClinicaSellar, nota_soap=nota)
        
        with transaction.atomic():
            # Cambiar estado del sello
            estado_anterior = sello.estado_sello
            sello.estado_sello = 'EDITABLE'  # Volver a editable
            sello.save()
            
            # Crear registro de auditoría del desbloqueo
            ExpedienteNotaSHA.objects.create(
                nota_soap=nota,
                empresa=nota.empresa,
                paciente=nota.paciente,
                medico=request.user,
                version=ExpedienteNotaSHA.objects.filter(nota_soap=nota).count() + 1,
                snapshot_jsonb={
                    'tipo': 'DESBLOQUEO_FORENSE',
                    'estado_anterior': estado_anterior,
                    'nuevo_estado': 'EDITABLE',
                    'justificacion': justificacion,
                    'desbloqueado_por': request.user.username,
                    'timestamp_desbloqueo': timezone.localtime(timezone.now()).isoformat(),
                },
                estado_nota='DESBLOQUEADA',
                ip_origen=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
            
            logger.critical(
                f"[BLINDAJE] DESBLOQUEO FORENSE nota=#{nota_id} "
                f"por {request.user.username} - Justificación: {justificacion[:100]}..."
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Nota desbloqueada para edición forense',
                'requiere_re_sellado': True,
                'advertencia': 'Esta acción queda registrada permanentemente en la bitácora forense'
            })
            
    except Exception as e:
        logger.error(f"[BLINDAJE] Error en desbloqueo_forense: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# 5. CONFIGURAR PIN-LAB (Para médicos)
# =============================================================================

@login_required
@require_POST
def configurar_pin_lab(request):
    """
    Permite a un médico configurar su PIN-LAB.
    El PIN se almacena como hash SHA256, nunca en texto plano.
    """
    try:
        pin = request.POST.get('pin', '').strip()
        pin_confirmacion = request.POST.get('pin_confirmacion', '').strip()
        
        # Validaciones
        if len(pin) < 4:
            return JsonResponse({
                'success': False,
                'error': 'El PIN debe tener al menos 4 caracteres'
            }, status=400)
        
        if pin != pin_confirmacion:
            return JsonResponse({
                'success': False,
                'error': 'Los PIN no coinciden'
            }, status=400)
        
        # Obtener perfil de médico
        medico_profile = getattr(request.user, 'medico_profile', None)
        if not medico_profile:
            # Crear perfil si no existe
            from core.models import Medico
            medico_profile, _ = Medico.objects.get_or_create(
                usuario=request.user,
                defaults={
                    'nombre_completo': request.user.get_full_name(),
                    'cedula_profesional': '',
                }
            )
            request.user.medico_profile = medico_profile
        
        # Generar hash y guardar
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        medico_profile.lab_validation_pin_hash = pin_hash
        medico_profile.pin_configurado_en = timezone.localtime(timezone.now())
        medico_profile.save()
        
        logger.info(f"[BLINDAJE] PIN-LAB configurado para médico {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'PIN-LAB configurado exitosamente',
            'pin_configurado_en': medico_profile.pin_configurado_en.isoformat()
        })
        
    except Exception as e:
        logger.error(f"[BLINDAJE] Error en configurar_pin_lab: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# 6. VALIDACIÓN PÚBLICA (Verificación externa sin login)
# =============================================================================

@require_GET
def verificar_publico(request, token):
    """
    Verificación pública de una nota sellada vía token único.
    No requiere autenticación — es para pacientes/terceros.
    """
    try:
        sello = get_object_or_404(
            NotaClinicaSellar.objects.select_related('nota_soap', 'medico_firmante'),
            token_verificacion=token,
            estado_sello='SELLADA'
        )
        
        # Verificar integridad de la cadena
        resultado_integridad = verificar_cadena_integridad(sello.nota_soap_id)
        
        return JsonResponse({
            'valido': resultado_integridad['valido'] and sello.estado_sello == 'SELLADA',
            'folio_unico': sello.folio_unico,
            'medico_firmante': sello.medico_firmante.get_full_name() if sello.medico_firmante else 'N/A',
            'cedula_profesional': sello.cedula_profesional,
            'especialidad': sello.especialidad,
            'fecha_sellado': sello.timestamp_sellado.isoformat() if sello.timestamp_sellado else None,
            'hash_expediente': sello.expediente_sha.hash_sha256 if sello.expediente_sha else None,
            'cadena_integridad': resultado_integridad,
            'mensaje': 'Esta nota ha sido verificada electrónicamente y es auténtica' 
                       if resultado_integridad['valido'] else 
                       'ADVERTENCIA: Se detectaron inconsistencias en la cadena de integridad'
        })
        
    except Exception as e:
        logger.error(f"[BLINDAJE] Error en verificar_publico: {e}", exc_info=True)
        return JsonResponse({
            'valido': False,
            'error': 'Token inválido o nota no encontrada'
        }, status=404)


# =============================================================================
# 7. CATÁLOGO CIE-10 (Para diagnósticos codificados)
# =============================================================================

@login_required
@require_GET
def buscar_cie10(request):
    """
    Busca códigos CIE-10 por código o descripción.
    """
    try:
        q = request.GET.get('q', '').strip()
        
        if len(q) < 3:
            return JsonResponse({
                'results': [],
                'message': 'Ingrese al menos 3 caracteres'
            })
        
        resultados = CatalogoCIE10.objects.filter(
            models.Q(codigo__icontains=q) | 
            models.Q(descripcion__icontains=q),
            activo=True
        )[:20]
        
        return JsonResponse({
            'results': [
                {
                    'codigo': r.codigo,
                    'descripcion': r.descripcion,
                    'categoria': r.categoria,
                }
                for r in resultados
            ]
        })
        
    except Exception as e:
        logger.error(f"[BLINDAJE] Error en buscar_cie10: {e}", exc_info=True)
        return JsonResponse({
            'error': str(e)
        }, status=500)


# Importar models para buscar_cie10
from django.db import models
