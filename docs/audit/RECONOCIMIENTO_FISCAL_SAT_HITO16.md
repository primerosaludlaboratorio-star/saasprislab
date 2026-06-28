# Reconocimiento táctico — Hito 16: Consistencia fiscal SAT / Facturama

**Rol:** Arquitecto de integraciones fiscales (reconocimiento, sin cambios de código).  
**Versión:** 1.0  
**Fecha:** 2026-04-02  
**Alcance de lectura:** `contabilidad/`, `core/models/` (ventas, pacientes, base), `farmacia/` (búsqueda dirigida), `config/settings.py`.

---

## Estado actual

### 1. Ruta del dinero (Lab / Farmacia → CFDI)

- **Modelo fiscal principal:** `contabilidad.models.FacturaCFDI` enlaza el receptor vía `ClienteFacturacion` (RFC, razón social, CP de 5 caracteres, régimen, uso CFDI). Los montos agregados incluyen `subtotal`, `total_impuestos_trasladados` y `total`.
- **Desglose de IVA:** Por línea existe `ConceptoFactura` + `ImpuestoConcepto` (traslado IVA `002`, `tasa_o_cuota`, `base`, `importe`). En `contabilidad.views.crear_factura` al guardar un borrador se crea IVA 16% por concepto y se actualizan totales en la factura. El JSON hacia Facturama (`facturama_api._construir_cfdi_json`) arma `Items[].Taxes` desde esos impuestos.
- **Laboratorio:** `FacturaCFDI.orden_laboratorio` es un `ForeignKey` opcional a `core.OrdenDeServicio`. **En la vista `crear_factura` actual no se asigna** `orden_laboratorio` desde el POST; el flujo es factura manual en contabilidad. No hay FK desde `core.PagoOrden` hacia `FacturaCFDI`; `PagoOrden` solo audita cobros multimodales (`monto_efectivo`, tarjetas, transferencia, `client_mutation_id` para idempotencia de cobro, no de timbrado).
- **Farmacia:** En `FacturaCFDI` el FK a venta de farmacia sigue **comentado** en el modelo (nota “cuando se cree el modelo en core”). `core.Venta` / `Pago` no aparecen enlazados a CFDI en el código revisado de `farmacia/`. Hay comentarios de “FASE contabilidad” en servicios de caja, sin integración timbrado aún.

### 2. Idempotencia fiscal (Facturama)

- **`contabilidad/facturama_api.py` — `timbrar_cfdi`:** Construye una clave determinista `sha256("cfdi-empresa{eid}-fac{factura.id}")` y la envía en cabecera HTTP **`Idempotency-Key`**. Requiere `cfdi_empresa_scope_id()` (empresa del cliente o del usuario creador); si falta, no llama al PAC.
- **`contabilidad/services/timbrado_cfdi.py`:** `transaction.atomic` + `select_for_update(nowait=True)` sobre la fila `FacturaCFDI`; estados `FACTURANDO` / `TIMBRADO` / `ERROR`; evita doble timbrado concurrente en aplicación. Comando `reconciliar_facturas_pendientes` devuelve a `PENDIENTE` facturas atascadas en `FACTURANDO` tras timeout.
- **Tests:** `core/tests/test_e2e_cfdi.py` cubre clave determinista, lock 409 JSON, y que un segundo POST no vuelva a llamar al mock del PAC.
- **Matiz:** La garantía ante el SAT depende de que el **PAC Facturama respete** `Idempotency-Key` en `POST /3/cfdis`. El código del producto ya la envía; falta validación explícita contra documentación oficial del proveedor en la fase de implementación (Hito 16).

### 3. Sandbox seguro (`FACTURAMA_SANDBOX`)

- **`config/settings.py`:**  
  - `FACTURAMA_SANDBOX = os.environ.get('FACTURAMA_SANDBOX', 'True') == 'True'` → **por defecto sandbox** si la variable no está definida.  
  - Si `PRISLAB_DEPLOYMENT_MODE == 'training_sandbox'`, se **fuerza** `FACTURAMA_SANDBOX = True`.  
  - `FacturamaAPI` usa `https://apisandbox.facturama.mx` si `sandbox` es verdadero, si no `https://api.facturama.mx`.
- **Brecha de blindaje:** **`DEBUG` no fuerza** sandbox. Un entorno con `DEBUG=True` pero `FACTURAMA_SANDBOX=False` y credenciales de producción **podría** llamar a la API productiva. El riesgo es operativo/configuración, no un bug de URL invertida.

### 4. Validación frontend (CFDI 4.0 receptor)

- **Alta de cliente fiscal:** `contabilidad/templates/contabilidad/clientes/crear.html` exige RFC y CP con `required`, `maxlength` (13 / 5) y formato básico HTML5; **no** hay validación de patrón SAT (RFC genérico vs. persona moral, dígito verificador, CP existente en catálogo).
- **Timbrado:** `contabilidad/templates/contabilidad/facturas/detalle.html` muestra botón “Timbrar con SAT” solo si `factura.estado == 'BORRADOR'`. **No** hay comprobación previa en plantilla ni en `ejecutar_timbrado` de RFC/CP válidos para 4.0 antes del POST; se confía en datos ya guardados en `ClienteFacturacion`.
- **Paciente vs. receptor:** `core.Paciente` tiene `datos_fiscales` opcional (`DatosFiscales` en `core`) **distinto** del flujo `ClienteFacturacion` usado por facturas. No hay flujo automático que exija RFC+CP del paciente al marcar `requiere_factura` en laboratorio antes de abrir contabilidad.

---

## Brechas detectadas (gaps)

| Área | Gap |
|------|-----|
| **Trazabilidad Lab** | `orden_laboratorio` existe en modelo pero no se rellena en `crear_factura`; `PagoOrden` no referencia CFDI. No hay “un cobro = una factura” trazable en BD. |
| **Trazabilidad Farmacia** | Sin FK `FacturaCFDI` ↔ `Venta`; comentario en modelo sin implementar. |
| **Consistencia fiscal global** | `OrdenDeServicio.requiere_factura` existe en lab, pero no dispara creación ni validación de datos fiscales del receptor en el flujo de cobro. |
| **UI timbrado vs. estados** | `timbrado_cfdi` permite timbrar desde `PENDIENTE` y `ERROR`, pero la plantilla solo ofrece botón en `BORRADOR`. Tras `reconciliar_facturas_pendientes` (→ `PENDIENTE`) el usuario puede quedar sin acción de timbrado en UI. |
| **Validación RFC / CP 4.0** | Solo longitud/required en formulario de cliente; sin validadores SAT, sin bloqueo pre-timbrado en servidor, sin enlace obligatorio paciente → datos fiscales completos. |
| **Sandbox** | No hay “doble candado” `DEBUG → siempre sandbox”; depende de variables de entorno y disciplina operativa. |
| **Idempotencia PAC** | Cabecera enviada; confirmar comportamiento real del endpoint Facturama y tiempos de deduplicación. |

---

## Plan de ataque técnico (siguiente fase — Hito 16)

**Paso 1 — Modelo y trazabilidad**

- `contabilidad/models.py`: descomentar o añadir FK opcional `venta` → `core.Venta` (o modelo unificado de venta); valorar FK opcional `pago_orden` → `core.PagoOrden` o tabla puente si un pago parcial genera factura.
- Migración Django asociada.
- Documentar invariantes: una factura puede cubrir N pagos o un solo pago (definición de negocio).

**Paso 2 — Flujos desde cobro**

- `contabilidad/views.py` (y/o nuevo `contabilidad/services/factura_desde_orden.py`): acción “Generar borrador CFDI” desde contexto de `OrdenDeServicio` con totales alineados a `PagoOrden` / saldo cobrado; asignar `orden_laboratorio` y conceptos desde `DetalleOrden` o política de precios acordada.
- `farmacia/`: punto de extensión desde cierre de venta o servicio existente para proponer factura y enlazar `venta_id` (vistas/servicios concretos según UX definida).

**Paso 3 — Validación CFDI 4.0**

- Nuevo módulo pequeño, p. ej. `contabilidad/validators_cfdi.py` (o `core/validators_fiscales.py`): RFC (longitud, charset, opcional dígito verificador), CP 5 dígitos numéricos, coherencia mínima con catálogos SAT donde aplique.
- `contabilidad/views.py` (`crear_cliente`, `timbrar_factura` vía servicio): rechazar timbrado con mensaje claro si el receptor no cumple.
- Plantillas `clientes/crear.html` y `facturas/detalle.html`: mensajes UX + deshabilitar timbrado si validación falla (opcional JS espejo de reglas servidor).

**Paso 4 — UI estados y recuperación**

- `contabilidad/templates/contabilidad/facturas/detalle.html`: mostrar acción de timbrado coherente con `PENDIENTE` y `ERROR` (mismas reglas que `ejecutar_timbrado`).
- Revisar `lista_facturas` / badges para operadores.

**Paso 5 — Sandbox y operaciones**

- `config/settings.py`: considerar `if DEBUG: FACTURAMA_SANDBOX = True` **o** warning explícito al arranque si `DEBUG and not FACTURAMA_SANDBOX` (definir política con el Director para no romper pruebas mixtas intencionales).
- Documentación de despliegue: variables obligatorias para producción.

**Paso 6 — Verificación con Facturama**

- Prueba en sandbox: mismo `Idempotency-Key`, doble POST, verificar respuesta única o código esperado.
- Ajustar `facturama_api.py` solo si el contrato real del PAC difiere (p. ej. nombre de cabecera o cuerpo).

---

## Archivos de referencia rápida

| Tema | Archivos |
|------|----------|
| Modelos CFDI | `contabilidad/models.py` |
| Cliente PAC | `contabilidad/facturama_api.py` |
| Timbrado + lock | `contabilidad/services/timbrado_cfdi.py`, `contabilidad/views.py` (`timbrar_factura`, `crear_factura`) |
| Pagos lab | `core/models/ventas.py` (`PagoOrden`) |
| Orden + bandera factura | `core/models/laboratorio.py` (`requiere_factura`) |
| Config | `config/settings.py` (bloque ~731–737) |
| Tests blindaje | `core/tests/test_e2e_cfdi.py` |
| Reconciliación | `contabilidad/management/commands/reconciliar_facturas_pendientes.py` |

---

*Fin del reconocimiento táctico — listo para iniciar implementación Hito 16 bajo control de cambios.*
