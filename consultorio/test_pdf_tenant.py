"""
Regresión de tenant para las vistas PDF de receta del consultorio.

Las vistas `imprimir_receta_profesional` / `api_generar_receta_pdf` resolvían la
empresa con `getattr(request.user, 'empresa', None)` (lookup directo NO canónico),
saltándose `request.empresa_actual` que inyecta EmpresaIdentityMiddleware. Para un
usuario que opera dentro del contexto de otra empresa (p.ej. soporte/multi-empresa,
donde `request.empresa_actual` ≠ `user.empresa`) el scope quedaba mal: la consulta
legítima del tenant activo daba Http404.

Fix: usar `empresa_efectiva_request(request)` (= `request.empresa_actual ∥ user.empresa`),
el contrato canónico que ya usa el resto del módulo.

`test_resuelve_tenant_por_empresa_actual...` DISCRIMINA el fix: con el código viejo
`get_object_or_404` lanza Http404; con el nuevo, la consulta del tenant activo se
resuelve y la vista llega a la rama "sin receta" (HttpResponse 404, sin excepción).
"""
from django.test import TestCase, RequestFactory
from django.http import Http404
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Empresa, Paciente, ConsultaMedica
from consultorio.pdf_views_prislab import imprimir_receta_profesional

User = get_user_model()


class RecetaPdfTenantTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empA = Empresa.objects.create(nombre='Emp A', rfc='AAA010101AA1')
        self.empB = Empresa.objects.create(nombre='Emp B', rfc='BBB010101BB2')
        # Usuario cuya empresa "de casa" es A.
        self.userA = User.objects.create_user(
            username='medA', password='x12345678', email='a@a.com',
            empresa=self.empA, rol='MEDICO',
        )
        # Consulta SIN receta, perteneciente a la empresa B.
        self.pacB = Paciente.objects.create(
            empresa=self.empB, nombres='Pac', apellido_paterno='B', nombre_completo='Pac B',
        )
        self.consultaB = ConsultaMedica.objects.create(
            empresa=self.empB, paciente=self.pacB,
            folio_consulta='C-B-1', fecha_consulta=timezone.now(),
        )

    def _request(self, empresa_actual):
        req = self.factory.get(f'/consultorio/pdf/receta/{self.consultaB.id}/')
        req.user = self.userA
        req.empresa_actual = empresa_actual  # lo que inyecta EmpresaIdentityMiddleware
        return req

    def test_resuelve_tenant_por_empresa_actual_no_por_user_empresa(self):
        # userA operando en el contexto de la empresa B (empresa_actual=B).
        # Con el fix, la consulta de B se resuelve (scope correcto) y, al no tener
        # receta, la vista devuelve un HttpResponse 404 "no tiene receta" (NO Http404).
        resp = imprimir_receta_profesional(self._request(self.empB), self.consultaB.id)
        self.assertEqual(resp.status_code, 404)
        self.assertIn(b'no tiene receta', resp.content)

    def test_aisla_cuando_contexto_es_su_propia_empresa(self):
        # userA en su propia empresa A NO debe poder resolver la consulta de B.
        with self.assertRaises(Http404):
            imprimir_receta_profesional(self._request(self.empA), self.consultaB.id)
