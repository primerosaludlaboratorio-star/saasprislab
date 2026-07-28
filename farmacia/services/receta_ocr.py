"""OCR de recetas y conciliación contra el catálogo de Farmacia."""

import unicodedata
from difflib import SequenceMatcher

from django.db.models import Q

from core.models import Producto


def _normalizar(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


def _medicamentos(datos):
    """Normaliza la salida del proveedor de IA sin confiar en dosis como cantidad."""
    resultado = []
    for item in datos.get("medicamentos", []) if isinstance(datos, dict) else []:
        if isinstance(item, str):
            item = {"texto": item}
        if not isinstance(item, dict):
            continue
        texto = (item.get("texto") or item.get("nombre") or item.get("nombre_comercial") or "").strip()
        if texto:
            try:
                cantidad = int(item.get("cantidad") or 1)
            except (TypeError, ValueError):
                cantidad = 1
            resultado.append({
                "texto": texto[:300],
                "cantidad_sugerida": max(1, min(cantidad, 99)),
                "indicaciones": str(item.get("indicaciones") or "")[:500],
                "confianza": float(item.get("confianza") or 0),
            })
    return resultado


def conciliar_medicamentos(empresa, datos):
    """Devuelve candidatos del catálogo para revisión humana, no una selección automática."""
    medicamentos = _medicamentos(datos)
    catalogo = list(Producto.objects_all.filter(empresa=empresa).only(
        "id", "nombre", "sustancia_activa", "marca_laboratorio", "concentracion",
        "forma_farmaceutica", "presentacion", "stock", "precio_publico",
        "requiere_receta", "es_antibiotico", "equivalencias_comerciales",
    ))
    sugerencias = []
    for medicamento in medicamentos:
        consulta = _normalizar(medicamento["texto"])
        candidatos = []
        for producto in catalogo:
            campos = {
                "nombre": _normalizar(producto.nombre),
                "sustancia_activa": _normalizar(producto.sustancia_activa),
                "marca": _normalizar(producto.marca_laboratorio),
                "concentracion": _normalizar(producto.concentracion),
                "equivalencias": _normalizar(producto.equivalencias_comerciales),
            }
            score = 0
            equivalentes = [campos["nombre"], campos["sustancia_activa"]]
            equivalentes.extend(x.strip() for x in campos["equivalencias"].split(',') if x.strip())
            consulta_tokens = {x for x in consulta.split() if len(x) > 2}
            for equivalente in equivalentes:
                if not equivalente:
                    continue
                if consulta == equivalente:
                    score = max(score, 100)
                elif consulta in equivalente:
                    score = max(score, 92)
                elif equivalente in consulta:
                    score = max(score, 88)
                else:
                    tokens_equivalente = {x for x in equivalente.split() if len(x) > 2}
                    overlap = len(consulta_tokens & tokens_equivalente)
                    ratio = SequenceMatcher(None, consulta, equivalente).ratio()
                    if overlap:
                        score = max(score, 70 + min(15, overlap * 5) + int(ratio * 10))
                    elif ratio >= 0.70:
                        score = max(score, 65 + int(ratio * 20))
            if campos["marca"] and campos["marca"] in consulta:
                score += 3
            if score:
                candidatos.append((score, producto))
        candidatos.sort(key=lambda pair: (-pair[0], -int(pair[1].stock or 0), pair[1].nombre))
        sugerencias.append({
            **medicamento,
            "candidatos": [{
                "producto_id": producto.id,
                "nombre": producto.nombre,
                "sustancia_activa": producto.sustancia_activa or "",
                "marca": producto.marca_laboratorio or "",
                "concentracion": producto.concentracion or "",
                "forma_farmaceutica": producto.forma_farmaceutica or "",
                "presentacion": producto.presentacion or "",
                "stock": int(producto.stock or 0),
                "precio_publico": str(producto.precio_publico or 0),
                "requiere_receta": bool(producto.requiere_receta or producto.es_antibiotico),
                "confianza_conciliacion": score,
            } for score, producto in candidatos[:5]],
        })
    return sugerencias
