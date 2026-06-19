from __future__ import annotations

import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from core.models import OrdenDeServicio, Paciente
from .models import CampanaMarketing, CuponMarketing, CuponUso
from .utils import generar_codigo_cupon, generar_cupon_imagen_jpg


@login_required
def dashboard_marketing(request):
    try:
        empresa = getattr(request.user, "empresa", None)
        
        if not empresa:
            from django.contrib import messages
            messages.error(request, 'Usuario no tiene empresa asignada.')
            from django.shortcuts import redirect
            return redirect('home')
        
        try:
            campanas = CampanaMarketing.objects.filter(empresa=empresa).order_by("-fecha_creacion")[:50]
            cupones = CuponMarketing.objects.filter(empresa=empresa).order_by("-fecha_creacion")[:50]
            pacientes = Paciente.objects.filter(empresa=empresa).order_by("nombre_completo")[:200]
        except Exception as e:
            import logging
            logger = logging.getLogger('marketing')
            logger.error(f"Error en consultas de dashboard_marketing: {str(e)}", exc_info=True)
            campanas = CampanaMarketing.objects.none()
            cupones = CuponMarketing.objects.none()
            pacientes = Paciente.objects.none()
        
        return render(
            request,
            "marketing/dashboard_marketing.html",
            {"campanas": campanas, "cupones": cupones, "pacientes": pacientes, "empresa": empresa},
        )
    except Exception as e:
        import logging
        logger = logging.getLogger('marketing')
        logger.critical(f"CRITICAL ERROR in dashboard_marketing view: {str(e)}", exc_info=True)
        return render(request, "core/error_500.html", {"message": "Error crítico en módulo de Marketing. Contacte a soporte."}, status=500)


@login_required
@require_http_methods(["POST"])
def api_generar_cupon(request):
    empresa = getattr(request.user, "empresa", None)
    sucursal = getattr(request.user, "sucursal", None)
    paciente_id = request.POST.get("paciente_id")
    porcentaje = (request.POST.get("porcentaje") or "0").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()

    try:
        porcentaje_dec = Decimal(porcentaje)
    except Exception:
        porcentaje_dec = Decimal("0.00")

    paciente = None
    if paciente_id:
        paciente = Paciente.objects.filter(id=paciente_id, empresa=empresa).first()

    codigo = generar_codigo_cupon()
    payload = f"PRISVALLE|EMPRESA:{getattr(empresa, 'id', 'NA')}|CUPON:{codigo}|PCT:{porcentaje_dec}"

    ruta_rel = generar_cupon_imagen_jpg(
        empresa_nombre=getattr(empresa, "nombre", "PRISLAB"),
        paciente_nombre=getattr(paciente, "nombre_completo", "") if paciente else "",
        payload_qr=payload,
    )

    cupon = CuponMarketing.objects.create(
        empresa=empresa,
        sucursal=sucursal,
        paciente=paciente,
        codigo=codigo,
        porcentaje_descuento=porcentaje_dec,
        descripcion=descripcion or None,
        creado_por=request.user,
        imagen=ruta_rel,
    )

    return JsonResponse(
        {"ok": True, "codigo": cupon.codigo, "imagen": cupon.imagen.url if cupon.imagen else None}
    )


@login_required
@require_http_methods(["POST"])
def api_crear_campana(request):
    empresa = getattr(request.user, "empresa", None)
    sucursal = getattr(request.user, "sucursal", None)
    segmento = (request.POST.get("segmento") or "").strip()
    mensaje = (request.POST.get("mensaje") or "").strip()

    if not segmento or not mensaje:
        return JsonResponse({"ok": False, "error": "Segmento y mensaje son obligatorios."}, status=400)

    c = CampanaMarketing.objects.create(
        empresa=empresa,
        sucursal=sucursal,
        segmento=segmento,
        mensaje_whatsapp=mensaje,
        creado_por=request.user,
    )
    return JsonResponse({"ok": True, "id": c.id})


@login_required
@require_http_methods(["POST"])
def api_aplicar_cupon(request):
    """
    Registra uso de cupón (paciente + orden). Mitiga dobles clics vía Idempotency-Key.
    El PDV con venta registra el uso en farmacia.services.venta_farmacia_service (misma clave).
    """
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        return JsonResponse({"status": "error", "mensaje": "Sin empresa"}, status=403)

    idem = (request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY") or "").strip()
    if len(idem) < 8:
        return JsonResponse(
            {
                "status": "error",
                "mensaje": "Encabezado Idempotency-Key es obligatorio (mínimo 8 caracteres).",
            },
            status=400,
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "mensaje": "JSON inválido"}, status=400)

    codigo = (data.get("codigo") or "").strip().upper()
    paciente_id = data.get("paciente_id")
    orden_id = data.get("orden_id")

    if not codigo:
        return JsonResponse({"status": "error", "mensaje": "código de cupón requerido"}, status=400)

    existente = CuponUso.objects.filter(idempotency_key=idem[:128]).first()
    if existente:
        return JsonResponse(
            {
                "status": "success",
                "reintento": True,
                "cupon_uso_id": existente.id,
                "cupon_id": existente.cupon_id,
            }
        )

    cupon = CuponMarketing.objects.filter(empresa=empresa, codigo=codigo).first()
    if not cupon:
        return JsonResponse({"status": "error", "mensaje": "Cupón no encontrado"}, status=404)

    paciente = None
    if paciente_id:
        paciente = Paciente.objects.filter(id=paciente_id, empresa=empresa).first()
        if not paciente:
            return JsonResponse({"status": "error", "mensaje": "Paciente inválido"}, status=400)

    if not orden_id:
        return JsonResponse(
            {"status": "error", "mensaje": "orden_id es obligatorio para este endpoint."},
            status=400,
        )

    orden = OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa).first()
    if not orden:
        return JsonResponse({"status": "error", "mensaje": "Orden inválida"}, status=400)

    if paciente and orden.paciente_id != paciente.id:
        return JsonResponse(
            {"status": "error", "mensaje": "La orden no corresponde al paciente"},
            status=400,
        )
    if not paciente:
        paciente = orden.paciente

    try:
        with transaction.atomic():
            uso = CuponUso.objects.create(
                empresa=empresa,
                cupon=cupon,
                paciente=paciente,
                orden=orden,
                venta=None,
                idempotency_key=idem[:128],
            )
    except IntegrityError:
        prev = CuponUso.objects.filter(idempotency_key=idem[:128]).first()
        if prev:
            return JsonResponse(
                {
                    "status": "success",
                    "reintento": True,
                    "cupon_uso_id": prev.id,
                    "cupon_id": prev.cupon_id,
                }
            )
        return JsonResponse(
            {"status": "error", "mensaje": "Cupón ya aplicado a esta orden o paciente"},
            status=409,
        )

    return JsonResponse(
        {
            "status": "success",
            "cupon_uso_id": uso.id,
            "codigo": cupon.codigo,
            "porcentaje_descuento": float(cupon.porcentaje_descuento),
        }
    )


@login_required
def entrenamiento_ia(request):
    """
    Acceso directo a Academy / simulaciones.
    MVP: pantalla de aterrizaje; el roleplay completo se conecta desde core/ai_brain.py.
    """
    empresa = getattr(request.user, "empresa", None)
    return render(request, "marketing/entrenamiento_ia.html", {"empresa": empresa})


# ==================== CAMPAÑAS ====================

@login_required
def lista_campanas(request):
    """Lista de todas las campañas de marketing."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    
    # Filtros
    estado = request.GET.get('estado', 'todas')
    tipo = request.GET.get('tipo', 'todos')
    
    campanas = CampanaMarketing.objects.filter(empresa=empresa)
    
    if estado == 'activas':
        campanas = campanas.filter(activa=True)
    elif estado == 'inactivas':
        campanas = campanas.filter(activa=False)
    
    if tipo != 'todos':
        campanas = campanas.filter(segmento=tipo)
    
    campanas = campanas.order_by('-fecha_creacion')[:100]
    
    return render(request, "marketing/campanas/lista.html", {
        "campanas": campanas,
        "empresa": empresa,
        "filtro_estado": estado,
        "filtro_tipo": tipo,
    })


@login_required
def crear_campana(request):
    """Crear nueva campaña de marketing."""
    from django.contrib import messages
    from django.shortcuts import redirect
    
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        segmento = request.POST.get('segmento', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        canal = request.POST.get('canal', 'whatsapp')
        
        if not nombre or not segmento or not mensaje:
            messages.error(request, 'Nombre, segmento y mensaje son obligatorios.')
        else:
            campana = CampanaMarketing.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, "sucursal", None),
                nombre=nombre,
                segmento=segmento,
                mensaje_whatsapp=mensaje,
                canal_comunicacion=canal,
                creado_por=request.user,
                activa=True,
            )
            messages.success(request, f'Campaña "{campana.nombre}" creada exitosamente.')
            return redirect('marketing:lista_campanas')
    
    # Obtener segmentos disponibles
    segmentos = ['Todos', 'Diabéticos', 'Hipertensos', 'Pediatría', 'Adultos Mayores', 'VIP']
    canales = ['whatsapp', 'email', 'sms']
    
    return render(request, "marketing/campanas/crear.html", {
        "empresa": empresa,
        "segmentos": segmentos,
        "canales": canales,
    })


@login_required
def editar_campana(request, campana_id):
    """Editar una campaña de marketing existente."""
    from django.contrib import messages
    from django.shortcuts import redirect, get_object_or_404

    empresa = getattr(request.user, "empresa", None)
    campana = get_object_or_404(CampanaMarketing, id=campana_id, empresa=empresa)

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        segmento = request.POST.get('segmento', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        canal = request.POST.get('canal', campana.canal_comunicacion)

        if not nombre or not segmento or not mensaje:
            messages.error(request, 'Nombre, segmento y mensaje son obligatorios.')
        else:
            campana.nombre = nombre
            campana.segmento = segmento
            campana.mensaje_whatsapp = mensaje
            campana.canal_comunicacion = canal
            campana.activa = request.POST.get('activa') == 'on'
            campana.save(update_fields=['nombre', 'segmento', 'mensaje_whatsapp', 'canal_comunicacion', 'activa'])
            messages.success(request, f'Campaña "{campana.nombre}" actualizada exitosamente.')
            return redirect('marketing:lista_campanas')

    segmentos = ['Todos', 'Diabéticos', 'Hipertensos', 'Pediatría', 'Adultos Mayores', 'VIP']
    canales = ['whatsapp', 'email', 'sms']

    return render(request, "marketing/campanas/crear.html", {
        "empresa": empresa,
        "campana": campana,
        "segmentos": segmentos,
        "canales": canales,
        "editar": True,
    })


@login_required
def dashboard_campanas(request):
    """Dashboard con métricas de campañas."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    
    campanas = CampanaMarketing.objects.filter(empresa=empresa).order_by('-fecha_creacion')[:10]
    
    # Métricas
    total_campanas = CampanaMarketing.objects.filter(empresa=empresa).count()
    campanas_activas = CampanaMarketing.objects.filter(empresa=empresa, activa=True).count()
    
    # Métricas reales por campaña: se cruzan con CuponMarketing para estimar alcance
    # y con OrdenDeServicio para estimar conversiones post-campaña (7 días)
    from django.utils import timezone
    from datetime import timedelta
    campanas_data = []
    for c in campanas:
        # Cupones asociados al segmento de esta campaña → proxy de "enviados"
        enviados = CuponMarketing.objects.filter(
            empresa=empresa,
            descripcion__icontains=c.segmento[:20] if c.segmento else '',
        ).count() if c.segmento else 0

        # Cupones usados (tienen paciente asignado) → proxy de "abiertos"
        abiertos = CuponMarketing.objects.filter(
            empresa=empresa,
            descripcion__icontains=c.segmento[:20] if c.segmento else '',
            paciente__isnull=False,
        ).count() if c.segmento else 0

        # Órdenes creadas en los 7 días siguientes a la campaña → proxy de "conversiones"
        from core.models import OrdenDeServicio
        conversiones = 0
        try:
            ventana_fin = c.fecha_creacion + timedelta(days=7)
            conversiones = OrdenDeServicio.objects.filter(
                empresa=empresa,
                fecha_creacion__gte=c.fecha_creacion,
                fecha_creacion__lte=ventana_fin,
            ).values('paciente_id').distinct().count()
        except Exception:
            pass

        campanas_data.append({
            'nombre': c.nombre or c.segmento,
            'canal': c.canal_comunicacion,
            'enviados': enviados,
            'abiertos': abiertos,
            'conversiones': conversiones,
            'fecha': c.fecha_creacion.strftime('%d/%m/%Y') if c.fecha_creacion else '',
        })
    
    return render(request, "marketing/campanas/dashboard.html", {
        "campanas": campanas,
        "empresa": empresa,
        "total_campanas": total_campanas,
        "campanas_activas": campanas_activas,
        "campanas_data": campanas_data,
    })


# ==================== CUPONES ====================

@login_required
def lista_cupones(request):
    """Lista de todos los cupones."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    
    # Filtros
    estado = request.GET.get('estado', 'todos')
    
    cupones = CuponMarketing.objects.filter(empresa=empresa)
    
    if estado == 'activos':
        cupones = cupones.filter(usos__isnull=True)
    elif estado == 'usados':
        cupones = cupones.filter(usos__isnull=False).distinct()
    
    cupones = cupones.order_by('-fecha_creacion')[:100]
    
    return render(request, "marketing/cupones/lista.html", {
        "cupones": cupones,
        "empresa": empresa,
        "filtro_estado": estado,
    })


@login_required
def generar_cupon(request):
    """Generar nuevo cupón de descuento."""
    from django.contrib import messages
    from django.shortcuts import redirect
    
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    if request.method == 'POST':
        paciente_id = request.POST.get('paciente_id')
        porcentaje = request.POST.get('porcentaje', '0').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        cantidad = int(request.POST.get('cantidad', 1))
        
        try:
            porcentaje_dec = Decimal(str(porcentaje))
            if porcentaje_dec <= 0 or porcentaje_dec > 100:
                raise ValueError("Porcentaje inválido")
        except (ValueError, Exception):
            messages.error(request, 'Porcentaje debe ser entre 1 y 100.')
            return redirect('marketing:generar_cupon')
        
        # Generar cupones
        cupones_creados = []
        for _ in range(cantidad):
            paciente = None
            if paciente_id:
                paciente = Paciente.objects.filter(id=paciente_id, empresa=empresa).first()
            
            codigo = generar_codigo_cupon()
            payload = f"PRISVALLE|EMPRESA:{empresa.id}|CUPON:{codigo}|PCT:{porcentaje_dec}"
            
            ruta_rel = generar_cupon_imagen_jpg(
                empresa_nombre=empresa.nombre,
                paciente_nombre=paciente.nombre_completo if paciente else "",
                payload_qr=payload,
            )
            
            cupon = CuponMarketing.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, "sucursal", None),
                paciente=paciente,
                codigo=codigo,
                porcentaje_descuento=porcentaje_dec,
                descripcion=descripcion or None,
                creado_por=request.user,
                imagen=ruta_rel,
            )
            cupones_creados.append(cupon)
        
        messages.success(request, f'{cantidad} cupón(es) generado(s) exitosamente.')
        return redirect('marketing:lista_cupones')
    
    # GET: mostrar formulario
    pacientes = Paciente.objects.filter(empresa=empresa).order_by('nombre_completo')[:200]
    
    return render(request, "marketing/cupones/generar.html", {
        "empresa": empresa,
        "pacientes": pacientes,
    })


# ==================== CONTACTOS ====================

@login_required
def lista_contactos(request):
    """Lista de contactos/leads."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    
    # Por ahora mostramos pacientes como contactos
    busqueda = request.GET.get('q', '').strip()
    segmento = request.GET.get('segmento', 'todos')
    
    contactos = Paciente.objects.filter(empresa=empresa)
    
    if busqueda:
        contactos = contactos.filter(nombre_completo__icontains=busqueda)
    
    contactos = contactos.order_by('nombre_completo')[:200]
    
    return render(request, "marketing/contactos/lista.html", {
        "contactos": contactos,
        "empresa": empresa,
        "busqueda": busqueda,
        "segmento": segmento,
    })


@login_required
def importar_contactos(request):
    """Importar contactos desde CSV/Excel."""
    from django.contrib import messages
    from django.shortcuts import redirect
    
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        
        # Validar extensión
        if not archivo.name.endswith(('.csv', '.xlsx', '.xls')):
            messages.error(request, 'Solo se permiten archivos CSV o Excel.')
            return redirect('marketing:importar_contactos')
        
        try:
            import csv
            import io
            
            # Leer archivo CSV
            decoded_file = archivo.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            contactos_importados = 0
            for row in reader:
                nombre = row.get('nombre', '').strip()
                telefono = row.get('telefono', '').strip()
                email = row.get('email', '').strip()
                
                if nombre:
                    # Crear o actualizar paciente
                    Paciente.objects.get_or_create(
                        empresa=empresa,
                        nombre_completo=nombre,
                        defaults={
                            'telefono': telefono,
                            'email': email,
                        }
                    )
                    contactos_importados += 1
            
            messages.success(request, f'{contactos_importados} contacto(s) importado(s) exitosamente.')
            return redirect('marketing:lista_contactos')
            
        except Exception as e:
            messages.error(request, f'Error al importar: {str(e)}')
            return redirect('marketing:importar_contactos')
    
    return render(request, "marketing/contactos/importar.html", {
        "empresa": empresa,
    })


# ==================== IA DE REACTIVACIÓN ================================

@login_required
@require_http_methods(["GET"])
def api_detectar_pacientes_inactivos(request):
    """
    PRIS Marketing IA — Detecta pacientes crónicos que no han tenido
    actividad en los últimos N meses (default: 6).
    Segmentos soportados: diabeticos, hipertensos, renales, cardiaco, todos.

    Retorna lista de pacientes con teléfono, último estudio y enlace WhatsApp pre-generado.
    """
    import logging
    from datetime import timedelta
    from django.utils import timezone
    from core.models import Paciente, OrdenDeServicio
    from core.utils.whatsapp_sender import generar_enlace_whatsapp

    logger = logging.getLogger('marketing')
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Sin empresa'}, status=400)

    meses = int(request.GET.get('meses', 6))
    segmento = request.GET.get('segmento', 'diabeticos').lower()

    fecha_corte = timezone.now() - timedelta(days=meses * 30)

    # Palabras clave por segmento para buscar en estudios
    PALABRAS_CLAVE = {
        'diabeticos': ['glucosa', 'hba1c', 'hemoglobina glucosilada', 'diabetes', 'curva de glucosa'],
        'hipertensos': ['electrolitos', 'sodio', 'potasio', 'creatinina', 'urea', 'hipertension'],
        'renales': ['creatinina', 'urea', 'depuracion', 'aclaramiento', 'renal'],
        'cardiaco': ['troponina', 'ck-mb', 'bnp', 'dhl', 'cardiaco'],
        'todos': [],
    }
    claves = PALABRAS_CLAVE.get(segmento, PALABRAS_CLAVE['diabeticos'])

    try:
        # 1. Obtener pacientes con órdenes de los estudios clave (en cualquier momento)
        if claves:
            from core.models import DetalleOrden
            from django.db.models import Q
            q = Q()
            for c in claves:
                q |= Q(analito__nombre__icontains=c)
            pacientes_ids_cronicos = (
                DetalleOrden.objects.filter(
                    q,
                    orden__empresa=empresa,
                ).values_list('orden__paciente_id', flat=True).distinct()
            )
        else:
            pacientes_ids_cronicos = Paciente.objects.filter(
                empresa=empresa, activo=True
            ).values_list('id', flat=True)

        # 2. De esos, encontrar los que NO tienen órdenes desde fecha_corte
        pacientes_con_actividad_reciente = (
            OrdenDeServicio.objects.filter(
                empresa=empresa,
                paciente_id__in=pacientes_ids_cronicos,
                fecha_creacion__gte=fecha_corte,
            ).values_list('paciente_id', flat=True).distinct()
        )

        pacientes_inactivos = (
            Paciente.objects.filter(
                id__in=pacientes_ids_cronicos,
                empresa=empresa,
                activo=True,
            ).exclude(
                id__in=pacientes_con_actividad_reciente,
            ).select_related()
            .order_by('nombre_completo')[:100]
        )

        resultado = []
        empresa_nombre = getattr(empresa, 'nombre', 'PRISLAB')
        for p in pacientes_inactivos:
            whatsapp = None
            if p.telefono:
                nombre_corto = (p.nombre_completo or '').split()[0] if p.nombre_completo else 'Paciente'
                msg = (
                    f"Hola {nombre_corto} 👋\n\n"
                    f"En *{empresa_nombre}* nos importa tu salud. "
                    f"Han pasado algunos meses desde tu última visita y queremos invitarte "
                    f"a programar tu chequeo de control. 🧬\n\n"
                    f"¿Te gustaría agendar una cita? Escríbenos y con gusto te atendemos. "
                    f"¡Primero tu salud! 💙"
                )
                try:
                    whatsapp = generar_enlace_whatsapp(p.telefono, msg)
                except Exception:
                    pass
            resultado.append({
                'id': p.id,
                'nombre': p.nombre_completo or '',
                'telefono': p.telefono or '',
                'fecha_nacimiento': p.fecha_nacimiento.isoformat() if p.fecha_nacimiento else None,
                'whatsapp': whatsapp,
            })

        return JsonResponse({
            'ok': True,
            'segmento': segmento,
            'meses_inactivo': meses,
            'total': len(resultado),
            'pacientes': resultado,
        })

    except Exception as e:
        logger.error('api_detectar_pacientes_inactivos: %s', e, exc_info=True)
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
def dashboard_reactivacion_ia(request):
    """Vista del dashboard de reactivación con IA."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.shortcuts import redirect
        return redirect('home')
    return render(request, "marketing/reactivacion_ia.html", {
        "empresa": empresa,
        "segmentos": [
            ('diabeticos', 'Diabéticos / Control de Glucosa', '🩸'),
            ('hipertensos', 'Hipertensos / Control Renal', '💊'),
            ('renales', 'Pacientes Renales', '🫘'),
            ('cardiaco', 'Control Cardíaco', '❤️'),
            ('todos', 'Todos los Pacientes Inactivos', '👥'),
        ],
    })
