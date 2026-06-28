"""
Módulo de Biblioteca RAG — PRIS-IA Fuente de Verdad
====================================================
Flujo:
  1. Director QC sube PDF → estado_rag = SUBIDO
  2. Endpoint /procesar/ → extrae texto, genera embeddings → ENTRENADO
  3. Worklist llama /consultar-worklist/ → RAG busca en Chroma/SQLite → cita el manual
  4. Reporte final lleva firma Q.B. Giselle Margarita (Responsable Sanitaria)
"""
import json
import logging
import os
import threading
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import (
    CapsulaSabiduria,
    DocumentoCapacitacion,
    Empresa,
)

logger = logging.getLogger('core.rag')


# ─── Helpers de acceso ────────────────────────────────────────────────────────

def _es_director_qc(user) -> bool:
    """Solo Director, Admin o Superusuario pueden gestionar documentos."""
    return (
        user.is_superuser
        or user.is_staff
        or getattr(user, 'rol', '').upper() in ('DIRECTOR', 'ADMIN', 'ADMINISTRADOR', 'QUIMICO')
    )


def _resolver_documento_capacitacion(empresa, identificador):
    qs = DocumentoCapacitacion.objects.filter(empresa=empresa)
    try:
        token = uuid.UUID(str(identificador))
        return get_object_or_404(qs, token_acceso=token)
    except (ValueError, TypeError, AttributeError):
        return get_object_or_404(qs, pk=identificador)


def _procesar_pdf_background(documento_id: int, empresa_id: int) -> None:
    """Ingesta el PDF en hilo secundario para no bloquear la respuesta HTTP."""
    try:
        from core.models import DocumentoCapacitacion as Doc
        doc = Doc.objects.get(pk=documento_id)
        doc.estado_rag = Doc.ESTADO_PROCESANDO
        doc.error_rag = ''
        doc.save(update_fields=['estado_rag', 'error_rag'])

        from core.utils.rag_engine import ingerir_documento_pdf
        chunks = ingerir_documento_pdf(
            documento_id=documento_id,
            empresa_id=empresa_id,
            titulo=doc.titulo,
            categoria=doc.modulo_relacionado or 'GENERAL',
            pdf_path=doc.archivo.path,
        )
        doc.chunks_rag = chunks
        doc.estado_rag = Doc.ESTADO_ENTRENADO
        doc.save(update_fields=['chunks_rag', 'estado_rag'])
        logger.info('RAG: documento %d indexado — %d chunks', documento_id, chunks)
    except Exception as exc:
        logger.exception('RAG: error procesando documento %d: %s', documento_id, exc)
        try:
            from core.models import DocumentoCapacitacion as Doc
            Doc.objects.filter(pk=documento_id).update(
                estado_rag=Doc.ESTADO_ERROR,
                error_rag=str(exc)[:500],
            )
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en _procesar_pdf_background (capacitacion_rag.py)")
            pass


# ─── Vista principal: Biblioteca RAG ─────────────────────────────────────────

@login_required
def dashboard_capacitacion(request):
    """Dashboard de la Biblioteca de Entrenamiento RAG."""
    empresa = getattr(request.user, 'empresa', None)

    documentos = DocumentoCapacitacion.objects.filter(
        empresa=empresa,
        activo=True,
    ).select_related('subido_por').order_by('-fecha_creacion')

    capsulas = CapsulaSabiduria.objects.filter(
        empresa=empresa,
        activo=True,
    ).order_by('-fecha_creacion')[:10]

    # Estadísticas semáforo
    total  = documentos.count()
    entrenados  = documentos.filter(estado_rag=DocumentoCapacitacion.ESTADO_ENTRENADO).count()
    procesando  = documentos.filter(estado_rag=DocumentoCapacitacion.ESTADO_PROCESANDO).count()
    subidos     = documentos.filter(estado_rag=DocumentoCapacitacion.ESTADO_SUBIDO).count()
    con_error   = documentos.filter(estado_rag=DocumentoCapacitacion.ESTADO_ERROR).count()
    total_chunks = sum(d.chunks_rag for d in documentos)

    modulo_actual = request.GET.get('modulo', None)
    tip_dia = None
    if modulo_actual:
        tip_dia = CapsulaSabiduria.objects.filter(
            empresa=empresa,
            activo=True,
            documento_fuente__modulo_relacionado=modulo_actual,
        ).order_by('?').first()

    return render(request, 'core/capacitacion/dashboard.html', {
        'empresa': empresa,
        'documentos': documentos,
        'capsulas': capsulas,
        'tip_dia': tip_dia,
        'modulo_actual': modulo_actual,
        'stats': {
            'total': total,
            'entrenados': entrenados,
            'procesando': procesando,
            'subidos': subidos,
            'con_error': con_error,
            'total_chunks': total_chunks,
        },
        'MODULO_CHOICES': DocumentoCapacitacion.MODULO_CHOICES,
        'TIPO_CHOICES': DocumentoCapacitacion.TIPO_CHOICES,
        'es_director': _es_director_qc(request.user),
    })


# ─── Subir documento ─────────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def subir_documento_capacitacion(request):
    """Sube un PDF/DOCX a la Biblioteca y dispara ingesta RAG en background."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa asignada'}, status=403)

    if not _es_director_qc(request.user):
        return JsonResponse({'status': 'error', 'mensaje': 'Solo el Director QC puede gestionar la Biblioteca'}, status=403)

    titulo            = request.POST.get('titulo', '').strip()
    tipo              = request.POST.get('tipo_documento', request.POST.get('tipo', DocumentoCapacitacion.TIPO_MANUAL))
    modulo_relacionado = request.POST.get('modulo_relacionado', DocumentoCapacitacion.MODULO_GENERAL)
    descripcion       = request.POST.get('descripcion', '').strip()
    version           = request.POST.get('version', '1.0').strip()
    validado_por_nombre = request.POST.get('validado_por_nombre', 'Q.B. Giselle Margarita López Gutiérrez').strip()
    cedula_validador  = request.POST.get('cedula_validador', '').strip()
    archivo           = request.FILES.get('archivo')

    if not titulo:
        return JsonResponse({'status': 'error', 'mensaje': 'El título es obligatorio'}, status=400)
    if not archivo:
        return JsonResponse({'status': 'error', 'mensaje': 'Debe adjuntar un archivo'}, status=400)

    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in ('.pdf', '.docx', '.doc', '.txt'):
        return JsonResponse({'status': 'error', 'mensaje': 'Solo se permiten PDF, DOCX o TXT'}, status=400)

    # Validar tamaño (max 100 MB)
    if archivo.size > 100 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'mensaje': 'El archivo no puede superar 100 MB'}, status=400)

    documento = DocumentoCapacitacion.objects.create(
        empresa=empresa,
        titulo=titulo,
        tipo=tipo,
        modulo_relacionado=modulo_relacionado,
        descripcion=descripcion,
        version=version,
        validado_por_nombre=validado_por_nombre or 'Q.B. Giselle Margarita López Gutiérrez',
        cedula_validador=cedula_validador,
        archivo=archivo,
        estado_rag=DocumentoCapacitacion.ESTADO_SUBIDO,
        subido_por=request.user,
    )

    # Disparar ingesta en segundo plano si es PDF
    if ext == '.pdf':
        t = threading.Thread(
            target=_procesar_pdf_background,
            args=(documento.id, empresa.id),
            daemon=True,
        )
        t.start()
        mensaje = f'"{titulo}" subido. Indexación en proceso…'
    else:
        mensaje = f'"{titulo}" subido. Los archivos no-PDF no se indexan automáticamente.'

    return JsonResponse({
        'status': 'success',
        'mensaje': mensaje,
        'documento_id': documento.id,
        'documento_token': str(documento.token_acceso),
        'estado_rag': documento.estado_rag,
        'semaforo': documento.semaforo_emoji,
    })


# ─── Reprocesar un documento (forzado) ───────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def reprocesar_documento(request, documento_id):
    """Re-indexa un documento que falló o que el Director quiere actualizar."""
    empresa = getattr(request.user, 'empresa', None)
    if not _es_director_qc(request.user):
        return JsonResponse({'status': 'error', 'mensaje': 'Sin permisos'}, status=403)

    doc = _resolver_documento_capacitacion(empresa, documento_id)
    ext = os.path.splitext(doc.archivo.name)[1].lower()
    if ext != '.pdf':
        return JsonResponse({'status': 'error', 'mensaje': 'Solo se reindexan PDFs'}, status=400)

    doc.estado_rag = DocumentoCapacitacion.ESTADO_PROCESANDO
    doc.error_rag = ''
    doc.save(update_fields=['estado_rag', 'error_rag'])

    t = threading.Thread(
        target=_procesar_pdf_background,
        args=(doc.id, empresa.id),
        daemon=True,
    )
    t.start()
    return JsonResponse({'status': 'success', 'mensaje': 'Re-indexación iniciada'})


# ─── Estado en tiempo real (polling) ─────────────────────────────────────────

@login_required
def estado_documento_rag(request, documento_id):
    """Retorna el estado RAG de un documento (para polling del frontend)."""
    empresa = getattr(request.user, 'empresa', None)
    doc = _resolver_documento_capacitacion(empresa, documento_id)
    return JsonResponse({
        'estado_rag': doc.estado_rag,
        'chunks_rag': doc.chunks_rag,
        'semaforo': doc.semaforo_emoji,
        'semaforo_class': doc.semaforo_class,
        'error': doc.error_rag or '',
    })


# ─── Eliminar documento ───────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def eliminar_documento(request, documento_id):
    """Desactiva (soft-delete) un documento de la Biblioteca."""
    empresa = getattr(request.user, 'empresa', None)
    if not _es_director_qc(request.user):
        return JsonResponse({'status': 'error', 'mensaje': 'Sin permisos'}, status=403)
    doc = _resolver_documento_capacitacion(empresa, documento_id)
    doc.activo = False
    doc.save(update_fields=['activo'])
    return JsonResponse({'status': 'success', 'mensaje': f'"{doc.titulo}" eliminado de la Biblioteca'})


# ─── Consulta RAG general (chat capacitación) ─────────────────────────────────

@login_required
@require_http_methods(['POST'])
def consultar_pris_rag(request):
    """
    Consulta a PRIS con RAG real:
    1. Vectoriza la pregunta con Google text-embedding-004
    2. Busca top-3 chunks más similares en Chroma/SQLite
    3. Llama a Gemini con el contexto encontrado (RAG puro)
    4. Si RAG falla → fallback a keyword matching en contenido_texto
    """
    empresa = getattr(request.user, 'empresa', None)
    data = {}
    try:
        data = json.loads(request.body)
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en consultar_pris_rag (capacitacion_rag.py)")
        data = request.POST.dict()

    consulta = (data.get('consulta') or data.get('query') or '').strip()
    modulo_contexto = data.get('modulo_contexto') or data.get('modulo', 'GENERAL')

    if not consulta:
        return JsonResponse({'status': 'error', 'mensaje': 'Consulta vacía'}, status=400)

    empresa_id = empresa.id if empresa else 0

    # ── Intento 1: RAG vectorial real ──────────────────────────────────────────
    try:
        from core.utils.rag_engine import consultar_cerebro
        resultado = consultar_cerebro(
            pregunta=consulta,
            empresa_id=empresa_id,
            categoria=modulo_contexto or 'GENERAL',
        )
        if resultado.get('respuesta') and 'No encontré contexto' not in resultado['respuesta']:
            return JsonResponse({
                'status': 'success',
                'respuesta': resultado['respuesta'],
                'fuentes': resultado.get('fuentes', []),
                'contexto': resultado.get('contexto', []),
                'motor': 'RAG-Vectorial',
            })
    except Exception as exc:
        logger.warning('RAG vectorial falló, usando fallback: %s', exc)

    # ── Fallback: keyword matching sobre contenido_texto ──────────────────────
    from django.db.models import Q
    docs_qs = DocumentoCapacitacion.objects.filter(
        empresa=empresa,
        activo=True,
        estado_rag=DocumentoCapacitacion.ESTADO_ENTRENADO,
    )
    if modulo_contexto and modulo_contexto != 'GENERAL':
        docs_qs = docs_qs.filter(
            Q(modulo_relacionado=modulo_contexto) | Q(modulo_relacionado='GENERAL')
        )

    palabras = consulta.lower().split()
    encontrados = []
    for doc in docs_qs:
        if doc.contenido_texto:
            hits = sum(1 for p in palabras if p in doc.contenido_texto.lower())
            if hits:
                encontrados.append({'doc': doc, 'hits': hits})
    encontrados.sort(key=lambda x: x['hits'], reverse=True)

    if encontrados:
        fuentes = [f"Fuente: {e['doc'].titulo}" for e in encontrados[:3]]
        fragmentos = '\n\n'.join(
            e['doc'].contenido_texto[:600] for e in encontrados[:3]
        )
        respuesta = (
            f"**Basado en los manuales de la Biblioteca:**\n\n{fragmentos}\n\n"
            f"📚 *{', '.join(fuentes)}*"
        )
        return JsonResponse({
            'status': 'success',
            'respuesta': respuesta,
            'fuentes': fuentes,
            'motor': 'Keyword-Fallback',
        })

    return JsonResponse({
        'status': 'success',
        'respuesta': (
            'No encontré información en la Biblioteca interna para esa consulta. '
            'Considera subir el manual correspondiente (ej. Manual de Bethesda).'
        ),
        'fuentes': [],
        'motor': 'Sin-Contexto',
    })


# ─── Consulta RAG específica para Worklist ─────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def consultar_pris_worklist(request):
    """
    Endpoint especializado para la Worklist Analítica.
    Recibe: estudio, parametros, valores, empresa_id
    Devuelve: interpretación clínica RAG citando manuales (Bethesda, CLSI, etc.)
    """
    empresa = getattr(request.user, 'empresa', None)
    try:
        data = json.loads(request.body)
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en consultar_pris_worklist (capacitacion_rag.py)")
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)

    estudio     = data.get('estudio', 'Estudio no especificado')
    parametros  = data.get('parametros', [])   # [{nombre, valor, unidad, ref_min, ref_max}, ...]
    contexto    = data.get('contexto', '')

    # Construir pregunta clínica con los valores capturados
    lineas_valores = '\n'.join(
        f"  • {p.get('nombre', '?')}: {p.get('valor', '?')} {p.get('unidad', '')} "
        f"(Ref: {p.get('ref_min', '?')}–{p.get('ref_max', '?')})"
        for p in parametros if p.get('valor')
    ) or '  (Sin valores ingresados aún)'

    pregunta = (
        f"Interpretación clínica del estudio: {estudio}\n"
        f"Valores capturados:\n{lineas_valores}\n"
        f"{('Contexto adicional: ' + contexto) if contexto else ''}\n"
        "¿Cuáles son los hallazgos relevantes y qué recomienda la literatura?"
    )

    empresa_id = empresa.id if empresa else 0

    try:
        from core.utils.rag_engine import consultar_cerebro
        resultado = consultar_cerebro(
            pregunta=pregunta,
            empresa_id=empresa_id,
            categoria='LABORATORIO',
        )
        respuesta = resultado.get('respuesta', '')
        fuentes   = resultado.get('fuentes', [])

        # Agregar firma legal si hay respuesta
        if respuesta and fuentes:
            responsable = DocumentoCapacitacion.objects.filter(
                empresa=empresa, activo=True, estado_rag='ENTRENADO'
            ).values_list('validado_por_nombre', flat=True).first()
            if responsable:
                respuesta += (
                    f"\n\n---\n*Interpretación basada en la Biblioteca interna de PRISLAB. "
                    f"Validación clínica: {responsable}.*"
                )

        return JsonResponse({
            'status': 'success',
            'respuesta': respuesta,
            'fuentes': fuentes,
            'motor': 'RAG-Worklist',
        })
    except Exception as exc:
        logger.warning('consultar_pris_worklist falló: %s', exc)
        return JsonResponse({
            'status': 'success',
            'respuesta': (
                'El motor RAG no pudo consultar los manuales en este momento. '
                'Revisa los resultados según tus rangos de referencia habituales.'
            ),
            'fuentes': [],
            'motor': 'Error-Fallback',
        })


# ─── Tip del día ──────────────────────────────────────────────────────────────

@login_required
def obtener_tip_dia(request):
    """Obtiene el tip del día según el módulo actual."""
    empresa = getattr(request.user, 'empresa', None)
    modulo = request.GET.get('modulo', None)

    qs = CapsulaSabiduria.objects.filter(empresa=empresa, activo=True)
    if modulo:
        qs = qs.filter(documento_fuente__modulo_relacionado=modulo)

    tip = qs.order_by('?').first()
    if tip:
        return JsonResponse({
            'status': 'success',
            'titulo': tip.titulo,
            'contenido': tip.contenido,
            'tipo': tip.get_tipo_contenido_display() if hasattr(tip, 'get_tipo_contenido_display') else 'Cápsula',
            'url_video': None,
        })
    return JsonResponse({'status': 'success', 'mensaje': 'No hay tips disponibles'})