"""
Tests para Buzón / Comunicación / Notificaciones.
Cobertura: tenant isolation, roles, endpoints públicos, APIs internas.
"""
import json
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa, Usuario, BuzonQuejas, NotificacionSistema


class BuzonKanbanSecurityTests(TestCase):
    """Kanban de quejas: tenant, roles, sin-empresa."""

    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre="Buzon A", rfc="BZA260625A1")
        self.empresa_b = Empresa.objects.create(nombre="Buzon B", rfc="BZB260625B2")

        self.director_a = Usuario.objects.create_user(
            username="dir_a", password="test", empresa=self.empresa_a, rol="DIRECTOR"
        )
        self.director_b = Usuario.objects.create_user(
            username="dir_b", password="test", empresa=self.empresa_b, rol="DIRECTOR"
        )
        self.cajero = Usuario.objects.create_user(
            username="cajero_bz", password="test", empresa=self.empresa_a, rol="CAJERO"
        )
        self.sin_empresa = Usuario.objects.create_user(
            username="sin_emp_bz", password="test", empresa=None, rol="DIRECTOR"
        )

    def test_kanban_tenant_isolation(self):
        BuzonQuejas.objects.create(empresa=self.empresa_a, tipo="QUEJA", mensaje="Q-A", estado="PENDIENTE")
        BuzonQuejas.objects.create(empresa=self.empresa_b, tipo="QUEJA", mensaje="Q-B", estado="PENDIENTE")

        self.client.force_login(self.director_a)
        resp = self.client.get(reverse("buzon_kanban"))
        self.assertEqual(resp.status_code, 200)
        mensajes = [q.mensaje for q in resp.context["quejas_nuevas"]]
        self.assertIn("Q-A", mensajes)
        self.assertNotIn("Q-B", mensajes)

    def test_kanban_sin_empresa_redirige(self):
        self.client.force_login(self.sin_empresa)
        resp = self.client.get(reverse("buzon_kanban"))
        self.assertEqual(resp.status_code, 302)

    def test_kanban_rechaza_cajero(self):
        self.client.force_login(self.cajero)
        resp = self.client.get(reverse("buzon_kanban"))
        self.assertIn(resp.status_code, [302, 403])

    def test_kanban_estadisticas_por_empresa(self):
        BuzonQuejas.objects.create(empresa=self.empresa_a, tipo="QUEJA", mensaje="Q1", estado="PENDIENTE", sentimiento_ia="CRITICO")
        BuzonQuejas.objects.create(empresa=self.empresa_a, tipo="SUGERENCIA", mensaje="S1", estado="PENDIENTE")
        BuzonQuejas.objects.create(empresa=self.empresa_b, tipo="QUEJA", mensaje="Q-otro", estado="PENDIENTE")

        self.client.force_login(self.director_a)
        resp = self.client.get(reverse("buzon_kanban"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_quejas"], 2)
        self.assertEqual(resp.context["quejas_criticas"], 1)
        self.assertEqual(resp.context["quejas_sin_analizar"], 2)


class TuOpinionPublicTests(TestCase):
    """Vista pública tu_opinion: resolución de empresa, creación anónima."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Pub E", rfc="PUB260625E1")

    def test_get_sin_parametro_muestra_sin_empresa(self):
        resp = self.client.get(reverse("tu_opinion"))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["empresa"])

    def test_get_con_empresa_resuelve(self):
        resp = self.client.get(f"{reverse('tu_opinion')}?empresa={self.empresa.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["empresa"], self.empresa)

    def test_post_sin_empresa_error(self):
        resp = self.client.post(reverse("tu_opinion"), {"tipo": "QUEJA", "mensaje": "Test"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("No se pudo identificar", resp.context["error"])

    def test_post_crea_queja(self):
        resp = self.client.post(
            f"{reverse('tu_opinion')}?empresa={self.empresa.id}",
            {"tipo": "SUGERENCIA", "mensaje": "Mejorar sala", "nombre": "Juan", "anonimo": "false"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["exito"])
        q = BuzonQuejas.objects.latest("id")
        self.assertEqual(q.empresa, self.empresa)
        self.assertEqual(q.tipo, "SUGERENCIA")
        self.assertEqual(q.nombre_remitente, "Juan")

    def test_post_anonimo_guarda_sin_nombre(self):
        resp = self.client.post(
            f"{reverse('tu_opinion')}?empresa={self.empresa.id}",
            {"tipo": "QUEJA", "mensaje": "Anónimo", "anonimo": "true", "nombre": "Oculto"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["exito"])
        q = BuzonQuejas.objects.latest("id")
        self.assertTrue(q.anonimo)
        self.assertIsNone(q.nombre_remitente)

    def test_post_sin_mensaje_error(self):
        resp = self.client.post(
            f"{reverse('tu_opinion')}?empresa={self.empresa.id}",
            {"tipo": "QUEJA", "mensaje": ""},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["error"], "El mensaje es obligatorio")

    def test_empresa_inactiva_no_resuelve(self):
        self.empresa.activa = False
        self.empresa.save()
        resp = self.client.get(f"{reverse('tu_opinion')}?empresa={self.empresa.id}")
        self.assertIsNone(resp.context["empresa"])


class ApiCambiarEstadoQuejaTests(TestCase):
    """API de cambio de estado: tenant, transiciones, sin-empresa."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="API E", rfc="API260625E1")
        self.otra = Empresa.objects.create(nombre="Otra E", rfc="OTR260625E2")
        self.director = Usuario.objects.create_user(
            username="dir_api", password="test", empresa=self.empresa, rol="DIRECTOR"
        )
        self.otro_dir = Usuario.objects.create_user(
            username="otro_dir", password="test", empresa=self.otra, rol="DIRECTOR"
        )
        self.sin_empresa = Usuario.objects.create_user(
            username="sin_api", password="test", empresa=None, rol="DIRECTOR"
        )
        self.queja = BuzonQuejas.objects.create(
            empresa=self.empresa, tipo="QUEJA", mensaje="Test", estado="PENDIENTE"
        )

    def _cambiar(self, user, queja_id, estado, **extra):
        self.client.force_login(user)
        return self.client.post(
            reverse("api_cambiar_estado_queja", args=[queja_id]),
            json.dumps({"estado": estado, **extra}),
            content_type="application/json",
        )

    def test_cambiar_a_en_revision(self):
        resp = self._cambiar(self.director, self.queja.id, "EN_REVISION")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.queja.refresh_from_db()
        self.assertEqual(self.queja.estado, "EN_REVISION")

    def test_cambiar_a_resuelto(self):
        resp = self._cambiar(self.director, self.queja.id, "RESUELTO", notas_resolucion="Solucionado")
        self.assertEqual(resp.status_code, 200)
        self.queja.refresh_from_db()
        self.assertEqual(self.queja.estado, "RESUELTO")
        self.assertIsNotNone(self.queja.fecha_resolucion)
        self.assertEqual(self.queja.resuelto_por, self.director)
        self.assertEqual(self.queja.notas_resolucion, "Solucionado")

    def test_cambiar_a_descartado(self):
        resp = self._cambiar(self.director, self.queja.id, "DESCARTADO")
        self.assertEqual(resp.status_code, 200)
        self.queja.refresh_from_db()
        self.assertEqual(self.queja.estado, "DESCARTADO")

    def test_reabrir_resuelto_limpia_datos(self):
        self.queja.estado = "RESUELTO"
        self.queja.fecha_resolucion = self.queja.fecha_creacion
        self.queja.resuelto_por = self.director
        self.queja.save()
        resp = self._cambiar(self.director, self.queja.id, "PENDIENTE")
        self.assertEqual(resp.status_code, 200)
        self.queja.refresh_from_db()
        self.assertEqual(self.queja.estado, "PENDIENTE")
        self.assertIsNone(self.queja.fecha_resolucion)
        self.assertIsNone(self.queja.resuelto_por)

    def test_cross_tenant_bloqueado(self):
        resp = self._cambiar(self.otro_dir, self.queja.id, "EN_REVISION")
        self.assertEqual(resp.status_code, 404)

    def test_sin_empresa_rechaza_403(self):
        resp = self._cambiar(self.sin_empresa, self.queja.id, "EN_REVISION")
        self.assertEqual(resp.status_code, 403)

    def test_estado_invalido_rechaza_400(self):
        resp = self._cambiar(self.director, self.queja.id, "INEXISTENTE")
        self.assertEqual(resp.status_code, 400)

    def test_queja_inexistente_404(self):
        resp = self._cambiar(self.director, 99999, "PENDIENTE")
        self.assertEqual(resp.status_code, 404)


class ApiObtenerQuejasTests(TestCase):
    """API obtener quejas: tenant, filtrado, sin-empresa."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Get E", rfc="GET260625E1")
        self.director = Usuario.objects.create_user(
            username="dir_get", password="test", empresa=self.empresa, rol="DIRECTOR"
        )
        self.sin_empresa = Usuario.objects.create_user(
            username="sin_get", password="test", empresa=None, rol="DIRECTOR"
        )
        BuzonQuejas.objects.create(empresa=self.empresa, tipo="QUEJA", mensaje="Q1", estado="PENDIENTE")
        BuzonQuejas.objects.create(empresa=self.empresa, tipo="SUGERENCIA", mensaje="S1", estado="RESUELTO")

    def test_obtener_todas(self):
        self.client.force_login(self.director)
        resp = self.client.get(reverse("api_obtener_quejas"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["quejas"]), 2)

    def test_filtrar_por_estado(self):
        self.client.force_login(self.director)
        resp = self.client.get(f"{reverse('api_obtener_quejas')}?estado=PENDIENTE")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["quejas"]), 1)
        self.assertEqual(data["quejas"][0]["estado"], "PENDIENTE")

    def test_sin_empresa_rechaza_403(self):
        self.client.force_login(self.sin_empresa)
        resp = self.client.get(reverse("api_obtener_quejas"))
        self.assertEqual(resp.status_code, 403)


class ApiCrearNotificacionTests(TestCase):
    """API crear notificación: permisos, tenant, validación."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Notif E", rfc="NTF260625E1")
        self.admin = Usuario.objects.create_user(
            username="admin_ntf", password="test", empresa=self.empresa, rol="ADMIN"
        )
        self.cajero = Usuario.objects.create_user(
            username="caj_ntf", password="test", empresa=self.empresa, rol="CAJERO"
        )
        self.sin_empresa = Usuario.objects.create_user(
            username="sin_ntf", password="test", empresa=None, rol="ADMIN"
        )

    def _crear(self, user, payload):
        self.client.force_login(user)
        return self.client.post(
            reverse("api_crear_notificacion"),
            json.dumps(payload),
            content_type="application/json",
        )

    def test_crear_notificacion_exito(self):
        resp = self._crear(self.admin, {"titulo": "Test", "mensaje": "Cuerpo", "tipo": "INFO"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        n = NotificacionSistema.objects.latest("id")
        self.assertEqual(n.titulo, "Test")
        self.assertEqual(n.empresa, self.empresa)

    def test_cajero_rechazado_403(self):
        resp = self._crear(self.cajero, {"titulo": "X", "mensaje": "Y"})
        self.assertEqual(resp.status_code, 403)

    def test_sin_empresa_rechaza_403(self):
        resp = self._crear(self.sin_empresa, {"titulo": "X", "mensaje": "Y"})
        self.assertEqual(resp.status_code, 403)

    def test_json_invalido_400(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("api_crear_notificacion"),
            "not json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_get_rechazado_405(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("api_crear_notificacion"))
        self.assertEqual(resp.status_code, 405)


class EjecutarVerificacionesTests(TestCase):
    """Verificaciones manuales: permisos, tenant."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Verif E", rfc="VRF260625E1")
        self.staff = Usuario.objects.create_user(
            username="staff_vf", password="test", empresa=self.empresa, rol="ADMIN", is_staff=True
        )
        self.no_staff = Usuario.objects.create_user(
            username="nostaff", password="test", empresa=self.empresa, rol="CAJERO"
        )
        self.sin_empresa = Usuario.objects.create_user(
            username="sin_vf", password="test", empresa=None, rol="ADMIN", is_staff=True
        )

    def test_staff_ejecuta_ok(self):
        self.client.force_login(self.staff)
        resp = self.client.post(reverse("ejecutar_verificaciones"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    def test_no_staff_rechaza_403(self):
        self.client.force_login(self.no_staff)
        resp = self.client.post(reverse("ejecutar_verificaciones"))
        self.assertEqual(resp.status_code, 403)

    def test_sin_empresa_rechaza_403(self):
        self.client.force_login(self.sin_empresa)
        resp = self.client.post(reverse("ejecutar_verificaciones"))
        self.assertEqual(resp.status_code, 403)

    def test_get_rechazado_405(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("ejecutar_verificaciones"))
        self.assertEqual(resp.status_code, 405)


class NotificacionesFlujoCompletoTests(TestCase):
    """Flujo completo: lista, badge, marcar leída, marcar todas, configurar."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Flujo E", rfc="FLJ260625E1")
        self.user = Usuario.objects.create_user(
            username="flujo_user", password="test", empresa=self.empresa, rol="ADMIN"
        )
        self.sin_empresa = Usuario.objects.create_user(
            username="flujo_sin", password="test", empresa=None, rol="CAJERO"
        )
        self.n1 = NotificacionSistema.crear(
            empresa=self.empresa, titulo="N1", mensaje="Mensaje 1", tipo="INFO", modulo="GENERAL"
        )
        self.n2 = NotificacionSistema.crear(
            empresa=self.empresa, titulo="N2", mensaje="Mensaje 2", tipo="ALERTA", modulo="LABORATORIO"
        )

    def test_lista_con_empresa(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("notificaciones_lista"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.context["notificaciones"]), 2)
        self.assertEqual(resp.context["total_no_leidas"], 2)

    def test_lista_sin_empresa_vacio(self):
        self.client.force_login(self.sin_empresa)
        resp = self.client.get(reverse("notificaciones_lista"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["notificaciones"]), 0)
        self.assertTrue(resp.context["error_empresa"])

    def test_badge_con_empresa(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("notificaciones_badge"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["no_leidas"], 2)
        self.assertEqual(len(data["recientes"]), 2)

    def test_badge_sin_empresa_cero(self):
        self.client.force_login(self.sin_empresa)
        resp = self.client.get(reverse("notificaciones_badge"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["no_leidas"], 0)

    def test_marcar_leida(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("notificacion_leer", args=[self.n1.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.leida)
        self.assertIsNotNone(self.n1.fecha_lectura)

    def test_marcar_leida_cross_tenant_404(self):
        otra = Empresa.objects.create(nombre="OtraFlujo", rfc="OTF260625E2")
        otro_user = Usuario.objects.create_user(
            username="otro_flujo", password="test", empresa=otra, rol="ADMIN"
        )
        self.client.force_login(otro_user)
        resp = self.client.post(reverse("notificacion_leer", args=[self.n1.id]))
        self.assertEqual(resp.status_code, 404)

    def test_marcar_leida_sin_empresa_403(self):
        self.client.force_login(self.sin_empresa)
        resp = self.client.post(reverse("notificacion_leer", args=[self.n1.id]))
        self.assertEqual(resp.status_code, 403)

    def test_marcar_todas(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("notificaciones_marcar_todas"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["marcadas"], 2)

    def test_marcar_todas_sin_empresa_403(self):
        self.client.force_login(self.sin_empresa)
        resp = self.client.post(reverse("notificaciones_marcar_todas"))
        self.assertEqual(resp.status_code, 403)

    def test_configurar_con_empresa(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("configurar_notificaciones"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total"], 2)

    def test_configurar_sin_empresa_redirige(self):
        self.client.force_login(self.sin_empresa)
        resp = self.client.get(reverse("configurar_notificaciones"))
        self.assertEqual(resp.status_code, 302)

    def test_filtro_tipo(self):
        self.client.force_login(self.user)
        resp = self.client.get(f"{reverse('notificaciones_lista')}?tipo=ALERTA")
        self.assertEqual(resp.status_code, 200)
        for n in resp.context["notificaciones"]:
            self.assertEqual(n.tipo, "ALERTA")

    def test_filtro_no_leidas(self):
        self.n1.marcar_leida()
        self.client.force_login(self.user)
        resp = self.client.get(f"{reverse('notificaciones_lista')}?no_leidas=1")
        self.assertEqual(resp.status_code, 200)
        for n in resp.context["notificaciones"]:
            self.assertFalse(n.leida)
