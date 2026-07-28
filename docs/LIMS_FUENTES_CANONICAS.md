# Fuentes canónicas de LIMS y Laboratorio

## Regla operativa

Desde el 28 de julio de 2026, la única fuente editable del catálogo LIMS es el
directorio `datos_lims/`. Los archivos de la raíz o comandos legacy no deben
editarse para corregir el catálogo; solo se conservan por compatibilidad y
deben consumir las fuentes canónicas cuando se ejecuten.

## Archivos y responsabilidad

| Orden | Archivo | Fuente de verdad |
|---|---|---|
| 1 | `Parametros.csv` | Analitos, códigos, abreviaturas, área, muestra, método, unidades y venta individual |
| 2 | `Valores_normalidad.csv` | Rangos por analito, sexo y edad |
| 3 | `Examenes.csv` | Perfiles/estudios comerciales y sus identificadores |
| 4 | `Examenes_Perfil.csv` | Composición de cada perfil por analitos |
| 5 | `Paquetes.csv` | Paquetes comerciales |
| 6 | `Paquetes_Perfil.csv` | Composición de paquetes por prueba o perfil |
| 7 | `Tarifa_estudios de laboratorio.csv` | Precios públicos vigentes |

`tarifas.csv` se conserva como compatibilidad legacy. No es una fuente
independiente: cualquier actualización debe hacerse primero en la tarifa
canónica de `datos_lims/` y después sincronizarse mediante el pipeline LIMS.

## Pipeline único

```text
Parametros + Valores_normalidad
        -> Analito + rangos
Examenes + Examenes_Perfil
        -> PerfilLims + composición
Paquetes + Paquetes_Perfil
        -> PaqueteLims + composición
Tarifa_estudios de laboratorio.csv
        -> PrecioItem
```

Ejecutar la auditoría antes de importar:

```text
python manage.py auditar_fuentes_lims
python manage.py auditar_asignaciones_inventario_lims --empresa-id 1
```

Importar únicamente mediante:

```text
python manage.py ensamblar_lims_v75
```

## Reglas de integridad

- El catálogo es exclusivamente humano; no se aceptan registros caninos,
  equinos, felinos ni veterinarios.
- `Id_parametro`, `Id_examen` y la abreviatura de paquete deben ser únicos.
- Las abreviaturas de analito son la llave clínica prioritaria. Los códigos
  legacy repetidos no se resuelven por posición ni por el primer resultado.
- Toda referencia debe apuntar a un analito, perfil o paquete existente.
- Los rangos superpuestos no se corrigen automáticamente: requieren validación
  clínica documentada para evitar cambiar interpretación de resultados.
- Las entidades veterinarias ya existentes en BD se desactivan del catálogo
  operativo y se conservan para no romper historiales, resultados o auditoría.
- Una fórmula de consumo solo puede ligar un analito y un reactivo de la misma
  empresa; `MUESTRA` no lleva analito y se descuenta una sola vez por orden.
- Los analitos calculados no consumen inventario físico; cualquier fórmula
  física ligada a ellos se reporta como advertencia para revisión.

## Criterio para iniciar interfaces

No se inicia una interfaz nueva hasta que `auditar_fuentes_lims` termine sin
errores y la importación completa termine con cero referencias huérfanas. Las
advertencias de códigos legacy repetidos deben permanecer visibles en el
reporte de auditoría y nunca resolverse silenciosamente.

La auditoría también reporta rangos de edad superpuestos como advertencia
clínica. Esa advertencia no bloquea la integridad técnica, pero sí debe ser
revisada por el químico responsable antes de declarar validados los resultados.
