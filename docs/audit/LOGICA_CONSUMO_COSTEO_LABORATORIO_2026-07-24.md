# Logica de consumo y costeo del laboratorio

**Tenant:** 1 - Primero Salud Laboratorio SAS de CV  
**Fecha:** 2026-07-24  
**Alcance:** LIMS, inventario analitico y costeo de ejecuciones

## Regla de negocio

Un perfil o paquete comercial no es una existencia de inventario. El paquete solo determina lo que se vende y lo que se desglosa en el LIMS. El inventario se controla por articulos atomicos:

| Nivel | Ejemplo | Regla |
|---|---|---|
| Muestra | Tubo dorado, aguja, torunda, alcohol | Se consume una vez por orden/muestra. Torunda y alcohol pueden quedar como uso libre si la politica del laboratorio no desea control unitario. |
| Analito | Glucosa, urea, creatinina y los otros analitos QSC | Cada analito tiene su reactivo, marca, equipo, lote, unidad y cantidad por determinacion. |
| Repeticion | Repeticion de glucosa | Consume la cantidad adicional del analito repetido y conserva el motivo, usuario y fecha. No duplica los materiales de toma. |
| QC/calibracion | Control o calibracion | Se registra como consumo tecnico separado, no como paciente. |

## Escenario QSC

Para una QSC de seis analitos:

1. Se descuenta una vez el tubo dorado, aguja y cualquier material comun configurado como `MUESTRA`.
2. Se descuenta una unidad o volumen configurado para cada uno de los seis analitos.
3. Si se repite solo glucosa, se descuenta nuevamente glucosa; no se descuentan de nuevo tubo, aguja, torunda o alcohol.
4. Si se realiza una nueva toma, debe generarse un evento de muestra nuevo. Ese evento si puede consumir nuevamente los materiales comunes.

Para glucosa individual se aplica la misma regla: materiales comunes una vez y solo el reactivo de glucosa como consumo analitico.

## Implementacion

- `inventario.models.ConsumoEstudioReactivo.aplicacion` distingue `ANALITO` y `MUESTRA`.
- Las formulas `MUESTRA` no requieren FK a un analito y usan una clave idempotente por orden, evitando doble descuento al validar seis resultados.
- `SalidaAnaliticaLab` conserva el lote, cantidad, orden, analito cuando corresponde, formula y usuario validador.
- `CosteoEjecucionAnaliticaLab` congela el costo desde `SalidaAnaliticaLab.cantidad_consumida * LoteReactivoLab.precio_unitario_compra` y guarda el detalle de cada lote.
- La repeticion queda vinculada a `RepeticionAnaliticaLab` y tiene su propio evento de costeo.
- La base impide formulas comunes duplicadas por empresa, articulo, equipo y grupo mediante una restriccion condicional.

## Costos y ganancias

El costo material real por ejecucion ya queda disponible. La utilidad material se calcula como ingreso asignado menos costo material. Para paquetes comerciales, el sistema no debe repartir automaticamente el precio entre analitos sin una regla aprobada; el ingreso se conserva a nivel de orden hasta definir una politica de asignacion. Mano de obra, depreciacion, energia y gastos indirectos deben agregarse posteriormente como componentes de costo separados, no mezclarse con el costo del lote.

## Captura operativa

La plantilla `Plantilla_Carga_Reactivos_Insumos_Prislab_v5_2026-07-24.xlsx` contiene el prellenado completo del catalogo disponible:

- `bom_consumo_prueba`: receta por muestra y analito.
- `consumo_por_analito`: precarga de los analitos del catalogo LIMS.
- `costeo_por_prueba`: campos para determinacion, repeticion, QC, calibracion, lote, costo e ingreso.
- `captura_reactivos`: Factor reumatoide y los seis antigenos de reacciones febriles: Tifico O, Tifico H, Paratifico B, Paratifico A, Brucella abortus y Proteus.
- `captura_consumibles`: tubo dorado, tubo lila EDTA, tubo verde heparina, aguja, puntilla, torunda y alcohol.
- `catalogo_equipos`: procesos de aglutinacion en placa y analisis de quimica clinica, ambos marcados para completar con el equipo fisico real.
- `catalogo_pruebas`: relaciones precargadas entre perfiles y analitos tomadas de `Examenes_Perfil.csv`.
- 806 filas de parametros LIMS, 101 pruebas del catalogo y 755 relaciones perfil/prueba-analito precargadas.
- Reactivos, controles y calibradores precargados por cada parametro para confirmar si aplican fisicamente; no se presentan como existencia disponible.
- Consumibles precargados por los tipos de muestra reales del catalogo, ademas de los materiales comunes de toma.
- Equipos precargados por metodo analitico como `EQUIPO_POR_CONFIRMAR`; el nombre, marca, modelo, serie e interfaz se completan con el inventario fisico.

Las filas precargadas con sufijo `-CONFIRMAR` son guias de captura y no deben importarse como articulos definitivos hasta completar marca, fabricante, presentacion, lote, equipo, costo y responsable. Las filas de QSC incluidas en la BOM son ejemplos marcados `PENDIENTE_LIGAR`; deben sustituirse por los codigos reales del catalogo antes de importar a produccion.

## Evidencia

La prueba de seis analitos valida que una muestra consume un unico material comun, seis reactivos analiticos y seis registros de costeo. Las pruebas de repeticion e idempotencia permanecen en verde.
