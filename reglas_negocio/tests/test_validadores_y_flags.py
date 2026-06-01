"""Cobertura mínima: triple llave, pánico, flags en ReglaNegocio."""
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Empresa
from core.services.feature_flags import activar, flag_activo
from reglas_negocio.models import EjecucionRegla, ReglaNegocio
from reglas_negocio.validadores import (
    requiere_doble_validacion,
    validar_triple_llave,
    validar_valor_panico,
)

User = get_user_model()


class _FakeQS:
    """Simula QuerySet mínimo para _llave_validacion_tecnica y slicing [:500]."""

    def __init__(self, items):
        self._items = list(items)

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return _FakeQS(self._items[key])
        return self._items[key]

    def exists(self):
        return bool(self._items)

    def first(self):
        return self._items[0] if self._items else None

    def filter(self, **kwargs):
        if kwargs.get('validado') is False:
            return _FakeQS([x for x in self._items if not getattr(x, 'validado', False)])
        return _FakeQS(self._items)


class _FakeResultadosMgr:
    def __init__(self, items):
        self._items = items

    def all(self):
        return _FakeQS(self._items)


class ValidadoresTripleLlaveTests(TestCase):
    def test_legacy_orden_usuario_valido_y_pago_ok(self):
        # _llave_validacion_tecnica legacy: exige hasattr(orden, 'usuario_valido')
        orden = SimpleNamespace(
            estado_pago='PAGADO',
            usuario_valido=object(),
            usuario_valido_id=1,
            paciente=SimpleNamespace(telefono_verificado=True),
        )
        ok, errores = validar_triple_llave(orden)
        self.assertTrue(ok)
        self.assertEqual(errores, [])

    def test_orden_no_pagada_falla(self):
        orden = SimpleNamespace(
            estado_pago='PENDIENTE',
            usuario_valido=object(),
            usuario_valido_id=1,
            paciente=SimpleNamespace(telefono_verificado=True),
        )
        ok, errores = validar_triple_llave(orden)
        self.assertFalse(ok)
        self.assertTrue(any('pagada' in e.lower() for e in errores))

    def test_ods_resultados_todos_validados_ok(self):
        r = SimpleNamespace(validado=True)
        orden = SimpleNamespace(
            estado_pago=True,
            resultados=_FakeResultadosMgr([r]),
            paciente=SimpleNamespace(telefono_verificado=True),
        )
        ok, errores = validar_triple_llave(orden)
        self.assertTrue(ok)
        self.assertEqual(errores, [])

    def test_ods_hay_resultado_sin_validar_falla(self):
        orden = SimpleNamespace(
            estado_pago=True,
            resultados=_FakeResultadosMgr(
                [SimpleNamespace(validado=True), SimpleNamespace(validado=False)]
            ),
            paciente=SimpleNamespace(telefono_verificado=True),
        )
        ok, errores = validar_triple_llave(orden)
        self.assertFalse(ok)
        self.assertTrue(any('validada' in e.lower() for e in errores))

    def test_telefono_no_verificado_falla(self):
        orden = SimpleNamespace(
            estado_pago='PAGADO',
            usuario_valido=object(),
            usuario_valido_id=1,
            paciente=SimpleNamespace(telefono_verificado=False),
        )
        ok, errores = validar_triple_llave(orden)
        self.assertFalse(ok)
        self.assertTrue(any('teléfono' in e.lower() for e in errores))


class ValidadoresPanicoTests(TestCase):
    def test_es_critico_dispara_panico(self):
        res = SimpleNamespace(es_critico=True, valor='999')
        ok, msg = validar_valor_panico(res)
        self.assertTrue(ok)
        self.assertIn('PÁNICO', msg)

    def test_rango_estudio_fuera_de_limites(self):
        estudio = SimpleNamespace(rango_panico_min=0.0, rango_panico_max=10.0)
        res = SimpleNamespace(es_critico=False, valor_obtenido='20', estudio=estudio)
        ok, msg = validar_valor_panico(res)
        self.assertTrue(ok)
        self.assertIn('PÁNICO', msg)

    def test_requiere_doble_validacion_si_hay_panico(self):
        estudio = SimpleNamespace(rango_panico_min=0.0, rango_panico_max=1.0)
        res = SimpleNamespace(es_critico=False, valor_obtenido='50', estudio=estudio)
        orden = SimpleNamespace(resultados=_FakeResultadosMgr([res]))
        self.assertTrue(requiere_doble_validacion(orden))


class ReglaNegocioModeloYFlagsTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='RN Test Co', rfc='RNTE990101XXX')
        self.user = User.objects.create_user(
            username='rn_flags_tester',
            password='x',
            empresa=self.empresa,
            rol='ADMIN',
        )

    def test_str_regla_negocio(self):
        r = ReglaNegocio.objects.create(
            empresa=self.empresa,
            nombre='Regla demo',
            codigo='RN_TEST_STR_001',
            activa=True,
        )
        s = str(r)
        self.assertIn('ACTIVA', s)
        self.assertIn('RN_TEST_STR_001', s)

    def test_ejecucion_regla_str(self):
        regla = ReglaNegocio.objects.create(
            empresa=self.empresa,
            nombre='R',
            codigo='RN_TEST_EJEC_001',
        )
        ej = EjecucionRegla.objects.create(regla=regla, resultado=True, mensaje='ok')
        self.assertIn('OK', str(ej))

    def test_activar_flag_persiste_y_flag_activo_lo_ve(self):
        codigo = 'ISO_STRICT_MODE'
        self.assertFalse(flag_activo(codigo, self.empresa))
        self.assertTrue(activar(codigo, self.empresa, self.user))
        self.assertTrue(flag_activo(codigo, self.empresa))
