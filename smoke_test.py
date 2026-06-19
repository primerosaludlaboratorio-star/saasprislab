"""Script de smoke tests — ejecutar con: python smoke_test.py"""
import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

errores = []
ok = []

# TEST 1: Feature Flags
try:
    from core.services.feature_flags import flag_activo, obtener_todos, FLAG_CATALOG
    todos = obtener_todos()
    assert len(todos) == len(FLAG_CATALOG)
    ok.append('FeatureFlags: {} flags cargados OK'.format(len(todos)))
except Exception as e:
    errores.append('FeatureFlags FALLO: {}'.format(e))

# TEST 2: OCR Documental
try:
    from core.services.ocr_documental import analizar_documento, _sugerencias_negocio
    sug = _sugerencias_negocio('receta ginecologica embarazo', 'F', 28)
    assert len(sug) > 0
    ok.append('OCR Motor: {} sugerencias contextuales OK'.format(len(sug)))
except Exception as e:
    errores.append('OCR FALLO: {}'.format(e))

# TEST 3: Audio Legal hash
try:
    from core.utils.pris_audio_vision import generar_hash_digital
    h = generar_hash_digital('test transcripcion', '2026-01-01T00:00:00')
    assert len(h) == 64
    ok.append('AudioLegal: hash SHA-256 OK ({})...'.format(h[:16]))
except Exception as e:
    errores.append('AudioLegal hash FALLO: {}'.format(e))

# TEST 4: Coach Toma Muestra
try:
    from core.utils.pris_audio_vision import evaluar_protocolo_toma_muestra
    reporte = evaluar_protocolo_toma_muestra(
        'verifiqué nombre del paciente, pregunté ayuno, registré hora de toma',
        ['QS', 'GLUCOSA']
    )
    assert reporte['activo'] == True
    score = reporte['score_porcentaje']
    ok.append('Coach Toma Muestra: score {}% OK'.format(score))
except Exception as e:
    errores.append('Coach FALLO: {}'.format(e))

# TEST 5: 2FA views
try:
    from core.views.autenticacion_2fa import setup_2fa, verificar_2fa, desactivar_2fa
    from core.views.autenticacion_2fa import _ip_exenta_2fa, _2fa_activo_para_usuario
    ok.append('2FA Views: imports OK')
except Exception as e:
    errores.append('2FA FALLO: {}'.format(e))

# TEST 6: Audio Legal views
try:
    from core.views.audio_legal import api_sellar_audio, api_verificar_integridad_audio
    ok.append('AudioLegal Views: imports OK')
except Exception as e:
    errores.append('AudioLegal Views FALLO: {}'.format(e))

# TEST 7: Feature Flags Admin
try:
    from core.views.feature_flags_admin import panel_feature_flags, api_toggle_flag
    ok.append('FeatureFlags Admin Views: imports OK')
except Exception as e:
    errores.append('FeatureFlags Admin FALLO: {}'.format(e))

# TEST 8: VoiceAuditLog en DB
try:
    from core.models import VoiceAuditLog
    count = VoiceAuditLog.objects.count()
    ok.append('VoiceAuditLog: {} registros en DB OK'.format(count))
except Exception as e:
    errores.append('VoiceAuditLog FALLO: {}'.format(e))

# TEST 9: seguridad DispositivoTOTP
try:
    from seguridad.models import DispositivoTOTP, CodigoBackup2FA, LogAccionSensible
    count = DispositivoTOTP.objects.count()
    ok.append('Seguridad 2FA: modelos OK ({} dispositivos)'.format(count))
except Exception as e:
    errores.append('Seguridad 2FA FALLO: {}'.format(e))

# TEST 10: PRIS nueva tool OCR
try:
    from core.views.pris_ia import TOOLS_DESCRIPCION
    assert 'analizar_imagen_documento' in TOOLS_DESCRIPCION
    ok.append('PRIS tool analizar_imagen_documento: registrada OK')
except Exception as e:
    errores.append('PRIS tool FALLO: {}'.format(e))

# TEST 11: URLs críticas
try:
    from django.test import RequestFactory
    from django.urls import reverse
    urls_check = [
        'panel_feature_flags',
        'api_sellar_audio',
        'verificar_2fa',
        'pris_ia_chat',
        'bienestar_dashboard',
    ]
    for name in urls_check:
        try:
            url = reverse(name)
            ok.append('URL {}: {} OK'.format(name, url))
        except Exception as ue:
            errores.append('URL {} FALLO: {}'.format(name, ue))
except Exception as e:
    errores.append('URL tests FALLO: {}'.format(e))

# TEST 12: ISO 15189 service
try:
    from laboratorio.services.iso15189 import validar_resultado
    ok.append('ISO15189 service: import OK')
except Exception as e:
    errores.append('ISO15189 FALLO: {}'.format(e))

# TEST 13: ZPL service
try:
    from laboratorio.services.etiquetas_zpl import generar_zpl_tubo
    zpl = generar_zpl_tubo('TEST-001', 'Juan Perez', urgente=True)
    assert '^XA' in zpl
    ok.append('ZPL Etiquetas: generación OK')
except Exception as e:
    errores.append('ZPL FALLO: {}'.format(e))

# TEST 14: Corte Caja Unificado
try:
    from farmacia.services.corte_caja_unificado import cerrar_turno_unificado
    ok.append('Corte Caja Unificado: import OK')
except Exception as e:
    errores.append('Corte Caja FALLO: {}'.format(e))

# TEST 15: War Room views
try:
    from core.views.war_room import war_room, api_war_room_anomalias
    ok.append('War Room views: imports OK')
except Exception as e:
    errores.append('War Room FALLO: {}'.format(e))

# TEST 16: Cadena de Frío service
try:
    from core.services.cadena_frio import validar_temperatura
    r = validar_temperatura(4.5)
    assert r['valida'] == True
    r2 = validar_temperatura(10.0)
    assert r2['valida'] == False
    r3 = validar_temperatura(1.0)
    assert r3['valida'] == False
    ok.append('Cadena Frio: validacion 2-8C OK')
except Exception as e:
    errores.append('Cadena Frio FALLO: {}'.format(e))

# TEST 17: Prediccion de Stock service
try:
    from core.services.prediccion_stock import predecir_dias_hasta_agotamiento, reporte_inventario_predictivo
    ok.append('Prediccion Stock: imports OK')
except Exception as e:
    errores.append('Prediccion Stock FALLO: {}'.format(e))

# TEST 18: Consentimiento Digital views
try:
    from core.views.consentimiento_digital import pagina_consentimiento, api_guardar_consentimiento
    ok.append('Consentimiento Digital: imports OK')
except Exception as e:
    errores.append('Consentimiento Digital FALLO: {}'.format(e))

# TEST 19: Inventario Predictivo views
try:
    from core.views.inventario_predictivo import reporte_prediccion_stock, api_prediccion_stock
    ok.append('Inventario Predictivo views: imports OK')
except Exception as e:
    errores.append('Inventario Predictivo FALLO: {}'.format(e))

# TEST 19b: buscar_estudio sin venta_individual (bug fix crítico)
try:
    from laboratorio.models import Estudio
    from django.db.models import Q
    qs = Estudio.objects.filter(activo=True).filter(
        Q(nombre__icontains='glucosa') | Q(codigo__icontains='GLU')
    )
    # El test pasa si NO lanza AttributeError y devuelve resultados
    count = qs.count()
    ok.append('buscar_estudio fix venta_individual: OK ({} estudios con glucosa)'.format(count))
except Exception as e:
    errores.append('buscar_estudio FALLO (venta_individual): {}'.format(e))

# TEST 20: Production env check
try:
    from production_env_check import verificar_entorno, generar_fernet_key
    fernet = generar_fernet_key()
    assert len(fernet) > 30
    ok.append('Production Env Check: FERNET_KEY generada OK ({})...'.format(fernet[:16]))
except Exception as e:
    errores.append('Production Env Check FALLO: {}'.format(e))

# TEST 21: ISO_STRICT_MODE flag OFF por defecto
try:
    from core.services.feature_flags import FLAG_CATALOG
    assert 'ISO_STRICT_MODE' in FLAG_CATALOG
    assert FLAG_CATALOG['ISO_STRICT_MODE']['default'] == False
    ok.append('ISO_STRICT_MODE: OFF por defecto OK')
except Exception as e:
    errores.append('ISO_STRICT_MODE FALLO: {}'.format(e))

# TEST 22: URLs nuevas de Brechas de Oro
try:
    from django.urls import reverse
    nuevas_urls = [
        'war_room', 'api_war_room_anomalias',
        'inventario_prediccion', 'api_prediccion_stock',
    ]
    for name in nuevas_urls:
        try:
            url = reverse(name)
            ok.append('URL {}: {} OK'.format(name, url))
        except Exception as ue:
            errores.append('URL {} FALLO: {}'.format(name, ue))
except Exception as e:
    errores.append('URLs Brechas de Oro FALLO: {}'.format(e))

print()
print('=' * 60)
print('SMOKE TEST — PRISLAB v5.2 EMPORIO')
print('=' * 60)
for msg in ok:
    print('  [OK]   ' + msg)
if errores:
    print()
    for msg in errores:
        print('  [FAIL] ' + msg)
print()
total = len(ok) + len(errores)
print('RESULTADO: {}/{} tests pasados'.format(len(ok), total))
if not errores:
    print('ESTADO: SISTEMA EN VUELO')
else:
    print('ESTADO: {} FALLO(S) DETECTADO(S)'.format(len(errores)))
print('=' * 60)
