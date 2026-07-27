# Datos requeridos para cerrar CCI/Westgard

Este documento define la información que debe entregar el laboratorio antes de
declarar cerrado el control de calidad interno. No se deben crear mediciones
ficticias para completar el flujo.

## 1. Equipo y canal

- Fabricante, modelo, número de serie e identificador interno.
- Sucursal, área, responsable y estado operativo.
- Analito, código LIMS, unidad y método.
- Reactivo asociado, marca, lote vigente y fecha de apertura.
- Instalación, mantenimiento vigente y certificado de calibración.
- Intervalo de mantenimiento, calibración y revisión metrológica.
- Interfaz utilizada: manual, archivo, HL7 u otra.

## 2. Material de control

- Fabricante, nombre comercial, nivel y número de lote.
- Analito, método y equipo al que aplica.
- Unidad de medida y factor de conversión, si existe.
- Media objetivo y desviación estándar del inserto o del laboratorio.
- Rango aceptable, caducidad y fecha de apertura.
- Condiciones de almacenamiento y estabilidad después de apertura.
- Número de pruebas disponibles y cantidad remanente.
- Inserto o certificado del fabricante como archivo trazable.
- Responsable que verificó la configuración y fecha de aprobación.

## 3. Reglas y frecuencia

- Reglas Westgard aplicables y política aprobada.
- Número de niveles por corrida.
- Frecuencia: inicio de turno, cambio de lote, calibración, mantenimiento,
  corrida y repetición.
- Situaciones que bloquean el resultado de paciente.
- Personas que pueden liberar el canal y evidencia requerida.
- Tiempo de retención de resultados, gráficas y decisiones.

## 4. Mediciones reales

- Fecha, hora, operador y turno.
- Equipo, analito, nivel y lote de control.
- Resultado, unidad y valor convertido si aplica.
- Lote de reactivo, calibrador y consumibles relevantes.
- Corrida, calibración o mantenimiento relacionado.
- Estado calculado, regla disparada y decisión del responsable.
- Observaciones, repetición y archivo fuente si vino por interfaz.

## 5. Cuando exista rechazo

- Descripción de la desviación y pacientes potencialmente afectados.
- Revisión de reactivo, control, calibración, mantenimiento y temperatura.
- Acción inmediata: detener, repetir, recalibrar o cambiar lote.
- Causa raíz y acción correctiva/preventiva.
- Resultado posterior que demuestra recuperación.
- Responsable, fecha de autorización y evidencia adjunta.

## 6. Información adicional recomendable

- Catálogo de pruebas, perfiles, paquetes y analitos con sus unidades.
- Relación prueba-analito-reactivo-equipo-consumible y cantidades por prueba.
- Lotes y caducidades de reactivos, calibradores, controles e insumos.
- Procedimientos normalizados y versiones vigentes.
- Personal autorizado para captura, revisión, liberación y metrología.
- Registro de no conformidades y acciones correctivas.
- Rondas EQA/PEEC, proveedor, periodo, resultados y evaluación.
- Indicadores de rechazo CCI, repeticiones, liberación, caducidades y consumo.

## 7. Orden recomendado de captura

1. Equipos y analitos.
2. Métodos, unidades y relaciones con pruebas LIMS.
3. Reactivos, calibradores, controles y consumibles con lote.
4. Media, desviación estándar y reglas aprobadas.
5. Procedimientos, responsables y permisos.
6. Mediciones reales de varios días y turnos.
7. Rechazos, acciones correctivas y liberaciones.
8. EQA/PEEC y métricas de desempeño.

## Criterio de cierre

CCI/Westgard podrá declararse operativo únicamente cuando exista al menos un
canal real configurado con material vigente, parámetros aprobados, mediciones
reales suficientes para evaluar las reglas, evidencia de una decisión de
revisión y verificación de que un rechazo bloquea el canal hasta su liberación
autorizada.
