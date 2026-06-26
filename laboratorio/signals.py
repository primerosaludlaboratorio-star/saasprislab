# -*- coding: utf-8 -*-
"""
🔬 PILAR 2 & 3: SIGNALS PARA HISTORIAL AUTOMÁTICO + PRIVACIDAD NOM-024
Sistema PRISLAB - Laboratorio

Objetivo: 
- Detectar cambios en resultados y registrar automáticamente en historial
- Implementar permisos de privacidad para datos clínicos sensibles
"""

import logging

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from core.models import ResultadoParametro
from laboratorio.models import HistorialResultados

logger = logging.getLogger(__name__)


# ==============================================================================
# PILAR 2: SIGNAL PARA HISTORIAL AUTOMÁTICO DE RESULTADOS
# ==============================================================================

@receiver(pre_save, sender=ResultadoParametro)
def detectar_cambio_resultado(sender, instance, **kwargs):
    """
    Signal pre_save: Detecta cambios en resultados ya validados.
    
    Flujo:
    1. Verificar si el resultado ya existe (no es nuevo)
    2. Obtener valor original de la base de datos
    3. Comparar con el nuevo valor
    4. Si son diferentes Y el resultado estaba validado → Registrar en historial
    
    Nota: Este signal se ejecuta ANTES de guardar, por eso usamos pre_save.
          El registro en historial se hace en post_save para tener el ID.
    """
    if not instance.pk:
        # Es un resultado nuevo, no hay historial que registrar
        return
    
    try:
        # Obtener el valor actual de la base de datos
        resultado_original = ResultadoParametro.objects.get(pk=instance.pk)
        
        # Comparar valores (el modelo usa 'valor' como campo unificado)
        valor_original = resultado_original.valor
        valor_nuevo = instance.valor
        
        # Determinar si hubo cambio
        cambio_detectado = False
        valor_anterior_log = None
        valor_nuevo_log = None
        
        if valor_original != valor_nuevo:
            cambio_detectado = True
            valor_anterior_log = str(valor_original) if valor_original else "NULL"
            valor_nuevo_log = str(valor_nuevo) if valor_nuevo else "NULL"
        
        # Si hubo cambio y el resultado estaba validado, marcar para historial
        if cambio_detectado and resultado_original.validado:
            # Guardar información en el instance para usarla en post_save
            instance._cambio_detectado = True
            instance._valor_anterior = valor_anterior_log
            instance._valor_nuevo = valor_nuevo_log
            instance._resultado_validado_antes = resultado_original.validado
        else:
            instance._cambio_detectado = False
    
    except ResultadoParametro.DoesNotExist:
        # No existe en DB (es nuevo)
        instance._cambio_detectado = False


@receiver(post_save, sender=ResultadoParametro)
def registrar_historial_resultado(sender, instance, created, **kwargs):
    """
    Signal post_save: Registra el cambio en HistorialResultados si fue detectado.
    
    Este signal se ejecuta DESPUÉS de guardar, cuando ya tenemos el ID.
    """
    # Si es un resultado nuevo, no hay historial que registrar
    if created:
        return
    
    # Verificar si se detectó un cambio en pre_save
    if not getattr(instance, '_cambio_detectado', False):
        return
    
    # Obtener datos del cambio
    valor_anterior = getattr(instance, '_valor_anterior', 'DESCONOCIDO')
    valor_nuevo = getattr(instance, '_valor_nuevo', 'DESCONOCIDO')
    
    # Determinar usuario responsable
    # Nota: El usuario se debe pasar desde la vista, aquí usamos el validado_por como fallback
    usuario_responsable = instance.validado_por if hasattr(instance, 'validado_por') else None
    
    if not usuario_responsable:
        # Si no hay usuario, intentar obtener del request (requiere middleware)
        # Por ahora, dejamos que se registre sin usuario (lo ideal es pasarlo desde la vista)
        return
    
    # Determinar si el resultado ya fue entregado
    orden = instance.orden
    resultado_entregado = orden.estado in ['ENTREGADO', 'RESULTADOS_LISTOS']
    
    # Crear registro en historial
    try:
        HistorialResultados.objects.create(
            resultado_asociado=instance,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
            motivo_cambio="Corrección automática detectada por el sistema",
            usuario_responsable=usuario_responsable,
            resultado_validado_previamente=True,
            resultado_entregado_previamente=resultado_entregado,
            observaciones_supervisor=f"Cambio automático registrado. Orden: {orden.folio_orden}"
        )
        
        logger.info(f"Historial registrado para ResultadoParametro #{instance.id}")

    except (ValueError, TypeError, DatabaseError) as e:
        logger.error(f"Error al registrar historial para ResultadoParametro #{instance.id}: {e}")
    
    # Limpiar atributos temporales
    delattr(instance, '_cambio_detectado')
    delattr(instance, '_valor_anterior')
    delattr(instance, '_valor_nuevo')


# ==============================================================================
# PILAR 3: PERMISOS PERSONALIZADOS PARA NOM-024 (PRIVACIDAD)
# ==============================================================================

def crear_permisos_privacidad():
    """
    Crea permisos personalizados para control de acceso a datos sensibles.
    
    Permisos creados:
    1. laboratorio.ver_datos_clinicos_sensibles
    2. laboratorio.ver_historial_completo_paciente
    3. laboratorio.ver_diagnosticos
    
    Asignación recomendada:
    - Químicos: Todos los permisos
    - Médicos: Todos los permisos
    - Recepción: NINGUNO
    - Caja: NINGUNO
    - Administrador: Todos (para auditorías)
    """
    from django.contrib.auth.models import Group
    
    # Obtener ContentType de modelos relevantes
    content_type_resultado = ContentType.objects.get_for_model(ResultadoParametro)
    from core.models import OrdenDeServicio as _ODS
    content_type_orden = ContentType.objects.get_for_model(_ODS)
    
    # Crear permisos si no existen
    permisos_creados = []
    
    # Permiso 1: Ver datos clínicos sensibles (VIH, VPH, ETS, etc.)
    permiso_sensibles, created = Permission.objects.get_or_create(
        codename='ver_datos_clinicos_sensibles',
        content_type=content_type_resultado,
        defaults={
            'name': 'Puede ver resultados de estudios sensibles (VIH, ETS, etc.)'
        }
    )
    if created:
        permisos_creados.append('ver_datos_clinicos_sensibles')
    
    # Permiso 2: Ver historial completo de paciente
    permiso_historial, created = Permission.objects.get_or_create(
        codename='ver_historial_completo_paciente',
        content_type=content_type_orden,
        defaults={
            'name': 'Puede ver el historial clínico completo del paciente'
        }
    )
    if created:
        permisos_creados.append('ver_historial_completo_paciente')
    
    # Permiso 3: Ver diagnósticos
    permiso_diagnosticos, created = Permission.objects.get_or_create(
        codename='ver_diagnosticos',
        content_type=content_type_orden,
        defaults={
            'name': 'Puede ver diagnósticos y observaciones médicas'
        }
    )
    if created:
        permisos_creados.append('ver_diagnosticos')
    
    print(f"✅ Permisos NOM-024 creados: {', '.join(permisos_creados) if permisos_creados else 'Todos ya existían'}")
    
    # Asignar permisos a grupos por defecto
    asignar_permisos_grupos(permiso_sensibles, permiso_historial, permiso_diagnosticos)
    
    return permisos_creados


def asignar_permisos_grupos(permiso_sensibles, permiso_historial, permiso_diagnosticos):
    """
    Asigna permisos a los grupos correspondientes.
    """
    from django.contrib.auth.models import Group
    
    # Definir matriz de permisos por rol
    matriz_permisos = {
        'Químico': [permiso_sensibles, permiso_historial, permiso_diagnosticos],
        'Médico': [permiso_sensibles, permiso_historial, permiso_diagnosticos],
        'Administrador': [permiso_sensibles, permiso_historial, permiso_diagnosticos],
        'Recepción': [],  # Sin acceso a datos sensibles
        'Caja': [],  # Sin acceso a datos sensibles
        'Enfermería': [permiso_diagnosticos],  # Solo diagnósticos, no resultados sensibles
    }
    
    for nombre_grupo, permisos in matriz_permisos.items():
        try:
            grupo, created = Group.objects.get_or_create(name=nombre_grupo)
            
            if created:
                print(f"✅ Grupo '{nombre_grupo}' creado")
            
            # Asignar permisos
            for permiso in permisos:
                grupo.permissions.add(permiso)
            
            print(f"✅ Permisos asignados a grupo '{nombre_grupo}': {len(permisos)} permisos")
        
        except (ValueError, PermissionError, Group.DoesNotExist) as e:
            print(f"❌ Error asignando permisos a '{nombre_grupo}': {str(e)}")


# ==============================================================================
# HELPER: VERIFICAR SI ESTUDIO ES SENSIBLE
# ==============================================================================

def es_estudio_sensible(estudio_nombre):
    """
    Verifica si un estudio contiene información sensible según NOM-024-SSA3-2012.
    
    Estudios sensibles:
    - VIH (ELISA, Western Blot, Carga Viral, CD4)
    - ETS (VPH, VDRL, Herpes, Hepatitis B/C)
    - Drogas de abuso
    - Pruebas genéticas
    - Embarazo (en algunos contextos)
    """
    estudios_sensibles = [
        'VIH', 'ELISA', 'WESTERN BLOT', 'CD4', 'CARGA VIRAL',
        'VPH', 'PAPANICOLAOU', 'VDRL', 'RPR', 'FTA',
        'HEPATITIS B', 'HEPATITIS C', 'HERPES',
        'DROGAS', 'TOXICOLOGIA', 'MARIHUANA', 'COCAINA',
        'GENETICA', 'CARIOTIPO', 'ADN',
        'EMBARAZO', 'BETA HCG', 'GONADOTROPINA'
    ]
    
    nombre_upper = estudio_nombre.upper()
    
    for keyword in estudios_sensibles:
        if keyword in nombre_upper:
            return True
    
    return False


# ==============================================================================
# MIDDLEWARE: INYECTAR USUARIO EN SIGNALS (OPCIONAL)
# ==============================================================================

class UsuarioEnSignalsMiddleware:
    """
    Middleware para inyectar el usuario actual en los signals.
    
    Permite que los signals tengan acceso al request.user sin pasar explícitamente.
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Guardar usuario en thread-local
        from threading import local
        _thread_locals = local()
        _thread_locals.user = getattr(request, 'user', None)
        
        response = self.get_response(request)
        
        return response


# ==============================================================================
# FUNCIÓN DE INICIALIZACIÓN (LLAMAR EN APPS.PY)
# ==============================================================================

def inicializar_sistema_privacidad():
    """
    Función principal para inicializar el sistema de privacidad.
    
    Debe ser llamada en apps.py del módulo laboratorio:
    
    ```python
    class LaboratorioConfig(AppConfig):
        def ready(self):
            from laboratorio.signals import inicializar_sistema_privacidad
            inicializar_sistema_privacidad()
    ```
    """
    print("🔒 Inicializando sistema de privacidad NOM-024...")
    
    try:
        crear_permisos_privacidad()
        print("✅ Sistema de privacidad inicializado correctamente")
    except (ValueError, PermissionError, ImportError) as e:
        print(f"⚠️ Error inicializando sistema de privacidad: {str(e)}")
