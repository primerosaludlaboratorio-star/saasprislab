"""
core/views/pris_ia/_constants.py

Constantes globales compartidas por todo el paquete pris_ia.
Este módulo es el origen de verdad sin dependencias cíclicas.
"""

from core.models import AccionPRIS


# Mapeo de tool_name -> tipo AccionPRIS
_TOOL_TO_TIPO = {
    "crear_paciente":                   AccionPRIS.TIPO_CREAR_REGISTRO,
    "buscar_o_crear_paciente":          AccionPRIS.TIPO_CREAR_REGISTRO,
    "crear_orden_laboratorio":          AccionPRIS.TIPO_CREAR_REGISTRO,
    "cobrar_orden":                     AccionPRIS.TIPO_CREAR_REGISTRO,
    "registrar_venta_farmacia":         AccionPRIS.TIPO_CREAR_REGISTRO,
    "crear_cotizacion":                 AccionPRIS.TIPO_GENERAR_REPORTE,
    "cancelar_orden":                   AccionPRIS.TIPO_MODIFICAR_REGISTRO,
    "actualizar_resultado_laboratorio": AccionPRIS.TIPO_VALIDAR_RESULTADO,
    "guardar_resultado":                AccionPRIS.TIPO_VALIDAR_RESULTADO,
}


TOOLS_DESCRIPCION = """
HERRAMIENTAS DISPONIBLES (PRIS-Jarvis — Acceso Irrestricto) — responde con JSON puro:
{"tool": "nombre_herramienta", "args": {"arg1": "valor1"}}

═══ CONSULTA (solo lectura — sin confirmación) ═══
1.  buscar_paciente — args: nombre, telefono — Busca pacientes registrados
2.  obtener_estadisticas_dia — args: fecha (YYYY-MM-DD) — Estadísticas del día
3.  buscar_ordenes — args: folio, paciente_nombre, estado, hoy (bool) — Busca órdenes
4.  obtener_resultados_orden — args: folio — Resultados de laboratorio de un folio
5.  buscar_medicamento — args: nombre — Busca medicamentos en farmacia con stock
6.  buscar_estudio — args: nombre — Busca estudios clínicos y su precio
7.  obtener_saldo_caja — args: {} — Saldo y ventas del día
8.  listar_ordenes_pendientes — args: area, limite — Órdenes pendientes de procesar
9.  consultar_inventario — args: producto, limite — Stock real en lotes de productos
10. auditar_errores_recientes — args: modulo, limite — Errores activos en Sentinel
11. generar_corte_caja — args: fecha — Resumen de corte de caja
12. auditoria_sistema_completa — args: {} — Diagnóstico completo [SOLO SUPERUSUARIO]
13. consultar_expediente_paciente — args: paciente_id O nombre, limite_ordenes — Historial completo del paciente
14. consultar_indicadores_kpi — args: periodo (HOY/SEMANA/MES), categoria (LABORATORIO/FARMACIA/GENERAL) — KPIs para el director

═══ ESCRITURA — Acciones reales (REQUIEREN CONFIRMACIÓN HUMANA) ═══
15. crear_paciente — args: nombres, apellido_paterno, apellido_materno, telefono, fecha_nacimiento (YYYY-MM-DD), sexo (M/F/O), confirmado
    → Registra un paciente nuevo
16. crear_orden_laboratorio — args: paciente_id O paciente_nombre, estudios_ids ([int]) O estudios_nombres ([str]), metodo_pago, descuento_monto, confirmado
    → Crea una orden de laboratorio con estudios
17. cobrar_orden — args: folio_orden, metodo_pago (EFECTIVO/TARJETA/TRANSFERENCIA), monto_pagado, confirmado
    → Cobra y marca como PAGADA una orden
18. registrar_venta_farmacia — args: productos ([{nombre, cantidad}]), metodo_pago, paciente_nombre, confirmado
    → Registra una venta en farmacia POS
19. crear_cotizacion — args: paciente_nombre, estudios_nombres ([str]) O estudios_ids ([int]), descuento_porcentaje
    → Genera una cotización (sin confirmación — solo cálculo)
20. buscar_o_crear_paciente — args: nombres, apellido_paterno, telefono, fecha_nacimiento, sexo
    → Busca paciente y lo crea si no existe (flujo automático)
21. actualizar_resultado_laboratorio — args: folio_orden, nombre_parametro, valor, confirmado
    → Sugiere resultado (borrador IA); NO valida; el QFB debe validar en captura
22. guardar_resultado — args: folio_orden, nombre_parametro, valor — alias; mismo borrador IA
23. cancelar_orden — args: folio_orden, motivo, confirmado
    → Cancela una orden de laboratorio
24. aplicar_descuento_orden — args: folio_orden, descuento_monto O descuento_porcentaje, motivo, confirmado
    → Aplica o modifica el descuento de una orden
25. cambiar_estado_orden — args: folio_orden, nuevo_estado (PENDIENTE_PAGO/PAGADO/EN_PROCESO/CANCELADA), confirmado
    → Cambia estado operativo; PROHIBIDO: RESULTADOS_LISTOS y ENTREGADO (solo validación humana en captura)
26. programar_cita — args: paciente_id O paciente_nombre, fecha (YYYY-MM-DD), hora (HH:MM), tipo_cita (LABORATORIO/CONSULTORIO), motivo, confirmado
    → Programa una cita médica o de laboratorio
27. enviar_notificacion_paciente — args: paciente_id O paciente_nombre, canal (SMS/EMAIL/WHATSAPP), mensaje, confirmado
    → Envía una notificación al paciente
28. modificar_paciente — args: paciente_id, [telefono, email, sexo], confirmado
    → Actualiza datos de un paciente existente
29. gestionar_usuario — args: accion (CREAR/DESACTIVAR), username, nombres, apellido_paterno, email, rol, password (para CREAR), confirmado
    → Administra usuarios del sistema [DIRECTOR/ADMIN]
30. analizar_imagen_documento — args: imagen_b64 — Clasifica INE/receta/orden y pre-llena formulario de recepción
31. buscar_reactivo_laboratorio — args: nombre, limite — Busca reactivos/consumibles en el Silo de Laboratorio con stock disponible
32. consultar_stock_silos — args: silo (LAB/CONSULTORIO/GENERAL), nombre — Consulta stock en cualquier silo de inventario
33. validar_orden_laboratorio — args: folio_orden, confirmado — Valida y libera resultados de una orden (REQUIERE PIN del QFB en panel)
34. notificar_resultados_whatsapp — args: folio_orden, confirmado — Genera enlace WhatsApp para notificar al paciente que sus resultados están listos
35. consultar_manual_lab — args: pregunta — Consulta la biblioteca de manuales/protocolos del laboratorio (RAG). Responde preguntas como "¿cuál es el tubo para coagulación?", "tiempo de ayuno para glucosa", "protocolo de calibración"

PROTOCOLO OBLIGATORIO PARA ESCRITURAS:
- SIEMPRE usa confirmado:false primero → el resumen del plan aparece y el usuario confirma con "sí"/"confirmo"/"dale"
- SOLO ejecuta con confirmado:true cuando el usuario dice "sí", "confirmo", "procede" o equivalente
- Para flujos compuestos (registrar paciente + crear orden + cobrar), ejecuta UNA herramienta a la vez y espera confirmación
- NUNCA inventes datos. Si algo no existe, dilo claramente y ofrece buscar alternativas

FLUJO EJEMPLO — "necesito crear una orden de laboratorio":
1. Pregunta: "¿Para qué paciente? ¿Tiene registro en el sistema?"
2. buscar_paciente → si no existe: crear_paciente (con confirmación)
3. buscar_estudio para cada estudio mencionado
4. crear_orden_laboratorio con confirmado:false → muestra resumen → espera "sí"
5. crear_orden_laboratorio con confirmado:true → crea la orden y da el folio
6. Pregunta: "¿La cobro ahora?"

EJEMPLOS RÁPIDOS:
- "registra a Juan López tel 555-1234" → {"tool":"crear_paciente","args":{"nombres":"Juan","apellido_paterno":"López","telefono":"555-1234","confirmado":false}}
- "crea orden de BH y QS para María García" → primero buscar_paciente, luego crear_orden_laboratorio
- "cobra el folio F-001 en efectivo" → {"tool":"cobrar_orden","args":{"folio_orden":"F-001","metodo_pago":"EFECTIVO","confirmado":false}}
- "¿cuántas órdenes hay hoy?" → {"tool":"obtener_estadisticas_dia","args":{}}
- "expediente de Juan" → {"tool":"consultar_expediente_paciente","args":{"nombre":"Juan"}}
- "KPIs de hoy" → {"tool":"consultar_indicadores_kpi","args":{"periodo":"HOY","categoria":"GENERAL"}}
"""


# Escudo RBAC: mapeo de herramienta -> grupos permitidos
# None = sin restricción (cualquier usuario autenticado puede usar).
# Lista de grupos = requiere pertenecer al menos a uno de ellos.
_TOOL_RBAC = {
    # Consulta (sin restricción)
    "buscar_paciente":                    None,
    "obtener_estadisticas_dia":           None,
    "buscar_ordenes":                     None,
    "obtener_resultados_orden":           None,
    "buscar_medicamento":                 None,
    "buscar_estudio":                     None,
    "listar_ordenes_pendientes":          None,
    "consultar_inventario":               None,
    # Consulta restringida
    "guardar_resultado":                  ["LABORATORIO", "GERENCIA_OPERATIVA", "Administrador"],
    "obtener_saldo_caja":                 ["FARMACIA", "GERENCIA_OPERATIVA", "GERENCIA", "Administrador"],
    "auditar_errores_recientes":          ["GERENCIA_OPERATIVA", "GERENCIA", "Administrador"],
    "generar_corte_caja":                 ["FARMACIA", "GERENCIA_OPERATIVA", "GERENCIA", "Administrador"],
    "auditoria_sistema_completa":         [],   # Solo superusuario
    # Escritura — Recepción / Laboratorio
    "crear_paciente":                     ["RECEPCION", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "crear_orden_laboratorio":            ["RECEPCION", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "cobrar_orden":                       ["RECEPCION", "FARMACIA", "ADMIN", "Administrador", "GERENCIA", "LABORATORIO"],
    "buscar_o_crear_paciente":            ["RECEPCION", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "actualizar_resultado_laboratorio":   ["LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "cancelar_orden":                     ["RECEPCION", "ADMIN", "Administrador", "GERENCIA"],
    # Escritura — Farmacia
    "registrar_venta_farmacia":           ["FARMACIA", "ADMIN", "Administrador", "GERENCIA"],
    # Escritura — Cotizaciones (acceso amplio)
    "crear_cotizacion":                   ["RECEPCION", "LABORATORIO", "FARMACIA", "ADMIN", "Administrador", "GERENCIA"],
    "consultar_expediente_paciente":      ["MEDICOS", "MEDICO", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "aplicar_descuento_orden":            ["RECEPCION", "ADMIN", "Administrador", "GERENCIA"],
    "cambiar_estado_orden":               ["RECEPCION", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "programar_cita":                     ["RECEPCION", "MEDICOS", "MEDICO", "ADMIN", "Administrador", "GERENCIA"],
    "enviar_notificacion_paciente":       ["RECEPCION", "MEDICOS", "MEDICO", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "consultar_indicadores_kpi":          ["GERENCIA_OPERATIVA", "GERENCIA", "GERENTE", "ADMIN", "Administrador"],
    "modificar_paciente":                 ["RECEPCION", "MEDICOS", "MEDICO", "ADMIN", "Administrador", "GERENCIA"],
    "gestionar_usuario":                  ["DIRECTOR", "ADMIN", "Administrador", "GERENCIA"],
}


_SUPERUSER_ONLY_TOOLS = {"auditoria_sistema_completa"}


# PRIS/Prisci: cada herramienta respeta el rol del usuario en sesión.
# La confirmación humana es una capa adicional, no la única defensa.
_PRISCI_EXTERNAL_ALLOWED_TOOLS = {
    "buscar_estudio",
    "crear_cotizacion",
    "consultar_manual_lab",
    "buscar_medicamento",
}
