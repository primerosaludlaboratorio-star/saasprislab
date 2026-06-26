"""
Vista para el Reporte Guiado de Fricción (Evolución del Buzón de Sugerencias).
Sistema de wizard paso a paso para capturar problemas de forma estructurada.
"""
import json
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib import messages

from core.models import BuzonQuejas, Empresa


@login_required
def reporte_friccion(request):
    """
    Vista principal del Reporte Guiado de Fricción.
    Muestra el wizard paso a paso con integración de PRIS.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    paso_actual = int(request.GET.get('paso', 1))
    
    # Si es POST, procesar el paso actual
    if request.method == 'POST':
        paso = int(request.POST.get('paso', 1))
        
        if paso == 1:
            # Paso 1: Identificación del Dolor
            modulo = request.POST.get('modulo_afectado', '')
            if not modulo:
                messages.error(request, 'Por favor, selecciona el módulo donde ocurre la fricción.')
                return render(request, 'core/reporte_friccion.html', {
                    'empresa': empresa,
                    'paso_actual': 1,
                    'usuario': request.user
                })
            
            # Guardar en sesión
            request.session['reporte_friccion'] = {
                'modulo_afectado': modulo,
                'paso': 2
            }
            return redirect(reverse('reporte_friccion') + '?paso=2')
        
        elif paso == 2:
            # Paso 2: Diagnóstico Guiado
            que_intentabas = request.POST.get('que_intentabas_hacer', '').strip()
            que_te_detiene = request.POST.get('que_te_detiene', '').strip()
            es_tecnico_o_proceso = request.POST.get('es_tecnico_o_proceso', '')
            
            if not que_intentabas or not que_te_detiene or not es_tecnico_o_proceso:
                messages.error(request, 'Por favor, completa todos los campos del diagnóstico.')
                return render(request, 'core/reporte_friccion.html', {
                    'empresa': empresa,
                    'paso_actual': 2,
                    'usuario': request.user,
                    'datos_paso1': request.session.get('reporte_friccion', {})
                })
            
            # Actualizar sesión
            datos = request.session.get('reporte_friccion', {})
            datos.update({
                'que_intentabas_hacer': que_intentabas,
                'que_te_detiene': que_te_detiene,
                'es_tecnico_o_proceso': es_tecnico_o_proceso,
                'paso': 3
            })
            request.session['reporte_friccion'] = datos
            return redirect(reverse('reporte_friccion') + '?paso=3')
        
        elif paso == 3:
            # Paso 3: El Punto Crítico
            impacto = request.POST.get('impacto_tiempo', '')
            
            if not impacto:
                messages.error(request, 'Por favor, selecciona el impacto en tiempo.')
                return render(request, 'core/reporte_friccion.html', {
                    'empresa': empresa,
                    'paso_actual': 3,
                    'usuario': request.user,
                    'datos_paso1': request.session.get('reporte_friccion', {})
                })
            
            # Actualizar sesión
            datos = request.session.get('reporte_friccion', {})
            datos.update({
                'impacto_tiempo': impacto,
                'paso': 4
            })
            request.session['reporte_friccion'] = datos
            return redirect(reverse('reporte_friccion') + '?paso=4')
        
        elif paso == 4:
            # Paso 4: La Chispa de Mejora
            solucion = request.POST.get('solucion_propuesta', '').strip()
            
            if not solucion:
                messages.error(request, 'Por favor, comparte tu solución propuesta.')
                return render(request, 'core/reporte_friccion.html', {
                    'empresa': empresa,
                    'paso_actual': 4,
                    'usuario': request.user,
                    'datos_paso1': request.session.get('reporte_friccion', {})
                })
            
            # Obtener todos los datos de la sesión
            datos = request.session.get('reporte_friccion', {})
            
            # Determinar categoría automática
            categoria = determinar_categoria_automatica(datos)
            
            # Generar punto crítico
            punto_critico = generar_punto_critico(datos)
            
            # Crear el reporte
            # Incluir toda la info de friccion en el campo mensaje
            mensaje_completo = (
                f"Módulo: {datos.get('modulo_afectado', 'N/A')}\n"
                f"Qué intentaba hacer: {datos.get('que_intentabas_hacer', '')}\n"
                f"Qué lo detuvo: {datos.get('que_te_detiene', '')}\n"
                f"Técnico o proceso: {datos.get('es_tecnico_o_proceso', 'N/A')}\n"
                f"Impacto tiempo: {datos.get('impacto_tiempo', 'N/A')}\n"
                f"Punto crítico: {punto_critico}\n"
                f"Solución propuesta: {solucion}"
            )
            reporte = BuzonQuejas.objects.create(
                empresa=empresa,
                tipo='SUGERENCIA',
                mensaje=mensaje_completo,
                nombre_remitente=request.user.get_full_name() or request.user.username,
                contacto=request.user.email or '',
                anonimo=False,
                estado='PENDIENTE',
                categoria_ia=categoria,
                plan_accion_sugerido=solucion,
            )
            
            # Limpiar sesión
            if 'reporte_friccion' in request.session:
                del request.session['reporte_friccion']
            
            messages.success(request, '¡Gracias por tu reporte! Tu opinión nos ayuda a mejorar PRISLAB.')
            return redirect('buzon_kanban')
    
    # GET: Mostrar el paso actual
    datos_sesion = request.session.get('reporte_friccion', {})
    
    return render(request, 'core/reporte_friccion.html', {
        'empresa': empresa,
        'paso_actual': paso_actual,
        'usuario': request.user,
        'datos_paso1': datos_sesion
    })


def determinar_categoria_automatica(datos):
    """
    Determina la categoría automática basándose en las respuestas.
    """
    es_tecnico = datos.get('es_tecnico_o_proceso', '')
    impacto = datos.get('impacto_tiempo', '')
    
    if es_tecnico == 'TECNICO':
        return 'ERROR_TECNICO'
    elif es_tecnico == 'PROCESO':
        return 'PROCESO'
    elif impacto == 'AFECTA_PACIENTE':
        return 'BIENESTAR'
    else:
        return 'OPTIMIZACION'


def generar_punto_critico(datos):
    """
    Genera un resumen del punto crítico para destacar en el Kanban.
    """
    modulo = datos.get('modulo_afectado', 'Desconocido')
    que_detiene = datos.get('que_te_detiene', '')
    impacto = datos.get('impacto_tiempo', '')
    
    # Extraer las primeras palabras clave
    palabras_clave = que_detiene.split()[:10]
    resumen = ' '.join(palabras_clave)
    
    punto = f"[{modulo}] {resumen}"
    
    if impacto == 'AFECTA_PACIENTE':
        punto += " ⚠️ AFECTA ATENCIÓN AL PACIENTE"
    elif 'MAS_30_MIN' in impacto:
        punto += " ⏱️ IMPACTO ALTO EN TIEMPO"
    
    return punto


@login_required
@require_http_methods(["POST"])
def api_pris_ayuda(request):
    """
    API para que PRIS ayude al usuario durante el reporte.
    """
    paso = int(request.POST.get('paso', 1))
    contexto = request.POST.get('contexto', '')
    
    # Mensajes de apoyo de PRIS según el paso
    mensajes_pris = {
        1: "Hola, soy PRIS. Tu opinión nos ayuda a que PRISLAB sea un mejor lugar para trabajar. ¿En qué módulo estás experimentando la fricción?",
        2: "Perfecto. Ahora necesito entender mejor el problema. ¿Qué estabas intentando hacer cuando encontraste el obstáculo?",
        3: "Entiendo. Este problema está afectando tu eficiencia. ¿Cuánto tiempo te está costando o cómo afecta a la atención del paciente?",
        4: "Excelente. Ahora, si tú fueras el arquitecto del sistema, ¿cómo lo solucionarías? Tu perspectiva es valiosa."
    }
    
    mensaje = mensajes_pris.get(paso, "Continúa con el siguiente paso. Estoy aquí para ayudarte.")
    
    return JsonResponse({
        'status': 'success',
        'mensaje': mensaje,
        'paso': paso
    })

# NOTA: `buzon_kanban` vivía aquí duplicado y, por orden de import en
# core/views/__init__.py, sombreaba al canónico de core/views/buzon.py — que sí
# usa las categorías reales de BuzonQuejas.categoria_ia (TIEMPOS/TRATO/PRECIOS…).
# Esta copia agrupaba por categorías de fricción inexistentes (OPTIMIZACION/…),
# dejando el desglose por categoría siempre en 0. Eliminado para resolver la
# colisión; la ruta director/buzon usa ahora el de core/views/buzon.py.
