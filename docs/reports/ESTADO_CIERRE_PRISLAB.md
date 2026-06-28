# Estado de Cierre - PRISLAB Laboratorio y Consultorio

**Generado:** 2026-06-26 16:34:17  

**Script:** `scripts/generar_reporte_cierre_md.py`

---

## 1. Resumen Ejecutivo

| Indicador | Valor | Estado |

|---|---|---|

| Monolitos convertidos a paquetes | 3/3 | ✅ |

| manage.py check | OK | ✅ |

| Exports core.views.laboratorio | 73 | ✅ |

| Exports core.views.pris_ia | 9 | ✅ |

| URL patterns config.urls | 406 | ✅ |

| `except Exception` en todo el repo | 2270 | ⚠️ |

| Imports legacy restantes | 16 | ⚠️ |



## 2. Verificacion de Monolitos -> Paquetes

### core/views/laboratorio.py

- Paquete: `core/views/laboratorio/` ✅

- Backup: `core/views/laboratorio.py.bak` ❌

- Monolito eliminado: ❌

- Estado: **FALLO**

- Archivos: 13

  - `__init__.py` (3740 bytes, 169 lineas)

  - `_helpers.py` (1609 bytes, 49 lineas)

  - `caja.py` (17022 bytes, 406 lineas)

  - `calidad.py` (30031 bytes, 744 lineas)

  - `captura.py` (15349 bytes, 385 lineas)

  - `config_lims.py` (9383 bytes, 255 lineas)

  - `edicion_orden.py` (13866 bytes, 368 lineas)

  - `escaneo_ia.py` (14180 bytes, 348 lineas)

  - `pacientes_lab.py` (3021 bytes, 87 lineas)

  - `pdf_impresion.py` (16432 bytes, 418 lineas)

  - `recepcion.py` (15909 bytes, 383 lineas)

  - `reportes.py` (8562 bytes, 226 lineas)

  - `resultados.py` (17107 bytes, 433 lineas)



### core/views/pris_ia.py

- Paquete: `core/views/pris_ia/` ✅

- Backup: `core/views/pris_ia.py.bak` ❌

- Monolito eliminado: ❌

- Estado: **FALLO**

- Archivos: 9

  - `__init__.py` (1375 bytes, 46 lineas)

  - `_constants.py` (10909 bytes, 157 lineas)

  - `_dispatcher.py` (5506 bytes, 119 lineas)

  - `_gemini.py` (4366 bytes, 109 lineas)

  - `_prompts.py` (4212 bytes, 87 lineas)

  - `_rbac.py` (1866 bytes, 50 lineas)

  - `_tools_lab.py` (10030 bytes, 238 lineas)

  - `_tools_lectura.py` (26823 bytes, 598 lineas)

  - `views.py` (16363 bytes, 386 lineas)



### config/urls.py

- Paquete: `config/urls/` ✅

- Backup: `config/urls.py.bak` ❌

- Monolito eliminado: ❌

- Estado: **FALLO**

- Archivos: 10

  - `__init__.py` (1234 bytes, 39 lineas)

  - `_helpers.py` (459 bytes, 12 lineas)

  - `api.py` (1586 bytes, 34 lineas)

  - `core_views.py` (1710 bytes, 34 lineas)

  - `director.py` (6172 bytes, 102 lineas)

  - `farmacia.py` (3827 bytes, 50 lineas)

  - `finanzas.py` (4555 bytes, 66 lineas)

  - `laboratorio.py` (11349 bytes, 148 lineas)

  - `modulos.py` (15644 bytes, 218 lineas)

  - `pris_ia.py` (5324 bytes, 81 lineas)



## 3. manage.py check

```
System check identified no issues (0 silenced).
```



## 4. Imports Legacy Restantes

| Descripcion | Patron | Ocurrencias |

|---|---|---|

| ordenes.py legacy | `laboratorio.models.ordenes` | 6 |

| laboratorio Orden legacy | `from laboratorio.models import Orden` | 4 |

| laboratorio Medico legacy | `from laboratorio.models import Medico` | 3 |

| consultorio legacy.py | `consultorio.legacy` | 3 |



## 5. Excepciones Genericas (`except Exception`)

**Total encontrados:** 2270


### 5.1 Distribucion por carpeta

| Carpeta | Casos |

|---|---|

| `core/views` | 298 |

| `core/management/commands` | 210 |

| `.` | 164 |

| `core/services` | 76 |

| `core/utils` | 50 |

| `scripts_legacy` | 42 |

| `core/middleware` | 41 |

| `.venv/Lib/site-packages/billiard` | 37 |

| `scripts` | 31 |

| `.venv/Lib/site-packages/numpy/f2py` | 29 |

| `core` | 29 |

| `core/services/lims` | 29 |

| `middleware_local/drivers` | 28 |

| `.venv/Lib/site-packages/pypdf` | 26 |

| `.venv/Lib/site-packages/playwright/_impl` | 22 |

| `.venv/Lib/site-packages/grpc` | 21 |

| `.venv/Lib/site-packages/click` | 20 |

| `.venv/Lib/site-packages/pip/_vendor/rich` | 20 |

| `.venv/Lib/site-packages/websockets/asyncio` | 19 |

| `.venv/Lib/site-packages/websockets/sync` | 18 |

| `laboratorio/management/commands` | 18 |

| `.venv/Lib/site-packages/coverage` | 17 |

| `.venv/Lib/site-packages/google/genai` | 17 |

| `.venv/Lib/site-packages/numpy/_core/tests` | 17 |

| `.venv/Lib/site-packages/PIL` | 17 |

| `.venv/Lib/site-packages/pypdf/generic` | 16 |

| `.venv/Lib/site-packages/_pytest` | 16 |

| `.venv/Lib/site-packages/django/test` | 15 |

| `.venv/Lib/site-packages/google/genai/_interactions` | 14 |

| `farmacia/management/commands` | 14 |

| ... y 258 mas | - |



### 5.2 Primeros 50 casos detallados

| Archivo | Linea | Codigo |

|---|---|---|

| `cargar_excel_forzado.py` | 177 | `except Exception as e:` |

| `cargar_excel_forzado.py` | 193 | `except Exception as e:` |

| `cargar_excel_robusto.py` | 150 | `except Exception as e:` |

| `cargar_excel_robusto.py` | 172 | `except Exception as e:` |

| `cargar_tarifas.py` | 96 | `except Exception as e:` |

| `configurar_admin.py` | 44 | `except Exception as e:` |

| `configurar_admin_completo.py` | 68 | `except Exception as e:` |

| `create_e2e_user.py` | 63 | `except Exception as e:` |

| `e2e_test_prod.py` | 21 | `except Exception:` |

| `e2e_test_prod.py` | 81 | `except Exception as e:` |

| `e2e_test_prod.py` | 97 | `except Exception as e:` |

| `e2e_test_prod.py` | 117 | `except Exception as e:` |

| `ejecutar_pruebas_e2e.py` | 66 | `except Exception as e:` |

| `ejecutar_pruebas_playwright.py` | 36 | `except Exception as e:` |

| `ejecutar_pruebas_playwright.py` | 53 | `except Exception as e:` |

| `generar_migraciones_consolidacion.py` | 56 | `except Exception as e:` |

| `generar_vapid_keys.py` | 69 | `except Exception as e:` |

| `migracion_ordenes_forense.py` | 191 | `except Exception as e:` |

| `migracion_ordenes_forense.py` | 224 | `except Exception as e:` |

| `migracion_ordenes_forense.py` | 266 | `except Exception as e:` |

| `migracion_ordenes_forense.py` | 334 | `except Exception as e:` |

| `migracion_ordenes_forense.py` | 366 | `except Exception as e:` |

| `probar_registro_pacientes.py` | 114 | `except Exception as e:` |

| `reset_admin_password.py` | 29 | `except Exception as e:` |

| `smoke_test.py` | 17 | `except Exception as e:` |

| `smoke_test.py` | 27 | `except Exception as e:` |

| `smoke_test.py` | 37 | `except Exception as e:` |

| `smoke_test.py` | 51 | `except Exception as e:` |

| `smoke_test.py` | 60 | `except Exception as e:` |

| `smoke_test.py` | 68 | `except Exception as e:` |

| `smoke_test.py` | 76 | `except Exception as e:` |

| `smoke_test.py` | 85 | `except Exception as e:` |

| `smoke_test.py` | 94 | `except Exception as e:` |

| `smoke_test.py` | 103 | `except Exception as e:` |

| `smoke_test.py` | 122 | `except Exception as ue:` |

| `smoke_test.py` | 125 | `except Exception as e:` |

| `smoke_test.py` | 133 | `except Exception as e:` |

| `smoke_test.py` | 143 | `except Exception as e:` |

| `smoke_test.py` | 151 | `except Exception as e:` |

| `smoke_test.py` | 159 | `except Exception as e:` |

| `smoke_test.py` | 173 | `except Exception as e:` |

| `smoke_test.py` | 181 | `except Exception as e:` |

| `smoke_test.py` | 189 | `except Exception as e:` |

| `smoke_test.py` | 197 | `except Exception as e:` |

| `smoke_test.py` | 211 | `except Exception as e:` |

| `smoke_test.py` | 221 | `except Exception as e:` |

| `smoke_test.py` | 231 | `except Exception as e:` |

| `smoke_test.py` | 246 | `except Exception as ue:` |

| `smoke_test.py` | 249 | `except Exception as e:` |

| `test_api.py` | 34 | `except Exception as e:` |

| ... | ... | *2220 casos adicionales* |



## 6. Archivos Criticos

| Archivo | Tamano | Lineas | Existe |

|---|---|---|---|

| `consultorio/api_views.py` | 9512 bytes | 267 | ✅ |

| `laboratorio/services/cci_canal.py` | 7336 bytes | 212 | ✅ |

| `laboratorio/services/escudo_clinico_lims.py` | 4700 bytes | 120 | ✅ |

| `laboratorio/models/ordenes.py` | 8946 bytes | 252 | ✅ |



## 7. Plan de Cierre Propuesto (pendiente de aprobacion)

Marca con `[x]` las acciones que quieres implementar y responde con el numero de items.


### Fase 1: Seguridad inmediata (1-2 dias)

- [ ] Corregir `except Exception` en `consultorio/api_views.py`

- [ ] Corregir `except Exception` en `laboratorio/services/cci_canal.py`

- [ ] Corregir `except Exception` en `laboratorio/services/escudo_clinico_lims.py`



### Fase 2: Legacy imports (1-2 dias)

- [ ] Eliminar `laboratorio.models.ordenes` (4 ocurrencias)

- [ ] Eliminar `from laboratorio.models import Orden` (2 ocurrencias)

- [ ] Eliminar `from laboratorio.models import Medico` (1 ocurrencia)

- [ ] Eliminar `consultorio.legacy` (1 ocurrencia)



### Fase 3: Excepciones por modulo (varios dias)

- [ ] Management commands (limpiar `except Exception` en commands)

- [ ] Servicios de laboratorio

- [ ] Tests (`core/tests`)

- [ ] Scripts de migracion y E2E



---

**Instrucciones:** Lee este documento, marca las acciones a implementar y dime "Implementar Fase X, items Y, Z". Asi ejecutamos sin gastar tokens en listados.
