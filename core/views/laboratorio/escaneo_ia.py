"""
Escaneo IA (recetas médicas, identificaciones), dashboard de pendientes.
"""
import io
import re
import json
import logging
import traceback

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from django.db.models import Q

from core.models import (
    OrdenDeServicio, DetalleOrden,
)
from core.lims_cart import search_lims_catalog

logger = logging.getLogger('core')


@login_required
@require_http_methods(["POST"])
def escanear_receta_ia(request):
    """
    Vista para escanear recetas médicas usando Gemini Vision API.
    Recibe una imagen y devuelve JSON con datos extraídos.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    try:
        # Verificar que hay API Key configurada
        if not settings.GOOGLE_API_KEY:
            return JsonResponse({
                'error': 'GOOGLE_API_KEY no configurada. Configure la variable de entorno GOOGLE_API_KEY.'
            }, status=500)

        # Obtener la imagen del request
        if 'imagen' not in request.FILES:
            return JsonResponse({'error': 'No se recibió ninguna imagen'}, status=400)

        imagen_file = request.FILES['imagen']

        # Leer la imagen
        imagen_bytes = imagen_file.read()

        # Preparar el prompt del sistema
        prompt_sistema = """Actúa como un asistente de laboratorio experto. Analiza esta imagen de receta médica y extrae la información en formato JSON estricto.

IMPORTANTE: Responde SOLO con un objeto JSON válido, sin texto adicional, sin markdown, sin explicaciones.

Formato requerido:
{
  "nombre_paciente": "string o 'DUDA' si no se puede leer",
  "edad": número entero o null si no se encuentra,
  "fecha_receta": "YYYY-MM-DD o 'DUDA' si no se puede leer",
  "estudios_detectados": ["lista", "de", "estudios", "encontrados"]
}

Si algún campo no se puede leer claramente, usa 'DUDA' para strings o null para números.
Para estudios_detectados, lista todos los nombres de estudios, análisis o pruebas que encuentres en la receta.
"""

        # Usar cliente centralizado google.genai
        from core.utils.gemini_client import get_gemini_client
        import base64
        client = get_gemini_client()

        # Codificar imagen como base64 para la API
        imagen_b64 = base64.b64encode(imagen_bytes).decode('utf-8')
        mime_type = imagen_file.content_type or 'image/jpeg'

        from google.genai import types as genai_types
        image_part = genai_types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type)

        # Generar contenido con Gemini (multimodal)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt_sistema, image_part],
        )

        # Extraer el texto de la respuesta
        texto_respuesta = response.text.strip()

        # Limpiar el texto (puede venir con markdown o código)
        if texto_respuesta.startswith('```json'):
            texto_respuesta = texto_respuesta[7:]
        if texto_respuesta.startswith('```'):
            texto_respuesta = texto_respuesta[3:]
        if texto_respuesta.endswith('```'):
            texto_respuesta = texto_respuesta[:-3]
        texto_respuesta = texto_respuesta.strip()

        # Parsear JSON
        try:
            datos_extraidos = json.loads(texto_respuesta)
        except json.JSONDecodeError as e:
            # Si falla el parseo, intentar extraer el JSON manualmente
            json_match = re.search(r'\{[^{}]*\}', texto_respuesta, re.DOTALL)
            if json_match:
                try:
                    datos_extraidos = json.loads(json_match.group())
                except json.JSONDecodeError:
                    return JsonResponse({
                        'error': f'Error al parsear respuesta de Gemini: {str(e)}. Respuesta recibida: {texto_respuesta[:200]}'
                    }, status=500)
            else:
                return JsonResponse({
                    'error': f'No se pudo extraer JSON de la respuesta: {texto_respuesta[:200]}'
                }, status=500)

        # Validar estructura básica
        estudios_detectados = datos_extraidos.get('estudios_detectados', [])

        # RECEPCIÓN AUTOMATIZADA: Buscar estudios en el catálogo y sugerirlos
        estudios_sugeridos = []
        if estudios_detectados:
            for nombre_estudio in estudios_detectados:
                if nombre_estudio and nombre_estudio != 'DUDA':
                    for row in search_lims_catalog(nombre_estudio, empresa=empresa, limit_analitos=3, limit_otros=2):
                        estudios_sugeridos.append({
                            'id': row.get('id'),
                            'codigo': row.get('codigo') or '',
                            'nombre': row.get('nombre') or '',
                            'precio': float(row.get('precio') or 0),
                            'indicaciones': row.get('indicaciones') or '',
                            'es_perfil': bool(row.get('es_perfil')),
                            'descripcion_interna': row.get('descripcion_interna') or '',
                            'coincidencia': nombre_estudio,
                        })

        # Eliminar duplicados (por ID)
        estudios_unicos = {}
        for est in estudios_sugeridos:
            if est['id'] not in estudios_unicos:
                estudios_unicos[est['id']] = est

        resultado = {
            'nombre_paciente': datos_extraidos.get('nombre_paciente', 'DUDA'),
            'edad': datos_extraidos.get('edad'),
            'fecha_receta': datos_extraidos.get('fecha_receta', 'DUDA'),
            'estudios_detectados': estudios_detectados,
            'estudios_sugeridos': list(estudios_unicos.values())  # Estudios del catálogo que coinciden
        }

        return JsonResponse({
            'exito': True,
            'datos': resultado
        })

    except (ImportError, RuntimeError, ValueError, TypeError, OSError, json.JSONDecodeError) as e:
        return JsonResponse({
            'error': f'Error al procesar la receta: {str(e)}',
            'traceback': traceback.format_exc() if settings.DEBUG else None
        }, status=500)


@login_required
@require_http_methods(["POST"])
def escanear_identidad_ia(request):
    """
    RECEPCIÓN INTELIGENTE (OCR de Identidades)
    Jarvis-Vision: Lee INE/Pasaporte y devuelve JSON para autocompletar Paciente.
    """
    try:
        if not settings.GOOGLE_API_KEY:
            return JsonResponse(
                {"error": "GOOGLE_API_KEY no configurada. Configure la variable de entorno GOOGLE_API_KEY."},
                status=500,
            )

        # Control de acceso IA (solo roles operativos, y si el usuario tiene permiso)
        if not getattr(request.user, "puede_usar_ia", False):
            return JsonResponse({"error": "Acceso IA no habilitado para este usuario."}, status=403)

        # Usar cliente centralizado de Gemini Vision (API v1 estable)
        from core.utils.gemini_client import get_gemini_client, get_gemini_model

        try:
            client = get_gemini_client()
            model_name = get_gemini_model('gemini-2.0-flash')
        except (ImportError, RuntimeError, ValueError) as e:
            return JsonResponse(
                {"error": f"Error al inicializar Gemini: {str(e)}"},
                status=500,
            )

        if "imagen" not in request.FILES:
            return JsonResponse({"error": "No se recibió ninguna imagen"}, status=400)

        imagen_file = request.FILES["imagen"]
        imagen_bytes = imagen_file.read()

        prompt_sistema = """Actúa como un asistente de recepción clínica experto. Analiza esta imagen de una identificación oficial (INE o Pasaporte) y extrae los datos en formato JSON estricto.

IMPORTANTE: Responde SOLO con un objeto JSON válido, sin texto adicional, sin markdown, sin explicaciones.

Formato requerido:
{
  "tipo_documento": "INE|PASAPORTE|OTRO|DUDA",
  "nombre_completo": "string o 'DUDA'",
  "fecha_nacimiento": "YYYY-MM-DD o 'DUDA'",
  "sexo": "M|F|DUDA",
  "curp": "string o ''",
  "numero_documento": "string o ''",
  "domicilio": "string o ''"
}

Reglas:
- Si no se puede leer con claridad, usa 'DUDA' para strings críticos (tipo_documento, nombre_completo, fecha_nacimiento, sexo).
- Para curp/numero_documento/domicilio usa '' si no se encuentra.
"""

        try:
            from PIL import Image

            Image.open(io.BytesIO(imagen_bytes)).verify()
        except (ImportError, OSError, ValueError) as e:
            return JsonResponse({"error": f"Error al procesar la imagen: {str(e)}"}, status=400)

        from google.genai import types as genai_types

        mime_type = imagen_file.content_type or "image/jpeg"
        image_part = genai_types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type)
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt_sistema, image_part],
        )
        texto_respuesta = (response.text or "").strip()

        # Limpieza defensiva (a veces viene con fences)
        if texto_respuesta.startswith("```json"):
            texto_respuesta = texto_respuesta[7:]
        if texto_respuesta.startswith("```"):
            texto_respuesta = texto_respuesta[3:]
        if texto_respuesta.endswith("```"):
            texto_respuesta = texto_respuesta[:-3]
        texto_respuesta = texto_respuesta.strip()

        try:
            datos_extraidos = json.loads(texto_respuesta)
        except json.JSONDecodeError:
            json_match = re.search(r"\{[\s\S]*\}", texto_respuesta)
            if not json_match:
                return JsonResponse({"error": f"No se pudo extraer JSON: {texto_respuesta[:200]}"}, status=500)
            datos_extraidos = json.loads(json_match.group())

        resultado = {
            "tipo_documento": (datos_extraidos.get("tipo_documento") or "DUDA"),
            "nombre_completo": (datos_extraidos.get("nombre_completo") or "DUDA"),
            "fecha_nacimiento": (datos_extraidos.get("fecha_nacimiento") or "DUDA"),
            "sexo": (datos_extraidos.get("sexo") or "DUDA"),
            "curp": (datos_extraidos.get("curp") or ""),
            "numero_documento": (datos_extraidos.get("numero_documento") or ""),
            "domicilio": (datos_extraidos.get("domicilio") or ""),
        }

        return JsonResponse({"exito": True, "datos": resultado})

    except (ImportError, RuntimeError, ValueError, TypeError, OSError, json.JSONDecodeError, KeyError) as e:
        return JsonResponse(
            {
                "error": f"Error al procesar la identificación: {str(e)}",
                "traceback": traceback.format_exc() if settings.DEBUG else None,
            },
            status=500,
        )


@login_required
def dashboard_pendientes(request):
    """
    DASHBOARD DE PENDIENTES: Real-time con alertas Jarvis por tiempo excedido.
    Muestra: Cultivos pendientes, folios sin validar, slides pendientes de revisión.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    ahora = timezone.now()

    # 1. ÓRDENES PENDIENTES DE VALIDACIÓN (Resultados listos pero no validados)
    ordenes_pendientes_validacion = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado='RESULTADOS_LISTOS'
    ).select_related('paciente', 'sucursal').order_by('-fecha_creacion')[:50]

    # Calcular tiempo transcurrido y alertas
    ordenes_con_alerta = []
    for orden in ordenes_pendientes_validacion:
        tiempo_transcurrido = ahora - orden.fecha_creacion
        horas_pendiente = tiempo_transcurrido.total_seconds() / 3600

        # Alerta roja si lleva más de 24 horas
        alerta_roja = horas_pendiente > 24
        # Alerta amarilla si lleva más de 12 horas
        alerta_amarilla = horas_pendiente > 12 and not alerta_roja

        ordenes_con_alerta.append({
            'orden': orden,
            'horas_pendiente': round(horas_pendiente, 1),
            'alerta_roja': alerta_roja,
            'alerta_amarilla': alerta_amarilla,
        })

    # 2. CULTIVOS PENDIENTES DE ENTREGA (hoy)
    from datetime import date
    cultivos_pendientes = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado__in=['EN_PROCESO', 'RESULTADOS_LISTOS'],
    ).filter(
        Q(detalles__analito__departamento__icontains='cultivo')
        | Q(detalles__analito__nombre__icontains='cultivo')
        | Q(detalles__descripcion_linea__icontains='cultivo')
    ).distinct().select_related('paciente').order_by('-fecha_creacion')[:20]

    # 3. FOLIOS SIN VALIDAR (detalles con resultado listo pero orden no validada)
    folios_sin_validar = DetalleOrden.objects.filter(
        orden__empresa=empresa,
        estado_procesamiento='RESULTADO_LISTO',
        orden__estado__in=['EN_PROCESO', 'RESULTADOS_LISTOS']
    ).select_related(
        'orden', 'orden__paciente', 'analito', 'perfil_lims', 'paquete_lims'
    ).order_by('-orden__fecha_creacion')[:30]

    # 4. SLIDES PENDIENTES DE REVISIÓN (si existe modelo de slides)

    # Estadísticas resumidas
    stats = {
        'total_ordenes_pendientes': len(ordenes_con_alerta),
        'ordenes_alerta_roja': sum(1 for o in ordenes_con_alerta if o['alerta_roja']),
        'ordenes_alerta_amarilla': sum(1 for o in ordenes_con_alerta if o['alerta_amarilla']),
        'cultivos_pendientes_hoy': cultivos_pendientes.count(),
        'folios_sin_validar': folios_sin_validar.count(),
    }

    return render(request, 'core/laboratorio/dashboard_pendientes.html', {
        'ordenes_con_alerta': ordenes_con_alerta,
        'cultivos_pendientes': cultivos_pendientes,
        'folios_sin_validar': folios_sin_validar,
        'stats': stats,
    })
