# Formato de carga de reactivos e insumos

**Empresa objetivo:** Primero Salud Laboratorio SAS de CV  
**Tenant:** `1`  
**Uso:** levantamiento inicial de información para cargar el inventario de laboratorio sin perder trazabilidad.  
**Responsable de captura:** personal designado por laboratorio, almacén y compras.  
**Responsable de validación:** responsable sanitario o persona autorizada.

## 1. Regla principal

No se debe inventar ningún dato. Si un dato administrativo no está disponible durante la migración, se captura como `No disponible durante la migración` o `No aplica`, según corresponda, y se deja una observación. Los datos físicos y operativos que afectan la seguridad no se omiten: nombre, tipo, unidad, lote, caducidad y cantidad deben confirmarse antes de liberar un lote.

El sistema maneja dos niveles:

1. **Catálogo:** qué artículo es y cómo se identifica.
2. **Lote:** qué existencia física se recibió, cuándo caduca, cuánto hay y qué documentos la respaldan.

Un mismo artículo puede tener varios lotes. Nunca se debe crear un artículo nuevo solo porque llegó otro lote.

## 2. Clasificación correcta

| Tipo | Cuándo usarlo | Ejemplos |
|---|---|---|
| `REACTIVO` | Sustancia o kit usado directamente en un análisis | Reactivo de glucosa, colorante, reactivo de química clínica |
| `CALIBRADOR` | Material para calibrar un equipo o método | Calibrador de química clínica |
| `CONTROL_QC` | Material de control interno de calidad | Control nivel normal, patológico o positivo |
| `CONSUMIBLE` | Material que se utiliza en la operación analítica | Tira de orina, tubo, punta, laminilla, cubreobjetos |
| `REFACCION` | Pieza o accesorio de equipo, no consumido por una prueba | Filtro, lámpara, rotor, sensor |
| Insumo general | Artículo no analítico de operación | Guantes no analíticos, papelería, limpieza, cafetería, uniforme |

**Importante:** una tira, tubo, laminilla o punta usada dentro del procesamiento de una prueba debe registrarse como `CONSUMIBLE` en el catálogo de laboratorio, aunque coloquialmente se le llame insumo.

## 3. Tabla A: catálogo de reactivos e insumos analíticos

Se llena una fila por artículo, no una fila por lote.

| Campo en sistema | Obligatorio | Cómo llenarlo correctamente | Ejemplo |
|---|---:|---|---|
| `codigo_interno` | Sí | Código único interno de Primero Salud. No reutilizarlo para otro artículo. | `LAB-REAC-0001` |
| `nombre` | Sí | Nombre técnico completo, tal como aparece en envase o inserto. | `Reactivo para glucosa oxidasa` |
| `tipo` | Sí | Elegir una clasificación de la tabla anterior. | `REACTIVO` |
| `descripcion` | Recomendado | Presentación, concentración, método o notas que diferencien el artículo. | `Kit para método GOD-POD,  R1/R2` |
| `marca` | Sí para trazabilidad | Marca comercial visible en el envase. Si no existe, escribir `GENÉRICO` y justificarlo. | `Spinreact` |
| `fabricante` | Recomendado | Fabricante legal que aparece en el envase o inserto. No confundirlo con distribuidor. | `Spinreact S.A.` |
| `referencia_fabricante` | Recomendado | Número de catálogo o referencia del fabricante. | `1001190` |
| `unidad_medida` | Sí | Unidad real de conteo o consumo. Usar `UNIDAD`, `ML`, `UL`, `L`, `MG`, `G`, `KIT` u otra disponible. | `ML` |
| `temperatura_almacenamiento` | Sí cuando aplique | Copiar el rango del fabricante. No suponerlo. | `2-8°C` |
| `requiere_cadena_frio` | Sí | `Sí` si el producto exige refrigeración o congelación; `No` solo con respaldo del fabricante. | `Sí` |
| `stock_minimo` | Recomendado | Nivel que dispara alerta o reorden. Definir con el responsable del laboratorio. | `10` |
| `stock_maximo` | Opcional | Existencia máxima recomendada. Dejar vacío si aún no está definida. | `50` |
| `proveedor_preferido` | Recomendado | Proveedor habitual, no necesariamente el proveedor de cada lote. | `Distribuidora ABC` |
| `precio_ultima_compra` | Recomendado | Último precio unitario conocido. No confundir con costo total de la factura. | `1250.00` |
| `activo` | Sí | `Sí` si puede utilizarse; `No` si quedó descontinuado o no debe seleccionarse. | `Sí` |
| `notas` | Recomendado | Información útil no cubierta por otro campo. | `Usar con equipo X; requiere mezcla` |

### Regla para catálogos duplicados

Antes de crear un artículo, buscar por:

- nombre técnico;
- referencia del fabricante;
- marca;
- presentación;
- unidad de medida.

Si ya existe, actualizar el catálogo y crear o seleccionar el lote correspondiente. No duplicar por cambio de proveedor, factura o fecha de compra.

## 4. Tabla B: lote de reactivo o insumo analítico

Se llena una fila por cada combinación artículo + número de lote. Si el mismo artículo llega con los lotes `27` y `28`, son dos registros de lote.

| Campo en sistema | Obligatorio | Cómo llenarlo correctamente | Ejemplo |
|---|---:|---|---|
| `reactivo` | Sí | Seleccionar el artículo existente del catálogo. | `LAB-REAC-0001` |
| `numero_lote` | Sí | Copiar exactamente del envase. Respetar letras, guiones y ceros. | `G2026-027` |
| `fecha_caducidad` | Sí | Fecha impresa en el envase, en formato `AAAA-MM-DD`. No aceptar un lote ya vencido. | `2027-08-31` |
| `fecha_apertura` | Al abrir | Registrar el día en que se abrió o empezó a utilizarse. | `2026-07-24` |
| `fecha_compra` | Recomendado | Fecha de compra según factura, nota o proveedor. | `2026-07-20` |
| `cantidad_inicial` | Sí | Cantidad recibida en la unidad de medida del catálogo. | `6` |
| `cantidad_actual` | Sí | Al alta inicial debe ser igual a `cantidad_inicial`, salvo que exista consumo documentado. | `6` |
| `proveedor` | Recomendado | Proveedor que entregó este lote específico. | `Distribuidora ABC` |
| `precio_unitario_compra` | Recomendado | Precio por unidad de medida o presentación recibida. | `1250.00` |
| `costo_total_lote` | Automático | No calcular manualmente si el sistema lo genera; equivale a cantidad inicial por precio unitario. | `7500.00` |
| `orden_compra` | Si existe | Orden de compra de origen. | `OC-2026-0042` |
| `factura_numero` | Si existe | Folio exacto de factura o nota de venta. | `A-18492` |
| `factura_estado` | Sí | `REGISTRADA`, `PENDIENTE`, `NO_APLICA` o `NO_DISPONIBLE`. Elegir según evidencia. | `REGISTRADA` |
| `factura_fecha` | Si existe | Fecha que aparece en la factura. | `2026-07-20` |
| `factura_documento` | Si existe | PDF o imagen legible de la factura. | `factura_A-18492.pdf` |
| `inserto_estado` | Según tipo | `ADJUNTO`, `VERIFICADO`, `PENDIENTE`, `NO_APLICA` o `NO_DISPONIBLE`. | `VERIFICADO` |
| `inserto_version` | Si existe | Versión o fecha del inserto del fabricante. | `Rev. 04/2025` |
| `inserto_documento` | Si existe | PDF o imagen del inserto. | `inserto_glucosa.pdf` |
| `trazabilidad_estado` | Automático/validar | `COMPLETA` cuando no hay faltantes; `ADAPTACION` mientras existan faltantes administrativos. | `ADAPTACION` |
| `campos_pendientes` | Automático/validar | Lista de datos que faltan. No borrar pendientes sin aportar evidencia. | `factura, inserto` |
| `trazabilidad_observaciones` | Recomendado | Explicar por qué falta un dato y quién debe completarlo. | `Compra anterior a la migración; localizar factura.` |
| `estado` | Sí | Iniciar en `CUARENTENA` hasta verificar recepción/QC; pasar a `ACTIVO` solo con autorización. | `CUARENTENA` |
| `lote_aprobado_qc` | Sí para uso | Marcar solo después de la revisión definida por el laboratorio. | `No` |
| `aprobado_por` | Al aprobar | Usuario responsable de la aprobación QC. | `Usuario QFB` |
| `observaciones_qc` | Al revisar | Resultado de revisión, incidencia o condición de uso. | `Envase íntegro; temperatura conforme.` |

### Reglas críticas del lote

- No registrar dos veces el mismo artículo con el mismo número de lote.
- No corregir un número de lote creando otro registro si ya hubo movimientos; usar el procedimiento autorizado de corrección.
- No poner `cantidad_actual` mayor que `cantidad_inicial`.
- No liberar un lote vencido.
- Un lote en `CUARENTENA` no debe consumirse en pruebas clínicas.
- El sistema debe descontar por lote siguiendo FEFO cuando se valide el resultado, salvo reglas de adaptación documentadas.

## 5. Tabla C: catálogo de insumos generales

Usar esta sección para artículos que no forman parte de una prueba ni de una fórmula de consumo analítico.

| Campo en sistema | Obligatorio | Cómo llenarlo correctamente | Ejemplo |
|---|---:|---|---|
| `codigo_interno` | Sí | Código único del insumo. | `INS-ASEO-0001` |
| `nombre` | Sí | Nombre claro y específico. | `Guante de nitrilo mediano` |
| `categoria` | Sí | Papelería, limpieza, informática, infraestructura, cafetería, uniforme u otro. | `LIMPIEZA` |
| `area_principal` | Sí | Área que normalmente lo solicita o consume. | `LABORATORIO` |
| `descripcion` | Recomendado | Talla, material, presentación o especificación. | `Caja de 100 piezas, sin polvo` |
| `unidad_medida` | Sí | Unidad de inventario. | `CAJA` |
| `stock_minimo` | Recomendado | Nivel que genera alerta. | `5` |
| `stock_maximo` | Opcional | Máximo recomendado. | `20` |
| `proveedor_preferido` | Recomendado | Proveedor habitual. | `Proveedor XYZ` |
| `precio_ultima_compra` | Recomendado | Precio unitario de la última compra. | `180.00` |
| `activo` | Sí | Disponible para solicitar o no. | `Sí` |
| `notas` | Recomendado | Condiciones de almacenamiento o uso. | `Almacenar seco.` |

### Lote de insumo general

| Campo | Obligatorio | Regla |
|---|---:|---|
| `insumo` | Sí | Seleccionar el catálogo existente. |
| `cantidad_inicial` | Sí | Cantidad recibida. |
| `cantidad_actual` | Sí | Igual a la inicial al registrar la entrada. |
| `precio_unitario_compra` | Recomendado | Precio unitario de esa entrada. |
| `orden_compra` | Si existe | Vincular la orden de origen. |
| `recibido_por` | Sí | Usuario que físicamente recibió y contó. |
| `fecha_recepcion` | Automático | No modificar; la plataforma la registra. |

Los insumos generales no sustituyen a los consumibles analíticos. Si una salida debe descontarse automáticamente por una prueba LIMS, debe estar en `CatalogoReactivoLab` como `CONSUMIBLE` y tener una fórmula de consumo.

## 6. Tabla D: consumo por prueba LIMS

Se llena una fila por cada analito y reactivo/consumible utilizado.

| Campo | Obligatorio | Cómo llenarlo | Ejemplo |
|---|---:|---|---|
| `analito` | Sí | Seleccionar el analito autoritativo de LIMS. | `Glucosa` |
| `reactivo` | Sí | Seleccionar el artículo exacto del catálogo. | `Reactivo glucosa GOD-POD` |
| `cantidad_por_prueba` | Sí | Cantidad real consumida por una determinación. | `0.50` |
| `unidad` | Sí | Unidad de consumo: `ML`, `UL`, `UNIDAD`, etc. | `ML` |
| `incluye_overhead_qc` | Sí | Marcar si la cantidad ya incluye controles/calibraciones prorrateados. | `No` |
| `activo` | Sí | Desactivar cuando cambie el método, equipo o reactivo. | `Sí` |

No se debe asignar consumo a analitos calculados que no usan material directo. La fórmula debe validarse con el químico responsable, el inserto y el procedimiento normalizado de operación.

## 7. Valores permitidos para adaptación

| Situación real | Captura correcta | No hacer |
|---|---|---|
| No existe factura porque es inventario histórico | `factura_estado = NO_DISPONIBLE` + observación | Inventar folio |
| El artículo no requiere inserto | `inserto_estado = NO_APLICA` | Dejarlo como verificado |
| El inserto existe pero aún no se digitaliza | `inserto_estado = PENDIENTE` | Marcar `VERIFICADO` |
| Se conoce lote y caducidad, pero no fecha de compra | Dejar `fecha_compra` vacía y registrar pendiente | Usar la fecha de carga como fecha de compra |
| No se conoce la marca | `marca = GENÉRICO` solo si se confirma que no aparece en el envase, con observación | Copiar el nombre del proveedor como marca |
| Se desconoce el costo | `precio_unitario_compra = 0` solo con autorización y nota | Estimar un precio sin evidencia |
| El lote está recibido pero no revisado | `estado = CUARENTENA` | Liberarlo directamente a `ACTIVO` |

## 8. Paquete mínimo que debe entregar cada responsable

Por cada artículo:

1. Fotografía legible del frente y reverso del envase.
2. Fotografía del número de lote y caducidad.
3. Inserto, si aplica.
4. Factura, nota o evidencia de compra, si existe.
5. Cantidad física contada.
6. Condición de almacenamiento.
7. Nombre de quien captura y nombre de quien valida.

## 9. Orden recomendado de captura

1. Crear o localizar el catálogo.
2. Confirmar tipo, marca, fabricante, unidad y almacenamiento.
3. Crear un lote por cada número de lote físico.
4. Capturar cantidad inicial y actual.
5. Adjuntar factura e inserto o seleccionar el estado correcto de adaptación.
6. Dejar el lote en `CUARENTENA`.
7. Validar recepción y QC.
8. Cambiar a `ACTIVO` solo con autorización.
9. Configurar consumo por analito LIMS.
10. Realizar una prueba controlada y verificar que el descuento se registre en el lote correcto.

## 10. Control antes de subir la información

| Verificación | Resultado esperado |
|---|---|
| No hay códigos internos repetidos dentro del tenant | Sí |
| Cada lote tiene artículo, lote, caducidad y cantidad | Sí |
| Las cantidades usan la unidad del catálogo | Sí |
| No hay lotes vencidos liberados | Sí |
| Los lotes históricos tienen pendientes documentados | Sí |
| Facturas e insertos están vinculados o marcados correctamente | Sí |
| Los artículos consumidos por LIMS tienen fórmula por analito | Sí |
| El responsable sanitario revisó los lotes que pasan a activo | Sí |
| Se conserva una copia de los archivos fuente | Sí |

## 11. Formato sugerido para hoja de captura

Para facilitar la carga masiva, usar una hoja con estas pestañas:

| Pestaña | Una fila representa | Clave de relación |
|---|---|---|
| `catalogo_lab` | Un reactivo, calibrador, control o consumible | `codigo_interno` |
| `lotes_lab` | Un lote físico | `codigo_interno + numero_lote` |
| `catalogo_general` | Un insumo operativo | `codigo_interno` |
| `lotes_general` | Una entrada de insumo general | `codigo_interno + fecha_recepcion` |
| `consumo_lims` | Una fórmula analito-artículo | `analito + codigo_interno` |
| `documentos` | Un archivo o evidencia | `codigo_interno + numero_lote` |

Antes de importar, el personal debe entregar la hoja con las observaciones y evidencias. La carga no debe ejecutarse directamente sobre producción sin una revisión de duplicados, unidades, caducidades y tenant.

## 12. Criterio de cierre del inventario de laboratorio

El inventario no se considera cerrado solo porque los artículos aparezcan en pantalla. Se considera listo para operación cuando:

- el catálogo no tiene duplicados;
- todos los lotes físicos están representados;
- las cantidades coinciden con el conteo;
- los lotes se encuentran en el estado correcto;
- la trazabilidad faltante está documentada;
- los consumos LIMS están configurados y probados;
- una salida de prueba descuenta del lote correcto;
- el responsable sanitario valida el conjunto.

## 13. Regla de descuento automático por prueba

El descuento debe trabajar con una **receta de consumo persistente**, no con texto libre ni con una selección temporal de pantalla.

### 13.1 Componentes obligatorios y alternativas

Una prueba puede tener varios componentes obligatorios:

| Grupo de consumo | Ejemplo para hemoglobina glucosilada | Regla |
|---|---|---|
| Reactivo principal | Kit Wondfo para HbA1c | Se descuenta una opción seleccionada |
| Consumible | Punta o cubeta | Se descuenta si está configurado |
| Líquido del equipo | Diluyente específico del analizador | Se descuenta si aplica |
| Control/calibración | Material QC o calibrador | Se registra como consumo técnico o QC según el procedimiento |

Dentro de un mismo grupo pueden existir alternativas. Por ejemplo, dos marcas compatibles para HbA1c. Solo una debe estar marcada como **seleccionada para uso**; la otra permanece disponible, pero no descuenta mientras no sea activada.

### 13.2 Cambio de reactivo en operación

El cambio de marca o reactivo no debe borrar el historial. El flujo esperado es:

1. Registrar el nuevo artículo y su lote.
2. Liberar el lote mediante QC.
3. Seleccionarlo como alternativa activa para ese grupo, analito y equipo.
4. Registrar fecha, usuario y motivo del cambio.
5. Las nuevas pruebas descuentan el nuevo reactivo.
6. Las salidas históricas conservan el reactivo y lote que realmente se usaron.

La marca puede cambiar entre lotes sin crear otro analito. Si cambia la composición, método o compatibilidad, debe crearse una fórmula alternativa nueva y no editar destructivamente la fórmula histórica.

### 13.3 Cantidad por prueba y presentaciones

El inventario debe aceptar tanto presentaciones como consumo operativo. Ejemplo:

| Dato | Valor |
|---|---:|
| Presentación recibida | Caja de 24 pruebas |
| Cantidad inicial del lote | `24 UNIDADES` |
| Consumo por resultado | `1 UNIDAD` |
| Repetición | `1 UNIDAD` adicional |
| Saldo después de una prueba | `23 UNIDADES` |

Si el fabricante expresa el rendimiento como `24 pruebas por caja`, la caja no debe registrarse como una sola unidad consumible si el descuento se hará prueba por prueba. Se debe registrar la equivalencia de presentación y la unidad operativa que realmente se descuenta.

### 13.4 Repetición de una prueba

Una repetición no debe editar ni duplicar silenciosamente el resultado original. Debe crear un **evento de repetición** con:

- resultado o analito relacionado;
- motivo de la repetición;
- usuario que la autorizó y usuario que la ejecutó;
- fecha y hora;
- reactivos/lotes descontados;
- cantidad adicional consumida;
- clave de idempotencia para impedir doble descuento por reenvío.

La prueba inicial descuenta una vez. Cada repetición autorizada descuenta una vez adicional. Cancelar o corregir un evento no debe borrar historial: debe generar una reversa trazable cuando corresponda.

### 13.5 Equipos e interfaces

La receta de consumo debe poder asociarse a:

- empresa y sucursal;
- analito LIMS;
- equipo o analizador;
- código que envía el equipo por HL7/ASTM;
- grupo de consumo;
- reactivo o consumible;
- unidad y cantidad por ejecución;
- alternativa seleccionada;
- vigencia desde/hasta;
- usuario y motivo del cambio.

Si un analito se procesa en dos equipos, cada equipo puede tener una receta diferente. Si no se especifica equipo, la receta solo debe usarse como configuración genérica cuando no exista una receta específica para el equipo utilizado.

### 13.6 Estado actual de implementación

El sistema ya cuenta con descuento FEFO idempotente al validar `ResultadoParametro`, fórmulas por analito y salidas ligadas a lote. Antes de declarar este flujo cerrado aún deben implementarse y probarse:

- grupos de consumo con alternativas seleccionables;
- selección persistente por analito y equipo;
- vínculo del resultado con el equipo de origen;
- evento formal de repetición con descuento adicional;
- reversa trazable de una repetición;
- pantalla para cambiar de reactivo sin perder el historial;
- pruebas de caja de 24 pruebas, consumo inicial, cambio de marca, cambio de lote y repetición.
