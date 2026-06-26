"""
Módulo de Vistas para Gestión de Pacientes.
Incluye: Búsqueda de pacientes, creación rápida desde modales.
"""
import json
import logging

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from core.models import Empresa, Paciente, DiscountPolicy
from core.utils.empresa_request import empresa_efectiva_request

logger = logging.getLogger(__name__)


def _empresa_efectiva_pacientes(request):
    return empresa_efectiva_request(request)


def api_buscar_pacientes(request):
    """
    API para buscar pacientes por nombre o teléfono.
    
    Entrada:
        - GET: query parameter 'q' (mínimo 2 caracteres)
        - Requiere autenticación; en AJAX devuelve JSON 401 si la sesión expiró
    
    Salida:
        - JSON: {'pacientes': [{'id': int, 'nombre': str, ...}]}
        - Siempre devuelve JSON, incluso en caso de error
    
    Excepciones:
        - Si el usuario no está autenticado, devuelve JSON para evitar redirects HTML en fetch()
        - Si no hay empresa asignada, devuelve JSON con error
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'code': 'AUTH_REQUIRED',
            'mensaje': 'Sesión expirada. Inicia sesión nuevamente.',
            'pacientes': []
        }, status=401)

    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)
    
    empresa = _empresa_efectiva_pacientes(request)
    if not empresa:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Usuario sin empresa asignada',
            'pacientes': []
        }, status=400)

    # Aceptar 'nombre' (PDV) o 'q' (otros flujos) para compatibilidad
    query = (request.GET.get('nombre') or request.GET.get('q') or '').strip()
    
    try:
        if not query or len(query) < 2:
            return JsonResponse({'pacientes': []})
        
        pacientes = Paciente.objects.filter(
            empresa=empresa,
            activo=True
        ).select_related('politica_descuento')
        q_filter = (
            Q(nombre_completo__icontains=query) |
            Q(telefono__icontains=query) |
            Q(nombres__icontains=query) |
            Q(apellido_paterno__icontains=query)
        )
        if query.isdigit():
            q_filter |= Q(id=int(query))
        pacientes = pacientes.filter(q_filter
        )[:10]
        
        resultados = []
        for p in pacientes:
            descuento_info = None
            if p.politica_descuento and hasattr(p.politica_descuento, 'activa') and p.politica_descuento.activa:
                descuento_info = {
                    'porcentaje': float(p.politica_descuento.porcentaje_descuento),
                    'requiere_autorizacion': p.politica_descuento.requiere_autorizacion,
                    'nombre_politica': p.politica_descuento.nombre
                }
            
            resultados.append({
                'id': p.id,
                'nombre': p.nombre_completo,
                'tipo': p.tipo,
                'telefono': p.telefono or '',
                'edad': p.edad if hasattr(p, 'edad') else None,
                'sexo': p.sexo if hasattr(p, 'sexo') else '',
                'descuento': descuento_info
            })
        
        return JsonResponse({'pacientes': resultados})
    
    except Exception as e:
        logger.error('Error en api_buscar_pacientes: %s', e, exc_info=True)
        
        # Siempre devolver JSON, nunca HTML
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al buscar pacientes: {str(e)}',
            'pacientes': []
        }, status=500)

@login_required
def api_guardar_paciente(request):
    """API para crear o actualizar un paciente rápidamente desde un modal."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)
    
    empresa = _empresa_efectiva_pacientes(request)
    if not empresa:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Usuario sin empresa asignada. Configure su empresa en el panel de administración.',
        }, status=400)
    
    try:
        # Parsear JSON
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'status': 'error', 'mensaje': 'Error al procesar los datos JSON: ' + str(e)}, status=400)
        
        # Aceptar nombres separados O nombre completo
        nombres_sep = data.get('nombres', '').strip()
        ap_paterno = data.get('apellido_paterno', data.get('apellidos', '')).strip() if data.get('apellido_paterno') or data.get('apellidos') else ''
        ap_materno = data.get('apellido_materno', '').strip()
        nombre_completo_raw = data.get('nombre', '').strip()

        # Construir nombre_completo desde campos separados si vienen
        if nombres_sep:
            partes = [nombres_sep]
            if ap_paterno:
                partes.append(ap_paterno)
            if ap_materno:
                partes.append(ap_materno)
            nombre = ' '.join(partes)
        else:
            nombre = nombre_completo_raw

        fecha_nacimiento = data.get('fecha_nacimiento', '').strip() if data.get('fecha_nacimiento') else None
        edad = data.get('edad')  # Puede venir como int o None
        sexo = data.get('sexo', '').strip() if data.get('sexo') else None
        telefono = data.get('telefono', '').strip() if data.get('telefono') else None
        email = data.get('email', '').strip() if data.get('email') else None
        tipo = data.get('tipo', 'GENERAL')
        
        # Validación de campos requeridos
        if not nombre:
            return JsonResponse({'status': 'error', 'mensaje': 'El nombre es obligatorio'}, status=400)
        
        # Validar formato de fecha si se proporciona, o calcular desde edad
        fecha_nac_obj = None
        if fecha_nacimiento:
            try:
                from datetime import datetime
                fecha_nac_obj = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'status': 'error', 'mensaje': 'Formato de fecha inválido. Use YYYY-MM-DD'}, status=400)
        elif edad is not None:
            # Si no hay fecha pero sí edad, calcular la fecha de nacimiento
            try:
                from datetime import datetime, date
                edad_int = int(edad)
                if edad_int < 0 or edad_int > 150:
                    return JsonResponse({'status': 'error', 'mensaje': 'La edad debe estar entre 0 y 150 años'}, status=400)
                
                hoy = date.today()
                # Calcular fecha de nacimiento restando los años
                fecha_nac_obj = date(hoy.year - edad_int, hoy.month, hoy.day)
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'mensaje': 'Edad inválida. Debe ser un número entre 0 y 150'}, status=400)
        
        # Crear o actualizar paciente
        try:
            defaults_pac = {
                'fecha_nacimiento': fecha_nac_obj,
                'sexo': sexo if sexo in ['M', 'F'] else None,
                'telefono': telefono if telefono else None,
                'email': email if email else None,
                'tipo': tipo,
                'activo': True,
            }
            # Poblar campos de nombre separados si vinieron
            if nombres_sep:
                defaults_pac['nombres'] = nombres_sep
            if ap_paterno:
                defaults_pac['apellido_paterno'] = ap_paterno
            if ap_materno:
                defaults_pac['apellido_materno'] = ap_materno

            paciente, creado = Paciente.objects.get_or_create(
                empresa=empresa,
                nombre_completo=nombre,
                defaults=defaults_pac,
            )
            
            # Si ya existía, actualizar campos opcionales
            if not creado:
                # Actualizar fecha de nacimiento si se proporciona (directa o calculada desde edad)
                if fecha_nac_obj:
                    paciente.fecha_nacimiento = fecha_nac_obj
                # Si se proporcionó edad pero no fecha, calcular y actualizar
                elif edad is not None:
                    from datetime import date
                    edad_int = int(edad)
                    hoy = date.today()
                    paciente.fecha_nacimiento = date(hoy.year - edad_int, hoy.month, hoy.day)
                
                if sexo and sexo in ['M', 'F']:
                    paciente.sexo = sexo
                if telefono:
                    paciente.telefono = telefono
                if email:
                    paciente.email = email
                paciente.activo = True
                paciente.save()

            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='CREATE' if creado else 'UPDATE',
                modelo='Paciente',
                objeto_id=str(paciente.id),
                datos_nuevos={
                    'nombre_completo': paciente.nombre_completo,
                    'telefono': paciente.telefono or '',
                    'sexo': getattr(paciente, 'sexo', ''),
                },
                request=request,
            )
            
            return JsonResponse({
                'status': 'success',
                'success': True,
                'mensaje': 'Paciente creado correctamente' if creado else 'Paciente actualizado correctamente',
                'paciente': {
                    'id': paciente.id,
                    'uuid': str(paciente.uuid) if paciente.uuid else '',
                    'codigo': str(paciente.uuid)[:8].upper() if paciente.uuid else f'P-{paciente.id}',
                    'nombre': paciente.nombre_completo,
                    'nombre_completo': paciente.nombre_completo,
                    'nombres': paciente.nombres or '',
                    'apellido_paterno': paciente.apellido_paterno or '',
                    'apellido_materno': paciente.apellido_materno or '',
                    'tipo': paciente.tipo,
                    'telefono': paciente.telefono or '',
                    'email': paciente.email or '',
                    'edad': paciente.calcular_edad() if hasattr(paciente, 'calcular_edad') else None,
                    'sexo': paciente.sexo if hasattr(paciente, 'sexo') else '',
                }
            })
        except Exception as db_error:
            logging.getLogger(__name__).exception("Error inesperado en api_guardar_paciente (pacientes.py)")
            return JsonResponse({'status': 'error', 'mensaje': f'Error al guardar el paciente en la base de datos: {str(db_error)}'}, status=500)
        
    except Exception as e:
        logger.error('Error en api_guardar_paciente', exc_info=True)
        return JsonResponse({'status': 'error', 'mensaje': 'Error inesperado al guardar el paciente. Contacte al administrador.'}, status=500)

# Alias para compatibilidad con código existente
@login_required
def buscar_paciente(request):
    """Buscar paciente por nombre para aplicar descuentos automáticos (compatibilidad)."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    nombre = request.GET.get('nombre', '').strip()
    empresa = _empresa_efectiva_pacientes(request)

    if nombre and empresa:
        q_filter = Q(nombre_completo__icontains=nombre) | Q(telefono__icontains=nombre)
        if nombre.isdigit():
            q_filter |= Q(id=int(nombre))
        pacientes = Paciente.objects.filter(
            empresa=empresa,
            activo=True,
        ).filter(q_filter).select_related('politica_descuento')[:10]

        resultados = []
        for p in pacientes:
            descuento_info = None
            if p.politica_descuento and getattr(p.politica_descuento, 'activa', False):
                descuento_info = {
                    'porcentaje': float(p.politica_descuento.porcentaje_descuento),
                    'requiere_autorizacion': p.politica_descuento.requiere_autorizacion,
                    'nombre_politica': p.politica_descuento.nombre,
                }

            resultados.append({
                'id': p.id,
                'nombre': p.nombre_completo,
                'tipo': p.tipo,
                'telefono': p.telefono or '',
                'edad': p.edad if hasattr(p, 'edad') else None,
                'sexo': p.sexo if hasattr(p, 'sexo') else '',
                'descuento': descuento_info,
            })

        return JsonResponse({'pacientes': resultados})

    return JsonResponse({'pacientes': []})