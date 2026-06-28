"""
API endpoints para consulta directa, paciente+consulta, búsqueda de pacientes,
transcripción IA, receta inmediata, certificado inmediato, orden de laboratorio,
archivos adjuntos, vademécum, signos vitales tendencia, plantillas especialidad.
"""
import json
import logging
import uuid as uuid_lib
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.urls import reverse, NoReverseMatch
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from core.models import (
    Paciente, Medico, CitaMedica, ConsultaMedica,
    SignosVitales, Receta, RecetaItem, Producto,
    CertificadoMedico, OrdenDeServicio, DetalleOrden,
)
from core.lims_cart import resolve_lims_cart_ids, aplicar_precio_convenio
from core.services.audit_service import registrar_auditoria
from core.utils.empresa_request import empresa_efectiva_request

from ._helpers import (
    _empresa_explicita_usuario, _resolver_medico_usuario,
    _int_or_none, _dec_or_none,
)

logger = logging.getLogger('consultorio')


# ==============================================================================
# API: CREAR CONSULTA DIRECTA (paciente existente)
# ==============================================================================

@login_required
@require_http_methods(["POST"])
def api_crear_consulta_directa(request):
    """
    API para crear consulta con paciente existente.
    Redirige directamente a la consulta SOAP.
    """
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'mensaje': 'JSON inválido'}, status=400)

        paciente_id = data.get('paciente_id')
        motivo = data.get('motivo', 'Consulta general')

        empresa = _empresa_explicita_usuario(request)
        if not empresa:
            return JsonResponse({'ok': False, 'mensaje': 'Usuario sin empresa asignada'}, status=403)

        if paciente_id is None or paciente_id == '':
            return JsonResponse({'ok': False, 'mensaje': 'paciente_id es requerido'}, status=400)

        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
        medico = _resolver_medico_usuario(request, empresa, autocrear=True)

        with transaction.atomic():
            cita = CitaMedica.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, 'sucursal', None),
                paciente=paciente,
                medico=medico,
                fecha_cita=timezone.localdate(),
                hora_cita=timezone.localtime().time(),
                duracion_estimada=30,
                motivo=motivo,
                estado='EN_CURSO'
            )

            ConsultaMedica.objects.get_or_create(
                cita=cita,
                defaults={
                    'empresa': empresa,
                    'sucursal': getattr(request.user, 'sucursal', None),
                    'paciente': paciente,
                    'medico': medico,
                    'tipo_consulta': 'SUBSECUENTE' if paciente.consultas.exists() else 'PRIMERA_VEZ',
                    'estado': 'EN_CURSO',
                    'motivo_consulta': motivo,
                    'padecimiento_actual': motivo,
                    'diagnostico_principal': 'En proceso',
                    'plan_tratamiento': '',
                }
            )

            return JsonResponse({
                'ok': True,
                'mensaje': 'Consulta creada exitosamente',
                'cita_id': cita.id,
                'paciente': paciente.nombre_completo
            })

    except Http404:
        return JsonResponse({'ok': False, 'mensaje': 'Paciente no encontrado'}, status=404)
    except (DatabaseError, ValidationError) as e:
        return JsonResponse({'ok': False, 'mensaje': f'Error: {str(e)}'}, status=500)


# ==============================================================================
# API: CREAR PACIENTE Y CONSULTA
# ==============================================================================

@login_required
@require_http_methods(["POST"])
def api_crear_paciente_y_consulta(request):
    """
    API para crear paciente nuevo + consulta automáticamente.
    Flujo simplificado para médicos sin enfermero.
    """
    try:
        from datetime import datetime as dt

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'mensaje': 'JSON inválido'}, status=400)

        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'mensaje': 'Usuario sin empresa asignada'}, status=403)

        nombre = data.get('nombre', '').strip()
        apellidos = data.get('apellidos', '').strip()
        fecha_nacimiento = data.get('fecha_nacimiento')
        sexo = data.get('sexo')

        if not all([nombre, apellidos, fecha_nacimiento, sexo]):
            return JsonResponse({
                'ok': False,
                'mensaje': 'Faltan datos obligatorios (nombre, apellidos, fecha de nacimiento, sexo)'
            }, status=400)

        try:
            fecha_nac = dt.strptime(fecha_nacimiento, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return JsonResponse({
                'ok': False,
                'mensaje': 'fecha_nacimiento debe tener formato AAAA-MM-DD'
            }, status=400)

        hoy = date.today()
        if fecha_nac > hoy:
            return JsonResponse({'ok': False, 'mensaje': 'La fecha de nacimiento no puede ser futura.'}, status=400)
        if fecha_nac < date(1900, 1, 1):
            return JsonResponse({'ok': False, 'mensaje': 'La fecha de nacimiento debe ser posterior a 1900.'}, status=400)

        medico = _resolver_medico_usuario(request, empresa, autocrear=True)

        with transaction.atomic():
            nombre_completo = f"{nombre} {apellidos}".strip()
            paciente = Paciente.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, 'sucursal', None),
                nombre_completo=nombre_completo,
                fecha_nacimiento=fecha_nac,
                sexo=sexo,
                telefono=data.get('telefono', ''),
                email=data.get('email', ''),
                tipo='GENERAL'
            )

            cita = CitaMedica.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, 'sucursal', None),
                paciente=paciente,
                medico=medico,
                fecha_cita=timezone.localdate(),
                hora_cita=timezone.localtime().time(),
                duracion_estimada=30,
                motivo=data.get('motivo', 'Consulta general'),
                estado='EN_CURSO'
            )

            ConsultaMedica.objects.get_or_create(
                cita=cita,
                defaults={
                    'empresa': empresa,
                    'sucursal': getattr(request.user, 'sucursal', None),
                    'paciente': paciente,
                    'medico': medico,
                    'tipo_consulta': 'PRIMERA_VEZ',
                    'estado': 'EN_CURSO',
                    'motivo_consulta': data.get('motivo', 'Consulta general'),
                    'padecimiento_actual': data.get('motivo', 'Consulta general'),
                    'diagnostico_principal': 'En proceso',
                    'plan_tratamiento': '',
                }
            )

            return JsonResponse({
                'ok': True,
                'mensaje': 'Paciente y consulta creados exitosamente',
                'cita_id': cita.id,
                'paciente_id': paciente.id,
                'paciente': paciente.nombre_completo
            })

    except (DatabaseError, ValidationError) as e:
        return JsonResponse({'ok': False, 'mensaje': f'Error al crear paciente: {str(e)}'}, status=500)


# ==============================================================================
# API: BUSCAR PACIENTES
# ==============================================================================

@login_required
@require_http_methods(['GET'])
def api_buscar_pacientes(request):
    """
    API para buscar pacientes en tiempo real.
    Responde con JSON incluyendo UUID para navegacion.
    """
    termino = request.GET.get('q', '').strip()
    empresa = _empresa_explicita_usuario(request)
    if not empresa:
        return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada', 'pacientes': []}, status=403)

    if len(termino) < 2:
        return JsonResponse({'success': True, 'pacientes': []})

    sin_uuid = Paciente.objects.filter(empresa=empresa, activo=True, uuid__isnull=True)
    for p in sin_uuid[:50]:
        p.uuid = uuid_lib.uuid4()
        p.save(update_fields=['uuid'])

    pacientes = Paciente.objects.filter(
        empresa=empresa,
        activo=True,
    ).exclude(uuid__isnull=True).filter(
        Q(nombre_completo__icontains=termino) |
        Q(telefono__icontains=termino)
    ).order_by('nombre_completo')[:10]

    resultados = [{
        'id': p.id,
        'uuid': str(p.uuid),
        'nombre_completo': p.nombre_completo,
        'edad': p.edad,
        'sexo_display': p.get_sexo_display() if p.sexo else '--',
        'telefono': p.telefono or '',
    } for p in pacientes]

    return JsonResponse({'success': True, 'pacientes': resultados})


# ==============================================================================
# API: TRANSCRIPCIÓN INTELIGENTE CON IA
# ==============================================================================

@login_required
@require_http_methods(['POST'])
def api_analizar_transcripcion(request):
    """
    MOTOR IA SOAP INTELIGENTE.
    Analiza la transcripción completa de una consulta y clasifica en campos SOAP.
    """
    respuesta_texto = ''
    try:
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
        transcripcion = data.get('transcripcion_completa', '').strip()
        cita_id = data.get('cita_id')

        if not transcripcion:
            return JsonResponse({'ok': False, 'error': 'No se recibio transcripcion'}, status=400)

        from core.utils.gemini_client import generate_content

        prompt = f"""
Eres un asistente médico experto y altamente preciso. Tu tarea es analizar la
transcripción de una consulta médica donde el doctor habla libremente, y
CLASIFICAR AUTOMÁTICAMENTE cada fragmento de información en su campo SOAP correcto.

TRANSCRIPCIÓN COMPLETA DE LA CONSULTA:
---
{transcripcion}
---

REGLAS DE CLASIFICACIÓN (OBLIGATORIAS):
1. motivo_consulta: Lo que el PACIENTE reporta como razón de su visita (síntomas iniciales)
2. padecimiento_actual: Historia del padecimiento actual, evolución de síntomas,
   cuándo empezó, qué ha tomado, cómo ha progresado
3. exploracion_fisica: Lo que el MÉDICO observa, palpa, ausculta (hallazgos objetivos).
   Incluye: "a la exploración se encuentra...", "campos pulmonares...", "abdomen...",
   "faringe...", "se observa...", datos de la exploración clínica
4. diagnostico_principal: El diagnóstico final o presuntivo que el médico da
5. diagnostico_cie10: Código CIE-10 si se menciona (ej: J06.9, E11, K29.7).
   Si el diagnóstico es claro pero no se da código, SUGIERE uno.
6. diagnosticos_secundarios: Otros diagnósticos mencionados
7. plan_tratamiento: Medicamentos prescritos con dosis, frecuencia, duración.
   Incluye indicaciones como: reposo, dieta, hidratación, medidas generales
8. estudios_solicitados: Labs, rayos X, ultrasonidos o cualquier estudio solicitado
9. pronostico: Debe ser uno de: EXCELENTE, BUENO, REGULAR, RESERVADO, MALO
10. medicamentos_detectados: Lista de medicamentos mencionados, cada uno con:
    nombre, dosis, frecuencia, duracion, via (si se menciona)

FORMATO DE RESPUESTA (JSON ESTRICTO):
{{
  "motivo_consulta": "...",
  "padecimiento_actual": "...",
  "exploracion_fisica": "...",
  "diagnostico_principal": "...",
  "diagnostico_cie10": "...",
  "diagnosticos_secundarios": "...",
  "plan_tratamiento": "...",
  "estudios_solicitados": "...",
  "pronostico": "BUENO",
  "medicamentos_detectados": [
    {{
      "nombre": "Paracetamol",
      "dosis": "500mg",
      "frecuencia": "cada 8 horas",
      "duracion": "5 días",
      "via": "oral"
    }}
  ],
  "signos_vitales_detectados": {{
    "temperatura": null,
    "frecuencia_cardiaca": null,
    "presion_arterial": null,
    "peso": null,
    "talla": null,
    "saturacion": null
  }}
}}

REGLAS CRÍTICAS:
- NO inventes información que no esté en la transcripción
- Si un campo no tiene datos, usa "" (string vacío) o null para numéricos
- Sé preciso con los términos médicos
- Conserva los nombres comerciales Y genéricos de los medicamentos
- Si se menciona CIE-10, úsalo; si no, sugiere el más probable
- RESPONDE SOLO CON EL JSON, sin texto adicional ni backticks
"""

        try:
            respuesta_texto = generate_content(
                prompt,
                model_name='gemini-2.0-flash',
                temperature=0.2,
                max_tokens=2000,
            ).strip()
        except (ImportError, AttributeError, ValueError, RuntimeError) as ia_error:
            logger.warning('IA de transcripcion no disponible, usando fallback local: %s', ia_error)
            campos_soap = {
                "motivo_consulta": transcripcion[:500],
                "padecimiento_actual": transcripcion,
                "exploracion_fisica": "",
                "diagnostico_principal": "",
                "diagnostico_cie10": "",
                "diagnosticos_secundarios": "",
                "plan_tratamiento": "",
                "estudios_solicitados": "",
                "pronostico": "BUENO",
                "medicamentos_detectados": [],
                "signos_vitales_detectados": {
                    "temperatura": None, "frecuencia_cardiaca": None,
                    "presion_arterial": None, "peso": None,
                    "talla": None, "saturacion": None,
                },
            }
            respuesta_texto = json.dumps(campos_soap)

        if respuesta_texto.startswith('```'):
            respuesta_texto = respuesta_texto.split('```')[1]
            if respuesta_texto.startswith('json'):
                respuesta_texto = respuesta_texto[4:]
            respuesta_texto = respuesta_texto.strip()

        campos_soap = json.loads(respuesta_texto)

        transcripcion_guardada = False
        if cita_id:
            try:
                cita = CitaMedica.objects.filter(id=cita_id, empresa=empresa).first()
                consulta_tr = ConsultaMedica.objects.filter(cita=cita).first() if cita else None
                if consulta_tr:
                    consulta_tr.transcripcion_completa = transcripcion
                    consulta_tr.save(update_fields=['transcripcion_completa'])
                    transcripcion_guardada = True
            except (DatabaseError, ValidationError) as e:
                logger.error('Error guardando transcripcion: %s', e, exc_info=True)

        return JsonResponse({
            'ok': True,
            'campos_soap': campos_soap,
            'transcripcion_guardada': transcripcion_guardada,
            'mensaje': 'Campos SOAP extraidos y clasificados exitosamente',
        })

    except json.JSONDecodeError as e:
        return JsonResponse({
            'ok': False,
            'error': f'Error parseando JSON de IA: {str(e)}',
            'respuesta_ia': respuesta_texto,
        }, status=500)
    except (DatabaseError, ValidationError, ValueError, TypeError, ImportError, RuntimeError) as e:
        logger.error("Error en analisis de transcripcion: %s", e)
        return JsonResponse({'ok': False, 'error': f'Error procesando transcripcion: {str(e)}'}, status=500)


# ==============================================================================
# API: GENERACIÓN INMEDIATA DE RECETA
# ==============================================================================

@login_required
@require_http_methods(['POST'])
def api_generar_receta_inmediata(request):
    """Genera una receta INMEDIATAMENTE sin esperar al final de la consulta."""
    import uuid as _uuid
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
        cita_id = data.get('cita_id')
        medicamentos = data.get('medicamentos', [])

        if cita_id is None or cita_id == '':
            return JsonResponse({'ok': False, 'error': 'cita_id es requerido'}, status=400)
        if not medicamentos:
            return JsonResponse({'ok': False, 'error': 'Debe agregar al menos un medicamento'}, status=400)

        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)

        medico = _resolver_medico_usuario(request, empresa, medico_preferido=cita.medico, autocrear=True)

        consulta, _ = ConsultaMedica.objects.get_or_create(
            cita=cita,
            defaults={
                'empresa': empresa,
                'medico': medico,
                'paciente': cita.paciente,
                'fecha_consulta': timezone.now(),
                'motivo_consulta': 'En proceso',
                'padecimiento_actual': '',
                'exploracion_fisica': '',
                'diagnostico_principal': 'En proceso',
                'plan_tratamiento': '',
            }
        )

        with transaction.atomic():
            folio = f"RX-{cita_id}-{_uuid.uuid4().hex[:6].upper()}"
            receta = Receta.objects.create(
                empresa=empresa,
                medico=medico,
                paciente=cita.paciente,
                folio_receta=folio,
                diagnostico_principal=consulta.diagnostico_principal or 'En proceso',
                indicaciones=consulta.plan_tratamiento if consulta.plan_tratamiento else '',
                medico_nombre_completo=medico.nombre_completo if medico else request.user.get_full_name(),
                medico_cedula=medico.cedula_profesional if medico else '',
                medico_especialidad=medico.especialidad if medico else 'Médico General',
            )

            for med in medicamentos:
                nombre = med.get('nombre', '')
                dosis = med.get('dosis', '')
                duracion = med.get('duracion', '')
                try:
                    cant = int(med.get('cantidad', 1) or 1)
                except (ValueError, TypeError):
                    cant = 1

                med_producto = None
                if nombre:
                    med_producto = Producto.objects.filter(nombre__icontains=nombre, empresa=empresa).first()

                partes = [nombre]
                if dosis:
                    partes.append(f"Dosis: {dosis}")
                if duracion:
                    partes.append(f"Duración: {duracion}")
                texto = ' | '.join(partes)

                RecetaItem.objects.create(
                    receta=receta,
                    medicamento=med_producto,
                    texto_libre=texto,
                    cantidad=cant,
                )

            consulta.receta = receta
            consulta.save(update_fields=['receta'])

        url_pdf = request.build_absolute_uri(
            reverse('consultorio:pdf_receta_paciente', args=[consulta.id])
        )
        try:
            url_farmacia = request.build_absolute_uri(reverse('pdv_farmacia')) + '?receta_id=' + str(receta.id)
        except NoReverseMatch:
            url_farmacia = None

        return JsonResponse({
            'ok': True,
            'receta_id': receta.id,
            'url_pdf': url_pdf,
            'url_farmacia': url_farmacia,
            'mensaje': 'Receta generada exitosamente'
        })

    except (DatabaseError, ValidationError, ValueError, TypeError) as e:
        logger.error("Error generando receta inmediata: %s", e, exc_info=True)
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ==============================================================================
# API: GENERACIÓN INMEDIATA DE CERTIFICADO
# ==============================================================================

@login_required
@require_http_methods(['POST'])
def api_generar_certificado_inmediato(request):
    """Genera un certificado médico INMEDIATAMENTE."""
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
        cita_id = data.get('cita_id')
        tipo = data.get('tipo')
        motivo = data.get('motivo') or data.get('diagnostico', '')
        recomendaciones = data.get('recomendaciones', '')
        dias_incapacidad = data.get('dias_incapacidad', 0)

        if not motivo:
            return JsonResponse({'ok': False, 'error': 'Debe especificar el motivo o diagnóstico del certificado'}, status=400)
        if cita_id is None or cita_id == '':
            return JsonResponse({'ok': False, 'error': 'cita_id es requerido'}, status=400)

        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)

        medico = _resolver_medico_usuario(request, empresa, medico_preferido=cita.medico, autocrear=True)

        consulta, _ = ConsultaMedica.objects.get_or_create(
            cita=cita,
            defaults={
                'empresa': empresa,
                'medico': medico,
                'paciente': cita.paciente,
                'fecha_consulta': timezone.now(),
                'motivo_consulta': motivo,
                'padecimiento_actual': '',
                'exploracion_fisica': '',
                'diagnostico_principal': motivo,
                'plan_tratamiento': '',
            }
        )

        import uuid as _uuid
        fecha_inicio = timezone.now().date()
        dias_inc = _int_or_none(dias_incapacidad) or 0
        fecha_fin = fecha_inicio + timedelta(days=dias_inc) if dias_inc else fecha_inicio

        tipo_map = {
            'MEDICO': 'SALUD', 'INCAPACIDAD': 'INCAPACIDAD',
            'APTITUD': 'APTITUD', 'DEFUNCION': 'DEFUNCION', 'NACIMIENTO': 'NACIMIENTO',
        }
        tipo_cert = tipo_map.get(tipo, 'OTRO')
        folio_cert = f"CERT-{cita_id}-{_uuid.uuid4().hex[:6].upper()}"

        descripcion_texto = f"{motivo}. {recomendaciones}".strip() if recomendaciones else motivo
        certificado = CertificadoMedico.objects.create(
            empresa=empresa,
            consulta=consulta,
            medico=medico,
            paciente=cita.paciente,
            folio_certificado=folio_cert,
            tipo_certificado=tipo_cert,
            diagnostico=consulta.diagnostico_principal or motivo,
            descripcion=descripcion_texto,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            dias_incapacidad=dias_inc if dias_inc else None,
        )

        registrar_auditoria(
            accion='CREATE',
            modelo='CertificadoMedico',
            objeto_id=str(certificado.id),
            datos_nuevos={
                'folio': certificado.folio_certificado,
                'tipo': tipo_cert,
                'paciente_id': cita.paciente_id,
                'cita_id': cita.id,
            },
            request=request,
        )

        url_ver = request.build_absolute_uri(
            reverse('consultorio:ver_certificado', args=[certificado.id])
        )
        return JsonResponse({
            'ok': True,
            'certificado_id': certificado.id,
            'url_ver': url_ver,
            'url_pdf': url_ver,
            'mensaje': '✅ Certificado generado exitosamente'
        })

    except (DatabaseError, ValidationError, ValueError, TypeError) as e:
        logger.error("Error generando certificado: %s", e)
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ==============================================================================
# API: GENERACIÓN INMEDIATA DE ORDEN DE LABORATORIO
# ==============================================================================

@login_required
@require_http_methods(['POST'])
def api_generar_orden_laboratorio_inmediata(request):
    """Genera una orden de laboratorio INMEDIATAMENTE."""
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
        cita_id = data.get('cita_id')
        estudios = data.get('estudios', [])
        urgencia = data.get('urgencia', 'NORMAL')

        if cita_id is None or cita_id == '':
            return JsonResponse({'ok': False, 'error': 'cita_id es requerido'}, status=400)
        if not estudios:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar al menos un estudio'}, status=400)

        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        cita = get_object_or_404(CitaMedica, id=cita_id, empresa=empresa)

        medico = _resolver_medico_usuario(request, empresa, medico_preferido=cita.medico, autocrear=True)

        tipo_srv = 'URGENCIA' if urgencia == 'URGENCIA' else 'RUTINA'

        raw_ids = []
        for item in estudios:
            if isinstance(item, dict):
                eid = item.get('id')
                if eid is not None:
                    raw_ids.append(eid)
            else:
                raw_ids.append(item)

        lineas = resolve_lims_cart_ids(list(raw_ids), empresa=empresa)
        if not lineas:
            return JsonResponse({
                'ok': False,
                'error': 'No se resolvió ningún ítem del catálogo LIMS (analito/perfil/paquete)',
            }, status=400)

        with transaction.atomic():
            total_orden = Decimal('0.00')
            for row in lineas:
                total_orden += aplicar_precio_convenio(row['precio_base'], row['precio_key'], {}, Decimal('0'))
            total_orden = total_orden.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            orden = OrdenDeServicio.objects.create(
                empresa=empresa,
                paciente=cita.paciente,
                medico_referente=medico,
                tipo_servicio=tipo_srv,
                diagnostico=f'Orden generada en consulta (Cita #{cita.id})',
                estado='PENDIENTE_PAGO',
                total=total_orden,
                responsable_ingreso=request.user,
            )

            for row in lineas:
                precio_momento = aplicar_precio_convenio(
                    row['precio_base'], row['precio_key'], {}, Decimal('0')
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                desc = (row.get('descripcion_linea') or '')[:300]
                DetalleOrden.objects.create(
                    orden=orden,
                    analito=row['analito'],
                    perfil_lims=row['perfil_lims'],
                    paquete_lims=row['paquete_lims'],
                    descripcion_linea=desc,
                    precio_momento=precio_momento,
                )

        return JsonResponse({
            'ok': True,
            'orden_id': orden.id,
            'url_detalle': reverse('imprimir_ticket_lab', args=[orden.id]),
            'mensaje': '✅ Orden de laboratorio generada exitosamente'
        })

    except (DatabaseError, ValidationError, ValueError, TypeError) as e:
        logger.error("Error generando orden: %s", e)
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ==============================================================================
# ARCHIVOS ADJUNTOS
# ==============================================================================

@login_required
def archivos_paciente(request, paciente_id):
    """Vista de archivos adjuntos de un paciente."""
    from consultorio.models import ArchivoAdjuntoConsulta
    from django.shortcuts import render

    empresa = empresa_efectiva_request(request)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    archivos = ArchivoAdjuntoConsulta.objects.filter(
        paciente=paciente, empresa=empresa
    ).order_by('-fecha_subida')

    tipos_archivo = {}
    for archivo in archivos:
        tipo = archivo.get_tipo_display()
        if tipo not in tipos_archivo:
            tipos_archivo[tipo] = []
        tipos_archivo[tipo].append(archivo)

    return render(request, 'consultorio/archivos_paciente.html', {
        'paciente': paciente,
        'archivos': archivos,
        'tipos_archivo': tipos_archivo,
        'tipo_choices': ArchivoAdjuntoConsulta.TIPO_CHOICES,
    })


@login_required
@require_http_methods(['POST'])
def api_subir_archivo(request):
    """API para subir archivos adjuntos (radiografías, tomografías, etc.)."""
    from consultorio.models import ArchivoAdjuntoConsulta

    try:
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        paciente_id = request.POST.get('paciente_id')
        consulta_id = request.POST.get('consulta_id')
        tipo = request.POST.get('tipo', 'DOCUMENTO')
        titulo = request.POST.get('titulo', 'Sin título')
        descripcion = request.POST.get('descripcion', '')
        origen = request.POST.get('origen', '')
        fecha_documento = request.POST.get('fecha_documento')

        if not paciente_id:
            return JsonResponse({'ok': False, 'error': 'paciente_id es requerido'}, status=400)
        if 'archivo' not in request.FILES:
            return JsonResponse({'ok': False, 'error': 'No se recibio archivo'}, status=400)

        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

        consulta = None
        if consulta_id:
            consulta = ConsultaMedica.objects.filter(id=consulta_id, empresa=empresa).first()
            if consulta and consulta.paciente_id != paciente.id:
                return JsonResponse({
                    'ok': False,
                    'error': 'La consulta seleccionada no corresponde al paciente indicado'
                }, status=400)

        archivo = ArchivoAdjuntoConsulta.objects.create(
            empresa=empresa,
            paciente=paciente,
            consulta=consulta,
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion,
            archivo=request.FILES['archivo'],
            origen=origen,
            fecha_documento=fecha_documento if fecha_documento else None,
            subido_por=request.user,
        )

        return JsonResponse({
            'ok': True,
            'archivo_id': archivo.id,
            'titulo': archivo.titulo,
            'tipo': archivo.get_tipo_display(),
            'mensaje': f'Archivo "{titulo}" subido exitosamente'
        })

    except (DatabaseError, ValidationError, ValueError, TypeError, OSError) as e:
        logger.error("Error subiendo archivo: %s", e)
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_eliminar_archivo(request, archivo_id):
    """Eliminar archivo adjunto."""
    from consultorio.models import ArchivoAdjuntoConsulta
    from django.core.exceptions import ObjectDoesNotExist

    try:
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
        archivo = get_object_or_404(ArchivoAdjuntoConsulta, id=archivo_id, empresa=empresa)
        nombre = archivo.titulo
        archivo.delete()

        return JsonResponse({'ok': True, 'mensaje': f'Archivo "{nombre}" eliminado'})
    except (DatabaseError, ValidationError, ObjectDoesNotExist, OSError) as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ==============================================================================
# VADEMÉCUM API
# ==============================================================================

@login_required
@require_http_methods(['GET'])
def api_buscar_vademecum(request):
    """API para buscar medicamentos en el Vademécum integrado."""
    from consultorio.models import Vademecum

    termino = request.GET.get('q', '').strip()

    if len(termino) < 2:
        return JsonResponse([], safe=False)

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)

    medicamentos = Vademecum.objects.filter(activo=True).filter(
        Q(empresa=empresa) | Q(empresa__isnull=True)
    ).filter(
        Q(nombre_generico__icontains=termino) |
        Q(nombre_comercial__icontains=termino) |
        Q(principio_activo__icontains=termino) |
        Q(grupo_terapeutico__icontains=termino)
    ).order_by('nombre_generico')[:15]

    resultados = [{
        'id': m.id,
        'nombre_generico': m.nombre_generico,
        'nombre_comercial': m.nombre_comercial,
        'principio_activo': m.principio_activo,
        'presentacion': m.presentacion,
        'concentracion': m.concentracion,
        'via': m.get_via_administracion_display(),
        'dosis_adulto': m.dosis_adulto,
        'dosis_pediatrica': m.dosis_pediatrica,
        'dosis_maxima': m.dosis_maxima,
        'contraindicaciones': m.contraindicaciones,
        'efectos_adversos': m.efectos_adversos,
        'interacciones': m.interacciones,
        'embarazo': m.get_embarazo_categoria_display() if m.embarazo_categoria else '',
        'requiere_receta': m.requiere_receta,
        'controlado': m.controlado,
        'en_farmacia': m.producto_farmacia_id is not None,
    } for m in medicamentos]

    return JsonResponse(resultados, safe=False)


# ==============================================================================
# SIGNOS VITALES TENDENCIA API
# ==============================================================================

@login_required
@require_http_methods(['GET'])
def api_signos_vitales_tendencia(request, paciente_id):
    """Retorna historial de signos vitales para gráficas de tendencias."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    signos = SignosVitales.objects.filter(paciente=paciente).order_by('fecha_registro')[:20]

    datos = {
        'fechas': [], 'peso': [], 'imc': [], 'pa_sistolica': [],
        'pa_diastolica': [], 'temperatura': [], 'glucosa': [], 'fc': [], 'spo2': [],
    }

    for s in signos:
        datos['fechas'].append(s.fecha_registro.strftime('%d/%m/%Y'))
        datos['peso'].append(float(s.peso) if s.peso else None)
        datos['imc'].append(float(s.imc) if s.imc else None)
        datos['pa_sistolica'].append(s.presion_arterial_sistolica)
        datos['pa_diastolica'].append(s.presion_arterial_diastolica)
        datos['temperatura'].append(float(s.temperatura) if s.temperatura else None)
        datos['glucosa'].append(float(s.glucosa_capilar) if s.glucosa_capilar else None)
        datos['fc'].append(s.frecuencia_cardiaca)
        datos['spo2'].append(s.saturacion_oxigeno)

    return JsonResponse({
        'ok': True,
        'paciente': paciente.nombre_completo,
        'total_registros': len(signos),
        'datos': datos,
    })


# ==============================================================================
# PLANTILLAS POR ESPECIALIDAD
# ==============================================================================

@login_required
@require_http_methods(['GET'])
def api_plantillas_especialidad(request):
    """Retorna plantillas de notas clínicas filtradas por especialidad del médico."""
    from core.models import PlantillaNotaClinica
    from consultorio.models import ConfiguracionMedico

    empresa = _empresa_explicita_usuario(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)

    try:
        config = ConfiguracionMedico.objects.get(medico=request.user)
        especialidad = config.especialidad_principal
    except ConfiguracionMedico.DoesNotExist:
        especialidad = ''

    plantillas = PlantillaNotaClinica.objects.filter(
        empresa=empresa, activa=True
    ).filter(
        Q(es_publica=True) |
        Q(creado_por=request.user) |
        Q(especialidad__icontains=especialidad) |
        Q(especialidad='')
    ).order_by('-veces_usada', 'nombre')[:20]

    resultados = [{
        'id': p.id,
        'nombre': p.nombre,
        'descripcion': p.descripcion,
        'especialidad': p.especialidad,
        'subjetivo': p.subjetivo,
        'objetivo': p.objetivo,
        'analisis': p.analisis,
        'plan': p.plan,
        'veces_usada': p.veces_usada,
    } for p in plantillas]

    return JsonResponse(resultados, safe=False)


@login_required
@require_http_methods(['POST'])
def api_usar_plantilla(request, plantilla_id):
    """Incrementa contador de uso y retorna datos de la plantilla."""
    from core.models import PlantillaNotaClinica

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
    plantilla = get_object_or_404(PlantillaNotaClinica, id=plantilla_id, empresa=empresa)
    plantilla.veces_usada += 1
    plantilla.save(update_fields=['veces_usada'])

    return JsonResponse({
        'ok': True,
        'subjetivo': plantilla.subjetivo,
        'objetivo': plantilla.objetivo,
        'analisis': plantilla.analisis,
        'plan': plantilla.plan,
    })


# ==============================================================================
# API: RESULTADOS DISPONIBLES PARA EL DASHBOARD MÉDICO
# ==============================================================================

@login_required
@require_http_methods(['GET'])
def api_resultados_disponibles(request):
    """
    Devuelve las órdenes de laboratorio con resultados listos
    vinculadas a pre-órdenes del médico actual.
    """
    try:
        from core.models import PreOrdenLaboratorio
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'status': 'success', 'resultados': []})

        preordenes = PreOrdenLaboratorio.objects.filter(
            empresa=empresa,
            medico_solicitante=request.user,
            estado='COBRADA'
        ).select_related('paciente', 'orden_vinculada')[:10]

        resultados = []
        for preorden in preordenes:
            if preorden.orden_vinculada:
                orden = preorden.orden_vinculada
                if orden.estado in ['RESULTADOS_LISTOS', 'ENTREGADO']:
                    estudios_names = list(
                        orden.detalles.values_list('estudio__nombre', flat=True)[:3]
                    )
                    resultados.append({
                        'orden_id': orden.id,
                        'paciente_nombre': preorden.paciente.nombre_completo if preorden.paciente else 'N/D',
                        'estudios': ', '.join(estudios_names),
                        'fecha': timezone.localtime(orden.fecha_creacion).strftime('%d/%m/%Y') if orden.fecha_creacion else '',
                    })

        return JsonResponse({'status': 'success', 'resultados': resultados})
    except (DatabaseError, ImportError, AttributeError) as e:
        return JsonResponse({'status': 'success', 'resultados': [], 'nota': str(e)})
