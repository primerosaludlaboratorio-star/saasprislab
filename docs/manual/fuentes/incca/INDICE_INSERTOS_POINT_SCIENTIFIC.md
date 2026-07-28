# Índice de insertos Point Scientific para INCCA

## Estado

- Fuente original: `C:\Users\jonil\Downloads\INSERTOS POINTE SCIENTIFIC`
- Copia canónica del repositorio: `docs/manual/fuentes/incca/point_scientific/`
- Documentos integrados: 29 PDF
- Uso: referencia técnica para métodos, reactivos, controles, calibradores, alertas, interferencias y capacitación.
- Los insertos no modifican por sí mismos el catálogo ni la configuración productiva del INCCA.

## Documentos disponibles

- `ACIDO URICO.pdf`
- `ALBUMINA.pdf`
- `ALT.pdf`
- `AMILASA.pdf`
- `Amonio Reagent.pdf`
- `AST.pdf`
- `AUTO HDL COLESTEROL.pdf`
- `AUTO LDL COLESTEROL.pdf`
- `BILIRRUBINA DIRECTA.pdf`
- `BILIRRUBINA TOTAL.pdf`
- `CALCIO 2 PARTES.pdf`
- `CALCIO ARSENAZO.pdf`
- `CALIBRADOR AUTO HDL-LDL COLESTEROL.pdf`
- `COLESTEROL.pdf`
- `CREATINA KINASA.pdf`
- `CREATININA.pdf`
- `DESHIDROGENASA LACTICA.pdf`
- `FOSFATASA ACIDA.pdf`
- `FOSFATASA ALCALINA.pdf`
- `GAMA GLUTAMIL TRANSFERASA.pdf`
- `GLUCOSA.pdf`
- `HbA1c.pdf`
- `HDL COLESTEROL PEG POINTE.pdf`
- `MAGNESIO.pdf`
- `MICROALBUMINA.pdf`
- `MICROPROTEINA.pdf`
- `NITROGENO DE UREA.pdf`
- `PROTEINA TOTAL.pdf`
- `TRIGLICERIDOS.pdf`

## Integración pendiente

Cada inserto debe asociarse explícitamente con el método exacto del INCCA, el analito del catálogo, el reactivo/lote, el control, el calibrador, el volumen programado, las unidades, los rangos y las reglas de interferencia. Esa asociación se realizará únicamente cuando la correspondencia esté validada; no se inferirá solo por el nombre del PDF.

La carpeta revisada no contiene archivos separados de interfaces ni material de capacitación. Si existen en otra ubicación, deben incorporarse como fuentes independientes y conservar su versión y fecha.

## Manuales INCCA incorporados

Los manuales originales se conservan en `docs/manual/fuentes/incca/manuales/`:

- `Manual_de_Usuario_InCCA_2015_v2.09.05.pdf`: manual operativo completo del instrumento, instalación, configuración, operación, mantenimiento y resolución de problemas.
- `InCCA Software Automatic Bidirectional LIS Connectivity rev2 - copia.pdf`: especificación de conectividad bidireccional LIS, procesos de entrada/salida y parámetros de integración.

Estos documentos son la referencia para diseñar la interfase INCCA-LIMS, documentar la capacitación del personal y definir diagnósticos técnicos. Antes de activar una regla automática se debe validar el método contra el nombre exacto del equipo, el catálogo del laboratorio y la configuración vigente.
