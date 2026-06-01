"""
═══════════════════════════════════════════════════════════════════════════════
MOTOR DE TOKENS LIMS v7.5 — Integración de Órdenes desde Notas SOAP
═══════════════════════════════════════════════════════════════════════════════

Este módulo implementa la Capa 3 de la Arquitectura de Blindaje v2.0:
Convierte tokens de texto en órdenes de laboratorio trazables.

Tokens soportados:
  • analito:<codigo>     → Un analito específico
  • perfil:<codigo>      → Perfil de estudios
  • paquete:<codigo>     → Paquete completo

Ejemplo:
  "Solicito analito:GLU perfil:LIVER paquete:BASICO_MUJER"
  
Se convierte automáticamente en una OrdenDeServicio con DetalleOrden.
═══════════════════════════════════════════════════════════════════════════════
"""

import re
import logging
from datetime import datetime

from django.db import transaction
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TokenLIMSError(Exception):
    """Error en procesamiento de tokens LIMS."""
    pass


class TokenLIMSParser:
    """
    Parser de tokens LIMS v7.5 desde texto libre.
    
    Soporta formatos:
      analito:GLUCOSA
      perfil:LIVER_FUNCTION
      paquete:BASICO_PRENATAL
      
    También soporta variantes:
      analito:GLU, glucosa, GLUC
      perfil:LIVER, hepatico
    """
    
    # Patrones de tokens
    TOKEN_PATTERNS = [
        (r'analito[s]?:\s*([A-Za-z0-9_\-]+)', 'analito'),
        (r'perfil[es]?:\s*([A-Za-z0-9_\-]+)', 'perfil'),
        (r'paquete[s]?:\s*([A-Za-z0-9_\-]+)', 'paquete'),
        # Alias comunes
        (r'\bstudy:\s*([A-Za-z0-9_\-]+)', 'analito'),
        (r'\btest:\s*([A-Za-z0-9_\-]+)', 'analito'),
    ]
    
    # Mapeo de alias comunes a códigos estándar
    ALIAS_ANALITOS = {
        # Glucosa
        'GLU': 'GLUCOSA',
        'GLUC': 'GLUCOSA',
        'GLUCOSA': 'GLUCOSA',
        'AZUCAR': 'GLUCOSA',
        # Urea
        'UREA': 'UREA',
        'BUN': 'UREA',
        # Creatinina
        'CREAT': 'CREATININA',
        'CREATININA': 'CREATININA',
        # Colesterol
        'COL': 'COLESTEROL_TOTAL',
        'COLESTEROL': 'COLESTEROL_TOTAL',
        # Triglicéridos
        'TG': 'TRIGLICERIDOS',
        'TRIGLICERIDOS': 'TRIGLICERIDOS',
    }
    
    @classmethod
    def extraer_tokens(cls, texto):
        """
        Extrae todos los tokens válidos del texto.
        
        Returns:
            list: [{'tipo': 'analito', 'codigo': 'GLUCOSA', 'raw': 'analito:GLU'}]
        """
        if not texto:
            return []
        
        tokens = []
        texto_upper = texto.upper()
        
        for pattern, tipo in cls.TOKEN_PATTERNS:
            matches = re.finditer(pattern, texto_upper, re.IGNORECASE)
            for match in matches:
                codigo_raw = match.group(1)
                codigo = cls._normalizar_codigo(codigo_raw, tipo)
                
                token = {
                    'tipo': tipo,
                    'codigo_raw': codigo_raw,
                    'codigo': codigo,
                    'posicion': match.start(),
                    'match': match.group(0),
                }
                tokens.append(token)
        
        # Eliminar duplicados manteniendo el orden
        seen = set()
        unique_tokens = []
        for t in tokens:
            key = (t['tipo'], t['codigo'])
            if key not in seen:
                seen.add(key)
                unique_tokens.append(t)
        
        return unique_tokens
    
    @classmethod
    def _normalizar_codigo(cls, codigo, tipo):
        """Normaliza el código según alias definidos."""
        codigo_upper = codigo.upper().strip()
        
        if tipo == 'analito':
            return cls.ALIAS_ANALITOS.get(codigo_upper, codigo_upper)
        
        return codigo_upper


class MotorOrdenesLIMS:
    """
    Motor de generación de órdenes LIMS desde tokens.
    
    Responsabilidades:
    1. Resolver tokens a analitos del catálogo LIMS
    2. Validar preparaciones (ayuno, preparación especial)
    3. Generar OrdenDeServicio con DetalleOrden
    4. Crear registro de trazabilidad OrdenTokenLIMS
    """
    
    @classmethod
    def generar_orden_desde_tokens(cls, texto_nota, paciente, medico, empresa, 
                                   nota_soap=None, validar_preparacion=True):
        """
        Genera una orden de laboratorio desde tokens en texto.
        
        Args:
            texto_nota: Texto de la nota SOAP
            paciente: Instancia de Paciente
            medico: Instancia de Usuario (médico)
            empresa: Instancia de Empresa
            nota_soap: Instancia opcional de NotaClinicaSOAP
            validar_preparacion: Si True, valida reglas de preparación
        
        Returns:
            dict: {
                'success': True/False,
                'orden': OrdenDeServicio (si success=True),
                'tokens_resueltos': [...],
                'alertas': [...],
                'errores': [...]
            }
        """
        try:
            # 1. Extraer tokens
            tokens = TokenLIMSParser.extraer_tokens(texto_nota)
            
            if not tokens:
                return {
                    'success': False,
                    'errores': ['No se encontraron tokens LIMS en el texto'],
                    'tokens_resueltos': [],
                    'alertas': [],
                }
            
            errores = []
            tokens_resueltos = []
            alertas = []
            
            # 2. Resolver cada token
            analitos_a_solicitar = []
            
            for token in tokens:
                try:
                    resultado = cls._resolver_token(token)
                    if resultado:
                        token['resuelto'] = True
                        token['analitos'] = resultado['analitos']
                        token['nombre'] = resultado['nombre']
                        tokens_resueltos.append(token)
                        
                        # Agregar analitos a la lista
                        for analito in resultado['analitos']:
                            if analito not in analitos_a_solicitar:
                                analitos_a_solicitar.append(analito)
                    else:
                        token['resuelto'] = False
                        errores.append(f"No se encontró '{token['codigo']}' en el catálogo LIMS")
                        
                except Exception as e:
                    token['resuelto'] = False
                    errores.append(f"Error resolviendo {token['tipo']}:{token['codigo']}: {str(e)}")
            
            if not analitos_a_solicitar:
                return {
                    'success': False,
                    'errores': errores or ['No se pudieron resolver los tokens a analitos'],
                    'tokens_resueltos': tokens_resueltos,
                    'alertas': alertas,
                }
            
            # 3. Validar preparaciones si se solicita
            if validar_preparacion:
                from core.models import ReglaPreparacionAnalito
                
                for analito in analitos_a_solicitar:
                    try:
                        regla = ReglaPreparacionAnalito.objects.filter(
                            analito=analito,
                            activo=True
                        ).first()
                        
                        if regla:
                            validacion = regla.validar_paciente(paciente)
                            if validacion['alertas']:
                                alertas.extend(validacion['alertas'])
                    except Exception as e:
                        logger.warning(f"Error validando preparación para {analito}: {e}")
            
            # 4. Crear orden de servicio
            with transaction.atomic():
                from core.models import OrdenDeServicio, DetalleOrden, OrdenTokenLIMS
                
                # Generar folio
                año = datetime.now().year
                count = OrdenDeServicio.objects.filter(
                    empresa=empresa,
                    folio_orden__startswith=f'ORD-{año}-'
                ).count()
                folio = f'ORD-{año}-{str(count + 1).zfill(6)}'
                
                # Crear orden
                orden = OrdenDeServicio.objects.create(
                    paciente=paciente,
                    medico_referente=medico,
                    empresa=empresa,
                    folio_orden=folio,
                    estado='PENDIENTE',
                )
                
                # Crear detalles
                for analito in analitos_a_solicitar:
                    DetalleOrden.objects.create(
                        orden=orden,
                        analito=analito,
                        estado='PENDIENTE',
                    )
                
                # Registrar trazabilidad de tokens
                if nota_soap:
                    OrdenTokenLIMS.objects.create(
                        nota_soap=nota_soap,
                        orden_lims=orden,
                        tokens_json=[{
                            'tipo': t['tipo'],
                            'codigo': t['codigo'],
                            'resuelto': t.get('resuelto', False),
                        } for t in tokens_resueltos],
                        texto_original=texto_nota,
                        preparacion_validada=validar_preparacion,
                        alertas_preparacion=alertas,
                        medico_generador=medico,
                    )
                
                logger.info(
                    f"[LIMS-v7.5] Orden {folio} generada desde tokens: "
                    f"{len(analitos_a_solicitar)} analitos"
                )
                
                return {
                    'success': True,
                    'orden': orden,
                    'folio': folio,
                    'tokens_resueltos': tokens_resueltos,
                    'analitos_solicitados': len(analitos_a_solicitar),
                    'alertas': alertas,
                    'errores': errores,  # Advertencias no críticas
                }
                
        except Exception as e:
            logger.error(f"[LIMS-v7.5] Error generando orden: {e}", exc_info=True)
            return {
                'success': False,
                'errores': [str(e)],
                'tokens_resueltos': [],
                'alertas': [],
            }
    
    @classmethod
    def _resolver_token(cls, token):
        """
        Resuelve un token específico a analitos del catálogo LIMS.
        
        Returns:
            dict: {'analitos': [...], 'nombre': '...'} o None si no encontrado
        """
        from lims.models import Analito, Perfil, Paquete
        
        tipo = token['tipo']
        codigo = token['codigo']
        
        if tipo == 'analito':
            # Buscar analito por código
            analito = Analito.objects.filter(
                codigo=codigo,
                activo=True
            ).first()
            
            if not analito:
                # Intentar búsqueda por nombre
                analito = Analito.objects.filter(
                    nombre__icontains=codigo,
                    activo=True
                ).first()
            
            if analito:
                return {
                    'analitos': [analito],
                    'nombre': analito.nombre,
                }
        
        elif tipo == 'perfil':
            # Buscar perfil
            perfil = Perfil.objects.filter(
                codigo=codigo,
                activo=True
            ).first()
            
            if perfil:
                analitos = list(perfil.analitos.filter(activo=True))
                if analitos:
                    return {
                        'analitos': analitos,
                        'nombre': perfil.nombre,
                    }
        
        elif tipo == 'paquete':
            # Buscar paquete
            paquete = Paquete.objects.filter(
                codigo=codigo,
                activo=True
            ).first()
            
            if paquete:
                # Obtener analitos de todos los perfiles del paquete
                analitos = []
                for perfil in paquete.perfiles.filter(activo=True):
                    analitos.extend(perfil.analitos.filter(activo=True))
                
                if analitos:
                    # Eliminar duplicados
                    analitos_unicos = list({a.id: a for a in analitos}.values())
                    return {
                        'analitos': analitos_unicos,
                        'nombre': paquete.nombre,
                    }
        
        return None


class ValidadorPreparacion:
    """
    Valida reglas de preparación para órdenes LIMS.
    """
    
    @staticmethod
    def validar_orden_completa(orden, paciente):
        """
        Valida todas las reglas de preparación para una orden.
        
        Returns:
            dict: {
                'valido': True/False,
                'alertas': [...],
                'requiere_ayuno': True/False,
                'horas_ayuno': N
            }
        """
        from core.models import ReglaPreparacionAnalito
        
        alertas = []
        requiere_ayuno = False
        max_horas_ayuno = 0
        
        for detalle in orden.detalles.select_related('analito'):
            analito = detalle.analito
            
            regla = ReglaPreparacionAnalito.objects.filter(
                analito=analito,
                activo=True
            ).first()
            
            if regla:
                if regla.requiere_ayuno:
                    requiere_ayuno = True
                    max_horas_ayuno = max(max_horas_ayuno, regla.horas_ayuno)
                
                validacion = regla.validar_paciente(paciente)
                alertas.extend(validacion['alertas'])
        
        return {
            'valido': True,  # Las alertas son informativas, no bloqueantes
            'alertas': list(set(alertas)),  # Eliminar duplicados
            'requiere_ayuno': requiere_ayuno,
            'horas_ayuno': max_horas_ayuno if requiere_ayuno else 0,
        }


# =============================================================================
# API DE TOKENS LIMS (para uso en views)
# =============================================================================

def api_procesar_tokens_lims(request):
    """
    API endpoint para procesar tokens desde AJAX.
    
    POST params:
        - texto: Texto con tokens
        - paciente_id: ID del paciente
        - nota_soap_id: (opcional) ID de nota SOAP
    """
    from django.http import JsonResponse
    from core.models import Paciente
    
    try:
        texto = request.POST.get('texto', '')
        paciente_id = request.POST.get('paciente_id')
        nota_soap_id = request.POST.get('nota_soap_id')
        
        if not texto or not paciente_id:
            return JsonResponse({
                'success': False,
                'error': 'Faltan parámetros: texto y paciente_id son requeridos'
            }, status=400)
        
        paciente = Paciente.objects.get(id=paciente_id)
        
        # Obtener nota SOAP si se proporciona
        nota_soap = None
        if nota_soap_id:
            from core.models import NotaClinicaSOAP
            nota_soap = NotaClinicaSOAP.objects.filter(id=nota_soap_id).first()
        
        resultado = MotorOrdenesLIMS.generar_orden_desde_tokens(
            texto_nota=texto,
            paciente=paciente,
            medico=request.user,
            empresa=request.user.empresa if hasattr(request.user, 'empresa') else None,
            nota_soap=nota_soap,
            validar_preparacion=True,
        )
        
        # Serializar respuesta
        if resultado['success']:
            return JsonResponse({
                'success': True,
                'orden_id': resultado['orden'].id,
                'folio': resultado['folio'],
                'analitos_solicitados': resultado['analitos_solicitados'],
                'tokens': resultado['tokens_resueltos'],
                'alertas': resultado['alertas'],
                'errores': resultado['errores'],
            })
        else:
            return JsonResponse({
                'success': False,
                'errores': resultado['errores'],
                'tokens': resultado['tokens_resueltos'],
                'alertas': resultado['alertas'],
            }, status=400)
            
    except Paciente.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Paciente no encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"[LIMS-v7.5] Error en API: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
