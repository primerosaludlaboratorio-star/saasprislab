"""
═══════════════════════════════════════════════════════════════════════════════
AUDITORÍA PROFUNDA (DEEP DIVE) — 5 FRENTES FUNCIONALES PERIFÉRICOS
PRISLAB v5.0 — Informe de Auditoría Forense
Fecha: 2026-04-03
═══════════════════════════════════════════════════════════════════════════════

Este script documenta los hallazgos de la auditoría profunda de los 5 frentes
funcionales y periféricos que estaban activos en código pero pendientes de
revisión exhaustiva según el Documento Maestro §6.8, §6.4, §6.10 y §6.11.

CLASIFICACIÓN DE RIESGOS:
🔴 CRÍTICO — Riesgo inmediato, requiere atención urgente
🟡 MEDIO — Riesgo moderado, debe atenderse en próxima iteración
🟢 BAJO — Riesgo bajo, implementar monitoreo

═══════════════════════════════════════════════════════════════════════════════
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Any


class AuditoriaFrentesPerifericos:
    """
    Clase para documentar hallazgos de auditoría de los 5 frentes periféricos.
    """
    
    HALLAZGOS = []
    
    @classmethod
    def documentar_hallazgo(
        cls,
        frente: str,
        categoria: str,
        nivel_riesgo: str,
        descripcion: str,
        ubicacion: str,
        recomendacion: str,
        referencia_codigo: str = None
    ):
        """Documenta un hallazgo de auditoría."""
        hallazgo = {
            'id': f'H-{len(cls.HALLAZGOS)+1:03d}',
            'frente': frente,
            'categoria': categoria,
            'nivel_riesgo': nivel_riesgo,
            'descripcion': descripcion,
            'ubicacion': ubicacion,
            'recomendacion': recomendacion,
            'referencia_codigo': referencia_codigo,
            'timestamp': datetime.now().isoformat(),
        }
        cls.HALLAZGOS.append(hallazgo)
        return hallazgo
    
    @classmethod
    def ejecutar_auditoria(cls):
        """Ejecuta la auditoría completa de los 5 frentes."""
        
        # ═══════════════════════════════════════════════════════════════════════
        # FRENTES AUDITADOS:
        # 1. Frente Fiscal: Contabilidad y Facturación (CFDI)
        # 2. Motor Financiero Secundario: Nómina, CXC y CRM
        # 3. Deuda Técnica LIMS: Intérprete de Fórmulas
        # 4. Flujos Clínicos Auxiliares: Enfermería y Logística
        # 5. RH y Módulos Satélite (Bienestar, IA, Voz)
        # ═══════════════════════════════════════════════════════════════════════
        
        cls._auditar_frente_fiscal()
        cls._auditar_motor_financiero()
        cls._auditar_deuda_tecnica_lims()
        cls._auditar_flujos_clinicos_auxiliares()
        cls._auditar_rh_modulos_satelite()
        
        return cls.generar_informe()
    
    @classmethod
    def _auditar_frente_fiscal(cls):
        """
        🔴 FRETE 1: Frente Fiscal — Contabilidad y Facturación (CFDI)
        
        Riesgo Principal: Race conditions en timbrado
        """
        # Hallazgo 1: Race Condition en timbrado
        cls.documentar_hallazgo(
            frente='Frente Fiscal (CFDI)',
            categoria='Race Condition / Concurrencia',
            nivel_riesgo='🔴 CRÍTICO',
            descripcion=(
                'La vista timbrar_factura() NO utiliza select_for_update() ni '
                'bloqueo de fila en la base de datos. Si dos usuarios (o el mismo '
                'usuario en dos pestañas) intentan timbrar la misma factura '
                'simultáneamente, ambas solicitudes podrían pasar la validación '
                'factura.estado == "TIMBRADO" antes de que cualquiera complete, '
                'resultando en múltiples facturas ante el SAT para el mismo ingreso.'
            ),
            ubicacion='@contabilidad/views.py:234-275 — timbrar_factura()',
            referencia_codigo="""
@login_required
def timbrar_factura(request, factura_id):
    # ... líneas 243-248 ...
    factura = get_object_or_404(FacturaCFDI, id=factura_id, usuario_creo__empresa=empresa)
    
    if factura.estado == 'TIMBRADO':  # ← Race condition: dos requests leen BORRADOR
        messages.warning(request, 'Esta factura ya está timbrada.')
        return redirect('contabilidad:detalle_factura', factura_id=factura.id)
    
    # Ambos requests pueden llegar aquí simultáneamente
    api = FacturamaAPI()
    resultado = api.timbrar_cfdi(factura)  # ← Ambos llaman a Facturama
            """.strip(),
            recomendacion=(
                '1. Usar select_for_update() para bloquear la fila: '
                'FacturaCFDI.objects.select_for_update().get(id=factura_id)\n'
                '2. Envolver la transacción completa (incluyendo llamada API) en '
                'transaction.atomic()\n'
                '3. Implementar campo timbrando_en_proceso con timestamp para '
                'evitar timbrados concurrentes\n'
                '4. Agregar índice único condicional en uuid_sat para prevenir '
                'duplicados a nivel DB'
            )
        )
        
        # Hallazgo 2: Idempotencia en API Facturama
        cls.documentar_hallazgo(
            frente='Frente Fiscal (CFDI)',
            categoria='Idempotencia / API Externa',
            nivel_riesgo='🟡 MEDIO',
            descripcion=(
                'La API de Facturama no implementa clave de idempotencia '
                '(Idempotency-Key). Si hay un timeout de red justo después de '
                'que Facturama timbra pero antes de recibir la respuesta, el '
                'usuario podría reintentar y crear una segunda factura ante el SAT.'
            ),
            ubicacion='@contabilidad/facturama_api.py:36-85 — timbrar_cfdi()',
            referencia_codigo="""
response = requests.post(
    url,
    auth=self.auth,
    headers=headers,  # ← Falta 'Idempotency-Key': folio_interno_unico
    json=cfdi_json,
    timeout=(5, 30)
)
            """.strip(),
            recomendacion=(
                '1. Generar clave de idempotencia única por factura (ej: hash de '
                'folio_interno + usuario_id + timestamp_dia)\n'
                '2. Enviar en headers: {"Idempotency-Key": clave}\n'
                '3. Almacenar clave usada y verificar antes de reintentar\n'
                '4. Implementar patrón "circuit breaker" para timeouts consecutivos'
            )
        )
        
        # Hallazgo 3: Falta de pruebas E2E en sandbox
        cls.documentar_hallazgo(
            frente='Frente Fiscal (CFDI)',
            categoria='Testing / Cobertura',
            nivel_riesgo='🟡 MEDIO',
            descripcion=(
                'No se encontraron pruebas E2E automatizadas que validen el flujo '
                'completo de timbrado usando el sandbox de Facturama. El riesgo '
                'es que cambios en producción rompan el timbrado sin detectarse.'
            ),
            ubicacion='@tests/ — directorio de pruebas',
            referencia_codigo='No se encontraron tests E2E para timbrado CFDI',
            recomendacion=(
                '1. Crear test_e2e_timbrado.py con pytest-playwright\n'
                '2. Usar FACTURAMA_SANDBOX=True en CI/CD\n'
                '3. Validar flujo: Crear borrador → Timbrar → Verificar UUID → '
                'Cancelar (si el sandbox lo permite)'
            )
        )
    
    @classmethod
    def _auditar_motor_financiero(cls):
        """
        🟡 FRENTE 2: Motor Financiero Secundario — Nómina, CXC, CRM
        
        Riesgo Principal: Fugas de información por permisos
        """
        # Hallazgo 1: CXC (Cuentas por Cobrar) — No encontrado
        cls.documentar_hallazgo(
            frente='Motor Financiero (CXC)',
            categoria='Módulo Faltante',
            nivel_riesgo='🟡 MEDIO',
            descripcion=(
                'El módulo de Cuentas por Cobrar (CXC) mencionado en el Documento '
                'Maestro §6.8 no fue encontrado en el codebase. Esto puede indicar:\n'
                'a) Que aún no se implementa\n'
                'b) Que está integrado en otro módulo (ej: core/views/ventas.py)\n'
                'c) Que fue renombrado (ej: financiero/cuentas_por_cobrar.py)'
            ),
            ubicacion='@core/views/ — no existe cuentas_por_cobrar.py',
            referencia_codigo='Archivo no encontrado en búsqueda: **/*cxc*.py',
            recomendacion=(
                '1. Confirmar con equipo de producto si CXC está en roadmap\n'
                '2. Si existe con otro nombre, documentar en CHANGELOG\n'
                '3. Si está pendiente, agregar a backlog con prioridad'
            )
        )
        
        # Hallazgo 2: Nómina — Roles correctos
        cls.documentar_hallazgo(
            frente='Motor Financiero (Nómina)',
            categoria='Seguridad / Autorización',
            nivel_riesgo='🟢 BAJO',
            descripcion=(
                'El módulo de Nómina implementa correctamente el decorador '
                '@role_required("DIRECTOR", "ADMIN", "GERENTE") en todas las '
                'vistas sensibles. No se detectaron fugas de información por URLs.'
            ),
            ubicacion='@core/views/nomina.py — todas las vistas',
            referencia_codigo="""
@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
def dashboard_nomina(request):
    # ...

@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
def editar_recibo(request, pk):
    # ...
            """.strip(),
            recomendacion=(
                '✅ Implementación correcta. Mantener matriz de roles. '
                'Sugerencia: Agregar auditoría de logs para accesos a nómina.'
            )
        )
        
        # Hallazgo 3: CRM — Sin multi-tenant estricto
        cls.documentar_hallazgo(
            frente='Motor Financiero (CRM)',
            categoria='Seguridad / Multi-tenancy',
            nivel_riesgo='🟡 MEDIO',
            descripcion=(
                'Las vistas de CRM usan filtro por empresa, pero no verifican '
                'explícitamente que el usuario pertenezca a esa empresa. Un usuario '
                'con URL manipulada podría potencialmente acceder a prospectos de '
                'otra empresa si conoce el ID.'
            ),
            ubicacion='@core/views/crm.py:110 — detalle_prospecto()',
            referencia_codigo="""
def detalle_prospecto(request, pk):
    empresa = _empresa(request)
    prospecto = get_object_or_404(ProspectoCRM, pk=pk, empresa=empresa)
    # Falta: verificar que request.user.empresa == empresa
            """.strip(),
            recomendacion=(
                '1. Agregar verificación explícita: '
                'if request.user.empresa != empresa: raise PermissionDenied\n'
                '2. Implementar middleware de verificación de empresa para todas '
                'las vistas multi-tenant'
            )
        )
    
    @classmethod
    def _auditar_deuda_tecnica_lims(cls):
        """
        🔴 FRENTE 3: Deuda Técnica LIMS — Intérprete de Fórmulas
        
        Riesgo Principal: Vulnerabilidad de ejecución de código
        """
        # Hallazgo 1: Fórmulas en BD sin motor implementado
        cls.documentar_hallazgo(
            frente='Deuda Técnica LIMS (Fórmulas)',
            categoria='Deuda Técnica / Riesgo Seguridad',
            nivel_riesgo='🔴 CRÍTICO',
            descripcion=(
                'El modelo Analito tiene campos formula (TextField) y es_calculado '
                '(BooleanField) que almacenan fórmulas matemáticas en la BD, pero '
                'NO existe un intérprete seguro implementado. '
                '\n\nRiesgo: Cuando se implemente el motor de cálculo, si se usa '
                'eval() o exec() de Python sin sandboxing, un atacante podría '
                'inyectar código malicioso en el campo formula y ejecutar comandos '
                'arbitrarios en el servidor (RCE — Remote Code Execution).'
            ),
            ubicacion='@lims/models.py:56-68 — Analito.formula, Analito.es_calculado',
            referencia_codigo="""
class Analito(models.Model):
    # ...
    formula = models.TextField(
        blank=True,
        verbose_name='Fórmula',
        help_text='Expresión desde Parametros.csv (Formula)...',
    )
    es_calculado = models.BooleanField(
        default=False,
        verbose_name='¿Calculado?',
        help_text='True si el resultado se obtiene por motor interno...',
    )
    # NO hay método calcular() ni intérprete implementado
            """.strip(),
            recomendacion=(
                '1. NO usar eval() o exec() bajo ninguna circunstancia\n'
                '2. Implementar intérprete matemático seguro con whitelist:\n'
                '   - asteval (librería de sandboxing matemático)\n'
                '   - O parser propio con operaciones permitidas: +, -, *, /, **, '
                'sqrt(), log(), etc.\n'
                '3. Validar fórmulas en clean() del modelo con regex estricto\n'
                '4. Ejecutar cálculos en contenedor/entorno aislado\n'
                '5. Limitar tiempo de ejecución (timeout) y memoria'
            )
        )
        
        # Hallazgo 2: No se encontró eval() inseguro (positivo)
        cls.documentar_hallazgo(
            frente='Deuda Técnica LIMS (Fórmulas)',
            categoria='Validación Positiva',
            nivel_riesgo='🟢 BAJO',
            descripcion=(
                'Búsqueda exhaustiva con grep no encontró uso de eval() o exec() '
                'en el módulo LIMS ni en core. Esto es positivo — significa que '
                'el riesgo aún no está materializado, pero debe prevenirse antes '
                'de implementar el motor de cálculo.'
            ),
            ubicacion='@lims/, @core/ — búsqueda completa',
            referencia_codigo='grep -r "eval(" lims/ core/ → No results found',
            recomendacion=(
                '✅ No existe código inseguro actualmente. '
                'Implementar linting en CI/CD para prohibir eval()/exec() '
                'en futuros commits.'
            )
        )
    
    @classmethod
    def _auditar_flujos_clinicos_auxiliares(cls):
        """
        🟢 FRENTE 4: Flujos Clínicos Auxiliares — Enfermería y Logística
        
        Riesgo Principal: Inconsistencia de datos clínicos
        """
        # Hallazgo 1: Enfermería — Sin vinculación a Expediente Inmutable
        cls.documentar_hallazgo(
            frente='Flujos Clínicos (Enfermería)',
            categoria='Integración / Blindaje Forense',
            nivel_riesgo='🟡 MEDIO',
            descripcion=(
                'El módulo de Enfermería (Triage/Signos Vitales) captura datos '
                'clínicos importantes, pero NO está vinculado al nuevo motor de '
                'Expediente Inmutable (Blindaje v2.0) que acabamos de implementar. '
                'Los signos vitales no generan snapshots SHA256 ni sellos PIN-LAB.'
            ),
            ubicacion='@enfermeria/views.py:55-81 — capturar_signos_vitales()',
            referencia_codigo="""
@login_required
def capturar_signos_vitales(request, cita_id):
    # ...
    if form.is_valid():
        signos = form.save(commit=False)
        signos.paciente = cita.paciente
        signos.empresa = cita.empresa
        signos.cita = cita
        signos.registrado_por = request.user
        signos.save()
        # ← Falta: Crear snapshot en ExpedienteNotaSHA
        # ← Falta: Vincular con Blindaje v2.0
            """.strip(),
            recomendacion=(
                '1. Extender SignosVitales para crear snapshot automático en '
                'ExpedienteNotaSHA\n'
                '2. Agregar campo signos.firmado_con_pin para validación médica\n'
                '3. Implementar middleware de blindaje para modelos clínicos '
                '(similar a NotaClinicaSOAP)'
            )
        )
        
        # Hallazgo 2: Logística — Implementación robusta
        cls.documentar_hallazgo(
            frente='Flujos Clínicos (Logística)',
            categoria='Implementación / Transacciones',
            nivel_riesgo='🟢 BAJO',
            descripcion=(
                'El módulo de Logística (Rutas de Recolección, Transferencias) '
                'implementa transacciones atómicas correctamente, usa '
                'transaction.atomic(), y tiene sistema de logs de auditoría. '
                'Incluye certificación de cadena de frío ISO 15189.'
            ),
            ubicacion='@logistica/views.py:277-300 — enviar_transferencia()',
            referencia_codigo="""
with transaction.atomic():
    # Actualizar cantidades enviadas
    for detalle in transferencia.detalles.all():
        detalle.cantidad_enviada = detalle.cantidad_solicitada
        detalle.save(update_fields=['cantidad_enviada'])
    
    # Cambiar estado
    transferencia.estado = 'ENVIADA'
    transferencia.save()
    
    # Log
    LogTransferencia.objects.create(...)
            """.strip(),
            recomendacion=(
                '✅ Implementación correcta. Mantener estándar en otros módulos. '
                'Sugerencia: Agregar índices en LogTransferencia para consultas '
                'frecuentes.'
            )
        )
    
    @classmethod
    def _auditar_rh_modulos_satelite(cls):
        """
        🟡 FRENTE 5: RH y Módulos Satélite — Bienestar, IA, Voz
        
        Riesgo Principal: Incumplimiento NOM-035, seguridad de APIs
        """
        # Hallazgo 1: Bienestar — NOM-035 parcialmente implementada
        cls.documentar_hallazgo(
            frente='RH y Satélites (Bienestar NOM-035)',
            categoria='Cumplimiento Normativo / NOM-035',
            nivel_riesgo='🟡 MEDIO',
            descripcion=(
                'El módulo de Bienestar implementa detección de riesgo emocional '
                '(ROJO_VIDA, ROJO_VIOLENCIA, ROJO_ACOSO) y envío de alertas a '
                'administradores. Sin embargo, no se encontró:\n'
                '1. Sistema de anonimización de datos para reportes NOM-035\n'
                '2. Retención temporal de datos sensibles (deberían eliminarse '
                'después de X meses según NOM-035)\n'
                '3. Consentimiento explícito del trabajador para procesamiento '
                'de datos emocionales'
            ),
            ubicacion='@bienestar/views.py:190-209 — detectar_riesgo_emocional()',
            referencia_codigo="""
def detectar_riesgo_emocional(texto):
    # Palabras clave de alto riesgo
    palabras_suicidio = ['suicidio', 'suicidarme', 'matarme', ...]
    # ...
    if any(palabra in texto_lower for palabra in palabras_suicidio):
        return 'ROJO_VIDA'
            """.strip(),
            recomendacion=(
                '1. Implementar política de retención: eliminar entradas de diario '
                'después de 6 meses (configurable)\n'
                '2. Agregar consentimiento informado en onboarding del empleado\n'
                '3. Crear reporte NOM-035 agregado/anónimo para dirección\n'
                '4. Documentar procedimiento de respuesta a alertas ROJO_VIDA'
            )
        )
        
        # Hallazgo 2: Voice Commander — No auditado (falta implementación)
        cls.documentar_hallazgo(
            frente='RH y Satélites (Voice Commander)',
            categoria='Módulo No Encontrado / HTTPS',
            nivel_riesgo='🟢 BAJO',
            descripcion=(
                'No se encontró el módulo "Voice Commander" en el codebase. '
                'Según el Documento Maestro §6.11, debe exigir HTTPS estricto '
                'para proteger la transmisión de comandos de voz. '
                '\n\nPosibles ubicaciones:\n'
                '- ia/views.py (integrado en módulo IA)\n'
                '- middleware de reconocimiento de voz\n'
                '- Pendiente de implementación'
            ),
            ubicacion='@/ — Voice Commander no encontrado',
            referencia_codigo='Búsqueda: **/voice*.py, **/comand*.py → No results',
            recomendacion=(
                '1. Confirmar si Voice Commander está implementado con otro nombre\n'
                '2. Si existe: verificar que requiera HTTPS (SECURE_SSL_REDIRECT)\n'
                '3. Si no existe: documentar en backlog'
            )
        )
        
        # Hallazgo 3: Asistente IA — Timeout y sanitización OK
        cls.documentar_hallazgo(
            frente='RH y Satélites (Asistente IA)',
            categoria='Seguridad / API Externa',
            nivel_riesgo='🟢 BAJO',
            descripcion=(
                'El módulo de Bienestar usa Gemini Flash con timeout configurado '
                '(10 segundos) y sanitización básica del input del usuario. '
                'El contexto está restringido a bienestar emocional. '
                '\n\nPositivo: No se encontraron prompts susceptibles a jailbreaking.'
            ),
            ubicacion='@bienestar/views.py:144-161 — api_chat_bienestar()',
            referencia_codigo="""
response = model.generate_content(
    prompt_completo, 
    generation_config=config, 
    request_options={'timeout': 10}  # ← Timeout configurado
)
            """.strip(),
            recomendacion=(
                '✅ Implementación segura. Sugerencias adicionales:\n'
                '1. Agregar rate limiting por usuario (max 20 mensajes/hora)\n'
                '2. Implementar logging de prompts para auditoría\n'
                '3. Validar que la respuesta de IA no contenga PII del usuario'
            )
        )
    
    @classmethod
    def generar_informe(cls) -> Dict[str, Any]:
        """Genera el informe consolidado de auditoría."""
        
        # Clasificar por nivel de riesgo
        criticos = [h for h in cls.HALLAZGOS if '🔴' in h['nivel_riesgo']]
        medios = [h for h in cls.HALLAZGOS if '🟡' in h['nivel_riesgo']]
        bajos = [h for h in cls.HALLAZGOS if '🟢' in h['nivel_riesgo']]
        
        informe = {
            'metadata': {
                'titulo': 'Auditoría Profunda (Deep Dive) — 5 Frentes Periféricos',
                'version_prislab': '5.0',
                'fecha_auditoria': datetime.now().isoformat(),
                'auditor': 'Cascade AI — Análisis Estático',
                'documento_referencia': 'Documento Maestro §6.8, §6.4, §6.10, §6.11',
            },
            'resumen_ejecutivo': {
                'total_hallazgos': len(cls.HALLAZGOS),
                'criticos': len(criticos),
                'medios': len(medios),
                'bajos': len(bajos),
                'frentes_auditados': [
                    'Frente Fiscal (CFDI)',
                    'Motor Financiero Secundario (Nómina, CXC, CRM)',
                    'Deuda Técnica LIMS (Intérprete de Fórmulas)',
                    'Flujos Clínicos Auxiliares (Enfermería, Logística)',
                    'RH y Módulos Satélite (Bienestar, IA, Voz)',
                ],
            },
            'hallazgos_criticos': criticos,
            'hallazgos_medios': medios,
            'hallazgos_bajos': bajos,
            'hallazgos_por_frente': {
                'frente_fiscal_cfdi': [h for h in cls.HALLAZGOS if 'Fiscal' in h['frente']],
                'motor_financiero': [h for h in cls.HALLAZGOS if 'Financiero' in h['frente']],
                'deuda_tecnica_lims': [h for h in cls.HALLAZGOS if 'LIMS' in h['frente']],
                'flujos_clinicos': [h for h in cls.HALLAZGOS if 'Clínicos' in h['frente']],
                'rh_satelites': [h for h in cls.HALLAZGOS if 'Satélites' in h['frente']],
            },
            'recomendaciones_prioritarias': [
                {
                    'prioridad': 1,
                    'hallazgo_id': 'H-001',
                    'accion': 'Implementar select_for_update() en timbrado CFDI',
                    'estimacion': '4 horas',
                    'riesgo_si_no_se_atiende': 'Duplicidad de facturas ante SAT, multas fiscales',
                },
                {
                    'prioridad': 2,
                    'hallazgo_id': 'H-005',
                    'accion': 'Diseñar intérprete matemático seguro (NO eval())',
                    'estimacion': '16 horas',
                    'riesgo_si_no_se_atiende': 'RCE (Remote Code Execution), compromiso total del servidor',
                },
                {
                    'prioridad': 3,
                    'hallazgo_id': 'H-002',
                    'accion': 'Agregar Idempotency-Key en llamadas a Facturama',
                    'estimacion': '2 horas',
                    'riesgo_si_no_se_atiende': 'Timbrados duplicados por timeouts de red',
                },
                {
                    'prioridad': 4,
                    'hallazgo_id': 'H-003',
                    'accion': 'Crear pruebas E2E de timbrado en sandbox',
                    'estimacion': '8 horas',
                    'riesgo_si_no_se_atiende': 'Regresiones en producción sin detección',
                },
            ],
        }
        
        return informe
    
    @classmethod
    def generar_markdown(cls) -> str:
        """Genera informe en formato Markdown para documentación."""
        informe = cls.generar_informe()
        
        md = f"""# {informe['metadata']['titulo']}

**Versión PRISLAB:** {informe['metadata']['version_prislab']}  
**Fecha:** {informe['metadata']['fecha_auditoria']}  
**Referencia:** {informe['metadata']['documento_referencia']}

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Total Hallazgos | {informe['resumen_ejecutivo']['total_hallazgos']} |
| 🔴 Críticos | {informe['resumen_ejecutivo']['criticos']} |
| 🟡 Medios | {informe['resumen_ejecutivo']['medios']} |
| 🟢 Bajos | {informe['resumen_ejecutivo']['bajos']} |

### Frentes Auditados
{chr(10).join(['- ' + f for f in informe['resumen_ejecutivo']['frentes_auditados']])}

---

## 🔴 Hallazgos Críticos (Requieren Atención Inmediata)

"""
        
        for h in informe['hallazgos_criticos']:
            md += f"""### {h['id']}: {h['categoria']}

**Frente:** {h['frente']}  
**Ubicación:** `{h['ubicacion']}`

**Descripción:**
{h['descripcion']}

**Código de Referencia:**
```python
{h.get('referencia_codigo', 'N/A')}
```

**Recomendación:**
{h['recomendacion']}

---

"""
        
        md += """## 🟡 Hallazgos Medios (Atender en Próxima Iteración)

"""
        
        for h in informe['hallazgos_medios']:
            md += f"""### {h['id']}: {h['categoria']}

**Frente:** {h['frente']}  
**Ubicación:** `{h['ubicacion']}`

**Descripción:**
{h['descripcion']}

**Recomendación:**
{h['recomendacion']}

---

"""
        
        md += """## 🟢 Hallazgos Bajos (Monitoreo)

"""
        
        for h in informe['hallazgos_bajos']:
            md += f"""### {h['id']}: {h['categoria']}

**Frente:** {h['frente']}  
**Ubicación:** `{h['ubicacion']}`

**Descripción:**
{h['descripcion']}

**Recomendación:**
{h['recomendacion']}

---

"""
        
        md += """## Plan de Acción Prioritario

| Prioridad | ID | Acción | Estimación | Riesgo si No se Atiende |
|-----------|----|--------|------------|------------------------|
"""
        
        for rec in informe['recomendaciones_prioritarias']:
            md += f"| {rec['prioridad']} | {rec['hallazgo_id']} | {rec['accion']} | {rec['estimacion']} | {rec['riesgo_si_no_se_atiende']} |\n"
        
        md += """

---

## Conclusión

La auditoría revela **2 hallazgos CRÍTICOS** que requieren atención inmediata:

1. **Race condition en timbrado CFDI** — Riesgo de duplicidad ante el SAT
2. **Deuda técnica en fórmulas LIMS** — Riesgo de ejecución remota de código

Se recomienda priorizar estos dos temas antes del próximo despliegue a producción.

---
*Informe generado automáticamente por sistema de auditoría PRISLAB*
"""
        
        return md


def main():
    """Ejecuta la auditoría y genera los informes."""
    print("═" * 80)
    print("AUDITORÍA PROFUNDA — 5 FRENTES FUNCIONALES PERIFÉRICOS")
    print("PRISLAB v5.0 — Análisis Estático de Código")
    print("═" * 80)
    
    # Ejecutar auditoría
    auditoria = AuditoriaFrentesPerifericos()
    informe = auditoria.ejecutar_auditoria()
    
    # Mostrar resumen
    print(f"\n📊 RESUMEN EJECUTIVO:")
    print(f"   Total hallazgos: {informe['resumen_ejecutivo']['total_hallazgos']}")
    print(f"   🔴 Críticos: {informe['resumen_ejecutivo']['criticos']}")
    print(f"   🟡 Medios: {informe['resumen_ejecutivo']['medios']}")
    print(f"   🟢 Bajos: {informe['resumen_ejecutivo']['bajos']}")
    
    print(f"\n🔴 HALLAZGOS CRÍTICOS:")
    for h in informe['hallazgos_criticos']:
        print(f"   {h['id']}: {h['categoria']} — {h['frente']}")
    
    print(f"\n📋 RECOMENDACIONES PRIORITARIAS:")
    for rec in informe['recomendaciones_prioritarias']:
        print(f"   P{rec['prioridad']}: [{rec['hallazgo_id']}] {rec['accion']} ({rec['estimacion']})")
    
    # Generar archivos
    print(f"\n💾 GENERANDO ARCHIVOS...")
    
    # JSON
    json_path = 'AUDITORIA_5_FRENTES_PERIFERICOS.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(informe, f, indent=2, ensure_ascii=False, default=str)
    print(f"   ✓ {json_path}")
    
    # Markdown
    md_path = 'AUDITORIA_5_FRENTES_PERIFERICOS.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(auditoria.generar_markdown())
    print(f"   ✓ {md_path}")
    
    print(f"\n✅ Auditoría completada exitosamente.")
    print("═" * 80)
    
    return informe


if __name__ == '__main__':
    main()
