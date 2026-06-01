"""
Construcción de `detalles_procesados` para HTML de resultados (portal paciente e impresión).
Unifica la lógica que antes vivía solo en `imprimir_resultados_pdf` (perfiles LIMS + flags).
"""
from django.db.models import Q

from core.models import ResultadoParametro
from lims.models import Analito


def _categoria_grupo_detalle(detalle) -> str:
    d = detalle
    return (
        (d.perfil_lims.nombre if d.perfil_lims_id else None)
        or (d.paquete_lims.nombre if d.paquete_lims_id else None)
        or (d.analito.nombre if d.analito_id else None)
        or (d.descripcion_linea or "").strip()
        or "Resultados"
    )


def construir_detalles_procesados_orden(orden):
    """
    Devuelve (detalles_procesados, ultimo_validador).
    Cada ítem: detalle, resultado_parseado, categoria_grupo.
    """
    detalles = orden.detalles.select_related(
        "analito", "perfil_lims", "paquete_lims", "validado_por"
    ).all()

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
                        resultado_parseado.append(
                            {
                                "descripcion": descripcion,
                                "valor": valor,
                                "unidades": unidades,
                                "analito_id": an.id if an else None,
                            }
                        )

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
