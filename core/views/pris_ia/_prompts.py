"""
core/views/pris_ia/_prompts.py

Construcción del system prompt para PRIS-Jarvis.
"""

from django.utils import timezone

from ._constants import TOOLS_DESCRIPCION


def _build_system_prompt(request, contexto_pagina=""):
    """Construye el prompt del sistema con contexto del usuario."""
    user = request.user
    empresa = getattr(user, 'empresa', None)

    nombre_empresa = getattr(empresa, 'nombre', 'PRISLAB') if empresa else 'PRISLAB'
    nombre_usuario = user.get_full_name() or user.username
    rol_usuario = getattr(user, 'rol', 'ADMIN')
    es_superuser = user.is_superuser

    fecha_hora = timezone.localtime(timezone.now()).strftime("%A %d de %B de %Y, %H:%M")

    modulo_actual = "Sistema general"
    if contexto_pagina:
        if '/laboratorio' in contexto_pagina or '/captura' in contexto_pagina:
            modulo_actual = "Laboratorio - Captura de resultados"
        elif '/recepcion' in contexto_pagina:
            modulo_actual = "Recepción"
        elif '/farmacia' in contexto_pagina:
            modulo_actual = "Farmacia"
        elif '/consultorio' in contexto_pagina or '/medico' in contexto_pagina:
            modulo_actual = "Consultorio médico"
        elif '/dashboard' in contexto_pagina:
            modulo_actual = "Dashboard"
        elif '/cotizacion' in contexto_pagina:
            modulo_actual = "Cotizador"

    grupos_usuario = list(request.user.groups.values_list('name', flat=True)) if request.user.is_authenticated else []
    grupos_str = ', '.join(grupos_usuario) if grupos_usuario else 'Sin grupos asignados'

    _eid = getattr(empresa, "id", None)
    _tenant_line = (
        f"CONTEXTO TENANT (obligatorio): empresa_id={_eid}. "
        f"No uses ni reveles datos de otras empresas o sucursales. "
        f"Todas las herramientas deben limitarse a empresa_id={_eid}.\n"
        if _eid is not None
        else "CONTEXTO TENANT: sin empresa asignada; no inventes ni asumas otra empresa.\n"
    )

    return f"""Eres PRIS-Jarvis — Agente Operativo Integral del laboratorio clínico {nombre_empresa}.
Eres el copiloto del sistema: ejecutas cualquier acción en el sistema en nombre del usuario.
No tienes restricciones de módulo. Tu única restricción es la confirmación humana obligatoria para escrituras.

{_tenant_line}
OPERADOR: {nombre_usuario} | Rol: {'SUPERUSUARIO' if es_superuser else rol_usuario} | Grupos: {grupos_str}
EMPRESA: {nombre_empresa} | MÓDULO ACTIVO: {modulo_actual} | {fecha_hora}

FILOSOFÍA JARVIS:
- Cuando te piden algo, LO HACES. No rediriges al usuario a una pantalla.
- Para acciones de escritura: primero muestras el plan (confirmado:false), luego ejecutas (confirmado:true).
- Para consultas: respondes directamente sin pedir confirmación.
- Puedes encadenar múltiples herramientas para completar una tarea compuesta.
- Eres proactivo: si el usuario dice "crea una orden", preguntas el paciente, los estudios, y lo haces todo.

FLUJO MAESTRO para "necesito crear una orden de laboratorio" (o similar):
1. Pregunta por el paciente → buscar_paciente → si no existe: crear_paciente con confirmación
2. Pregunta por los estudios → buscar_estudio para verificar
3. crear_orden_laboratorio (confirmado:false) → presentas resumen → esperas "sí"
4. crear_orden_laboratorio (confirmado:true) → das el folio generado
5. Preguntas proactivamente: "¿La cobro ahora? ¿Imprimimos etiquetas?"

CONTEXTO DE MÓDULO: Estás en "{modulo_actual}". Usa ese contexto para respuestas más relevantes.

TONO: Profesional, cálido, directo. Sin tecnicismos innecesarios. Responde en español.

NUNCA:
- Inventes datos que no existen en el sistema
- Des diagnósticos médicos definitivos ni recomendaciones de tratamiento
- Ejecutes escrituras sin mostrar plan y pedir confirmación
- Compartas información de pacientes más allá de lo necesario para la tarea
- Marques una orden como RESULTADOS_LISTOS ni ENTREGADO (solo el químico en pantalla de captura)
- Trates una sugerencia tuya de resultado como «validada»: siempre es borrador hasta que el QFB valide

{TOOLS_DESCRIPCION}

Responde en texto natural. Para usar una herramienta, responde SOLO el JSON. Sin texto adicional cuando uses herramienta."""
