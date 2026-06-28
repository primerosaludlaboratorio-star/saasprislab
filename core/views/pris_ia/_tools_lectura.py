"""
core/views/pris_ia/_tools_lectura.py

Herramientas de solo lectura de Prisci (búsquedas, consultas, auditoría).
"""

import json
import logging
from datetime import datetime

from django.db import OperationalError
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.timezone import localdate

logger = logging.getLogger('core')


def _tool_buscar_paciente(args, empresa):
    from core.models import Paciente
    nombre = args.get("nombre", "")
    telefono = args.get("telefono", "")
    limite = min(int(args.get("limite", 5)), 10)
    qs = Paciente.objects.filter(empresa=empresa, activo=True)
    if nombre:
        qs = qs.filter(
            Q(nombre_completo__icontains=nombre) |
            Q(apellido_paterno__icontains=nombre) |
            Q(nombres__icontains=nombre)
        )
    if telefono:
        qs = qs.filter(telefono__icontains=telefono)
    qs = qs.order_by('-fecha_registro')[:limite]
    resultados = list(qs)
    return {
        "total": len(resultados),
        "pacientes": [{"id": p.id, "nombre": p.nombre_completo or "",
                       "telefono": p.telefono or "",
                       "fecha_nacimiento": p.fecha_nacimiento.isoformat() if p.fecha_nacimiento else ""} for p in resultados]
    }


def _tool_estadisticas_dia(args, empresa):
    from core.models import OrdenDeServicio, Venta
    fecha_str = args.get("fecha", "")
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else localdate()
    except ValueError:
        fecha = localdate()
    ordenes = OrdenDeServicio.objects.filter(empresa=empresa, fecha_creacion__date=fecha)
    ventas = 0
    try:
        # Venta usa 'fecha' (no fecha_creacion) y estado 'COMPLETADA'
        ventas = Venta.objects.filter(
            empresa=empresa, fecha__date=fecha, estado='COMPLETADA'
        ).aggregate(t=Sum('total'))['t'] or 0
    except (ImportError, LookupError, AttributeError):
        pass
    return {
        "fecha": fecha.isoformat(),
        "ordenes_total": ordenes.count(),
        "ordenes_pendientes": ordenes.filter(estado__in=["PENDIENTE_PAGO", "PAGADO", "EN_PROCESO"]).count(),
        "ordenes_completadas": ordenes.filter(estado__in=["RESULTADOS_LISTOS", "ENTREGADO"]).count(),
        "ventas_farmacia_mxn": float(ventas),
    }


def _tool_buscar_ordenes(args, empresa):
    from core.models import OrdenDeServicio
    folio = args.get("folio", "")
    paciente_nombre = args.get("paciente_nombre", "")
    estado = args.get("estado", "")
    hoy = args.get("hoy", False)
    qs = OrdenDeServicio.objects.filter(empresa=empresa).select_related('paciente')
    if folio:
        qs = qs.filter(folio_orden__icontains=folio)
    if paciente_nombre:
        qs = qs.filter(Q(paciente__nombre_completo__icontains=paciente_nombre) |
                       Q(paciente_nombre_snapshot__icontains=paciente_nombre))
    if estado:
        qs = qs.filter(estado=estado.upper())
    if hoy:
        qs = qs.filter(fecha_creacion__date=localdate())
    qs = qs.order_by('-fecha_creacion')[:10]
    return {
        "total": qs.count(),
        "ordenes": [{"id": o.id, "folio": o.folio_orden,
                     "paciente": o.paciente.nombre_completo if o.paciente else (o.paciente_nombre_snapshot or ""),
                     "estado": o.estado,
                     "fecha": timezone.localtime(o.fecha_creacion).strftime("%d/%m/%Y %H:%M"),
                     "total": float(o.total or 0)} for o in qs]
    }


def _tool_resultados_orden(args, empresa):
    from core.models import OrdenDeServicio, DetalleOrden, ResultadoParametro
    folio = args.get("folio", "")
    try:
        orden = OrdenDeServicio.objects.filter(empresa=empresa).filter(
            Q(folio_orden=folio) | Q(folio_orden__icontains=folio)).first()
        if not orden:
            return {"error": f"No se encontró la orden '{folio}'"}
        detalles = DetalleOrden.objects.filter(orden=orden).select_related(
            'analito', 'perfil_lims', 'paquete_lims',
        )
        estudios = []
        for d in detalles:
            label = (
                d.descripcion_linea
                or (d.analito.nombre if d.analito_id else '')
                or (d.perfil_lims.nombre if d.perfil_lims_id else '')
                or (d.paquete_lims.nombre if d.paquete_lims_id else '')
                or ''
            )
            params = []
            if d.analito_id:
                for rp in ResultadoParametro.objects.filter(
                    orden=orden, analito=d.analito,
                ).select_related('analito'):
                    params.append({
                        "parametro": rp.analito.nombre if rp.analito else "",
                        "valor": str(rp.valor or ""),
                        "unidades": (rp.analito.unidades if rp.analito else "") or "",
                        "validado": rp.validado,
                    })
            estudios.append({
                "estudio": label,
                "estado": d.estado_procesamiento,
                "parametros": params,
            })
        return {"folio": orden.folio_orden,
                "paciente": orden.paciente.nombre_completo if orden.paciente else "",
                "estado": orden.estado, "estudios": estudios}
    except (LookupError, AttributeError, ValueError) as e:
        return {"error": str(e)}


def _tool_guardar_resultado(args, empresa, user):
    from django.db import IntegrityError
    from core.models import OrdenDeServicio, ResultadoParametro, DetalleOrden
    from core.services.ia_clinical_governance import METODO_IA_BORRADOR, defaults_resultado_ia_borrador
    from lims.models import Analito
    folio = args.get("folio_orden", "")
    nombre_param = args.get("nombre_parametro", "")
    valor = args.get("valor", "")
    try:
        orden = OrdenDeServicio.objects.filter(empresa=empresa, folio_orden__icontains=folio).first()
        if not orden:
            return {"error": f"Orden '{folio}' no encontrada"}
        analitos_ids = list(
            DetalleOrden.objects.filter(orden=orden, analito__isnull=False).values_list(
                'analito_id', flat=True,
            )
        )
        analito = Analito.objects.filter(id__in=analitos_ids).filter(
            Q(nombre__icontains=nombre_param)
            | Q(codigo__icontains=nombre_param)
            | Q(abreviatura__icontains=nombre_param)
        ).first()
        if not analito:
            return {"error": f"Analito '{nombre_param}' no encontrado en orden '{folio}'"}
        if getattr(analito, "es_calculado", False):
            return {
                "error": (
                    f"El analito '{analito.abreviatura}' es calculado por fórmula; "
                    "debe capturarse vía laboratorio (motor clínico), no por voz."
                )
            }
        _ia_def = defaults_resultado_ia_borrador()
        rp, created = ResultadoParametro.objects.get_or_create(
            orden=orden,
            analito=analito,
            defaults={
                'valor': valor,
                'capturado_por': user,
                **_ia_def,
            },
        )
        if not created:
            rp.valor = valor
            rp.capturado_por = user
            rp.metodo_captura = METODO_IA_BORRADOR
            rp.validado = False
            rp.aprobado_por_humano = False
            rp.validado_por = None
            rp.fecha_validacion = None
            rp.save(
                update_fields=[
                    'valor', 'capturado_por', 'metodo_captura', 'validado',
                    'aprobado_por_humano', 'validado_por', 'fecha_validacion',
                ]
            )
        return {
            "exito": True,
            "accion": "creado" if created else "actualizado",
            "parametro": analito.nombre,
            "valor": valor,
            "unidades": analito.unidades or "",
            "aprobado_por_humano": False,
            "metodo_captura": METODO_IA_BORRADOR,
            "aviso_etico": (
                "Borrador IA: el QFB debe revisar y pulsar Validar en captura; "
                "la IA no libera resultados clínicos."
            ),
        }
    except (LookupError, IntegrityError, ValueError) as e:
        return {"error": str(e)}


def _tool_buscar_medicamento(args, empresa):
    from core.models import Producto
    nombre = args.get("nombre", "")
    # Producto no tiene campo 'activo', se filtra solo por empresa y nombre/sustancia
    qs = Producto.objects.filter(empresa=empresa).filter(
        Q(nombre__icontains=nombre) | Q(sustancia_activa__icontains=nombre)
    ).order_by('nombre')[:8]
    resultados = list(qs)
    return {"total": len(resultados),
            "medicamentos": [{"id": p.id, "nombre": p.nombre,
                               "sustancia": p.sustancia_activa or "",
                               "presentacion": p.presentacion or "",
                               "concentracion": p.concentracion or "",
                               "precio": float(p.precio_publico or 0),
                               "stock": p.stock or 0} for p in resultados]}


def _tool_buscar_estudio(args, empresa):
    from lims.models import Analito, ValorReferenciaAnalito
    nombre = args.get("nombre", "")
    if not nombre:
        return {"error": "Especifica el nombre del estudio a buscar (ej: 'Glucosa', 'BH')."}

    qs = Analito.objects.filter(activo=True, empresa=empresa).filter(
        Q(nombre__icontains=nombre) | Q(codigo__icontains=nombre) |
        Q(abreviatura__icontains=nombre)
    ).prefetch_related('rangos').order_by('nombre')[:8]

    resultados = list(qs)
    if not resultados:
        return {"total": 0, "estudios": [],
                "sugerencia": f"No encontré estudios con '{nombre}'. Verifica el nombre o usa términos como 'glucosa', 'BH', 'QS'."}

    estudios_out = []
    for e in resultados:
        rangos_resumen = []
        try:
            for rango in e.rangos.filter(sexo='A').order_by('edad_minima')[:5]:
                rangos_resumen.append({
                    "parametro": e.nombre,
                    "min": float(rango.ref_minimo) if rango.ref_minimo is not None else None,
                    "max": float(rango.ref_maximo) if rango.ref_maximo is not None else None,
                    "unidad": rango.texto_referencia or e.unidades or "",
                })
        except (LookupError, AttributeError):
            pass

        estudios_out.append({
            "id": e.id,
            "nombre": e.nombre,
            "codigo": e.codigo or "",
            "abreviatura": e.abreviatura or "",
            "precio": float(e.costo_lista or 0),
            "muestra": e.tipo_muestra or "Suero",
            "tubo": "",
            "indicaciones": e.indicaciones or "",
            "dias_entrega": "1",
            "es_perfil": False,
            "rangos_referencia": rangos_resumen,
        })

    return {"total": len(estudios_out), "estudios": estudios_out}


def _tool_saldo_caja(args, empresa, user):
    from core.models import Venta
    hoy = localdate()
    # Venta usa campo 'fecha' (DateTimeField) y estado 'COMPLETADA'
    ventas = Venta.objects.filter(empresa=empresa, fecha__date=hoy, estado='COMPLETADA')
    total = ventas.aggregate(t=Sum('total'))['t'] or 0
    return {"fecha": hoy.isoformat(), "total_ventas": float(total),
            "numero_ventas": ventas.count()}


def _tool_ordenes_pendientes(args, empresa):
    from core.models import OrdenDeServicio
    area = args.get("area", "")
    limite = min(int(args.get("limite", 10)), 20)
    # Todos los estados que aún no están entregados ni cancelados
    qs = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado__in=["PENDIENTE_PAGO", "PAGADO", "EN_PROCESO", "RESULTADOS_LISTOS"]
    ).select_related('paciente').order_by('fecha_creacion')
    if area:
        qs = qs.filter(detalles__analito__departamento__icontains=area).distinct()
    resultados = list(qs[:limite])
    return {
        "total": len(resultados),
        "pendientes": [{"folio": o.folio_orden,
                        "paciente": o.paciente.nombre_completo if o.paciente else (o.paciente_nombre_snapshot or ""),
                        "estado": o.get_estado_display() if hasattr(o, 'get_estado_display') else o.estado,
                        "hora": timezone.localtime(o.fecha_creacion).strftime("%H:%M")} for o in resultados]
    }


def _tool_consultar_inventario(args, empresa):
    """Consulta stock de productos por nombre, sustancia o categoría."""
    from django.db.models import Sum as DjSum
    from core.models import Producto
    nombre = args.get("producto", args.get("nombre", ""))
    sucursal = args.get("sucursal", "")  # reservado para multi-sucursal
    limite = min(int(args.get("limite", 10)), 20)
    qs = Producto.objects.filter(empresa=empresa)
    if nombre:
        qs = qs.filter(
            Q(nombre__icontains=nombre) |
            Q(sustancia_activa__icontains=nombre) |
            Q(categoria__nombre__icontains=nombre)
        )
    qs = qs.order_by('nombre')[:limite]
    items = []
    for p in qs:
        # Stock real desde lotes
        try:
            from farmacia.models import Lote
            stock_lotes = Lote.objects.filter(producto=p, cantidad__gt=0).aggregate(
                total=DjSum('cantidad'))['total'] or 0
        except (ImportError, LookupError, AttributeError):
            stock_lotes = p.stock or 0
        items.append({
            "id": p.id,
            "nombre": p.nombre,
            "sustancia": p.sustancia_activa or "",
            "presentacion": p.presentacion or "",
            "precio_publico": float(p.precio_publico or 0),
            "precio_compra": float(p.precio_compra or 0),
            "stock": int(stock_lotes),
        })
    return {"total": len(items), "productos": items}


def _tool_auditar_errores_recientes(args, empresa):
    """Escanea los últimos errores del sistema Sentinel y da un diagnóstico."""
    modulo = args.get("modulo", "")
    limite = min(int(args.get("limite", 10)), 30)
    try:
        from consultorio.models import IncidenciaSentinel
        qs = IncidenciaSentinel.objects.filter(
            estado__in=["PENDIENTE", "EN_REPARACION"]
        )
        if empresa:
            qs = qs.filter(empresa=empresa)
        if modulo:
            qs = qs.filter(
                Q(url_afectada__icontains=modulo) |
                Q(namespace__icontains=modulo)
            )
        qs = qs.order_by('-fecha_creacion')[:limite]
        errores = []
        for inc in qs:
            errores.append({
                "id": inc.id,
                "fecha": timezone.localtime(inc.fecha_creacion).strftime("%d/%m %H:%M") if inc.fecha_creacion else "",
                "tipo": inc.tipo_excepcion or "Desconocido",
                "url": (inc.url_afectada or "")[:120],
                "severidad": inc.severidad,
                "resumen": (inc.resumen_para_director or inc.tipo_excepcion or "")[:200],
            })
        criticos = sum(1 for e in errores if e["severidad"] == "CRITICA")
        return {
            "total_pendientes": len(errores),
            "criticos": criticos,
            "errores": errores,
            "diagnostico": (
                f"Hay {len(errores)} incidencias pendientes, {criticos} críticas."
                if errores else "No hay errores pendientes. Sistema limpio."
            ),
        }
    except (ImportError, LookupError, OperationalError) as e:
        return {"error": str(e)}


def _tool_generar_corte_caja(args, empresa, user):
    """Genera un resumen de corte de caja del día (o fecha indicada)."""
    from core.models import Venta
    fecha_str = args.get("fecha", "")
    try:
        from datetime import datetime as _dt
        fecha = _dt.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else localdate()
    except ValueError:
        fecha = localdate()

    qs = Venta.objects.filter(empresa=empresa, fecha__date=fecha, estado="COMPLETADA")
    total_ventas = qs.aggregate(t=Sum('total'))['t'] or 0

    # Desglose por método de pago
    try:
        from django.db.models import Sum as DjSum
        from core.models import Venta as V
        metodos = {}
        for venta in qs:
            for pago in getattr(venta, 'pagos', V.objects.none()).filter(pk__isnull=True):
                mp = getattr(pago, 'metodo_pago', 'OTRO')
                metodos[mp] = metodos.get(mp, 0) + float(getattr(pago, 'monto', 0))
    except (ImportError, AttributeError, LookupError):
        metodos = {}

    # Devoluciones del día
    canceladas = Venta.objects.filter(empresa=empresa, fecha__date=fecha, estado="CANCELADA")
    total_dev = canceladas.aggregate(t=Sum('total'))['t'] or 0

    return {
        "fecha": fecha.isoformat(),
        "total_ventas": float(total_ventas),
        "num_ventas": qs.count(),
        "total_devoluciones": float(total_dev),
        "neto": float(total_ventas - total_dev),
        "desglose_pago": metodos,
        "generado_por": user.get_full_name() or user.username,
    }


def _tool_auditoria_sistema_completa(args, empresa, user):
    """
    Auditoría completa del sistema: BD, modelos críticos, incidencias, Drive.
    Solo disponible para superusuarios.
    """
    from django.db import connection as _conn
    from django.conf import settings
    reporte = {
        "timestamp": timezone.now().isoformat(),
        "usuario": user.username,
        "checks": {},
    }

    # 1. Conexión BD
    try:
        with _conn.cursor() as c:
            c.execute("SELECT 1")
        reporte["checks"]["base_datos"] = {"ok": True, "msg": "Conexión activa"}
    except (OperationalError, OSError) as e:
        reporte["checks"]["base_datos"] = {"ok": False, "msg": str(e)[:100]}

    # 2. Modelos críticos
    modelos_check = {
        "Pacientes": ("core", "Paciente"),
        "Ordenes": ("core", "OrdenDeServicio"),
        "Productos": ("core", "Producto"),
        "Estudios": ("laboratorio", "Estudio"),
    }
    from django.apps import apps as django_apps
    counts = {}
    for label, (app, model) in modelos_check.items():
        try:
            m = django_apps.get_model(app, model)
            counts[label] = m.objects.count()
        except (LookupError, OperationalError) as e:
            counts[label] = f"ERROR: {e}"
    reporte["checks"]["modelos"] = counts

    # 3. Incidencias Sentinel
    try:
        from consultorio.models import IncidenciaSentinel
        qs_pend = IncidenciaSentinel.objects.filter(
            estado__in=["PENDIENTE", "EN_REPARACION"]
        )
        if empresa:
            qs_pend = qs_pend.filter(empresa=empresa)
        reporte["checks"]["sentinel"] = {
            "ok": qs_pend.count() == 0,
            "pendientes": qs_pend.count(),
            "criticos": qs_pend.filter(severidad="CRITICA").count(),
        }
    except (ImportError, LookupError, OperationalError) as e:
        reporte["checks"]["sentinel"] = {"ok": False, "error": str(e)[:100]}

    # 4. Google Drive
    drive_activo = getattr(settings, '_DRIVE_STORAGE_ACTIVO', False)
    reporte["checks"]["drive"] = {"activo": drive_activo}

    # Veredicto global
    errores = [k for k, v in reporte["checks"].items()
               if isinstance(v, dict) and not v.get("ok", True)]
    reporte["veredicto"] = "SISTEMA OPERATIVO" if not errores else f"ATENCION: {', '.join(errores)}"
    reporte["ok"] = len(errores) == 0
    return reporte


def _resumir_resultado_tool(tool_name, resultado):
    if not isinstance(resultado, dict):
        return "Herramienta ejecutada"
    if resultado.get("denegado_rbac"):
        return f"RBAC denegado: {resultado.get('error', '')}"
    if resultado.get("necesita_confirmacion"):
        return "Pendiente de confirmación del usuario"
    if resultado.get("necesita_aclaracion"):
        return "Necesita aclaración del usuario"
    if resultado.get("aviso"):
        return resultado.get("mensaje", "Aviso generado")
    if resultado.get("error"):
        return f"Error: {resultado['error']}"
    # Herramientas de consulta
    if tool_name == "buscar_paciente":
        return f"{resultado.get('total', 0)} paciente(s) encontrado(s)"
    elif tool_name == "obtener_estadisticas_dia":
        return (f"Hoy: {resultado.get('ordenes_total', 0)} ordenes, "
                f"{resultado.get('ordenes_pendientes', 0)} pendientes, "
                f"${resultado.get('ventas_farmacia_mxn', 0):.2f} en farmacia")
    elif tool_name == "buscar_ordenes":
        return f"{resultado.get('total', 0)} orden(es) encontrada(s)"
    elif tool_name in ("guardar_resultado", "actualizar_resultado_laboratorio"):
        return f"Guardado: {resultado.get('parametro')} = {resultado.get('valor')}" if resultado.get("exito") else "No guardado"
    elif tool_name == "obtener_saldo_caja":
        return f"Ventas hoy: ${resultado.get('total_ventas', 0):.2f} ({resultado.get('numero_ventas', 0)} tickets)"
    elif tool_name == "listar_ordenes_pendientes":
        return f"{resultado.get('total', 0)} orden(es) pendiente(s)"
    elif tool_name == "consultar_inventario":
        return f"{resultado.get('total', 0)} producto(s) encontrado(s) en inventario"
    elif tool_name == "auditar_errores_recientes":
        return resultado.get("diagnostico", "Auditoria ejecutada")
    elif tool_name == "generar_corte_caja":
        return (f"Corte {resultado.get('fecha', '')}: "
                f"${resultado.get('total_ventas', 0):.2f} ventas, "
                f"neto ${resultado.get('neto', 0):.2f}")
    elif tool_name == "auditoria_sistema_completa":
        return resultado.get("veredicto", "Auditoria ejecutada")
    # Herramientas operativas
    elif tool_name == "crear_paciente":
        return resultado.get("mensaje", "Paciente creado" if resultado.get("exito") else "Error al crear paciente")
    elif tool_name == "crear_orden_laboratorio":
        return resultado.get("mensaje", f"Orden {resultado.get('folio_orden', '')} creada" if resultado.get("exito") else "Error al crear orden")
    elif tool_name == "cobrar_orden":
        return resultado.get("mensaje", f"Orden cobrada ${resultado.get('total', 0):.2f}" if resultado.get("exito") else "Error al cobrar")
    elif tool_name == "registrar_venta_farmacia":
        return resultado.get("mensaje", f"Venta ${resultado.get('total', 0):.2f}" if resultado.get("exito") else "Error en venta")
    elif tool_name == "crear_cotizacion":
        return resultado.get("mensaje", f"Cotización #{resultado.get('cotizacion_id', '')} creada" if resultado.get("exito") else "Error al cotizar")
    elif tool_name == "buscar_o_crear_paciente":
        return resultado.get("mensaje", "Paciente procesado")
    elif tool_name == "cancelar_orden":
        return resultado.get("mensaje", "Orden cancelada" if resultado.get("exito") else "Error al cancelar")
    elif tool_name == "analizar_imagen_documento":
        tipo = resultado.get('tipo_documento', 'OTRO')
        prefill = resultado.get('prefill', {})
        sug = resultado.get('sugerencias_negocio', [])
        resumen = f"Documento: {tipo}"
        if prefill.get('nombre_paciente'):
            resumen += f" — Paciente: {prefill['nombre_paciente']}"
        if sug:
            resumen += f" — {len(sug)} sugerencia(s) de perfil"
        return resumen
    elif tool_name == "consultar_expediente_paciente":
        total = resultado.get('total_ordenes', 0)
        nombre = resultado.get('nombre', '')
        return f"Expediente de {nombre}: {total} órdenes totales"
    elif tool_name == "consultar_indicadores_kpi":
        lab = resultado.get('laboratorio', {})
        farm = resultado.get('farmacia', {})
        return (f"KPIs {resultado.get('periodo','')}: "
                f"{lab.get('ordenes_total',0)} órdenes lab, "
                f"${farm.get('ingresos_farmacia',0):.2f} farmacia")
    elif tool_name == "aplicar_descuento_orden":
        return resultado.get("mensaje", f"Descuento aplicado ${resultado.get('descuento_monto',0):.2f}" if resultado.get("exito") else "Error al aplicar descuento")
    elif tool_name == "cambiar_estado_orden":
        return resultado.get("mensaje", f"Estado cambiado a {resultado.get('nuevo_estado','')}" if resultado.get("exito") else "Error al cambiar estado")
    elif tool_name == "programar_cita":
        return resultado.get("mensaje", f"Cita programada el {resultado.get('fecha','')}" if resultado.get("exito") else "Error al programar cita")
    elif tool_name == "enviar_notificacion_paciente":
        return resultado.get("mensaje", f"Notificación {resultado.get('canal','')} enviada" if resultado.get("exito") else "Error al enviar notificación")
    elif tool_name == "modificar_paciente":
        return resultado.get("mensaje", "Paciente modificado" if resultado.get("exito") else "Error al modificar paciente")
    elif tool_name == "gestionar_usuario":
        return resultado.get("mensaje", "Usuario gestionado" if resultado.get("exito") else "Error al gestionar usuario")
    return "Herramienta ejecutada"


def _tool_analizar_imagen_documento(args, empresa, request):
    """
    Capa 4: Clasificación y extracción de documento con el Motor OCR.
    Usa la imagen que ya viene adjunta al request (imagen_b64 en el body).
    """
    try:
        from core.services.ocr_documental import analizar_documento
        imagen_b64 = args.get('imagen_b64', '')
        if not imagen_b64:
            # Intentar obtener del body del request
            try:
                body = json.loads(request.body)
                imagen_b64 = body.get('imagen_b64', '')
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        if not imagen_b64:
            return {'error': 'No se adjuntó imagen para analizar.'}
        resultado = analizar_documento(imagen_b64, empresa=empresa, usuario=request.user)
        return resultado
    except Exception as exc:
        logging.getLogger(__name__).exception("Error inesperado en _tool_analizar_imagen_documento (_tools_lectura.py)")
        # Broad catch intencional: OCR externo puede fallar de múltiples formas.
        return {'error': f'Error en análisis de documento: {exc}'}