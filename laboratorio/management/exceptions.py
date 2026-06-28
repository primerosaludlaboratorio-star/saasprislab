"""
Excepciones estandar para management commands
"""

class CommandError(Exception):
    """Base para errores de comandos de administracion"""
    pass

class DataFormatError(CommandError):
    """Error en formato de datos (CSV, JSON, etc.)"""
    pass

class ValidationError(CommandError):
    """Error de validacion de datos"""
    pass

class MigrationError(CommandError):
    """Error durante migracion de datos"""
    pass

class SimulationError(CommandError):
    """Error durante simulacion"""
    pass
