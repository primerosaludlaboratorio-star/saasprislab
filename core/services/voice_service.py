"""
PRIS VOICE COMMANDER - Servicio de Procesamiento de Voz
Integración con Gemini AI para comandos contextuales con RBAC
"""

import logging
import json
import time
from datetime import datetime
from django.conf import settings

logger = logging.getLogger('voice')


# ==============================================================================
# RBAC: CONTROL DE PERMISOS POR ROL
# ==============================================================================

# Comandos permitidos por nivel de autorización
COMANDOS_POR_ROL = {
    'STAFF': {
        'permitidos': [
            'buscar_paciente',
            'ver_stock',
            'consultar_precio',
            'enviar_mensaje',
            'ver_agenda',
            'registrar_venta',
            'surtir_receta',
            'cerrar_caja',
            'nuevo_paciente',
            'ver_historial',
        ],
        'bloqueados': [
            'eliminar',
            'modificar_configuracion',
            'ver_logs',
            'reiniciar_sistema',
            'borrar_datos',
            'modificar_permisos',
        ]
    },
    'DIRECTOR': {
        'permitidos': '*',  # Todos los comandos
        'criticos_requieren_auth': [
            'eliminar',
            'reiniciar_sistema',
            'borrar_datos',
            'modificar_permisos',
            'acceder_logs_sentinel',
        ]
    }
}


def verificar_permiso_comando(usuario, intencion):
    """
    Verifica si el usuario tiene permiso para ejecutar el comando.
    
    Args:
        usuario: Instancia del Usuario
        intencion: String de la intención detectada (ej: 'buscar_paciente')
    
    Returns:
        dict: {
            'permitido': bool,
            'requiere_auth': bool,
            'motivo': str
        }
    """
    # Determinar nivel del usuario
    if usuario.is_superuser:
        nivel = 'DIRECTOR'
    else:
        nivel = 'STAFF'
    
    permisos = COMANDOS_POR_ROL.get(nivel, COMANDOS_POR_ROL['STAFF'])
    
    # Caso DIRECTOR: todos permitidos, algunos requieren auth
    if nivel == 'DIRECTOR':
        if intencion in permisos.get('criticos_requieren_auth', []):
            return {
                'permitido': True,
                'requiere_auth': True,
                'motivo': 'Comando crítico. Requiere autenticación biométrica.'
            }
        return {
            'permitido': True,
            'requiere_auth': False,
            'motivo': 'Nivel DIRECTOR: todos los comandos permitidos'
        }
    
    # Caso STAFF: verificar lista permitidos/bloqueados
    if intencion in permisos['permitidos']:
        return {
            'permitido': True,
            'requiere_auth': False,
            'motivo': f'Comando permitido para nivel {nivel}'
        }
    
    if intencion in permisos['bloqueados']:
        return {
            'permitido': False,
            'requiere_auth': False,
            'motivo': f'Comando no autorizado para nivel {nivel}. Contacta al Director.'
        }
    
    # Si no está en ninguna lista, bloquear por seguridad
    return {
        'permitido': False,
        'requiere_auth': False,
        'motivo': 'Comando no reconocido o no autorizado'
    }


# ==============================================================================
# MAPEO DE COMANDOS A ACCIONES
# ==============================================================================

COMANDOS_RAPIDOS = {
    'cerrar_caja': {
        'url': '/farmacia/cierre-turno/',
        'metodo': 'GET',
        'descripcion': 'Abrir vista de cierre de turno',
    },
    'nuevo_paciente': {
        'url': '/pacientes/registro/',
        'metodo': 'MODAL',
        'descripcion': 'Abrir modal de registro rápido de paciente',
    },
    'surtir_receta': {
        'accion': 'cargar_receta_en_pdv',
        'descripcion': 'Cargar medicamentos de receta en el carrito de PDV',
        'requiere_parametros': ['folio'],
    },
    'buscar_paciente': {
        'accion': 'abrir_buscador_pacientes',
        'descripcion': 'Abrir buscador de pacientes con término de búsqueda',
        'requiere_parametros': ['nombre'],
    },
    'ver_stock': {
        'accion': 'buscar_producto',
        'descripcion': 'Buscar y mostrar stock de producto',
        'requiere_parametros': ['producto'],
    },
}


# ==============================================================================
# PROCESAMIENTO CON GEMINI AI (CONTEXTO INYECTADO)
# ==============================================================================

def procesar_comando_voz(transcripcion, usuario, url_actual, datos_pantalla=None):
    """
    Procesa un comando de voz con contexto visual inyectado en Gemini.
    
    Args:
        transcripcion (str): Texto transcrito del comando de voz
        usuario: Instancia del Usuario que emitió el comando
        url_actual (str): URL de la pantalla donde está el usuario
        datos_pantalla (str): Contexto adicional de lo que el usuario ve
    
    Returns:
        dict: {
            'intencion': str,
            'parametros': dict,
            'respuesta': str,
            'accion': dict,
            'tiempo_procesamiento_ms': int
        }
    """
    tiempo_inicio = time.time()
    
    # Determinar rol del usuario
    if usuario.is_superuser:
        rol = 'DIRECTOR'
    elif usuario.groups.filter(name__in=['MEDICO', 'DOCTOR']).exists():
        rol = 'MÉDICO'
    elif usuario.groups.filter(name='FARMACIA').exists():
        rol = 'FARMACÉUTICO'
    elif usuario.groups.filter(name='LABORATORIO').exists():
        rol = 'LABORATORISTA'
    elif usuario.groups.filter(name='RECEPCION').exists():
        rol = 'RECEPCIONISTA'
    else:
        rol = 'STAFF'

    _empresa = getattr(usuario, 'empresa', None)
    _eid = getattr(_empresa, 'id', None)
    _tenant = (
        f"- Tenant obligatorio: empresa_id={_eid}. No uses ni cites datos de otras empresas.\n"
        if _eid is not None
        else "- Tenant: usuario sin empresa asignada; no asumas otra empresa.\n"
    )
    
    # Construcción del prompt con contexto visual
    prompt = f"""Eres PRIS Voice Commander, el asistente de voz de un sistema médico integral (PRISLAB).

**CONTEXTO DEL USUARIO:**
- Rol: {rol} ({usuario.get_full_name()})
{_tenant}- Ubicación en el sistema: {url_actual}
- Pantalla actual: {datos_pantalla or 'No disponible'}

**COMANDO DEL USUARIO:**
"{transcripcion}"

**TU TAREA:**
1. Analizar la intención del usuario considerando su contexto visual
2. Extraer parámetros relevantes (nombres, folios, números)
3. Generar una respuesta clara y concisa
4. Determinar la acción a ejecutar

**IMPORTANTE:**
- Si el usuario dice pronombres ("súrtela", "búscalo", "ciérrala"), usar el contexto de pantalla para entender qué objeto específico
- Si el comando no está claro, pedir aclaración
- Si el comando requiere parámetros faltantes, solicítalos

**RESPONDE EN JSON:**
{{
    "intencion": "nombre_de_la_intencion",
    "parametros": {{"clave": "valor"}},
    "respuesta_usuario": "Texto de respuesta al usuario",
    "requiere_aclaracion": false,
    "confianza": 0.95
}}

**INTENCIONES VÁLIDAS:**
- buscar_paciente
- surtir_receta
- cerrar_caja
- nuevo_paciente
- ver_stock
- consultar_precio
- enviar_mensaje
- ver_agenda
- ver_historial
"""
    
    try:
        # Intentar usar Gemini
        from google.generativeai import configure, GenerativeModel
        
        api_key = settings.GOOGLE_API_KEY or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("No hay API key configurada")
        
        configure(api_key=api_key)
        model = GenerativeModel('gemini-2.0-flash')
        
        response = model.generate_content(
            prompt,
            generation_config={'max_output_tokens': 512},
            request_options={'timeout': 10}
        )
        
        # Parsear respuesta JSON
        texto_respuesta = response.text.strip()
        
        # Extraer JSON (puede venir con markdown)
        if '```json' in texto_respuesta:
            texto_respuesta = texto_respuesta.split('```json')[1].split('```')[0].strip()
        elif '```' in texto_respuesta:
            texto_respuesta = texto_respuesta.split('```')[1].split('```')[0].strip()
        
        resultado = json.loads(texto_respuesta)
        
        intencion = resultado.get('intencion', 'desconocida')
        parametros = resultado.get('parametros', {})
        respuesta = resultado.get('respuesta_usuario', 'Comando procesado.')
        
        # Verificar permisos
        permiso = verificar_permiso_comando(usuario, intencion)
        
        if not permiso['permitido']:
            from core.utils.ia_output_sanitize import sanitizar_salida_ia

            _deny = f"⚠️ {permiso['motivo']}"
            _deny, _ = sanitizar_salida_ia(_deny, empresa_id=_eid)
            return {
                'intencion': intencion,
                'parametros': parametros,
                'respuesta': _deny,
                'accion': None,
                'bloqueado': True,
                'requiere_auth': False,
                'tiempo_procesamiento_ms': int((time.time() - tiempo_inicio) * 1000)
            }
        
        # Buscar acción mapeada
        accion = COMANDOS_RAPIDOS.get(intencion)

        from core.utils.ia_output_sanitize import sanitizar_salida_ia

        respuesta, _ok = sanitizar_salida_ia(respuesta, empresa_id=_eid)
        
        return {
            'intencion': intencion,
            'parametros': parametros,
            'respuesta': respuesta,
            'accion': accion,
            'bloqueado': False,
            'requiere_auth': permiso['requiere_auth'],
            'tiempo_procesamiento_ms': int((time.time() - tiempo_inicio) * 1000)
        }
        
    except Exception as e:
        logger.error(f"Error al procesar comando con IA: {e}", exc_info=True)
        
        # Fallback: análisis offline simple
        return _procesar_comando_offline(transcripcion, usuario, url_actual, tiempo_inicio)


def _procesar_comando_offline(transcripcion, usuario, url_actual, tiempo_inicio):
    """
    Procesamiento offline (sin IA) basado en palabras clave.
    Fallback cuando Gemini no está disponible.
    """
    texto_lower = transcripcion.lower()
    
    # Detección simple por palabras clave
    if any(palabra in texto_lower for palabra in ['cerrar caja', 'cierre', 'corte']):
        intencion = 'cerrar_caja'
        respuesta = 'Abriendo cierre de turno...'
        accion = COMANDOS_RAPIDOS['cerrar_caja']
    
    elif any(palabra in texto_lower for palabra in ['nuevo paciente', 'registrar paciente', 'alta']):
        intencion = 'nuevo_paciente'
        respuesta = 'Abriendo formulario de registro de paciente...'
        accion = COMANDOS_RAPIDOS['nuevo_paciente']
    
    elif 'surtir' in texto_lower or 'receta' in texto_lower:
        intencion = 'surtir_receta'
        # Intentar extraer número de folio
        import re
        numeros = re.findall(r'\d+', transcripcion)
        folio = numeros[0] if numeros else None
        
        if folio:
            respuesta = f'Cargando receta #{folio} en el carrito...'
            parametros = {'folio': folio}
        else:
            respuesta = '¿Cuál es el folio de la receta?'
            parametros = {}
        
        accion = COMANDOS_RAPIDOS['surtir_receta']
    
    elif any(palabra in texto_lower for palabra in ['buscar', 'paciente', 'nombre']):
        intencion = 'buscar_paciente'
        # Extraer nombre después de "buscar"
        if 'buscar' in texto_lower:
            nombre = texto_lower.split('buscar')[-1].strip()
            parametros = {'nombre': nombre}
            respuesta = f'Buscando paciente: {nombre}'
        else:
            parametros = {}
            respuesta = '¿Qué paciente buscas?'
        
        accion = COMANDOS_RAPIDOS['buscar_paciente']
    
    else:
        intencion = 'desconocida'
        respuesta = 'No entendí el comando. ¿Podrías repetir?'
        parametros = {}
        accion = None
    
    # Verificar permisos
    permiso = verificar_permiso_comando(usuario, intencion)

    from core.utils.ia_output_sanitize import sanitizar_salida_ia

    _eid_off = getattr(getattr(usuario, 'empresa', None), 'id', None)
    _txt = respuesta if permiso['permitido'] else f"⚠️ {permiso['motivo']}"
    _txt, _ = sanitizar_salida_ia(_txt, empresa_id=_eid_off)
    
    return {
        'intencion': intencion,
        'parametros': parametros,
        'respuesta': _txt,
        'accion': accion if permiso['permitido'] else None,
        'bloqueado': not permiso['permitido'],
        'requiere_auth': permiso['requiere_auth'],
        'tiempo_procesamiento_ms': int((time.time() - tiempo_inicio) * 1000)
    }


# ==============================================================================
# UTILIDADES
# ==============================================================================

def registrar_comando_voz(usuario, transcripcion, resultado, url_actual, datos_pantalla=None):
    """
    Registra el comando de voz en VoiceAuditLog.
    
    Args:
        usuario: Usuario que emitió el comando
        transcripcion: Texto del comando
        resultado: Dict con el resultado del procesamiento
        url_actual: URL donde se emitió
        datos_pantalla: Contexto visual
    
    Returns:
        VoiceAuditLog instance
    """
    from core.models import VoiceAuditLog
    
    # Determinar tipo de comando
    if resultado.get('bloqueado'):
        estado = 'BLOQUEADO'
        tipo = 'ACCION'
    elif resultado.get('requiere_auth'):
        tipo = 'CRITICO'
        estado = 'EXITOSO'
    elif resultado.get('intencion') == 'enviar_mensaje':
        tipo = 'COMUNICACION'
        estado = 'EXITOSO'
    else:
        tipo = 'ACCION'
        estado = 'EXITOSO'
    
    log = VoiceAuditLog.objects.create(
        usuario=usuario,
        empresa=usuario.empresa,
        url_actual=url_actual,
        datos_pantalla=datos_pantalla,
        transcripcion=transcripcion,
        tipo_comando=tipo,
        intencion_detectada=resultado.get('intencion', 'desconocida'),
        parametros_extraidos=resultado.get('parametros', {}),
        respuesta_ia=resultado.get('respuesta', ''),
        accion_ejecutada=str(resultado.get('accion', '')),
        estado=estado,
        requiere_autenticacion=resultado.get('requiere_auth', False),
        nivel_autorizado='DIRECTOR' if usuario.is_superuser else 'STAFF',
        tiempo_procesamiento_ms=resultado.get('tiempo_procesamiento_ms', 0)
    )
    
    logger.info(f"Comando de voz registrado: {log.id} - {usuario.username} - {resultado.get('intencion')}")
    
    return log
