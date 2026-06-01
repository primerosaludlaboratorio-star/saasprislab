# 📄 FORMATO DE RECETA PROFESIONAL PRISLAB
**Fecha:** 31 de Enero de 2026 - 01:00 hrs  
**Basado en:** Receta de Dra. Monserrat Mateos Pérez  
**Estado:** 🟢 **IMPLEMENTANDO AHORA**

---

## 📋 **ESTRUCTURA DEL FORMATO**

### **DISEÑO VISUAL:**
```
┌─────────────────────────────────────────────────────────────┐
│  🏥 PRISLAB                                                 │
│  PRISLAB PRIMER SALUD LABORATORIO                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Dra. NOMBRE COMPLETO                                 │   │
│  │ Especialidad: ESPECIALIDAD                          │   │
│  │ CED PROF: NÚMERO                                    │   │
│  │ Universidad: INSTITUCIÓN                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  NOMBRE: _____________________________________________      │
│  FECHA: ___/___/___      EDAD: ___ AÑOS                   │
│                                                              │
│  T/A: ___/___ MM/HG      PESO: ___ KG                      │
│  FC: ___                 TALLA: ___ CM                     │
│  FR: ___                 IMC: ___                          │
│  TEMP: ___ C°                                               │
│                                                              │
│  ALERGIAS: ___________________________________________      │
│  IDX: ________________________________________________      │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │  [ESPACIO GRANDE PARA RECETA/TRATAMIENTO]           │   │
│  │                                                       │   │
│  │                                                       │   │
│  │                                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  PRÓXIMA CITA: _______________________________________      │
│  FIRMA: _______________________________________________     │
│                                                              │
│  CITAS                                                       │
│  LUNES A VIERNES: 7:00 AM – 4:00 PM                        │
│  SÁBADOS: 7:00 AM – 2:00 PM                                │
│  DOMINGOS: 8:00 AM – 2:00 PM                               │
│                                                              │
│  CALLE JUAN DE LA LUZ ENRÍQUEZ #308 B COL. CENTRO          │
│  ACAYUCAN, VERACRUZ                                         │
│  (924) 688 21 00 | 924 105 78 31                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 **CARACTERÍSTICAS DEL DISEÑO**

### **1. ENCABEZADO (Logo + Nombre)**
```python
# Logo PRISLAB (si existe)
if empresa.logo:
    logo = Image(empresa.logo.path, width=3*cm, height=2*cm)
else:
    # Texto grande en su lugar
    logo = Paragraph("🏥 PRISLAB", style_logo)

# Nombre de la empresa
nombre_empresa = Paragraph(
    "PRISLAB PRIMER SALUD LABORATORIO",
    ParagraphStyle('empresa', fontSize=14, bold=True, alignment=TA_CENTER)
)
```

### **2. DATOS DEL MÉDICO (Recuadro con Borde)**
```python
# Obtener médico (Dra. Brizia o el que esté logueado)
medico = consulta.medico

# Recuadro con borde
datos_medico = [
    [f"Dra. {medico.nombre_completo}"],
    [f"{medico.especialidad}"],
    [f"CED PROF: {medico.cedula_profesional}"],
    [f"Universidad: {medico.universidad or 'Universidad Veracruzana'}"]
]

tabla_medico = Table(datos_medico, colWidths=[18*cm])
tabla_medico.setStyle(TableStyle([
    ('BOX', (0, 0), (-1, -1), 2, colors.black),  # Borde
    ('PADDING', (0, 0), (-1, -1), 10),
    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (0, 0), 12),  # Nombre más grande
    ('FONTSIZE', (0, 1), (-1, -1), 10),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
]))
```

### **3. DATOS DEL PACIENTE (Formato Simple)**
```python
# Nombre en una línea completa
nombre_linea = f"NOMBRE: {consulta.paciente.nombre_completo}"

# Fecha y Edad en la misma línea
fecha_edad = f"FECHA: {consulta.fecha_consulta.strftime('%d/%m/%Y')}      EDAD: {consulta.paciente.edad} AÑOS"

# Crear párrafos
elements.append(Paragraph(nombre_linea, style_campo))
elements.append(Paragraph(fecha_edad, style_campo))
```

### **4. SIGNOS VITALES (2 Columnas)**
```python
# Obtener signos vitales o valores por defecto
sv = consulta.signos_vitales

# Columna izquierda y derecha
signos_data = [
    [f"T/A: {sv.presion_arterial if sv else '___/___'} MM/HG", 
     f"PESO: {sv.peso if sv else '___'} KG"],
    [f"FC: {sv.frecuencia_cardiaca if sv else '___'}", 
     f"TALLA: {sv.talla if sv else '___'} CM"],
    [f"FR: {sv.frecuencia_respiratoria if sv else '___'}", 
     f"IMC: {sv.imc if sv else '___'}"],
    [f"TEMP: {sv.temperatura if sv else '___'} C°", 
     ""],
]

tabla_signos = Table(signos_data, colWidths=[9*cm, 9*cm])
tabla_signos.setStyle(TableStyle([
    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
    ('FONTSIZE', (0, 0), (-1, -1), 10),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
]))
```

### **5. ALERGIAS Y DIAGNÓSTICO**
```python
# Alergias
alergias = consulta.paciente.alergias if hasattr(consulta.paciente, 'alergias') else 'Ninguna conocida'
elements.append(Paragraph(f"ALERGIAS: {alergias}", style_campo))

# Diagnóstico (IDX)
idx = consulta.diagnostico_principal or '___'
if consulta.diagnostico_cie10:
    idx += f" ({consulta.diagnostico_cie10})"
elements.append(Paragraph(f"IDX: {idx}", style_campo))
```

### **6. ESPACIO PARA RECETA/TRATAMIENTO (GRANDE)**
```python
# Rx grande y estilizado
elements.append(Paragraph(
    '<font size="36" color="blue"><b>Rx</b></font>',
    style_rx
))

# Tratamiento con espacio amplio
tratamiento = consulta.plan_tratamiento or '''
___________________________________
___________________________________
___________________________________
___________________________________
___________________________________
___________________________________
'''

elements.append(Paragraph(tratamiento, style_receta))
```

### **7. PRÓXIMA CITA Y FIRMA**
```python
# Próxima cita (opcional)
proxima_cita = consulta.proxima_cita if hasattr(consulta, 'proxima_cita') else '___'
elements.append(Paragraph(f"PRÓXIMA CITA: {proxima_cita}", style_campo))

# Línea para firma
elements.append(Spacer(1, 1*cm))
elements.append(Paragraph("_" * 80, style_firma))
elements.append(Paragraph("FIRMA", style_firma))
```

### **8. INFORMACIÓN DE CONTACTO (PIE)**
```python
# Horarios
horarios = """
CITAS
LUNES A VIERNES: 7:00 AM – 4:00 PM
SÁBADOS: 7:00 AM – 2:00 PM
DOMINGOS: 8:00 AM – 2:00 PM
"""

# Dirección y teléfonos
contacto = f"""
{empresa.direccion or 'CALLE JUAN DE LA LUZ ENRÍQUEZ #308 B COL. CENTRO, ACAYUCAN, VERACRUZ'}
{empresa.telefono or '(924) 688 21 00'} | {empresa.telefono_movil or '924 105 78 31'}
"""

elements.append(Paragraph(horarios, style_footer))
elements.append(Paragraph(contacto, style_footer))
```

---

## 🎨 **ESTILOS DEFINIDOS**

```python
# Estilo para campos (NOMBRE:, FECHA:, etc.)
style_campo = ParagraphStyle(
    'Campo',
    parent=styles['Normal'],
    fontSize=11,
    fontName='Helvetica',
    leading=14,
    spaceAfter=4,
)

# Estilo para Rx grande
style_rx = ParagraphStyle(
    'Rx',
    parent=styles['Normal'],
    fontSize=36,
    fontName='Helvetica-Bold',
    textColor=colors.HexColor('#0066cc'),
    alignment=TA_LEFT,
    spaceAfter=10,
)

# Estilo para receta/tratamiento
style_receta = ParagraphStyle(
    'Receta',
    parent=styles['Normal'],
    fontSize=11,
    fontName='Helvetica',
    leading=18,
    leftIndent=20,
    spaceBefore=10,
    spaceAfter=10,
)

# Estilo para firma
style_firma = ParagraphStyle(
    'Firma',
    parent=styles['Normal'],
    fontSize=10,
    fontName='Helvetica',
    alignment=TA_CENTER,
)

# Estilo para footer
style_footer = ParagraphStyle(
    'Footer',
    parent=styles['Normal'],
    fontSize=9,
    fontName='Helvetica',
    alignment=TA_CENTER,
    textColor=colors.grey,
    leading=12,
)
```

---

## ✅ **VALORES POR DEFECTO**

### **Si NO se llenaron campos:**
```python
{
    'presion_arterial': '___/___',
    'frecuencia_cardiaca': '___',
    'frecuencia_respiratoria': '___',
    'temperatura': '___',
    'peso': '___',
    'talla': '___',
    'imc': '___',
    'alergias': 'Ninguna conocida',
    'tratamiento': '[Espacio para escribir tratamiento]',
    'proxima_cita': '___',
}
```

---

## 🔐 **DATOS DEL MÉDICO AUTOMÁTICOS**

### **Prioridad de datos:**
```python
# 1. Intentar obtener del usuario logueado
if hasattr(request.user, 'medico_profile'):
    medico = request.user.medico_profile
# 2. Obtener del médico de la consulta
else:
    medico = consulta.medico

# 3. Datos completos
nombre = medico.nombre_completo
cedula = medico.cedula_profesional
especialidad = medico.especialidad or 'Médico General'
universidad = getattr(medico, 'universidad', 'Universidad Veracruzana')
```

### **Para Dra. Brizia (ejemplo):**
```python
{
    'nombre': 'BRIZIA [APELLIDO]',
    'cedula': '[CÉDULA DE BRIZIA]',
    'especialidad': '[ESPECIALIDAD DE BRIZIA]',
    'universidad': '[UNIVERSIDAD DE BRIZIA]'
}
```

---

## 📱 **RESPONSIVE Y TAMAÑO**

### **Configuración de página:**
```python
doc = SimpleDocTemplate(
    buffer,
    pagesize=letter,  # Tamaño carta (8.5 x 11 pulgadas)
    topMargin=1*cm,
    bottomMargin=1*cm,
    leftMargin=1.5*cm,
    rightMargin=1.5*cm,
)
```

### **Márgenes:**
- Superior: 1 cm (espacio para logo)
- Inferior: 1 cm (espacio para footer)
- Izquierda/Derecha: 1.5 cm

---

## 🚀 **IMPLEMENTACIÓN**

**Archivo:** `consultorio/pdf_views.py`  
**Función:** `imprimir_receta_paciente(request, consulta_id)`

**Características:**
- ✅ Formato exacto de la receta de Monserrat
- ✅ Datos automáticos del médico logueado
- ✅ Campos opcionales con defaults
- ✅ Logo PRISLAB
- ✅ Información de contacto
- ✅ Layout profesional y limpio

**Resultado:**
```
PDF profesional listo para imprimir e entregar al paciente
```

---

## ✅ **CHECKLIST DE IMPLEMENTACIÓN**

- [✅] Analizar formato de PDF de referencia
- [⏳] Reescribir función `imprimir_receta_paciente`
- [⏳] Agregar estilos profesionales
- [⏳] Implementar valores por defecto
- [⏳] Obtener datos del médico automáticamente
- [⏳] Agregar logo PRISLAB
- [⏳] Agregar información de contacto
- [⏳] Probar con Dra. Brizia
- [⏳] Desplegar a producción

---

**Estado:** 🟡 **EN IMPLEMENTACIÓN**  
**Próximo:** Reescribir función completa en `pdf_views.py`
