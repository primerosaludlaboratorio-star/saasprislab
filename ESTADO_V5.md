# Estado de Preparación V 5.0 - Núcleo Pris-Valle

## ✅ COMPLETADO

### Arquitectura Base
- ✅ Plan de integración documentado (`PLAN_INTEGRACION_V5.md`)
- ✅ Estructura de módulos creada
- ✅ Modelos base implementados
- ✅ Migraciones generadas y aplicadas

### Modelos Creados

#### Seguridad (`seguridad/models.py`)
- ✅ `ConfiguracionSeguridad` - Configuración de alertas y números de emergencia
- ✅ `AlertaPanico` - Registro de alertas de pánico

#### IoT (`iot/models.py`)
- ✅ `Kiosco` - Dispositivos kiosco (tablets)
- ✅ `VerificacionKiosco` - Verificaciones pendientes/completadas

#### IA (`ia/models.py`)
- ✅ `CotizacionOCR` - Resultados de OCR sobre recetas
- ✅ `TranscripcionVoz` - Transcripciones de audio

#### Reglas de Negocio (`reglas_negocio/validadores.py`)
- ✅ `validar_triple_llave()` - Validación antes de envío
- ✅ `validar_valor_panico()` - Detección de valores críticos
- ✅ `requiere_doble_validacion()` - Lógica de doble validación
- ✅ `validar_corte_ciego()` - Validación de corte ciego

### Extensiones a Modelos Existentes

#### Laboratorio
- ✅ `Estudio.rango_panico_min` - Valor mínimo de pánico
- ✅ `Estudio.rango_panico_max` - Valor máximo de pánico

#### Pacientes
- ✅ `Paciente.telefono_verificado` - Flag de verificación
- ✅ `Paciente.codigo_verificacion_sms` - Código de verificación
- ✅ `Paciente.fecha_verificacion_telefono` - Fecha de verificación

---

## 🔄 PENDIENTE (Próximos Sprints)

### Sprint 1: Triple Llave (Prioridad Alta)
- [ ] Integrar `validar_triple_llave()` en vista de envío de resultados
- [ ] Crear endpoint de verificación de teléfono por SMS
- [ ] Agregar UI para mostrar errores de Triple Llave

### Sprint 2: Corte Ciego (Prioridad Alta)
- [ ] Modificar vista `corte_caja_dia()` para ocultar monto esperado
- [ ] Agregar campo `monto_reportado` si no existe
- [ ] Implementar cálculo de diferencia y registro de incidencias

### Sprint 3: Valores de Pánico (Prioridad Media)
- [ ] Extender `Resultado.save()` para detectar pánico automáticamente
- [ ] Crear vista de doble validación
- [ ] Bloquear impresión/envío si hay pánico sin doble validación

### Sprint 4: Cotizador OCR (Prioridad Media)
- [ ] Integrar Google Cloud Vision o Tesseract
- [ ] Crear endpoint `/ia/cotizar-ocr/`
- [ ] Implementar matching de estudios detectados
- [ ] Crear UI para subir imagen y mostrar resultados

### Sprint 5: Oído Clínico (Prioridad Media)
- [ ] Integrar OpenAI Whisper API
- [ ] Crear endpoint `/ia/transcribir-voz/`
- [ ] Implementar extracción de entidades (LLM)
- [ ] Agregar botón "Grabar Entrevista" en captura

### Sprint 6: Módulo Kiosco (Prioridad Baja - Requiere Hardware)
- [ ] Implementar polling endpoint `/api/kiosco/pendientes/`
- [ ] Crear vista para tablet (`/kiosco/verificacion/`)
- [ ] Agregar botón "Enviar a Kiosco" en recepción
- [ ] (Opcional) Implementar WebSockets con Django Channels

### Sprint 7: Botón de Pánico (Prioridad Baja)
- [ ] Agregar JavaScript global para capturar atajo de teclado
- [ ] Crear endpoint `/seguridad/panico/`
- [ ] Integrar WhatsApp/Telegram API
- [ ] Crear dashboard de alertas de seguridad

---

## 📦 Dependencias Futuras

**No instalar aún** - Solo cuando se implemente cada módulo:

```bash
# Para Kiosco (WebSockets)
pip install channels channels-redis

# Para OCR
pip install google-cloud-vision

# Para Voz
pip install openai

# Para Alertas
pip install twilio python-telegram-bot
```

---

## 🎯 Estado Actual

**Base de Datos:** ✅ Migraciones aplicadas  
**Modelos:** ✅ Creados y listos  
**Validadores:** ✅ Implementados  
**Integración:** ⏳ Pendiente (Sprint 1)

---

## 📝 Notas para Desarrollo

1. **Compatibilidad**: Todos los campos nuevos son opcionales (`null=True, blank=True`)
2. **Testing**: Las pruebas E2E existentes siguen funcionando
3. **Feature Flags**: Considerar agregar flags en `settings.py` para activar/desactivar módulos
4. **Documentación**: Cada módulo debe tener su propio README cuando se implemente

---

**Última actualización:** 2026-01-20  
**Próxima revisión:** Después de Sprint 1 (Triple Llave)
