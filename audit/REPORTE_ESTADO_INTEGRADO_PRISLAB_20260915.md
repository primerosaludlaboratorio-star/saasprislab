# PRISLAB SaaS - Reporte de estado integrado

Fecha: 2026-09-15
Rama: `release/v1.0-local`
Commit de referencia: `88c22cb73496799b49e9f390f2dc84990db07728`
Estado remoto: local y `origin/release/v1.0-local` coinciden en el mismo SHA.

## Proposito

Este documento es la fuente de contexto para GitHub Copilot, Codex y cualquier
testigo independiente que revise PRISLAB. Separa hechos comprobados, limites
de entorno y trabajo pendiente. No debe interpretarse como aprobacion de
produccion.

## Fuente de verdad

- Checkout canonico: `C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master`
- Remoto: `https://github.com/primerosaludlaboratorio-star/saasprislab.git`
- Rama: `release/v1.0-local`
- Tip auditado: `88c22cb73496799b49e9f390f2dc84990db07728`
- No usar copias Desktop alternativas, reportes antiguos ni otro worktree como
  fuente sin comparar SHA.

## Commits relevantes

- `6e2d07a`: coverage fijado en requirements.
- `43e1a8a`: actualizacion de acciones CI.
- `3ddf65a`: plan integral de auditoria.
- `1efc133`: generador de FREEZE.
- `4613c29`: generador de inventario.
- `88c22cb`: controles negativos y portabilidad de tooling.

## Artefactos de Fase 2

Ubicacion externa:
`C:\Users\jonil\Desktop\PRISLAB_AUDIT_EVIDENCE\PRISLAB_AUDIT_PHASE2_88C22CB_CLEAN_20260915`

| Artefacto | SHA-256 |
|---|---|
| `FREEZE.json` | `4810312948923843AD7541555517BF65250A9FB4D7FC7360C191DB8B45ED5E23` |
| `INVENTARIO.json` | `99E9260EDBE2A1AE26BBC765DC5C49073874BBB01BE2AF1A3F5E647A6AD88229` |
| `INVENTARIO.csv` | `EF7DDAB26BFF8B8E6B1BA07AC470D697B98E59B302697A3638AF766C40C134E1` |

El worktree usado para esta corrida fue limpio: 2164 archivos versionados y
0 no versionados.

## Conteos reproducidos

- Aplicaciones Django: 33
- Modelos: 266
- Vistas propias: 92
- Rutas URL anidadas: 1956
- Migraciones: 239
- Comandos: 174
- Dependencias del lock: 120

## Correcciones del tooling

Los generadores de auditoria fueron corregidos y publicados para:

- evitar fallos de consola CP1252 en Windows;
- calcular hashes Git sin depender de shell POSIX;
- recorrer URLconf anidado;
- evitar vistas importadas de otros modulos;
- incluir todas las dependencias, no solo las primeras 50;
- escribir JSON y CSV en UTF-8.

El modo `dry-run` de controles negativos funciona, pero sus cinco detectores
son referencias hipoteticas que no existen como bateria ejecutable. Resultado:
`skipped/errors`, no PASS.

## Estado de Fase 2

`FASE_2_CERRADA - FUENTE E INVENTARIO VERIFICADOS`

Esto certifica congelamiento e inventario desde el tip indicado. No certifica
seguridad completa, integracion PostgreSQL, flujos humanos ni produccion.

## Cinco puntos que no se pueden cerrar con la maquina local actual

### 1. Python 3.12 y Django del lock

La maquina local ejecuta Python `3.14.0` y el runtime disponible carga Django
`5.1.15`. El archivo `requirements.lock` fija Django `5.2.17`. Por tanto, un
test local con este interprete no prueba el entorno bloqueado de CI/despliegue.

### 2. PostgreSQL 16

No hay `psql` ni servidor PostgreSQL disponible localmente. La evidencia de
SQLite o de una configuracion no conectada no certifica transacciones,
bloqueos, indices, constraints ni migraciones reales en PostgreSQL 16.

### 3. Controles negativos reales

El script existe, pero sus pruebas detectoras son nombres de referencia; no
hay cinco detectores implementados que puedan fallar deliberadamente y ser
restaurados en un entorno descartable. No se debe ejecutar una siembra en la
rama auditada ni en produccion.

### 4. Flujos E2E humanos

El inventario no equivale a usar la interfaz. Falta ejecutar en staging los
flujos completos de farmacia, recepcion, laboratorio/LIMS, inventario, PDFs,
pagos, devoluciones, cancelaciones, errores, reintentos y roles reales.

### 5. Staging, produccion y testigo independiente

La maquina local no contiene la evidencia de un despliegue reproducible con
imagen, digest, Nginx/ingress, workers, backup/restauracion, smoke postdeploy
y repeticion independiente. Un `git push` o un health check no sustituyen esa
prueba.

## Estado del checkout de trabajo

El checkout principal conserva cambios locales ajenos y no committeados en
archivos de pruebas, reportes y scripts. No se incluyeron en este reporte ni
se deben descartar sin revision del propietario. La auditoria de Fase 2 uso un
worktree limpio separado, por lo que esos cambios no contaminaron los conteos.

## Reglas para continuar

1. No declarar PASS por reportes historicos.
2. Cada corrida debe registrar RUN_ID, SHA, entorno, conteos, logs y hashes.
3. No imprimir ni modificar credenciales, tokens, PHI o datos productivos.
4. Ejecutar Python 3.12/PostgreSQL 16 en CI o staging real.
5. Implementar detectores negativos reales en una copia descartable.
6. Ejecutar los flujos completos mediante la interfaz y conservar evidencia.
7. Reconciliar GitHub, Codex y el testigo independiente por SHA y artefactos.
8. Desplegar solo despues de cerrar los gates aplicables.

## Dictamen integrado

`LISTO_PARA_FASE_3`

No es `LISTO_PARA_VALIDACION_HUMANA` ni `APROBADO_PARA_PRODUCCION`.
