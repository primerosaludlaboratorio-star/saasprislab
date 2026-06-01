"""
═══════════════════════════════════════════════════════════════════════════════
AUDITORÍA DE INTEGRIDAD — MÓDULO INVENTARIO (Excluyendo Farmacia)
═══════════════════════════════════════════════════════════════════════════════
Fecha: 2026-04-03
Auditor: Windsurf (Cascade)
Versión: v1.0 — Audit Report Inventario v8.x
Alcance: inventario/ (silos Lab, Consultorio, Generales, Compras, Traspasos)
Referencia: DOCS_AUDIT_MAESTRO.md §5, §6
═══════════════════════════════════════════════════════════════════════════════

==============================================================================
1. RESUMEN EJECUTIVO
==============================================================================

Estado General: ✅ ESTABLE con mejoras recomendadas

Hallazgos Críticos: 0
Hallazgos Medios: 3  
Hallazgos Leves: 4

El módulo de inventario (inventario/) presenta una arquitectura sólida con:
• Aislamiento de silos (Lab, Consultorio, Generales) correctamente implementado
• Uso apropiado de select_for_update() en operaciones críticas
• Transacciones atómicas en flujos de stock
• Modelo multi-tenant consistente (empresa FK en todos los modelos)

==============================================================================
2. MAPEO DE COMPONENTES AUDITADOS
==============================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│ ARCHIVOS MAPEADOS                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ • inventario/models.py           (1374 líneas, 18 modelos)                 │
│ • inventario/signals.py          (336 líneas, 4 motores FEFO)              │
│ • inventario/views.py            (655 líneas, Silo Lab)                    │
│ • inventario/views_consultorio.py (278 líneas, Silo Consultorio)           │
│ • inventario/views_generales.py  (425 líneas, Silo Generales)            │
│ • inventario/views_compras.py    (425 líneas, Motor Compras)               │
│ • inventario/views_traspasos.py  (443 líneas, Logística)                   │
│ • inventario/admin.py             (181 líneas, 11 admins)                  │
│ • inventario/urls.py              (107 líneas, 44 rutas)                   │
│ • inventario/apps.py              (11 líneas, signals conectados)        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ MODELOS INVENTARIO (18 modelos principales)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ SILO LABORATORIO:                                                           │
│   • CatalogoReactivoLab        Catálogo maestro de reactivos              │
│   • ConsumoEstudioReactivo       Fórmulas de consumo por analito             │
│   • LoteReactivoLab            Lotes FEFO con QC                            │
│   • SalidaAnaliticaLab         Descuentos auto por validación              │
│   • SalidaTecnicaLab           Descuentos manuales (mantenimiento)         │
│                                                                             │
│ SILO CONSULTORIO:                                                           │
│   • CatalogoInsumoConsultorio    Catálogo de material de curación            │
│   • LoteInsumoConsultorio      Lotes FEFO                                   │
│   • SalidaConsumoConsultorio   Registro de uso por cita                    │
│                                                                             │
│ SILO GENERALES:                                                             │
│   • CatalogoInsumoGeneral      Catálogo de papelería/limpieza              │
│   • LoteInsumoGeneral          Lotes FEFO                                   │
│   • ValeRequisicion            Vales de requisición interna                 │
│   • LineaValeRequisicion       Líneas de vale                               │
│                                                                             │
│ MOTOR DE COMPRAS:                                                           │
│   • ProveedorCompras           Catálogo de proveedores (no COFEPRIS)        │
│   • OrdenDeCompra              Órdenes de compra consolidadas              │
│   • LineaOrdenCompra           Líneas con GenericFK a silos                 │
│                                                                             │
│ LOGÍSTICA INTER-SEDES:                                                       │
│   • TraspasoInventario         Traspasos entre empresas/sucursales          │
│   • LineaTraspasoInventario    Líneas de traspaso con snapshots             │
│   • NotificacionDiscrepancia   Alertas de discrepancias al Director         │
└─────────────────────────────────────────────────────────────────────────────┘

==============================================================================
3. HALLAZGOS DETALLADOS
==============================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│ HALLAZGO MEDIO #1 — Falta de campo 'inventario_descontado' en SalidaAnaliticaLab │
├─────────────────────────────────────────────────────────────────────────────┤
│ Ubicación: inventario/signals.py:52-99 (descontar_reactivos_fefo)          │
│                                                                             │
│ Descripción:                                                                │
│ El signal post_save de ResultadoParametro que descuenta reactivos NO tiene │
│ un flag de idempotencia persistente como el que se implementó en farmacia   │
│ (Venta.inventario_descontado).                                              │
│                                                                             │
│ Riesgo:                                                                     │
│ Si el signal se ejecuta múltiples veces (retry HTTP, doble-click, worker    │
│ paralelo), podría generar múltiples SalidaAnaliticaLab para el mismo       │
│ resultado, descontando stock múltiples veces.                              │
│                                                                             │
│ Evidencia:                                                                  │
│   ya_descontado = SalidaAnaliticaLab.objects.filter(...).exists()          │
│   ← Esto es una validación "soft", no una garantía de idempotencia         │
│                                                                             │
│ Recomendación:                                                              │
│ • Agregar campo idempotency_key a SalidaAnaliticaLab (similar a             │
│   MovimientoCaja.idempotency_key en farmacia)                             │
│ • Usar get_or_create con idempotency_key en el signal                       │
│ • Implementar retry con exponential backoff como en farmacia                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ HALLAZGO MEDIO #2 — Race condition potencial en ValeRequisicion.entregar   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Ubicación: inventario/views_generales.py (detalle_vale, acción entregar)    │
│                                                                             │
│ Descripción:                                                                │
│ El signal descontar_generales_por_vale en inventario/signals.py:235-294    │
│ implementa un FEFO fallback, pero la vista principal que debería hacer    │
│ el descuento atómico no está usando select_for_update() en los lotes.       │
│                                                                             │
│ Riesgo:                                                                     │
│ Concurrencia en entrega de vales podría causar:                             │
│   • Doble descuento de lotes                                                │
│   • Stock negativo                                                          │
│   • Asignación incorrecta de lote_entregado                                 │
│                                                                             │
│ Recomendación:                                                              │
│ • Agregar transaction.atomic() + select_for_update() en la vista de        │
│   entrega de vales                                                          │
│ • Orden de bloqueo: Vale → Lotes FEFO                                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ HALLAZGO MEDIO #3 — Validación de stock insuficiente sin transacción atómica│
├─────────────────────────────────────────────────────────────────────────────┤
│ Ubicación: inventario/views_consultorio.py:registrar_salida_consultorio    │
│ (líneas 200-278 aprox)                                                      │
│                                                                             │
│ Descripción:                                                                │
│ La vista de registro de salida de consultorio valida stock disponible      │
│ antes de descontar, pero entre la validación y el descuento puede haber     │
│ una condición de carrera.                                                   │
│                                                                             │
│ Riesgo:                                                                     │
│   • Validación: lote.cantidad_actual >= cantidad_solicitada                │
│   • (otro proceso descuenta el mismo lote)                                 │
│   • Descuento: lote.cantidad_actual -= cantidad → stock negativo           │
│                                                                             │
│ Recomendación:                                                              │
│ • Usar select_for_update() al obtener el lote                             │
│ • Calcular stock disponible dentro de la transacción atómica                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ HALLAZGO LEVE #1 — Inconsistencia en cálculo de stock mínimo (extra)       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Ubicación: inventario/views_compras.py:71-75                               │
│                                                                             │
│ Descripción:                                                                │
│ qs.extra(where=["inventario_catalogoreactivolab.stock_minimo > 0"])         │
│ Este query usa .extra() que está deprecado y puede romper en Django 5.x    │
│                                                                             │
│ Recomendación:                                                              │
│ • Reemplazar con filter(stock_minimo__gt=0) o annotate                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ HALLAZGO LEVE #2 — GenericFK sin validación de ContentType                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Ubicación: inventario/models.py:1091-1104 (LineaOrdenCompra)               │
│                                                                             │
│ Descripción:                                                                │
│ El modelo LineaOrdenCompra usa GenericForeignKey para referenciar          │
│ artículos de los 3 silos. El limit_choices_to restringe el ContentType,    │
│ pero no hay validación en el save() o clean() para evitar referencias a    │
│ objetos inactivos o eliminados.                                             │
│                                                                             │
│ Riesgo:                                                                     │
│ Bajo — el admin y vistas filtran por activo=True, pero una operación       │
│ manual podría crear líneas con artículos inactivos.                        │
│                                                                             │
│ Recomendación:                                                              │
│ • Agregar validación en LineaOrdenCompra.clean() para verificar que        │
│   el artículo referenciado esté activo                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ HALLAZGO LEVE #3 — Falta de índice en campo 'estado' de LoteInsumoGeneral   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Ubicación: inventario/models.py:840-844 (LoteInsumoGeneral.Meta)           │
│                                                                             │
│ Descripción:                                                                │
│ Los lotes de insumos generales no tienen un campo 'estado' como los lotes  │
│ de laboratorio (CUARENTENA, ACTIVO, AGOTADO, etc.).                         │
│                                                                             │
│ Esto puede dificultar:                                                      │
│   • Query de lotes activos para FEFO                                        │
│   • Auditoría de lotes agotados/vencidos                                    │
│                                                                             │
│ Recomendación:                                                              │
│ • Considerar agregar campo 'estado' a LoteInsumoGeneral para              │
│   consistencia con los otros silos                                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ HALLAZGO LEVE #4 — Traspaso sin verificación de tenant en recepción        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Ubicación: inventario/views_traspasos.py:269-308 (_ejecutar_recepcion)     │
│                                                                             │
│ Descripción:                                                                │
│ Al recibir un traspaso, el sistema crea nuevos lotes en la empresa destino │
│ pero no verifica explícitamente que el usuario receptor pertenezca a esa   │
│ empresa. El decorador @_empresa_required verifica empresa del request,    │
│ pero no hay doble verificación de que empresa_destino == empresa del user.  │
│                                                                             │
│ Riesgo:                                                                     │
│ Bajo — requiere suplantación de sesión o manipulación de POST.              │
│                                                                             │
│ Recomendación:                                                              │
│ • Agregar assert explícito:                                                 │
│   assert traspaso.empresa_destino_id == empresa.pk                          │
└─────────────────────────────────────────────────────────────────────────────┘

==============================================================================
4. FORTALEZAS IDENTIFICADAS
==============================================================================

✅ Arquitectura de Silos:
   • Separación clara entre Lab, Consultorio y Generales
   • Sin mezcla con el silo Farmacia (COFEPRIS)
   • Cada silo tiene sus propios modelos de catálogo, lotes y salidas

✅ Multi-tenant correcto:
   • FK a Empresa en TODOS los modelos
   • Helper _get_empresa() sin fallback a Empresa.objects.first()
   • Filtro por empresa en todas las queries administrativas

✅ Uso de select_for_update() (encontrado en 8 lugares):
   • inventario/signals.py:4 usages (FEFO Lab y Generales)
   • inventario/views_traspasos.py:3 usages (despacho, rechazo)
   • inventario/views_generales.py:1 usage (vales)

✅ Transacciones atómicas:
   • transaction.atomic() en vistas críticas de stock
   • Rollback automático en caso de error

✅ Sistema de traspasos robusto:
   • Flujo de estados: BORRADOR → EN_TRANSITO → RECIBIDO/RECHAZADO
   • Stock sale del origen al despachar
   • Stock entra al destino al recibir con PIN
   • Notificación automática de discrepancias

✅ Auditoría integrada:
   • Snapshots en líneas de traspaso (nombre_articulo_snapshot)
   • Registro de usuario y fecha en todas las operaciones
   • NotificacionDiscrepancia para alertar al Director

==============================================================================
5. COMPARATIVO CON FARMACIA (v1.13 Endurecida)
==============================================================================

| Característica          | Farmacia (v1.13)          | Inventario (v8.x)        |
|-------------------------|---------------------------|----------------------------|
| Idempotencia descuento  | ✅ Venta.inventario_descontado | ⚠️ Validación "soft" en signal |
| select_for_update()     | ✅ Sí, en orden correcto   | ✅ Sí, en FEFO             |
| Transacciones atómicas  | ✅ Sí                     | ✅ Sí                       |
| Retry loop              | ✅ 3 intentos + backoff    | ❌ No implementado          |
| Notificación errores    | ✅ Email/Telegram          | ✅ NotificacionDiscrepancia |
| Conciliación 1:1        | ✅ MovimientoCaja ↔ Venta | N/A (no hay cobro directo)  |
| Hash integridad         | ❌ No aplica              | N/A                         |

==============================================================================
6. RECOMENDACIONES PRIORITARIAS
==============================================================================

PRIORIDAD ALTA:
1. Agregar idempotency_key a SalidaAnaliticaLab y usar get_or_create
2. Implementar retry loop con exponential backoff en signals de inventario
3. Auditar y endurecer ValeRequisicion.entregar con select_for_update()

PRIORIDAD MEDIA:
4. Validación de stock atómica en registro de salida de consultorio
5. Reemplazar .extra() deprecado en views_compras
6. Agregar campo 'estado' a LoteInsumoGeneral

PRIORIDAD BAJA:
7. Validación de GenericFK en LineaOrdenCompra.clean()
8. Assert de tenant en recepción de traspasos

==============================================================================
7. COMANDOS DE AUDITORÍA RECOMENDADOS
==============================================================================

Sugerencia: Crear comando similar a bankguard_audit para inventario:

```python
# inventario/management/commands/auditar_integridad_inventario.py

class Command(BaseCommand):
    '''Auditoría de integridad del módulo inventario'''
    
    def handle(self, *args, **options):
        # 1. Verificar dobles descuentos de reactivos
        # 2. Verificar stock negativo en lotes
        # 3. Verificar traspasos pendientes > 30 días
        # 4. Verificar lotes vencidos marcados como ACTIVO
        # 5. Verificar vales entregados con cantidad_entregada=0
```

==============================================================================
8. CONCLUSIÓN
==============================================================================

El módulo de inventario presenta una arquitectura sólida y bien diseñada,
con separación de silos y buenas prácticas de multi-tenancy. Los principales
hallazgos están relacionados con la falta de idempotencia "hard" en el
descuento automático de reactivos (similar al problema que se resolvió en
farmacia v1.13) y algunas validaciones de concurrencia que pueden reforzarse.

No se detectaron vulnerabilidades críticas que comprometan la integridad
de datos, pero se recomienda implementar las mejoras de Prioridad Alta
antes de escalar a múltiples usuariosc concurrentes.

ESTADO FINAL: ✅ ESTABLE (con mejoras recomendadas)

═══════════════════════════════════════════════════════════════════════════════
Fin del Reporte de Auditoría — Módulo Inventario v8.x
═══════════════════════════════════════════════════════════════════════════════
"""
