# API v3 — Payloads de ejemplo para QA (v8.5, code freeze)

Documento operativo para la **Semana de Regresión**. Los endpoints viven bajo el prefijo `https://<host>/api/v3/`.

## Autenticación y cabeceras

- **Auth:** `SessionAuth` (misma sesión que el panel web). La petición debe incluir la **cookie de sesión** del usuario cajero o del químico, según el endpoint.
- **Correlación:** el middleware puede inyectar `request_id`; en errores, el cuerpo incluye siempre `request_id` en el sobre estándar (Cadenero).

---

## 1. `POST /api/v3/farmacia/pdv/cobrar`

### Campos relevantes (resumen)

| Área | Campos |
|------|--------|
| Totales | `subtotal`, `iva_total`, `redondeo`, `total_final` (deben ser coherentes con ítems y pagos) |
| Cliente | `cliente` (texto), opcional `paciente_id` |
| Líneas | `items[]`: `producto_id` o `id`, `cantidad`, `precio_unitario`, `subtotal`, `iva_item`; opcional `lote_id` |
| Pagos | `pagos` como objeto `{ "efectivo", "tarjeta", "transferencia" }` **o** lista de `{ "metodo", "monto" }` |
| Otros | `efectivo_recibido`, `cambio_entregado`, `referencia_pago`; cortesía: `es_cortesia`, `motivo_cortesia`, `autorizado_por_cortesia` |

**QA:** sustituir `producto_id` por un producto real de la empresa en pruebas, con stock vigente en lote no caducado. La suma de pagos debe igualar `total_final` (tolerancia ±0.01), salvo flujo de cortesía.

### Ejemplo de cuerpo JSON (venta simple, un ítem, solo efectivo)

```json
{
  "cliente": "María Elena Vázquez Ríos",
  "paciente_id": null,
  "subtotal": 348.28,
  "iva_total": 55.72,
  "redondeo": 0.00,
  "total_final": 404.00,
  "descuento_aplicado": 0,
  "descuento_porcentaje": 0,
  "total_original": 404.00,
  "items": [
    {
      "producto_id": 1847,
      "cantidad": 2,
      "precio_unitario": 174.14,
      "subtotal": 348.28,
      "iva_item": 55.72
    }
  ],
  "pagos": {
    "efectivo": 404.00,
    "tarjeta": 0,
    "transferencia": 0
  },
  "efectivo_recibido": 500.00,
  "cambio_entregado": 96.00,
  "referencia_pago": ""
}
```

*Nota:* el `producto_id` **1847** es ilustrativo; en laboratorio debe corresponder a un medicamento real (p. ej. línea de antibiótico o analgésico) con existencias suficientes.

### Ejemplo alternativo: pagos como lista (cobro mixto)

```json
{
  "cliente": "PÚBLICO GENERAL",
  "subtotal": 860.00,
  "iva_total": 137.60,
  "redondeo": 0,
  "total_final": 997.60,
  "items": [
    {
      "producto_id": 2201,
      "cantidad": 1,
      "precio_unitario": 860.00,
      "subtotal": 860.00,
      "iva_item": 137.60
    }
  ],
  "pagos": [
    { "metodo": "EFECTIVO", "monto": 497.60 },
    { "metodo": "TARJETA", "monto": 500.00 }
  ],
  "efectivo_recibido": 500.00,
  "cambio_entregado": 2.40,
  "referencia_pago": "AUTH-78432"
}
```

---

## 2. `POST /api/v3/lims/resultados/captura`

### Contrato HTTP

- En el **cuerpo JSON**, `orden_id` va en la **raíz** (entero, PK de `OrdenDeServicio` en la empresa del usuario).
- El resto del objeto es el `data` del servicio: `accion`, `resultados`, `metodo_captura`, etc.

### Estructura de `resultados`

- Clave: **id numérico de `DetalleOrden`** (como string en JSON está permitido).
- Valor: `resultado`, `observaciones`, y opcionalmente `parametros` (mapa `analito_id` → `{ "valor": "..." }`).

### Ejemplo — borrador (sin validar)

```json
{
  "orden_id": 45821,
  "accion": "borrador",
  "metodo_captura": "MANUAL",
  "resultados": {
    "90344": {
      "resultado": "98",
      "observaciones": "Muestra sin hemólisis visible.",
      "parametros": {
        "112": { "valor": "5.2" },
        "113": { "valor": "140" }
      }
    },
    "90345": {
      "resultado": "Negativo",
      "observaciones": ""
    }
  }
}
```

### Ejemplo — validación (`accion: validar`)

Requiere que la orden y los detalles existan; en validación pueden aplicarse reglas de fórmulas, equipo (`equipo_id`), consentimiento y roles. Para pruebas mínimas, partir del borrador anterior y cambiar solo:

```json
{
  "orden_id": 45821,
  "accion": "validar",
  "metodo_captura": "MANUAL",
  "equipo_id": 3,
  "resultados": {
    "90344": {
      "resultado": "102",
      "observaciones": "Repetición por control interno.",
      "parametros": {
        "112": { "valor": "5.1" },
        "113": { "valor": "139" }
      }
    }
  }
}
```

*Nota:* `90344`, `112`, `113`, `45821` y `equipo_id` son **placeholders**; QA debe tomarlos de una orden real en estado que permita captura.

---

## 3. Respuestas de error (Cadenero / `BusinessApiError`)

Los errores de negocio no devuelven el JSON crudo del servicio legacy: el API v3 unifica al esquema **`ApiErrorEnvelope`**:

| Campo | Tipo | Descripción |
|--------|------|-------------|
| `code` | string | Código estable (p. ej. `STOCK_INSUFFICIENT`, `FORMULA_INCOMPLETA`) |
| `message` | string | Mensaje legible para usuario/operador |
| `detail` | object | Contexto extra (p. ej. campos del cuerpo original del servicio) |
| `request_id` | string | UUID de correlación |

### 3.1 Stock insuficiente (PDV) → HTTP **409**

El servicio interno puede responder 400 con texto de stock; la capa v3 lo expone como **409** con código `STOCK_INSUFFICIENT`.

```json
{
  "code": "STOCK_INSUFFICIENT",
  "message": "Stock insuficiente para Paracetamol 500 mg Tabletas. Faltan 3 unidades.",
  "detail": {
    "status": "error"
  },
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 3.2 Desajuste de pagos (PDV) → HTTP **409**

```json
{
  "code": "PAYMENT_TOTAL_MISMATCH",
  "message": "La suma de pagos ($350.00) no coincide con el total ($404.00). Ajuste los montos.",
  "detail": {
    "status": "error"
  },
  "request_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

### 3.3 Validación clínica / fórmulas (LIMS) → HTTP **422**

Cuando el servicio indica `codigo: FORMULA_INCOMPLETA` (analitos derivados sin datos base), v3 responde **422** y conserva el código de negocio. El array `formulas_avisos` replica la forma devuelta por el motor de fórmulas (`analito_id`, `codigo`, `error`).

```json
{
  "code": "FORMULA_INCOMPLETA",
  "message": "No se pudieron calcular todos los analitos derivados. Capture valores numéricos en los analitos base indicados en la fórmula.",
  "detail": {
    "status": "error",
    "formulas_avisos": [
      {
        "analito_id": 205,
        "codigo": "EGFR_CKD_EPI",
        "error": "dependencias_insatisfechas_o_ciclo"
      }
    ]
  },
  "request_id": "c3d4e5f6-a7b8-9012-cdef-123456789012"
}
```

### 3.4 Placeholder migración 0058 (LIMS) → HTTP **422**

```json
{
  "code": "LIMS_PLACEHOLDER_0058",
  "message": "Hay resultados ligados al analito placeholder de la migración 0058. Ejecute: python manage.py ensamblar_lims_v75 y luego remap_placeholder_resultados antes de validar.",
  "detail": {
    "status": "error"
  },
  "request_id": "d4e5f6a7-b8c9-0123-def0-234567890123"
}
```

### 3.5 Errores de validación de Ninja (parámetros/query)

Para parámetros inválidos en otros endpoints GET, el código suele ser `VALIDATION_ERROR` con HTTP **422** y `detail.errors` en formato Pydantic/Ninja.

---

## Referencia rápida

| Endpoint | Método | Rol / contexto típico |
|----------|--------|-------------------------|
| `/api/v3/farmacia/pdv/cobrar` | POST | CAJERO, FARMACIA, ADMIN, GERENTE (misma regla que PDV) |
| `/api/v3/lims/resultados/captura` | POST | QUIMICO, ADMIN, LABORATORIO (alineado a captura manual LIMS) |

*Versión documentada: 8.5 (code freeze). No ampliar contratos sin cambio de versión y proceso de release.*
