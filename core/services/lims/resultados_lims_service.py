"""
Captura y validación clínica de resultados LIMS (ResultadoParametro, DetalleOrden, estado orden).
Persistencia multi-analito bajo transaction.atomic(); la vista solo enruta HTTP.
"""
import json
import logging

from django.db import transaction
from django.utils import timezone

from core.api_contracts.errors import BusinessApiError
from core.lims_cart import detalle_orden_etiqueta
from core.models import AuditLog, DetalleOrden, OrdenDeServicio, ResultadoParametro
from core.utils.trazabilidad import registrar_trazabilidad, serializar_modelo
from lims.models import Analito
from reglas_negocio.validadores import validar_triple_llave

logger_core = logging.getLogger('core')


class ResultadosLimsService:
    """Guardado de captura manual, validación contra rangos y transición a RESULTADOS_LISTOS."""

    @staticmethod
    def guardar_captura(request, empresa, orden_id):
        """
        Equivalente a api_guardar_resultados (POST JSON).
        Devuelve {'http_status': int, 'body': dict}.
        """
        try:
            try:
                OrdenDeServicio.objects.get(id=orden_id, empresa=empresa)
            except OrdenDeServicio.DoesNotExist:
                return {
                    'http_status': 404,
                    'body': {'status': 'error', 'mensaje': f'Orden {orden_id} no encontrada'},
                }

            try:
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                return {
                    'http_status': 400,
                    'body': {'status': 'error', 'mensaje': f'JSON inválido: {e}'},
                }

            return ResultadosLimsService.guardar_captura_desde_datos(
                request, empresa, orden_id, data, usuario_efectivo=None
            )
        except OrdenDeServicio.DoesNotExist:
            return {
                'http_status': 404,
                'body': {'status': 'error', 'mensaje': 'Orden no encontrada'},
            }
        except Exception as e:
            import traceback

            error_detail = traceback.format_exc()
            try:
                logger_core.error(
                    'FALLO AL GUARDAR RESULTADOS (LABORATORIO) - '
                    'Usuario: %s (ID: %s) - Orden ID: %s - Error: %s - Tipo: %s - Traceback: %s - Empresa: %s',
                    getattr(request.user, 'username', '?'),
                    getattr(request.user, 'id', None),
                    orden_id,
                    str(e),
                    type(e).__name__,
                    error_detail[:500],
                    empresa.nombre,
                )
            except Exception as log_error:
                logger_core.error(
                    'guardar_resultados: error secundario al registrar el error principal: %s',
                    log_error,
                )
            return {
                'http_status': 500,
                'body': {'status': 'error', 'mensaje': f'Error inesperado: {str(e)}'},
            }

    @staticmethod
    def guardar_captura_desde_datos(request, empresa, orden_id, data, *, usuario_efectivo=None):
        """
        Misma lógica que guardar_captura con payload ya parseado (dict).
        usuario_efectivo: usuario Django para captura/validación cuando no hay sesión (p.ej. HL7).
        data puede incluir 'metodo_captura' (p.ej. INTERFAZ) para ResultadoParametro.
        """
        try:
            try:
                OrdenDeServicio.objects.get(id=orden_id, empresa=empresa)
            except OrdenDeServicio.DoesNotExist:
                return {
                    'http_status': 404,
                    'body': {'status': 'error', 'mensaje': f'Orden {orden_id} no encontrada'},
                }

            actor = usuario_efectivo if usuario_efectivo is not None else request.user
            metodo_captura_rp = str(data.get('metodo_captura') or 'MANUAL').strip()[:20] or 'MANUAL'

            resultados_data = data.get('resultados', {})
            accion = data.get('accion', 'borrador')

            _MIG0058_CODIGO = '__PRISLAB_MIG_0058__'
            if accion == 'validar':
                if ResultadoParametro.objects.filter(
                    orden_id=orden_id,
                    analito__codigo=_MIG0058_CODIGO,
                ).exists():
                    return {
                        'http_status': 400,
                        'body': {
                            'status': 'error',
                            'mensaje': (
                                'Hay resultados ligados al analito placeholder de la migración 0058. '
                                'Ejecute: python manage.py ensamblar_lims_v75 y luego '
                                'remap_placeholder_resultados antes de validar.'
                            ),
                            'codigo': 'LIMS_PLACEHOLDER_0058',
                        },
                    }
                raw_eq = data.get('equipo_id')
                equipo_validacion = None
                if raw_eq is not None and str(raw_eq).strip() != '':
                    try:
                        eid = int(raw_eq)
                    except (TypeError, ValueError):
                        return {
                            'http_status': 400,
                            'body': {'status': 'error', 'mensaje': 'equipo_id inválido'},
                        }
                    from laboratorio.models import Equipo
                    from laboratorio.services.metrologia_lab import evaluar_metrologia_equipo
                    from laboratorio.services.cci_canal import QC_CANAL_CODIGO

                    equipo_validacion = Equipo.objects.filter(pk=eid, activo=True).first()
                    if not equipo_validacion:
                        return {
                            'http_status': 400,
                            'body': {
                                'status': 'error',
                                'mensaje': 'Equipo no encontrado o inactivo.',
                            },
                        }
                    nivel, mmsg = evaluar_metrologia_equipo(equipo_validacion)
                    if nivel != 'ok':
                        return {
                            'http_status': 400,
                            'body': {
                                'status': 'error',
                                'mensaje': (
                                    mmsg
                                    or 'Calibración / metrología del equipo no permite validar resultados.'
                                ),
                                'codigo': QC_CANAL_CODIGO,
                            },
                        }

                if equipo_validacion:
                    from laboratorio.services.cci_canal import mensaje_bloqueo_canal, QC_CANAL_CODIGO

                    for _det_id, _datos in (resultados_data or {}).items():
                        for analito_id_str, param_info in (_datos.get('parametros') or {}).items():
                            try:
                                aid = int(analito_id_str)
                            except (TypeError, ValueError):
                                continue
                            if aid == 0 or not (param_info.get('valor') or '').strip():
                                continue
                            an = Analito.objects.filter(id=aid, activo=True).first()
                            if not an:
                                continue
                            msg_canal = mensaje_bloqueo_canal(empresa, equipo_validacion, an)
                            if msg_canal:
                                return {
                                    'http_status': 400,
                                    'body': {
                                        'status': 'error',
                                        'mensaje': msg_canal,
                                        'codigo': QC_CANAL_CODIGO,
                                        'analito_id': aid,
                                    },
                                }

            from core.utils.auditoria_helper import crear_log_auditoria

            pdf_pendiente_pago = False
            saldo_pdf_pendiente = None
            aviso_consentimiento = None
            _formula_engine_snapshot = {}

            with transaction.atomic():
                orden = OrdenDeServicio.objects.select_for_update().filter(
                    id=orden_id,
                    empresa=empresa,
                ).first()
                if not orden:
                    return {
                        'http_status': 404,
                        'body': {'status': 'error', 'mensaje': 'Orden no encontrada'},
                    }

                if accion == 'validar' and orden.estado in ('RESULTADOS_LISTOS', 'ENTREGADO'):
                    logger_core.info(
                        'ResultadosLimsService validar idempotente orden=%s usuario=%s estado=%s',
                        orden_id,
                        getattr(actor, 'username', str(getattr(actor, 'pk', '?'))),
                        orden.estado,
                    )
                    return {
                        'http_status': 200,
                        'body': {
                            'status': 'success',
                            'mensaje': 'La orden ya estaba validada; no se duplicó la operación.',
                            'orden_id': orden.id,
                            'folio': orden.folio_orden,
                            'validado': True,
                            'idempotente': True,
                        },
                    }

                if not resultados_data:
                    return {
                        'http_status': 400,
                        'body': {'status': 'error', 'mensaje': 'No se recibieron resultados'},
                    }

                for detalle_id, datos in resultados_data.items():
                    try:
                        detalle_id_int = int(detalle_id)
                        try:
                            detalle = DetalleOrden.objects.get(id=detalle_id_int, orden=orden)
                        except DetalleOrden.DoesNotExist:
                            continue

                        datos_anterior = {
                            'resultado': detalle.resultado or '',
                            'observaciones': detalle.observaciones or '',
                            'validado_por': detalle.validado_por.id if detalle.validado_por else None,
                            'fecha_validacion': (
                                detalle.fecha_validacion.isoformat()
                                if detalle.fecha_validacion
                                else None
                            ),
                        }

                        resultado_nuevo = datos.get('resultado', '').strip()
                        observaciones_nueva = datos.get('observaciones', '').strip()

                        if resultado_nuevo:
                            analito_linea = getattr(detalle, 'analito', None)
                            etiqueta = detalle_orden_etiqueta(detalle)
                            if analito_linea and analito_linea.tipo_resultado == 'NUMERICO':
                                try:
                                    valor_numerico = float(resultado_nuevo.replace(',', '.'))
                                    if valor_numerico < 0:
                                        return {
                                            'http_status': 400,
                                            'body': {
                                                'status': 'error',
                                                'mensaje': (
                                                    f'El resultado no puede ser negativo para {etiqueta}'
                                                ),
                                            },
                                        }
                                except ValueError:
                                    return {
                                        'http_status': 400,
                                        'body': {
                                            'status': 'error',
                                            'mensaje': (
                                                f'El resultado de {etiqueta} debe ser un número válido'
                                            ),
                                        },
                                    }

                        detalle.resultado = resultado_nuevo
                        detalle.observaciones = observaciones_nueva
                        detalle.validado_por = actor
                        detalle.fecha_validacion = timezone.now()
                        detalle.save()

                        parametros_data = datos.get('parametros', {})
                        if parametros_data:
                            for analito_id_str, param_info in parametros_data.items():
                                try:
                                    aid = int(analito_id_str)
                                    if aid == 0:
                                        continue
                                    an = Analito.objects.filter(id=aid, activo=True).first()
                                    if an and getattr(an, 'es_calculado', False):
                                        continue
                                    if an and param_info.get('valor', '').strip():
                                        valor_param = param_info['valor'].strip()
                                        rp, _created = ResultadoParametro.objects.update_or_create(
                                            orden=orden,
                                            analito=an,
                                            defaults={
                                                'valor': valor_param,
                                                'capturado_por': actor,
                                                'fecha_captura': timezone.now(),
                                                'metodo_captura': metodo_captura_rp,
                                                'validado': accion == 'validar',
                                                'aprobado_por_humano': False,
                                            },
                                        )
                                        if accion == 'validar':
                                            rp.validado_por = actor
                                            rp.fecha_validacion = timezone.now()
                                            rp.save(
                                                update_fields=['validado_por', 'fecha_validacion']
                                            )
                                        from core.utils.referencia_lims_edad import (
                                            contexto_edad_sexo_para_lims,
                                        )

                                        _ctx_v = contexto_edad_sexo_para_lims(orden, orden.paciente)
                                        _vd = {}
                                        try:
                                            _vd = rp.validar_contra_rango(
                                                edad=_ctx_v['edad'],
                                                sexo=_ctx_v['sexo'],
                                                edad_dias=_ctx_v['edad_dias'],
                                            ) or {}
                                        except Exception:
                                            logger_core.debug(
                                                'ResultadosLimsService validar_contra_rango rp=%s',
                                                rp.pk,
                                                exc_info=True,
                                            )
                                        try:
                                            rp.refresh_from_db()
                                        except Exception:
                                            pass
                                        if _vd.get('es_critico') or getattr(rp, 'es_critico', False):
                                            try:
                                                from laboratorio.services.escudo_clinico_lims import (
                                                    notificar_panico_escudo_lims,
                                                )

                                                notificar_panico_escudo_lims(
                                                    rp,
                                                    orden,
                                                    _vd,
                                                    request_user=actor,
                                                )
                                            except Exception as _esc_exc:
                                                logger_core.warning(
                                                    'Escudo LIMS captura manual: %s', _esc_exc
                                                )
                                except (ValueError, TypeError):
                                    continue

                        datos_nuevo = {
                            'resultado': resultado_nuevo,
                            'observaciones': observaciones_nueva,
                            'validado_por': getattr(actor, 'id', None),
                            'fecha_validacion': detalle.fecha_validacion.isoformat(),
                        }

                        crear_log_auditoria(
                            empresa=empresa,
                            usuario=actor,
                            accion=AuditLog.ACCION_UPDATE,
                            modelo='DetalleOrden',
                            objeto_id=detalle.id,
                            datos_anterior=datos_anterior,
                            datos_nuevo=datos_nuevo,
                            sucursal=getattr(actor, 'sucursal', None),
                            request=request,
                        )

                    except (ValueError, DetalleOrden.DoesNotExist):
                        continue

                from core.services.clinical_math import sync_calculated_resultados_for_orden

                _sync_formulas = sync_calculated_resultados_for_orden(
                    orden, actor, accion_validar=(accion == 'validar')
                )
                _formula_engine_snapshot['sync'] = _sync_formulas
                _must_calc_ids = set()
                for _d in DetalleOrden.objects.filter(
                    orden=orden, analito__isnull=False
                ).select_related('analito'):
                    _aa = _d.analito
                    if _aa.es_calculado and (_aa.formula or '').strip():
                        _must_calc_ids.add(_aa.id)
                _done_calc_ids = {int(k) for k in _sync_formulas.get('computados', {}).keys()}
                if accion == 'validar' and _must_calc_ids - _done_calc_ids:
                    return {
                        'http_status': 400,
                        'body': {
                            'status': 'error',
                            'mensaje': (
                                'No se pudieron calcular todos los analitos derivados. '
                                'Capture valores numéricos en los analitos base indicados en la fórmula.'
                            ),
                            'codigo': 'FORMULA_INCOMPLETA',
                            'formulas_avisos': _sync_formulas.get('avisos', []),
                        },
                    }

                from core.utils.referencia_lims_edad import contexto_edad_sexo_para_lims

                for _aid_str in _sync_formulas.get('computados', {}):
                    try:
                        _rp_calc = ResultadoParametro.objects.get(
                            orden=orden, analito_id=int(_aid_str)
                        )
                    except ResultadoParametro.DoesNotExist:
                        continue
                    _ctx_c = contexto_edad_sexo_para_lims(orden, orden.paciente)
                    _vd_c = {}
                    try:
                        _vd_c = _rp_calc.validar_contra_rango(
                            edad=_ctx_c['edad'],
                            sexo=_ctx_c['sexo'],
                            edad_dias=_ctx_c['edad_dias'],
                        ) or {}
                    except Exception:
                        logger_core.debug(
                            'ResultadosLimsService validar_contra_rango rp_calc=%s',
                            _rp_calc.pk,
                            exc_info=True,
                        )
                    try:
                        _rp_calc.refresh_from_db()
                    except Exception:
                        pass
                    if _vd_c.get('es_critico') or getattr(_rp_calc, 'es_critico', False):
                        try:
                            from laboratorio.services.escudo_clinico_lims import (
                                notificar_panico_escudo_lims,
                            )

                            notificar_panico_escudo_lims(
                                _rp_calc, orden, _vd_c, request_user=actor
                            )
                        except Exception as _esc_c:
                            logger_core.warning('Escudo LIMS fórmula: %s', _esc_c)

                if accion == 'validar':
                    rol_usuario = (getattr(actor, 'rol', '') or '').upper().strip()
                    es_quimico_por_grupo = actor.groups.filter(
                        name__in=['LABORATORIO', 'GERENCIA_OPERATIVA']
                    ).exists()
                    if (
                        rol_usuario
                        not in ('QUIMICO', 'LABORATORIO', 'ADMIN', 'ADMINISTRADOR')
                        and not actor.is_superuser
                        and not actor.is_staff
                        and not es_quimico_por_grupo
                    ):
                        return {
                            'http_status': 403,
                            'body': {
                                'status': 'error',
                                'mensaje': (
                                    'Solo personal autorizado (Químico/Admin) puede validar resultados.'
                                ),
                            },
                        }

                    _orden_chk = OrdenDeServicio.objects.select_related('paciente').prefetch_related(
                        'resultados',
                    ).get(pk=orden.pk)
                    ok_llave, errs_llave = validar_triple_llave(_orden_chk)
                    if not ok_llave:
                        transaction.set_rollback(True)
                        return {
                            'http_status': 400,
                            'body': {
                                'status': 'error',
                                'mensaje': (
                                    ' '.join(errs_llave).strip()
                                    or 'La orden no cumple las reglas para validar y publicar resultados.'
                                ),
                                'codigo': 'TRIPLE_LLAVE',
                                'errores': errs_llave,
                            },
                        }

                    try:
                        from core.views.consentimientos import validar_consentimiento_requerido

                        tiene_consentimiento, mensaje_consentimiento = (
                            validar_consentimiento_requerido(orden)
                        )
                        if not tiene_consentimiento:
                            aviso_consentimiento = mensaje_consentimiento
                            logger_core.warning(
                                'Validación sin consentimiento firmado - Orden %s - Usuario: %s - Motivo: %s',
                                orden_id,
                                getattr(actor, 'username', str(getattr(actor, 'pk', '?'))),
                                mensaje_consentimiento,
                            )
                    except Exception:
                        logger_core.warning(
                            'guardar_resultados: error verificando consentimiento (orden=%s)',
                            orden_id,
                            exc_info=True,
                        )

                    try:
                        from core.services.motor_reportes_lab import (
                            generar_reporte_pdf,
                            guardar_reporte_en_storage,
                        )
                        from core.utils.candado_financiero import ReportePdfSaldoPendienteError

                        pdf_bytes = generar_reporte_pdf(orden, request=request)
                        pdf_url = guardar_reporte_en_storage(orden, pdf_bytes)
                        if not pdf_url:
                            return {
                                'http_status': 500,
                                'body': {
                                    'status': 'error',
                                    'mensaje': (
                                        'No se pudo guardar el PDF de resultados en storage. '
                                        'La orden no fue marcada como lista.'
                                    ),
                                },
                            }
                    except ReportePdfSaldoPendienteError as e:
                        pdf_pendiente_pago = True
                        saldo_pdf_pendiente = float(e.saldo_pendiente)
                        logger_core.info(
                            'ResultadosLimsService: validación sin PDF por saldo pendiente orden=%s saldo=%s',
                            orden_id,
                            saldo_pdf_pendiente,
                        )
                    except Exception as e:
                        logger_core.error(
                            'guardar_resultados: fallo generando/guardando PDF (orden=%s): %s',
                            orden_id,
                            e,
                            exc_info=True,
                        )
                        return {
                            'http_status': 500,
                            'body': {
                                'status': 'error',
                                'mensaje': (
                                    f'No se pudo generar/adjuntar el PDF de resultados: {str(e)}'
                                ),
                            },
                        }

                    ResultadoParametro.objects.filter(orden=orden).update(aprobado_por_humano=True)

                    orden.estado = 'RESULTADOS_LISTOS'

                    orden.detalles.filter(
                        estado_procesamiento__in=['PENDIENTE_TOMA', 'TOMA_REALIZADA', 'EN_PROCESO']
                    ).update(
                        estado_procesamiento='RESULTADO_LISTO',
                        validado_por=actor,
                        fecha_validacion=timezone.now(),
                    )

                orden.save()

                if accion == 'validar':
                    try:
                        from core.models import BitacoraEntregaResultados

                        bit, _ = BitacoraEntregaResultados.objects.get_or_create(
                            orden_id=orden.id,
                            defaults={
                                'empresa': empresa,
                                'folio_orden': getattr(orden, 'folio_orden', f'ORD-{orden.id}'),
                                'paciente_nombre': str(orden.paciente) if orden.paciente else '',
                                'paciente_id': orden.paciente.id if orden.paciente else None,
                                'canal': 'VALIDACION',
                                'estado': 'PENDIENTE',
                                'usuario_entrega': actor,
                            },
                        )
                    except Exception as _e:
                        logger_core.warning('BitacoraEntregaResultados: %s', _e)

                    try:
                        from laboratorio.services.escudo_clinico_lims import (
                            notificar_panico_escudo_lims,
                        )
                        from core.models import ResultadoParametro as RP

                        rps = list(RP.objects.filter(orden=orden).select_related('analito'))
                        _ctx_fin = contexto_edad_sexo_para_lims(orden, orden.paciente)

                        for rp in rps:
                            if not rp.valor or not rp.analito_id:
                                continue
                            try:
                                vr = rp.validar_contra_rango(
                                    edad=_ctx_fin['edad'],
                                    sexo=_ctx_fin['sexo'],
                                    edad_dias=_ctx_fin['edad_dias'],
                                ) or {}
                                try:
                                    rp.refresh_from_db()
                                except Exception:
                                    pass
                                if getattr(rp, 'es_critico', False):
                                    notificar_panico_escudo_lims(
                                        rp, orden, vr, request_user=actor
                                    )
                            except Exception as _rp_err:
                                logger_core.warning(
                                    'Escudo LIMS validación final rp %s: %s', rp.pk, _rp_err
                                )
                    except Exception as _ev:
                        logger_core.warning('Validacion escudo LIMS: %s', _ev)

                    registrar_trazabilidad(
                        tipo_operacion='RESULTADO_LAB',
                        modulo='LABORATORIO',
                        referencia_id=orden.id,
                        referencia_tipo='OrdenDeServicio',
                        accion='AUTORIZAR',
                        descripcion=(
                            f'Resultados de laboratorio validados - Orden: {orden.folio_orden} - '
                            f'Paciente: {orden.paciente.nombre_completo}'
                        ),
                        usuario=actor,
                        empresa=empresa,
                        datos_nuevos=serializar_modelo(orden),
                        request=request,
                    )

            mensaje = (
                'Resultados guardados como borrador'
                if accion == 'borrador'
                else 'Resultados validados y publicados correctamente'
            )
            respuesta = {
                'status': 'success',
                'mensaje': mensaje,
                'orden_id': orden.id,
                'folio': orden.folio_orden,
                'validado': accion == 'validar',
            }
            _fe = _formula_engine_snapshot.get('sync') or {}
            if _fe.get('computados'):
                respuesta['formulas_computados'] = _fe['computados']
            if _fe.get('avisos'):
                respuesta['formulas_avisos'] = _fe['avisos']
            if accion == 'validar' and aviso_consentimiento:
                respuesta['aviso_consentimiento'] = aviso_consentimiento
                respuesta['mensaje'] += f' (Aviso: {aviso_consentimiento})'
            if accion == 'validar' and pdf_pendiente_pago:
                respuesta['pdf_pendiente_pago'] = True
                respuesta['codigo_pdf'] = 'SALDO_PENDIENTE_PDF'
                if saldo_pdf_pendiente is not None:
                    respuesta['saldo_pendiente'] = saldo_pdf_pendiente
                respuesta['mensaje'] = (
                    f"{respuesta['mensaje']} El PDF oficial quedará disponible al liquidar el saldo en recepción."
                ).strip()

            return {'http_status': 200, 'body': respuesta}

        except OrdenDeServicio.DoesNotExist:
            return {
                'http_status': 404,
                'body': {'status': 'error', 'mensaje': 'Orden no encontrada'},
            }
        except Exception as e:
            import traceback

            error_detail = traceback.format_exc()
            _u = usuario_efectivo if usuario_efectivo is not None else request.user
            try:
                logger_core.error(
                    'FALLO AL GUARDAR RESULTADOS (LABORATORIO) - '
                    'Usuario: %s (ID: %s) - Orden ID: %s - Error: %s - Tipo: %s - Traceback: %s - Empresa: %s',
                    getattr(_u, 'username', '?'),
                    getattr(_u, 'id', None),
                    orden_id,
                    str(e),
                    type(e).__name__,
                    error_detail[:500],
                    empresa.nombre,
                )
            except Exception as log_error:
                logger_core.error(
                    'guardar_resultados: error secundario al registrar el error principal: %s',
                    log_error,
                )
            return {
                'http_status': 500,
                'body': {'status': 'error', 'mensaje': f'Error inesperado: {str(e)}'},
            }

    @staticmethod
    def bulk_validar_por_ids(request, empresa, ids):
        """
        Marca ResultadoParametro como validados por lista de PKs (misma regla de empresa).
        ids: lista de int.
        Devuelve {'http_status', 'body'}.
        """
        rol = (getattr(request.user, 'rol', '') or '').upper().strip()
        puede_validar = (
            rol in ('QUIMICO', 'LABORATORIO', 'ADMIN', 'ADMINISTRADOR')
            or request.user.is_superuser
            or request.user.is_staff
        )
        if not puede_validar:
            return {
                'http_status': 403,
                'body': {'status': 'error', 'mensaje': 'Sin permisos para validar resultados'},
            }

        if not ids:
            return {
                'http_status': 400,
                'body': {'status': 'error', 'mensaje': 'No se recibieron IDs'},
            }

        ahora = timezone.now()
        with transaction.atomic():
            base_qs = ResultadoParametro.objects.filter(
                id__in=ids,
                orden__empresa=empresa,
                validado=False,
            )
            orden_ids = list(
                base_qs.order_by('orden_id')
                .values_list('orden_id', flat=True)
                .distinct()
            )
            actualizados = base_qs.update(
                validado=True,
                validado_por=request.user,
                fecha_validacion=ahora,
            )

            if actualizados > 0:
                fallos = []
                for oid in set(orden_ids):
                    orden = OrdenDeServicio.objects.select_related('paciente').prefetch_related(
                        'resultados',
                    ).get(pk=oid, empresa=empresa)
                    ok_llave, errs_llave = validar_triple_llave(orden)
                    if not ok_llave:
                        fallos.append(
                            {
                                'orden_id': oid,
                                'folio': getattr(orden, 'folio_orden', None),
                                'errores': errs_llave,
                            }
                        )
                if fallos:
                    raise BusinessApiError(
                        'TRIPLE_LLAVE',
                        (
                            'La validación masiva fue rechazada: una o más órdenes no cumplen '
                            'requisitos financieros o clínicos (triple llave).'
                        ),
                        detail={'fallos': fallos},
                        status_code=400,
                    )

        return {
            'http_status': 200,
            'body': {
                'status': 'ok',
                'actualizados': actualizados,
                'mensaje': f'{actualizados} resultado(s) validado(s) correctamente',
            },
        }
