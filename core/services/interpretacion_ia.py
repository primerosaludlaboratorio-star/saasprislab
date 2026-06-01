"""
PRISLAB R107 - Motor de Interpretacion IA para Resultados de Laboratorio
=========================================================================
Genera un "Resumen de Bienestar" amigable para el paciente usando Gemini.
NO es un diagnostico medico - es una explicacion sencilla de si los valores
estan en rangos normales.

Uso:
    from core.services.interpretacion_ia import generar_resumen_bienestar
    texto = generar_resumen_bienestar(orden)
"""

import logging

logger = logging.getLogger(__name__)

# Prompt del sistema - instrucciones estrictas para evitar diagnosticos
SYSTEM_PROMPT = """Eres un asistente de laboratorio clinico. Tu trabajo es explicar 
resultados de laboratorio de forma SENCILLA y AMIGABLE para que un paciente sin 
conocimiento medico pueda entender sus resultados.

REGLAS ESTRICTAS:
1. NUNCA des un diagnostico medico.
2. NUNCA recomiendes medicamentos.
3. NUNCA digas "usted tiene" o "usted padece".
4. USA frases como "tus valores sugieren", "se encuentran dentro de lo esperado", 
   "podria ser bueno consultar con tu medico".
5. Maximo 4-5 oraciones cortas.
6. Si hay valores fuera de rango, di: "Algunos valores estan ligeramente fuera del 
   rango de referencia, tu medico podra orientarte mejor."
7. Siempre termina con: "Recuerda que este resumen es informativo y no sustituye 
   la consulta medica."
8. Escribe en espanol neutro sin acentos.
9. NO uses formato markdown, solo texto plano."""


def generar_resumen_bienestar(orden):
    """
    Genera un resumen de bienestar amigable basado en los resultados de la orden.
    
    Args:
        orden: OrdenDeServicio instance con resultados ya capturados.
    
    Returns:
        str: Texto del resumen, o None si no se puede generar.
    """
    try:
        from core.models import ResultadoParametro
        
        # Obtener resultados de la orden
        resultados = ResultadoParametro.objects.filter(
            orden=orden,
            valor__isnull=False,
        ).exclude(
            valor=''
        ).exclude(
            valor='Pendiente'
        ).select_related('parametro')
        
        if not resultados.exists():
            return None
        
        # Construir contexto para la IA
        lineas_resultado = []
        hay_fuera_rango = False
        hay_critico = False
        
        for r in resultados:
            nombre = r.parametro.nombre if r.parametro else 'Parametro'
            valor = r.valor
            unidad = r.parametro.unidad or '' if r.parametro else ''
            estado = 'normal'
            
            if r.fuera_rango:
                estado = 'fuera de rango'
                hay_fuera_rango = True
            if r.es_critico:
                estado = 'critico'
                hay_critico = True
            
            lineas_resultado.append(f"- {nombre}: {valor} {unidad} ({estado})")
        
        if not lineas_resultado:
            return None
        
        # Construir el prompt
        paciente = orden.paciente
        nombre = paciente.nombre_completo if paciente else 'Paciente'
        
        prompt = f"""{SYSTEM_PROMPT}

Paciente: {nombre}
Resultados del laboratorio:
{chr(10).join(lineas_resultado)}

Genera un resumen de bienestar breve (maximo 5 oraciones) para este paciente. 
{"NOTA: Hay valores fuera de rango, mencionalo con tacto." if hay_fuera_rango else ""}
{"NOTA: Hay valores criticos, recomienda visitar al medico pronto." if hay_critico else ""}"""
        
        # Llamar a Gemini usando el helper de alto nivel (evita el bug
        # 'str has no attribute generate_content': get_gemini_model() retorna
        # un str con el nombre del modelo, no un objeto modelo invocable).
        from core.utils.gemini_client import generate_content as _gemini_gen
        texto_raw = _gemini_gen(
            prompt,
            model_name='gemini-2.0-flash',
            temperature=0.3,
            max_tokens=300,
        )
        if texto_raw:
            texto = texto_raw.strip().replace('**', '').replace('*', '').replace('#', '')
            logger.info(f"[IA] Resumen de bienestar generado para orden {orden.folio_orden}")
            return texto

        return None
        
    except Exception as e:
        logger.warning(f"[IA] No se pudo generar resumen de bienestar: {e}")
        return None
