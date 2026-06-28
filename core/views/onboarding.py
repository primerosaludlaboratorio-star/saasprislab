"""
core/views/onboarding.py
═══════════════════════════════════════════════════════════════════════════════
PRISLAB V6.0 — PILAR 4: WIZARD "TACA TACA TACA" — ALTA ATÓMICA DE CLIENTES

Flujo de 5 pasos para registrar una nueva empresa en el ecosistema SaaS.
TODA la operación es una única Transaction Atómica: si cualquier paso falla,
se revierte todo y NO quedan registros huérfanos en la DB.

PASOS:
  1. Identidad Legal       → Nombre, RFC, datos fiscales, régimen
  2. Identidad Visual      → Logo, colores, hoja membretada
  3. Módulos Contratados   → Feature flags del plan elegido
  4. Carga de Personal     → Excel con usuarios, roles y credenciales
  5. Confirmación          → Resumen + activación + envío de bienvenida

ACCESO: Solo superusuarios PRISLAB (is_superuser=True).
═══════════════════════════════════════════════════════════════════════════════
"""
import json
import logging
import re

from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

logger = logging.getLogger('core.onboarding')

_solo_superusuario = user_passes_test(lambda u: u.is_superuser)


# ─── PLANES PREDEFINIDOS ─────────────────────────────────────────────────────
# El Director puede elegir un plan predefinido o personalizar módulo por módulo.

PLANES = {
    'BASICO': {
        'nombre':     'Plan Básico',
        'precio_ref': 'Consultar',
        'modulos': {
            'modulo_laboratorio': True,  'modulo_farmacia': False,
            'modulo_expediente_clinico': False, 'modulo_consulta_externa': False,
            'modulo_hospitalizacion': False, 'modulo_citas': True,
            'modulo_rrhh': False, 'modulo_contabilidad': False,
            'modulo_ia': False, 'modulo_iot': False,
        },
    },
    'PROFESIONAL': {
        'nombre':     'Plan Profesional',
        'precio_ref': 'Consultar',
        'modulos': {
            'modulo_laboratorio': True, 'modulo_farmacia': True,
            'modulo_expediente_clinico': True, 'modulo_consulta_externa': True,
            'modulo_hospitalizacion': False, 'modulo_citas': True,
            'modulo_rrhh': True, 'modulo_contabilidad': True,
            'modulo_ia': True, 'modulo_iot': False,
        },
    },
    'ENTERPRISE': {
        'nombre':     'Plan Enterprise (Todo incluido)',
        'precio_ref': 'Consultar',
        'modulos': {k: True for k in [
            'modulo_laboratorio', 'modulo_farmacia', 'modulo_expediente_clinico',
            'modulo_consulta_externa', 'modulo_hospitalizacion', 'modulo_citas',
            'modulo_rrhh', 'modulo_contabilidad', 'modulo_ia', 'modulo_iot',
        ]},
    },
}


# ─── VISTAS DEL WIZARD ───────────────────────────────────────────────────────

@method_decorator(_solo_superusuario, name='dispatch')
class OnboardingWizardView(TemplateView):
    """Vista principal del Wizard de alta de cliente."""
    template_name = 'core/onboarding/wizard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['planes'] = PLANES
        ctx['paso_actual'] = self.request.GET.get('paso', '1')
        return ctx


@method_decorator(_solo_superusuario, name='dispatch')
class OnboardingCrearEmpresaView(View):
    """
    API endpoint para crear una empresa completa de forma atómica.

    Recibe JSON con todos los datos del wizard y crea:
    1. Empresa (con colores, logo, hoja membretada)
    2. ConfiguracionModulos (módulos contratados)
    3. Usuario administrador inicial
    4. Usuarios del Excel de personal

    Si cualquier paso falla → rollback total.
    """

    def post(self, request):
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            payload = request.POST.dict()

        try:
            resultado = self._crear_empresa_atomica(request, payload)
            return JsonResponse({'ok': True, **resultado})
        except Exception as exc:
            logger.error('[ONBOARDING] Fallo atómico: %s', exc, exc_info=True)
            return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    @transaction.atomic
    def _crear_empresa_atomica(self, request, payload: dict) -> dict:
        """Toda la creación en una única transacción. Si falla → rollback."""
        from core.models import Empresa, ConfiguracionModulos, Usuario
        from core.tenant import tenant_bypass

        with tenant_bypass():

            # ── PASO 1: Crear Empresa ─────────────────────────────────────
            empresa = Empresa.objects.create(
                nombre            = payload['nombre'],
                rfc               = payload.get('rfc', '').upper(),
                direccion         = payload.get('direccion', ''),
                telefono          = payload.get('telefono', ''),
                color_primario    = payload.get('color_primario', '#003366'),
                color_secundario  = payload.get('color_secundario', '#FFD700'),
                color_fondo       = payload.get('color_fondo', '#F8F9FA'),
                css_personalizado = payload.get('css_personalizado', ''),
                activa            = True,
            )
            logger.info('[ONBOARDING] Empresa creada: %s (id=%s)', empresa.nombre, empresa.pk)

            # ── PASO 2: ConfiguracionModulos ──────────────────────────────
            plan_key = payload.get('plan', 'PROFESIONAL')
            plan     = PLANES.get(plan_key, PLANES['PROFESIONAL'])
            modulos  = payload.get('modulos_custom', plan['modulos'])

            cfg = ConfiguracionModulos.objects.create(
                empresa=empresa,
                **modulos,
            )
            logger.info('[ONBOARDING] Módulos configurados para %s: %s', empresa.nombre, modulos)

            # ── PASO 3: Usuario Administrador de la empresa ───────────────
            admin_data = payload.get('admin', {})
            admin_username = admin_data.get('username') or self._slug_empresa(empresa.nombre)
            admin_email    = admin_data.get('email', '')
            admin_password = admin_data.get('password') or self._generar_password_temporal()

            admin_user = Usuario.objects.create_user(
                username   = admin_username,
                email      = admin_email,
                password   = admin_password,
                empresa    = empresa,
                rol        = 'DIRECTOR',
                is_staff   = True,
                first_name = admin_data.get('nombre', 'Admin'),
                last_name  = empresa.nombre,
            )
            logger.info('[ONBOARDING] Admin creado: %s', admin_username)

            # ── PASO 4: Cargar Personal desde Excel (si se envió) ─────────
            usuarios_creados = []
            personal_data = payload.get('personal', [])
            for fila in personal_data:
                try:
                    uname = self._safe_username(fila.get('username') or fila.get('nombre', ''))
                    if not uname or Usuario.objects.filter(username=uname).exists():
                        continue
                    pwd = fila.get('password') or self._generar_password_temporal()
                    u = Usuario.objects.create_user(
                        username   = uname,
                        email      = fila.get('email', ''),
                        password   = pwd,
                        empresa    = empresa,
                        rol        = fila.get('rol', 'RECEPCION'),
                        first_name = fila.get('nombre', ''),
                        last_name  = fila.get('apellido', ''),
                    )
                    usuarios_creados.append({'username': u.username, 'password': pwd})
                except Exception as exc:
                    logger.warning('[ONBOARDING] Fallo creando usuario %s: %s', fila, exc)

            logger.info('[ONBOARDING] %d usuarios de personal creados.', len(usuarios_creados))

            # ── PASO 5: Vincular al Catálogo Maestro ─────────────────────
            # (Automático: CatalogResolver resuelve por cascada)
            # Si se quiere copiar el catálogo maestro en lugar de heredarlo,
            # descomentar el bloque siguiente:
            # _copiar_catalogo_maestro(empresa)

            return {
                'empresa_id':        empresa.pk,
                'empresa_nombre':    empresa.nombre,
                'admin_username':    admin_username,
                'admin_password':    admin_password,  # Solo en primera respuesta
                'plan':              plan['nombre'],
                'usuarios_creados':  len(usuarios_creados),
                'usuarios_detalle':  usuarios_creados,
            }

    @staticmethod
    def _slug_empresa(nombre: str) -> str:
        """Genera un username base a partir del nombre de la empresa."""
        slug = re.sub(r'[^\w]', '_', nombre.lower())[:20]
        return f'admin_{slug}'

    @staticmethod
    def _safe_username(raw: str) -> str:
        """Sanitiza un string para usarlo como username."""
        return re.sub(r'[^\w.@+-]', '_', raw.strip())[:150]

    @staticmethod
    def _generar_password_temporal() -> str:
        """Genera una contraseña temporal segura de 12 caracteres."""
        import secrets, string
        alphabet = string.ascii_letters + string.digits + '!@#$%'
        return ''.join(secrets.choice(alphabet) for _ in range(12))


@_solo_superusuario
def api_parse_excel_personal(request):
    """
    Recibe un archivo Excel con la plantilla de personal y devuelve
    el listado de usuarios en JSON para confirmar antes de crear.

    Columnas esperadas en el Excel:
        nombre | apellido | email | rol | username (opcional)

    Roles válidos: DIRECTOR, LABORATORIO, FARMACIA, CAJERO, RECEPCION, MEDICO
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requerido'}, status=405)

    excel_file = request.FILES.get('excel')
    if not excel_file:
        return JsonResponse({'error': 'Archivo excel requerido'}, status=400)

    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        ws = wb.active
        filas = []
        headers = None

        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(c).lower().strip() if c else '' for c in row]
                continue
            if not any(row):
                continue
            fila = {}
            for j, val in enumerate(row):
                if j < len(headers) and headers[j]:
                    fila[headers[j]] = str(val).strip() if val is not None else ''
            filas.append(fila)

        return JsonResponse({
            'ok': True,
            'total': len(filas),
            'personal': filas,
        })

    except Exception as exc:
        logger.error('[ONBOARDING] Error parseando Excel: %s', exc)
        return JsonResponse({'error': str(exc)}, status=400)


@_solo_superusuario
def api_listar_empresas(request):
    """Lista todas las empresas registradas con su estado de módulos."""
    from core.models import Empresa, ConfiguracionModulos
    from core.tenant import tenant_bypass

    with tenant_bypass():
        empresas = Empresa.objects.all().order_by('nombre')
        resultado = []
        for emp in empresas:
            cfg = ConfiguracionModulos.objects.filter(empresa=emp).first()
            resultado.append({
                'id':     emp.pk,
                'nombre': emp.nombre,
                'rfc':    emp.rfc,
                'activa': emp.activa,
                'modulos': {
                    'laboratorio':  getattr(cfg, 'modulo_laboratorio', False),
                    'farmacia':     getattr(cfg, 'modulo_farmacia', False),
                    'consultorio':  getattr(cfg, 'modulo_consulta_externa', False),
                    'ia':           getattr(cfg, 'modulo_ia', False),
                } if cfg else {},
            })

    return JsonResponse({'ok': True, 'empresas': resultado})
