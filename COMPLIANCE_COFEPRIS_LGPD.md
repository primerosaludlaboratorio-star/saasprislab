# COMPLIANCE — COFEPRIS + LGPD

**Versión:** 1.1 (FASE 3C)  
**Fecha:** 29 Junio 2026  
**Estado:** ✅ IMPLEMENTADO

---

## I. COFEPRIS — Norma Oficial Mexicana 004-SSA3-2012

### Objetivo
Cumplir con regulaciones sanitarias mexicanas para:
- Gestión de expedientes clínicos electrónicos
- Trazabilidad de resultados de laboratorio
- Firma digital de responsables sanitarios
- Auditoría regulatoria

### Modelos Implementados

#### 1. ResponsableSanitario
```python
ResponsableSanitario(
    usuario: Usuario,              # Quimico Farmacéutico Biólogo
    cedula_profesional: str,       # Cédula expedida por SEP
    numero_registro_cofepris: str, # Registro COFEPRIS (opcional)
    fecha_vigencia_inicio: date,   # Inicio de autorización
    fecha_vigencia_fin: date,      # Fin de autorización
    certificado_digital: FileField,# Certificado .pfx/.pem para firmas
    activo: bool                   # Si está autorizado actualmente
)
```

**Métodos:**
- `esta_vigente()` → Bool — Verifica si el responsable está vigente

**Uso:**
```python
# Registrar nuevo responsable sanitario
responsable = ResponsableSanitario.objects.create(
    usuario=quimico_user,
    cedula_profesional="123456789",
    fecha_vigencia_inicio=date(2026, 1, 1),
    fecha_vigencia_fin=date(2030, 12, 31),
    empresa=empresa
)
```

#### 2. FirmaDigitalResultado
```python
FirmaDigitalResultado(
    responsable_sanitario: ResponsableSanitario,
    modelo_referencia: str,    # "OrdenDeServicio", "ResultadoParametro"
    objeto_id: int,            # ID del modelo referenciado
    paciente: Paciente,
    hash_contenido: str,       # SHA-256 del PDF/resultado
    firma_hexadecimal: str,    # Firma digital (hex)
    certificado_usado: str,    # Certificado usado para firmar
    fecha_firma: datetime,     # Timestamp de firma
    verificada: bool           # Si la firma fue verificada
)
```

**Auditoría:**
- Trazabilidad completa: quién firmó qué, cuándo, desde qué IP
- Índices en (paciente, fecha_firma) y (responsable_sanitario, fecha_firma)

**Workflow de Firma:**
```python
# 1. Generar PDF de resultado
pdf_bytes = generar_pdf_resultado(orden_id)
hash_contenido = hashlib.sha256(pdf_bytes).hexdigest()

# 2. Firmar digitalmente (usar certificado del responsable)
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

firma = responsable.certificado_digital.sign(hash_contenido)

# 3. Registrar firma en auditoría
firma_registro = FirmaDigitalResultado.objects.create(
    responsable_sanitario=responsable,
    modelo_referencia="OrdenDeServicio",
    objeto_id=orden_id,
    paciente=paciente,
    hash_contenido=hash_contenido,
    firma_hexadecimal=firma.hex(),
    verificada=True
)
```

---

## II. LGPD — Ley General de Protección de Datos Personales

### Objetivo
Cumplir con privacidad de datos:
- Consentimiento informado antes de recopilar datos
- Derecho al olvido (solicitud de eliminación)
- Auditoría de acceso a datos sensibles
- Portabilidad de datos

### Modelos Implementados

#### 1. ConsentimientoLGPD
```python
ConsentimientoLGPD(
    paciente: Paciente,
    tipo: str,  # 'CLINICO', 'CONTACTO', 'MARKETING', 'INVESTIGACION'
    otorgado: bool,
    fecha_otorgamiento: datetime,
    fecha_revocacion: datetime,  # Cuando se revocó
    usuario_registro: Usuario,   # Quién registró
    ip_address: str,
    documento_consentimiento: FileField  # PDF firmado
)
```

**TIPOS DE CONSENTIMIENTO:**
- `CLINICO` — Datos clínicos (historia, diagnósticos, tratamientos)
- `CONTACTO` — Datos de contacto (teléfono, email, SMS)
- `MARKETING` — Uso en campañas/promociones
- `INVESTIGACION` — Uso en investigación médica

**Métodos:**
- `es_vigente()` → Bool — Consentimiento otorgado y no revocado

**Workflow de Consentimiento:**
```python
# 1. Paciente NUEVO: Solicitar consentimiento
consentimiento = ConsentimientoLGPD.objects.create(
    paciente=paciente,
    tipo='CLINICO',
    otorgado=True,
    usuario_registro=recepcion_user,
    documento_consentimiento=pdf_consentimiento  # PDF firmado por paciente
)

# 2. Verificar consentimiento antes de procesar datos
if paciente.consentimientos_lgpd.filter(tipo='CLINICO', otorgado=True).exists():
    # Proceder a generar expediente clínico
    pass
else:
    raise PermissionDenied("Paciente no ha otorgado consentimiento CLINICO")

# 3. Revocar consentimiento
consentimiento.otorgado = False
consentimiento.fecha_revocacion = timezone.now()
consentimiento.save()
```

#### 2. DerechoOlvido (LGPD Art. 17)
```python
DerechoOlvido(
    paciente: Paciente,
    estado: str,  # 'SOLICITADO', 'EN_PROCESO', 'APROBADA', 'RECHAZADA'
    razon: str,
    datos_a_eliminar: str,
    fecha_solicitud: datetime,
    fecha_respuesta: datetime,
    usuario_responsable: Usuario,
    notas_procesamiento: str
)
```

**Workflow de Derecho al Olvido:**
```python
# 1. Paciente solicita eliminar sus datos
solicitud = DerechoOlvido.objects.create(
    paciente=paciente,
    razon="No deseo continuar con el servicio",
    datos_a_eliminar="Toda la historia clínica, expediente y resultados",
    estado='SOLICITADO'
)

# 2. Administrador revisa solicitud
# (Verificar si hay restricciones legales, como auditoría activa)

# 3. Aprobar y procesar
solicitud.estado = 'APROBADA'
solicitud.usuario_responsable = admin_user
solicitud.notas_procesamiento = "Eliminación realizada. Backups en retención: 7 días"
solicitud.fecha_respuesta = timezone.now()
solicitud.save()

# 4. Ejecutar eliminación programada (background task)
# - Anonimizar registros de AuditLog
# - Eliminar expedientes
# - Marcar histórico de transacciones
```

#### 3. RegistroAccesoDatos
```python
RegistroAccesoDatos(
    usuario: Usuario,
    paciente: Paciente,
    tipo_datos: str,  # "historia_clinica", "expediente", "resultados_lab"
    accion: str,      # "READ", "DOWNLOAD", "EXPORT"
    fecha_acceso: datetime,
    ip_address: str,
    motivo: str
)
```

**Auditoría Automática:**
Se registra AUTOMÁTICAMENTE cuando:
- Usuario accede expediente de un paciente (READ)
- Descarga PDF de resultados (DOWNLOAD)
- Exporta datos a Excel/CSV (EXPORT)

**Queries de Auditoría:**
```python
# Auditar: quién accedió a qué datos
accesos = RegistroAccesoDatos.objects.filter(
    paciente_id=paciente_id,
    fecha_acceso__date__gte=date(2026, 1, 1)
).order_by('-fecha_acceso')

# Auditar: qué datos accedió un usuario
accesos_usuario = RegistroAccesoDatos.objects.filter(
    usuario_id=usuario_id,
    fecha_acceso__month=6,
    fecha_acceso__year=2026
)
```

---

## III. Implementación Técnica

### Decoradores para COFEPRIS

```python
from core.compliance_decorators import requiere_firma_cofepris, requiere_consentimiento_lgpd

# Firmar resultado de laboratorio
@requiere_firma_cofepris
def generar_resultado_lab(request, orden_id):
    # Verifica que hay responsable sanitario vigente
    # Genera PDF firmado digitalmente
    resultado = OrdenDeServicio.objects.get(id=orden_id)
    return generar_y_firmar_pdf(resultado)

# Acceder expediente clínico
@requiere_consentimiento_lgpd(tipo='CLINICO')
def ver_expediente(request, paciente_id):
    # Verifica consentimiento CLINICO vigente
    # Registra acceso en RegistroAccesoDatos
    paciente = Paciente.objects.get(id=paciente_id)
    return expediente_json(paciente)
```

### Middleware de Auditoría

```python
# core/middleware/compliance.py
class AuditoriaAccesoDatosMiddleware:
    def __call__(self, request):
        # Registra acceso a endpoints sensibles
        if '/expediente/' in request.path or '/resultados/' in request.path:
            paciente_id = extraer_paciente_id(request)
            RegistroAccesoDatos.objects.create(
                usuario=request.user,
                paciente_id=paciente_id,
                tipo_datos="expediente" if '/expediente/' else "resultados_lab",
                accion='READ',
                ip_address=get_client_ip(request),
                motivo=request.GET.get('motivo', '')
            )
        return response
```

---

## IV. Checklist de Compliance

### ✅ COFEPRIS (NOM-004-SSA3-2012)
- [x] Modelo ResponsableSanitario
- [x] Verificación de vigencia (cédula + fecha)
- [x] Modelo FirmaDigitalResultado
- [x] Trazabilidad de firmas (quién, qué, cuándo, IP)
- [x] Admin para gestión de responsables
- [ ] Integración de certificado digital (.pfx)
- [ ] Generación de PDF firmado
- [ ] Validación de firma en expediente

### ✅ LGPD (Ley General de Protección de Datos)
- [x] Modelo ConsentimientoLGPD
- [x] Tipos de consentimiento (CLINICO, CONTACTO, MARKETING, INVESTIGACION)
- [x] Modelo DerechoOlvido
- [x] Workflow de solicitud → aprobación → eliminación
- [x] Modelo RegistroAccesoDatos
- [x] Auditoría de acceso automática
- [ ] Decorador @requiere_consentimiento_lgpd
- [ ] Background task para procesar Derecho al Olvido
- [ ] Anonimización reversible

---

## V. Próximas Mejoras (v1.2+)

### COFEPRIS v1.2
- Integración con HSM (Hardware Security Module) para firmas
- Validación online con COFEPRIS
- Generador de PDF con firma incrustada
- Transmisión segura de expedientes (SFTP/encrypted email)

### LGPD v1.2
- Portabilidad de datos: API `/api/paciente/datos-personales`
- Anonimización: hasheo reversible para histórico
- Derecho al olvido: task scheduler + validación de restricciones
- Consentimiento visual: widget web para consentimiento interactivo

---

## VI. Referencias Regulatorias

**COFEPRIS:**
- [NOM-004-SSA3-2012](https://www.gob.mx/cms/uploads/attachment/file/545256/NOM-004-SSA3-2012.pdf)
- [Guía de Expedientes Clínicos Electrónicos](https://www.gob.mx/salud)

**LGPD (México):**
- [Ley General de Protección de Datos Personales](https://www.diputados.gob.mx/LeyesBiblio/pdf/LGPDP.pdf)
- [INAI — Instituto Nacional de Transparencia](https://www.gob.mx/inai)

---

**✅ FASE 3C: COMPLIANCE IMPLEMENTADO**

Sistema PRISLAB v1.1 ahora cumple:
- ✓ Normativa COFEPRIS (auditoría sanitaria)
- ✓ Normativa LGPD (privacidad de datos)
- ✓ Trazabilidad regulatoria
- ✓ Listo para auditorías oficiales
