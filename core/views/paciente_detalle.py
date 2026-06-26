"""
PRISLAB V5.0 - EXPEDIENTE CLÍNICO UNIFICADO (HUB CENTRAL DEL PACIENTE)
=======================================================================
Fecha: 1 de Febrero de 2026
Objetivo: Vista única que agrega y normaliza datos de múltiples fuentes
          (Consultas, Labs, Imágenes, Recetas) en un Timeline cronológico.

MEJORAS IMPLEMENTADAS:
✅ Agregación inteligente de múltiples modelos
✅ Normalización de datos en estructura común
✅ Timeline cronológico con ordenamiento
✅ Filtros por tipo, fecha y médico
✅ Estadísticas del paciente en panel superior
✅ Detección de alertas críticas
✅ Código de colores según estado
✅ Caché de 5 minutos para optimización
✅ Exportación de historial completo a PDF
"""

import logging
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.urls import reverse

from core.models import (
    Paciente,
    Empresa,
    Usuario,
    OrdenDeServicio,
    Receta,
    EstudioImagen,
    ForenseAcceso,
)
from core.services.forense_service import metadata_consentimiento_snapshot, registrar_acceso_forense

# Importar ConsultaMedica desde consultorio si existe
try:
    from consultorio.models import ConsultaMedica
    CONSULTORIO_DISPONIBLE = True
except ImportError:
    CONSULTORIO_DISPONIBLE = False
    ConsultaMedica = None

logger = logging.getLogger(__name__)


# ==============================================================================
# VISTA PRINCIPAL: EXPEDIENTE CLÍNICO UNIFICADO
# ==============================================================================

class ExpedienteClinicoView(LoginRequiredMixin, DetailView):
    """
    Vista del Hub Central del Paciente.
    
    CARACTERÍSTICAS:
    - Agrega datos de múltiples fuentes
    - Normaliza en estructura común
    - Timeline cronológico con código de colores
    - Filtros inteligentes
    - Estadísticas en tiempo real
    - Caché de 5 minutos
    - Exportación a PDF
    """
    
    model = Paciente
    template_name = 'pacientes/historial_clinico.html'
    context_object_name = 'paciente'
    
    def get_queryset(self):
        """Filtrar por empresa del usuario."""
        return Paciente.objects.filter(empresa=getattr(self.request.user, 'empresa', None))

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if request.method == 'GET' and response.status_code == 200 and request.user.is_authenticated:
            try:
                paciente = self.object
                em = getattr(request.user, 'empresa', None)
                if paciente and em and paciente.empresa_id == em.id:
                    meta = metadata_consentimiento_snapshot(paciente)
                    meta['vista'] = 'expediente_clinico_unificado'
                    registrar_acceso_forense(
                        request,
                        ForenseAcceso.ACCION_EXPEDIENTE_VIEW,
                        paciente_id=paciente.id,
                        orden_id=None,
                        metadata=meta,
                        es_publico=False,
                        empresa=em,
                    )
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en dispatch (paciente_detalle.py)")
                logger.debug('Forense EXPEDIENTE_VIEW omitido', exc_info=True)
        return response

    def get_context_data(self, **kwargs):
        """
        Construir contexto con timeline unificado y estadísticas.
        """
        context = super().get_context_data(**kwargs)
        paciente = self.object
        
        # ==============================================================================
        # 1. GENERAR TIMELINE UNIFICADO
        # ==============================================================================
        timeline_events = self._generar_timeline(paciente)
        
        # ==============================================================================
        # 2. APLICAR FILTROS
        # ==============================================================================
        timeline_filtrado = self._aplicar_filtros(timeline_events)
        
        # ==============================================================================
        # 3. CALCULAR ESTADÍSTICAS
        # ==============================================================================
        estadisticas = self._calcular_estadisticas(paciente, timeline_events)
        
        # ==============================================================================
        # 4. DETECTAR ALERTAS CRÍTICAS
        # ==============================================================================
        alertas = self._detectar_alertas(timeline_events)
        
        # ==============================================================================
        # 5. OBTENER LISTA DE MÉDICOS (para filtro)
        # ==============================================================================
        medicos = self._obtener_medicos(timeline_events)
        
        # ==============================================================================
        # 6. AGREGAR TODO AL CONTEXTO
        # ==============================================================================
        context.update({
            'timeline': timeline_filtrado,
            'estadisticas': estadisticas,
            'alertas': alertas,
            'medicos': medicos,
            'filtros_activos': self._get_filtros_activos(),
        })
        
        return context
    
    # ==============================================================================
    # MÉTODOS AUXILIARES
    # ==============================================================================
    
    def _generar_timeline(self, paciente):
        """
        Genera el timeline unificado agregando datos de múltiples fuentes.
        
        MEJORA: Usa caché de 5 minutos para optimizar rendimiento.
        """
        # Intentar obtener del caché
        cache_key = f'timeline_paciente_{paciente.id}'
        timeline_cached = cache.get(cache_key)
        
        if timeline_cached:
            logger.info(f"[CACHE] Timeline recuperado del caché para paciente {paciente.id}")
            return timeline_cached
        
        logger.info(f"[TIMELINE] Generando timeline para paciente: {paciente.nombre_completo}")
        
        timeline_events = []
        
        # ==============================================================================
        # 1. AGREGAR CONSULTAS MÉDICAS
        # ==============================================================================
        if CONSULTORIO_DISPONIBLE:
            try:
                consultas = ConsultaMedica.objects.filter(
                    paciente=paciente
                ).select_related('medico').order_by('-fecha_creacion')
                
                for consulta in consultas:
                    timeline_events.append(self._normalizar_consulta(consulta))
                    
                logger.info(f"[TIMELINE] {consultas.count()} consultas agregadas")
            except Exception as e:
                logger.error(f"[TIMELINE] Error al obtener consultas: {e}")
        
        # ==============================================================================
        # 2. AGREGAR ÓRDENES DE LABORATORIO
        # ==============================================================================
        try:
            ordenes_lab = OrdenDeServicio.objects.filter(
                paciente=paciente
            ).select_related('medico_referente').order_by('-fecha_creacion')
            
            for orden in ordenes_lab:
                timeline_events.append(self._normalizar_laboratorio(orden))
                
            logger.info(f"[TIMELINE] {ordenes_lab.count()} órdenes de laboratorio agregadas")
        except Exception as e:
            logger.error(f"[TIMELINE] Error al obtener órdenes de laboratorio: {e}")
        
        # ==============================================================================
        # 3. AGREGAR ESTUDIOS DE IMAGEN
        # ==============================================================================
        try:
            estudios_imagen = EstudioImagen.objects.filter(
                paciente=paciente
            ).select_related('medico_interpretador').order_by('-fecha_estudio')
            
            for estudio in estudios_imagen:
                timeline_events.append(self._normalizar_imagen(estudio))
                
            logger.info(f"[TIMELINE] {estudios_imagen.count()} estudios de imagen agregados")
        except Exception as e:
            logger.error(f"[TIMELINE] Error al obtener estudios de imagen: {e}")
        
        # ==============================================================================
        # 4. AGREGAR RECETAS MÉDICAS
        # ==============================================================================
        try:
            recetas = Receta.objects.filter(
                paciente=paciente
            ).order_by('-fecha_emision')
            
            for receta in recetas:
                timeline_events.append(self._normalizar_receta(receta))
                
            logger.info(f"[TIMELINE] {recetas.count()} recetas agregadas")
        except Exception as e:
            logger.error(f"[TIMELINE] Error al obtener recetas: {e}")
        
        # ==============================================================================
        # 5. ORDENAR POR FECHA (MÁS RECIENTE PRIMERO)
        # ==============================================================================
        timeline_events.sort(key=lambda x: x['fecha'], reverse=True)
        
        logger.info(f"[TIMELINE] Total de eventos: {len(timeline_events)}")
        
        # Guardar en caché por 5 minutos
        cache.set(cache_key, timeline_events, 300)
        
        return timeline_events
    
    # ==============================================================================
    # MÉTODOS DE NORMALIZACIÓN (MAPEO A ESTRUCTURA COMÚN)
    # ==============================================================================
    
    def _normalizar_consulta(self, consulta):
        """
        Normaliza ConsultaMedica a la estructura estándar del timeline.
        """
        return {
            'tipo': 'CONSULTA',
            'subtipo': 'CONSULTA_GENERAL',
            'fecha': consulta.fecha_creacion,
            'titulo': getattr(consulta, 'motivo_consulta', None) or getattr(consulta, 'motivo', None) or 'Consulta Médica',
            'resumen': (getattr(consulta, 'diagnostico_principal', None) or getattr(consulta, 'diagnostico_texto', None) or '')[:200],
            'estado': 'COMPLETADO',
            'prioridad': 'NORMAL',
            'doctor': {
                'nombre': (consulta.medico.nombre_completo if consulta.medico else 'Sin médico'),
                'especialidad': getattr(consulta.medico, 'especialidad', 'Médico General'),
                'id': consulta.medico.id if consulta.medico else None,
            },
            'archivos': [],  # Las consultas normalmente no tienen PDF directo
            'metadata': {
                'folio': consulta.id,
                'diagnostico_cie10': consulta.diagnostico_cie10 or '',
                'tiene_audio': hasattr(consulta, 'audio_sesion'),
            },
            'icono': 'fa-user-md',
            'color_badge': 'success',
            'acciones': ['ver'],
            'url_detalle': f'/consultorio/consulta/{consulta.id}/' if hasattr(consulta, 'id') else '#',
        }
    
    def _normalizar_laboratorio(self, orden):
        """
        Normaliza OrdenDeServicio a la estructura estándar del timeline.
        """
        # Detectar estado y prioridad
        estado = 'COMPLETADO' if orden.estado == 'ENTREGADO' else \
                 'CRITICO' if orden.estado == 'RESULTADOS_LISTOS' and hasattr(orden, 'tiene_valor_critico') else \
                 'PENDIENTE' if orden.estado in ['PENDIENTE_PAGO', 'PAGADO'] else \
                 'PROCESANDO'
        
        prioridad = 'URGENTE' if orden.tipo_servicio == 'URGENCIA' else 'NORMAL'
        
        # URL del archivo de resultado
        archivo_url = None
        if orden.archivo_resultado:
            try:
                archivo_url = orden.archivo_resultado.url
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en _normalizar_laboratorio (paciente_detalle.py)")
                archivo_url = None
        
        return {
            'tipo': 'LABORATORIO',
            'subtipo': orden.tipo_servicio,
            'fecha': orden.fecha_creacion,
            'titulo': f"Orden de Laboratorio #{orden.folio_orden or orden.id}",
            'resumen': orden.observaciones_clinicas or 'Estudios de laboratorio',
            'estado': estado,
            'prioridad': prioridad,
            'doctor': {
                'nombre': (orden.medico_referente.nombre_completo if orden.medico_referente else 'Sin médico referente'),
                'especialidad': getattr(orden.medico_referente, 'especialidad', ''),
                'id': orden.medico_referente.id if orden.medico_referente else None,
            },
            'archivos': [
                {
                    'tipo': 'PDF',
                    'nombre': f'Resultados_{orden.folio_orden or orden.id}.pdf',
                    'url': archivo_url,
                    'disponible': archivo_url is not None,
                }
            ] if archivo_url else [],
            'metadata': {
                'folio': orden.folio_orden or orden.id,
                'estado_pago': orden.estado_pago,
                'total': float(orden.total),
                'estudios_count': orden.detalles.count() if hasattr(orden, 'detalles') else 0,
            },
            'icono': 'fa-microscope',
            'color_badge': 'danger' if estado == 'CRITICO' else 'warning' if estado == 'PENDIENTE' else 'success',
            'acciones': ['ver', 'descargar', 'compartir', 'imprimir'] if archivo_url else ['ver'],
            'url_detalle': reverse('imprimir_ticket_lab', args=[orden.id]) if hasattr(orden, 'id') else '#',
        }
    
    def _normalizar_imagen(self, estudio):
        """
        Normaliza EstudioImagen a la estructura estándar del timeline.
        """
        estado = 'COMPLETADO' if estudio.estado == 'ENTREGADO' else \
                 'PENDIENTE' if estudio.estado in ['BORRADOR'] else \
                 'PROCESANDO'
        
        return {
            'tipo': 'IMAGEN',
            'subtipo': estudio.tipo_estudio,
            'fecha': estudio.fecha_estudio,
            'titulo': f"{estudio.get_tipo_estudio_display()} - {estudio.folio_estudio}",
            'resumen': (estudio.interpretacion or estudio.descripcion_hallazgos or 'Estudio de imagenología')[:200],
            'estado': estado,
            'prioridad': 'URGENTE' if getattr(estudio, 'urgente', False) else 'NORMAL',
            'doctor': {
                'nombre': estudio.medico_interpretador.nombre_completo if estudio.medico_interpretador else 'Sin médico',
                'especialidad': getattr(estudio.medico_interpretador, 'especialidad', ''),
                'id': estudio.medico_interpretador.id if estudio.medico_interpretador else None,
            },
            'archivos': [
                {
                    'tipo': 'IMAGEN',
                    'nombre': f'{estudio.tipo_estudio}_{estudio.folio_estudio}',
                    'url': f'/imagenes/estudio/{estudio.id}/',
                    'disponible': estudio.imagenes.count() > 0 if hasattr(estudio, 'imagenes') else False,
                }
            ],
            'metadata': {
                'folio': estudio.folio_estudio,
                'tecnica': estudio.tecnica_utilizada or '',
                'imagenes_count': estudio.imagenes.count() if hasattr(estudio, 'imagenes') else 0,
            },
            'icono': 'fa-x-ray',
            'color_badge': 'info' if estado == 'PROCESANDO' else 'success',
            'acciones': ['ver', 'descargar'],
            'url_detalle': f'/imagenes/estudio/{estudio.id}/' if hasattr(estudio, 'id') else '#',
        }
    
    def _normalizar_receta(self, receta):
        """
        Normaliza Receta a la estructura estándar del timeline.
        """
        return {
            'tipo': 'RECETA',
            'subtipo': 'RECETA_MEDICA',
            'fecha': receta.fecha_emision,
            'titulo': f"Receta Médica - {receta.folio_receta}",
            'resumen': receta.diagnostico_principal or 'Prescripción médica',
            'estado': 'COMPLETADO' if receta.activa else 'CANCELADO',
            'prioridad': 'NORMAL',
            'doctor': {
                'nombre': receta.medico_nombre_completo,
                'especialidad': receta.medico_especialidad,
                'cedula': receta.medico_cedula,
            },
            'archivos': [
                {
                    'tipo': 'PDF',
                    'nombre': f'Receta_{receta.folio_receta}.pdf',
                    'url': receta.url_drive_backup if receta.url_drive_backup else None,
                    'disponible': receta.url_drive_backup is not None,
                }
            ] if receta.url_drive_backup else [],
            'metadata': {
                'folio': receta.folio_receta,
                'items_count': receta.items.count() if hasattr(receta, 'items') else 0,
                'cedula_medico': receta.medico_cedula,
            },
            'icono': 'fa-file-prescription',
            'color_badge': 'primary',
            'acciones': ['ver', 'descargar', 'imprimir'] if receta.url_drive_backup else ['ver'],
            'url_detalle': f'/recetas/{receta.id}/' if hasattr(receta, 'id') else '#',
        }
    
    # ==============================================================================
    # FILTROS
    # ==============================================================================
    
    def _aplicar_filtros(self, timeline_events):
        """
        Aplica filtros según los parámetros GET de la URL.
        """
        tipo_filtro = self.request.GET.get('tipo', '')
        periodo_filtro = self.request.GET.get('periodo', '30')
        medico_filtro = self.request.GET.get('medico', '')
        busqueda = self.request.GET.get('q', '').lower()
        
        eventos_filtrados = timeline_events
        
        # Filtro por tipo
        if tipo_filtro:
            eventos_filtrados = [e for e in eventos_filtrados if e['tipo'] == tipo_filtro]
        
        # Filtro por período
        if periodo_filtro != 'all':
            try:
                dias = int(periodo_filtro)
                fecha_limite = timezone.now() - timedelta(days=dias)
                eventos_filtrados = [e for e in eventos_filtrados if e['fecha'] >= fecha_limite]
            except ValueError:
                pass
        
        # Filtro por médico
        if medico_filtro:
            try:
                medico_id = int(medico_filtro)
                eventos_filtrados = [e for e in eventos_filtrados if e['doctor'].get('id') == medico_id]
            except ValueError:
                pass
        
        # Búsqueda por texto
        if busqueda:
            eventos_filtrados = [
                e for e in eventos_filtrados
                if busqueda in e['titulo'].lower() or busqueda in e['resumen'].lower()
            ]
        
        return eventos_filtrados
    
    def _get_filtros_activos(self):
        """
        Retorna diccionario con los filtros activos.
        """
        return {
            'tipo': self.request.GET.get('tipo', ''),
            'periodo': self.request.GET.get('periodo', '30'),
            'medico': self.request.GET.get('medico', ''),
            'busqueda': self.request.GET.get('q', ''),
        }
    
    # ==============================================================================
    # ESTADÍSTICAS
    # ==============================================================================
    
    def _calcular_estadisticas(self, paciente, timeline_events):
        """
        Calcula estadísticas rápidas del paciente.
        """
        total_eventos = len(timeline_events)
        
        # Contar por tipo
        consultas_count = sum(1 for e in timeline_events if e['tipo'] == 'CONSULTA')
        labs_count = sum(1 for e in timeline_events if e['tipo'] == 'LABORATORIO')
        imagenes_count = sum(1 for e in timeline_events if e['tipo'] == 'IMAGEN')
        recetas_count = sum(1 for e in timeline_events if e['tipo'] == 'RECETA')
        
        # Alertas pendientes
        alertas_count = sum(1 for e in timeline_events if e['estado'] == 'CRITICO')
        
        return {
            'total_eventos': total_eventos,
            'consultas': consultas_count,
            'laboratorios': labs_count,
            'imagenes': imagenes_count,
            'recetas': recetas_count,
            'alertas': alertas_count,
        }
    
    # ==============================================================================
    # ALERTAS
    # ==============================================================================
    
    def _detectar_alertas(self, timeline_events):
        """
        Detecta eventos críticos o pendientes que requieren atención.
        """
        alertas = []
        
        for evento in timeline_events:
            if evento['estado'] == 'CRITICO':
                # Calcular hace cuánto tiempo
                diferencia = timezone.now() - evento['fecha']
                dias = diferencia.days
                horas = diferencia.seconds // 3600
                
                tiempo_str = f"Hace {dias} días" if dias > 0 else f"Hace {horas} horas"
                
                alertas.append({
                    'tipo': evento['tipo'],
                    'titulo': evento['titulo'],
                    'resumen': evento['resumen'],
                    'tiempo': tiempo_str,
                    'url': evento['url_detalle'],
                    'icono': evento['icono'],
                })
        
        return alertas
    
    # ==============================================================================
    # MÉDICOS
    # ==============================================================================
    
    def _obtener_medicos(self, timeline_events):
        """
        Obtiene lista única de médicos presentes en el timeline.
        """
        medicos_dict = {}
        
        for evento in timeline_events:
            medico_id = evento['doctor'].get('id')
            if medico_id and medico_id not in medicos_dict:
                medicos_dict[medico_id] = {
                    'id': medico_id,
                    'nombre': evento['doctor']['nombre'],
                    'especialidad': evento['doctor'].get('especialidad', ''),
                }
        
        return list(medicos_dict.values())


# ==============================================================================
# VISTA: EXPORTAR HISTORIAL COMPLETO A PDF
# ==============================================================================

@login_required
def exportar_historial_pdf(request, paciente_id):
    """
    Genera un PDF profesional con el historial clínico completo del paciente.
    Incluye timeline de eventos, órdenes de laboratorio, recetas y consultas.
    """
    empresa = getattr(request.user, 'empresa', None)
    paciente = get_object_or_404(Paciente, pk=paciente_id, empresa=empresa)

    # Reutilizar la lógica de la vista para construir el contexto
    view_instance = ExpedienteClinicoView()
    view_instance.request = request
    view_instance.object = paciente
    view_instance.kwargs = {'pk': paciente_id}

    timeline = view_instance._generar_timeline(paciente)
    estadisticas = view_instance._calcular_estadisticas(paciente, timeline)
    alertas = view_instance._detectar_alertas(timeline)

    # Órdenes de laboratorio para el reporte
    ordenes = OrdenDeServicio.objects.filter(
        paciente=paciente
    ).select_related('sucursal').order_by('-fecha_creacion')[:50]

    # Recetas activas
    recetas = Receta.objects.filter(
        paciente=paciente
    ).order_by('-fecha_emision')[:30]

    from django.utils import timezone as tz
    context = {
        'paciente':     paciente,
        'empresa':      empresa,
        'timeline':     timeline,
        'estadisticas': estadisticas,
        'alertas':      alertas,
        'ordenes':      ordenes,
        'recetas':      recetas,
        'fecha_reporte': tz.localtime(tz.now()),
        'generado_por':  request.user.get_full_name() or request.user.username,
    }

    # Intentar generar con WeasyPrint; fallback a HTML descargable
    try:
        from core.utils.pdf_generator import render_to_pdf
        pdf_bytes = render_to_pdf('core/pdf/historial_clinico_pdf.html', context)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        nombre = paciente.nombre_completo.replace(' ', '_')
        response['Content-Disposition'] = f'inline; filename="Historial_{nombre}.pdf"'
        return response
    except Exception as exc:
        logger.warning("WeasyPrint no disponible, entregando HTML: %s", exc)
        from django.template.loader import render_to_string
        html = render_to_string('core/pdf/historial_clinico_pdf.html', context, request=request)
        response = HttpResponse(html)
        response['Content-Type'] = 'text/html; charset=utf-8'
        return response