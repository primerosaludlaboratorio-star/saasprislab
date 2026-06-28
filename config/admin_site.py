"""
config/admin_site.py
═══════════════════════════════════════════════════════════════════════════════
PRISLAB V5.4 — "OPERACIÓN TRANSPARENTE"

AdminSite personalizado que reorganiza el panel en 8 Departamentos Operativos
en lugar de mostrar las apps de Django.

Cada grupo de personal solo ve su departamento.
La Dirección tiene visibilidad global sobre todos.
═══════════════════════════════════════════════════════════════════════════════
"""
from django.contrib.admin import AdminSite


# ─── CONFIGURACIÓN DE DEPARTAMENTOS ─────────────────────────────────────────
DEPARTAMENTOS_CONFIG = {
    'LABORATORIO': {
        'label': '🔬 Laboratorio',
        'orden': 1,
        # Grupos que pueden ver este departamento
        'grupos_permitidos': {'LABORATORIO', 'QUIMICO', 'DIRECTOR', 'SOCIOS'},
    },
    'FARMACIA': {
        'label': '💊 Farmacia',
        'orden': 2,
        'grupos_permitidos': {'FARMACIA', 'CAJERO', 'DIRECTOR', 'SOCIOS'},
    },
    'PACIENTES': {
        'label': '👥 Pacientes',
        'orden': 3,
        'grupos_permitidos': {'RECEPCION', 'LABORATORIO', 'FARMACIA', 'MEDICO', 'DIRECTOR', 'SOCIOS'},
    },
    'CONSULTORIO': {
        'label': '🩺 Consultorio Médico',
        'orden': 4,
        'grupos_permitidos': {'MEDICO', 'DIRECTOR', 'SOCIOS'},
    },
    'FINANZAS': {
        'label': '💰 Finanzas y Caja',
        'orden': 5,
        'grupos_permitidos': {'DIRECTOR', 'SOCIOS'},       # BÚNKER de Dirección
    },
    'PERSONAL': {
        'label': '👔 Gestión de Personal',
        'orden': 6,
        'grupos_permitidos': {'DIRECTOR', 'SOCIOS'},       # BÚNKER de Dirección
    },
    'BIENESTAR': {
        'label': '🌱 Bienestar y Cultura (NOM-035)',
        'orden': 7,
        'grupos_permitidos': {'DIRECTOR', 'SOCIOS'},       # BÚNKER de Dirección
    },
    'SEGURIDAD': {
        'label': '🛡️ Seguridad y Auditoría',
        'orden': 8,
        'grupos_permitidos': {'DIRECTOR', 'SOCIOS'},       # BÚNKER de Dirección
    },
    'SISTEMA': {
        'label': '⚙️ Sistema y Configuración',
        'orden': 9,
        'grupos_permitidos': set(),                        # Solo superusuario
    },
}


# ─── MAPA (app_label, model_name_lower) → DEPARTAMENTO ──────────────────────
# Todos los modelos NO mapeados van a 'SISTEMA' (solo superusuario).

MODEL_DEPARTMENT_MAP = {

    # ── 🔬 LABORATORIO ───────────────────────────────────────────────────────
    ('laboratorio', 'estudio'):                  'LABORATORIO',
    ('laboratorio', 'categoriaexamen'):          'LABORATORIO',
    ('laboratorio', 'parametro'):               'LABORATORIO',
    ('laboratorio', 'valorreferencia'):         'LABORATORIO',
    ('laboratorio', 'rangoreferenciaparametro'): 'LABORATORIO',
    ('laboratorio', 'perfillaboratorio'):        'LABORATORIO',
    ('laboratorio', 'orden'):                   'LABORATORIO',
    ('laboratorio', 'detalleorden'):            'LABORATORIO',
    ('laboratorio', 'resultado'):               'LABORATORIO',
    ('laboratorio', 'resultadohl7'):            'LABORATORIO',
    ('laboratorio', 'equipo'):                  'LABORATORIO',
    ('laboratorio', 'codigoparametroequipo'):   'LABORATORIO',
    ('laboratorio', 'enviomaquila'):            'LABORATORIO',
    ('laboratorio', 'notificacionpanico'):      'LABORATORIO',
    ('laboratorio', 'controlcalidad'):          'LABORATORIO',
    ('laboratorio', 'bitacoramantenimiento'):   'LABORATORIO',
    ('laboratorio', 'historialresultados'):     'LABORATORIO',
    ('laboratorio', 'insumoestudio'):           'LABORATORIO',
    ('laboratorio', 'medico'):                  'LABORATORIO',
    ('laboratorio', 'responsablesanitario'):    'LABORATORIO',
    ('laboratorio', 'diferencialleucocitario'): 'LABORATORIO',
    ('laboratorio', 'indiceeritrocitario'):     'LABORATORIO',
    ('laboratorio', 'precursorcellular'):       'LABORATORIO',
    ('core', 'estudio'):                        'LABORATORIO',
    ('core', 'categoriaestudio'):               'LABORATORIO',
    ('core', 'parametro'):                      'LABORATORIO',
    ('core', 'rangoreferencia'):                'LABORATORIO',
    ('core', 'seccionlaboratorio'):             'LABORATORIO',
    ('core', 'resultadoparametro'):             'LABORATORIO',
    ('core', 'detalleorden'):                   'LABORATORIO',
    ('core', 'ordendeservicio'):                'LABORATORIO',
    ('core', 'tomamuestra'):                    'LABORATORIO',
    ('core', 'enviomaquila'):                   'LABORATORIO',
    ('core', 'preordenlaboratorio'):            'LABORATORIO',
    ('core', 'bitacoraentregaresultados'):      'LABORATORIO',
    ('core', 'controlcalidad'):                 'LABORATORIO',
    ('core', 'historialresultados'):            'LABORATORIO',
    ('core', 'mantenimientoequipo'):            'LABORATORIO',
    ('core', 'medico'):                         'LABORATORIO',
    ('core', 'convenio'):                       'LABORATORIO',
    ('core', 'convenioprecioestudio'):          'LABORATORIO',
    ('iot',  'kiosco'):                         'LABORATORIO',
    ('iot',  'verificacionkiosco'):             'LABORATORIO',

    # ── 💊 FARMACIA ──────────────────────────────────────────────────────────
    ('core',     'producto'):                   'FARMACIA',
    ('core',     'lote'):                       'FARMACIA',
    ('core',     'ajusteinventario'):           'FARMACIA',
    ('core',     'demandainsatisfecha'):        'FARMACIA',
    ('core',     'discountpolicy'):             'FARMACIA',
    ('farmacia', 'proveedor'):                  'FARMACIA',
    ('farmacia', 'movimientoinventario'):       'FARMACIA',
    ('farmacia', 'mermafarmacia'):              'FARMACIA',
    ('farmacia', 'motivoajuste'):               'FARMACIA',
    ('farmacia', 'registroantibiotico'):        'FARMACIA',
    ('farmacia', 'devolucionventa'):            'FARMACIA',
    ('farmacia', 'aperturacaja'):               'FARMACIA',
    ('farmacia', 'cierreturnofarmacia'):        'FARMACIA',

    # ── 👥 PACIENTES ─────────────────────────────────────────────────────────
    ('core',      'paciente'):                  'PACIENTES',
    ('core',      'historiaclinica'):           'PACIENTES',
    ('core',      'antecedente'):               'PACIENTES',
    ('core',      'consentimientoinformado'):   'PACIENTES',
    ('core',      'firmadigital'):              'PACIENTES',
    ('core',      'signosvitales'):             'PACIENTES',
    ('core',      'logaccesoexpediente'):       'PACIENTES',
    ('core',      'registroauditoriaconsentimiento'): 'PACIENTES',
    ('pacientes', 'paciente'):                  'PACIENTES',
    ('pacientes', 'usuariopaciente'):           'PACIENTES',
    ('pacientes', 'solicitudaccesoportal'):     'PACIENTES',
    ('pacientes', 'accesoexpedienteportal'):    'PACIENTES',

    # ── 🩺 CONSULTORIO ────────────────────────────────────────────────────────
    ('consultorio', 'consultamedica'):          'CONSULTORIO',
    ('consultorio', 'agendacita'):              'CONSULTORIO',
    ('consultorio', 'notamedica'):              'CONSULTORIO',
    ('consultorio', 'somatometria'):            'CONSULTORIO',
    ('consultorio', 'vademecum'):               'CONSULTORIO',
    ('consultorio', 'imagenultrasonido'):       'CONSULTORIO',
    ('consultorio', 'reporteultrasonido'):      'CONSULTORIO',
    ('consultorio', 'encuestasatisfaccion'):    'CONSULTORIO',
    ('consultorio', 'listaespera'):             'CONSULTORIO',
    ('consultorio', 'seguimientotratamiento'):  'CONSULTORIO',
    ('consultorio', 'archivoadjuntoconsulta'):  'CONSULTORIO',
    ('consultorio', 'cobroconsulta'):           'CONSULTORIO',
    ('consultorio', 'configuracionmedico'):     'CONSULTORIO',
    ('consultorio', 'cajaconsultorio'):         'CONSULTORIO',
    ('consultorio', 'analisispatron'):          'CONSULTORIO',
    ('consultorio', 'valeliquidacion'):         'CONSULTORIO',
    ('consultorio', 'incidenciasentinel'):      'CONSULTORIO',
    ('core', 'consultamedica'):                 'CONSULTORIO',
    ('core', 'citamedica'):                     'CONSULTORIO',
    ('core', 'receta'):                         'CONSULTORIO',
    ('core', 'recetaitem'):                     'CONSULTORIO',
    ('core', 'notaclinicasoap'):                'CONSULTORIO',
    ('core', 'plantillanotaclinica'):           'CONSULTORIO',
    ('core', 'estudioimagen'):                  'CONSULTORIO',
    ('core', 'imagendetalle'):                  'CONSULTORIO',
    ('core', 'plantillaestudioimagen'):         'CONSULTORIO',
    ('core', 'certificadomedico'):              'CONSULTORIO',
    ('core', 'audioconsulta'):                  'CONSULTORIO',
    ('core', 'historialcambiosconsulta'):       'CONSULTORIO',

    # ── 💰 FINANZAS Y CAJA ── (BÚNKER DIRECCIÓN) ─────────────────────────────
    ('core', 'venta'):                          'FINANZAS',
    ('core', 'detalleventa'):                   'FINANZAS',
    ('core', 'pago'):                           'FINANZAS',
    ('core', 'pagoorden'):                      'FINANZAS',
    ('core', 'movimientocaja'):                 'FINANZAS',
    ('core', 'gastocaja'):                      'FINANZAS',
    ('core', 'gasto'):                          'FINANZAS',
    ('core', 'gastooperativo'):                 'FINANZAS',
    ('core', 'metaventa'):                      'FINANZAS',
    ('core', 'devolucionventa'):                'FINANZAS',
    ('core', 'salesreturn'):                    'FINANZAS',
    ('core', 'notacredito'):                    'FINANZAS',
    ('core', 'datosfiscales'):                  'FINANZAS',
    ('core', 'facturasat'):                     'FINANZAS',
    ('core', 'cuentaporcobrar'):                'FINANZAS',
    ('core', 'pagocuentaporcobrar'):            'FINANZAS',
    ('core', 'solicitudautorizacion'):          'FINANZAS',
    ('core', 'incidenciaoperativa'):            'FINANZAS',
    ('core', 'buzonquejas'):                    'FINANZAS',
    ('contabilidad', 'facturacfdi'):            'FINANZAS',
    ('contabilidad', 'clientefacturacion'):     'FINANZAS',
    ('contabilidad', 'conceptofactura'):        'FINANZAS',
    ('contabilidad', 'impuestoconcepto'):       'FINANZAS',

    # ── 👔 GESTIÓN DE PERSONAL ── (BÚNKER DIRECCIÓN) ─────────────────────────
    ('core', 'empleado'):                       'PERSONAL',
    ('core', 'registroasistencia'):             'PERSONAL',
    ('core', 'incidenciaasistencia'):           'PERSONAL',
    ('core', 'horariotrabajo'):                 'PERSONAL',
    ('core', 'periodonomina'):                  'PERSONAL',
    ('core', 'recibonomina'):                   'PERSONAL',
    ('core', 'competencia'):                    'PERSONAL',
    ('core', 'evaluaciondesempeno'):            'PERSONAL',
    ('core', 'detalleevaluacion'):              'PERSONAL',
    ('core', 'plandesarrollo'):                 'PERSONAL',
    ('core', 'documentocapacitacion'):          'PERSONAL',
    ('core', 'programacapacitacion'):           'PERSONAL',
    ('core', 'capsulasabiduria'):               'PERSONAL',
    ('core', 'libroliderazgo'):                 'PERSONAL',
    ('core', 'documentoconocimiento'):          'PERSONAL',
    ('marketing', 'campanamarketing'):          'PERSONAL',
    ('marketing', 'cuponmarketing'):            'PERSONAL',
    ('marketing', 'prospectocrm'):              'PERSONAL',
    ('marketing', 'seguimientocrm'):            'PERSONAL',

    # ── 🌱 BIENESTAR Y CULTURA ── (BÚNKER DIRECCIÓN — datos cifrados) ─────────
    ('bienestar', 'diarioemocional'):           'BIENESTAR',
    ('bienestar', 'recursocrecimiento'):        'BIENESTAR',
    ('core', 'diarioemocionalstaff'):           'BIENESTAR',
    ('core', 'sesioncoachingstaff'):            'BIENESTAR',
    ('core', 'evaluacionnom035'):               'BIENESTAR',
    ('core', 'alertabienestar'):                'BIENESTAR',
    ('core', 'alertaburnout'):                  'BIENESTAR',
    ('core', 'conversacionbienestar'):          'BIENESTAR',
    ('core', 'mensajeinterno'):                 'BIENESTAR',
    ('core', 'bitacora39a'):                    'BIENESTAR',

    # ── 🛡️ SEGURIDAD Y AUDITORÍA ── (BÚNKER DIRECCIÓN) ───────────────────────
    ('seguridad', 'logaccionsensible'):         'SEGURIDAD',
    ('seguridad', 'sesionactiva'):              'SEGURIDAD',
    ('seguridad', 'alertapanico'):              'SEGURIDAD',
    ('seguridad', 'codigobackup2fa'):           'SEGURIDAD',
    ('seguridad', 'configuracionseguridad'):    'SEGURIDAD',
    ('seguridad', 'dispositivosms'):            'SEGURIDAD',
    ('seguridad', 'dispositivototp'):           'SEGURIDAD',
    ('core', 'accionpris'):                     'SEGURIDAD',
    ('core', 'voiceauditlog'):                  'SEGURIDAD',
    ('core', 'auditlog'):                       'SEGURIDAD',
    ('core', 'notificacionsistema'):            'SEGURIDAD',
    ('core', 'logaccesoexpediente'):            'SEGURIDAD',
    ('reglas_negocio', 'reglanegocio'):         'SEGURIDAD',
    ('reglas_negocio', 'ejecucionregla'):       'SEGURIDAD',
    ('ia', 'cotizacionocr'):                    'SEGURIDAD',
    ('ia', 'transcripcionvoz'):                 'SEGURIDAD',
    ('core', 'pushsubscription'):               'SEGURIDAD',
    ('core', 'backupregistro'):                 'SEGURIDAD',
    ('core', 'rutalogistica'):                  'SEGURIDAD',
    ('logistica', 'transferenciainventario'):   'SEGURIDAD',
    ('logistica', 'detalletransferencia'):      'SEGURIDAD',
    ('logistica', 'logtransferencia'):          'SEGURIDAD',
    ('logistica', 'rutarecoleccion'):           'SEGURIDAD',
    ('logistica', 'visitadomicilio'):           'SEGURIDAD',
}


def mark_safe_header(text):
    """Helper para evitar importar mark_safe en el nivel del módulo antes de Django setup."""
    try:
        from django.utils.safestring import mark_safe
        return mark_safe(text)
    except ImportError:
        return text


# ─── ADMIN SITE PERSONALIZADO ────────────────────────────────────────────────

class PrislabAdminSite(AdminSite):
    """
    AdminSite de PRISLAB organizado por Departamentos Operativos.

    - Superusuario: ve TODO.
    - Director/Socios: ven todos los departamentos.
    - Personal operativo: solo ven su departamento asignado.
    """
    site_header = 'PRISLAB — Panel de Administración'
    site_title  = 'PRISLAB Admin'
    index_title = 'Emporio PRISLAB — Centro de Operaciones'

    def get_app_list(self, request, app_label=None):
        """
        Reemplaza la lista de apps por la lista de Departamentos.
        Filtra según los grupos del usuario autenticado.
        """
        original_app_list = super().get_app_list(request, app_label)

        if request.user.is_superuser:
            # Superusuario: reorganiza TODOS los modelos por departamento
            return self._build_department_list(original_app_list, allowed_deps=None)

        # Detectar grupos/rol del usuario
        user_groups = set(request.user.groups.values_list('name', flat=True))
        user_rol    = getattr(request.user, 'rol', '').upper()
        if user_rol:
            user_groups.add(user_rol)

        # Determinar qué departamentos puede ver
        allowed_deps = set()
        for dep_key, dep_cfg in DEPARTAMENTOS_CONFIG.items():
            if user_groups & dep_cfg['grupos_permitidos']:
                allowed_deps.add(dep_key)

        # Siempre permitir SISTEMA para staff con is_staff
        # (superuser ya está manejado arriba)

        return self._build_department_list(original_app_list, allowed_deps)

    def _build_department_list(self, original_app_list, allowed_deps):
        """
        Toma la app_list original de Django y la reorganiza como departamentos.
        allowed_deps=None → muestra TODO (superusuario).
        """
        # 1. Aplanar todos los modelos de la lista original
        all_models = []
        for app in original_app_list:
            for model_info in app.get('models', []):
                all_models.append({
                    'app_label':  app['app_label'],
                    'model_info': model_info,
                })

        # 2. Clasificar cada modelo en su departamento
        buckets = {k: [] for k in DEPARTAMENTOS_CONFIG}
        buckets['SISTEMA'] = []

        for entry in all_models:
            al         = entry['app_label']
            model_name = entry['model_info']['object_name'].lower()
            dep_key    = MODEL_DEPARTMENT_MAP.get((al, model_name), 'SISTEMA')
            buckets[dep_key].append(entry['model_info'])

        # 3. Construir la lista de "apps" para el template,
        #    respetando los permisos del usuario
        result = []
        for dep_key, dep_cfg in sorted(
            DEPARTAMENTOS_CONFIG.items(),
            key=lambda x: x[1]['orden']
        ):
            if allowed_deps is not None and dep_key not in allowed_deps:
                continue
            models_in_dep = buckets.get(dep_key, [])
            if not models_in_dep:
                continue
            result.append({
                'name':      dep_cfg['label'],
                'app_label': dep_key.lower(),
                'app_url':   f'#dep-{dep_key.lower()}',
                'has_module_perms': True,
                'models':    sorted(models_in_dep, key=lambda m: m.get('name', '')),
            })

        return result


# Instancia global del site personalizado (opcional — el monkey-patch es la vía principal)
prislab_admin_site = PrislabAdminSite(name='prislab_admin')
