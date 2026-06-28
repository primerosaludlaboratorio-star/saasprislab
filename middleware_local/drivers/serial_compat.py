"""Compatibilidad liviana para drivers seriales del middleware local."""

try:
    import serial as _serial
    import serial.tools.list_ports  # noqa: F401

    serial = _serial
except ImportError:
    class _MissingSerialModule:
        SerialException = RuntimeError

        class tools:
            class list_ports:
                @staticmethod
                def comports():
                    return []

        @staticmethod
        def Serial(*args, **kwargs):
            raise RuntimeError(
                "pyserial no esta instalado. Instale las dependencias de "
                "middleware_local/requirements.txt para conectar equipos seriales."
            )

    serial = _MissingSerialModule()
