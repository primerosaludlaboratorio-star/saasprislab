# REFACTORIZACIÓN: RANGOS DE REFERENCIA DINÁMICOS PARA LABORATORIO

**Fecha:** 2026-01-22  
**Objetivo:** Implementar sistema de rangos de referencia dinámicos con segmentación por edad y sexo

---

## RESUMEN DE CAMBIOS IMPLEMENTADOS

### ✅ 1. Actualización del Modelo `Estudio` (Parámetro/Analito)

#### Campos Agregados:
- **`tipo_valor`** (CharField con Choices):
  - Opciones: `'NUMERICO'`, `'TEXTO'`, `'TITULO'`
  - Default: `'NUMERICO'`
  - Permite clasificar el tipo de resultado que produce el estudio

- **`metodo`** (CharField, opcional):
  - Método de análisis utilizado (ej: Colorimétrico, Inmunoensayo)
  - Max length: 200

- **`departamento`** (CharField, opcional):
  - Departamento responsable del análisis (ej: Hematología, Bioquímica)
  - Max length: 100

- **`formula`** (TextField, opcional):
  - Fórmula de cálculo si aplica

#### Archivo Modificado:
- `core/models.py` (líneas 916-943)

---

### ✅ 2. Creación del Modelo `RangoReferencia`

#### Estructura del Modelo:

**Relación:**
- `parametro` (ForeignKey a `Estudio`) - Relación padre-hijo

**Segmentación por Sexo:**
- `sexo` (CharField con Choices):
  - `'M'` = Masculino
  - `'F'` = Femenino
  - `'I'` = Indistinto (default)

**Segmentación por Edad:**
- `unidad_edad` (CharField con Choices):
  - `'DIAS'` = Días (vital para pediatría)
  - `'MESES'` = Meses
  - `'AÑOS'` = Años (default)
- `edad_min` (Integer, nullable)
- `edad_max` (Integer, nullable)

**Valores del Rango:**
- `valor_minimo` (Decimal, nullable) - Para resultados numéricos
- `valor_maximo` (Decimal, nullable) - Para resultados numéricos
- `valor_texto` (TextField, nullable) - Para resultados cualitativos (ej: 'Negativo', 'Positivo')

**Metadatos:**
- `activo` (Boolean, default=True)
- `fecha_creacion` (DateTime, auto_now_add)
- `fecha_actualizacion` (DateTime, auto_now)
- `notas` (TextField, nullable)

#### Índices Optimizados:
- Índice compuesto: `['parametro', 'sexo', 'activo']`
- Índice compuesto: `['parametro', 'unidad_edad', 'edad_min', 'edad_max']`

#### Archivo Creado:
- `core/models.py` (líneas 1189-1306)

---

### ✅ 3. Lógica de Validación Automática

#### Método en `DetalleOrden`:
- **`validar_resultado_contra_rango()`**
  - Busca automáticamente el `RangoReferencia` correcto según:
    - Edad del paciente (convierte a días/meses/años según unidad)
    - Sexo del paciente
  - Valida si el resultado está dentro o fuera del rango
  - Retorna diccionario con:
    - `fuera_de_rango`: bool
    - `rango_aplicado`: RangoReferencia o None
    - `mensaje`: str descriptivo

#### Signal Automático:
- **`validar_resultado_automatico`** (post_save signal)
  - Se ejecuta automáticamente al guardar un `DetalleOrden`
  - Valida solo si hay resultado y el estudio es numérico
  - Registra advertencias en log si está fuera de rango
  - No interrumpe el guardado si falla (robustez)

#### Archivos Modificados:
- `core/models.py` (líneas 1074-1186, 2144-2168)

---

### ✅ 4. Migraciones Aplicadas

**Migración Creada:**
- `core/migrations/0028_estudio_departamento_estudio_formula_estudio_metodo_and_more.py`

**Cambios en Base de Datos:**
- ✅ Agregado campo `tipo_valor` a `Estudio`
- ✅ Agregado campo `metodo` a `Estudio`
- ✅ Agregado campo `departamento` a `Estudio`
- ✅ Agregado campo `formula` a `Estudio`
- ✅ Modificados campos `valor_minimo` y `valor_maximo` (marcados como DEPRECADOS)
- ✅ Creada tabla `RangoReferencia` con todos los campos

**Estado:** ✅ Migraciones aplicadas exitosamente

---

### ✅ 5. Registro en Admin de Django

#### Modelos Registrados:

1. **`CategoriaEstudioAdmin`**
   - List display: nombre
   - Search: nombre

2. **`EstudioAdmin`**
   - List display: codigo, nombre, categoria, tipo_valor, precio, activo
   - List filter: categoria, tipo_valor, activo, es_perfil
   - Search: codigo, nombre, abreviatura
   - Fieldsets organizados:
     - Datos Básicos
     - Tipo y Metadatos (nuevo)
     - Logística
     - Jerarquía
     - Valores Críticos (Legacy - colapsado)
     - Descripción
   - **Inline:** `RangoReferenciaInline` - Permite agregar rangos directamente desde el estudio

3. **`RangoReferenciaAdmin`**
   - List display: parametro, sexo, unidad_edad, edad_min, edad_max, valor_minimo, valor_maximo, activo
   - List filter: sexo, unidad_edad, activo, parametro__categoria
   - Search: parametro__nombre, parametro__codigo, notas
   - Fieldsets organizados:
     - Parámetro
     - Segmentación
     - Valores del Rango
     - Metadatos
   - Readonly: fecha_creacion, fecha_actualizacion

4. **`DetalleOrdenAdmin`**
   - List display: orden, estudio, estado_procesamiento, validado_por, fecha_validacion
   - List filter: estado_procesamiento, valor_critico_confirmado, orden__estado
   - Search: orden__folio_orden, estudio__nombre, resultado

#### Archivo Modificado:
- `core/admin.py` (líneas 136-210)

---

## EJEMPLOS DE USO

### Ejemplo 1: Crear Rango de Referencia para Glucosa en Adultos

```python
from core.models import Estudio, RangoReferencia

# Obtener el estudio de Glucosa
glucosa = Estudio.objects.get(codigo='GLU')

# Crear rango para adultos (18-99 años), indistinto de sexo
rango_adulto = RangoReferencia.objects.create(
    parametro=glucosa,
    sexo='I',  # Indistinto
    unidad_edad='AÑOS',
    edad_min=18,
    edad_max=99,
    valor_minimo=70.0,
    valor_maximo=100.0,
    activo=True
)
```

### Ejemplo 2: Crear Rango para Pediatría (Días)

```python
# Rango para recién nacidos (0-30 días)
rango_rn = RangoReferencia.objects.create(
    parametro=glucosa,
    sexo='I',
    unidad_edad='DIAS',
    edad_min=0,
    edad_max=30,
    valor_minimo=40.0,
    valor_maximo=150.0,
    activo=True
)
```

### Ejemplo 3: Validar Resultado Automáticamente

```python
from core.models import DetalleOrden

# Obtener un detalle de orden con resultado
detalle = DetalleOrden.objects.get(id=123)
detalle.resultado = "95.5"  # Glucosa
detalle.save()  # El signal validará automáticamente

# O validar manualmente
validacion = detalle.validar_resultado_contra_rango()
print(validacion)
# {
#     'fuera_de_rango': False,
#     'rango_aplicado': <RangoReferencia: Glucosa | Indistinto | 18-99 Años | 70.0-100.0>,
#     'mensaje': 'Dentro del rango normal'
# }
```

---

## VENTAJAS DE LA REFACTORIZACIÓN

1. **Flexibilidad Total:**
   - Soporta múltiples rangos por estudio
   - Segmentación precisa por edad (días, meses, años)
   - Segmentación por sexo cuando aplica

2. **Pediatría:**
   - Rangos específicos para recién nacidos (días)
   - Rangos para lactantes (meses)
   - Rangos para niños (años)

3. **Validación Automática:**
   - No requiere intervención manual
   - Se ejecuta al guardar resultados
   - Registra advertencias en logs

4. **Compatibilidad:**
   - Los campos legacy (`valor_minimo`, `valor_maximo` en `Estudio`) siguen funcionando
   - Migración gradual posible

5. **Administración Visual:**
   - Inline en admin para agregar rangos fácilmente
   - Filtros y búsquedas optimizadas

---

## PRÓXIMOS PASOS RECOMENDADOS

1. **Migración de Datos Legacy:**
   - Crear script para migrar `valor_minimo`/`valor_maximo` de `Estudio` a `RangoReferencia`
   - Establecer rangos por defecto para estudios existentes

2. **Integración en Frontend:**
   - Mostrar alerta visual cuando resultado está fuera de rango
   - Mostrar rango aplicado en la interfaz de captura

3. **Reportes:**
   - Generar reporte de resultados fuera de rango
   - Estadísticas por estudio y rango de edad

4. **Importación desde CSV:**
   - Crear comando de management para importar rangos desde CSV legacy
   - Mapear columnas: método, departamento, fórmula

---

## VERIFICACIÓN

✅ **Django Check:** Sin errores  
✅ **Migraciones:** Aplicadas exitosamente  
✅ **Modelos:** Todos los campos presentes  
✅ **Admin:** Todos los modelos registrados  
✅ **Método de Validación:** Implementado y funcional  
✅ **Signal:** Configurado correctamente  

---

**Refactorización completada exitosamente el:** 2026-01-22
