"""Helpers de compatibilidad para detalles de orden LIMS/legacy."""


def get_estudio_legacy(detalle):
    """Devuelve Estudio legacy si existe; en LIMS puro devuelve None."""
    estudio = getattr(detalle, 'estudio', None)
    if estudio:
        return estudio

    analito = getattr(detalle, 'analito', None)
    return getattr(analito, 'estudio', None) if analito else None


def get_detalle_nombre(detalle):
    """Nombre seguro para tickets, CxC y timeline sin depender de detalle.estudio."""
    if getattr(detalle, 'descripcion_linea', None):
        return detalle.descripcion_linea
    if getattr(detalle, 'analito_id', None):
        return detalle.analito.nombre
    if getattr(detalle, 'perfil_lims_id', None):
        return detalle.perfil_lims.nombre
    if getattr(detalle, 'paquete_lims_id', None):
        return detalle.paquete_lims.nombre

    estudio = get_estudio_legacy(detalle)
    return getattr(estudio, 'nombre', '') or 'Estudio'


def get_detalle_abreviatura(detalle):
    if getattr(detalle, 'analito_id', None):
        return detalle.analito.abreviatura or detalle.analito.nombre
    estudio = get_estudio_legacy(detalle)
    return getattr(estudio, 'abreviatura', '') or get_detalle_nombre(detalle)


def get_detalle_codigo(detalle):
    if getattr(detalle, 'analito_id', None):
        return detalle.analito.codigo or detalle.analito.abreviatura or ''
    estudio = get_estudio_legacy(detalle)
    return getattr(estudio, 'codigo', '') or getattr(estudio, 'abreviatura', '') or ''


def get_detalle_unidades(detalle):
    if getattr(detalle, 'analito_id', None):
        return detalle.analito.unidades or ''
    estudio = get_estudio_legacy(detalle)
    return getattr(estudio, 'unidades', '') or getattr(estudio, 'unidad', '') or ''


def get_detalle_muestra(detalle):
    if getattr(detalle, 'analito_id', None):
        return detalle.analito.tipo_muestra or 'S/N'
    estudio = get_estudio_legacy(detalle)
    return getattr(estudio, 'muestra_requerida', '') or 'S/N'


def attach_detalle_display_attrs(detalles):
    """Agrega atributos transient para plantillas raw de impresión."""
    for detalle in detalles:
        estudio = get_estudio_legacy(detalle)
        detalle.display_nombre = get_detalle_nombre(detalle)
        detalle.display_abreviatura = get_detalle_abreviatura(detalle)
        detalle.display_codigo = get_detalle_codigo(detalle)
        detalle.display_unidades = get_detalle_unidades(detalle)
        detalle.display_muestra = get_detalle_muestra(detalle)
        detalle.display_ref_min = getattr(estudio, 'valor_minimo', None) if estudio else None
        detalle.display_ref_max = getattr(estudio, 'valor_maximo', None) if estudio else None
        detalle.display_ref_texto = getattr(estudio, 'texto_referencia', '') if estudio else ''
    return detalles
