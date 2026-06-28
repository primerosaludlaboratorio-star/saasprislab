# 🏥 Agente de Integración LIS - PRISLAB SaaS

Agente local que conecta equipos físicos del laboratorio con el sistema PRISLAB SaaS en la nube.

## 📋 Descripción

Este módulo implementa la "Capa Física" de integración LIS (Laboratory Information System). El agente se ejecuta en una PC Windows del laboratorio y mantiene conexiones activas con múltiples equipos de laboratorio, recibiendo resultados automáticamente y sincronizándolos con el sistema en la nube.

## 🚀 Instalación

### Requisitos

- Python 3.8 o superior
- Windows 10/11 o Linux
- Acceso a puertos seriales (COM) para equipos serial
- Acceso a red TCP/IP para equipos en red

### Instalación de dependencias

```bash
pip install -r requirements.txt
```

## ⚙️ Configuración

1. **Editar `config.yaml`:**

   - Configurar `sucursal_id`: ID de la sucursal en PRISLAB
   - Configurar `cloud_url`: URL del servidor PRISLAB SaaS
   - Configurar `cloud_token`: Token de autenticación (obtener del panel admin)
   - Configurar equipos: Agregar cada equipo con su configuración específica

2. **Ejemplo de configuración:**

```yaml
sucursal_id: 1
cloud_url: "http://localhost:8000"
cloud_token: "tu_token_aqui"

equipos:
  - nombre: "Norma Icon 5"
    driver: "norma_icon"
    tipo: "tcp"
    ip: "192.168.1.50"
    puerto: 5000
```

## 🔌 Equipos Soportados

### 1. Norma Icon 5
- **Protocolo:** TCP/IP con HL7/XML
- **Driver:** `norma_icon`
- **Configuración:** IP y puerto TCP/IP

### 2. InCCA Química
- **Protocolo:** Serial con ASTM 1394
- **Driver:** `incca`
- **Configuración:** Puerto COM, baudrate, paridad

### 3. Mission U120
- **Protocolo:** Serial con texto simple
- **Driver:** `mission_u120`
- **Configuración:** Puerto COM, baudrate, delimitador

### 4. Wondfo Finecare (Genérico)
- **Protocolo:** Serial o TCP/IP unidireccional
- **Driver:** `wondfo_finecare`
- **Configuración:** Serial (COM) o TCP/IP (IP:Puerto)

## 🎯 Uso

### Ejecutar el agente

```bash
python agente_laboratorio.py
```

### Con archivo de configuración personalizado

```bash
python agente_laboratorio.py --config mi_config.yaml
```

### Ejecutar en segundo plano (Windows)

```bash
pythonw agente_laboratorio.py
```

## 📡 Funcionamiento

1. **Inicio:** El agente lee `config.yaml` y crea drivers para cada equipo configurado.

2. **Conexión:** Cada driver establece su conexión (serial o TCP/IP) según la configuración.

3. **Recepción:** Los drivers escuchan continuamente resultados de los equipos.

4. **Procesamiento:** Los resultados se parsean según el formato del equipo.

5. **Sincronización:** Los resultados se envían automáticamente a la nube mediante POST a `/api/laboratorio/resultados/recepcion_equipo/`.

6. **Logs:** Todo se registra en `agente_laboratorio.log` y en la consola.

## 🔒 Seguridad

- El agente usa **Token de autenticación** para comunicarse con la nube
- El token debe obtenerse desde el panel de administración de PRISLAB
- Los resultados se envían mediante HTTPS en producción

## 📊 Logs

Los logs se guardan en:
- **Archivo:** `agente_laboratorio.log`
- **Consola:** Salida estándar en tiempo real

Niveles de log:
- `INFO`: Operaciones normales
- `WARNING`: Advertencias (ej: checksum inválido)
- `ERROR`: Errores críticos

## 🐛 Troubleshooting

### Puerto COM no encontrado
- Verificar que el puerto existe en Administrador de dispositivos
- Asegurarse de que el puerto no esté en uso por otra aplicación

### Conexión TCP/IP fallida
- Verificar IP y puerto del equipo
- Verificar conectividad de red
- Verificar firewall

### Token inválido
- Verificar que el token es correcto en `config.yaml`
- Obtener nuevo token desde el panel admin

### Resultados no aparecen en la nube
- Verificar logs en `agente_laboratorio.log`
- Verificar conectividad con el servidor (`cloud_url`)
- Verificar que el endpoint existe en el servidor

## 📝 Estructura del Proyecto

```
middleware_local/
├── __init__.py
├── agente_laboratorio.py      # Agente principal
├── config.yaml                # Configuración
├── requirements.txt           # Dependencias
├── README.md                  # Este archivo
└── drivers/
    ├── __init__.py
    ├── norma_icon.py          # Driver Norma Icon (TCP/IP HL7/XML)
    ├── incca_chem.py          # Driver InCCA (Serial ASTM 1394)
    ├── mission_u120.py        # Driver Mission U120 (Serial texto)
    └── wondfo_finecare.py     # Driver genérico (Serial/TCP/IP)
```

## 🎓 Próximos Pasos

1. **Descargar** el script en la PC del laboratorio
2. **Instalar** dependencias con `pip install -r requirements.txt`
3. **Configurar** `config.yaml` con los datos del laboratorio
4. **Conectar** los cables (serial o red) a los equipos
5. **Ejecutar** el agente
6. **Verificar** que los resultados aparecen en "Lista de Trabajo" del sistema

## 📞 Soporte

Para soporte técnico, consultar la documentación de PRISLAB SaaS o contactar al equipo de desarrollo.

---

**PRISLAB SaaS - Integración LIS v1.0.0**
