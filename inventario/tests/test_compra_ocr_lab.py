from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import Empresa
from inventario.models import CatalogoReactivoLab, LoteReactivoLab
from inventario.services.compra_ocr import conciliar_compra_laboratorio


def _png():
    from PIL import Image
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
    return SimpleUploadedFile("compra.png", buffer.getvalue(), content_type="image/png")


class CompraOcrLaboratorioTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Lab OCR")
        self.usuario = get_user_model().objects.create_user(
            username="lab_ocr_admin", password="test123456", rol="ADMIN", empresa=self.empresa,
        )
        self.reactivo = CatalogoReactivoLab.objects.create(
            empresa=self.empresa, codigo_interno="R-001", nombre="Reactivo Hematología",
            tipo="REACTIVO", unidad_medida="KIT",
        )
        self.client.force_login(self.usuario)

    def test_concilia_por_codigo_y_no_crea_lote(self):
        sugerencias = conciliar_compra_laboratorio(self.empresa, {"productos": [{
            "texto": "R-001", "cantidad": "2", "numero_lote": "L-1",
        }]})
        self.assertEqual(sugerencias[0]["candidatos"][0]["reactivo_id"], self.reactivo.id)
        self.assertFalse(LoteReactivoLab.objects.filter(empresa=self.empresa).exists())

    @patch("inventario.views.compra_ocr.analizar_compra_laboratorio")
    def test_analisis_guarda_borrador_y_no_modifica_inventario(self, analizar):
        analizar.return_value = {"activo": True, "confianza": 0.9,
                                 "datos_extraidos": {"productos": [{"texto": "R-001"}]},
                                 "texto_extraido": "R-001"}
        response = self.client.post(reverse("inventario:api_analizar_compra_laboratorio"), {"documento_compra": _png()})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LoteReactivoLab.objects.filter(empresa=self.empresa).exists())
