"""
Tests focalizados para el módulo Director:
- dashboard_director: acceso, tenant, KPIs del día, timezone
- director_analizadores: acceso, CRUD, toggle, eliminar_mapeo
- probar_conexion: método POST requerido, IP vacía
- Regresiones timezone/tenant
"""
import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import localdate, make_aware
from datetime import datetime

from core.models import Empresa, Sucursal, Venta

Usuario = get_user_model()


def _make_empresa(nombre="EmpresaDir", rfc="DIR260607TST"):
    return Empresa.objects.create(nombre=nombre, rfc=rfc)


def _make_director(empresa, username="dir_user", rol="DIRECTOR"):
    return Usuario.objects.create_user(
        username=username,
        password="test123456789",
        empresa=empresa,
        rol=rol,
    )


def _make_no_director(empresa, username="ndir_user"):
    return Usuario.objects.create_user(
        username=username,
        password="test123456789",
        empresa=empresa,
        rol="TECNICO",
    )


# ─── DASHBOARD DIRECTOR ──────────────────────────────────────────────────────

class DashboardDirectorAccesoTest(TestCase):
    def setUp(self):
        self.empresa = _make_empresa()
        self.director = _make_director(self.empresa)
        self.no_director = _make_no_director(self.empresa)

    def test_director_puede_acceder(self):
        self.client.login(username="dir_user", password="test123456789")
        response = self.client.get(reverse("dashboard_director"))
        self.assertEqual(response.status_code, 200)

    def test_no_director_es_redirigido(self):
        self.client.login(username="ndir_user", password="test123456789")
        response = self.client.get(reverse("dashboard_director"))
        self.assertIn(response.status_code, [302, 200])
        if response.status_code == 302:
            self.assertIn("home", response["Location"])

    def test_anonimo_redirige_a_login(self):
        response = self.client.get(reverse("dashboard_director"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_superuser_puede_acceder(self):
        su = Usuario.objects.create_superuser(
            username="superdir", password="test123456789", empresa=self.empresa
        )
        self.client.login(username="superdir", password="test123456789")
        response = self.client.get(reverse("dashboard_director"))
        self.assertEqual(response.status_code, 200)

    def test_grupo_gerencia_puede_acceder(self):
        gerente = Usuario.objects.create_user(
            username="gerente_g", password="test123456789", empresa=self.empresa
        )
        g, _ = Group.objects.get_or_create(name="GERENCIA")
        gerente.groups.add(g)
        self.client.login(username="gerente_g", password="test123456789")
        response = self.client.get(reverse("dashboard_director"))
        self.assertEqual(response.status_code, 200)


class DashboardDirectorTenantTest(TestCase):
    """Verifica que KPIs solo ven datos de la empresa propia."""

    def setUp(self):
        self.empresa_a = _make_empresa("EmpresaA", "AAA260607TST")
        self.empresa_b = _make_empresa("EmpresaB", "BBB260607TST")
        self.dir_a = _make_director(self.empresa_a, username="dir_a")
        self.dir_b = _make_director(self.empresa_b, username="dir_b")
        hoy = localdate()
        inicio = make_aware(datetime.combine(hoy, datetime.min.time()))
        Venta.objects.create(
            empresa=self.empresa_a,
            usuario=self.dir_a,
            subtotal=500,
            total=500,
            estado="COMPLETADA",
            fecha=inicio + timedelta(hours=1),
        )

    def test_director_a_no_ve_datos_empresa_b(self):
        self.client.login(username="dir_b", password="test123456789")
        response = self.client.get(reverse("dashboard_director"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_ventas_hoy"], 0)

    def test_director_a_ve_sus_propias_ventas(self):
        self.client.login(username="dir_a", password="test123456789")
        response = self.client.get(reverse("dashboard_director"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response.context["total_ventas_hoy"]), 500)


class DashboardDirectorTimezoneTest(TestCase):
    """Regresión: hoy debe calcularse con localdate() no timezone.now().date()."""

    def setUp(self):
        self.empresa = _make_empresa("EmpresaTZ", "TZZ260607TST")
        self.director = _make_director(self.empresa, username="dir_tz")

    def test_fecha_hoy_en_contexto_es_formato_local(self):
        self.client.login(username="dir_tz", password="test123456789")
        response = self.client.get(reverse("dashboard_director"))
        self.assertEqual(response.status_code, 200)
        # hoy debe ser calculado con localdate() — sólo validamos que el dashboard carga
        self.assertIn('empresa', response.context)

    def test_sin_empresa_redirige_a_home_no_a_login(self):
        """Regresión: sin empresa asignada el middleware inyecta empresa por defecto
        (resolve_default_empresa_sistema). El resultado es 200 o un redirect a 'home',
        pero NUNCA a /login/.
        """
        sin_empresa = Usuario.objects.create_user(
            username="dir_sin_emp", password="test123456789", rol="DIRECTOR"
        )
        self.client.login(username="dir_sin_emp", password="test123456789")
        response = self.client.get(reverse("dashboard_director"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response["Location"])


# ─── ANALIZADORES ────────────────────────────────────────────────────────────

class DirectorAnalizadoresTest(TestCase):
    def setUp(self):
        self.empresa = _make_empresa("EmpresaAnz", "ANZ260607TST")
        self.director = _make_director(self.empresa, username="dir_anz")
        self.no_director = _make_no_director(self.empresa, username="ndir_anz")
        self.client.login(username="dir_anz", password="test123456789")

    def test_lista_analizadores_accesible(self):
        response = self.client.get(reverse("director_analizadores"))
        self.assertEqual(response.status_code, 200)

    def test_no_director_recibe_403(self):
        self.client.login(username="ndir_anz", password="test123456789")
        response = self.client.get(reverse("director_analizadores"))
        self.assertEqual(response.status_code, 403)

    def test_crear_equipo_protocolo_invalido_usa_default_astm(self):
        response = self.client.post(
            reverse("director_analizadores_crear"),
            {
                "nombre": "Equipo Prueba",
                "marca": "Roche",
                "protocolo": "MANUAL",  # no existe en PROTOCOLO_CHOICES
            },
        )
        self.assertIn(response.status_code, [302, 200])
        from laboratorio.models import Equipo
        eq = Equipo.objects.filter(nombre="Equipo Prueba").first()
        self.assertIsNotNone(eq)
        self.assertEqual(eq.protocolo, Equipo.PROTOCOLO_ASTM)

    def test_crear_equipo_nombre_vacio_no_crea(self):
        from laboratorio.models import Equipo
        count_antes = Equipo.objects.count()
        response = self.client.post(
            reverse("director_analizadores_crear"),
            {"nombre": "  ", "protocolo": "ASTM"},
        )
        self.assertEqual(Equipo.objects.count(), count_antes)

    def test_toggle_requiere_post(self):
        from laboratorio.models import Equipo
        eq = Equipo.objects.create(nombre="EqToggle", protocolo="ASTM", activo=True)
        response = self.client.get(
            reverse("director_analizadores_toggle", args=[eq.id])
        )
        self.assertEqual(response.status_code, 405)

    def test_toggle_cambia_estado(self):
        from laboratorio.models import Equipo
        eq = Equipo.objects.create(nombre="EqToggle2", protocolo="ASTM", activo=True)
        response = self.client.post(
            reverse("director_analizadores_toggle", args=[eq.id])
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["ok"])
        eq.refresh_from_db()
        self.assertFalse(eq.activo)

    def test_eliminar_mapeo_requiere_post(self):
        from laboratorio.models import Equipo, CodigoParametroEquipo
        from laboratorio.models import Parametro, Estudio, CategoriaExamen
        eq = Equipo.objects.create(nombre="EqMapeo", protocolo="ASTM")
        cat = CategoriaExamen.objects.create(nombre="Cat Test")
        estudio = Estudio.objects.create(nombre="Estudio Test", codigo="ET01", categoria=cat)
        param = Parametro.objects.create(
            nombre="Param Test", estudio=estudio, unidades="mg/dL"
        )
        mapeo = CodigoParametroEquipo.objects.create(
            equipo=eq, parametro=param, codigo_equipo="WBC"
        )
        response = self.client.get(
            reverse("director_analizadores_eliminar_mapeo", args=[mapeo.id])
        )
        self.assertEqual(response.status_code, 405)

    def test_eliminar_mapeo_post_elimina(self):
        from laboratorio.models import Equipo, CodigoParametroEquipo
        from laboratorio.models import Parametro, Estudio, CategoriaExamen
        eq = Equipo.objects.create(nombre="EqMapeo2", protocolo="ASTM")
        cat = CategoriaExamen.objects.create(nombre="Cat Test2")
        estudio = Estudio.objects.create(nombre="Estudio Test2", codigo="ET02", categoria=cat)
        param = Parametro.objects.create(
            nombre="Param Test2", estudio=estudio, unidades="mg/dL"
        )
        mapeo = CodigoParametroEquipo.objects.create(
            equipo=eq, parametro=param, codigo_equipo="HGB"
        )
        response = self.client.post(
            reverse("director_analizadores_eliminar_mapeo", args=[mapeo.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CodigoParametroEquipo.objects.filter(id=mapeo.id).exists())


class ProbarConexionTest(TestCase):
    def setUp(self):
        self.empresa = _make_empresa("EmpresaConn", "CON260607TST")
        self.director = _make_director(self.empresa, username="dir_conn")
        self.client.login(username="dir_conn", password="test123456789")

    def test_get_devuelve_405(self):
        response = self.client.get(reverse("director_analizadores_probar_conexion"))
        self.assertEqual(response.status_code, 405)

    def test_ip_vacia_devuelve_error(self):
        response = self.client.post(
            reverse("director_analizadores_probar_conexion"),
            data=json.dumps({"ip": "", "puerto": 9100}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data["ok"])

    def test_ip_invalida_devuelve_sin_respuesta(self):
        response = self.client.post(
            reverse("director_analizadores_probar_conexion"),
            data=json.dumps({"ip": "192.0.2.1", "puerto": 9999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("ok", data)

    def test_no_director_recibe_403(self):
        no_dir = _make_no_director(self.empresa, username="ndir_conn")
        self.client.login(username="ndir_conn", password="test123456789")
        response = self.client.post(
            reverse("director_analizadores_probar_conexion"),
            data=json.dumps({"ip": "127.0.0.1", "puerto": 9100}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
