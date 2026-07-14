# Catálogo de Dominios de Negocio — PRISLAB SaaS

**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## Resumen de dominios detectados

| Dominio | Directorio principal | Archivos | Estado general | Prioridad |
|---------|----------------------|----------|----------------|-----------|
| **Core / Plataforma** | `core/` | 776 | IMPLEMENTADO | P0 |
| **Laboratorio LIMS** | `lims/` | 46 | IMPLEMENTADO | P0 |
| **Laboratorio operativo** | `laboratorio/` | 77 | IMPLEMENTADO | P0 |
| **Consultorio médico** | `consultorio/` | 80 | IMPLEMENTADO | P1 |
| **Farmacia** | `farmacia/` | 62 | IMPLEMENTADO | P1 |
| **Inventario** | `inventario/` | 78 | IMPLEMENTADO | P1 |
| **Contabilidad** | `contabilidad/` | 40 | IMPLEMENTADO | P1 |
| **Pacientes** | `pacientes/` | 27 | IMPLEMENTADO | P0 |
| **Seguridad y RBAC** | `seguridad/` | 24 | IMPLEMENTADO | P0 |
| **Recepción** | `recepcion/` | 15 | IMPLEMENTADO | P1 |
| **Marketing** | `marketing/` | 35 | IMPLEMENTADO | P2 |
| **Bienestar** | `bienestar/` | 23 | IMPLEMENTADO | P2 |
| **Academia** | `academia/` | 21 | IMPLEMENTADO | P2 |
| **Enfermería** | `enfermeria/` | 15 | IMPLEMENTADO | P2 |
| **IoT** | `iot/` | 15 | IMPLEMENTADO | P2 |
| **Logística** | `logistica/` | 18 | IMPLEMENTADO | P2 |
| **Mantenimiento** | `mantenimiento/` | 57 | IMPLEMENTADO | P2 |
| **Reglas de negocio** | `reglas_negocio/` | 11 | IMPLEMENTADO | P1 |
| **Suscripciones** | `suscripciones/` | 10 | IMPLEMENTADO | P2 |
| **PRIS AI Core** | `pris_ai_core/` | 10 | IMPLEMENTADO | P1 |
| **IA / MCA** | `ia/` | 17 | IMPLEMENTADO | P1 |
| **Middleware local** | `middleware_local/` | 12 | IMPLEMENTADO | P2 |

---

## Dominios detallados

### 1. Core / Plataforma

- **Propósito:** Funcionalidad central compartida por todos los módulos: autenticación, usuarios, empresas, sucursales, tenant, catálogos, ventas, cobros, resultados, dashboards, y servicios transversales.
- **Actores:** Administrador, director, recepcionista, laboratorista, médico, paciente, sistema.
- **Entidades principales:** Usuario, Empresa, Sucursal, Paciente, Orden, Resultado, Perfil, Analito, Cobro, Pago.
- **Flujos principales:**
  - Autenticación y autorización.
  - Creación de órdenes de laboratorio.
  - Captura de resultados.
  - Generación de PDF de resultados.
  - Cobranza y facturación.
  - Dashboards y reportes.
- **Dependencias:** Todos los demás dominios.

### 2. Laboratorio (LIMS + operativo)

- **Propósito:** Gestión del ciclo de vida de muestras, catálogo de exámenes, perfiles, paquetes, valores de referencia, calidad, recepción y reportes.
- **Actores:** Laboratorista, técnico, director, paciente.
- **Entidades principales:** Analito, PerfilLims, PaqueteLims, ValorReferenciaAnalito, PerfilAnalito, Orden, Muestra, Resultado.
- **Flujos principales:**
  - Importación de catálogo LIMS.
  - Creación de perfiles y paquetes.
  - Definición de valores de referencia.
  - Captura y validación de resultados.
  - Liberación de resultados al paciente.
- **Dependencias:** Core, pacientes, farmacia, inventario.

### 3. Consultorio médico

- **Propósito:** Consultas médicas, SOAP, recetas, certificados, triage, integración con laboratorio/farmacia.
- **Actores:** Médico, enfermera, recepcionista, paciente.
- **Entidades principales:** Consulta, Receta, Certificado, Triage, Historial clínico.
- **Dependencias:** Core, pacientes, farmacia, laboratorio.

### 4. Farmacia

- **Propósito:** Punto de venta, inventario de medicamentos, compras, devoluciones, regulatorio.
- **Actores:** Cajero, farmacéutico, administrador.
- **Entidades principales:** Producto, Venta, Compra, Devolución, Movimiento, Lote.
- **Dependencias:** Core, inventario, contabilidad.

### 5. Inventario

- **Propósito:** Control de insumos, reactivos, productos, traspasos entre sucursales.
- **Actores:** Almacenista, administrador, laboratorista.
- **Entidades principales:** Producto, Stock, Movimiento, Traspaso, Orden de compra.
- **Dependencias:** Core, farmacia, laboratorio.

### 6. Contabilidad

- **Propósito:** Cuentas por cobrar, facturación, reportes financieros, autofactura.
- **Actores:** Contador, administrador, director.
- **Entidades principales:** Factura, Pago, Cuenta por cobrar, Corte de caja.
- **Dependencias:** Core, ventas, cobros.

### 7. Pacientes

- **Propósito:** Portal del paciente, historial clínico, acceso a resultados, datos demográficos.
- **Actores:** Paciente, médico, recepcionista.
- **Entidades principales:** Paciente, Historial, AccesoResultado.
- **Dependencias:** Core, laboratorio.

### 8. Seguridad y RBAC

- **Propósito:** Roles, permisos, grupos, auditoría de accesos, reglas de negocio de seguridad.
- **Actores:** Administrador de seguridad, sistema.
- **Entidades principales:** Rol, Permiso, Grupo, ReglaNegocio, Auditoria.
- **Dependencias:** Core.

### 9. IA / MCA

- **Propósite:** Asistente médico, interpretación de resultados, generación de recetas, chat con IA, agentes de diagnóstico.
- **Actores:** Médico, paciente, director.
- **Entidades principales:** Agente, Tool, Prompt, Conversación, Memoria.
- **Dependencias:** Core, consultorio, laboratorio.

### 10. Infraestructura y operaciones

- **Propósito:** Docker, Compose, Nginx, CI/CD, monitoreo, backups, scripts de utilidad.
- **Actores:** DevOps, SRE.
- **Componentes:** GitHub Actions, Prometheus, Grafana, Alertmanager, backups de PostgreSQL.
- **Dependencias:** Toda la plataforma.

---

## Matriz de dependencias entre dominios

| Dominio | Depende de |
|---------|------------|
| Core | — |
| LIMS | Core, Pacientes |
| Laboratorio | Core, LIMS, Inventario |
| Consultorio | Core, Pacientes, Farmacia, Laboratorio |
| Farmacia | Core, Inventario, Contabilidad |
| Inventario | Core, Farmacia, Laboratorio |
| Contabilidad | Core, Ventas (Core) |
| Pacientes | Core, Laboratorio |
| Seguridad | Core |
| IA | Core, Consultorio, Laboratorio |
| Recepción | Core, Pacientes, Laboratorio |
| Marketing | Core |

---

## Notas

- Los nombres de dominios se mantienen exactamente como aparecen en el árbol de directorios del repositorio.
- El dominio `core` concentra la mayor parte del código (776 archivos) y es el núcleo transversal.
- Los dominios P0 son aquellos críticos para la operación del laboratorio: Core, LIMS, Laboratorio, Pacientes, Seguridad.
