# PROTOCOLO MAESTRO DE AUDITORIA MULTI-IA PARA PRISLAB

> Ver estado canónico actual de rama y hallazgos: `docs/ai_coordination/ESTADO_CANONICO_RAMA_RELEASE_V1_0_LOCAL.md`

Fecha de consolidacion: 2026-06-18  
Autor de consolidacion: Codex  
Uso previsto: entregar a Imperium, Claude, Cascada, Copilot u otra IA auditora  
Modo de uso recomendado: por bloques, no todo de una sola vez

## 1. Objetivo de este documento

Este documento existe para que cualquier IA auditora entienda con precision:

- el estado real del proyecto
- que ya fue estabilizado tecnicamente
- que no debe entrar en modo rescate caotico
- que debe auditar con rigor profesional
- que debe producir hallazgos claros
- que no debe modificar codigo si se le pide modo solo auditoria

La meta es fortificar PRISLAB como si lo estuviera revisando un equipo de varios senior developers desde angulos distintos:

- arquitectura
- logica de negocio
- seguridad
- multitenancy
- produccion
- despliegue
- pruebas funcionales
- paridad contra legacy
- coherencia operativa

## 2. Regla principal de operacion

Si esta IA entra en modo auditoria:

- no debe cambiar codigo
- no debe crear parches
- no debe reescribir archivos
- no debe tocar configuraciones productivas
- no debe inventar hallazgos
- no debe dar consejos genericos

Solo debe:

- leer
- revisar
- comparar
- ejecutar pruebas permitidas
- detectar bugs, riesgos, regresiones y huecos funcionales
- generar reportes de alta calidad

Si se le autoriza una segunda fase de correccion, eso ocurre despues, por separado.

## 3. Regla documental obligatoria del proyecto

En PRISLAB existe una regla ya establecida:

Toda persona, agente o IA que haga cualquiera de estas acciones:

- cambio de codigo
- cambio de infraestructura
- cambio de variables de entorno
- despliegue
- prueba funcional
- correccion de bug
- carga de catalogos
- validacion de produccion

debe actualizar en el mismo movimiento:

1. [CHECKLIST_CONTROL_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\CHECKLIST_CONTROL_PRISLAB.md)
2. [REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md)

Si no se actualizan esos dos documentos, el trabajo no se considera cerrado.

Nota:

Si la IA esta en modo solo auditoria, no tiene que modificar codigo, pero su reporte debe dejar claro que cualquier cambio posterior debera reflejarse en esos dos archivos.

## 4. Estado real del proyecto al momento de esta auditoria

PRISLAB SaaS ya no esta en fase de rescate.

Esta en fase de:

- endurecimiento
- validacion por bloques
- auditoria cruzada
- cierre de ultima milla
- paridad final contra legacy

Estado tecnico confirmado:

- `manage.py check` OK
- `makemigrations --check --dry-run` OK
- `manage.py test` global OK
- resultado global: `251 tests OK`, `23 skipped`, `0 failures`, `0 errors`
- `PRIS IA` ya no esta bloqueado por el stub muerto
- `Academia` ya esta integrada y tiene pruebas
- el smoke script de integracion ya no rompe el descubrimiento de pruebas
- el proveedor de IA ya tiene fallback seguro entre Gemini y DeepSeek

Veredicto tecnico:

- la base del codigo es estable para revision seria
- no significa que el proyecto este funcionalmente terminado al 100% como reemplazo del legacy
- si significa que cualquier auditoria nueva debe concentrarse en hallar huecos reales, no en diagnosticar una base rota

## 5. Documentos fuente de verdad

Toda IA auditora debe leer primero estos documentos, en este orden:

1. [REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md)
2. [CHECKLIST_CONTROL_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\CHECKLIST_CONTROL_PRISLAB.md)
3. [DEPLOY.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\DEPLOY.md)
4. [README.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\README.md)
5. [env_produccion.txt](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\env_produccion.txt)
6. [nginx/conf.d/prislab.conf](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\nginx\conf.d\prislab.conf)
7. [verify_deployment.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\verify_deployment.sh)
8. [scripts/deploy_vps.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\deploy_vps.sh)
9. [scripts/aplicar_fixes_produccion.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\aplicar_fixes_produccion.sh)
10. [test_integracion_real.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\test_integracion_real.py)

Documentos de apoyo recomendados:

- [PLAN_CIERRE_MIGRACION_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\PLAN_CIERRE_MIGRACION_PRISLAB.md)
- [PLAN_BLOQUE_POR_BLOQUE_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\PLAN_BLOQUE_POR_BLOQUE_PRISLAB.md)
- [ANEXO_TECNICO_PRISLAB_LEGACY_VS_SAAS.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\ANEXO_TECNICO_PRISLAB_LEGACY_VS_SAAS.md)

## 6. Que ya se hizo y no debe perderse de vista

### 6.1 IA y PRIS

Archivo clave:

- [core/views/pris_ia.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\views\pris_ia.py)

Ya se corrigio:

- el retorno temprano que dejaba muerto el flujo real del asistente
- ahora el flujo real con Gemini, function calling, herramientas, confirmaciones y `AccionPRIS` ya esta activo

### 6.2 Cliente de IA unificado

Archivo clave:

- [core/utils/gemini_client.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\utils\gemini_client.py)

Ya se robustecio:

- `GOOGLE_API_KEY` queda como clave canonica
- se mantienen aliases `GOOGLE_GEMINI_API_KEY` y `GEMINI_API_KEY`
- fallback seguro entre Gemini y DeepSeek cuando una variable vieja queda mal
- mensajes mas claros para errores 403

### 6.3 Google Drive

Archivos clave:

- [config/drive_credentials.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\config\drive_credentials.py)
- [core/utils/google_drive.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\utils\google_drive.py)
- [config/storage_backends.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\config\storage_backends.py)

Ya esta definido:

- Drive usa cuenta de servicio, no API key
- sin credenciales el sistema usa fallback local
- errores de permisos ya entregan mensajes utiles

### 6.4 Academia

Archivos clave:

- [academia/models.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\academia\models.py)
- [academia/views.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\academia\views.py)
- [academia/tests.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\academia\tests.py)

Ya esta definido:

- modulo integrado dentro del sistema
- acceso limitado por empresa
- blindaje tenant para no otorgar accesos cross-tenant por error
- pruebas de acceso, reproduccion y heartbeat

### 6.5 Produccion

Infraestructura objetivo:

- VPS Vultr Ubuntu 26.04 LTS
- Nginx
- Gunicorn
- PostgreSQL
- Redis
- Celery
- Celery Beat
- dominio principal `prislab.labcorecloud.com`

Guia canónica actual:

- [DEPLOY.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\DEPLOY.md)

No usar como fuente principal:

- documentos historicos de Cloud Run
- documentos historicos de Railway
- documentos historicos de Nixpacks

## 7. Filosofia de auditoria que debe seguir la IA

La IA auditora no debe hacer una revision vaga.

Debe pensar como un equipo elite de multiples senior developers revisando desde angulos distintos:

- uno ve bugs
- uno ve arquitectura
- uno ve permisos
- uno ve multi-tenant
- uno ve despliegue
- uno ve UX funcional real
- uno ve coherencia operativa contra legacy

La auditoria debe buscar:

- bugs reales
- riesgos reales
- regresiones reales
- huecos funcionales
- incoherencias entre frontend y backend
- problemas de despliegue
- gaps contra el checklist
- diferencias importantes frente al legacy

No debe generar:

- ruido
- recomendaciones genéricas
- opiniones vagas
- "sería bueno considerar..."
- listas de buenas prácticas sin evidencia

## 8. Clasificacion obligatoria de hallazgos

Todo hallazgo debe clasificarse como una de estas categorias:

- critico
- alto
- medio
- bajo
- falso positivo

Y ademas debe clasificarse por naturaleza:

- bug real
- riesgo de seguridad
- regresion
- hueco funcional
- inconsistencia documental
- deuda tecnica
- diferencia contra legacy

## 9. Formato obligatorio de cada hallazgo

Por cada hallazgo la IA debe entregar:

1. modulo
2. severidad
3. archivo o zona
4. funcion, vista, servicio o flujo afectado
5. descripcion clara del problema
6. impacto real
7. evidencia
8. reproduccion o razon tecnica
9. recomendacion concreta
10. si bloquea operacion o no

Si no encuentra problema real, debe decirlo explicitamente.

## 10. Capas que debe revisar la auditoria

### 10.1 Codigo local

Revisar:

- bugs logicos
- validaciones faltantes
- regresiones
- errores de permisos
- multi-tenant
- flujos rotos entre frontend y backend
- IA
- Drive
- despliegue
- Academia

### 10.2 Paridad funcional contra legacy

No basta con que "el codigo se vea bien".

La IA debe revisar contra el checklist los bloques pendientes:

- Bloque 4 - Pacientes
- Bloque 5 - Clientes
- Bloque 6 - Médicos
- Bloque 11 - Programa de lealtad
- Bloque 12 - Microbiología
- Bloque 13 - Reportes
- Bloque 14 - Integraciones externas
- Bloque 15 - Validación final

Debe determinar:

- que ya existe
- que esta parcial
- que falta
- que no coincide con legacy

### 10.3 Produccion

Si tiene acceso a produccion, debe revisar:

- login
- recepcion y ordenes
- pacientes
- laboratorio
- farmacia
- consultorio
- academia
- reportes
- integraciones

Si no tiene acceso real a produccion, entonces debe auditar:

- [DEPLOY.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\DEPLOY.md)
- [env_produccion.txt](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\env_produccion.txt)
- [scripts/deploy_vps.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\deploy_vps.sh)
- [scripts/aplicar_fixes_produccion.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\aplicar_fixes_produccion.sh)
- [verify_deployment.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\verify_deployment.sh)

## 11. Orden recomendado de auditoria por bloques

Para no saturar a la IA y para mantener alta calidad, la auditoria debe darse por bloques.

Orden recomendado:

1. Estado base y documentos de control
2. Despliegue e infraestructura
3. IA, Drive y configuracion de credenciales
4. Recepcion y ordenes
5. Pacientes
6. Laboratorio
7. Farmacia
8. Consultorio
9. Seguridad y permisos
10. Academia
11. Reportes
12. Integraciones externas
13. Comparativa contra legacy
14. Veredicto final de reemplazo

## 12. Que debe ejecutar tecnicamente

Antes de opinar fuerte, la IA debe intentar validar al menos:

1. `manage.py check`
2. `manage.py makemigrations --check --dry-run`
3. `manage.py test`

Si ejecuta pruebas parciales, debe decir exactamente cuales.

Si no puede ejecutar algo, debe decirlo.

## 13. Que no debe hacer

La IA auditora no debe:

- asumir que algo esta roto solo porque no lo entiende rapido
- deducir secretos reales a partir de placeholders
- confundir warning esperado con bug confirmado
- reportar como fallo una ruta protegida que responde 403 o 404 de forma correcta
- mezclar recomendaciones de refactor con bugs bloqueantes
- sugerir cambios a ciegas sin evidencia

## 14. Como deben usarse varias IAs a la vez

La estrategia correcta es auditoria cruzada.

Cada IA puede ver cosas distintas:

- Claude puede profundizar arquitectura y logica
- Cascada puede ser fuerte en validacion integral o consistencia
- Copilot puede encontrar huecos de implementacion o regresiones chicas
- Imperium puede operar como auditor integral dentro del IDE

La gracia no es que todas hagan lo mismo.
La gracia es triangular hallazgos.

Luego una sola capa de consolidacion humana o tecnica decide:

- que es bug real
- que es falso positivo
- que se corrige primero
- que se documenta

## 15. Instruccion recomendada para una IA auditora

Texto sugerido:

```text
Modo auditoría estricta.
No modificar código.
No crear parches.
No reescribir archivos.
Solo:
- revisar código
- revisar arquitectura
- revisar despliegue
- revisar producción si tiene acceso
- ejecutar pruebas permitidas
- detectar bugs, riesgos, regresiones y huecos funcionales
- generar reportes claros y priorizados

Clasifica todo hallazgo como:
- crítico
- alto
- medio
- bajo
- falso positivo

Por cada hallazgo incluye:
- módulo
- archivo o zona
- función o flujo afectado
- impacto
- evidencia
- recomendación

Antes de auditar, leer:
1. REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md
2. CHECKLIST_CONTROL_PRISLAB.md
3. DEPLOY.md

No cambiar nada.
Solo auditar y reportar.
```

## 16. Prioridades reales del proyecto hoy

Lo pendiente ya no esta principalmente en estabilidad base del codigo.

Lo pendiente esta en:

- pruebas funcionales reales en produccion
- paridad contra legacy
- cierre por bloques del checklist
- revision de flujos modulo por modulo
- consolidacion final del reemplazo total

## 17. Meta final

La meta no es solo que "corra".

La meta es:

- reemplazar al sistema legacy con paridad operativa real
- dejar PRISLAB SaaS verificable, desplegable y auditable
- construir una pared extremadamente solida
- terminar el proyecto lo mas pronto posible sin perder trazabilidad, control ni calidad

## 18. Cierre

Este documento debe usarse como guia maestra para cualquier auditoria nueva.

Si una IA produce hallazgos, esos hallazgos deben consolidarse despues en:

- [CHECKLIST_CONTROL_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\CHECKLIST_CONTROL_PRISLAB.md)
- [REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md)

Sin esa consolidacion, la auditoria no esta cerrada.
