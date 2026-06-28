# Procedimiento de Verificación Humana UI

Fecha: 2026-06-23  
Alcance: PRISLAB SaaS en producción o staging, con ejecución manual en navegador por personal humano.

## Propósito

Este documento define cómo auditar la interfaz y los flujos reales de PRISLAB sin depender de extensiones de IA, asistentes de navegador o revisión automática.

La idea es simple: si la herramienta de IA falla, la verificación humana sigue.

## Regla principal

- El auditor humano abre la página, usa el sistema como usuario real y registra evidencia.
- No se asume que una IA haya validado la UI.
- No se cierra un flujo hasta verlo completo en navegador.
- Si un flujo falla, se documenta con hora, URL, acción y captura.

## Requisitos mínimos antes de auditar

1. URL de producción o staging.
2. Usuario de prueba por rol.
3. Contraseña de prueba vigente.
4. Navegador con sesión limpia o sesión conocida.
5. Acceso a capturas de pantalla.
6. Si es posible, consola del navegador abierta para registrar errores.

## Datos que deben existir

- Usuario de laboratorio.
- Usuario de farmacia.
- Usuario de consultorio.
- Usuario de director.
- Usuario administrador.
- Empresa o tenant de prueba.
- Sucursal de prueba.
- Catálogos básicos cargados cuando el flujo lo requiera.

## Qué debe registrar el auditor

Por cada flujo:

- URL exacta.
- Usuario usado.
- Empresa / tenant.
- Acción realizada.
- Resultado esperado.
- Resultado real.
- Si hubo 500, 403, 302 o pantalla vacía.
- Captura de pantalla.
- Mensaje visible en UI.
- Error de consola si aparece.

## Flujos obligatorios

### 1. Entrada al sistema

- Abrir `/`
- Abrir `/login/`
- Abrir `/home/`
- Verificar que:
  - login cargue
  - sesión autenticada redirija al destino correcto
  - no exista 500 en arranque

### 2. Laboratorio

Flujo mínimo:

1. Recepción.
2. Buscar o crear paciente.
3. Crear orden.
4. Agregar estudios.
5. Cobrar.
6. Toma de muestra.
7. Procesamiento.
8. Captura de resultados.
9. Validación.
10. Estado final `RESULTADOS_LISTOS`.
11. Verificar entrega / PDF / portal.

### 3. Farmacia

Flujo mínimo:

1. Abrir PDV.
2. Buscar producto.
3. Agregar al carrito.
4. Cobrar.
5. Cancelar venta.
6. Devolución.
7. Corte de caja.

### 4. Consultorio

Flujo mínimo:

1. Agendar cita.
2. Abrir consulta.
3. Guardar diagnóstico.
4. Validar que el expediente quede accesible.

### 5. Director

Flujo mínimo:

1. Abrir dashboard.
2. Ver métricas.
3. Ver estados de sucursal.
4. Ver que no truene con datos reales.

## Criterios de aceptación

- No hay 500 al entrar.
- No hay loops de redirección.
- El formulario captura valores reales.
- El botón ejecuta la acción correcta.
- El cambio de estado persiste en la base.
- La pantalla siguiente corresponde al flujo esperado.

## Criterios de rechazo

- 500.
- 403 inesperado.
- 302 infinito.
- Pantalla que carga pero no permite escribir.
- Botón que no produce cambio.
- Cambio visual sin persistencia real.

## Formato de reporte final

Cada hallazgo debe reportarse así:

- ID:
- Módulo:
- URL:
- Usuario:
- Paso:
- Resultado esperado:
- Resultado real:
- Severidad:
- Evidencia:
- Clasificación:
- Acción recomendada:

## Qué NO hacer

- No depender de la extención de Claude para validar lo que el humano puede ver.
- No cerrar un flujo solo porque la UI “se ve bien”.
- No asumir que una respuesta 200 significa éxito funcional.
- No reauditar lo que ya quedó canonizado sin nueva evidencia.
- No tratar como fallo funcional los WebSockets de impresión/QZ a `localhost` o `localhost.qz.io` si la herramienta los filtra como ruido conocido.

## Uso recomendado

Este documento se usa cuando:

- la extensión de IA falla,
- la UI necesita revisión manual,
- se quiere validar el flujo exacto de un usuario humano,
- o se requiere evidencia visual y funcional directa.

## Resultado esperado

El sistema debe poder ser usado por personal real sin depender de la IA para cada verificación.

## Herramienta canónica recomendada

Para evitar depender de extensiones de navegador o de reportes manuales dispersos, la verificación humana debe ejecutarse con:

```bash
npm run human:ui -- --target cloud --user <usuario> --pass <clave>
```

Modo visible con pausas:

```bash
npm run human:ui -- --target cloud --user <usuario> --pass <clave> --pause
```

Salida esperada:

- `auditoria_ui_<timestamp>/report.json`
- `auditoria_ui_<timestamp>/report.md`
- `auditoria_ui_<timestamp>/screenshots/`

Este comando debe usarse como primera validación humana. Las IAs quedan para la revisión final y para comparar hallazgos, no para sustituir la ejecución del flujo real.
