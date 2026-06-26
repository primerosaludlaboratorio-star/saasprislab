"""
Pruebas canónicas del módulo Buzón / Comunicación (Imperium).

Cubre:
- flujo público de `tu_opinion`: crea la queja en la empresa canónica (no en la
  "primera empresa activa" arbitraria) y exige CSRF real (no es csrf_exempt).
- resolución de la colisión de `buzon_kanban`: la vista cableada es la de
  core/views/buzon.py, que agrupa por las categorías REALES de BuzonQuejas
  (TIEMPOS/TRATO/…). La copia huérfana de reporte_friccion agrupaba por
  categorías inexistentes y dejaba el desglose en 0.
- aislamiento multi-tenant en cambio de estado de quejas (IDOR) y corte sin empresa.
"""
import json

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import Empresa, BuzonQuejas

User = get_user_model()


class TuOpinionPublicoTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.emp = Empresa.objects.create(nombre='Op Co', rfc='OPC010101AB1', activa=True)

    def test_post_publico_crea_queja_en_empresa_canonica(self):
        # Visitante anónimo (sin login). Con una sola empresa activa, el resolutor
        # canónico la selecciona (antes: "primera empresa activa" arbitraria).
        c = Client()
        r = c.post(reverse('tu_opinion'), {
            'tipo': 'QUEJA', 'mensaje': 'Esperé demasiado', 'nombre': 'Ana',
            'contacto': 'ana@x.com', 'anonimo': 'false',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(BuzonQuejas.objects.count(), 1)
        self.assertEqual(BuzonQuejas.objects.first().empresa_id, self.emp.id)

    def test_tu_opinion_exige_csrf(self):
        # enforce_csrf_checks=True + sin token => 403 (prueba que NO es csrf_exempt).
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse('tu_opinion'), {'tipo': 'QUEJA', 'mensaje': 'x'})
        self.assertEqual(r.status_code, 403)


class BuzonKanbanColisionTest(TestCase):
    """La vista cableada usa las categorías reales de categoria_ia."""

    def test_por_categoria_usa_categorias_reales(self):
        emp = Empresa.objects.create(nombre='K Co', rfc='KCO010101AB2')
        user = User.objects.create_user(username='kuser', password='test12345',
                                        email='k@k.com', empresa=emp, is_staff=True)
        BuzonQuejas.objects.create(empresa=emp, mensaje='lento', tipo='QUEJA',
                                   estado='PENDIENTE', categoria_ia='TIEMPOS')
        c = Client(); c.force_login(user)
        r = c.get(reverse('buzon_kanban'))
        self.assertEqual(r.status_code, 200)
        por_cat = r.context[-1]['por_categoria']
        # La vista canónica agrupa por TIEMPOS/TRATO/...; la huérfana (fricción) no
        # tenía la clave 'TIEMPOS' y dejaba el desglose en 0.
        self.assertIn('TIEMPOS', por_cat)
        self.assertEqual(por_cat['TIEMPOS'], 1)


class BuzonTenantTest(TestCase):
    """Cambiar estado de una queja de otra empresa => 404; sin empresa => 403."""

    @classmethod
    def setUpTestData(cls):
        cls.empA = Empresa.objects.create(nombre='BA', rfc='BZA010101AA1')
        cls.empB = Empresa.objects.create(nombre='BB', rfc='BZB010101BB2')
        cls.userA = User.objects.create_user(username='bzA', password='test12345',
                                              email='a@a.com', empresa=cls.empA, is_staff=True)
        cls.quejaB = BuzonQuejas.objects.create(empresa=cls.empB, mensaje='x', tipo='QUEJA',
                                                estado='PENDIENTE')

    def test_cambiar_estado_queja_otra_empresa_404(self):
        c = Client(); c.force_login(self.userA)
        r = c.post(reverse('api_cambiar_estado_queja', args=[self.quejaB.id]),
                   data=json.dumps({'estado': 'RESUELTO'}), content_type='application/json')
        self.assertEqual(r.status_code, 404)

    def test_cambiar_estado_sin_empresa_403(self):
        u = User.objects.create_user(username='bz_noemp', password='test12345', email='n@n.com')
        User.objects.filter(pk=u.pk).update(empresa=None)
        c = Client(); c.force_login(u)
        r = c.post(reverse('api_cambiar_estado_queja', args=[self.quejaB.id]),
                   data=json.dumps({'estado': 'RESUELTO'}), content_type='application/json')
        self.assertEqual(r.status_code, 403)
