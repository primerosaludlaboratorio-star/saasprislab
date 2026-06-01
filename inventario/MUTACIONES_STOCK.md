# Puntos de mutación de stock — inventario federado (referencia Fase 1)

Solo silos `inventario` y enlaces documentados. **No incluye farmacia.**

| Ubicación | Silo / modelo afectado |
|-----------|-------------------------|
| `inventario/signals.py` | Lab: `LoteReactivoLab`, `SalidaAnaliticaLab` (FEFO al validar `ResultadoParametro`) |
| `inventario/signals.py` | Generales: `LoteInsumoGeneral`, `LineaValeRequisicion` (fallback vale ENTREGADO) |
| `inventario/views_generales.py` | Generales: entrega de vales (`entregar`, FEFO con `select_for_update`) |
| `inventario/views_consultorio.py` | Consultorio: `LoteInsumoConsultorio` al registrar `SalidaConsumoConsultorio` |
| `inventario/views_traspasos.py` | Traspasos entre silos internos del módulo |
| `inventario/views.py` / `views_compras.py` | Altas de lotes, órdenes de compra, entradas |
| `mantenimiento/signals.py` (si aplica) | Refacciones ligadas a tickets CMMS que tocan inventario lab |

Revisar tras cada cambio en FEFO o nuevas señales.
