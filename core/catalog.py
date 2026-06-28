"""
core/catalog.py
═══════════════════════════════════════════════════════════════════════════════
PRISLAB V6.0 — PILAR 3: HERENCIA CLÍNICA (CATÁLOGO MAESTRO)

Patrón: Catálogo Global (empresa=None) + Override por tenant

FLUJO DE RESOLUCIÓN EN CASCADA:
    1. ¿Tiene la empresa un override específico para este estudio/parámetro?
       → Usar el override (precio, nombre, rango personalizados)
    2. ¿No tiene override?
       → Usar el registro del Catálogo Maestro (empresa=None)
    3. ¿No existe en el Maestro?
       → None

CUÁNDO se usan los Overrides:
    - Un laboratorio cliente cambia el precio de "Glucosa" para sus pacientes.
    - Una clínica renombra "Biometría Hemática" a "BH Completa".
    - Un laboratorio tiene rangos de referencia propios (ISO 15189 personalizado).
    - Un tenant desactiva un estudio que no ofrece en su sucursal.

SIN CAMBIOS EN LAS TABLAS MAESTRAS:
    Los overrides son registros separados. El Catálogo Maestro (creado y
    mantenido por PRISLAB) nunca se toca por un cliente.

MODELOS QUE USA:
    - laboratorio.Estudio       (catálogo maestro con empresa=None en un futuro)
    - laboratorio.Parametro     (ídem)
    - laboratorio.ValorReferencia
    - core.EstudioOverride      (nuevo, sin migración = proxy lógico)

IMPORTANTE: La implementación actual usa modelos existentes y un servicio
de resolución puro, sin nuevas tablas. Los overrides se almacenan como
registros de laboratorio.Estudio con empresa_id != None.
═══════════════════════════════════════════════════════════════════════════════
"""
import logging
from typing import Optional
from decimal import Decimal

logger = logging.getLogger('core.catalog')


# ─── RESOLVEDOR EN CASCADA ───────────────────────────────────────────────────

class CatalogResolver:
    """
    Servicio de resolución en cascada para estudios y parámetros.

    Garantiza que al consultar un estudio, siempre se obtenga la versión
    más específica disponible para la empresa en sesión.

    Uso:
        resolver = CatalogResolver(empresa)

        # Obtener estudio con posible override
        estudio = resolver.get_estudio('Glucosa')
        precio  = resolver.get_precio_estudio(estudio_id)
        rangos  = resolver.get_rangos_referencia(parametro_id, edad, sexo)
    """

    def __init__(self, empresa=None):
        """
        empresa: Instancia de Empresa o None para acceder al Catálogo Maestro.
        Si empresa=None, solo devuelve registros maestros.
        """
        self.empresa = empresa

    # ── Estudios ─────────────────────────────────────────────────────────────

    def get_estudio(self, nombre: str):
        """
        Busca un estudio por nombre, priorizando el override del tenant.

        Orden de búsqueda:
          1. Override del tenant (laboratorio.Estudio con empresa=self.empresa, nombre=nombre)
          2. Catálogo Maestro (laboratorio.Estudio con empresa=None)
          3. Catálogo Core legacy (core.Estudio)
        """
        from core.tenant import tenant_bypass

        with tenant_bypass():
            # Primero: override del tenant
            if self.empresa:
                override = self._buscar_estudio_tenant(nombre)
                if override:
                    override._es_override = True
                    return override

            # Segundo: catálogo maestro de laboratorio
            maestro = self._buscar_estudio_maestro(nombre)
            if maestro:
                maestro._es_override = False
                return maestro

            # Tercero: legacy en core.Estudio
            legacy = self._buscar_estudio_legacy(nombre)
            if legacy:
                legacy._es_override = False
                return legacy

        return None

    def get_estudio_by_id(self, estudio_id: int):
        """Obtiene un estudio por ID con herencia de override."""
        from core.tenant import tenant_bypass
        from laboratorio.models import Estudio as LabEstudio

        with tenant_bypass():
            # Verificar si el tenant tiene override para este estudio
            if self.empresa:
                try:
                    override = LabEstudio.objects.get(
                        empresa=self.empresa,
                        estudio_maestro_id=estudio_id,
                    )
                    override._es_override = True
                    return override
                except LabEstudio.DoesNotExist:
                    pass

            # Retornar el estudio maestro
            try:
                estudio = LabEstudio.objects.get(pk=estudio_id)
                estudio._es_override = False
                return estudio
            except LabEstudio.DoesNotExist:
                return None

    def get_precio_estudio(self, estudio_id: int) -> Optional[Decimal]:
        """
        Retorna el precio efectivo del estudio para el tenant.
        Override del tenant > Precio del catálogo maestro.
        """
        from core.tenant import tenant_bypass
        from laboratorio.models import Estudio as LabEstudio

        with tenant_bypass():
            if self.empresa:
                try:
                    override = LabEstudio.objects.get(
                        empresa=self.empresa,
                        estudio_maestro_id=estudio_id,
                    )
                    precio = getattr(override, 'precio_base', None)
                    if precio is not None:
                        return Decimal(str(precio))
                except LabEstudio.DoesNotExist:
                    pass

            try:
                estudio = LabEstudio.objects.get(pk=estudio_id)
                return Decimal(str(estudio.precio_base)) if estudio.precio_base else None
            except LabEstudio.DoesNotExist:
                return None

    def listar_estudios(self, activos_solo=True):
        """
        Lista de estudios efectivos para el tenant.

        Algoritmo:
          1. Cargar todos los estudios maestros.
          2. Cargar todos los overrides del tenant.
          3. Combinar: el override reemplaza al maestro si tiene el mismo nombre.
          4. Los estudios desactivados por el tenant (activo=False en override) se excluyen.
        """
        from core.tenant import tenant_bypass
        from laboratorio.models import Estudio as LabEstudio

        with tenant_bypass():
            # Estudios maestros (globales, empresa=None o empresa=self.empresa propia)
            qs_maestros = LabEstudio.objects.filter(empresa__isnull=True)
            if activos_solo:
                qs_maestros = qs_maestros.filter(activo=True) if hasattr(LabEstudio, 'activo') else qs_maestros

            maestros = {e.nombre.upper(): e for e in qs_maestros}

            # Overrides del tenant
            if self.empresa:
                overrides = LabEstudio.objects.filter(empresa=self.empresa)
                for ov in overrides:
                    ov._es_override = True
                    maestros[ov.nombre.upper()] = ov  # Sobrescribe el maestro

            return list(maestros.values())

    # ── Rangos de Referencia (ISO 15189 en cascada) ───────────────────────────

    def get_rangos_referencia(self, parametro_id: int, edad_anios: int = 0, sexo: str = 'I'):
        """
        Retorna los rangos de referencia efectivos para un parámetro,
        considerando edad y sexo.

        Cascada:
          1. RangoReferenciaParametro del tenant (override personalizado)
          2. RangoReferenciaParametro global (empresa=None)
          3. ValorReferencia legacy (laboratorio.ValorReferencia)
        """
        from core.tenant import tenant_bypass

        with tenant_bypass():
            # 1. Override del tenant
            if self.empresa:
                rango = self._get_rango_iso(parametro_id, edad_anios, sexo, empresa=self.empresa)
                if rango:
                    rango._es_override = True
                    return rango

            # 2. Catálogo Maestro ISO
            rango = self._get_rango_iso(parametro_id, edad_anios, sexo, empresa=None)
            if rango:
                rango._es_override = False
                return rango

            # 3. Legacy ValorReferencia
            return self._get_rango_legacy(parametro_id, sexo)

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _buscar_estudio_tenant(self, nombre: str):
        try:
            from laboratorio.models import Estudio
        except ImportError:
            return None
        return Estudio.objects.filter(
            empresa=self.empresa,
            nombre__icontains=nombre,
        ).first()

    def _buscar_estudio_maestro(self, nombre: str):
        try:
            from laboratorio.models import Estudio
        except ImportError:
            return None
        return Estudio.objects.filter(
            nombre__icontains=nombre,
        ).order_by('id').first()

    def _buscar_estudio_legacy(self, nombre: str):
        try:
            from core.models import Estudio
        except ImportError:
            return None
        return Estudio.objects.filter(nombre__icontains=nombre).first()

    def _get_rango_iso(self, parametro_id: int, edad: int, sexo: str, empresa=None):
        try:
            from laboratorio.models import RangoReferenciaParametro
            qs = RangoReferenciaParametro.objects.filter(
                parametro_id=parametro_id,
                activo=True,
            )
            if empresa:
                qs = qs.filter(empresa=empresa)
            else:
                qs = qs.filter(empresa__isnull=True)

            # Buscar rango que aplique por edad y sexo
            for rango in qs.order_by('-edad_min_anios'):
                rango_sexo = getattr(rango, 'sexo', 'I')
                if rango_sexo not in ('I', sexo, ''):
                    continue
                min_edad = getattr(rango, 'edad_min_anios', 0) or 0
                max_edad = getattr(rango, 'edad_max_anios', 999) or 999
                if min_edad <= edad <= max_edad:
                    return rango

            # Si no hay rango específico, devolver el general
            return qs.first()
        except ImportError:
            return None

    def _get_rango_legacy(self, parametro_id: int, sexo: str):
        try:
            from laboratorio.models import ValorReferencia, Parametro
        except ImportError:
            return None
        try:
            param = Parametro.objects.get(pk=parametro_id)
        except Parametro.DoesNotExist:
            return None
        return ValorReferencia.objects.filter(
            estudio=param.estudio,
            sexo__in=(sexo, 'I', ''),
        ).first()


# ─── FUNCIÓN HELPER GLOBAL ───────────────────────────────────────────────────

def get_resolver(request=None) -> CatalogResolver:
    """
    Obtiene un CatalogResolver para el tenant en sesión.

    Uso en vistas:
        resolver = get_resolver(request)
        estudio  = resolver.get_estudio('Glucosa')
    """
    if request:
        empresa = getattr(request, 'empresa_actual', None)
    else:
        from core.tenant import get_current_empresa
        empresa = get_current_empresa()

    return CatalogResolver(empresa=empresa)


def resolver_estudio(nombre: str, request=None):
    """Shortcut: busca un estudio con cascada tenant → maestro."""
    return get_resolver(request).get_estudio(nombre)


def resolver_rangos(parametro_id: int, edad: int = 0, sexo: str = 'I', request=None):
    """Shortcut: busca rangos con cascada tenant → maestro → legacy."""
    return get_resolver(request).get_rangos_referencia(parametro_id, edad, sexo)
