# Instruccion maestra para auditoria externa de PRISLAB con Antigravity

## Objetivo

Realizar una auditoria tecnica, funcional, de seguridad, trazabilidad, UX y operacion de PRISLAB sin modificar codigo, archivos, configuracion, ramas, base de datos productiva ni datos operativos. El resultado debe indicar que esta cerrado con evidencia, que falla, que no pudo verificarse y que puede mejorarse.

## Regla principal

Esta sesion es **solo auditoria y verificacion**.

- No editar archivos.
- No crear commits.
- No hacer push, pull request ni cambios en GitHub.
- No ejecutar migraciones contra produccion.
- No borrar, cancelar, cobrar, vender, devolver, modificar inventario ni alterar resultados reales.
- No cambiar permisos, secretos, variables de entorno, configuracion de deploy o reglas de GitHub.
- No inventar evidencia ni convertir una pantalla accesible en una funcion aprobada.

Si se detecta un defecto, documentarlo con reproduccion, impacto y propuesta robusta. La remediacion se ejecutara despues en una sesion autorizada y separada.

## Contexto que debes respetar

- Producto: PRISLAB SaaS.
- Empresa principal: Primero Salud Laboratorio SAS de CV.
- Marca comercial: LABCORE.
- Ramas objetivo: `release/v1.0-local` y el commit realmente desplegado.
- Modulos prioritarios: laboratorio, LIMS, inventario de reactivos e insumos, farmacia, PDV, auditoria, Sentinel, IA, documentos y despliegue.
- El libro de captura es `docs/manual/Plantilla_Carga_Reactivos_Insumos_Prislab.xlsx`.
- No confundir documentacion historica con evidencia actual. Toda afirmacion debe tener fecha, comando, URL, archivo, prueba o captura.

## Preparacion obligatoria

1. Confirmar raiz del checkout, rama, commit, remoto y estado de trabajo.
2. Confirmar que la auditoria trabaja sobre el mismo commit que se pretende evaluar.
3. Guardar un inventario inicial de archivos, configuracion, rutas, modelos, migraciones, workflows y pruebas.
4. Confirmar el entorno: local, staging o produccion; URL exacta; hora; zona horaria; usuario de auditoria; tenant; y restricciones de datos.
5. Si no hay acceso a produccion, marcarlo como **NO VERIFICABLE**, nunca como aprobado.
6. Si se usa navegador, capturar primero una fotografia del estado inicial y no reutilizar datos personales reales.

## Distribucion de agentes

Trabajar en paralelo con agentes independientes. Cada agente debe producir un informe separado y no modificar el checkout.

### Agente 1: integridad y trazabilidad Git

Verificar rama, commit, divergencia, archivos sin seguimiento, historial, tags, workflows, protecciones y correspondencia entre documentacion y codigo. Reportar cualquier diferencia entre el commit auditado y el desplegado.

### Agente 2: seguridad, autenticacion y RBAC

Revisar login, logout, 2FA, expiracion, sesiones, roles, permisos por ruta, bypass por `is_staff`, tenant isolation, CSRF, rate limits, secretos, endpoints publicos y acciones privilegiadas. Probar positivo y negativo por rol.

### Agente 3: LIMS y laboratorio clinico

Auditar catalogo de pruebas, analitos, perfiles, paquetes, tarifas, muestras, recepcion, toma, worklist, captura, formulas, resultados criticos, repeticion, validacion, rechazo, impresion, entrega, historial y estados. Verificar que cada transicion sea idempotente y auditable.

### Agente 4: inventario analitico

Verificar reactivos, controles, calibradores, consumibles, refacciones e insumos generales. Revisar articulo, marca, proveedor, lote, caducidad, apertura, almacenamiento, factura, inserto, SDS, cuarentena, consumo, merma, conversiones, equipo, analito, prueba, repeticion, QC y calibracion.

### Agente 5: motor de consumo LIMS

Auditar la relacion prueba-analito-equipo-material. Probar cantidades por determinacion, repeticion, QC, calibracion, rendimiento teorico/real, merma, conversion de presentacion, alternativas, lote preferente, agotamiento y cambio de lote sin doble descuento.

### Agente 6: farmacia y PDV

Verificar busqueda, seleccion, escaner, stock, lotes, fechas, antibioticos/controlados, venta, venta parcial, cancelacion, devolucion, devolucion parcial, cortes, precortes, gastos, ticket, WhatsApp, auditoria y permisos de empleado, administrador y administrador total.

### Agente 7: API y backend

Enumerar rutas y contratos. Probar autenticacion, autorizacion, validacion de payloads, errores, respuestas JSON, idempotencia, concurrencia, transacciones, filtros por tenant, paginacion, rendimiento y regresiones.

### Agente 8: interfaz y flujo humano

Recorrer cada pantalla como usuario real: navegacion, enlaces, botones, formularios, busqueda, seleccion, modales, mensajes, errores, accesibilidad, responsive, teclado, escaner y estados vacios. Registrar evidencia visual de cada escenario.

### Agente 9: seguridad clinica y regulatoria

Auditar Sentinel, coherencia clinica, Westgard, valores criticos, consentimiento, LFPDPPP, bitacoras, firmas, evidencia, COFEPRIS, ISO 15189 como marco operativo, exportaciones, PDFs y proteccion de datos.

### Agente 10: CI/CD, despliegue y operacion

Verificar checks obligatorios, SBOM, CodeQL, secretos, deploy, health checks, backup/restore, Redis/Celery, logs, alertas, rollback, variables requeridas, SSH y correspondencia de version desplegada.

### Agente 11: documentacion y consistencia

Comparar manuales, runbooks, ADRs, checklists, plantillas, rutas, nombres comerciales, variables, comandos y estado declarado contra el codigo y la interfaz actual.

## Metodo de prueba

Para cada funcion:

1. Definir precondiciones.
2. Definir entrada valida.
3. Ejecutar la accion.
4. Verificar respuesta visible, estado HTTP, base de datos, auditoria y efectos secundarios permitidos.
5. Ejecutar entrada invalida.
6. Repetir la misma accion para comprobar idempotencia.
7. Probar rol sin permiso y tenant ajeno.
8. Registrar resultado y evidencia.

No aceptar solo un `200`, una pantalla cargada o un mensaje generico como prueba de cierre.

## Escenarios minimos

- Datos completos.
- Datos incompletos durante periodo de adaptacion.
- Campo marcado `NO_APLICA` con justificacion.
- Lote 27 y lote 28 del mismo articulo.
- Cambio de marca manteniendo articulo y formula.
- Articulo con dos proveedores.
- Articulo agotado, vencido, bloqueado y en cuarentena.
- Prueba con reactivo principal y alternativa.
- Repeticion analitica.
- QC y calibracion.
- Error de equipo o analito no ligado.
- Usuario sin empresa.
- Usuario de otro tenant.
- Doble envio o doble click.
- Caida de Redis o servicio externo.
- Permisos de empleado frente a administrador.
- Conexion lenta, respuesta vacia y error 500.
- Vista movil y teclado.

## Formato obligatorio de cada hallazgo

```text
ID:
Severidad: CRITICA | ALTA | MEDIA | BAJA
Confianza: CONFIRMADO | PROBABLE | NO_VERIFICABLE
Modulo:
Flujo:
Entorno:
Commit o version:
Precondiciones:
Pasos exactos:
Resultado esperado:
Resultado observado:
Evidencia: archivo, linea, URL, captura, log, respuesta o consulta
Impacto operativo:
Impacto regulatorio o de datos:
Reproducible: SI | NO | INTERMITENTE
Riesgo de regresion:
Oportunidad de mejora:
Propuesta robusta:
Pruebas de aceptacion requeridas:
Plan de despliegue:
Plan de rollback:
No modificar codigo en esta sesion: SI
```

## Criterio de solucion propuesta

Una propuesta no puede ser un parche local. Debe incluir:

- causa raiz;
- modelo de datos y restricciones;
- contrato API y validaciones;
- permisos y tenant isolation;
- transaccion e idempotencia;
- interfaz y mensajes de error;
- pruebas unitarias, integracion, E2E y negativas;
- migracion reversible si aplica;
- observabilidad y auditoria;
- impacto de rendimiento;
- rollout gradual;
- rollback verificable;
- datos de prueba y limpieza controlada;
- criterio objetivo de aceptacion.

## Entregables finales

1. `00_resumen_ejecutivo.md`.
2. `01_hallazgos_confirmados.md`.
3. `02_hallazgos_no_verificables.md`.
4. `03_matriz_cobertura_funcional.csv`.
5. `04_matriz_riesgo_y_prioridad.csv`.
6. `05_oportunidades_mejora.md`.
7. `06_plan_remediacion_robusto.md`.
8. `07_evidencia/` con capturas, logs y respuestas sanitizadas.
9. `08_reconciliacion_documental.md`.

El resumen debe separar claramente: **APROBADO**, **FALLA CONFIRMADA**, **PENDIENTE**, **NO VERIFICABLE** y **OPORTUNIDAD DE MEJORA**. No usar porcentajes de cierre sin matriz de cobertura y evidencia por funcion.

## Criterio final

La auditoria termina cuando cada ruta y flujo dentro del alcance tiene un resultado, evidencia y responsable. Si hay una falla confirmada, no declarar el modulo cerrado. Si solo existe una propuesta, no presentarla como correccion aplicada. Si el entorno no permite probar produccion, dejarlo explicitamente pendiente.
