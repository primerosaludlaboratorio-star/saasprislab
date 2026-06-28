import json
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa, Usuario

from .models import AccesoAcademia, CursoAcademia, SesionVisualizacion, VideoAcademia


@override_settings(ACADEMIA_EMPRESAS_PERMITIDAS=["prislab"])
class AcademiaViewsTests(TestCase):
    def setUp(self):
        self.empresa_prislab = Empresa.objects.create(nombre="PRISLAB")
        self.empresa_externa = Empresa.objects.create(nombre="Otro Lab")

        self.admin = Usuario.objects.create_user(
            username="academia_admin",
            password="test123456",
            empresa=self.empresa_prislab,
            rol="ADMIN",
            is_staff=True,
        )
        self.alumno = Usuario.objects.create_user(
            username="academia_alumno",
            password="test123456",
            empresa=self.empresa_prislab,
            rol="RECEPCION",
        )
        self.usuario_externo = Usuario.objects.create_user(
            username="academia_externo",
            password="test123456",
            empresa=self.empresa_externa,
            rol="ADMIN",
        )

        self.curso = CursoAcademia.objects.create(
            empresa=self.empresa_prislab,
            slug="diplomado-qfb",
            titulo="Diplomado QFB",
            activo=True,
        )
        self.video = VideoAcademia.objects.create(
            empresa=self.empresa_prislab,
            curso=self.curso,
            titulo="Clase 1",
            orden=1,
            bunny_video_id="video_001",
        )
        self.acceso = AccesoAcademia.objects.create(
            empresa=self.empresa_prislab,
            usuario=self.alumno,
            curso=self.curso,
            fecha_expiracion=timezone.now() + timedelta(days=30),
            activo=True,
            otorgado_por=self.admin,
        )

        self.client = Client()

    def test_dashboard_404_para_empresa_no_habilitada(self):
        self.client.login(username="academia_externo", password="test123456")

        response = self.client.get(reverse("academia:dashboard"))

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "PRIS Sentinel esta reparando", status_code=404)

    def test_curso_detalle_permite_usuario_con_acceso_vigente(self):
        self.client.login(username="academia_alumno", password="test123456")

        response = self.client.get(reverse("academia:curso_detalle", args=[self.curso.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Diplomado QFB")

    @patch("academia.views.bunny_stream.generar_token_embed", return_value=("token", 999999, "https://embed.test/video"))
    def test_api_video_reproducir_devuelve_embed_para_usuario_autorizado(self, _mock_embed):
        self.client.login(username="academia_alumno", password="test123456")

        response = self.client.get(reverse("academia:api_video_reproducir", args=[self.video.id]))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["embed_url"], "https://embed.test/video")
        self.assertEqual(data["video_id"], self.video.id)

    def test_otorgar_acceso_bloquea_usuario_de_otra_empresa(self):
        self.client.login(username="academia_admin", password="test123456")

        response = self.client.post(
            reverse("academia:otorgar_acceso"),
            data={
                "usuario_id": self.usuario_externo.id,
                "curso_id": self.curso.id,
                "dias_vigencia": 15,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            AccesoAcademia.objects.filter(
                empresa=self.empresa_prislab,
                usuario=self.usuario_externo,
                curso=self.curso,
            ).exists()
        )

    def test_heartbeat_acumula_sesion_existente(self):
        self.client.login(username="academia_alumno", password="test123456")
        SesionVisualizacion.objects.create(
            empresa=self.empresa_prislab,
            usuario=self.alumno,
            video=self.video,
            segundos_acumulados=30,
            ultima_actividad=timezone.now(),
        )

        response = self.client.post(
            reverse("academia:api_heartbeat", args=[self.video.id]),
            data=json.dumps({"segundos_reproducidos": 15}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["segundos_acumulados"], 45)
        self.assertEqual(
            SesionVisualizacion.objects.filter(
                empresa=self.empresa_prislab,
                usuario=self.alumno,
                video=self.video,
                finalizada=False,
            ).count(),
            1,
        )

    def test_curso_detalle_block_cross_tenant(self):
        curso_externo = CursoAcademia.objects.create(
            empresa=self.empresa_externa,
            slug="curso-externo",
            titulo="Curso Externo",
            activo=True,
        )
        self.client.login(username="academia_alumno", password="test123456")
        response = self.client.get(reverse("academia:curso_detalle", args=[curso_externo.slug]))
        self.assertEqual(response.status_code, 404)

    def test_api_video_reproducir_block_cross_tenant(self):
        curso_externo = CursoAcademia.objects.create(
            empresa=self.empresa_externa,
            slug="curso-externo",
            titulo="Curso Externo",
            activo=True,
        )
        video_externo = VideoAcademia.objects.create(
            empresa=self.empresa_externa,
            curso=curso_externo,
            titulo="Clase Externa",
            orden=1,
            bunny_video_id="video_ext_001",
        )
        self.client.login(username="academia_alumno", password="test123456")
        response = self.client.get(reverse("academia:api_video_reproducir", args=[video_externo.id]))
        self.assertEqual(response.status_code, 404)

    @patch("academia.views._empresa_actual", return_value=None)
    def test_dashboard_empty_company_blocked(self, _mock_emp):
        user_sin_emp = Usuario.objects.create_user(
            username="academia_sin_empresa",
            password="test123456",
            empresa=None,
            rol="RECEPCION"
        )
        self.client.login(username="academia_sin_empresa", password="test123456")
        response = self.client.get(reverse("academia:dashboard"))
        self.assertEqual(response.status_code, 404)
