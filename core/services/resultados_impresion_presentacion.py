"""
Construcción de `detalles_procesados` para HTML de resultados (portal paciente e impresión).
Unifica la lógica que antes vivía solo en `imprimir_resultados_pdf` (perfiles LIMS + flags).
"""
from datetime import date
from types import SimpleNamespace

from django.db.models import Q

from core.models import ResultadoParametro
from core.utils.detalle_orden import attach_detalle_display_attrs
from lims.models import Analito, ValorReferenciaAnalito


def _categoria_grupo_detalle(detalle) -> str:
    d = detalle
    return (
        (d.perfil_lims.nombre if d.perfil_lims_id else None)
        or (d.paquete_lims.nombre if d.paquete_lims_id else None)
        or (d.analito.nombre if d.analito_id else None)
        or (d.descripcion_linea or "").strip()
        or "Resultados"
    )


def _rango_referencia_para_analito(analito, paciente):
    """
    Resuelve el rango de referencia más adecuado para un analito y paciente.
    Prioriza coincidencia exacta por sexo y edad; cae a indiferente si no hay match.
    """
    if not analito:
        return None

    sexo = (getattr(paciente, "sexo", None) or "I").upper()
    edad_anios = getattr(paciente, "edad", None)
    dias_vida = None
    fecha_nacimiento = getattr(paciente, "fecha_nacimiento", None)
    if fecha_nacimiento:
        try:
            dias_vida = max((date.today() - fecha_nacimiento).days, 0)
        except Exception:
            dias_vida = None

    rangos = list(ValorReferenciaAnalito.objects.filter(analito=analito).order_by("edad_minima", "sexo"))
    if not rangos:
        return None

    def _aplica(r):
        if r.sexo not in (sexo, "I"):
            return False
        if r.unidad_edad == "ANOS":
            if edad_anios is None:
                return False
            return r.edad_minima <= edad_anios <= r.edad_maxima
        if r.unidad_edad == "DIAS":
            if dias_vida is None:
                return False
            return r.edad_minima <= dias_vida <= r.edad_maxima
        return True

    seleccionado = next((r for r in rangos if _aplica(r)), None)
    if seleccionado is None:
        seleccionado = next((r for r in rangos if r.sexo in (sexo, "I")), rangos[0])

    ref_min = seleccionado.ref_minimo
    ref_max = seleccionado.ref_maximo
    ref_texto = (seleccionado.texto_referencia or "").strip()
    if not ref_texto and ref_min is not None and ref_max is not None:
        ref_texto = f"{float(ref_min):.2f} - {float(ref_max):.2f}"

    return {
        "ref_min": float(ref_min) if ref_min is not None else None,
        "ref_max": float(ref_max) if ref_max is not None else None,
        "ref_texto": ref_texto,
        "critico_min": float(seleccionado.valor_critico_bajo) if seleccionado.valor_critico_bajo is not None else None,
        "critico_max": float(seleccionado.valor_critico_alto) if seleccionado.valor_critico_alto is not None else None,
        "panico_fuera_ref": bool(seleccionado.es_critico_si_fuera_de_rango),
    }


def construir_detalles_procesados_orden(orden):
    """
    Devuelve (detalles_procesados, ultimo_validador).
    Cada ítem: detalle, resultado_parseado, categoria_grupo.
    """
    detalles = orden.detalles.select_related(
        "analito", "perfil_lims", "paquete_lims", "validado_por"
    ).prefetch_related("analito__rangos").all()
    attach_detalle_display_attrs(list(detalles))

    ultimo_validador = None
    if detalles.exists():
        detalles_con_validacion = detalles.filter(validado_por__isnull=False).order_by(
            "-fecha_validacion"
        )
        if detalles_con_validacion.exists():
            ultimo_validador = detalles_con_validacion.first().validado_por

    detalles_procesados = []
    for detalle in detalles:
        resultado_parseado = None
        if detalle.resultado and (detalle.perfil_lims_id or detalle.paquete_lims_id):
            lineas = detalle.resultado.split("\n")
            resultado_parseado = []
            for linea in lineas:
                linea = linea.strip()
                if linea and ":" in linea:
                    partes = linea.split(":")
                    if len(partes) >= 2:
                        descripcion = partes[0].strip()
                        resto = ":".join(partes[1:]).strip()
                        valores = resto.split()
                        valor = valores[0] if valores else ""
                        unidades = " ".join(valores[1:]) if len(valores) > 1 else ""
                        an = (
                            Analito.objects.filter(
                                Q(nombre__iexact=descripcion) | Q(codigo__iexact=descripcion)
                            )
                            .filter(activo=True)
                            .first()
                        )
                        rango = _rango_referencia_para_analito(an, orden.paciente) if an else None
                        resultado_parseado.append(
                            {
                                "descripcion": descripcion,
                                "valor": valor,
                                "unidades": unidades,
                                "analito_id": an.id if an else None,
                                **(rango or {}),
                            }
                        )

        if detalle.analito_id and detalle.analito:
            rango_detalle = _rango_referencia_para_analito(detalle.analito, orden.paciente)
            if rango_detalle:
                detalle.estudio = SimpleNamespace(
                    nombre=detalle.analito.nombre,
                    unidades=detalle.analito.unidades or "",
                    valor_minimo=rango_detalle.get("ref_min"),
                    valor_maximo=rango_detalle.get("ref_max"),
                    texto_referencia=rango_detalle.get("ref_texto", ""),
                )
                detalle.display_ref_min = rango_detalle.get("ref_min")
                detalle.display_ref_max = rango_detalle.get("ref_max")
                detalle.display_ref_texto = rango_detalle.get("ref_texto", "")

        detalles_procesados.append(
            {"detalle": detalle, "resultado_parseado": resultado_parseado}
        )

    for item in detalles_procesados:
        if item.get("resultado_parseado"):
            for param in item["resultado_parseado"]:
                try:
                    val_num = float(str(param.get("valor", "")).replace(",", "."))
                    ref_min = param.get("ref_min")
                    ref_max = param.get("ref_max")
                    critico_min = param.get("critico_min")
                    critico_max = param.get("critico_max")

                    es_anormal = False
                    es_critico = False
                    direccion = ""
                    if critico_min is not None and val_num < float(critico_min):
                        es_critico = True
                        direccion = "L"
                    elif critico_max is not None and val_num > float(critico_max):
                        es_critico = True
                        direccion = "H"
                    elif ref_min is not None and val_num < float(ref_min):
                        es_anormal = True
                        direccion = "L"
                    elif ref_max is not None and val_num > float(ref_max):
                        es_anormal = True
                        direccion = "H"
                    param["es_anormal"] = es_anormal
                    param["es_critico"] = es_critico
                    param["direccion"] = direccion

                    try:
                        aid = param.get("analito_id")
                        if aid and orden.paciente_id:
                            hist_qs = (
                                ResultadoParametro.objects.filter(
                                    orden__paciente_id=orden.paciente_id,
                                    analito_id=aid,
                                )
                                .exclude(orden=orden)
                                .exclude(valor="")
                                .order_by("-orden__fecha_creacion")[:3]
                            )
                            param["historial"] = [
                                {
                                    "valor": h.valor,
                                    "fecha": h.orden.fecha_creacion.strftime("%d/%m/%Y"),
                                }
                                for h in hist_qs
                            ]
                    except Exception:
                        param["historial"] = []
                except (ValueError, TypeError):
                    param.setdefault("es_anormal", False)
                    param.setdefault("es_critico", False)
                    param.setdefault("historial", [])

    for item in detalles_procesados:
        item["categoria_grupo"] = _categoria_grupo_detalle(item["detalle"])

    return detalles_procesados, ultimo_validador
