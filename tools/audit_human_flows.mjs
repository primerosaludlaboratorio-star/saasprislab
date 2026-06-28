/**
 * audit_human_flows.mjs
 * El "cerebro" del agente — flujos humanos reales por módulo, paso a paso.
 * Importado por run_ai_agent_audit.mjs.
 */

// Instrucción que se inyecta al inicio de CADA módulo
export const CODE_INSPECTION_RULE = `REGLA ROOT-CAUSE: Ante cualquier hallazgo HIGH/MEDIUM/CRITICAL:
1. inspect_code(query="término clave") — busca en views, templates, urls.py.
2. Si find_elements devuelve items con name/placeholder/id, úsalos como selector exacto en fill_input.
3. Si inspect_code localiza un archivo, llama read_code_file(file_path="...") para leer el contexto exacto.
4. En report_finding incluye root_cause="archivo:línea — explicación" y recommendation="fix concreto".`;

export const MODULE_FLOWS = [
  {
    id: 'login',
    name: 'LOGIN',
    steps: 8,
    prompt: (base, user, pass) => `
INSTRUCCIÓN CRÍTICA: Usa únicamente HTTP (no HTTPS). La URL base ya incluye el protocolo correcto.
1. navigate("${base}/login/")
2. fill_input(selector="input[name='username']", value="${user}")
3. fill_input(selector="input[type='password']", value="${pass}")
4. click(text="Iniciar Sesión")
5. get_page_state() → si URL no es /login/, login exitoso
6. Si URL sigue siendo /login/, report_finding(CRITICAL, "Login fallido", "Credenciales incorrectas o servidor no responde")
7. Si URL cambió, report_finding(INFO, "Login exitoso", "Usuario autenticado correctamente")
8. finish_module()
`,
  },
  {
    id: 'dashboard',
    name: 'DASHBOARD',
    steps: 5,
    prompt: (base) => `
1. navigate("${base}/")
2. get_page_state()
3. screenshot("dashboard_general")
4. find_elements("nav a, .sidebar a, .menu a")
5. finish_module()
`,
  },
  {
    id: 'laboratorio',
    name: 'LABORATORIO',
    steps: 22,
    prompt: (base) => `
MÓDULO: LABORATORIO
URLs: ${base}/laboratorio/recepcion/ | /laboratorio/lista-trabajo/ | /laboratorio/consulta-ordenes/ | /lims/estudios/

PASOS OBLIGATORIOS:
1. navigate("${base}/laboratorio/recepcion/")
2. get_page_state()
3. screenshot("lab_recepcion")
4. find_elements("input, select, button") → busca el campo de búsqueda de paciente
5. Intenta fill_input con el campo que encuentres (prueba: "input[placeholder*='aciente']", "input[name*='paciente']", "input[type='search']", "input[type='text']:first-child") → escribe "garcia"
6. Espera 1.5 seg, get_page_state() → ¿apareció lista de resultados o autocomplete?
7. Reporta si la búsqueda de paciente funciona (INFO) o no muestra nada (MEDIUM)
8. navigate("${base}/laboratorio/lista-trabajo/")
9. get_page_state()
10. find_elements("table, thead, tbody tr") → verifica que hay filas de datos
11. screenshot("lab_lista_trabajo")
12. Reporta las columnas que ves y si hay órdenes en la tabla
13. Si hay filas, intenta click en la primera fila o botón de acción visible
14. navigate("${base}/laboratorio/consulta-ordenes/")
15. get_page_state()
16. find_elements("input[type='date'], input[type='text'], select") → verifica filtros
17. screenshot("lab_consulta_ordenes")
18. navigate("${base}/lims/estudios/")
19. get_page_state() → ¿carga un catálogo de estudios o redirige a /admin/?
20. Si redirige a /admin/, reporta HIGH: "Catálogo de estudios redirige al Admin de Django"
21. screenshot("lab_lims_estudios")
22. finish_module()
`,
  },
  {
    id: 'farmacia',
    name: 'FARMACIA / PDV',
    steps: 24,
    prompt: (base) => `
MÓDULO: FARMACIA / PDV
URLs: ${base}/farmacia/ | /farmacia/pdv/ | /farmacia/inventario/ | /farmacia/historial-ventas/

PASOS OBLIGATORIOS:
1. navigate("${base}/farmacia/")
2. get_page_state() → verifica métricas del dashboard de farmacia
3. screenshot("farmacia_dashboard")
4. navigate("${base}/farmacia/pdv/")
5. get_page_state()
6. screenshot("farmacia_pdv_carga")
7. find_elements("input") → lista TODOS los inputs disponibles en el PDV
8. Para cada input que encuentres, intenta escribir "amox" usando fill_input
9. get_page_state() → ¿apareció lista de productos/autocomplete?
10. Si no aparece nada, intenta click en algún botón visible y repite búsqueda
11. screenshot("farmacia_pdv_busqueda")
12. Reporta si el buscador del PDV funciona (INFO) o está roto (HIGH)
13. find_elements("button") → busca botones de "Agregar", "Carrito", "Cobrar"
14. Reporta si existen los botones de flujo de venta
15. navigate("${base}/farmacia/inventario/")
16. get_page_state()
17. find_elements("table tbody tr, .product-row") → cuenta productos en inventario
18. screenshot("farmacia_inventario")
19. Reporta cuántos productos hay en inventario (INFO) o si está vacío (MEDIUM)
20. navigate("${base}/farmacia/historial-ventas/")
21. get_page_state()
22. find_elements("table tbody tr") → verifica registros de ventas
23. screenshot("farmacia_historial")
24. finish_module()
`,
  },
  {
    id: 'consultorio',
    name: 'CONSULTORIO',
    steps: 18,
    prompt: (base) => `
MÓDULO: CONSULTORIO
URLs: ${base}/consultorio/ | /medico/consulta/ | /medico/ultrasonido/lista-trabajo/

PASOS OBLIGATORIOS:
1. navigate("${base}/consultorio/")
2. get_page_state()
3. screenshot("consultorio_agenda")
4. find_elements("button, a") → busca "Nueva Cita", "Agendar", "Mi Agenda"
5. Reporta si la agenda/calendario está visible
6. find_elements("input") → busca buscador de paciente
7. Si hay buscador, fill_input con "garcia" y verifica resultado
8. navigate("${base}/medico/consulta/")
9. get_page_state()
10. find_elements("form, input, select, button") → verifica formulario SOAP
11. screenshot("consultorio_consulta_medica")
12. Reporta si el formulario de consulta médica (SOAP) está disponible
13. navigate("${base}/medico/ultrasonido/lista-trabajo/")
14. get_page_state()
15. find_elements("table, .worklist") → verifica lista de trabajo de ultrasonido
16. screenshot("consultorio_ultrasonido")
17. Reporta estado del módulo de ultrasonido
18. finish_module()
`,
  },
  {
    id: 'director',
    name: 'DIRECTOR / WAR ROOM',
    steps: 22,
    prompt: (base) => `
MÓDULO: DIRECTOR / WAR ROOM
URLs: ${base}/director/ | /director/buzon/ | /director/ranking/ | /director/autorizaciones/ | /director/auditoria/incidencias/

PASOS OBLIGATORIOS:
1. navigate("${base}/director/")
2. get_page_state()
3. find_elements(".card, .kpi, canvas, .metric") → verifica KPIs y gráficas
4. screenshot("director_dashboard")
5. Reporta si los KPIs tienen datos reales o están en cero/vacíos
6. navigate("${base}/director/buzon/")
7. get_page_state()
8. find_elements(".kanban, .column, .card, .task") → verifica columnas del Kanban
9. screenshot("director_buzon")
10. Reporta cuántas columnas y tarjetas hay en el buzón
11. navigate("${base}/director/ranking/")
12. get_page_state()
13. find_elements("table tbody tr") → cuenta empleados en el ranking
14. screenshot("director_ranking")
15. Reporta cuántos empleados aparecen y si tienen scores
16. navigate("${base}/director/autorizaciones/")
17. get_page_state()
18. Reporta si hay autorizaciones pendientes o el estado vacío
19. navigate("${base}/director/auditoria/incidencias/")
20. get_page_state()
21. screenshot("director_incidencias")
22. finish_module()
`,
  },
  {
    id: 'seguridad',
    name: 'SEGURIDAD',
    steps: 16,
    prompt: (base) => `
MÓDULO: SEGURIDAD
URLs: ${base}/seguridad/2fa/ | /seguridad/sesiones/ | /seguridad/auditoria/ | /seguridad/auditoria/logs/

PASOS OBLIGATORIOS:
1. navigate("${base}/seguridad/2fa/")
2. get_page_state()
3. find_elements("button, form, input") → verifica opciones de configurar 2FA
4. screenshot("seguridad_2fa")
5. Reporta si la configuración de 2FA está disponible
6. navigate("${base}/seguridad/sesiones/")
7. get_page_state()
8. find_elements("table tbody tr") → verifica sesiones activas
9. screenshot("seguridad_sesiones")
10. Reporta cuántas sesiones activas hay visibles
11. navigate("${base}/seguridad/auditoria/")
12. get_page_state()
13. screenshot("seguridad_auditoria_dashboard")
14. navigate("${base}/seguridad/auditoria/logs/")
15. get_page_state()
16. find_elements("table tbody tr, .log-entry") → verifica que hay registros
17. screenshot("seguridad_logs")
18. Reporta si el log de auditoría tiene registros recientes
19. finish_module()
`,
  },
  {
    id: 'academia',
    name: 'ACADEMIA',
    steps: 14,
    prompt: (base) => `
MÓDULO: ACADEMIA
URLs: ${base}/academia/ | /academia/accesos/otorgar/

PASOS OBLIGATORIOS:
1. navigate("${base}/academia/")
2. get_page_state()
3. find_elements(".course, .card, .curso, article, .module-card") → verifica cursos disponibles
4. screenshot("academia_dashboard")
5. Reporta cuántos cursos hay visibles y si tienen contenido
6. Si hay al menos un curso visible, haz click en el primero
7. get_page_state() → verifica que carga el detalle del curso (videos, materiales)
8. screenshot("academia_curso_detalle")
9. Reporta si el contenido del curso carga correctamente
10. navigate("${base}/academia/accesos/otorgar/")
11. get_page_state()
12. find_elements("form, select, input, button") → verifica formulario de otorgar accesos
13. screenshot("academia_accesos")
14. finish_module()
`,
  },
  {
    id: 'bienestar',
    name: 'BIENESTAR',
    steps: 16,
    prompt: (base) => `
MÓDULO: BIENESTAR
URLs: ${base}/bienestar/ | /bienestar/chat/ | /bienestar/diario/ | /bienestar/recursos/

PASOS OBLIGATORIOS:
1. navigate("${base}/bienestar/")
2. get_page_state()
3. screenshot("bienestar_dashboard")
4. Reporta qué secciones están visibles en el dashboard de bienestar
5. navigate("${base}/bienestar/chat/")
6. get_page_state()
7. find_elements("input, textarea, button") → verifica campo de chat con PRIS
8. screenshot("bienestar_chat")
9. Si hay campo de texto, escribe "Hola PRIS" y verifica si responde
10. navigate("${base}/bienestar/diario/")
11. get_page_state()
12. find_elements("form, textarea, input, button") → verifica formulario del diario
13. screenshot("bienestar_diario")
14. navigate("${base}/bienestar/recursos/")
15. get_page_state()
16. find_elements(".resource, .card, article") → verifica recursos disponibles
17. screenshot("bienestar_recursos")
18. finish_module()
`,
  },
  {
    id: 'contabilidad',
    name: 'CONTABILIDAD',
    steps: 16,
    prompt: (base) => `
MÓDULO: CONTABILIDAD
URLs: ${base}/contabilidad/ | /contabilidad/facturas/ | /contabilidad/clientes/

PASOS OBLIGATORIOS:
1. navigate("${base}/contabilidad/")
2. get_page_state()
3. screenshot("contabilidad_dashboard")
4. navigate("${base}/contabilidad/facturas/")
5. get_page_state()
6. find_elements("table tbody tr") → cuenta facturas existentes
7. screenshot("contabilidad_facturas")
8. Reporta cuántas facturas hay en la lista
9. find_elements("button, a") → busca "Nueva Factura", "Crear", "Emitir"
10. Si existe botón de nueva factura, haz click y verifica que abre el formulario
11. get_page_state() → verifica campos del formulario de factura
12. screenshot("contabilidad_nueva_factura")
13. navigate("${base}/contabilidad/clientes/")
14. get_page_state()
15. find_elements("table tbody tr") → cuenta clientes registrados
16. screenshot("contabilidad_clientes")
17. finish_module()
`,
  },
  {
    id: 'ia',
    name: 'IA / PRIS',
    steps: 18,
    prompt: (base) => `
MÓDULO: IA / PRIS
URLs: ${base}/ia/ | /ia/asistente/ | /pris/acciones/

PASOS OBLIGATORIOS:
1. navigate("${base}/ia/")
2. get_page_state()
3. screenshot("ia_dashboard")
4. Reporta qué herramientas de IA están disponibles en el panel
5. navigate("${base}/ia/asistente/")
6. get_page_state()
7. find_elements("input, textarea") → busca campo de consulta al asistente
8. screenshot("ia_asistente_vacio")
9. Si hay campo de texto, fill_input con "¿Cuáles son los valores normales de glucosa en ayuno?"
10. find_elements("button[type='submit'], button") → busca botón de enviar
11. click en el botón de enviar
12. Espera 3 segundos, get_page_state() → ¿respondió el asistente?
13. screenshot("ia_asistente_respuesta")
14. Reporta si el asistente médico responde (INFO) o falla (HIGH)
15. navigate("${base}/pris/acciones/")
16. get_page_state()
17. find_elements("table, .action-list, .card") → verifica lista de acciones PRIS
18. screenshot("ia_pris_acciones")
19. finish_module()
`,
  },
  {
    id: 'finanzas',
    name: 'FINANZAS',
    steps: 14,
    prompt: (base) => `
MÓDULO: FINANZAS
URLs: ${base}/finanzas/lab/caja/ | /finanzas/farmacia/caja/ | /finanzas/master/

PASOS OBLIGATORIOS:
1. session_check() → verifica que la sesión está activa
2. navigate("${base}/finanzas/lab/caja/")
3. get_page_state()
4. find_elements(".total, .saldo, .corte, table, .card") → verifica datos de caja
5. screenshot("finanzas_caja_lab")
6. Reporta si la caja del laboratorio muestra montos del día
7. navigate("${base}/finanzas/farmacia/caja/")
8. get_page_state()
9. screenshot("finanzas_caja_farmacia")
10. Reporta si la caja de farmacia tiene datos
11. navigate("${base}/finanzas/master/")
12. get_page_state()
13. find_elements("canvas, .chart, .total-consolidado, .card") → verifica dashboard maestro
14. screenshot("finanzas_master")
15. finish_module()
`,
  },

  {
    id: 'pacientes',
    name: 'PACIENTES',
    steps: 20,
    prompt: (base) => `
MÓDULO: PACIENTES
URLs: ${base}/pacientes/ | /pacientes/nuevo/ | /pacientes/buscar/

PASOS OBLIGATORIOS:
1. session_check()
2. navigate("${base}/pacientes/")
3. get_page_state()
4. screenshot("pacientes_lista")
5. find_elements("table tbody tr") → cuenta pacientes registrados
6. Reporta cuántos pacientes hay en la lista (INFO) o si está vacía (MEDIUM)
7. find_elements("input[type='search'], input[placeholder*='aciente'], input[name*='search']") → busca el campo de búsqueda
8. Si hay campo de búsqueda, fill_input con "garcia" y verifica resultados
9. screenshot("pacientes_busqueda")
10. navigate("${base}/pacientes/nuevo/")
11. get_page_state()
12. find_elements("form input, form select, form textarea") → lista todos los campos del formulario
13. screenshot("pacientes_nuevo_form")
14. Reporta si el formulario de nuevo paciente tiene: nombre, apellido, fecha nacimiento, CURP/DNI, teléfono, seguro
15. Intenta fill_input en el campo de nombre con "Paciente Test"
16. get_page_state() → verifica validaciones en tiempo real
17. Reporta si la validación del formulario funciona (INFO) o está rota (MEDIUM)
18. navigate("${base}/pacientes/buscar/")
19. get_page_state()
20. screenshot("pacientes_busqueda_avanzada")
21. finish_module()
`,
  },

  {
    id: 'expediente',
    name: 'EXPEDIENTE CLÍNICO',
    steps: 22,
    prompt: (base) => `
MÓDULO: EXPEDIENTE CLÍNICO
URLs: ${base}/expediente/ | /expediente/historial/ | /pacientes/ (click en un paciente)

PASOS OBLIGATORIOS:
1. session_check()
2. navigate("${base}/pacientes/")
3. get_page_state()
4. find_elements("table tbody tr a, .patient-row, tr td a") → busca links a expedientes
5. Si hay al menos una fila, haz click en el primer paciente para abrir su expediente
6. get_page_state() → verifica que se abre la vista de expediente
7. screenshot("expediente_vista_general")
8. find_elements("nav, .tabs, .tab-list, ul.nav") → verifica pestañas del expediente
9. Reporta qué secciones tiene el expediente (consultas, laboratorio, recetas, etc.)
10. Intenta hacer click en la pestaña de "Laboratorio" o "Resultados" si existe
11. get_page_state()
12. screenshot("expediente_tab_lab")
13. Intenta hacer click en la pestaña de "Recetas" o "Medicamentos" si existe
14. get_page_state()
15. screenshot("expediente_tab_recetas")
16. find_elements("button, a") → busca "Nueva Nota", "Agregar Consulta", "Nueva Receta"
17. Reporta si los botones de acción del expediente están presentes (INFO) o ausentes (HIGH)
18. navigate("${base}/expediente/")
19. get_page_state()
20. screenshot("expediente_index")
21. Reporta estado general del módulo de expediente clínico
22. finish_module()
`,
  },

  {
    id: 'configuracion',
    name: 'CONFIGURACIÓN',
    steps: 20,
    prompt: (base) => `
MÓDULO: CONFIGURACIÓN DEL SISTEMA
URLs: ${base}/configuracion/ | /configuracion/empresa/ | /configuracion/usuarios/ | /configuracion/modulos/

PASOS OBLIGATORIOS:
1. session_check()
2. navigate("${base}/configuracion/")
3. get_page_state()
4. screenshot("config_dashboard")
5. find_elements("nav a, .sidebar a, .menu-item a") → lista opciones del menú de configuración
6. Reporta qué secciones de configuración están disponibles
7. navigate("${base}/configuracion/empresa/")
8. get_page_state()
9. find_elements("form input, form select, form textarea") → verifica campos del perfil de empresa
10. screenshot("config_empresa")
11. Reporta si los datos de empresa (nombre, RFC, logo, dirección) son editables
12. navigate("${base}/configuracion/usuarios/")
13. get_page_state()
14. find_elements("table tbody tr") → cuenta usuarios del sistema
15. screenshot("config_usuarios")
16. Reporta cuántos usuarios hay y si hay botón "Nuevo Usuario" (INFO) o no hay gestión de usuarios (HIGH)
17. navigate("${base}/configuracion/modulos/")
18. get_page_state()
19. find_elements(".module-toggle, input[type='checkbox'], .switch") → verifica toggles de módulos
20. screenshot("config_modulos")
21. Reporta si se pueden activar/desactivar módulos del sistema
22. finish_module()
`,
  },
];
