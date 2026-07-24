"""Conciliación de líneas OCR contra el catálogo de Farmacia."""

from farmacia.services.receta_ocr import _normalizar
from core.models import Producto


def conciliar_compra(empresa, datos):
    lineas = datos.get("productos") if isinstance(datos, dict) else []
    catalogo = list(Producto.objects_all.filter(empresa=empresa).only(
        "id", "nombre", "sustancia_activa", "marca_laboratorio", "concentracion",
        "forma_farmaceutica", "presentacion", "precio_compra",
    ))
    resultado = []
    for linea in lineas if isinstance(lineas, list) else []:
        if isinstance(linea, str):
            linea = {"texto": linea}
        texto = str((linea or {}).get("texto") or (linea or {}).get("nombre") or "").strip()
        if not texto:
            continue
        consulta = _normalizar(texto)
        candidatos = []
        for producto in catalogo:
            campos = [_normalizar(producto.nombre), _normalizar(producto.sustancia_activa), _normalizar(producto.marca_laboratorio)]
            score = 100 if consulta in campos[:2] else (90 if consulta in campos[0] else (85 if consulta in campos[1] else 0))
            if score:
                candidatos.append((score, producto))
        candidatos.sort(key=lambda pair: (-pair[0], pair[1].nombre))
        try:
            cantidad = max(1, int((linea or {}).get("cantidad") or 1))
        except (TypeError, ValueError):
            cantidad = 1
        resultado.append({
            "texto": texto[:300], "cantidad": cantidad,
            "costo_unitario": str((linea or {}).get("costo_unitario") or "0"),
            "numero_lote": str((linea or {}).get("numero_lote") or "").strip().upper(),
            "fecha_caducidad": (linea or {}).get("fecha_caducidad") or "",
            "marca": str((linea or {}).get("marca") or "").strip(),
            "candidatos": [{
                "producto_id": p.id, "nombre": p.nombre,
                "sustancia_activa": p.sustancia_activa or "",
                "marca": p.marca_laboratorio or "", "concentracion": p.concentracion or "",
                "presentacion": p.presentacion or "", "confianza_conciliacion": score,
            } for score, p in candidatos[:5]],
        })
    return resultado
