"""
core/management/commands/seed_grupos_permisos.py
═══════════════════════════════════════════════════════════════════════════════
PRISLAB V5.4 — "OPERACIÓN TRANSPARENTE"

Crea (o actualiza) los 8 Grupos Operativos de permisos para segmentación
departamental del Admin y del Dashboard.

Uso:
    python manage.py seed_grupos_permisos

Idempotente: se puede ejecutar múltiples veces sin duplicar registros.
═══════════════════════════════════════════════════════════════════════════════
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps


# ─── CONFIGURACIÓN DE GRUPOS ─────────────────────────────────────────────────
# Formato: 'NOMBRE_GRUPO': [('app_label', 'model_name', ['action',...]), ...]
# actions: 'view', 'add', 'change', 'delete'  (view = solo lectura)

GRUPOS_CONFIG = {

    # ─── LABORATORIO ─────────────────────────────────────────────────────────
    'LABORATORIO': {
        'descripcion': 'Químicos y analistas de laboratorio',
        'permisos': [
            # Laboratorio — operaciones completas
            ('laboratorio', 'estudio',                  ['view', 'add', 'change']),
            ('laboratorio', 'parametro',                ['view', 'add', 'change']),
            ('laboratorio', 'valorreferencia',          ['view', 'add', 'change']),
            ('laboratorio', 'rangoreferenciaparametro', ['view', 'add', 'change']),
            ('laboratorio', 'perfillaboratorio',        ['view', 'add', 'change']),
            ('laboratorio', 'orden',                    ['view', 'add', 'change']),
            ('laboratorio', 'detalleorden',             ['view', 'add', 'change']),
            ('laboratorio', 'resultado',                ['view', 'add', 'change']),
            ('laboratorio', 'resultadohl7',             ['view']),
            ('laboratorio', 'equipo',                   ['view', 'change']),
            ('laboratorio', 'codigoparametroequipo',    ['view', 'add', 'change']),
            ('laboratorio', 'notificacionpanico',       ['view']),
            ('laboratorio', 'controlcalidad',           ['view', 'add']),
            ('laboratorio', 'bitacoramantenimiento',    ['view', 'add']),
            ('laboratorio', 'historialresultados',      ['view']),
            ('laboratorio', 'insumoestudio',            ['view', 'add', 'change']),
            ('laboratorio', 'categoriaexamen',          ['view', 'add', 'change']),
            ('core', 'resultadoparametro',              ['view', 'add', 'change']),
            ('core', 'ordendeservicio',                 ['view', 'add', 'change']),
            ('core', 'detalleorden',                    ['view', 'add', 'change']),
            ('core', 'tomamuestra',                     ['view', 'add', 'change']),
            ('core', 'bitacoraentregaresultados',       ['view', 'change']),
            # Pacientes — solo lectura (necesitan ver el expediente)
            ('core', 'paciente',                        ['view']),
            ('core', 'historiaclinica',                 ['view']),
        ],
    },

    # ─── FARMACIA ─────────────────────────────────────────────────────────────
    'FARMACIA': {
        'descripcion': 'Personal de farmacia y dispensación',
        'permisos': [
            ('core',     'producto',             ['view', 'add', 'change']),
            ('core',     'lote',                 ['view', 'add', 'change']),
            ('core',     'ajusteinventario',     ['view', 'add']),
            ('core',     'demandainsatisfecha',  ['view', 'add']),
            ('farmacia', 'proveedor',            ['view', 'add', 'change']),
            ('farmacia', 'movimientoinventario', ['view', 'add']),
            ('farmacia', 'mermafarmacia',        ['view', 'add']),
            ('farmacia', 'registroantibiotico',  ['view', 'add']),
            ('farmacia', 'devolucionventa',      ['view', 'add']),
            ('farmacia', 'aperturacaja',         ['view', 'add']),
            ('farmacia', 'cierreturnofarmacia',  ['view', 'add']),
            # Pacientes — solo lectura
            ('core', 'paciente',                 ['view']),
        ],
    },

    # ─── CAJERO ───────────────────────────────────────────────────────────────
    'CAJERO': {
        'descripcion': 'Cajeros y recepcionistas de caja',
        'permisos': [
            ('core', 'venta',            ['view', 'add', 'change']),
            ('core', 'detalleventa',     ['view', 'add']),
            ('core', 'pago',             ['view', 'add']),
            ('core', 'movimientocaja',   ['view', 'add']),
            ('core', 'gastocaja',        ['view', 'add']),
            ('core', 'paciente',         ['view', 'add', 'change']),
            ('core', 'ordendeservicio',  ['view', 'add']),
        ],
    },

    # ─── RECEPCION ────────────────────────────────────────────────────────────
    'RECEPCION': {
        'descripcion': 'Recepcionistas y personal de toma de muestra',
        'permisos': [
            ('core', 'paciente',         ['view', 'add', 'change']),
            ('core', 'ordendeservicio',  ['view', 'add', 'change']),
            ('core', 'detalleorden',     ['view', 'add']),
            ('core', 'tomamuestra',      ['view', 'add', 'change']),
            ('core', 'consentimientoinformado', ['view', 'add']),
            ('laboratorio', 'estudio',   ['view']),
        ],
    },

    # ─── MEDICO ───────────────────────────────────────────────────────────────
    'MEDICO': {
        'descripcion': 'Médicos y personal clínico del consultorio',
        'permisos': [
            ('core', 'paciente',            ['view', 'add', 'change']),
            ('core', 'historiaclinica',     ['view', 'add', 'change']),
            ('core', 'antecedente',         ['view', 'add', 'change']),
            ('core', 'notaclinicasoap',     ['view', 'add', 'change']),
            ('core', 'receta',              ['view', 'add', 'change']),
            ('core', 'recetaitem',          ['view', 'add', 'change']),
            ('core', 'citamedica',          ['view', 'add', 'change']),
            ('core', 'consultamedica',      ['view', 'add', 'change']),
            ('core', 'certificadomedico',   ['view', 'add', 'change']),
            ('core', 'audioconsulta',       ['view', 'add']),
            ('consultorio', 'agendacita',   ['view', 'add', 'change']),
            ('consultorio', 'consultamedica', ['view', 'add', 'change']),
            ('consultorio', 'somatometria', ['view', 'add', 'change']),
            ('consultorio', 'vademecum',    ['view']),
            # Puede ver resultados de lab de sus pacientes
            ('laboratorio', 'resultado',    ['view']),
            ('core', 'resultadoparametro',  ['view']),
        ],
    },

    # ─── DIRECTOR / SOCIOS ────────────────────────────────────────────────────
    'DIRECTOR': {
        'descripcion': 'Director General y socios — acceso global con búnker de privacidad',
        'permisos': [
            # Recibe todos los permisos en tiempo de ejecución (is_staff=True + grupo)
            # Solo marcamos los modelos del búnker que NO tienen otros grupos
        ],
        'all_perms': True,   # Flag especial: asigna todos los permisos disponibles
    },

    'SOCIOS': {
        'descripcion': 'Socios y auditores externos — solo lectura global',
        'permisos': [],
        'all_view_perms': True,  # Flag especial: asigna solo permisos 'view' de todo
    },
}


class Command(BaseCommand):
    help = (
        'Crea o actualiza los 8 Grupos Operativos de permisos departamentales '
        'para PRISLAB V5.4 (idempotente).'
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n🏛️  PRISLAB V5.4 — Creando Grupos Operativos...\n'
        ))

        creados  = 0
        actualizados = 0

        for nombre_grupo, config in GRUPOS_CONFIG.items():
            grupo, created = Group.objects.get_or_create(name=nombre_grupo)
            if created:
                creados += 1
                self.stdout.write(f'  ✅ Creado:     {nombre_grupo}')
            else:
                actualizados += 1
                self.stdout.write(f'  🔄 Existente:  {nombre_grupo}')

            # ── Caso especial: Director con TODOS los permisos ────────────────
            if config.get('all_perms'):
                todos = Permission.objects.all()
                grupo.permissions.set(todos)
                self.stdout.write(f'     → {todos.count()} permisos asignados (acceso total)')
                continue

            # ── Caso especial: Socios con solo VIEW ───────────────────────────
            if config.get('all_view_perms'):
                view_perms = Permission.objects.filter(codename__startswith='view_')
                grupo.permissions.set(view_perms)
                self.stdout.write(f'     → {view_perms.count()} permisos de solo lectura')
                continue

            # ── Permisos específicos por modelo ──────────────────────────────
            perms_to_assign = []
            for app_label, model_name, actions in config.get('permisos', []):
                try:
                    ct = ContentType.objects.get(app_label=app_label, model=model_name)
                except ContentType.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'     ⚠️  Modelo no encontrado: {app_label}.{model_name}'
                        )
                    )
                    continue

                for action in actions:
                    codename = f'{action}_{model_name}'
                    try:
                        perm = Permission.objects.get(content_type=ct, codename=codename)
                        perms_to_assign.append(perm)
                    except Permission.DoesNotExist:
                        pass  # El permiso no existe (normal para acciones custom)

            grupo.permissions.set(perms_to_assign)
            self.stdout.write(f'     → {len(perms_to_assign)} permisos configurados')

        self.stdout.write('\n' + self.style.SUCCESS(
            f'✅  COMPLETADO — {creados} grupos creados, {actualizados} grupos actualizados.\n'
            f'    Asigna los grupos a los usuarios desde:\n'
            f'    /admin/ → Autenticación y Autorización → Grupos\n'
        ))
