"""Conciliación segura de líneas OCR contra el catálogo de laboratorio."""

import unicodedata

from inventario.models import CatalogoReactivoLab


def _normalizar(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


def conciliar_compra_laboratorio(empresa, datos):
    lineas = datos.get("productos") if isinstance(datos, dict) else []
    # The catalog is a regular model; keep the explicit tenant filter here so
    # OCR suggestions never cross company boundaries.
    catalogo = list(CatalogoReactivoLab.objects.filter(empresa=empresa, activo=True).only(
        "id", "codigo_interno", "nombre", "marca", "fabricante", "unidad_medida", "tipo",
    ))
    resultado = []
    for linea in lineas if isinstance(lineas, list) else []:
        if isinstance(linea, str):
            linea = {"texto": linea}
        linea = linea or {}
        texto = str(linea.get("texto") or linea.get("nombre") or "").strip()
        if not texto:
            continue
        consulta = _normalizar(texto)
        candidatos = []
        for articulo in catalogo:
            campos = [_normalizar(articulo.codigo_interno), _normalizar(articulo.nombre),
                      _normalizar(articulo.marca), _normalizar(articulo.fabricante)]
            score = 100 if consulta in campos[:2] else (90 if any(consulta in c for c in campos if c) else 0)
            if score:
                candidatos.append((score, articulo))
        candidatos.sort(key=lambda pair: (-pair[0], pair[1].nombre))
        resultado.append({
            "texto": texto[:300], "cantidad": str(linea.get("cantidad") or "1"),
            "costo_unitario": str(linea.get("costo_unitario") or "0"),
            "numero_lote": str(linea.get("numero_lote") or "").strip().upper(),
            "fecha_caducidad": linea.get("fecha_caducidad") or "",
            "marca": str(linea.get("marca") or "").strip(),
            "candidatos": [{
                "reactivo_id": articulo.id, "codigo": articulo.codigo_interno,
                "nombre": articulo.nombre, "marca": articulo.marca or "",
                "fabricante": articulo.fabricante or "", "tipo": articulo.tipo,
                "unidad": articulo.unidad_medida, "confianza_conciliacion": score,
            } for score, articulo in candidatos[:5]],
        })
    return resultado
