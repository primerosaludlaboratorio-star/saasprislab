"""
Tests de aislamiento cross-tenant para:
- MensajeInterno (chat) con filtro por empresa
- BuzonQuejas (kanban) con categorías válidas
- Notificaciones con empresa=None → corte limpio
- tu_opinion pública sin fuga de empresa
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa, Sucursal, MensajeInterno, BuzonQuejas, NotificacionSistema

Usuario = get_user_model()


class MensajeInternoTenantIsolationTest(TestCase):
    """El chat interno no debe filtrar mensajes entre tenants."""

    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre="Clinica Alfa", rfc="ALF260625A1")
        self.empresa_b = Empresa.objects.create(nombre="Clinica Beta", rfc="BET260625B2")

        self.user_a1 = Usuario.objects.create_user(
            username="alfa_doctor", password="Test2026!A1",
            empresa=self.empresa_a, rol="MEDICO",
        )
        self.user_a2 = Usuario.objects.create_user(
            username="alfa_quimico", password="Test2026!A2",
            empresa=self.empresa_a, rol="QUIMICO",
        )
        self.user_b1 = Usuario.objects.create_user(
            username="beta_doctor", password="Test2026!B1",
            empresa=self.empresa_b, rol="MEDICO",
        )

    def test_mensaje_creado_con_empresa_del_remitente(self):
        self.client.force_login(self.user_a1)
        resp = self.client.post(
            reverse("api_enviar_mensaje"),
            json.dumps({"destinatario_id": self.user_a2.id, "mensaje": "Hola colega"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        msg = MensajeInterno.objects.latest("id")
        self.assertEqual(msg.empresa, self.empresa_a)

    def test_chat_lista_solo_usuarios_misma_empresa(self):
        self.client.force_login(self.user_a1)
        resp = self.client.get(reverse("api_listar_usuarios"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = [u["id"] for u in data["usuarios"]]
        self.assertIn(self.user_a2.id, ids)
        self.assertNotIn(self.user_b1.id, ids)

    def test_mensajes_no_se_filtran_entre_empresas(self):
        # Crear mensaje en empresa A
        MensajeInterno.objects.create(
            empresa=self.empresa_a, remitente=self.user_a1,
            destinatario=self.user_a2, mensaje="Secreto Alfa",
        )
        # Crear mensaje en empresa B
        MensajeInterno.objects.create(
            empresa=self.empresa_b, remitente=self.user_b1,
            destinatario=self.user_b1, mensaje="Secreto Beta",
        )

        self.client.force_login(self.user_a1)
        resp = self.client.get(
            reverse("api_obtener_mensajes"),
            {"destinatario_id": self.user_a2.id},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        textos = [m["mensaje"] for m in data["mensajes"]]
        self.assertIn("Secreto Alfa", textos)
        self.assertNotIn("Secreto Beta", textos)

    def test_conversaciones_solo_muestra_misma_empresa(self):
        MensajeInterno.objects.create(
            empresa=self.empresa_a, remitente=self.user_a2,
            destinatario=self.user_a1, mensaje="Hola",
        )
        MensajeInterno.objects.create(
            empresa=self.empresa_b, remitente=self.user_b1,
            destinatario=self.user_b1, mensaje="No debería verse",
        )

        self.client.force_login(self.user_a1)
        resp = self.client.get(reverse("api_listar_conversaciones"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        user_ids = [c["usuario_id"] for c in data["conversaciones"]]
        self.assertIn(self.user_a2.id, user_ids)
        self.assertNotIn(self.user_b1.id, user_ids)

    def test_enviar_mensaje_a_usuario_otra_empresa_rechaza(self):
        self.client.force_login(self.user_a1)
        resp = self.client.post(
            reverse("api_enviar_mensaje"),
            json.dumps({"destinatario_id": self.user_b1.id, "mensaje": "Fuga?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_chat_sin_empresa_rechaza(self):
        user_sin = Usuario.objects.create_user(
            username="sin_empresa", password="Test2026!SE",
            empresa=None, rol="CAJERO",
        )
        self.client.force_login(user_sin)
        resp = self.client.get(reverse("api_listar_usuarios"))
        self.assertEqual(resp.status_code, 400)


class BuzonKanbanTenantTest(TestCase):
    """El kanban de quejas debe aislar por empresa y usar categorías válidas."""

    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre="Clinica A", rfc="BKA260625A1")
        self.empresa_b = Empresa.objects.create(nombre="Clinica B", rfc="BKB260625B2")

        self.user_a = Usuario.objects.create_user(
            username="director_a", password="Test2026!DA",
            empresa=self.empresa_a, rol="DIRECTOR",
        )
        self.user_b = Usuario.objects.create_user(
            username="director_b", password="Test2026!DB",
            empresa=self.empresa_b, rol="DIRECTOR",
        )

    def test_buzon_kanban_solo_muestra_quejas_de_su_empresa(self):
        BuzonQuejas.objects.create(
            empresa=self.empresa_a, tipo="QUEJA", mensaje="Queja Alfa",
            estado="PENDIENTE",
        )
        BuzonQuejas.objects.create(
            empresa=self.empresa_b, tipo="QUEJA", mensaje="Queja Beta",
            estado="PENDIENTE",
        )

        self.client.force_login(self.user_a)
        resp = self.client.get(reverse("buzon_kanban"))
        self.assertEqual(resp.status_code, 200)
        mensajes = [q.mensaje for q in resp.context["quejas_nuevas"]]
        self.assertIn("Queja Alfa", mensajes)
        self.assertNotIn("Queja Beta", mensajes)

    def test_buzon_kanban_sin_empresa_redirige(self):
        user_sin = Usuario.objects.create_user(
            username="sin_emp_buzon", password="Test2026!SB",
            empresa=None, rol="DIRECTOR",
        )
        self.client.force_login(user_sin)
        resp = self.client.get(reverse("buzon_kanban"))
        self.assertEqual(resp.status_code, 302)

    def test_categorias_kanban_usan_categoria_choices(self):
        BuzonQuejas.objects.create(
            empresa=self.empresa_a, tipo="QUEJA", mensaje="Problema proceso",
            estado="PENDIENTE", categoria_ia="PROCESO",
        )
        self.client.force_login(self.user_a)
        resp = self.client.get(reverse("buzon_kanban"))
        self.assertEqual(resp.status_code, 200)
        # Todas las claves de por_categoria deben ser de CATEGORIA_CHOICES
        for cat in resp.context["por_categoria"]:
            self.assertIn(cat, dict(BuzonQuejas.CATEGORIA_CHOICES))


class TuOpinionTenantTest(TestCase):
    """La vista pública tu_opinion no debe usar Empresa.objects.first()."""

    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre="Publica A", rfc="TOA260625A1")
        self.empresa_b = Empresa.objects.create(nombre="Publica B", rfc="TOB260625B2")

    def test_tu_opinion_get_sin_parametro_muestra_sin_empresa(self):
        resp = self.client.get(reverse("tu_opinion"))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["empresa"])

    def test_tu_opinion_con_parametro_empresa_resuelve_correcta(self):
        resp = self.client.get(reverse("tu_opinion") + f"?empresa={self.empresa_a.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["empresa"], self.empresa_a)

    def test_tu_opinion_post_sin_empresa_muestra_error(self):
        resp = self.client.post(reverse("tu_opinion"), {
            "tipo": "QUEJA", "mensaje": "Test sin empresa",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("No se pudo identificar", resp.context["error"])

    def test_tu_opinion_post_con_empresa_crea_queja(self):
        resp = self.client.post(
            reverse("tu_opinion") + f"?empresa={self.empresa_a.id}",
            {"tipo": "SUGERENCIA", "mensaje": "Mejorar sala espera"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["exito"])
        q = BuzonQuejas.objects.latest("id")
        self.assertEqual(q.empresa, self.empresa_a)
        self.assertEqual(q.mensaje, "Mejorar sala espera")

    def test_tu_opinion_no_usa_first_active(self):
        # Crear empresa B primero para que sea "first" si alguien usa .first()
        # Pero nuestra vista no debe usarla sin parámetro explícito
        resp = self.client.get(reverse("tu_opinion"))
        self.assertIsNone(resp.context["empresa"])


class NotificacionesSinEmpresaTest(TestCase):
    """Notificaciones deben cortar limpio cuando empresa es None."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Notif Empresa", rfc="NEF260625A1")
        self.user_con = Usuario.objects.create_user(
            username="con_empresa_notif", password="Test2026!CN",
            empresa=self.empresa, rol="ADMIN",
        )
        self.user_sin = Usuario.objects.create_user(
            username="sin_empresa_notif", password="Test2026!SN",
            empresa=None, rol="CAJERO",
        )

    def test_lista_notificaciones_sin_empresa_muestra_vacio(self):
        self.client.force_login(self.user_sin)
        resp = self.client.get(reverse("notificaciones_lista"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["notificaciones"]), 0)
        self.assertTrue(resp.context.get("error_empresa"))

    def test_badge_sin_empresa_devuelve_cero(self):
        self.client.force_login(self.user_sin)
        resp = self.client.get(reverse("notificaciones_badge"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["no_leidas"], 0)

    def test_marcar_leida_sin_empresa_rechaza_403(self):
        self.client.force_login(self.user_sin)
        resp = self.client.post(reverse("notificacion_leer", args=[1]))
        self.assertEqual(resp.status_code, 403)

    def test_marcar_todas_sin_empresa_rechaza_403(self):
        self.client.force_login(self.user_sin)
        resp = self.client.post(reverse("notificaciones_marcar_todas"))
        self.assertEqual(resp.status_code, 403)

    def test_configurar_sin_empresa_redirige(self):
        self.client.force_login(self.user_sin)
        resp = self.client.get(reverse("configurar_notificaciones"))
        self.assertEqual(resp.status_code, 302)

    def test_ejecutar_verificaciones_sin_empresa_rechaza_403(self):
        self.client.force_login(self.user_sin)
        resp = self.client.post(reverse("ejecutar_verificaciones"))
        self.assertEqual(resp.status_code, 403)

    def test_api_crear_notificacion_sin_empresa_rechaza_403(self):
        self.client.force_login(self.user_sin)
        resp = self.client.post(
            reverse("api_crear_notificacion"),
            {"titulo": "Test", "mensaje": "Body"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_notificaciones_aisladas_por_empresa(self):
        NotificacionSistema.crear(
            empresa=self.empresa, titulo="Solo para Alfa",
            mensaje="Secreto", tipo="INFO", modulo="GENERAL",
        )
        self.client.force_login(self.user_con)
        resp = self.client.get(reverse("notificaciones_lista"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.context["notificaciones"]), 1)

        self.client.force_login(self.user_sin)
        resp = self.client.get(reverse("notificaciones_lista"))
        self.assertEqual(len(resp.context["notificaciones"]), 0)
