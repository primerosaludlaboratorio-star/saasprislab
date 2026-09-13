"""Filtros de presentación para textos clínicos de PRISLAB."""

import re

from django import template


register = template.Library()

# Abreviaturas que deben conservar su forma clínica aunque el catálogo venga
# importado en mayúsculas o con una capitalización inconsistente.
_ABREVIATURAS = {
    "ALT", "AST", "BH", "BUN", "CK", "CK-MB", "CO2", "DHL", "EGO",
    "FR", "GLU", "HCG", "HDL", "IGG", "IGM", "INR", "LDL", "PCR", "PH", "PSA",
    "QSC", "RPR", "T3", "T4", "TSH", "TGO", "TGP", "TP", "TTP", "VDRL",
    "VLDL", "VSG",
}
_ABREVIATURAS_CANONICAS = {item.casefold(): item for item in _ABREVIATURAS}

# Correcciones de ortografía clínica que no pueden resolverse con title/sentence
# case sin arriesgar nombres propios, unidades o abreviaturas.
_CORRECCIONES_CLINICAS = {
    "proteinas": "proteínas",
    "proteina": "proteína",
    "urobilinogeno": "urobilinógeno",
    "urobilinogenos": "urobilinógenos",
    "eritrocitos": "eritrocitos",
    "leucocitos": "leucocitos",
    "hemoglobina": "hemoglobina",
    "albumina": "albúmina",
    "fosforo": "fósforo",
    "magnesio": "magnesio",
    "acido urico": "ácido úrico",
    "ph": "pH",
    "ph.": "pH",
}


def _capitalizar_frase(texto):
    """Devuelve una frase en sentence case sin modificar abreviaturas clínicas."""
    texto = re.sub(r"\s+", " ", str(texto or "").strip())
    if not texto:
        return ""
    # Las expresiones de varias palabras deben corregirse antes de separar
    # tokens; así se conserva la acentuación completa de nombres clínicos.
    for origen, destino in _CORRECCIONES_CLINICAS.items():
        if " " in origen:
            texto = re.sub(
                rf"(?<!\w){re.escape(origen)}(?!\w)",
                destino,
                texto,
                flags=re.IGNORECASE,
            )
    if texto.casefold() in {"ph", "ph."}:
        return "pH"
    if texto.casefold() in _ABREVIATURAS_CANONICAS:
        return _ABREVIATURAS_CANONICAS[texto.casefold()]

    tokens = re.split(r"(\s+|[-/()])", texto)
    resultado = []
    for token in tokens:
        clave = token.casefold()
        if clave in _CORRECCIONES_CLINICAS:
            resultado.append(_CORRECCIONES_CLINICAS[clave])
            continue
        if clave in _ABREVIATURAS_CANONICAS:
            resultado.append(_ABREVIATURAS_CANONICAS[clave])
        elif token and token[0].isalpha():
            resultado.append(token.casefold())
        else:
            resultado.append(token)

    frase = "".join(resultado)
    for indice, caracter in enumerate(frase):
        if caracter.isalpha():
            return frase[:indice] + caracter.upper() + frase[indice + 1:]
    return frase


@register.filter(name="nombre_lims")
def nombre_lims(value):
    """Presenta nombres de analitos, perfiles y paquetes con ortografía uniforme."""
    return _capitalizar_frase(value)
