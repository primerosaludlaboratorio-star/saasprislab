import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from django.utils import timezone

from core.models import DetalleOrden, Empresa, OrdenDeServicio, Paciente, PagoOrden, Sucursal
from core.models.laboratorio import ResultadoParametro
from lims.models import Analito, PaqueteLims, PerfilLims, PrecioItem, ValorReferenciaAnalito

User = get_user_model()

TAG_STRESS = "[STRESS-PRISLAB-ANUAL]"

NOMBRES = [
    ("Ana", "Martinez", "Rios", "F"),
    ("Carlos", "Hernandez", "Vega", "M"),
    ("Rosa", "Jimenez", "Soto", "F"),
    ("Jorge", "Paredes", "Nunez", "M"),
    ("Fernanda", "Castillo", "Moral", "F"),
    ("Luis", "Garcia", "Morales", "M"),
    ("Daniela", "Torres", "Lopez", "F"),
    ("Miguel", "Romero", "Cruz", "M"),
    ("Patricia", "Flores", "Vargas", "F"),
    ("Oscar", "Mendoza", "Campos", "M"),
]


class Command(BaseCommand):
    help = (
        "Simula una carga operativa intensiva para PRISLAB: crea pacientes persistentes, "
        "órdenes LIMS con estados/pagos/resultados y ejecuta ventas reales de farmacia."
    )

    def add_arguments(self, parser):
        parser.add_argument("--empresa-id", type=int, default=None, help="Empresa objetivo.")
        parser.add_argument("--usuario", type=str, default="", help="Usuario responsable.")
        parser.add_argument("--pacientes", type=int, default=300, help="Pacientes a crear/asegurar.")
        parser.add_argument("--ordenes-lab", type=int, default=800, help="Órdenes de laboratorio a crear.")
        parser.add_argument("--ventas-farmacia", type=int, default=1500, help="Ventas de farmacia.")
        parser.add_argument("--devoluciones-farmacia", type=int, default=120, help="Devoluciones de farmacia.")
        parser.add_argument("--dias", type=int, default=365, help="Distribuir registros en este rango de días.")
        parser.add_argument(
            "--operacion-v150-lotes",
            type=int,
            default=3,
            help="Cuántas veces correr generar_data_operativa_v150 antes de la carga masiva.",
        )
        parser.add_argument("--sin-laboratorio", action="store_true", help="No crear órdenes LIMS.")
        parser.add_argument("--sin-farmacia", action="store_true", help="No ejecutar ventas de farmacia.")
        parser.add_argument("--sin-v150", action="store_true", help="No ejecutar lotes operativos v150.")

    def handle(self, *args, **options):
        self.random = random.Random()
        self.random.seed()

        empresa = self._resolver_empresa(options.get("empresa_id"))
        usuario = self._resolver_usuario(empresa, options.get("usuario"))
        sucursal = self._resolver_sucursal(empresa)

        dias = max(1, int(options["dias"]))
        pacientes_target = max(1, int(options["pacientes"]))
        ordenes_lab_target = max(0, int(options["ordenes_lab"]))
        ventas_target = max(0, int(options["ventas_farmacia"]))
        devoluciones_target = max(0, int(options["devoluciones_farmacia"]))
        v150_lotes = max(0, int(options["operacion_v150_lotes"]))

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("SIMULACION OPERATIVA ANUAL PRISLAB"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"Empresa: {empresa.id} - {empresa.nombre}")
        self.stdout.write(f"Usuario: {usuario.username}")
        self.stdout.write(f"Sucursal: {sucursal.id} - {sucursal.nombre}")
        self.stdout.write(
            f"Objetivos -> pacientes={pacientes_target}, ordenes_lab={ordenes_lab_target}, "
            f"ventas_farmacia={ventas_target}, devoluciones={devoluciones_target}, dias={dias}"
        )

        pacientes = self._asegurar_pacientes(
            empresa=empresa,
            sucursal=sucursal,
            total=pacientes_target,
            dias=dias,
        )

        resumen = {
            "pacientes_pool": len(pacientes),
            "v150_lotes": 0,
            "ordenes_lab": 0,
            "resultados_lab": 0,
            "ventas_farmacia": 0,
            "devoluciones_farmacia": 0,
        }

        if not options["sin_v150"] and v150_lotes:
            resumen["v150_lotes"] = self._ejecutar_lotes_v150(empresa.id, v150_lotes)

        if not options["sin_laboratorio"] and ordenes_lab_target:
            lab = self._generar_ordenes_lims(
                empresa=empresa,
                sucursal=sucursal,
                usuario=usuario,
                pacientes=pacientes,
                total=ordenes_lab_target,
                dias=dias,
            )
            resumen["ordenes_lab"] = lab["ordenes"]
            resumen["resultados_lab"] = lab["resultados"]

        if not options["sin_farmacia"] and ventas_target:
            farmacia = self._ejecutar_simulacion_farmacia(
                usuario=usuario.username,
                ventas=ventas_target,
                devoluciones=devoluciones_target,
                dias=dias,
            )
            resumen["ventas_farmacia"] = farmacia["ventas"]
            resumen["devoluciones_farmacia"] = farmacia["devoluciones"]

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("RESUMEN FINAL"))
        for key, value in resumen.items():
            self.stdout.write(f"- {key}: {value}")
        self.stdout.write(self.style.SUCCESS("SIMULACION OPERATIVA LISTA"))

    def _resolver_empresa(self, empresa_id):
        if empresa_id:
            empresa = Empresa.objects.filter(pk=empresa_id).first()
            if not empresa:
                raise CommandError(f"No existe Empresa id={empresa_id}.")
            return empresa
        empresa = Empresa.objects.filter(activa=True).order_by("pk").first()
        if not empresa:
            raise CommandError("No hay empresa activa.")
        return empresa

    def _resolver_usuario(self, empresa, username):
        if username:
            user = User.objects.filter(username=username, empresa=empresa).first()
            if not user:
                raise CommandError(f"No existe usuario '{username}' en empresa {empresa.id}.")
            return user
        user = (
            User.objects.filter(empresa=empresa, is_active=True)
            .order_by("-is_superuser", "-is_staff", "pk")
            .first()
        )
        if not user:
            raise CommandError(f"No hay usuario activo para empresa id={empresa.id}.")
        return user

    def _resolver_sucursal(self, empresa):
        sucursal = Sucursal.objects.filter(empresa=empresa, activa=True).order_by("pk").first()
        if not sucursal:
            raise CommandError(f"No hay sucursal activa para empresa id={empresa.id}.")
        return sucursal

    def _asegurar_pacientes(self, empresa, sucursal, total, dias):
        existentes = list(
            Paciente.objects.filter(empresa=empresa, nombre_completo__contains=TAG_STRESS).order_by("pk")
        )
        faltantes = max(0, total - len(existentes))
        creados = []
        for idx in range(faltantes):
            nom, ap_pat, ap_mat, sexo = NOMBRES[idx % len(NOMBRES)]
            numero = len(existentes) + idx + 1
            email = f"stress.prislab.{empresa.id}.{numero}@seed.invalid"
            fecha_nacimiento = timezone.now().date() - timedelta(days=self.random.randint(18 * 365, 75 * 365))
            paciente, created = Paciente.objects.get_or_create(
                empresa=empresa,
                email=email,
                defaults={
                    "sucursal": sucursal,
                    "nombres": nom,
                    "apellido_paterno": ap_pat,
                    "apellido_materno": ap_mat,
                    "nombre_completo": f"{TAG_STRESS} {nom} {ap_pat} {ap_mat} {numero}",
                    "fecha_nacimiento": fecha_nacimiento,
                    "sexo": sexo,
                    "telefono": f"5557{empresa.id:03d}{numero:05d}"[:20],
                    "tipo": self.random.choice(["GENERAL", "EMPLEADO", "FAMILIA", "INAPAM"]),
                },
            )
            if created:
                fecha_registro = timezone.now() - timedelta(
                    days=self.random.randint(0, dias),
                    hours=self.random.randint(0, 23),
                    minutes=self.random.randint(0, 59),
                )
                Paciente.objects.filter(pk=paciente.pk).update(fecha_registro=fecha_registro)
                creados.append(paciente)
        pacientes = existentes + creados
        self.stdout.write(
            self.style.NOTICE(
                f"Pacientes stress disponibles: {len(pacientes)} "
                f"(creados en esta corrida: {len(creados)})"
            )
        )
        return pacientes[:total]

    def _ejecutar_lotes_v150(self, empresa_id, lotes):
        ejecutados = 0
        for i in range(lotes):
            self.stdout.write(self.style.WARNING(f"Ejecutando lote v150 {i + 1}/{lotes}..."))
            call_command(
                "generar_data_operativa_v150",
                empresa_id=empresa_id,
                force=True,
                local_pdf=True,
                stdout=self.stdout,
            )
            ejecutados += 1
        return ejecutados

    def _generar_ordenes_lims(self, empresa, sucursal, usuario, pacientes, total, dias):
        catalogo = self._construir_catalogo_lims(empresa)
        if not catalogo:
            raise CommandError(
                "No hay items LIMS vendibles con precio. Ejecuta primero ensamblar_lims_v75 y precios."
            )

        creadas = 0
        resultados = 0
        estado_pool = [
            ("PENDIENTE_PAGO", 12),
            ("PAGADO", 18),
            ("EN_PROCESO", 35),
            ("RESULTADOS_LISTOS", 25),
            ("ENTREGADO", 10),
        ]
        estados = [estado for estado, peso in estado_pool for _ in range(peso)]

        for idx in range(total):
            paciente = self.random.choice(pacientes)
            created_at = timezone.now() - timedelta(
                days=self.random.randint(0, dias),
                hours=self.random.randint(0, 23),
                minutes=self.random.randint(0, 59),
            )
            estado = self.random.choice(estados)
            lineas = self._seleccionar_lineas_catalogo(catalogo)
            total_orden = sum((linea["precio"] for linea in lineas), Decimal("0.00")).quantize(Decimal("0.01"))

            pago_total, estado_pago = self._resolver_pago_para_estado(total_orden, estado)
            with transaction.atomic():
                orden = OrdenDeServicio.objects.create(
                    empresa=empresa,
                    sucursal=sucursal,
                    paciente=paciente,
                    paciente_nombre_snapshot=paciente.nombre_completo,
                    paciente_edad_snapshot=paciente.edad,
                    paciente_sexo_snapshot=paciente.sexo or "I",
                    total=total_orden,
                    anticipo=pago_total,
                    responsable_ingreso=usuario,
                    folio_orden=f"STRESS-LAB-{empresa.id}-{uuid.uuid4().hex[:10].upper()}",
                    tipo_servicio=self.random.choice(["RUTINA", "URGENTE", "CONTROL"]),
                    tarifa="PUBLICO_GENERAL",
                    diagnostico="Simulacion operativa anual controlada",
                    notas_internas=f"{TAG_STRESS} carga_lims",
                    estado=estado,
                    estado_pago=estado_pago,
                    origen_orden=self.random.choice(
                        ["PUBLICO_GENERAL", "MEDICO_EXTERNO", "CONVENIO", "URGENCIA"]
                    ),
                )
                OrdenDeServicio.objects.filter(pk=orden.pk).update(fecha_creacion=created_at)

                detalles = []
                for linea in lineas:
                    detalle = DetalleOrden.objects.create(
                        orden=orden,
                        analito=linea["analito"],
                        perfil_lims=linea["perfil"],
                        paquete_lims=linea["paquete"],
                        descripcion_linea=linea["descripcion"],
                        precio_momento=linea["precio"],
                        estado_procesamiento=self._estado_detalle_desde_orden(estado),
                        validado_por=usuario if estado in {"RESULTADOS_LISTOS", "ENTREGADO"} else None,
                        fecha_validacion=created_at if estado in {"RESULTADOS_LISTOS", "ENTREGADO"} else None,
                    )
                    detalles.append(detalle)

                if pago_total > 0:
                    self._crear_pago_orden(empresa, orden, usuario, pago_total, created_at)

                if estado in {"EN_PROCESO", "RESULTADOS_LISTOS", "ENTREGADO"}:
                    resultados += self._crear_resultados_para_orden(
                        orden=orden,
                        detalles=detalles,
                        usuario=usuario,
                        created_at=created_at,
                        validar=estado in {"RESULTADOS_LISTOS", "ENTREGADO"},
                    )

            creadas += 1
            if (idx + 1) % 100 == 0:
                self.stdout.write(f"Laboratorio: {idx + 1}/{total} ordenes creadas")

        self.stdout.write(
            self.style.NOTICE(f"Laboratorio masivo OK: ordenes={creadas}, resultados={resultados}")
        )
        return {"ordenes": creadas, "resultados": resultados}

    def _construir_catalogo_lims(self, empresa):
        catalogo = []
        for precio in PrecioItem.objects.filter(empresa=empresa, activo=True).select_related(
            "analito", "perfil", "paquete"
        ):
            amount = (precio.precio_venta or Decimal("0.00")).quantize(Decimal("0.01"))
            if amount <= 0:
                continue
            if precio.analito_id and precio.analito and precio.analito.activo:
                catalogo.append(
                    {
                        "tipo": "analito",
                        "analito": precio.analito,
                        "perfil": None,
                        "paquete": None,
                        "descripcion": precio.analito.nombre,
                        "precio": amount,
                    }
                )
            elif precio.perfil_id and precio.perfil and precio.perfil.activo:
                catalogo.append(
                    {
                        "tipo": "perfil",
                        "analito": None,
                        "perfil": precio.perfil,
                        "paquete": None,
                        "descripcion": precio.perfil.nombre,
                        "precio": amount,
                    }
                )
            elif precio.paquete_id and precio.paquete and precio.paquete.activo:
                catalogo.append(
                    {
                        "tipo": "paquete",
                        "analito": None,
                        "perfil": None,
                        "paquete": precio.paquete,
                        "descripcion": precio.paquete.nombre,
                        "precio": amount,
                    }
                )
        return catalogo

    def _seleccionar_lineas_catalogo(self, catalogo):
        cantidad = self.random.randint(1, min(4, len(catalogo)))
        indices = self.random.sample(range(len(catalogo)), cantidad)
        return [catalogo[i] for i in indices]

    def _resolver_pago_para_estado(self, total_orden, estado):
        if estado == "PENDIENTE_PAGO":
            return Decimal("0.00"), "PENDIENTE"
        if estado == "PAGADO":
            return total_orden, "PAGADO"
        if estado == "EN_PROCESO":
            if self.random.random() < 0.2:
                return (total_orden * Decimal("0.50")).quantize(Decimal("0.01")), "PARCIAL"
            return total_orden, "PAGADO"
        return total_orden, "PAGADO"

    def _estado_detalle_desde_orden(self, estado):
        if estado == "PENDIENTE_PAGO":
            return "PENDIENTE_TOMA"
        if estado == "PAGADO":
            return "TOMA_REALIZADA"
        if estado == "EN_PROCESO":
            return "EN_PROCESO"
        return "RESULTADO_LISTO"

    def _crear_pago_orden(self, empresa, orden, usuario, monto, fecha_pago):
        if monto <= 0:
            return None
        efectivo = monto
        credito = Decimal("0.00")
        debito = Decimal("0.00")
        transferencia = Decimal("0.00")
        forma = self.random.choice(["EFECTIVO", "MIX_TC", "MIX_TRANSFERENCIA"])
        if forma == "MIX_TC" and monto > Decimal("100.00"):
            credito = (monto * Decimal("0.30")).quantize(Decimal("0.01"))
            efectivo = (monto - credito).quantize(Decimal("0.01"))
        elif forma == "MIX_TRANSFERENCIA" and monto > Decimal("100.00"):
            transferencia = (monto * Decimal("0.40")).quantize(Decimal("0.01"))
            efectivo = (monto - transferencia).quantize(Decimal("0.01"))
        return PagoOrden.objects.create(
            empresa=empresa,
            orden=orden,
            monto_efectivo=efectivo,
            monto_credito=credito,
            monto_debito=debito,
            monto_tarjeta=(credito + debito).quantize(Decimal("0.01")),
            monto_transferencia=transferencia,
            referencia_pago=f"stress-{uuid.uuid4().hex[:10]}",
            fecha_pago=fecha_pago,
            usuario_registro=usuario,
        )

    def _crear_resultados_para_orden(self, orden, detalles, usuario, created_at, validar):
        total = 0
        for detalle in detalles:
            for analito in self._expandir_analitos_detalle(detalle):
                valor = self._valor_para_analito(analito)
                res, _ = ResultadoParametro.objects.update_or_create(
                    orden=orden,
                    analito=analito,
                    defaults={
                        "valor": valor,
                        "capturado_por": usuario,
                        "metodo_captura": "MANUAL",
                        "aprobado_por_humano": validar,
                        "validado": validar,
                        "validado_por": usuario if validar else None,
                        "fecha_validacion": created_at if validar else None,
                        "observaciones": "Carga masiva de estres controlada",
                    },
                )
                try:
                    res.validar_contra_rango(
                        edad=orden.paciente_edad_snapshot,
                        sexo=orden.paciente_sexo_snapshot,
                    )
                except Exception:
                    pass
                total += 1
        return total

    def _expandir_analitos_detalle(self, detalle):
        if detalle.analito_id:
            return [detalle.analito]
        if detalle.perfil_lims_id:
            return [a for a in detalle.perfil_lims.analitos.filter(activo=True) if not a.es_calculado]
        if detalle.paquete_lims_id:
            return [a for a in detalle.paquete_lims.get_todos_analitos().filter(activo=True) if not a.es_calculado]
        return []

    def _valor_para_analito(self, analito):
        if analito.tipo_resultado == "TEXTO":
            return "Negativo"
        if analito.tipo_resultado == "OPCIONES":
            opciones = [x.strip() for x in (analito.opciones_texto or "").splitlines() if x.strip()]
            return opciones[0] if opciones else "Normal"
        if analito.tipo_resultado != "NUMERICO":
            return "0"

        rango = ValorReferenciaAnalito.objects.filter(analito=analito).order_by("edad_minima").first()
        decimales = max(0, int(analito.decimales or 0))
        if rango and rango.ref_minimo is not None and rango.ref_maximo is not None:
            minimo = float(rango.ref_minimo)
            maximo = float(rango.ref_maximo)
            if minimo <= maximo:
                valor = self.random.uniform(minimo, maximo)
                return f"{valor:.{decimales}f}"
        if rango and rango.ref_minimo is not None:
            valor = float(rango.ref_minimo) + 1
            return f"{valor:.{decimales}f}"
        return f"{self.random.uniform(1, 20):.{decimales}f}"

    def _ejecutar_simulacion_farmacia(self, usuario, ventas, devoluciones, dias):
        self.stdout.write(self.style.WARNING("Ejecutando simulacion real de farmacia..."))
        call_command(
            "simular_ventas_farmacia_completo",
            ventas=ventas,
            devoluciones=devoluciones,
            dias=dias,
            usuario=usuario,
            stdout=self.stdout,
        )
        return {"ventas": ventas, "devoluciones": devoluciones}
