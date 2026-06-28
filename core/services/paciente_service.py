"""
PRISLAB V5 - Servicio de Gestión de Pacientes
Lógica centralizada para evitar duplicados y gestionar la identidad transversal
"""

import logging
from django.db.models import Q
from django.utils.text import slugify
from core.models import Paciente

logger = logging.getLogger(__name__)


def buscar_paciente_existente(nombre_completo, fecha_nacimiento=None, telefono=None, empresa=None):
    """
    Busca si ya existe un paciente en el sistema antes de crear uno nuevo.
    
    Estrategia de búsqueda (en orden de prioridad):
    1. Nombre + Fecha de Nacimiento (match exacto)
    2. Teléfono (si se proporciona)
    3. Nombre similar (fuzzy match por slug)
    
    Args:
        nombre_completo (str): Nombre del paciente
        fecha_nacimiento (date, optional): Fecha de nacimiento
        telefono (str, optional): Teléfono
        empresa (Empresa, optional): Filtrar por empresa
    
    Returns:
        Paciente|None: Paciente encontrado o None si no existe
    """
    if not nombre_completo:
        return None
    
    query = Q(activo=True, deleted_at__isnull=True)
    
    if empresa:
        query &= Q(empresa=empresa)
    
    # Búsqueda 1: Nombre + Fecha de Nacimiento (más precisa)
    if nombre_completo and fecha_nacimiento:
        paciente = Paciente.objects.filter(
            query,
            nombre_completo__iexact=nombre_completo.strip(),
            fecha_nacimiento=fecha_nacimiento
        ).first()
        
        if paciente:
            logger.info(f"Paciente encontrado por Nombre + Fecha Nac: {paciente.uuid}")
            return paciente
    
    # Búsqueda 2: Teléfono (si se proporciona y no está vacío)
    if telefono and telefono.strip():
        # Limpiar teléfono de caracteres especiales
        telefono_limpio = ''.join(filter(str.isdigit, telefono))
        
        if len(telefono_limpio) >= 10:  # Teléfono válido
            paciente = Paciente.objects.filter(
                query,
                telefono__icontains=telefono_limpio[-10:]  # Últimos 10 dígitos
            ).first()
            
            if paciente:
                logger.info(f"Paciente encontrado por Teléfono: {paciente.uuid}")
                return paciente
    
    # Búsqueda 3: Nombre similar (fuzzy match)
    # Normalizar nombre para comparación
    nombre_slug = slugify(nombre_completo).replace('-', ' ')
    
    if nombre_slug:
        pacientes_similares = Paciente.objects.filter(query)
        
        for paciente in pacientes_similares:
            paciente_slug = slugify(paciente.nombre_completo).replace('-', ' ')
            
            # Si los nombres normalizados son muy similares
            if nombre_slug == paciente_slug:
                logger.info(f"Paciente encontrado por Nombre similar: {paciente.uuid}")
                return paciente
    
    logger.info(f"No se encontró paciente existente para: {nombre_completo}")
    return None


def obtener_o_crear_paciente(nombre_completo, fecha_nacimiento=None, sexo=None, 
                             telefono=None, email=None, alergias=None,
                             tipo='GENERAL', empresa=None, sucursal=None, 
                             buscar_duplicados=True):
    """
    Obtiene un paciente existente o crea uno nuevo si no existe.
    
    Args:
        nombre_completo (str): Nombre del paciente
        fecha_nacimiento (date, optional): Fecha de nacimiento
        sexo (str, optional): 'M' o 'F'
        telefono (str, optional): Teléfono
        email (str, optional): Email
        alergias (str, optional): Alergias conocidas
        tipo (str): Tipo de paciente (default: 'GENERAL')
        empresa (Empresa): Empresa (requerido)
        sucursal (Sucursal, optional): Sucursal de registro
        buscar_duplicados (bool): Si True, busca duplicados antes de crear
    
    Returns:
        tuple: (Paciente, created: bool)
    """
    if not empresa:
        raise ValueError("Se requiere una empresa para crear/buscar pacientes")
    
    # Buscar duplicados si está habilitado
    if buscar_duplicados:
        paciente_existente = buscar_paciente_existente(
            nombre_completo=nombre_completo,
            fecha_nacimiento=fecha_nacimiento,
            telefono=telefono,
            empresa=empresa
        )
        
        if paciente_existente:
            logger.info(f"Usando paciente existente: {paciente_existente.uuid}")
            return (paciente_existente, False)
    
    # Crear nuevo paciente
    paciente = Paciente.objects.create(
        empresa=empresa,
        sucursal=sucursal,
        nombre_completo=nombre_completo.strip(),
        fecha_nacimiento=fecha_nacimiento,
        sexo=sexo,
        telefono=telefono,
        email=email,
        alergias=alergias or 'Ninguna',
        tipo=tipo,
        activo=True
    )
    
    logger.info(f"Paciente creado: {paciente.uuid} - {paciente.nombre_completo}")
    return (paciente, True)


def obtener_timeline_paciente(paciente):
    """
    Obtiene la línea de tiempo completa del paciente (Consultas + Lab + Farmacia).
    
    Args:
        paciente (Paciente): Instancia del paciente
    
    Returns:
        list: Lista de eventos ordenados cronológicamente (más reciente primero)
    """
    from core.models import ConsultaMedica, OrdenDeServicio, Venta
    
    eventos = []
    
    # 1. CONSULTAS MÉDICAS (core.ConsultaMedica: medico es Medico, tiene nombre_completo)
    consultas = ConsultaMedica.objects.filter(
        paciente=paciente
    ).select_related('medico', 'sucursal').order_by('-fecha_consulta')
    
    for consulta in consultas:
        medico_nombre = consulta.medico.nombre_completo if consulta.medico else 'N/A'
        eventos.append({
            'tipo': 'CONSULTA',
            'fecha': consulta.fecha_consulta,
            'titulo': f'Consulta Médica - Dr. {medico_nombre}',
            'descripcion': consulta.motivo_consulta or 'Sin motivo especificado',
            # Ruta canónica: resuelve detalle directo o redirige a SOAP si la consulta viene de una cita.
            'url': f'/consultorio/medico/consulta/ver/{consulta.id}/',
            'icono': 'bi-clipboard-pulse',
            'color': 'primary',
            'objeto': consulta
        })
    
    # 2. ÓRDENES DE LABORATORIO (core.OrdenDeServicio — v7.5)
    ordenes = OrdenDeServicio.objects.filter(
        paciente=paciente,
        estado__in=('RESULTADOS_LISTOS', 'ENTREGADO'),
    ).select_related('sucursal').order_by('-fecha_creacion')
    
    for orden in ordenes:
        eventos.append({
            'tipo': 'LABORATORIO',
            'fecha': orden.fecha_creacion,
            'titulo': f'Resultados de Laboratorio - {orden.folio_orden or orden.id}',
            'descripcion': f'Estado: {orden.get_estado_display()}',
            'url': f'/laboratorio/captura/{orden.id}/',
            'icono': 'bi-clipboard2-data',
            'color': 'success',
            'objeto': orden
        })
    
    # 3. VENTAS DE FARMACIA (modelo canonico core.Venta)
    try:
        ventas = Venta.objects.filter(
            empresa=paciente.empresa,
            paciente=paciente
        ).select_related('sucursal').prefetch_related('detalles__producto').order_by('-fecha')
        
        for venta in ventas:
            detalles_texto = f"Total: ${venta.total:.2f}"
            if hasattr(venta, 'detalles'):
                num_items = venta.detalles.count()
                detalles_texto += f" ({num_items} medicamentos)"
            
            eventos.append({
                'tipo': 'FARMACIA',
                'fecha': venta.fecha,
                'titulo': f'Surtido de Medicamentos - Folio {venta.folio_operacion or venta.id}',
                'descripcion': detalles_texto,
                'url': f'/farmacia/ticket/{venta.id}/',
                'icono': 'bi-capsule',
                'color': 'warning',
                'objeto': venta
            })
    except Exception as e:
        logger.warning(f"No se pudieron cargar ventas de farmacia: {e}")
    
    # Ordenar todos los eventos por fecha descendente
    eventos.sort(key=lambda x: x['fecha'], reverse=True)
    
    logger.info(f"Timeline generado para paciente {paciente.uuid}: {len(eventos)} eventos")
    return eventos
