"""
Paquete de signals de core.

Importa los 5 submódulos para que `apps.py` (`import core.signals`)
registre todos los receivers automáticamente.
"""
from . import folios
from . import auditoria
from . import resultados
from . import devoluciones
from . import ventas
