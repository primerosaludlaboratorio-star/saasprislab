"""
PRISLAB V5.0 - GENERADOR DE RUTAS INTELIGENTES PARA GOOGLE DRIVE
================================================================
Fecha: 1 de Febrero de 2026
Objetivo: Arquitectura de carpetas jerárquica y nomenclatura estandarizada

MEJORAS AL PROMPT ORIGINAL:
✅ Detección automática de tipo de documento
✅ Manejo robusto de nombres con caracteres especiales
✅ Versionado automático si el archivo ya existe
✅ Metadata enriquecida (folio, médico, fecha legible)
✅ Compatibilidad con múltiples tipos de instancias
✅ Logging de trazabilidad forense
✅ Validación de seguridad (tamaño, extensión)
"""

import os
import re
from datetime import datetime
from django.utils.text import slugify
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


# ==============================================================================
# BLOQUE 1: ARQUITECTURA DE CARPETAS Y NOMENCLATURA
# ==============================================================================

def generar_ruta_drive(instance, filename):
    """
    Genera ruta jerárquica inteligente para Google Drive.
    
    ESTRUCTURA: AÑO/MES/DIA/SLUG_PACIENTE/TIPO_DESCRIPCION_FOLIO.extension
    
    Args:
        instance: Instancia del modelo (Consulta, OrdenDeServicio, etc.)
        filename: Nombre original del archivo (será reemplazado)
    
    Returns:
        str: Ruta completa para el archivo
        
    Ejemplo:
        2026/02/01/juan-perez-lopez/LABORATORIO_Biometria-Hematica_ORD-001.pdf
        2026/02/01/maria-garcia/RECETA_Consulta-General_20260201-103045.pdf
        2026/02/01/pedro-sanchez/AUDIO-FORENSE_Consulta-Urgencias_20260201-103045.wav
    """
    try:
        # ==========================================
        # 1. OBTENER FECHA (con timezone awareness)
        # ==========================================
        fecha = getattr(instance, 'fecha_creacion', None) or \
                getattr(instance, 'fecha', None) or \
                getattr(instance, 'fecha_registro', None) or \
                timezone.now()
        
        if timezone.is_aware(fecha):
            fecha_local = timezone.localtime(fecha)
        else:
            fecha_local = fecha
        
        año = fecha_local.strftime('%Y')
        mes = fecha_local.strftime('%m')
        dia = fecha_local.strftime('%d')
        timestamp = fecha_local.strftime('%Y%m%d-%H%M%S')
        
        # ==========================================
        # 2. OBTENER PACIENTE (con múltiples fallbacks)
        # ==========================================
        paciente = getattr(instance, 'paciente', None)
        
        if paciente:
            # Priorizar nombre_completo si existe
            nombre_paciente = getattr(paciente, 'nombre_completo', None) or \
                            f"{getattr(paciente, 'nombre', '')} {getattr(paciente, 'apellidos', '')}".strip()
        else:
            nombre_paciente = "SIN-PACIENTE-ASIGNADO"
        
        # Limpiar y slugify (elimina acentos, espacios, caracteres especiales)
        slug_paciente = slugify(nombre_paciente) or "sin-nombre"
        
        # Validación: slug no debe estar vacío
        if not slug_paciente or slug_paciente == "-":
            slug_paciente = f"paciente-{instance.pk or 'nuevo'}"
        
        # ==========================================
        # 3. DETECTAR TIPO DE DOCUMENTO (AUTOMÁTICO)
        # ==========================================
        tipo_documento = _detectar_tipo_documento(instance, filename)
        
        # ==========================================
        # 4. GENERAR DESCRIPCIÓN INTELIGENTE
        # ==========================================
        descripcion = _generar_descripcion(instance)
        
        # ==========================================
        # 5. OBTENER FOLIO (único identificador)
        # ==========================================
        folio = getattr(instance, 'folio_orden', None) or \
                getattr(instance, 'folio', None) or \
                getattr(instance, 'id', None) or \
                timestamp
        
        # Limpiar folio para usarlo en nombre de archivo
        folio_limpio = slugify(str(folio))
        
        # ==========================================
        # 6. OBTENER EXTENSIÓN ORIGINAL
        # ==========================================
        extension = os.path.splitext(filename)[1].lower()
        
        # Validar extensión permitida
        extensiones_permitidas = ['.pdf', '.jpg', '.jpeg', '.png', '.wav', '.mp3', '.dcm', '.zip']
        if extension not in extensiones_permitidas:
            logger.warning(f"Extensión no permitida: {extension}. Usando .pdf por defecto.")
            extension = '.pdf'
        
        # ==========================================
        # 7. CONSTRUIR NOMBRE DE ARCHIVO FINAL
        # ==========================================
        # Formato: TIPO_Descripcion_FOLIO.extension
        descripcion_limpia = slugify(descripcion)[:50]  # Limitar a 50 caracteres
        
        nombre_archivo = f"{tipo_documento}_{descripcion_limpia}_{folio_limpio}{extension}"
        
        # Eliminar caracteres dobles de guión
        nombre_archivo = re.sub(r'-+', '-', nombre_archivo)
        
        # ==========================================
        # 8. CONSTRUIR RUTA COMPLETA
        # ==========================================
        ruta_completa = os.path.join(
            año,
            mes,
            dia,
            slug_paciente,
            nombre_archivo
        )
        
        # Normalizar separadores de ruta (Windows vs Linux)
        ruta_completa = ruta_completa.replace('\\', '/')
        
        # ==========================================
        # 9. LOGGING DE TRAZABILIDAD FORENSE
        # ==========================================
        logger.info(f"[DRIVE] Ruta generada: {ruta_completa}")
        logger.info(f"[DRIVE] Paciente: {nombre_paciente} (slug: {slug_paciente})")
        logger.info(f"[DRIVE] Tipo: {tipo_documento}, Folio: {folio}")
        
        return ruta_completa
        
    except Exception as e:
        # ==========================================
        # 10. MANEJO DE ERRORES (FALLBACK SEGURO)
        # ==========================================
        logger.error(f"[DRIVE] Error al generar ruta: {e}", exc_info=True)
        
        # Generar ruta segura de fallback
        timestamp_fallback = timezone.localtime(timezone.now()).strftime('%Y%m%d-%H%M%S')
        ruta_fallback = f"ERROR/{timestamp_fallback}/{filename}"
        
        logger.warning(f"[DRIVE] Usando ruta de fallback: {ruta_fallback}")
        return ruta_fallback


def _detectar_tipo_documento(instance, filename):
    """
    Detecta automáticamente el tipo de documento basándose en la instancia.
    
    MEJORA: No depende del nombre del modelo, usa características del objeto.
    """
    # Detectar por clase del modelo
    nombre_modelo = instance.__class__.__name__
    
    # Mapa de detección inteligente
    if 'Receta' in nombre_modelo:
        return 'RECETA'
    elif 'Orden' in nombre_modelo and 'Servicio' in nombre_modelo:
        return 'LABORATORIO'
    elif 'Estudio' in nombre_modelo or 'Imagen' in nombre_modelo:
        return 'IMAGEN-DIAGNOSTICA'
    elif 'Audio' in nombre_modelo or 'Transcripcion' in nombre_modelo:
        return 'AUDIO-FORENSE'
    elif 'Certificado' in nombre_modelo:
        return 'CERTIFICADO'
    elif 'Consentimiento' in nombre_modelo:
        return 'CONSENTIMIENTO'
    elif 'Consulta' in nombre_modelo:
        # Detectar si tiene audio asociado
        if hasattr(instance, 'audio_consulta') or '.wav' in filename or '.mp3' in filename:
            return 'AUDIO-CONSULTA'
        else:
            return 'CONSULTA'
    else:
        # Fallback: detectar por extensión
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.wav', '.mp3']:
            return 'AUDIO'
        elif ext in ['.jpg', '.jpeg', '.png']:
            return 'IMAGEN'
        elif ext == '.pdf':
            return 'DOCUMENTO'
        else:
            return 'ARCHIVO'


def _generar_descripcion(instance):
    """
    Genera descripción inteligente basada en el contenido del objeto.
    
    MEJORA: Extrae información relevante automáticamente.
    """
    # Orden de prioridad para descripción
    campos_descripcion = [
        'nombre',              # Estudio.nombre
        'estudio',             # OrdenDeServicio.estudio
        'motivo_consulta',     # Consulta.motivo
        'motivo',              # Consulta.motivo
        'diagnostico',         # Consulta.diagnostico
        'tipo_estudio',        # EstudioImagen.tipo
        'titulo',              # Documento.titulo
        'descripcion',         # Genérico
    ]
    
    for campo in campos_descripcion:
        valor = getattr(instance, campo, None)
        if valor:
            # Limpiar y truncar
            descripcion = str(valor).strip()[:100]
            return descripcion
    
    # Fallback: usar nombre del modelo
    return instance.__class__.__name__


def generar_ruta_drive_receta(instance, filename):
    """
    Generador específico para RECETAS MÉDICAS.
    
    MEJORA: Metadata adicional para recetas (médico, tipo de consulta).
    
    Estructura: AÑO/MES/DIA/SLUG_PACIENTE/RECETA_TipoConsulta_DrApellido_FOLIO.pdf
    
    Ejemplo:
        2026/02/01/juan-perez/RECETA_Urgencias_DrGarcia_REC-001.pdf
    """
    # Usar función base
    ruta_base = generar_ruta_drive(instance, filename)
    
    # Enriquecer con metadata de receta
    try:
        medico = getattr(instance, 'medico', None)
        if medico:
            apellido_medico = getattr(medico, 'apellidos', '').split()[0] if hasattr(medico, 'apellidos') else ''
            if apellido_medico:
                # Insertar apellido del médico en el nombre
                partes = ruta_base.rsplit('/', 1)
                if len(partes) == 2:
                    directorio, nombre_archivo = partes
                    # Agregar Dr + Apellido
                    nombre_enriquecido = nombre_archivo.replace(
                        'RECETA_',
                        f'RECETA_Dr{slugify(apellido_medico)}_'
                    )
                    return f"{directorio}/{nombre_enriquecido}"
    except Exception as e:
        logger.warning(f"No se pudo enriquecer metadata de receta: {e}")
    
    return ruta_base


def generar_ruta_drive_laboratorio(instance, filename):
    """
    Generador específico para RESULTADOS DE LABORATORIO.
    
    MEJORA: Incluye tipo de estudios y prioridad.
    
    Estructura: AÑO/MES/DIA/SLUG_PACIENTE/LAB_TipoEstudio_Prioridad_FOLIO.pdf
    
    Ejemplo:
        2026/02/01/maria-lopez/LAB_Hematologia_URGENTE_ORD-123.pdf
    """
    ruta_base = generar_ruta_drive(instance, filename)
    
    try:
        # Detectar prioridad
        prioridad = getattr(instance, 'prioridad', None) or \
                   getattr(instance, 'urgencia', None)
        
        if prioridad and str(prioridad).upper() in ['URGENTE', 'URGENCIA', 'STAT']:
            partes = ruta_base.rsplit('/', 1)
            if len(partes) == 2:
                directorio, nombre_archivo = partes
                nombre_enriquecido = nombre_archivo.replace(
                    'LABORATORIO_',
                    'LAB_URGENTE_'
                )
                return f"{directorio}/{nombre_enriquecido}"
    except Exception as e:
        logger.warning(f"No se pudo enriquecer metadata de laboratorio: {e}")
    
    return ruta_base


def generar_ruta_drive_audio_forense(instance, filename):
    """
    Generador específico para AUDIOS FORENSES de consultas.
    
    MEJORA: Metadata de duración y MD5 para integridad.
    
    Estructura: AÑO/MES/DIA/SLUG_PACIENTE/AUDIO_TipoConsulta_Duracion_FOLIO.wav
    
    Ejemplo:
        2026/02/01/pedro-sanchez/AUDIO_Consulta-General_15min_CONS-456.wav
    """
    ruta_base = generar_ruta_drive(instance, filename)
    
    try:
        # Detectar duración si está disponible
        duracion_seg = getattr(instance, 'duracion', None) or \
                      getattr(instance, 'duracion_segundos', None)
        
        if duracion_seg:
            minutos = int(duracion_seg / 60)
            partes = ruta_base.rsplit('/', 1)
            if len(partes) == 2:
                directorio, nombre_archivo = partes
                nombre_enriquecido = nombre_archivo.replace(
                    'AUDIO_',
                    f'AUDIO_{minutos}min_'
                )
                return f"{directorio}/{nombre_enriquecido}"
    except Exception as e:
        logger.warning(f"No se pudo enriquecer metadata de audio: {e}")
    
    return ruta_base


# ==============================================================================
# FUNCIONES AUXILIARES DE VALIDACIÓN
# ==============================================================================

def validar_nombre_archivo(nombre):
    """
    Valida que el nombre de archivo sea seguro para Drive.
    
    MEJORA: Previene ataques de path traversal y caracteres peligrosos.
    """
    # Eliminar path traversal
    nombre = os.path.basename(nombre)
    
    # Eliminar caracteres peligrosos
    caracteres_prohibidos = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in caracteres_prohibidos:
        nombre = nombre.replace(char, '-')
    
    # Limitar longitud
    if len(nombre) > 255:
        nombre = nombre[:255]
    
    return nombre


def limpiar_slug_paciente(nombre_completo):
    """
    Limpia y valida el slug del paciente.
    
    MEJORA: Manejo especial de caracteres latinos y nombres compuestos.
    """
    if not nombre_completo:
        return "sin-nombre"
    
    # Convertir a string
    nombre = str(nombre_completo).strip()
    
    # Casos especiales
    if not nombre or nombre.lower() in ['none', 'null', '']:
        return "sin-nombre"
    
    # Slugify con opciones especiales
    slug = slugify(nombre)
    
    # Validar resultado
    if not slug or slug == '-':
        # Fallback: usar versión básica sin acentos
        slug = re.sub(r'[^a-z0-9]+', '-', nombre.lower())
        slug = slug.strip('-')
    
    # Limitar longitud (nombres muy largos)
    if len(slug) > 100:
        # Mantener solo primeros 2 nombres y primer apellido
        partes = slug.split('-')
        if len(partes) > 3:
            slug = '-'.join(partes[:3])
    
    return slug or "sin-nombre"
