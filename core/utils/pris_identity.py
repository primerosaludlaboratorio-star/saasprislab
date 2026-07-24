"""Identidad visible de PRIS por tenant, sin duplicar el motor de IA."""


def nombre_asistente_ia(empresa) -> str:
    """Devuelve el nombre de marca del asistente para una Empresa."""
    configurado = (getattr(empresa, "nombre_asistente_ia", "") or "").strip()
    if configurado:
        return configurado

    nombre_empresa = (getattr(empresa, "nombre", "") or "").casefold()
    if "valle" in nombre_empresa:
        return "LIA"
    return "PRIS"
