import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "C:/Users/jonil/Desktop/PRISLAB_deploy_checkout/outputs/reactivos_insumos_2026-07-24";
await fs.mkdir(outputDir, { recursive: true });
const wb = Workbook.create();
const C = { navy: "#12304A", teal: "#0F766E", yellow: "#FFF2CC", blue: "#DCEEFF", orange: "#FCE4D6", gray: "#F2F4F7", border: "#C8D1DC", white: "#FFFFFF", red: "#F4CCCC" };

function colName(index) {
  let value = index;
  let name = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    value = Math.floor((value - 1) / 26);
  }
  return name;
}

function parseCsv(text) {
  const rows = [];
  let row = [], cell = "", quoted = false;
  const source = text.replace(/^\uFEFF/, "");
  for (let i = 0; i < source.length; i += 1) {
    const ch = source[i];
    const next = source[i + 1];
    if (ch === '"' && quoted && next === '"') { cell += '"'; i += 1; continue; }
    if (ch === '"') { quoted = !quoted; continue; }
    if (ch === ',' && !quoted) { row.push(cell.trim()); cell = ""; continue; }
    if ((ch === '\n' || ch === '\r') && !quoted) {
      if (ch === '\r' && next === '\n') i += 1;
      row.push(cell.trim()); cell = "";
      if (row.some(value => value !== "")) rows.push(row);
      row = [];
      continue;
    }
    cell += ch;
  }
  if (cell !== "" || row.length) { row.push(cell.trim()); rows.push(row); }
  return rows;
}

async function loadCsv(relativePath, headerIndex = 0) {
  const rows = parseCsv(await fs.readFile(new URL(relativePath, import.meta.url), "utf8"));
  const headers = rows[headerIndex] || [];
  return rows.slice(headerIndex + 1).map(row => Object.fromEntries(headers.map((header, index) => [header || `col_${index + 1}`, row[index] || ""])));
}

const limsExamenes = await loadCsv("../../datos_lims/Examenes.csv");
const limsParametros = await loadCsv("../../datos_lims/Parametros.csv");
const perfilRaw = parseCsv(await fs.readFile(new URL("../../datos_lims/Examenes_Perfil.csv", import.meta.url), "utf8"));
const limsPerfilRows = perfilRaw.slice(2).filter(row => row[0] && row[3]).map(row => ({
  codigoExamen: row[0], abreviaturaExamen: row[1], descripcionExamen: row[2], codigoAnalito: row[3], descripcionAnalito: row[4],
}));
const tariffRows = parseCsv(await fs.readFile(new URL("../../datos_lims/Tarifa_estudios de laboratorio.csv", import.meta.url), "utf8"));
const tariffHeaderIndex = tariffRows.findIndex(row => row[0] === "Tipo" && row[1] === "Código");
const limsTarifas = tariffHeaderIndex >= 0
  ? tariffRows.slice(tariffHeaderIndex + 1).map(row => ({ tipo: row[0] || "", codigo: row[1] || "", abreviatura: row[2] || "", descripcion: row[3] || "", importe: row[4] || "" })).filter(row => row.codigo || row.descripcion)
  : [];

function title(sheet, end, text) {
  sheet.mergeCells(`A1:${end}1`);
  sheet.getRange("A1").values = [[text]];
  sheet.getRange(`A1:${end}1`).format = { fill: C.navy, font: { bold: true, color: C.white, size: 15 }, verticalAlignment: "center" };
  sheet.getRange(`A1:${end}1`).format.rowHeight = 28;
}
function setup(sheet, end, sheetTitle, subtitle, headers, widths, formulaCols = [], rowEnd = 205) {
  title(sheet, end, sheetTitle);
  sheet.mergeCells(`A2:${end}2`);
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${end}2`).format = { fill: C.gray, font: { italic: true, color: "#475569", size: 10 }, wrapText: true };
  sheet.getRange(`A5:${end}5`).values = [headers];
  sheet.getRange(`A5:${end}5`).format = { fill: C.teal, font: { bold: true, color: C.white, size: 10 }, wrapText: true, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: C.border } };
  sheet.getRange(`A5:${end}5`).format.rowHeight = 42;
  sheet.getRange(`A6:${end}${rowEnd}`).format = { font: { color: "#1F2937", size: 10 }, borders: { preset: "inside", style: "thin", color: C.border } };
  headers.forEach((_, i) => sheet.getRange(`${colName(i + 1)}:${colName(i + 1)}`).format.columnWidth = widths[i] || 16);
  for (const col of headers.map((_, i) => colName(i + 1)).filter(c => !formulaCols.includes(c))) sheet.getRange(`${col}6:${col}${rowEnd}`).format.fill = C.yellow;
  for (const col of formulaCols) sheet.getRange(`${col}6:${col}${rowEnd}`).format.fill = C.blue;
  sheet.freezePanes.freezeRows(5);
  sheet.showGridLines = false;
  const table = sheet.tables.add(`A5:${end}${rowEnd}`, true, `${sheet.name.replace(/[^A-Za-z0-9]/g, "")}Table`);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
}
function listValidation(sheet, range, values) { sheet.getRange(range).dataValidation = { rule: { type: "list", values } }; }
function tenant(sheet, range = "A6:A205") { sheet.getRange(range).values = Array.from({ length: 200 }, () => [1]); }

const lists = wb.worksheets.add("Listas y definiciones");
const readme = wb.worksheets.add("LEEME");
const altaNuevo = wb.worksheets.add("alta_nuevo_articulo");
const catalogoLab = wb.worksheets.add("catalogo_lab");
const lotesLab = wb.worksheets.add("lotes_lab");
const catalogoGeneral = wb.worksheets.add("catalogo_general");
const lotesGeneral = wb.worksheets.add("lotes_general");
const consumoLims = wb.worksheets.add("consumo_lims");
const documentos = wb.worksheets.add("documentos");
const reactivos = wb.worksheets.add("captura_reactivos");
const controlesQc = wb.worksheets.add("captura_controles_qc");
const calibradores = wb.worksheets.add("captura_calibradores");
const consumibles = wb.worksheets.add("captura_consumibles");
const refacciones = wb.worksheets.add("captura_refacciones");
const insumosGenerales = wb.worksheets.add("captura_insumos_generales");
const consumoPrueba = wb.worksheets.add("consumo_por_prueba");
const pruebas = wb.worksheets.add("catalogo_pruebas");
const equipos = wb.worksheets.add("catalogo_equipos");
const proveedores = wb.worksheets.add("catalogo_proveedores");
const conversiones = wb.worksheets.add("conversiones_unidades");
const controlCarga = wb.worksheets.add("control_completitud");
const prefillPruebas = wb.worksheets.add("prefill_pruebas_lims");
const prefillAnalitos = wb.worksheets.add("prefill_analitos_lims");
const prefillTarifas = wb.worksheets.add("prefill_tarifas_lims");
const consumoAnalitos = wb.worksheets.add("consumo_por_analito");
const bomConsumo = wb.worksheets.add("bom_consumo_prueba");
const costeoPrueba = wb.worksheets.add("costeo_por_prueba");

title(lists, "G", "Listas permitidas y definiciones");
lists.getRange("A3:D3").values = [["tipo", "unidad_medida", "estado_lote", "estado_factura"]];
lists.getRange("A4:D10").values = [
  ["REACTIVO", "UNIDAD", "CUARENTENA", "REGISTRADA"],
  ["CALIBRADOR", "ML", "ACTIVO", "PENDIENTE"],
  ["CONTROL_QC", "UL", "BLOQUEADO", "NO_APLICA"],
  ["CONSUMIBLE", "L", "VENCIDO", "NO_DISPONIBLE"],
  ["REFACCION", "MG", "AGOTADO", null],
  ["INSUMO_GENERAL", "G", null, null],
  [null, "KIT", null, null],
];
lists.getRange("F3:G3").values = [["inserto_estado", "si_no"]];
lists.getRange("F4:G9").values = [["ADJUNTO", "Sí"], ["VERIFICADO", "No"], ["PENDIENTE", null], ["NO_APLICA", null], ["NO_DISPONIBLE", null], ["", null]];
lists.getRange("I3:I6").values = [["accion_catalogo"], ["NUEVO"], ["ACTUALIZAR_EXISTENTE"], ["NO_DUPLICAR"]];
lists.getRange("A3:D3").format = { fill: C.teal, font: { bold: true, color: C.white } };
lists.getRange("F3:G3").format = { fill: C.teal, font: { bold: true, color: C.white } };
lists.getRange("I3:I3").format = { fill: C.teal, font: { bold: true, color: C.white } };
lists.getRange("A3:I10").format.borders = { preset: "all", style: "thin", color: C.border };
lists.getRange("A:A").format.columnWidth = 20; lists.getRange("B:B").format.columnWidth = 18; lists.getRange("C:D").format.columnWidth = 18; lists.getRange("F:F").format.columnWidth = 20; lists.getRange("G:G").format.columnWidth = 12; lists.showGridLines = false;

title(readme, "H", "Plantilla de carga de reactivos e insumos | Primero Salud Laboratorio SAS de CV");
readme.mergeCells("A3:H3"); readme.getRange("A3").values = [["Tenant objetivo: 1 | Una fila por artículo, lote, fórmula o evidencia según la pestaña. No inventar datos."]];
readme.getRange("A3:H3").format = { fill: C.orange, font: { bold: true, color: "#7C2D12" }, wrapText: true };
readme.getRange("A5:B13").values = [
  ["Orden de captura", "Acción"],
  ["1", "Llenar catalogo_lab o catalogo_general. Buscar duplicados por nombre, marca, referencia y presentación."],
  ["2", "Registrar un lote separado por cada número de lote físico."],
  ["3", "Capturar cantidad, unidad, caducidad y condición de almacenamiento."],
  ["4", "Adjuntar o marcar correctamente factura e inserto; no sustituir evidencia con datos inventados."],
  ["5", "Mantener el lote en CUARENTENA hasta revisión y QC."],
  ["6", "Configurar consumo_lims para analitos y equipos cuando aplique."],
  ["7", "Registrar documentos en la pestaña documentos."],
  ["8", "Entregar el archivo para revisión antes de importar a producción."],
];
readme.getRange("A5:B5").format = { fill: C.teal, font: { bold: true, color: C.white } }; readme.getRange("A5:B13").format.wrapText = true; readme.getRange("A5:B13").format.borders = { preset: "all", style: "thin", color: C.border };
readme.getRange("A:A").format.columnWidth = 18; readme.getRange("B:B").format.columnWidth = 95;
readme.getRange("A15:B19").values = [["Leyenda", "Significado"], ["Amarillo", "Campo que debe llenar el personal."], ["Azul", "Campo calculado o controlado; no sobrescribir sin autorización."], ["Naranja", "Advertencia o dato que requiere revisión."], ["No aplica", "Usar solo cuando realmente no corresponda y dejar observación."]];
readme.getRange("A15:B15").format = { fill: C.teal, font: { bold: true, color: C.white } }; readme.getRange("A16").format.fill = C.yellow; readme.getRange("A17").format.fill = C.blue; readme.getRange("A18").format.fill = C.orange; readme.getRange("A15:B19").format.borders = { preset: "all", style: "thin", color: C.border }; readme.showGridLines = false;
readme.getRange("D5:E13").values = [["Hoja", "Qué debe llenar el personal"], ["captura_reactivos", "Identidad completa, marca/fabricante, lote, caducidad, apertura, almacenamiento, cadena de frío, proveedor, factura, SDS/inserto, estado, prueba, equipo y cantidades por prueba, repetición y QC."], ["captura_controles_qc", "Control, nivel, analito, matriz, equipo, lote, valores objetivo, rango, frecuencia, cantidad por corrida/repetición, estabilidad, frío, inserto y validación."], ["captura_calibradores", "Calibrador, analito, equipo, método, niveles, trazabilidad, lote, cantidad por calibración/repetición, frecuencia, estabilidad, frío, inserto y validación."], ["captura_consumibles", "Consumible, marca, presentación, lote/caducidad, equipo, prueba/proceso, cantidades por determinación, repetición y QC, esterilidad, ficha y estado."], ["captura_refacciones", "Equipo, marca/modelo/serie, parte y marca, cantidad, condición, ubicación, compra/garantía, instalación, vida útil, ficha y mantenimiento."], ["captura_insumos_generales", "Insumo, categoría, área, marca, presentación, existencias, mínimos/máximos, proveedor, recepción, uso específico, lote, reposición, soporte y estado."], ["consumo_por_prueba", "Prueba LIMS, analito, artículo, equipo, método, etapa, grupo, alternativa, seleccionado, cantidad por determinación, repetición, QC, unidad, conversión, lote, vigencia y responsable."], ["documentos", "Facturas, notas, insertos, SDS, fichas técnicas, fotografías y evidencias vinculadas al artículo y lote."]];
readme.getRange("D5:E5").format = { fill: C.teal, font: { bold: true, color: C.white } }; readme.getRange("D5:E13").format.wrapText = true; readme.getRange("D5:E13").format.borders = { preset: "all", style: "thin", color: C.border }; readme.getRange("D:D").format.columnWidth = 30; readme.getRange("E:E").format.columnWidth = 72;
readme.getRange("D14:E22").values = [["catalogo_pruebas", "Catálogo de pruebas, analitos, muestras, método, criterios, calibración, QC, repeticiones y SOP."], ["catalogo_equipos", "Equipos, interfaces, pruebas soportadas, materiales ligados, mantenimiento y calibración."], ["catalogo_proveedores", "Datos fiscales, contacto, marcas, suministro, documentos, evaluación y estado del proveedor."], ["conversiones_unidades", "Conversión de caja/kit/frasco a piezas, mL, pruebas o determinaciones; rendimiento, merma y factor."], ["control_completitud", "Pendientes por artículo antes de importar: lote, documento, prueba, equipo, consumo, responsable y fecha compromiso."], ["prefill_pruebas_lims", "Pruebas precargadas desde Examenes.csv. Completar reactivo, equipo, consumos, QC y calibración."], ["prefill_analitos_lims", "Analitos precargados desde Parametros.csv. Completar prueba, reactivo, equipo y cantidad."], ["prefill_tarifas_lims", "Tarifas precargadas desde la lista vigente. Confirmar precio, vigencia y código real."], ["consumo_por_analito", "Hoja operativa principal: una fila por analito consumible. Glucosa, urea y creatinina se capturan por separado; los paquetes no se inventarían."]];
readme.getRange("D23:E24").values = [["bom_consumo_prueba", "Receta operativa por muestra y analito. Los materiales comunes se marcan MUESTRA y se aplican una sola vez; los analitos se capturan como átomos independientes."], ["costeo_por_prueba", "Costeo por determinación, repetición, QC y calibración. El costo real debe venir del lote y el precio de compra; el ingreso de paquetes se asigna en revisión financiera."]];
readme.getRange("D23:E24").format.wrapText = true; readme.getRange("D23:E24").format.borders = { preset: "all", style: "thin", color: C.border };
readme.getRange("D14:E22").format.wrapText = true; readme.getRange("D14:E22").format.borders = { preset: "all", style: "thin", color: C.border };

const altaHeaders = ["tenant_id", "accion_catalogo", "tipo_articulo", "codigo_interno_existente", "nombre", "descripcion", "marca", "fabricante", "referencia_fabricante", "unidad_medida", "requiere_cadena_frio", "motivo_alta_o_cambio", "proveedor", "fecha_solicitud", "solicitado_por", "revisado_por", "estado_revision", "observaciones"];
setup(altaNuevo, "R", "Alta de nuevo reactivo, insumo o consumible", "Usar esta pestaña cuando se compre algo nuevo. NUEVO crea un artículo; ACTUALIZAR_EXISTENTE modifica uno localizado; NO_DUPLICAR detiene altas repetidas.", altaHeaders, [12,22,18,24,30,34,20,24,22,18,22,34,24,18,24,24,20,36]); tenant(altaNuevo); listValidation(altaNuevo, "B6:B205", ["NUEVO", "ACTUALIZAR_EXISTENTE", "NO_DUPLICAR"]); listValidation(altaNuevo, "C6:C205", ["REACTIVO", "CALIBRADOR", "CONTROL_QC", "CONSUMIBLE", "REFACCION", "INSUMO_GENERAL"]); listValidation(altaNuevo, "K6:K205", ["Sí", "No"]); listValidation(altaNuevo, "Q6:Q205", ["PENDIENTE", "APROBADO", "RECHAZADO"]); altaNuevo.getRange("N6:N205").format.numberFormat = "yyyy-mm-dd";

const labHeaders = ["tenant_id", "codigo_interno", "nombre", "tipo", "descripcion", "marca", "fabricante", "referencia_fabricante", "unidad_medida", "temperatura_almacenamiento", "requiere_cadena_frio", "stock_minimo", "stock_maximo", "proveedor_preferido", "precio_ultima_compra", "activo", "notas", "accion_catalogo"];
setup(catalogoLab, "R", "Catálogo de laboratorio", "Una fila por reactivo, calibrador, control o consumible. No crear duplicados por cambio de lote.", labHeaders, [12,20,30,18,34,20,24,22,16,24,20,14,14,24,18,12,34,22]); tenant(catalogoLab); listValidation(catalogoLab, "K6:K205", ["Sí", "No"]); listValidation(catalogoLab, "P6:P205", ["Sí", "No"]); listValidation(catalogoLab, "R6:R205", ["NUEVO", "ACTUALIZAR_EXISTENTE", "NO_DUPLICAR"]); catalogoLab.getRange("O6:O205").format.numberFormat = "$#,##0.00";

const loteHeaders = ["tenant_id", "codigo_interno", "numero_lote", "fecha_caducidad", "fecha_apertura", "fecha_compra", "cantidad_inicial", "cantidad_actual", "unidad_medida", "proveedor", "precio_unitario_compra", "costo_total_lote", "orden_compra", "factura_numero", "factura_estado", "factura_fecha", "factura_documento", "inserto_estado", "inserto_version", "inserto_documento", "trazabilidad_estado", "campos_pendientes", "trazabilidad_observaciones", "estado", "lote_aprobado_qc", "aprobado_por", "observaciones_qc"];
setup(lotesLab, "AA", "Lotes de reactivos e insumos analíticos", "Una fila por combinación artículo + número de lote físico. Registrar dos filas si llegan los lotes 27 y 28.", loteHeaders, [12,20,18,16,16,16,16,16,16,24,20,18,18,18,18,16,28,18,18,28,18,28,36,16,18,22,36], ["L", "U", "V"]); tenant(lotesLab);
lotesLab.getRange("L6").formulas = [[`=IF(OR(G6="",K6=""),"",G6*K6)`]]; lotesLab.getRange("L6:L205").fillDown();
lotesLab.getRange("U6").formulas = [[`=IF(AND(B6<>"",C6<>"",D6<>"",G6<>"",H6<>"",I6<>""),"COMPLETA","ADAPTACION")`]]; lotesLab.getRange("U6:U205").fillDown();
lotesLab.getRange("V6").formulas = [[`=IF(B6="","codigo_interno; ","")&IF(C6="","numero_lote; ","")&IF(D6="","fecha_caducidad; ","")&IF(G6="","cantidad_inicial; ","")&IF(H6="","cantidad_actual; ","")&IF(I6="","unidad_medida","")`]]; lotesLab.getRange("V6:V205").fillDown();
lotesLab.getRange("D6:F205").format.numberFormat = "yyyy-mm-dd"; lotesLab.getRange("P6:P205").format.numberFormat = "yyyy-mm-dd"; lotesLab.getRange("G6:H205").format.numberFormat = "#,##0.00"; lotesLab.getRange("K6:L205").format.numberFormat = "$#,##0.00";
listValidation(lotesLab, "O6:O205", ["REGISTRADA", "PENDIENTE", "NO_APLICA", "NO_DISPONIBLE"]); listValidation(lotesLab, "R6:R205", ["ADJUNTO", "VERIFICADO", "PENDIENTE", "NO_APLICA", "NO_DISPONIBLE"]); listValidation(lotesLab, "X6:X205", ["CUARENTENA", "ACTIVO", "BLOQUEADO", "VENCIDO", "AGOTADO"]); listValidation(lotesLab, "Y6:Y205", ["Sí", "No"]);
lotesLab.getRange("D6:D205").conditionalFormats.add("cellIs", { operator: "lessThan", formula: "TODAY()", format: { fill: C.red, font: { color: "#9C0006", bold: true } } }); lotesLab.getRange("G6:H205").conditionalFormats.add("cellIs", { operator: "lessThan", formula: 0, format: { fill: C.red, font: { color: "#9C0006", bold: true } } });

const generalHeaders = ["tenant_id", "codigo_interno", "nombre", "categoria", "area_principal", "descripcion", "unidad_medida", "stock_minimo", "stock_maximo", "proveedor_preferido", "precio_ultima_compra", "activo", "notas", "accion_catalogo"];
setup(catalogoGeneral, "N", "Catálogo de insumos generales", "Para artículos operativos que no se descuentan automáticamente por una prueba LIMS.", generalHeaders, [12,20,30,20,22,34,18,14,14,24,18,12,34,22]); tenant(catalogoGeneral); listValidation(catalogoGeneral, "L6:L205", ["Sí", "No"]); listValidation(catalogoGeneral, "N6:N205", ["NUEVO", "ACTUALIZAR_EXISTENTE", "NO_DUPLICAR"]); catalogoGeneral.getRange("K6:K205").format.numberFormat = "$#,##0.00";

const generalLotHeaders = ["tenant_id", "codigo_interno", "fecha_recepcion", "cantidad_inicial", "cantidad_actual", "unidad_medida", "precio_unitario_compra", "orden_compra", "factura_numero", "factura_estado", "recibido_por", "observaciones"];
setup(lotesGeneral, "L", "Entradas de insumos generales", "Una fila por entrada física. Usar para limpieza, papelería, infraestructura u otros insumos no analíticos.", generalLotHeaders, [12,20,18,18,18,18,22,18,18,18,24,40]); tenant(lotesGeneral); lotesGeneral.getRange("C6:C205").format.numberFormat = "yyyy-mm-dd"; lotesGeneral.getRange("G6:G205").format.numberFormat = "$#,##0.00"; listValidation(lotesGeneral, "J6:J205", ["REGISTRADA", "PENDIENTE", "NO_APLICA", "NO_DISPONIBLE"]);

const consumoHeaders = ["tenant_id", "analito", "codigo_interno", "equipo", "grupo_consumo", "es_alternativa", "seleccionada", "prioridad", "cantidad_por_prueba", "unidad", "incluye_overhead_qc", "activo", "motivo_cambio", "validado_por"];
setup(consumoLims, "N", "Fórmulas de consumo por prueba LIMS", "Una fila por analito + artículo + equipo. Persistir alternativas y activar solo la que corresponda.", consumoHeaders, [12,26,20,24,20,16,16,12,20,16,20,12,34,24]); tenant(consumoLims); listValidation(consumoLims, "F6:G205", ["Sí", "No"]); listValidation(consumoLims, "K6:L205", ["Sí", "No"]); consumoLims.getRange("I6:I205").format.numberFormat = "#,##0.0000";

const docsHeaders = ["tenant_id", "codigo_interno", "numero_lote", "tipo_documento", "nombre_archivo", "ruta_o_enlace", "fecha_documento", "estado_validacion", "validado_por", "observaciones"];
setup(documentos, "J", "Documentos y evidencias", "Relacionar facturas, notas, insertos, fotografías y evidencias con el artículo y el lote.", docsHeaders, [12,20,18,22,28,40,18,22,24,40]); tenant(documentos); documentos.getRange("G6:G205").format.numberFormat = "yyyy-mm-dd"; listValidation(documentos, "H6:H205", ["PENDIENTE", "VALIDADO", "RECHAZADO", "NO_APLICA"]);

const reactivoHeaders = ["tenant_id", "codigo_interno", "nombre_tecnico", "nombre_comercial", "marca", "fabricante", "referencia_catalogo", "presentacion", "unidad_medida", "lote", "caducidad", "fecha_apertura", "temperatura_almacenamiento", "requiere_cadena_frio", "cantidad_recibida", "cantidad_actual", "proveedor", "factura", "precio_unitario", "prueba_principal", "observaciones", "tipo_reactivo", "analito_o_prueba", "equipo", "metodo", "grupo_consumo", "cantidad_por_prueba", "unidad_consumo", "cantidad_por_repeticion", "cantidad_por_qc", "estabilidad_abierto", "inserto_estado", "sds_estado", "estado_lote", "responsable_validacion"];
setup(reactivos, "AI", "Captura individual de reactivos", "Una fila por reactivo y lote. Completar identidad, trazabilidad, condiciones, prueba, equipo, analito y consumos; relacionar el detalle exacto en consumo_por_prueba.", reactivoHeaders, [12,18,28,28,20,24,20,20,16,18,16,16,24,20,18,18,24,20,18,28,36,20,28,24,24,20,20,18,22,18,22,18,18,18,24]); tenant(reactivos); listValidation(reactivos, "N6:N205", ["Sí", "No"]); listValidation(reactivos, "AF6:AF205", ["ADJUNTO", "VERIFICADO", "PENDIENTE", "NO_APLICA", "NO_DISPONIBLE"]); listValidation(reactivos, "AG6:AG205", ["ADJUNTO", "PENDIENTE", "NO_APLICA", "NO_DISPONIBLE"]); listValidation(reactivos, "AH6:AH205", ["CUARENTENA", "ACTIVO", "BLOQUEADO", "VENCIDO", "AGOTADO"]); reactivos.getRange("K6:L205").format.numberFormat = "yyyy-mm-dd"; reactivos.getRange("S6:S205").format.numberFormat = "$#,##0.00"; reactivos.getRange("AA6:AD205").format.numberFormat = "#,##0.0000";

const qcHeaders = ["tenant_id", "codigo_interno", "nombre_control", "nivel_control", "analito", "equipo", "marca", "fabricante", "lote", "caducidad", "matriz", "valor_objetivo", "rango_aceptable", "unidad", "cantidad_recibida", "cantidad_actual", "cantidad_por_corrida", "frecuencia_qc", "proveedor", "factura", "inserto", "observaciones", "tipo_control", "tipo_muestra", "cantidad_por_repeticion", "estabilidad_abierto", "temperatura_almacenamiento", "requiere_cadena_frio", "estado_lote", "responsable_validacion", "documento_inserto", "fecha_validacion"];
setup(controlesQc, "AF", "Captura individual de controles de calidad", "Una fila por control, nivel y lote. Registrar analito, equipo, matriz, rango, frecuencia, consumos por corrida y repetición, condiciones e inserto.", qcHeaders, [12,18,28,18,24,24,20,24,18,16,18,18,22,14,18,18,20,20,24,20,20,36,20,20,22,22,24,20,18,24,28,18]); tenant(controlesQc); controlesQc.getRange("J6:J205").format.numberFormat = "yyyy-mm-dd"; controlesQc.getRange("AF6:AF205").format.numberFormat = "yyyy-mm-dd"; listValidation(controlesQc, "R6:R205", ["Diario", "Por corrida", "Semanal", "Mensual", "Según procedimiento"]); listValidation(controlesQc, "AB6:AB205", ["Sí", "No"]); listValidation(controlesQc, "AC6:AC205", ["CUARENTENA", "ACTIVO", "BLOQUEADO", "VENCIDO", "AGOTADO"]);

const calibradorHeaders = ["tenant_id", "codigo_interno", "nombre_calibrador", "analito", "equipo", "metodo", "marca", "fabricante", "lote", "caducidad", "trazabilidad", "niveles", "cantidad_recibida", "cantidad_actual", "cantidad_por_calibracion", "unidad", "frecuencia_calibracion", "proveedor", "factura", "inserto", "observaciones", "tipo_calibracion", "trazabilidad_documento", "cantidad_por_repeticion", "estabilidad_abierto", "temperatura_almacenamiento", "requiere_cadena_frio", "estado_lote", "responsable_validacion", "documento_inserto", "fecha_validacion"];
setup(calibradores, "AE", "Captura individual de calibradores", "Una fila por calibrador y lote. Especificar equipo, analito, método, niveles, trazabilidad, frecuencia, consumo, condiciones e inserto.", calibradorHeaders, [12,18,28,24,24,24,20,24,18,16,24,20,18,18,22,14,22,24,20,20,36,22,28,22,22,24,20,18,24,28,18]); tenant(calibradores); calibradores.getRange("J6:J205").format.numberFormat = "yyyy-mm-dd"; calibradores.getRange("AE6:AE205").format.numberFormat = "yyyy-mm-dd"; listValidation(calibradores, "Q6:Q205", ["Por corrida", "Diario", "Semanal", "Mensual", "Según procedimiento"]); listValidation(calibradores, "AA6:AA205", ["Sí", "No"]); listValidation(calibradores, "AB6:AB205", ["CUARENTENA", "ACTIVO", "BLOQUEADO", "VENCIDO", "AGOTADO"]);

const consumibleHeaders = ["tenant_id", "codigo_interno", "nombre_consumible", "tipo_consumible", "marca", "fabricante", "presentacion", "unidad_medida", "lote", "caducidad", "equipo", "prueba_o_proceso", "cantidad_recibida", "cantidad_actual", "cantidad_por_prueba", "unidad_consumo", "requiere_esterilidad", "proveedor", "factura", "temperatura_almacenamiento", "observaciones", "tipo_prueba", "cantidad_por_repeticion", "cantidad_por_qc", "estabilidad_abierto", "requiere_lote", "estado_lote", "responsable_validacion", "documento_ficha", "fecha_validacion"];
setup(consumibles, "AD", "Captura individual de consumibles analíticos", "Una fila por consumible y lote. Registrar prueba/proceso, equipo, cantidad por determinación, repetición, QC, esterilidad, lote y ficha técnica.", consumibleHeaders, [12,18,30,22,20,24,20,16,18,16,24,30,18,18,20,18,20,24,20,24,36,22,22,20,22,18,18,24,28,18]); tenant(consumibles); listValidation(consumibles, "Q6:Q205", ["Sí", "No"]); listValidation(consumibles, "Z6:Z205", ["Sí", "No"]); listValidation(consumibles, "AA6:AA205", ["CUARENTENA", "ACTIVO", "BLOQUEADO", "VENCIDO", "AGOTADO"]); consumibles.getRange("J6:J205").format.numberFormat = "yyyy-mm-dd"; consumibles.getRange("AD6:AD205").format.numberFormat = "yyyy-mm-dd";

const refaccionHeaders = ["tenant_id", "codigo_interno", "equipo", "marca_equipo", "modelo", "numero_serie_equipo", "nombre_refaccion", "numero_parte", "marca_refaccion", "cantidad", "unidad", "condicion", "ubicacion", "proveedor", "factura", "fecha_compra", "garantia_hasta", "intervalo_mantenimiento", "responsable", "observaciones", "fecha_instalacion", "vida_util_estimada", "es_consumible_equipo", "documento_ficha_tecnica", "estado_activo", "responsable_validacion", "observaciones_mantenimiento"];
setup(refacciones, "AA", "Captura individual de refacciones", "Una fila por refacción o accesorio. Ligar al equipo, número de parte, instalación, vida útil, garantía y mantenimiento; indicar si consume existencias del equipo.", refaccionHeaders, [12,18,24,20,20,24,28,20,20,14,14,18,20,24,20,16,16,24,24,36,18,22,20,28,16,24,36]); tenant(refacciones); listValidation(refacciones, "L6:L205", ["NUEVA", "INSTALADA", "REPARACION", "BAJA"]); listValidation(refacciones, "W6:W205", ["Sí", "No"]); listValidation(refacciones, "Y6:Y205", ["Sí", "No"]); refacciones.getRange("P6:Q205").format.numberFormat = "yyyy-mm-dd"; refacciones.getRange("U6:U205").format.numberFormat = "yyyy-mm-dd";

const generalDetailHeaders = ["tenant_id", "codigo_interno", "nombre_insumo", "categoria", "area_responsable", "marca", "presentacion", "unidad_medida", "lote_si_aplica", "caducidad_si_aplica", "cantidad_recibida", "cantidad_actual", "stock_minimo", "stock_maximo", "proveedor", "factura", "precio_unitario", "fecha_recepcion", "responsable", "observaciones", "uso_especifico", "lote_control", "fecha_caducidad", "frecuencia_reposicion", "documento_soporte", "estado", "responsable_validacion", "observaciones_control"];
setup(insumosGenerales, "AB", "Captura individual de insumos generales", "Una fila por insumo y entrada. Registrar uso específico, control de lote/caducidad cuando aplique, reposición, soporte, responsable y estado.", generalDetailHeaders, [12,18,30,22,24,20,22,16,20,20,18,18,14,14,24,20,18,18,24,36,30,18,18,22,28,16,24,36]); tenant(insumosGenerales); listValidation(insumosGenerales, "Z6:Z205", ["ACTIVO", "INACTIVO", "AGOTADO", "NO_APLICA"]); insumosGenerales.getRange("J6:J205").format.numberFormat = "yyyy-mm-dd"; insumosGenerales.getRange("R6:R205").format.numberFormat = "yyyy-mm-dd"; insumosGenerales.getRange("W6:W205").format.numberFormat = "yyyy-mm-dd"; insumosGenerales.getRange("Q6:Q205").format.numberFormat = "$#,##0.00";

const consumoPruebaHeaders = ["tenant_id", "prueba_lims", "analito", "codigo_interno", "tipo_articulo", "equipo", "metodo", "etapa_proceso", "grupo_consumo", "es_alternativa", "seleccionada", "cantidad_usada", "unidad_consumo", "cantidad_por_repeticion", "incluye_qc_calibracion", "frecuencia_consumo", "version_formula", "validado_por", "fecha_validacion", "activo", "observaciones", "cantidad_por_qc", "lote_preferente", "unidad_presentacion", "factor_conversion", "fuente_validacion", "fecha_inicio_vigencia", "fecha_fin_vigencia", "responsable_validacion", "observaciones_formula"];
setup(consumoPrueba, "AD", "Consumo detallado por prueba, analito y equipo", "Una fila por artículo usado. Tabla obligatoria para documentar prueba, analito, equipo, método, etapa, cantidad por determinación, repetición, QC, lote preferente y vigencia de la fórmula.", consumoPruebaHeaders, [12,28,24,18,20,24,24,24,20,16,16,18,18,22,24,20,18,24,18,12,36,18,20,20,18,28,18,18,24,36]); tenant(consumoPrueba); listValidation(consumoPrueba, "E6:E205", ["REACTIVO", "CONTROL_QC", "CALIBRADOR", "CONSUMIBLE", "REFACCION", "INSUMO_GENERAL"]); listValidation(consumoPrueba, "J6:K205", ["Sí", "No"]); listValidation(consumoPrueba, "O6:O205", ["Sí", "No"]); listValidation(consumoPrueba, "T6:T205", ["Sí", "No"]); consumoPrueba.getRange("S6:S205").format.numberFormat = "yyyy-mm-dd"; consumoPrueba.getRange("AA6:AB205").format.numberFormat = "yyyy-mm-dd"; consumoPrueba.getRange("L6:L205").format.numberFormat = "#,##0.0000"; consumoPrueba.getRange("N6:N205").format.numberFormat = "#,##0.0000"; consumoPrueba.getRange("V6:V205").format.numberFormat = "#,##0.0000"; consumoPrueba.getRange("Y6:Y205").format.numberFormat = "#,##0.0000";

const pruebasHeaders = ["tenant_id", "codigo_prueba", "nombre_prueba", "sinonimos", "analitos", "tipo_muestra", "contenedor", "volumen_muestra", "unidad_volumen", "equipo_principal", "metodo", "area", "tiempo_proceso_min", "temperatura_proceso", "requiere_calibracion", "frecuencia_calibracion", "requiere_qc", "frecuencia_qc", "repeticiones_permitidas", "criterio_repeticion", "resultado_critico", "sop_documento", "version_sop", "validado_por", "fecha_validacion", "activo", "observaciones"];
setup(pruebas, "AA", "Catálogo maestro de pruebas y analitos", "Una fila por prueba LIMS. Esta hoja define la prueba, muestra, equipo, método, controles, calibración, repeticiones y documento vigente antes de ligar consumos.", pruebasHeaders, [12,18,28,32,28,22,20,18,18,24,24,20,18,20,22,22,18,18,22,30,22,28,16,24,18,12,36]); tenant(pruebas); listValidation(pruebas, "O6:O205", ["Sí", "No"]); listValidation(pruebas, "Q6:Q205", ["Sí", "No"]); listValidation(pruebas, "Z6:Z205", ["Sí", "No"]); pruebas.getRange("Y6:Y205").format.numberFormat = "yyyy-mm-dd";
const catalogoPruebasPrefill = limsExamenes.slice(0, 200).map(row => [
  1,
  row.Codigo,
  row.Descripcion || row.Titulo,
  row.Abreviatura,
  [...new Set(limsPerfilRows.filter(p => p.abreviaturaExamen === row.Abreviatura || p.codigoExamen === row.Codigo).map(p => `${p.codigoAnalito}: ${p.descripcionAnalito}`))].join("; "),
  "SUERO / confirmar recipiente",
  "",
  "",
  "",
  "",
  row.Metodo,
  "",
  row.Tiempo_proceso,
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "Sí",
  "Precargado desde datos_lims/Examenes.csv; confirmar prueba, equipo, reactivos, consumo y QC."
]);
if (catalogoPruebasPrefill.length) pruebas.getRange(`A6:AA${5 + catalogoPruebasPrefill.length}`).values = catalogoPruebasPrefill;
pruebas.getRange(`A6:AA${5 + catalogoPruebasPrefill.length}`).format.fill = C.blue;
pruebas.getRange(`J6:J${5 + catalogoPruebasPrefill.length}`).format.fill = C.yellow;
pruebas.getRange(`O6:X${5 + catalogoPruebasPrefill.length}`).format.fill = C.yellow;

const reactivoPrefill = [
  [1, "RF-REACTIVO-CONFIRMAR", "Reactivo Factor reumatoide", "Factor reumatoide", "", "", "85/FR", "Confirmar presentación", "UNIDAD", "", "", "", "", "", "", "", "", "", "", "Factor reumatoide", "Precargado desde Parametros.csv; confirmar marca, fabricante, lote, costo y equipo.", "REACTIVO", "FR", "", "Inmunoturbidimetría", "REACTIVO_PRINCIPAL", "", "", "", "", "", "PENDIENTE", "PENDIENTE", "PENDIENTE", "PENDIENTE_VALIDAR"],
  ...[
    ["TIFICO O", "TO", "Tífico O"], ["TIFICO H", "TH", "Tífico H"], ["PARATIFICO B", "PB", "Paratífico B"], ["PARATIFICO A", "PA", "Paratífico A"], ["BRUCELLA ABORTUS", "BA", "Brucella abortus"], ["PROTEUS", "PT", "Proteus"],
  ].map(([codigo, abreviatura, nombre]) => [1, `RF-${codigo.replace(/\s+/g, "-")}-CONFIRMAR`, `Reactivo ${nombre}`, "Reacciones febriles", "", "", codigo, "Confirmar presentación", "UNIDAD", "", "", "", "", "", "", "", "", "", "", "Reacciones febriles", "Precargado desde Examenes_Perfil.csv y Parametros.csv; confirmar marca, fabricante, lote, costo y equipo.", "REACTIVO", abreviatura, "", "Inmunoaglutinación", "ANTIGENO_REACCIONES_FEBRILES", "", "", "", "", "", "PENDIENTE", "PENDIENTE", "PENDIENTE", "PENDIENTE_VALIDAR"]),
];
reactivos.getRange(`A6:AI${5 + reactivoPrefill.length}`).values = reactivoPrefill;
reactivos.getRange(`A6:AI${5 + reactivoPrefill.length}`).format.fill = C.orange;

const consumiblePrefill = [
  [1, "TUBO-DORADO-CONFIRMAR", "Tubo dorado", "TUBO_RECOLECCION", "", "", "Confirmar capacidad", "UNIDAD", "", "", "", "Toma de muestra / suero", "", "", "", "UNIDAD", "No", "", "", "", "Fuente: Examenes.csv/Parametros.csv y regla operativa confirmada por usuario; completar marca, lote, caducidad y cantidad.", "MUESTRA", "", "", "", "Sí", "PENDIENTE", "PENDIENTE_VALIDAR", "", ""],
  [1, "TUBO-LILA-CONFIRMAR", "Tubo lila EDTA", "TUBO_RECOLECCION", "", "", "Confirmar capacidad", "UNIDAD", "", "", "", "Muestra plasma/EDTA", "", "", "", "UNIDAD", "No", "", "", "", "Muestra documentada para estudios con EDTA; completar marca, lote, caducidad y cantidad.", "MUESTRA", "", "", "", "Sí", "PENDIENTE", "PENDIENTE_VALIDAR", "", ""],
  [1, "TUBO-VERDE-CONFIRMAR", "Tubo verde heparina", "TUBO_RECOLECCION", "", "", "Confirmar capacidad", "UNIDAD", "", "", "", "Muestra plasma/heparina", "", "", "", "UNIDAD", "No", "", "", "", "Muestra documentada para estudios especiales; completar marca, lote, caducidad y cantidad.", "MUESTRA", "", "", "", "Sí", "PENDIENTE", "PENDIENTE_VALIDAR", "", ""],
  [1, "AGUJA-CONFIRMAR", "Aguja de toma", "MATERIAL_TOMA", "", "", "Confirmar calibre", "UNIDAD", "", "", "", "Toma de muestra", "", "", "", "UNIDAD", "Sí", "", "", "", "Regla operativa confirmada por usuario; definir si se controla por pieza o uso libre.", "MUESTRA", "", "", "", "No", "PENDIENTE", "PENDIENTE_VALIDAR", "", ""],
  [1, "PUNTILLA-CONFIRMAR", "Puntilla", "CONSUMIBLE_ANALITICO", "", "", "Confirmar volumen", "UNIDAD", "", "", "", "Procesamiento analítico", "", "", "", "UNIDAD", "No", "", "", "", "Regla operativa confirmada por usuario; ligar a equipo y analito cuando se confirme el modelo.", "ANALITO", "", "", "", "Sí", "PENDIENTE", "PENDIENTE_VALIDAR", "", ""],
  [1, "TORUNDA-CONFIRMAR", "Torunda", "MATERIAL_TOMA", "", "", "Confirmar presentación", "UNIDAD", "", "", "", "Toma de muestra", "", "", "", "UNIDAD", "Sí", "", "", "", "Uso libre por política actual; completar marca y presentación si se decide controlar.", "MUESTRA", "", "", "", "No", "PENDIENTE", "PENDIENTE_VALIDAR", "", ""],
  [1, "ALCOHOL-CONFIRMAR", "Alcohol", "MATERIAL_TOMA", "", "", "Confirmar concentración/presentación", "ML", "", "", "", "Toma de muestra", "", "", "", "ML", "No", "", "", "", "Uso libre por política actual; completar marca, concentración y presentación.", "MUESTRA", "", "", "", "No", "PENDIENTE", "PENDIENTE_VALIDAR", "", ""],
];
consumibles.getRange(`A6:AD${5 + consumiblePrefill.length}`).values = consumiblePrefill;
consumibles.getRange(`A6:AD${5 + consumiblePrefill.length}`).format.fill = C.orange;

const equiposPrefill = [
  [1, "EQUIPO-RF-CONFIRMAR", "Equipo/proceso de reacciones febriles por confirmar", "", "", "", "Laboratorio", "Inmunología", "AGLUTINACION", "", "PENDIENTE", "Aglutinación en placa", "Tífico O; Tífico H; Paratífico B; Paratífico A; Brucella abortus; Proteus", "Reacciones febriles", "Puntillas; tubos; material de toma", "Antígenos de reacciones febriles", "", "", "", "", "", "", "", "", "", "PENDIENTE", "", "Fuente: Examenes.csv/Examenes_Perfil.csv; registrar nombre, marca, modelo y serie del equipo real."],
  [1, "EQUIPO-QC-CONFIRMAR", "Analizador de química clínica por confirmar", "", "", "", "Laboratorio", "Bioquímica clínica", "ANALIZADOR_QUIMICA", "", "PENDIENTE", "Colorimétrico Automatizado; Enzimático Automatizado", "Glucosa; Urea; Creatinina sérica; Colesterol; Triglicéridos; Ácido úrico", "QSC; química clínica", "Puntillas; tubos; calibradores; controles", "Reactivos por analito", "", "", "", "", "", "", "", "", "", "PENDIENTE", "", "Fuente: Parametros.csv; completar equipo físico, marca, modelo, serie e interfaz."],
];
equipos.getRange(`A6:AB${5 + equiposPrefill.length}`).values = equiposPrefill;
equipos.getRange(`A6:AB${5 + equiposPrefill.length}`).format.fill = C.orange;

const equiposHeaders = ["tenant_id", "codigo_equipo", "nombre_equipo", "marca", "modelo", "numero_serie", "ubicacion", "area", "tipo_equipo", "software_version", "interfaz_lims", "metodos_soportados", "analitos_soportados", "pruebas_soportadas", "consumibles_requeridos", "reactivos_requeridos", "calibradores_requeridos", "controles_requeridos", "mantenimiento_preventivo", "ultima_calibracion", "proxima_calibracion", "ultimo_mantenimiento", "proximo_mantenimiento", "proveedor_servicio", "manual_documento", "estado", "responsable", "observaciones"];
setup(equipos, "AB", "Catálogo maestro de equipos e interfaces", "Una fila por equipo. Ligar marca, modelo, serie, ubicación, pruebas, analitos, reactivos, consumibles, controles, calibración, mantenimiento e interfaz LIMS.", equiposHeaders, [12,18,28,20,20,22,20,20,22,18,20,32,32,32,32,32,28,28,24,18,18,20,20,24,28,16,24,36]); tenant(equipos); listValidation(equipos, "K6:K205", ["Sí", "No", "PENDIENTE"]); listValidation(equipos, "Z6:Z205", ["ACTIVO", "INACTIVO", "MANTENIMIENTO", "BAJA"]); equipos.getRange("T6:W205").format.numberFormat = "yyyy-mm-dd";

const proveedoresHeaders = ["tenant_id", "codigo_proveedor", "razon_social", "nombre_comercial", "rfc", "contacto", "telefono", "correo", "domicilio", "tipo_suministro", "marcas_distribuidas", "condiciones_pago", "tiempo_entrega_dias", "documentos_requeridos", "calificacion", "fecha_ultima_evaluacion", "activo", "observaciones"];
setup(proveedores, "R", "Catálogo maestro de proveedores", "Una fila por proveedor. Usar el mismo codigo_proveedor en capturas, lotes, facturas y documentos para mantener trazabilidad.", proveedoresHeaders, [12,20,30,26,18,24,18,30,36,24,34,24,20,30,16,20,12,36]); tenant(proveedores); listValidation(proveedores, "Q6:Q205", ["Sí", "No"]); proveedores.getRange("P6:P205").format.numberFormat = "yyyy-mm-dd";

const conversionHeaders = ["tenant_id", "codigo_interno", "nombre_articulo", "tipo_articulo", "presentacion_compra", "unidad_presentacion", "cantidad_contenida", "unidad_contenida", "unidad_descuento", "factor_conversion", "rendimiento_teorico", "rendimiento_real", "merma_porcentaje", "metodo_calculo", "validado_por", "fecha_validacion", "activo", "observaciones"];
setup(conversiones, "R", "Conversiones de presentación y rendimiento", "Una fila por artículo y presentación. Sirve para convertir caja, kit, frasco, mL, pruebas, piezas o determinaciones y permitir descuentos correctos.", conversionHeaders, [12,20,30,20,24,20,20,20,20,18,22,20,18,32,24,18,12,36]); tenant(conversiones); listValidation(conversiones, "Q6:Q205", ["Sí", "No"]); conversiones.getRange("P6:P205").format.numberFormat = "yyyy-mm-dd"; conversiones.getRange("J6:M205").format.numberFormat = "#,##0.0000";

const controlHeaders = ["tenant_id", "hoja_origen", "codigo_interno", "nombre_articulo", "tipo_articulo", "campo_obligatorio_faltante", "valor_no_aplica_justificado", "documento_pendiente", "lote_pendiente", "prueba_pendiente", "equipo_pendiente", "consumo_pendiente", "responsable", "fecha_compromiso", "estado_revision", "observaciones"];
setup(controlCarga, "P", "Control de completitud antes de importar", "Usar una fila por pendiente detectado. Ningún artículo debe pasar a producción si no están resueltos o justificados sus datos obligatorios, lote, documentos, prueba, equipo y consumo.", controlHeaders, [12,24,20,30,20,32,30,28,20,28,24,24,24,18,20,40]); tenant(controlCarga); listValidation(controlCarga, "O6:O205", ["PENDIENTE", "EN_REVISION", "CORREGIDO", "JUSTIFICADO", "BLOQUEADO"]); controlCarga.getRange("N6:N205").format.numberFormat = "yyyy-mm-dd";

const prefillPruebasHeaders = ["tenant_id", "codigo_prueba", "nombre_prueba", "abreviatura", "metodo_catalogo", "tiempo_proceso", "permite_venta_directa", "fuente", "reactivo_principal_a_confirmar", "equipo_a_confirmar", "consumo_por_determinacion", "consumo_por_repeticion", "qc_requerido", "calibracion_requerida", "estado_precarga", "observaciones"];
setup(prefillPruebas, "P", "Precarga de pruebas desde catálogo LIMS", "Fuente de datos del sistema. No contiene reactivos ni consumos inventados. Completar únicamente los campos amarillos y después ligar cada prueba a consumo_por_prueba.", prefillPruebasHeaders, [12,18,32,18,30,18,22,34,30,24,24,24,18,22,18,44], [], Math.max(205, 5 + limsExamenes.length));
const prefillPruebasRows = limsExamenes.map(row => [1, row.Codigo, row.Descripcion || row.Titulo, row.Abreviatura, row.Metodo, row.Tiempo_proceso, row.Permite_venta_directa, "datos_lims/Examenes.csv", "", "", "", "", "", "", "PENDIENTE_CONFIRMACION", "Confirmar reactivo, equipo, cantidad, repetición, QC y calibración antes de importar."]);
if (prefillPruebasRows.length) {
  prefillPruebas.getRange(`A6:P${5 + prefillPruebasRows.length}`).values = prefillPruebasRows;
  prefillPruebas.getRange(`A6:P${5 + prefillPruebasRows.length}`).format.fill = C.blue;
  prefillPruebas.getRange(`I6:N${5 + prefillPruebasRows.length}`).format.fill = C.yellow;
}
listValidation(prefillPruebas, `O6:O${5 + Math.max(205, limsExamenes.length)}`, ["PENDIENTE_CONFIRMACION", "REVISADA", "LISTA_PARA_LIGAR", "BLOQUEADA"]);

const prefillAnalitosHeaders = ["tenant_id", "id_parametro", "codigo", "abreviatura", "descripcion_analito", "departamento", "tipo_muestra", "metodo", "unidades", "tipo_resultado", "resultado_opciones", "decimales", "tiempo_proceso", "es_producto", "fuente", "prueba_lims_a_ligar", "reactivo_a_ligar", "equipo_a_ligar", "cantidad_a_confirmar", "estado_precarga"];
setup(prefillAnalitos, "T", "Precarga de analitos y parámetros LIMS", "806 parámetros del catálogo actual. Los campos de prueba, reactivo, equipo y cantidad quedan pendientes de confirmación; no se inventan relaciones.", prefillAnalitosHeaders, [12,16,18,18,32,24,22,30,18,18,28,14,18,16,28,28,28,24,24,22], [], Math.max(205, 5 + limsParametros.length));
const prefillAnalitosRows = limsParametros.map(row => [1, row.Id_parametro, row.Codigo, row.Abreviatura, row.Descripcion, row.Departamento, row.Tipo_muestra, row.Metodo, row.Unidades, row.Tipo_resultado, row.Resultado_opciones, row.Decimales, row.Tiempo_proceso, row.Es_Producto, "datos_lims/Parametros.csv", "", "", "", "", "PENDIENTE_LIGAR"]);
if (prefillAnalitosRows.length) {
  prefillAnalitos.getRange(`A6:T${5 + prefillAnalitosRows.length}`).values = prefillAnalitosRows;
  prefillAnalitos.getRange(`A6:T${5 + prefillAnalitosRows.length}`).format.fill = C.blue;
  prefillAnalitos.getRange(`P6:S${5 + prefillAnalitosRows.length}`).format.fill = C.yellow;
}
listValidation(prefillAnalitos, `T6:T${5 + Math.max(205, limsParametros.length)}`, ["PENDIENTE_LIGAR", "REVISADO", "LISTO_PARA_CONSUMO", "BLOQUEADO"]);

const prefillTarifasHeaders = ["tenant_id", "tipo_tarifa", "codigo", "abreviatura", "descripcion", "importe", "fuente", "codigo_prueba_o_paquete", "precio_confirmado", "observaciones"];
setup(prefillTarifas, "J", "Precarga de lista de precios LIMS", "Paquetes, perfiles y estudios encontrados en la lista de precios. Confirmar vigencia y ligar al código real antes de importar.", prefillTarifasHeaders, [12,18,20,20,48,16,34,28,18,40], [], Math.max(205, 5 + limsTarifas.length));
const prefillTarifasRows = limsTarifas.map(row => [1, row.tipo, row.codigo, row.abreviatura, row.descripcion, row.importe, "datos_lims/Tarifa_estudios de laboratorio.csv", row.codigo, "", "Confirmar vigencia, convenio y correspondencia con catálogo LIMS."]);
if (prefillTarifasRows.length) {
  prefillTarifas.getRange(`A6:J${5 + prefillTarifasRows.length}`).values = prefillTarifasRows;
  prefillTarifas.getRange(`A6:J${5 + prefillTarifasRows.length}`).format.fill = C.blue;
  prefillTarifas.getRange(`H6:I${5 + prefillTarifasRows.length}`).format.fill = C.yellow;
}
prefillTarifas.getRange(`F6:F${5 + prefillTarifasRows.length}`).format.numberFormat = "$#,##0.00";

const consumoAnalitoHeaders = ["tenant_id", "codigo_analito", "analito", "departamento", "tipo_muestra", "metodo", "unidad_resultado", "prueba_o_paquete_comercial_referencia", "codigo_reactivo", "nombre_reactivo", "marca", "fabricante", "presentacion", "lote", "caducidad", "equipo", "fase_proceso", "volumen_existencia", "unidad_existencia", "consumo_por_determinacion", "unidad_consumo", "consumo_por_repeticion", "consumo_por_qc", "consumo_por_calibracion", "factor_conversion", "rendimiento_teorico", "rendimiento_real", "stock_minimo", "stock_actual", "responsable_validacion", "estado_ligado", "regla_inventario", "observaciones"];
setup(consumoAnalitos, "AG", "Consumo e inventario por analito", "Esta es la hoja operativa principal: una fila por analito que realmente consume material. No inventariar quimica de 3, perfil o paquete; capturar por separado glucosa, urea, creatinina, colesterol, etc.", consumoAnalitoHeaders, [12,18,28,24,22,30,18,36,20,32,20,24,24,18,16,24,20,20,18,26,20,26,20,24,18,22,20,16,16,24,20,22,40], [], Math.max(205, 5 + limsParametros.length));
const consumoAnalitoRows = limsParametros.map(row => [
  1,
  row.Codigo,
  row.Descripcion,
  row.Departamento,
  row.Tipo_muestra,
  row.Metodo,
  row.Unidades,
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
  "PENDIENTE_LIGAR",
  "INVENTARIAR_ANALITO",
  "Precargado desde Parametros.csv. Ligar reactivo, equipo y cantidades reales; el paquete comercial solo sirve como referencia de venta."
]);
if (consumoAnalitoRows.length) {
  consumoAnalitos.getRange(`A6:AG${5 + consumoAnalitoRows.length}`).values = consumoAnalitoRows;
  consumoAnalitos.getRange(`A6:AG${5 + consumoAnalitoRows.length}`).format.fill = C.blue;
  consumoAnalitos.getRange(`H6:AF${5 + consumoAnalitoRows.length}`).format.fill = C.yellow;
}
listValidation(consumoAnalitos, `AE6:AE${5 + Math.max(205, limsParametros.length)}`, ["PENDIENTE_LIGAR", "REVISADO", "LISTO_PARA_DESCUENTO", "BLOQUEADO"]);
consumoAnalitos.getRange(`O6:O${5 + consumoAnalitoRows.length}`).format.numberFormat = "yyyy-mm-dd";
consumoAnalitos.getRange(`T6:X${5 + consumoAnalitoRows.length}`).format.numberFormat = "#,##0.0000";
consumoAnalitos.getRange(`Y6:AA${5 + consumoAnalitoRows.length}`).format.numberFormat = "#,##0.0000";

const bomHeaders = ["tenant_id", "codigo_prueba_comercial", "prueba_comercial", "nivel_consumo", "codigo_analito", "analito", "codigo_articulo", "articulo", "tipo_articulo", "marca", "equipo", "etapa_proceso", "cantidad_por_determinacion", "cantidad_por_repeticion", "cantidad_por_qc", "cantidad_por_calibracion", "unidad_consumo", "aplicar_una_vez_por_muestra", "aplicar_una_vez_por_orden", "factor_conversion", "lote_preferente", "estado_ligado", "responsable_validacion", "observaciones"];
setup(bomConsumo, "X", "BOM de consumo por prueba, muestra y analito", "No inventar datos. Ejemplo de regla: tubo dorado/aguja/torunda/alcohol = MUESTRA, una vez por orden; glucosa, urea, creatinina y los demás analitos = ANALITO, una fila independiente. QSC es referencia comercial, nunca artículo de inventario.", bomHeaders, [12,24,28,18,18,28,20,30,18,18,24,20,24,24,18,22,18,24,22,18,18,20,24,42]); tenant(bomConsumo); listValidation(bomConsumo, "D6:D205", ["MUESTRA", "ANALITO", "QC", "CALIBRACION"]); listValidation(bomConsumo, "I6:I205", ["REACTIVO", "CONTROL_QC", "CALIBRADOR", "CONSUMIBLE", "REFACCION", "INSUMO_GENERAL"]); listValidation(bomConsumo, "R6:S205", ["Sí", "No"]); listValidation(bomConsumo, "V6:V205", ["PENDIENTE_LIGAR", "REVISADO", "LISTO_PARA_DESCUENTO", "BLOQUEADO"]); bomConsumo.getRange("M6:P205").format.numberFormat = "#,##0.0000";
const bomExamples = [
  [1, "QSC-CONFIRMAR", "QSC (confirmar código real)", "MUESTRA", "", "", "", "Tubo dorado", "CONSUMIBLE", "", "", "TOMA_MUESTRA", 1, 0, 0, 0, "UNIDAD", "Sí", "Sí", 1, "", "PENDIENTE_LIGAR", "", "Ejemplo operativo: no importar hasta confirmar presentación y unidad."],
  [1, "QSC-CONFIRMAR", "QSC (confirmar código real)", "MUESTRA", "", "", "", "Aguja", "CONSUMIBLE", "", "", "TOMA_MUESTRA", 1, 0, 0, 0, "UNIDAD", "Sí", "Sí", 1, "", "PENDIENTE_LIGAR", "", "Uso común de muestra."],
  [1, "QSC-CONFIRMAR", "QSC (confirmar código real)", "MUESTRA", "", "", "", "Torunda", "CONSUMIBLE", "", "", "TOMA_MUESTRA", 1, 0, 0, 0, "UNIDAD", "Sí", "Sí", 1, "", "PENDIENTE_LIGAR", "", "Uso libre; registrar cantidad real si se decide controlar."],
  [1, "QSC-CONFIRMAR", "QSC (confirmar código real)", "MUESTRA", "", "", "", "Alcohol", "INSUMO_GENERAL", "", "", "TOMA_MUESTRA", 1, 0, 0, 0, "UNIDAD", "Sí", "Sí", 1, "", "PENDIENTE_LIGAR", "", "Uso libre; no forzar descuento por analito."],
  [1, "QSC-CONFIRMAR", "QSC (confirmar código real)", "ANALITO", "GLU-CONFIRMAR", "Glucosa (confirmar código LIMS)", "", "", "REACTIVO", "", "", "ANALISIS", 0, 0, 0, 0, "", "No", "No", 1, "", "PENDIENTE_LIGAR", "", "Capturar consumo real por determinación."],
  [1, "QSC-CONFIRMAR", "QSC (confirmar código real)", "ANALITO", "UREA-CONFIRMAR", "Urea (confirmar código LIMS)", "", "", "REACTIVO", "", "", "ANALISIS", 0, 0, 0, 0, "", "No", "No", 1, "", "PENDIENTE_LIGAR", "", "Una fila independiente; no inventariar QSC."],
  [1, "QSC-CONFIRMAR", "QSC (confirmar código real)", "ANALITO", "CREA-CONFIRMAR", "Creatinina (confirmar código LIMS)", "", "", "REACTIVO", "", "", "ANALISIS", 0, 0, 0, 0, "", "No", "No", 1, "", "PENDIENTE_LIGAR", "", "Una fila independiente; completar los otros analitos QSC igual."],
];
bomConsumo.getRange("A6:X12").values = bomExamples; bomConsumo.getRange("A6:X12").format.fill = C.orange;

const costeoHeaders = ["tenant_id", "codigo_prueba_comercial", "prueba_comercial", "codigo_analito", "analito", "tipo_ejecucion", "codigo_articulo", "articulo", "cantidad", "unidad", "costo_unitario_lote", "costo_determinacion", "costo_repeticion", "costo_qc", "costo_calibracion", "costo_comun_muestra", "costo_total_ejecucion", "precio_venta_o_ingreso_asignado", "margen_materiales", "orden_id", "paciente_id", "repeticion_id", "lote", "fecha", "validado_por", "observaciones"];
setup(costeoPrueba, "Z", "Costeo por prueba, repetición y paciente", "El sistema debe congelar el costo desde el lote consumido. Una repetición es una ejecución adicional; el ingreso de un paquete se conserva a nivel orden y solo se asigna por analito con una regla financiera documentada.", costeoHeaders, [12,24,28,18,28,18,20,30,14,16,20,20,20,16,18,20,22,26,20,16,16,18,18,18,24,42]); tenant(costeoPrueba); listValidation(costeoPrueba, "F6:F205", ["INICIAL", "REPETICION", "QC", "CALIBRACION"]); costeoPrueba.getRange("K6:S205").format.numberFormat = "$#,##0.0000";

for (const [sheet, name] of [[lists, "Listas y definiciones"], [readme, "LEEME"], [altaNuevo, "alta_nuevo_articulo"], [catalogoLab, "catalogo_lab"], [lotesLab, "lotes_lab"], [catalogoGeneral, "catalogo_general"], [lotesGeneral, "lotes_general"], [consumoLims, "consumo_lims"], [documentos, "documentos"], [reactivos, "captura_reactivos"], [controlesQc, "captura_controles_qc"], [calibradores, "captura_calibradores"], [consumibles, "captura_consumibles"], [refacciones, "captura_refacciones"], [insumosGenerales, "captura_insumos_generales"], [consumoPrueba, "consumo_por_prueba"], [pruebas, "catalogo_pruebas"], [equipos, "catalogo_equipos"], [proveedores, "catalogo_proveedores"], [conversiones, "conversiones_unidades"], [controlCarga, "control_completitud"], [prefillPruebas, "prefill_pruebas_lims"], [prefillAnalitos, "prefill_analitos_lims"], [prefillTarifas, "prefill_tarifas_lims"], [consumoAnalitos, "consumo_por_analito"], [bomConsumo, "bom_consumo_prueba"], [costeoPrueba, "costeo_por_prueba"]]) {
  const preview = await wb.render({ sheetName: name, range: "A1:H18", scale: 1, format: "png" });
  await fs.writeFile(`${outputDir}/${name}.png`, new Uint8Array(await preview.arrayBuffer()));
}
const inspect = await wb.inspect({ kind: "table", range: "lotes_lab!A1:AA12", include: "values,formulas", tableMaxRows: 12, tableMaxCols: 27, tableMaxCellChars: 80 });
await fs.writeFile(`${outputDir}/inspect_lotes_lab.ndjson`, inspect.ndjson ?? String(inspect));
const formulaErrors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
await fs.writeFile(`${outputDir}/formula_errors.ndjson`, formulaErrors.ndjson ?? String(formulaErrors));
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(`${outputDir}/Plantilla_Carga_Reactivos_Insumos_Prislab.xlsx`);
console.log(JSON.stringify({ output: `${outputDir}/Plantilla_Carga_Reactivos_Insumos_Prislab.xlsx`, errors: formulaErrors.ndjson }));
