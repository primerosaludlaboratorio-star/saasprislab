# Plan de auditoria integral de PRISLAB SaaS

Version 1.0 - 2026-09-15

## 1. Objetivo y alcance

Este plan adapta la metodologia de auditoria ciega entregada para Imperium al
proyecto PRISLAB SaaS. El objetivo es obtener evidencia reproducible de que el
sistema es seguro, funcional, multi-tenant, operable y listo para validacion
humana controlada.

El alcance incluye:

- Aplicacion Django y sus apps: laboratorio/LIMS, farmacia, inventario,
  recepcion, pacientes, enfermeria, consultorio, contabilidad, ventas,
  suscripciones, IoT, IA, seguridad y reportes.
- PostgreSQL, Redis/Celery, almacenamiento de archivos, PDF, Docker, Nginx,
  GitHub Actions y despliegue VPS.
- Flujos completos desde venta o recepcion hasta cobro, toma, procesamiento,
  validacion, impresion y entrega.
- Aislamiento entre empresas y sucursales, RBAC, auditoria, trazabilidad,
  concurrencia, errores, rollback, observabilidad y recuperacion.

No se considera evidencia suficiente: un grep, un endpoint que responde 200,
un test aislado, un artefacto generado sin abrir, un reporte previo, una base
SQLite como unico respaldo, o una correccion no probada contra el tip actual.

El plan es para PRISLAB. No modifica ni audita Imperium. Los nombres Gatekeeper,
MCP, WORM u otros del documento base solo se usan si existe un equivalente real
en PRISLAB; de lo contrario se marca N/A con justificacion.

## 2. Responsabilidades y separacion de funciones

### GitHub

GitHub Actions es el verificador reproducible e independiente de la sesion de
Codex. Debe ejecutar en un checkout limpio y publicar artefactos inmutables:

- commit SHA y estado del arbol;
- `manage.py check --deploy` y migraciones;
- pruebas unitarias, integracion y seguridad;
- lint, AST/SAST, tipos y compilacion;
- SCA, SBOM y auditoria de dependencias;
- pruebas de frontend, plantillas y construccion;
- cobertura y lista de omitidas, fallidas y `xfail`;
- hashes SHA-256 de reportes y paquetes.

GitHub no debe aceptar un merge si falla un gate obligatorio. Un workflow
verde no equivale por si solo a aprobacion de produccion.

### Codex

Codex debe:

- verificar el tip real, no una copia ni un reporte antiguo;
- analizar codigo, configuracion, modelos, vistas, servicios, plantillas,
  migraciones y scripts;
- reproducir cada hallazgo antes de corregirlo;
- implementar la correccion minima robusta, con regresion automatizada;
- documentar archivo, linea, causa, cambio, prueba y limite residual;
- comparar el SHA probado con el SHA desplegado;
- abstenerse de declarar independiente una prueba que el mismo cambio hizo
  pasar.

Codex puede cerrar un defecto tecnico con evidencia, pero no puede aceptar por
si solo riesgo residual, cambios destructivos de datos, credenciales o un
despliegue irreversible.

### Testigo independiente

Un segundo ejecutor autorizado, humano o agente externo, debe repetir la
matriz sobre un checkout limpio y entregar solo reportes read-only. Debe usar
su propio proceso y no recibir los hallazgos esperados como casos a aprobar.
Sus resultados se reconcilian contra los artefactos de GitHub y Codex.

### Responsable humano

El propietario de PRISLAB autoriza datos sinteticos, ventanas de despliegue,
riesgo residual y promocion. Ningun agente debe rotar, borrar ni exponer
credenciales por este plan. Los scripts historicos que el propietario ordene
conservar se clasifican como riesgo residual y se excluyen de acciones
destructivas.

## 3. Reglas de congelamiento y fuente de verdad

Antes de cada corrida se debe crear un identificador `RUN_ID` y un archivo
`FREEZE.json` fuera del checkout auditado. Debe contener:

- ruta canonica y commit SHA;
- rama, remoto y hash del arbol de trabajo;
- lista completa de archivos versionados y no versionados;
- versiones de Python, Django, Node, PostgreSQL, Redis y herramientas;
- hash de requirements lock, imagenes y artefactos de prueba;
- variables de entorno usadas, sin valores secretos;
- base de datos, empresa y sucursal de prueba;
- fecha, operador y proposito.

Las evidencias de ejecucion se guardan fuera del target, por ejemplo:
`C:\Users\jonil\Desktop\PRISLAB_AUDIT_EVIDENCE\<RUN_ID>`. Solo el plan,
resumen y referencias pueden versionarse en `audit/`.

No se mezclan worktrees, ramas, reportes o bases entre corridas. Se calcula el
hash inicial y final del tip. Si cambia, la corrida se invalida y se reinicia.

## 4. Fases de ejecucion

### Fase 0 - Autorizacion y seguridad operativa

- Definir si la corrida es estatico-local, staging o produccion read-only.
- Declarar presupuesto de tiempo, llamadas IA y almacenamiento.
- Usar cuentas temporales con minimo privilegio para pruebas por rol.
- Usar pacientes, ventas, lotes, resultados y documentos sinteticos.
- Prohibir borrados, cobros reales, devoluciones reales, cambios de usuarios,
  alteracion de lotes productivos y rotacion de secretos.
- Preparar rollback y evidencia antes de cualquier prueba mutante.

### Fase 1 - Inventario y deriva

Construir un inventario de aplicaciones, rutas, modelos, tareas, comandos,
plantillas, static, migraciones, integraciones, variables, workers y servicios.
Para cada componente indicar propietario, fuente, consumidor, estado y si esta
montado realmente en URLconf o despliegue.

Comparar:

- checkout local vs remoto;
- tip probado vs imagen desplegada;
- `requirements.txt` vs lock vs imagen;
- settings duplicados y variables efectivas;
- migraciones vs esquema PostgreSQL;
- rutas documentadas vs rutas vivas;
- scripts y fixtures contra modelos actuales.

### Fase 2 - Gates automaticos de GitHub

Los jobs obligatorios deben cubrir:

1. `manage.py check --deploy`.
2. `makemigrations --check --dry-run`.
3. suite Django completa con reporte JUnit.
4. pruebas tenant, RBAC, IDOR, CSRF, cifrado, uploads y rate limit.
5. `coverage` instalado desde el lock y umbral definido.
6. lint, compilacion y analisis AST/SAST.
7. tipos y contratos donde existan.
8. `pip-audit`, `npm audit` y SBOM con versiones exactas.
9. build Docker reproducible y escaneo de imagen.
10. validacion de plantillas, static, migraciones y OpenAPI si aplica.

El resumen debe separar PASS, FAIL, SKIP, XFAIL y BLOCKED. Un `ok=true` sin
conteos, logs y hash de artefactos es un falso verde.

### Fase 3 - Auditoria estatica de Codex

Revisar cada archivo de codigo alcanzable y los scripts operativos relevantes.
Priorizar:

- consultas sin `empresa` o `sucursal`;
- `get_object_or_404`, `update`, `delete`, `bulk_create` y acciones admin;
- decoradores, bypass de `is_staff`, superusuario y grupos;
- cambios de estado, validacion clinica y cierre de resultados;
- dinero, inventario, folios, idempotencia y concurrencia;
- archivos, media, PDFs, URLs publicas y SSRF;
- logs, PII/PHI, telemetria y llamadas a LLM;
- excepciones silenciosas, fallback fail-open y errores 500;
- comandos destructivos, backups y secretos.

Cada sospecha debe convertirse en un caso reproducible o clasificarse como no
confirmada. No se heredan hallazgos historicos sin revalidarlos contra el tip.

### Fase 4 - Staging tecnico

Levantar un entorno aislado con Python 3.12, PostgreSQL compatible con el
despliegue, Redis/Celery, almacenamiento temporal, Nginx y la misma imagen o
commit que se pretende probar. Ejecutar migraciones desde cero y con base
reutilizada. Medir latencia separando:

- tiempo de DDL y round-trip;
- tiempo de creacion de base;
- tiempo real de tests;
- bloqueos PostgreSQL y transacciones abiertas;
- disponibilidad de workers y cache.

El tunel SSH no debe ser el unico camino para certificar rendimiento. Cuando
sea necesario, ejecutar el runner junto a PostgreSQL y conservar la medicion
del tunel como diagnostico, no como resultado funcional.

### Fase 5 - Flujos humanos completos

Cada caso debe seguir la interfaz y conservar su folio desde el inicio hasta el
final. No se prueban ventanas aisladas. Registrar actor, empresa, sucursal,
datos sinteticos, pasos, respuesta visible, estado de base y archivos creados.

#### Farmacia y venta

- alta de producto con y sin codigo de barras;
- lote, caducidad, existencia, fraccionamiento y material de curacion;
- venta sola y combinada de medicamento, antibiotico, jeringa y consumibles;
- pago total, parcial, saldo, precio especial, descuento y redondeo permitido;
- edicion de folio y receta con alternativas legibles;
- cancelacion, devolucion autorizada, PIN, trazabilidad y restauracion de stock;
- historial de ventas, desglose, ticket, PDF y corte/precorte;
- historial de cortes por rol, filtros, exportacion y conciliacion;
- baja por caducidad, bloqueo de inventario y mensajes comprensibles.

#### Recepcion y laboratorio/LIMS

- alta de paciente y orden desde venta/recepcion;
- toma, muestras, etiquetas, estados y lista de trabajo;
- captura manual, equipo, LIS/HL7 y resultado maquilado;
- controles, calibradores, repeticiones, flags, panic values e interferencias;
- rechazo, correccion autorizada, validacion e inmutabilidad posterior;
- equipo fuera de servicio, otro equipo, corte de luz y reanudacion segura;
- PDF de resultados, impresion, entrega, portal y candado de saldo/privacidad;
- auditoria de cada cambio con usuario, fecha, valor anterior y nuevo.

#### Casos de error y recuperacion

- doble clic, reintento HTTP, timeout y respuesta duplicada;
- perdida de red, Redis, worker, equipo o almacenamiento;
- transaccion abortada a mitad de flujo;
- pago rechazado o monto inconsistente;
- archivo invalido, PDF no generado o descarga no autorizada;
- dos usuarios editando el mismo producto, orden, lote o resultado;
- usuario sin rol, empresa incorrecta y sucursal incorrecta.

### Fase 6 - Adversarial y controles negativos

Sembrar en un entorno descartable un defecto controlado por detector y exigir
que lo encuentre una vez. Ejemplos:

- quitar temporalmente un filtro de empresa;
- enviar un redondeo fuera de rango;
- cambiar un resultado ya validado;
- omitir un decorador de rol;
- exponer un archivo por URL directa;
- usar una dependencia vulnerable de prueba;
- modificar un registro append-only.

La siembra nunca se hace en produccion. Si un detector no atrapa su negativo,
el gate queda fallido aunque todos los tests normales pasen.

### Fase 7 - Reconciliacion y liberacion

Comparar reportes de GitHub, Codex y testigo independiente por commit, archivo,
severidad y evidencia. Resolver diferencias como CONFIRMADO, DESCARTADO,
STALE, LIMITACION o NO REPRODUCIBLE; nunca ocultarlas.

Solo despues se puede desplegar a staging y luego a produccion con:

- imagen identificada por digest;
- migraciones revisadas y backup verificado;
- smoke read-only post-deploy;
- health, logs, workers y rutas criticas comprobados;
- plan de rollback documentado;
- comparacion entre SHA auditado y SHA servido.

## 5. Matriz minima por modulo

Cada modulo debe tener una fila y evidencia para todas las columnas. Una celda
vacia es cobertura faltante, no N/A.

| Modulo | Auth/RBAC | Tenant | Flujo feliz | Errores/rollback | Concurrencia | PDF/UI | Integraciones | Auditoria |
|---|---|---|---|---|---|---|---|---|
| Farmacia/POS | | | | | | | | |
| Inventario | | | | | | | | |
| Recepcion | | | | | | | | |
| Laboratorio/LIMS | | | | | | | | |
| Pacientes | | | | | | | | |
| Contabilidad | | | | | | | | |
| Seguridad | | | | | | | | |
| IA | | | | | | | | |
| IoT/LIS | | | | | | | | |
| Reportes/PDF | | | | | | | | |
| Deploy/ops | | | | | | | | |

## 6. Esquema de hallazgo

Cada hallazgo usa un ID estable y contiene:

- modulo y flujo;
- severidad e impacto;
- naturaleza: seguridad, funcional, integridad, disponibilidad, deuda,
  estilo, vendor o limitacion;
- archivo y linea, si aplica;
- precondiciones y datos sinteticos;
- esperado vs observado;
- evidencia A: codigo/configuracion;
- evidencia B: prueba reproducible;
- evidencia C: comportamiento dinamico o estado persistido;
- SHA local, SHA desplegado y RUN_ID;
- correccion aplicada, regresion y resultado;
- estado: abierto, corregido-no-verificado, verificado, descartado, stale,
  bloqueado o riesgo aceptado.

Nunca se imprimen contrasenas, tokens, API keys, cookies, PHI o valores de
secreto. Se usan nombres, fingerprints parciales o hashes no reversibles.

## 7. Falsos verdes obligatorios

La auditoria debe comprobar explicitamente que no ocurre lo siguiente:

- se audita una copia distinta del checkout canonico;
- el reporte indica PASS con tests omitidos o no recolectados;
- se prueba SQLite pero se declara PostgreSQL certificado;
- el SHA probado no coincide con el desplegado;
- el PDF responde exitosamente pero no existe, esta vacio o es ilegible;
- una venta responde exito con inventario o pago parcialmente persistido;
- una URL de media permite leer un archivo sin autorizacion;
- un `except Exception` oculta un error funcional;
- un script antiguo contradice los modelos actuales;
- una matriz tiene modulos o columnas sin evidencia;
- un gate produce `ok=true` sin log, conteo y checksum;
- el testigo independiente recibe los resultados antes de probar.

## 8. Entregables

Fuera del checkout auditado, cada corrida produce:

- `FREEZE.json`;
- `INVENTARIO.json` y `INVENTARIO.csv`;
- `MATRIZ_COBERTURA.md`;
- `HALLAZGOS.json` y `HALLAZGOS.md`;
- `TEST_RESULTS.xml` y resumen de PASS/FAIL/SKIP/XFAIL;
- `SCA.txt`, SBOM y resultados de imagen;
- evidencia de flujos humanos con datos sinteticos;
- evidencia de PDF descargado, renderizado y validado;
- evidencia de rollback y recuperacion;
- `DEPLOY_EVIDENCE.md` con SHA, digest, migraciones y smoke tests;
- `RECONCILIACION_GITHUB_CODEX_TESTIGO.md`;
- `VEREDICTO_FINAL.md`.

El veredicto debe ser uno de: `NO_LISTO`, `LISTO_PARA_STAGING`,
`LISTO_PARA_VALIDACION_HUMANA` o `APROBADO_PARA_PRODUCCION`. El ultimo solo
es valido si no hay P0/P1 abiertos, todos los modulos tienen matriz completa,
los controles negativos pasan, la corrida independiente coincide y el
responsable humano acepta por escrito los riesgos residuales.

## 9. Orden operativo recomendado

1. Congelar tip y generar `FREEZE.json`.
2. Reconciliar checkout, remoto, imagen, settings y documentos.
3. Ejecutar gates obligatorios en GitHub.
4. Ejecutar auditoria estatica y corregir solo defectos confirmados.
5. Repetir gates en un checkout limpio.
6. Levantar staging Python 3.12/PostgreSQL y ejecutar pruebas tecnicas.
7. Ejecutar flujos humanos completos por modulo, empezando por farmacia y LIMS.
8. Ejecutar fallos, concurrencia y controles negativos.
9. Entregar el paquete al testigo independiente sin adelantar hallazgos.
10. Reconciliar, corregir, repetir pruebas afectadas y actualizar evidencia.
11. Desplegar solo el SHA aprobado, primero a staging y despues a produccion.
12. Ejecutar smoke read-only, firmar veredicto y archivar evidencias.

## 10. Regla de cierre

Un defecto no se cierra por estar documentado, por tener un commit o por
aparecer verde en una prueba aislada. Se cierra unicamente cuando existe una
correccion en el tip congelado, una regresion automatizada, una prueba de flujo
cuando corresponda, evidencia de entorno aplicable y reconciliacion
independiente. Lo que no pueda probarse se declara limitacion, nunca PASS.
