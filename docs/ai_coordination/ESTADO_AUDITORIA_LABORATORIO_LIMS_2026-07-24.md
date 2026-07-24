# Estado de auditoria laboratorio, LIMS e inventario analitico

**Fecha:** 2026-07-24  
**Rama auditada:** `release/v1.0-local`  
**Commit de documentacion previo:** `976ed0b`

## Actualizacion de logica de consumo y costeo

Se incorporo la distincion operativa entre consumo por analito y consumo comun por muestra:

- `ANALITO`: una formula independiente para glucosa, urea, creatinina y cada analito fisico.
- `MUESTRA`: una formula para tubo dorado, aguja, torunda, alcohol u otro material comun; se descuenta una vez por orden/muestra y no una vez por cada analito del perfil.
- Una repeticion consume la formula del analito repetido y no vuelve a descontar los materiales comunes de toma.
- `CosteoEjecucionAnaliticaLab` congela el costo usando el lote y el precio unitario de compra realmente consumidos, con vinculo a orden, paciente, analito, tipo de ejecucion y detalle de lotes.

La receta comercial `QSC` no es un articulo de inventario. Solo referencia la orden comercial; sus consumos se registran como materiales comunes y analitos atomicos. La asignacion del ingreso de un paquete entre analitos queda como regla financiera pendiente de confirmacion, para no inventar margen por analito.

Las migraciones funcionales generadas son `inventario/migrations/0015_costeoejecucionanaliticalab_and_more.py`, `0016_alter_costeoejecucionanaliticalab_repeticion_and_more.py` y `0017_remove_consumoestudioreactivo_inventario_consumo_estudio_reactivo_uniq_and_more.py`.

## Evidencia adicional

- 6 pruebas de inventario/FEFO/costeo en verde, incluyendo un escenario de seis analitos: un solo descuento comun, seis descuentos analiticos, costeo de las seis ejecuciones y repeticion idempotente. La suite dirigida completa de esta ronda quedo en 46 pruebas OK.
- Plantilla regenerada sin errores de formulas. Se agregaron `bom_consumo_prueba` y `costeo_por_prueba`.
- Archivo entregable nuevo: `docs/manual/Plantilla_Carga_Reactivos_Insumos_Prislab_v2_2026-07-24.xlsx`.

## Alcance ejecutado

Se verifico el flujo de laboratorio/LIMS y los componentes de inventario relacionados en codigo, con base local aislada para pruebas. Tambien se intento la verificacion humana desde navegador.

## Correcciones realizadas

1. Se aislo la base SQLite de los tests en `:memory:` cuando Django ejecuta la suite local. El servidor de desarrollo ya no puede bloquear la base de pruebas.
2. Se agrego un modo opt-in `PRISLAB_TEST_NO_MIGRATIONS=1` para pruebas unitarias que no requieren validar la historia de migraciones. Las pruebas de migraciones deben ejecutarse sin esa variable.
3. Se corrigio la prueba de toma de muestra para usar el namespace real `laboratorio:preparacion_toma`.
4. Se alineo la marca visible de la pantalla de preparacion de toma con `LABCORE`.

## Evidencia automatizada

Comandos ejecutados:

```powershell
python manage.py check
python manage.py makemigrations --check --noinput
$env:PRISLAB_TEST_NO_MIGRATIONS='1'
python manage.py test core.tests.test_lab_validation_pdf core.tests.test_laboratorio_recepcion_tenant core.tests.test_lims_config_tenant_security core.tests.test_coherencia_clinica -v 1
python manage.py test core.tests.test_lims_cart_search core.tests.test_farmacia_lotes_api core.tests.test_farmacia_entrada_precios core.tests.test_farmacia_regulatorio core.tests.test_auditoria_segura_laboratorio core.tests.test_auditoria_segura_farmacia core.tests.test_farmacia_permission_helpers -v 1
```

Resultados:

- `manage.py check`: correcto.
- `makemigrations --check`: correcto.
- Suite laboratorio/LIMS y coherencia: **17 pruebas OK**.
- Suite LIMS, inventario analitico, farmacia regulatoria y auditoria: **23 pruebas OK**.
- Total en esta ronda: **40 pruebas OK**.
- Sentinel genero eventos esperados para accesos cross-tenant y recursos inexistentes; no fueron fallas de aislamiento.
- Se observo una advertencia de rendimiento en entrada de mercancia: 963.77 ms, 11 consultas, umbral de latencia 800 ms. No fallo funcional, queda como oportunidad de optimizacion.
- Se observaron advertencias esperadas por consentimiento digital ausente y `LAB_VALIDATION_PIN` no configurado en escenarios de prueba.

## Verificacion humana

El servidor local arranco correctamente y las migraciones pendientes se aplicaron sin errores. La sesion de navegador disponible no pudo acceder al `127.0.0.1` de Windows por aislamiento entre el navegador conectado y el proceso local.

Esto significa:

- No existe evidencia de fallo funcional de la pantalla por ese motivo.
- Tampoco existe evidencia suficiente para declarar aprobada la interfaz humana.
- La verificacion de interfaz debe repetirse desde un navegador con acceso directo al host donde corre Django o desde el entorno de despliegue real.

## Estado de cierre

| Area | Estado | Evidencia |
|---|---|---|
| Configuracion Django | APROBADA | `check` sin incidencias |
| Migraciones aplicadas en entorno local | APROBADA | 212 migraciones aplicadas |
| Tenant y seguridad LIMS | APROBADA EN TESTS | 40 pruebas dirigidas en verde |
| Recepcion y toma de muestra | APROBADA EN TESTS | suite de laboratorio en verde |
| Coherencia clinica | APROBADA EN TESTS | 3 pruebas especificas dentro de la suite |
| Inventario analitico y consumo | APROBADA EN TESTS DIRIGIDOS | suite de inventario relacionada en verde |
| Interfaz como usuario humano | PENDIENTE | navegador aislado del localhost |
| Produccion | NO DECLARADA | no se verifico URL, despliegue ni credenciales finales en esta ronda |

## Pendientes obligatorios

1. Repetir el flujo humano en un navegador con acceso al servidor.
2. Ejecutar la misma matriz contra la URL de produccion con cuenta de auditoria y sin alterar datos reales.
3. Revisar la advertencia de latencia de entrada de mercancia antes de ampliar carga.
4. Ejecutar una ronda separada de migraciones completas sin `PRISLAB_TEST_NO_MIGRATIONS=1` para validar el historial, no solo el modelo final.

No se debe usar este documento para afirmar que produccion esta cerrada. Es el estado comprobable de esta ronda.
