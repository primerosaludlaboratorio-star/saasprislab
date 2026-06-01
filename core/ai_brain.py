"""
Cerebro Dual PRIS/LIA (IA Avanzada)

- Prompt dinámico por empresa:
  - Prislab -> PRIS (Ejecutivo, Rojo, Institucional)
  - Laboratorio del Valle -> LIA (Cálido, Azul, Familiar)
- Function calling con permisos:
  - validar_folios(rango) -> permitido
  - consultar_ventas(fecha) -> SOLO Dirección (superadmin)
  - buscar_rh(empleado) -> SOLO Dirección (superadmin)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from django.utils import timezone

from django.conf import settings

from core.models import Venta, Empleado, Bitacora39A
from core.models import Paciente


def iniciar_simulacion(usuario, escenario: str) -> Dict[str, Any]:
    """
    Modo Roleplay (Entrenamiento): la IA devuelve un guion de simulación y criterios de evaluación.
    """
    escenario = (escenario or "").strip()
    if not escenario:
        return {
            "ok": False,
            "mensaje": "Indica un escenario. Ejemplo: 'Paciente molesto por precio' o 'Paciente con miedo a la aguja'.",
        }

    # No requiere permisos especiales: es capacitación.
    return {
        "ok": True,
        "escenario": escenario,
        "instrucciones": [
            "Actúa como el personaje descrito. Responde como un humano real, con emoción pero sin agresiones.",
            "Evalúa al usuario al final con 3 puntos: empatía, claridad clínica, cierre ético.",
            "Nunca prometas curas ni inventes resultados. Si faltan datos, pide aclaración.",
        ],
        "rubrica": {
            "empatia": "0-10",
            "claridad_clinica": "0-10",
            "cierre_etico": "0-10",
        },
    }


def generar_campaña(usuario, segmento: str) -> Dict[str, Any]:
    """
    Genera campaña ética (sin invasión) y un cupón QR con branding.
    Nota: NO expone utilidades/finanzas; solo mensajes educativos + cupón.
    """
    segmento = (segmento or "").strip()
    if not segmento:
        return {"ok": False, "mensaje": "Indica un segmento. Ejemplo: 'diabeticos_inactivos'."}

    empresa = getattr(usuario, "empresa", None)
    qs = Paciente.objects.all()
    if empresa:
        qs = qs.filter(empresa=empresa)
    pacientes = list(qs.order_by("-id")[:5])

    # Mensaje educativo (plantilla base)
    mensaje = (
        "Hola, soy el equipo de {empresa}. Te compartimos un recordatorio de salud: "
        "un control periódico ayuda a detectar a tiempo cambios importantes. "
        "Si deseas, podemos orientarte sobre estudios recomendados según tu caso."
    ).format(empresa=getattr(empresa, "nombre", "PRISLAB"))

    # Cupón QR simple (sin depender de pagos): se guarda como PNG en media/cupones/
    try:
        import os
        from django.conf import settings
        from django.utils import timezone
        import qrcode
        from PIL import Image, ImageDraw, ImageFont

        codigo = f"CUPON-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        payload = f"PRISVALLE|{getattr(empresa, 'id', 'NA')}|{codigo}|{segmento}"

        qr = qrcode.QRCode(version=2, box_size=10, border=2)
        qr.add_data(payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # Branding básico (sin depender de fonts externas)
        canvas = Image.new("RGB", (qr_img.size[0], qr_img.size[1] + 90), "white")
        canvas.paste(qr_img, (0, 70))
        draw = ImageDraw.Draw(canvas)
        titulo = getattr(empresa, "nombre", "PRISLAB")
        draw.text((12, 10), f"{titulo} · Cupón", fill=(0, 0, 0))
        draw.text((12, 35), f"Código: {codigo}", fill=(30, 30, 30))

        out_dir = os.path.join(getattr(settings, "MEDIA_ROOT", "media"), "cupones")
        os.makedirs(out_dir, exist_ok=True)
        filename = f"{codigo}.png"
        out_path = os.path.join(out_dir, filename)
        canvas.save(out_path, format="PNG")

        cupon_rel = os.path.join("cupones", filename).replace("\\", "/")
    except Exception as e:
        codigo = None
        cupon_rel = None
        return {
            "ok": False,
            "mensaje": f"No se pudo generar el cupón QR: {str(e)}",
        }

    return {
        "ok": True,
        "segmento": segmento,
        "mensaje_whatsapp": mensaje,
        "pacientes_muestra": [{"id": p.id, "nombre": p.nombre_completo} for p in pacientes],
        "cupon_codigo": codigo,
        "cupon_qr_media_path": cupon_rel,
    }


def _empresa_nombre(usuario) -> str:
    try:
        return (usuario.empresa.nombre or "").strip()
    except Exception:
        return ""


def build_system_prompt(usuario) -> str:
    empresa = _empresa_nombre(usuario).lower()
    if empresa == "laboratorio del valle":
        nombre_ia = "LIA"
        tono = "Cálido, Azul, Familiar"
    else:
        nombre_ia = "PRIS"
        tono = "Ejecutivo, Rojo, Institucional"

    return (
        f"Eres {nombre_ia}. Tu tono es {tono}. "
        "Eres amable pero estricta con protocolos (FEFO, Triple Llave). "
        "Responde claro, directo y con pasos operativos. "
        "Si te piden datos financieros o de RH y el usuario no es Dirección, deniega amablemente."
    )


def superadmin_required(usuario) -> bool:
    # Política estricta: SOLO superuser
    return bool(getattr(usuario, "is_superuser", False))


def _deny_financial() -> str:
    return "Lo siento, ese dato es exclusivo de Dirección."


def validar_folios(usuario, rango: str) -> Dict[str, Any]:
    """
    Valida folios (simple): busca ventas cuyo folio contenga el rango/patrón.
    """
    rango = (rango or "").strip()
    if not rango:
        return {"ok": False, "mensaje": "Rango vacío. Ejemplo: POS-0001 a POS-0100 o POS-."}

    empresa = getattr(usuario, "empresa", None)
    qs = Venta.objects.all()
    if empresa:
        qs = qs.filter(empresa=empresa)
    qs = qs.filter(folio_operacion__icontains=rango).order_by("-fecha")[:50]
    return {
        "ok": True,
        "coincidencias": qs.count(),
        "muestra": [
            {"folio": v.folio_operacion, "fecha": v.fecha.isoformat() if v.fecha else None, "total": float(v.total)}
            for v in qs
        ],
    }


def consultar_ventas(usuario, fecha: str) -> Dict[str, Any]:
    """
    Consulta ventas por fecha (SOLO Dirección).
    """
    if not superadmin_required(usuario):
        return {"ok": False, "mensaje": _deny_financial()}

    empresa = getattr(usuario, "empresa", None)
    try:
        d = datetime.strptime((fecha or "").strip(), "%Y-%m-%d").date()
    except Exception:
        d = timezone.now().date()

    inicio = timezone.make_aware(datetime.combine(d, datetime.min.time()))
    fin = timezone.make_aware(datetime.combine(d, datetime.max.time()))

    qs = Venta.objects.filter(fecha__range=(inicio, fin))
    if empresa:
        qs = qs.filter(empresa=empresa)

    total = sum([v.total for v in qs])
    return {
        "ok": True,
        "fecha": d.isoformat(),
        "ventas": qs.count(),
        "total": float(total),
    }


def buscar_rh(usuario, empleado: str) -> Dict[str, Any]:
    """
    Busca RH (SOLO Dirección): empleado + últimas evaluaciones 39-A.
    """
    if not superadmin_required(usuario):
        return {"ok": False, "mensaje": _deny_financial()}

    empresa = getattr(usuario, "empresa", None)
    q = (empleado or "").strip()
    if not q:
        return {"ok": False, "mensaje": "Indica el nombre del empleado."}

    qs = Empleado.objects.all()
    if empresa:
        qs = qs.filter(empresa=empresa)
    emp = qs.filter(nombre__icontains=q).first()
    if not emp:
        return {"ok": False, "mensaje": "No encontré ese empleado."}

    evals = Bitacora39A.objects.filter(empleado=emp).order_by("-fecha_inicio_semana")[:5]
    return {
        "ok": True,
        "empleado": {"id": emp.id, "nombre": emp.nombre, "puesto": getattr(emp, "puesto", "")},
        "evaluaciones": [
            {
                "semana": e.fecha_inicio_semana.isoformat() if e.fecha_inicio_semana else None,
                "calificacion": float(getattr(e, "calificacion_general", 0) or 0),
            }
            for e in evals
        ],
    }


def _tools_schema() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "validar_folios",
                "description": "Validar folios/operaciones por un patrón o rango simple.",
                "parameters": {
                    "type": "object",
                    "properties": {"rango": {"type": "string"}},
                    "required": ["rango"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "consultar_ventas",
                "description": "Consultar ventas por fecha (YYYY-MM-DD). SOLO Dirección.",
                "parameters": {
                    "type": "object",
                    "properties": {"fecha": {"type": "string"}},
                    "required": ["fecha"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "buscar_rh",
                "description": "Buscar información de RH (empleado + últimas evaluaciones). SOLO Dirección.",
                "parameters": {
                    "type": "object",
                    "properties": {"empleado": {"type": "string"}},
                    "required": ["empleado"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "iniciar_simulacion",
                "description": "Modo roleplay de capacitación. Devuelve guion e indicadores de evaluación.",
                "parameters": {
                    "type": "object",
                    "properties": {"escenario": {"type": "string"}},
                    "required": ["escenario"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "generar_campaña",
                "description": "Genera campaña ética (mensaje educativo) y cupón QR con branding (sin finanzas).",
                "parameters": {
                    "type": "object",
                    "properties": {"segmento": {"type": "string"}},
                    "required": ["segmento"],
                },
            },
        },
    ]


def responder(usuario, pregunta: str) -> Dict[str, Any]:
    """
    Respuesta IA con Google Gemini. 
    Nota: Gemini no tiene function calling nativo como OpenAI, así que usamos prompt engineering.
    Retorna {respuesta, tool_calls?}.
    """
    # Usar cliente centralizado de Gemini (google.genai SDK)
    try:
        from core.utils.gemini_client import get_gemini_client
        _gemini_client = get_gemini_client()
    except Exception as e:
        return {
            "ok": False,
            "mensaje": f"Error de conexión con IA: {str(e)}"
        }
    
    system_prompt = build_system_prompt(usuario)
    
    # Construir prompt con instrucciones de herramientas disponibles
    herramientas_texto = """
Herramientas disponibles (responde SOLO si el usuario las solicita explícitamente):
- validar_folios(rango): Validar folios/operaciones por patrón
- consultar_ventas(fecha YYYY-MM-DD): Consultar ventas por fecha (SOLO Dirección)
- buscar_rh(empleado): Buscar información de RH (SOLO Dirección)
- iniciar_simulacion(escenario): Modo roleplay de capacitación
- generar_campaña(segmento): Generar campaña ética y cupón QR

Si el usuario solicita usar una herramienta, indica claramente qué herramienta y parámetros necesitas.
"""
    
    prompt_completo = f"""{system_prompt}

{herramientas_texto}

Pregunta del usuario: {pregunta or ""}

Responde como asistente experto. Si necesitas usar una herramienta, indícalo claramente."""
    
    try:
        import logging
        logger = logging.getLogger('core')
        logger.info(f"PRIS: Procesando pregunta: {pregunta[:50]}...")
        
        logger.info("PRIS: Generando respuesta con Gemini...")
        response = _gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt_completo,
            config={'temperature': 0.7, 'max_output_tokens': 500}
        )
        
        logger.info("PRIS: Respuesta generada exitosamente")
        respuesta = response.text if response and response.text else "No se pudo generar una respuesta."
        
        # Detectar si la respuesta menciona herramientas (análisis simple)
        tool_outputs = []
        respuesta_lower = respuesta.lower()
        
        # Si menciona alguna herramienta, intentar ejecutarla
        if "validar_folios" in respuesta_lower or "folio" in respuesta_lower:
            # Intentar extraer rango del contexto
            import re
            rango_match = re.search(r'folio[:\s]+([A-Z0-9-]+)', respuesta_lower)
            if rango_match:
                rango = rango_match.group(1)
                out = validar_folios(usuario, rango)
                tool_outputs.append({"tool": "validar_folios", "output": out})
        
        # Retornar formato correcto que espera api_ia_chat
        return {
            "ok": True,
            "respuesta": respuesta, 
            "tools": tool_outputs if tool_outputs else None
        }
        
    except Exception as e:
        import traceback
        return {
            "ok": False,
            "mensaje": f"Error al procesar respuesta IA: {str(e)}",
            "debug": traceback.format_exc()
        }
