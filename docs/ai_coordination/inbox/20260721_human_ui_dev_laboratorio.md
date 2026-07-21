# Auditoria humana UI de Laboratorio en desarrollo — 2026-07-21

## Alcance

Primera corrida de interacción visible en navegador contra el checkout QA de desarrollo:

- Base: `http://127.0.0.1:8000`
- Usuario QA: `admin`
- Base de datos: SQLite local del checkout de desarrollo
- Producción: **no involucrada**

## Evidencia ejecutada

| Flujo | Resultado | Evidencia observable |
|---|---|---|
| Login | OK | Redirección a dashboard autenticado |
| Abrir recepción de Laboratorio | OK | Pantalla de registro de orden cargada |
| Buscar paciente por nombre | OK después del ajuste local | `Carlos Auditoria Consultorio` apareció en la lista |
| Seleccionar paciente | OK | Paciente `id=21` quedó seleccionado y se mostró la tarjeta clínica |
| Buscar estudio | OK | La búsqueda de `Glucosa` y `Urea` mostró resultados |
| Agregar varios estudios | OK | Se agregaron `GLU` y `URE` |
| Calcular cobro exacto | OK | Subtotal/total `$145.00`, cobrado `$145.00`, saldo `$0.00` |
| Confirmar y persistir orden | OK | Tras aceptar el modal, se crearon `LAB-20260721-001` y `LAB-20260721-002` |
| Toma de muestra | OK | `LAB-20260721-002` inició y finalizó con checklist manual 6/6 |
| Captura de resultado | OK | `GLU=95` se guardó en `ResultadoParametro` |
| Validación humana | OK | La acción canónica `VALIDAR` dejó la orden en `VALIDADO` y generó PDF |
| Entrega | OK | La bandeja marcó `LAB-20260721-002` como `ENTREGADO` |
| CxC parcial | OK | `LAB-20260721-003`: total `$85.00`, abono `$40.00`, saldo `$45.00`, motivo y nota trazables |
| Cortesía | OK después de corrección | `LAB-20260721-004`: subtotal `$85.00`, total/abono/saldo `$0.00`; la vista ya no muestra saldo cobrable ficticio |
| Toma de cortesía | OK | La orden 11 completó checklist manual 6/6 y pasó a `TOMA_REALIZADA` |
| Envío a Maquila | OK | La UI confirmó el envío; la base QA confirmó `LAB-20260721-004` en `EN_MAQUILA` |
| Valor fuera de rango y justificación QFB | OK después de corrección | `LAB-20260721-005`: `GLUCOSA=500`; SweetAlert sustituyó `prompt()`, exigió comentario y el servidor rechazó API sin justificación antes de generar PDF |
| Rechazo/repetición | OK después de corrección | `LAB-20260721-006`: el botón pasó el detalle `id=10`, guardó `Hemolizada` y devolvió el detalle a `PENDIENTE_TOMA` |
| Complemento de pago | OK | `LAB-20260721-003`: se registraron `$45.00` adicionales; estado `PAGADO`, anticipo `$85.00`, saldo `$0.00` |
| Cancelación/reembolso | OK después de corrección | `LAB-20260721-006`: se añadió el botón visible, se canceló con motivo y se generó `GastoCaja=-85.00` |
| Control de Calidad | Parcial avanzado | Se corrigió `parametros_lista_json`; se registraron 3 lecturas `GLUCOSA` (100/101/99) del lote `QA-GLU-2026` y el histórico/Levey-Jennings básico cargan. Westgard CCI estricto requiere fixtures del canal CCI separado |

## Hallazgos y límites

1. La primera lectura del botón de confirmación parecía fallar porque la prueba no aceptó el modal; al aceptarlo, la orden se persistió correctamente.
2. Se hizo determinista la carga local de SweetAlert2 en `core/templates/base.html` para no depender de CDN.
3. Se corrigió `core/services/validador_ia.py` para usar la relación `analito` real de `ResultadoParametro`.
4. Se reemplazó el `prompt()` por un diálogo SweetAlert con textarea y se añadió el candado de servidor `JUSTIFICACION_QC_REQUERIDA` antes de generar PDF.
5. La Worklist ahora envía el `DetalleOrden` correcto al rechazo; Recepción expone el botón de cancelación y genera el movimiento negativo de caja.
4. El avance de Monitor sin PDF está diseñado para devolver `400` controlado en vez de `500`; la prueba focalizada automática quedó en ejecución/harness y no se cuenta como verde hasta obtener salida final.
5. `UREA` aparece como analito calculado con fórmula `BUN*2.14`; no es capturable manualmente sin el analito dependiente `BUN`.
6. El servidor QA reprodujo `503` en `/favicon.ico` por `ValueError: unsupported format` dentro de Sentinel; es un residual operativo separado del flujo clínico.

## Validaciones técnicas complementarias

- `manage.py check`: OK.
- `manage.py makemigrations --check --noinput`: OK.
- Orden QA final verificada: `id=9`, folio `LAB-20260721-002`, estado `ENTREGADO`.
- Resultado persistido: analito `GLU`, valor `95`, `validado=True`, `aprobado_por_humano=True`.

## Decisión

**Laboratorio permanece ABIERTO.** La ruta feliz, CxC, cortesía, toma, Maquila, fuera de rango con justificación, rechazo/repetición, complemento de pago, cancelación/reembolso y Levey-Jennings básico funcionan en QA. Faltan Westgard CCI estricto, UREA/BUN y la segunda auditoría humana completa.

## Próximo criterio de avance

Continuar con la matriz de excepciones y controles sobre datos QA, sin desplegar a producción hasta cerrar esos escenarios y documentar sus evidencias.
