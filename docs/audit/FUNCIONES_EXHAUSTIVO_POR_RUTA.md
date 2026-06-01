# FUNCIONES_EXHAUSTIVO — Inventario por ruta (URLconf)

**Origen:** `docs/audit/INVENTARIO_URLS.txt` (mismo timestamp que el JSON).
**Total de rutas registradas:** 1784

Cada fila es una entrada resuelta por Django: path + nombre de ruta + vista.

## Prefijo `/admin/` (1043 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/admin/` | index | `django.contrib.admin.sites.index` | ui |
| `/admin/(?P<url>.*)$` | — | `django.contrib.admin.sites.catch_all_view` | ui |
| `/admin/^(?P<app_label>auth\|core\|farmacia\|pacientes\|laboratorio\|lims\|seguridad\|iot\|ia\|reglas_negocio\|marketing\|consultorio\|logistica\|inventario\|mantenimiento\|bienestar\|contabilidad)/$` | app_list | `django.contrib.admin.sites.app_index` | ui |
| `/admin/auth/group/` | auth_group_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/auth/group/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/auth/group/<path:object_id>/change/` | auth_group_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/auth/group/<path:object_id>/delete/` | auth_group_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/auth/group/<path:object_id>/history/` | auth_group_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/auth/group/add/` | auth_group_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/autocomplete/` | autocomplete | `django.contrib.admin.sites.autocomplete_view` | ui |
| `/admin/bienestar/diarioemocional/` | bienestar_diarioemocional_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/bienestar/diarioemocional/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/bienestar/diarioemocional/<path:object_id>/change/` | bienestar_diarioemocional_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/bienestar/diarioemocional/<path:object_id>/delete/` | bienestar_diarioemocional_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/bienestar/diarioemocional/<path:object_id>/history/` | bienestar_diarioemocional_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/bienestar/diarioemocional/add/` | bienestar_diarioemocional_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/bienestar/recursocrecimiento/` | bienestar_recursocrecimiento_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/bienestar/recursocrecimiento/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/bienestar/recursocrecimiento/<path:object_id>/change/` | bienestar_recursocrecimiento_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/bienestar/recursocrecimiento/<path:object_id>/delete/` | bienestar_recursocrecimiento_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/bienestar/recursocrecimiento/<path:object_id>/history/` | bienestar_recursocrecimiento_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/bienestar/recursocrecimiento/add/` | bienestar_recursocrecimiento_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/agendacita/` | consultorio_agendacita_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/agendacita/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/agendacita/<path:object_id>/change/` | consultorio_agendacita_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/agendacita/<path:object_id>/delete/` | consultorio_agendacita_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/agendacita/<path:object_id>/history/` | consultorio_agendacita_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/agendacita/add/` | consultorio_agendacita_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/analisispatron/` | consultorio_analisispatron_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/analisispatron/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/analisispatron/<path:object_id>/change/` | consultorio_analisispatron_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/analisispatron/<path:object_id>/delete/` | consultorio_analisispatron_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/analisispatron/<path:object_id>/history/` | consultorio_analisispatron_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/analisispatron/add/` | consultorio_analisispatron_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/archivoadjuntoconsulta/` | consultorio_archivoadjuntoconsulta_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/archivoadjuntoconsulta/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/archivoadjuntoconsulta/<path:object_id>/change/` | consultorio_archivoadjuntoconsulta_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/archivoadjuntoconsulta/<path:object_id>/delete/` | consultorio_archivoadjuntoconsulta_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/archivoadjuntoconsulta/<path:object_id>/history/` | consultorio_archivoadjuntoconsulta_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/archivoadjuntoconsulta/add/` | consultorio_archivoadjuntoconsulta_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/cajaconsultorio/` | consultorio_cajaconsultorio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/cajaconsultorio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/cajaconsultorio/<path:object_id>/change/` | consultorio_cajaconsultorio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/cajaconsultorio/<path:object_id>/delete/` | consultorio_cajaconsultorio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/cajaconsultorio/<path:object_id>/history/` | consultorio_cajaconsultorio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/cajaconsultorio/add/` | consultorio_cajaconsultorio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/cobroconsulta/` | consultorio_cobroconsulta_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/cobroconsulta/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/cobroconsulta/<path:object_id>/change/` | consultorio_cobroconsulta_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/cobroconsulta/<path:object_id>/delete/` | consultorio_cobroconsulta_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/cobroconsulta/<path:object_id>/history/` | consultorio_cobroconsulta_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/cobroconsulta/add/` | consultorio_cobroconsulta_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/configuracionmedico/` | consultorio_configuracionmedico_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/configuracionmedico/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/configuracionmedico/<path:object_id>/change/` | consultorio_configuracionmedico_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/configuracionmedico/<path:object_id>/delete/` | consultorio_configuracionmedico_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/configuracionmedico/<path:object_id>/history/` | consultorio_configuracionmedico_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/configuracionmedico/add/` | consultorio_configuracionmedico_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/consultamedica/` | consultorio_consultamedica_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/consultamedica/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/consultamedica/<path:object_id>/change/` | consultorio_consultamedica_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/consultamedica/<path:object_id>/delete/` | consultorio_consultamedica_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/consultamedica/<path:object_id>/history/` | consultorio_consultamedica_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/consultamedica/add/` | consultorio_consultamedica_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/encuestasatisfaccion/` | consultorio_encuestasatisfaccion_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/encuestasatisfaccion/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/encuestasatisfaccion/<path:object_id>/change/` | consultorio_encuestasatisfaccion_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/encuestasatisfaccion/<path:object_id>/delete/` | consultorio_encuestasatisfaccion_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/encuestasatisfaccion/<path:object_id>/history/` | consultorio_encuestasatisfaccion_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/encuestasatisfaccion/add/` | consultorio_encuestasatisfaccion_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/imagenultrasonido/` | consultorio_imagenultrasonido_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/imagenultrasonido/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/imagenultrasonido/<path:object_id>/change/` | consultorio_imagenultrasonido_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/imagenultrasonido/<path:object_id>/delete/` | consultorio_imagenultrasonido_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/imagenultrasonido/<path:object_id>/history/` | consultorio_imagenultrasonido_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/imagenultrasonido/add/` | consultorio_imagenultrasonido_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/incidenciasentinel/` | consultorio_incidenciasentinel_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/incidenciasentinel/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/incidenciasentinel/<path:object_id>/change/` | consultorio_incidenciasentinel_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/incidenciasentinel/<path:object_id>/delete/` | consultorio_incidenciasentinel_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/incidenciasentinel/<path:object_id>/history/` | consultorio_incidenciasentinel_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/incidenciasentinel/add/` | consultorio_incidenciasentinel_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/listaespera/` | consultorio_listaespera_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/listaespera/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/listaespera/<path:object_id>/change/` | consultorio_listaespera_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/listaespera/<path:object_id>/delete/` | consultorio_listaespera_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/listaespera/<path:object_id>/history/` | consultorio_listaespera_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/listaespera/add/` | consultorio_listaespera_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/notamedica/` | consultorio_notamedica_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/notamedica/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/notamedica/<path:object_id>/change/` | consultorio_notamedica_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/notamedica/<path:object_id>/delete/` | consultorio_notamedica_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/notamedica/<path:object_id>/history/` | consultorio_notamedica_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/notamedica/add/` | consultorio_notamedica_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/reporteultrasonido/` | consultorio_reporteultrasonido_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/reporteultrasonido/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/reporteultrasonido/<path:object_id>/change/` | consultorio_reporteultrasonido_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/reporteultrasonido/<path:object_id>/delete/` | consultorio_reporteultrasonido_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/reporteultrasonido/<path:object_id>/history/` | consultorio_reporteultrasonido_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/reporteultrasonido/add/` | consultorio_reporteultrasonido_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/seguimientotratamiento/` | consultorio_seguimientotratamiento_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/seguimientotratamiento/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/seguimientotratamiento/<path:object_id>/change/` | consultorio_seguimientotratamiento_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/seguimientotratamiento/<path:object_id>/delete/` | consultorio_seguimientotratamiento_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/seguimientotratamiento/<path:object_id>/history/` | consultorio_seguimientotratamiento_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/seguimientotratamiento/add/` | consultorio_seguimientotratamiento_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/somatometria/` | consultorio_somatometria_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/somatometria/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/somatometria/<path:object_id>/change/` | consultorio_somatometria_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/somatometria/<path:object_id>/delete/` | consultorio_somatometria_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/somatometria/<path:object_id>/history/` | consultorio_somatometria_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/somatometria/add/` | consultorio_somatometria_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/vademecum/` | consultorio_vademecum_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/vademecum/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/vademecum/<path:object_id>/change/` | consultorio_vademecum_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/vademecum/<path:object_id>/delete/` | consultorio_vademecum_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/vademecum/<path:object_id>/history/` | consultorio_vademecum_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/vademecum/add/` | consultorio_vademecum_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/consultorio/valeliquidacion/` | consultorio_valeliquidacion_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/consultorio/valeliquidacion/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/consultorio/valeliquidacion/<path:object_id>/change/` | consultorio_valeliquidacion_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/consultorio/valeliquidacion/<path:object_id>/delete/` | consultorio_valeliquidacion_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/consultorio/valeliquidacion/<path:object_id>/history/` | consultorio_valeliquidacion_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/consultorio/valeliquidacion/add/` | consultorio_valeliquidacion_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/contabilidad/clientefacturacion/` | contabilidad_clientefacturacion_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/contabilidad/clientefacturacion/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/contabilidad/clientefacturacion/<path:object_id>/change/` | contabilidad_clientefacturacion_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/contabilidad/clientefacturacion/<path:object_id>/delete/` | contabilidad_clientefacturacion_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/contabilidad/clientefacturacion/<path:object_id>/history/` | contabilidad_clientefacturacion_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/contabilidad/clientefacturacion/add/` | contabilidad_clientefacturacion_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/contabilidad/conceptofactura/` | contabilidad_conceptofactura_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/contabilidad/conceptofactura/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/contabilidad/conceptofactura/<path:object_id>/change/` | contabilidad_conceptofactura_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/contabilidad/conceptofactura/<path:object_id>/delete/` | contabilidad_conceptofactura_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/contabilidad/conceptofactura/<path:object_id>/history/` | contabilidad_conceptofactura_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/contabilidad/conceptofactura/add/` | contabilidad_conceptofactura_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/contabilidad/facturacfdi/` | contabilidad_facturacfdi_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/contabilidad/facturacfdi/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/contabilidad/facturacfdi/<path:object_id>/change/` | contabilidad_facturacfdi_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/contabilidad/facturacfdi/<path:object_id>/delete/` | contabilidad_facturacfdi_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/contabilidad/facturacfdi/<path:object_id>/history/` | contabilidad_facturacfdi_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/contabilidad/facturacfdi/add/` | contabilidad_facturacfdi_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/ajusteinventario/` | core_ajusteinventario_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/ajusteinventario/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/ajusteinventario/<path:object_id>/change/` | core_ajusteinventario_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/ajusteinventario/<path:object_id>/delete/` | core_ajusteinventario_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/ajusteinventario/<path:object_id>/history/` | core_ajusteinventario_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/ajusteinventario/add/` | core_ajusteinventario_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/alertabienestar/` | core_alertabienestar_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/alertabienestar/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/alertabienestar/<path:object_id>/change/` | core_alertabienestar_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/alertabienestar/<path:object_id>/delete/` | core_alertabienestar_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/alertabienestar/<path:object_id>/history/` | core_alertabienestar_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/alertabienestar/add/` | core_alertabienestar_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/antecedente/` | core_antecedente_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/antecedente/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/antecedente/<path:object_id>/change/` | core_antecedente_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/antecedente/<path:object_id>/delete/` | core_antecedente_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/antecedente/<path:object_id>/history/` | core_antecedente_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/antecedente/add/` | core_antecedente_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/auditlog/` | core_auditlog_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/auditlog/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/auditlog/<path:object_id>/change/` | core_auditlog_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/auditlog/<path:object_id>/delete/` | core_auditlog_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/auditlog/<path:object_id>/history/` | core_auditlog_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/auditlog/add/` | core_auditlog_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/bitacora39a/` | core_bitacora39a_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/bitacora39a/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/bitacora39a/<path:object_id>/change/` | core_bitacora39a_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/bitacora39a/<path:object_id>/delete/` | core_bitacora39a_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/bitacora39a/<path:object_id>/history/` | core_bitacora39a_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/bitacora39a/add/` | core_bitacora39a_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/bitacoratemperatura/` | core_bitacoratemperatura_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/bitacoratemperatura/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/bitacoratemperatura/<path:object_id>/change/` | core_bitacoratemperatura_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/bitacoratemperatura/<path:object_id>/delete/` | core_bitacoratemperatura_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/bitacoratemperatura/<path:object_id>/history/` | core_bitacoratemperatura_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/bitacoratemperatura/add/` | core_bitacoratemperatura_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/buzonquejas/` | core_buzonquejas_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/buzonquejas/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/buzonquejas/<path:object_id>/change/` | core_buzonquejas_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/buzonquejas/<path:object_id>/delete/` | core_buzonquejas_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/buzonquejas/<path:object_id>/history/` | core_buzonquejas_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/buzonquejas/add/` | core_buzonquejas_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/capsulasabiduria/` | core_capsulasabiduria_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/capsulasabiduria/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/capsulasabiduria/<path:object_id>/change/` | core_capsulasabiduria_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/capsulasabiduria/<path:object_id>/delete/` | core_capsulasabiduria_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/capsulasabiduria/<path:object_id>/history/` | core_capsulasabiduria_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/capsulasabiduria/add/` | core_capsulasabiduria_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/certificadomedico/` | core_certificadomedico_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/certificadomedico/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/certificadomedico/<path:object_id>/change/` | core_certificadomedico_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/certificadomedico/<path:object_id>/delete/` | core_certificadomedico_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/certificadomedico/<path:object_id>/history/` | core_certificadomedico_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/certificadomedico/add/` | core_certificadomedico_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/citamedica/` | core_citamedica_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/citamedica/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/citamedica/<path:object_id>/change/` | core_citamedica_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/citamedica/<path:object_id>/delete/` | core_citamedica_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/citamedica/<path:object_id>/history/` | core_citamedica_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/citamedica/add/` | core_citamedica_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/competencia/` | core_competencia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/competencia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/competencia/<path:object_id>/change/` | core_competencia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/competencia/<path:object_id>/delete/` | core_competencia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/competencia/<path:object_id>/history/` | core_competencia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/competencia/add/` | core_competencia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/configuracionmodulos/` | core_configuracionmodulos_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/configuracionmodulos/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/configuracionmodulos/<path:object_id>/change/` | core_configuracionmodulos_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/configuracionmodulos/<path:object_id>/delete/` | core_configuracionmodulos_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/configuracionmodulos/<path:object_id>/history/` | core_configuracionmodulos_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/configuracionmodulos/add/` | core_configuracionmodulos_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/consentimientoinformado/` | core_consentimientoinformado_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/consentimientoinformado/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/consentimientoinformado/<path:object_id>/change/` | core_consentimientoinformado_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/consentimientoinformado/<path:object_id>/delete/` | core_consentimientoinformado_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/consentimientoinformado/<path:object_id>/history/` | core_consentimientoinformado_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/consentimientoinformado/add/` | core_consentimientoinformado_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/consultamedica/` | core_consultamedica_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/consultamedica/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/consultamedica/<path:object_id>/change/` | core_consultamedica_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/consultamedica/<path:object_id>/delete/` | core_consultamedica_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/consultamedica/<path:object_id>/history/` | core_consultamedica_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/consultamedica/add/` | core_consultamedica_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/convenio/` | core_convenio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/convenio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/convenio/<path:object_id>/change/` | core_convenio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/convenio/<path:object_id>/delete/` | core_convenio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/convenio/<path:object_id>/history/` | core_convenio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/convenio/add/` | core_convenio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/conversacionbienestar/` | core_conversacionbienestar_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/conversacionbienestar/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/conversacionbienestar/<path:object_id>/change/` | core_conversacionbienestar_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/conversacionbienestar/<path:object_id>/delete/` | core_conversacionbienestar_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/conversacionbienestar/<path:object_id>/history/` | core_conversacionbienestar_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/conversacionbienestar/add/` | core_conversacionbienestar_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/cuentaporcobrar/` | core_cuentaporcobrar_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/cuentaporcobrar/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/cuentaporcobrar/<path:object_id>/change/` | core_cuentaporcobrar_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/cuentaporcobrar/<path:object_id>/delete/` | core_cuentaporcobrar_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/cuentaporcobrar/<path:object_id>/history/` | core_cuentaporcobrar_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/cuentaporcobrar/add/` | core_cuentaporcobrar_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/datosfiscales/` | core_datosfiscales_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/datosfiscales/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/datosfiscales/<path:object_id>/change/` | core_datosfiscales_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/datosfiscales/<path:object_id>/delete/` | core_datosfiscales_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/datosfiscales/<path:object_id>/history/` | core_datosfiscales_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/datosfiscales/add/` | core_datosfiscales_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/detalleorden/` | core_detalleorden_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/detalleorden/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/detalleorden/<path:object_id>/change/` | core_detalleorden_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/detalleorden/<path:object_id>/delete/` | core_detalleorden_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/detalleorden/<path:object_id>/history/` | core_detalleorden_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/detalleorden/add/` | core_detalleorden_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/detalleventa/` | core_detalleventa_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/detalleventa/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/detalleventa/<path:object_id>/change/` | core_detalleventa_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/detalleventa/<path:object_id>/delete/` | core_detalleventa_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/detalleventa/<path:object_id>/history/` | core_detalleventa_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/detalleventa/add/` | core_detalleventa_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/devolucionventa/` | core_devolucionventa_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/devolucionventa/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/devolucionventa/<path:object_id>/change/` | core_devolucionventa_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/devolucionventa/<path:object_id>/delete/` | core_devolucionventa_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/devolucionventa/<path:object_id>/history/` | core_devolucionventa_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/devolucionventa/add/` | core_devolucionventa_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/discountpolicy/` | core_discountpolicy_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/discountpolicy/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/discountpolicy/<path:object_id>/change/` | core_discountpolicy_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/discountpolicy/<path:object_id>/delete/` | core_discountpolicy_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/discountpolicy/<path:object_id>/history/` | core_discountpolicy_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/discountpolicy/add/` | core_discountpolicy_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/documentocapacitacion/` | core_documentocapacitacion_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/documentocapacitacion/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/documentocapacitacion/<path:object_id>/change/` | core_documentocapacitacion_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/documentocapacitacion/<path:object_id>/delete/` | core_documentocapacitacion_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/documentocapacitacion/<path:object_id>/history/` | core_documentocapacitacion_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/documentocapacitacion/add/` | core_documentocapacitacion_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/empleado/` | core_empleado_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/empleado/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/empleado/<path:object_id>/change/` | core_empleado_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/empleado/<path:object_id>/delete/` | core_empleado_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/empleado/<path:object_id>/history/` | core_empleado_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/empleado/add/` | core_empleado_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/empresa/` | core_empresa_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/empresa/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/empresa/<path:object_id>/change/` | core_empresa_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/empresa/<path:object_id>/delete/` | core_empresa_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/empresa/<path:object_id>/history/` | core_empresa_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/empresa/add/` | core_empresa_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/enviomaquila/` | core_enviomaquila_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/enviomaquila/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/enviomaquila/<path:object_id>/change/` | core_enviomaquila_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/enviomaquila/<path:object_id>/delete/` | core_enviomaquila_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/enviomaquila/<path:object_id>/history/` | core_enviomaquila_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/enviomaquila/add/` | core_enviomaquila_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/estudio/` | core_estudio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/estudio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/estudio/<path:object_id>/change/` | core_estudio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/estudio/<path:object_id>/delete/` | core_estudio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/estudio/<path:object_id>/history/` | core_estudio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/estudio/add/` | core_estudio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/estudioimagen/` | core_estudioimagen_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/estudioimagen/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/estudioimagen/<path:object_id>/change/` | core_estudioimagen_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/estudioimagen/<path:object_id>/delete/` | core_estudioimagen_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/estudioimagen/<path:object_id>/history/` | core_estudioimagen_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/estudioimagen/add/` | core_estudioimagen_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/evaluaciondesempeno/` | core_evaluaciondesempeno_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/evaluaciondesempeno/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/evaluaciondesempeno/<path:object_id>/change/` | core_evaluaciondesempeno_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/evaluaciondesempeno/<path:object_id>/delete/` | core_evaluaciondesempeno_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/evaluaciondesempeno/<path:object_id>/history/` | core_evaluaciondesempeno_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/evaluaciondesempeno/add/` | core_evaluaciondesempeno_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/facturasat/` | core_facturasat_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/facturasat/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/facturasat/<path:object_id>/change/` | core_facturasat_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/facturasat/<path:object_id>/delete/` | core_facturasat_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/facturasat/<path:object_id>/history/` | core_facturasat_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/facturasat/add/` | core_facturasat_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/gasto/` | core_gasto_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/gasto/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/gasto/<path:object_id>/change/` | core_gasto_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/gasto/<path:object_id>/delete/` | core_gasto_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/gasto/<path:object_id>/history/` | core_gasto_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/gasto/add/` | core_gasto_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/gastocaja/` | core_gastocaja_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/gastocaja/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/gastocaja/<path:object_id>/change/` | core_gastocaja_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/gastocaja/<path:object_id>/delete/` | core_gastocaja_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/gastocaja/<path:object_id>/history/` | core_gastocaja_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/gastocaja/add/` | core_gastocaja_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/gastooperativo/` | core_gastooperativo_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/gastooperativo/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/gastooperativo/<path:object_id>/change/` | core_gastooperativo_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/gastooperativo/<path:object_id>/delete/` | core_gastooperativo_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/gastooperativo/<path:object_id>/history/` | core_gastooperativo_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/gastooperativo/add/` | core_gastooperativo_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/historiaclinica/` | core_historiaclinica_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/historiaclinica/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/historiaclinica/<path:object_id>/change/` | core_historiaclinica_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/historiaclinica/<path:object_id>/delete/` | core_historiaclinica_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/historiaclinica/<path:object_id>/history/` | core_historiaclinica_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/historiaclinica/add/` | core_historiaclinica_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/horariotrabajo/` | core_horariotrabajo_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/horariotrabajo/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/horariotrabajo/<path:object_id>/change/` | core_horariotrabajo_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/horariotrabajo/<path:object_id>/delete/` | core_horariotrabajo_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/horariotrabajo/<path:object_id>/history/` | core_horariotrabajo_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/horariotrabajo/add/` | core_horariotrabajo_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/incidenciaasistencia/` | core_incidenciaasistencia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/incidenciaasistencia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/incidenciaasistencia/<path:object_id>/change/` | core_incidenciaasistencia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/incidenciaasistencia/<path:object_id>/delete/` | core_incidenciaasistencia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/incidenciaasistencia/<path:object_id>/history/` | core_incidenciaasistencia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/incidenciaasistencia/add/` | core_incidenciaasistencia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/incidenciaoperativa/` | core_incidenciaoperativa_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/incidenciaoperativa/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/incidenciaoperativa/<path:object_id>/change/` | core_incidenciaoperativa_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/incidenciaoperativa/<path:object_id>/delete/` | core_incidenciaoperativa_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/incidenciaoperativa/<path:object_id>/history/` | core_incidenciaoperativa_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/incidenciaoperativa/add/` | core_incidenciaoperativa_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/logaccesoexpediente/` | core_logaccesoexpediente_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/logaccesoexpediente/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/logaccesoexpediente/<path:object_id>/change/` | core_logaccesoexpediente_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/logaccesoexpediente/<path:object_id>/delete/` | core_logaccesoexpediente_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/logaccesoexpediente/<path:object_id>/history/` | core_logaccesoexpediente_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/logaccesoexpediente/add/` | core_logaccesoexpediente_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/lote/` | core_lote_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/lote/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/lote/<path:object_id>/change/` | core_lote_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/lote/<path:object_id>/delete/` | core_lote_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/lote/<path:object_id>/history/` | core_lote_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/lote/add/` | core_lote_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/mantenimientoequipo/` | core_mantenimientoequipo_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/mantenimientoequipo/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/mantenimientoequipo/<path:object_id>/change/` | core_mantenimientoequipo_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/mantenimientoequipo/<path:object_id>/delete/` | core_mantenimientoequipo_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/mantenimientoequipo/<path:object_id>/history/` | core_mantenimientoequipo_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/mantenimientoequipo/add/` | core_mantenimientoequipo_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/medico/` | core_medico_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/medico/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/medico/<path:object_id>/change/` | core_medico_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/medico/<path:object_id>/delete/` | core_medico_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/medico/<path:object_id>/history/` | core_medico_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/medico/add/` | core_medico_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/mensajeinterno/` | core_mensajeinterno_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/mensajeinterno/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/mensajeinterno/<path:object_id>/change/` | core_mensajeinterno_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/mensajeinterno/<path:object_id>/delete/` | core_mensajeinterno_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/mensajeinterno/<path:object_id>/history/` | core_mensajeinterno_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/mensajeinterno/add/` | core_mensajeinterno_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/metaventa/` | core_metaventa_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/metaventa/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/metaventa/<path:object_id>/change/` | core_metaventa_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/metaventa/<path:object_id>/delete/` | core_metaventa_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/metaventa/<path:object_id>/history/` | core_metaventa_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/metaventa/add/` | core_metaventa_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/movimientocaja/` | core_movimientocaja_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/movimientocaja/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/movimientocaja/<path:object_id>/change/` | core_movimientocaja_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/movimientocaja/<path:object_id>/delete/` | core_movimientocaja_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/movimientocaja/<path:object_id>/history/` | core_movimientocaja_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/movimientocaja/add/` | core_movimientocaja_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/notaclinicasoap/` | core_notaclinicasoap_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/notaclinicasoap/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/notaclinicasoap/<path:object_id>/change/` | core_notaclinicasoap_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/notaclinicasoap/<path:object_id>/delete/` | core_notaclinicasoap_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/notaclinicasoap/<path:object_id>/history/` | core_notaclinicasoap_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/notaclinicasoap/add/` | core_notaclinicasoap_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/notacredito/` | core_notacredito_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/notacredito/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/notacredito/<path:object_id>/change/` | core_notacredito_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/notacredito/<path:object_id>/delete/` | core_notacredito_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/notacredito/<path:object_id>/history/` | core_notacredito_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/notacredito/add/` | core_notacredito_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/notificacionsistema/` | core_notificacionsistema_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/notificacionsistema/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/notificacionsistema/<path:object_id>/change/` | core_notificacionsistema_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/notificacionsistema/<path:object_id>/delete/` | core_notificacionsistema_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/notificacionsistema/<path:object_id>/history/` | core_notificacionsistema_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/notificacionsistema/add/` | core_notificacionsistema_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/ordendeservicio/` | core_ordendeservicio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/ordendeservicio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/ordendeservicio/<path:object_id>/change/` | core_ordendeservicio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/ordendeservicio/<path:object_id>/delete/` | core_ordendeservicio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/ordendeservicio/<path:object_id>/history/` | core_ordendeservicio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/ordendeservicio/add/` | core_ordendeservicio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/paciente/` | core_paciente_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/paciente/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/paciente/<path:object_id>/change/` | core_paciente_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/paciente/<path:object_id>/delete/` | core_paciente_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/paciente/<path:object_id>/history/` | core_paciente_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/paciente/add/` | core_paciente_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/pago/` | core_pago_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/pago/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/pago/<path:object_id>/change/` | core_pago_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/pago/<path:object_id>/delete/` | core_pago_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/pago/<path:object_id>/history/` | core_pago_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/pago/add/` | core_pago_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/pagoorden/` | core_pagoorden_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/pagoorden/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/pagoorden/<path:object_id>/change/` | core_pagoorden_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/pagoorden/<path:object_id>/delete/` | core_pagoorden_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/pagoorden/<path:object_id>/history/` | core_pagoorden_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/pagoorden/add/` | core_pagoorden_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/parametro/` | core_parametro_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/parametro/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/parametro/<path:object_id>/change/` | core_parametro_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/parametro/<path:object_id>/delete/` | core_parametro_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/parametro/<path:object_id>/history/` | core_parametro_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/parametro/add/` | core_parametro_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/periodonomina/` | core_periodonomina_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/periodonomina/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/periodonomina/<path:object_id>/change/` | core_periodonomina_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/periodonomina/<path:object_id>/delete/` | core_periodonomina_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/periodonomina/<path:object_id>/history/` | core_periodonomina_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/periodonomina/add/` | core_periodonomina_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/plandesarrollo/` | core_plandesarrollo_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/plandesarrollo/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/plandesarrollo/<path:object_id>/change/` | core_plandesarrollo_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/plandesarrollo/<path:object_id>/delete/` | core_plandesarrollo_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/plandesarrollo/<path:object_id>/history/` | core_plandesarrollo_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/plandesarrollo/add/` | core_plandesarrollo_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/plantillanotaclinica/` | core_plantillanotaclinica_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/plantillanotaclinica/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/plantillanotaclinica/<path:object_id>/change/` | core_plantillanotaclinica_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/plantillanotaclinica/<path:object_id>/delete/` | core_plantillanotaclinica_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/plantillanotaclinica/<path:object_id>/history/` | core_plantillanotaclinica_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/plantillanotaclinica/add/` | core_plantillanotaclinica_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/preordenlaboratorio/` | core_preordenlaboratorio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/preordenlaboratorio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/preordenlaboratorio/<path:object_id>/change/` | core_preordenlaboratorio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/preordenlaboratorio/<path:object_id>/delete/` | core_preordenlaboratorio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/preordenlaboratorio/<path:object_id>/history/` | core_preordenlaboratorio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/preordenlaboratorio/add/` | core_preordenlaboratorio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/producto/` | core_producto_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/producto/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/producto/<path:object_id>/change/` | core_producto_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/producto/<path:object_id>/delete/` | core_producto_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/producto/<path:object_id>/history/` | core_producto_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/producto/add/` | core_producto_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/rangoreferencia/` | core_rangoreferencia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/rangoreferencia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/rangoreferencia/<path:object_id>/change/` | core_rangoreferencia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/rangoreferencia/<path:object_id>/delete/` | core_rangoreferencia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/rangoreferencia/<path:object_id>/history/` | core_rangoreferencia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/rangoreferencia/add/` | core_rangoreferencia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/receta/` | core_receta_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/receta/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/receta/<path:object_id>/change/` | core_receta_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/receta/<path:object_id>/delete/` | core_receta_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/receta/<path:object_id>/history/` | core_receta_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/receta/add/` | core_receta_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/recetaitem/` | core_recetaitem_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/recetaitem/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/recetaitem/<path:object_id>/change/` | core_recetaitem_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/recetaitem/<path:object_id>/delete/` | core_recetaitem_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/recetaitem/<path:object_id>/history/` | core_recetaitem_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/recetaitem/add/` | core_recetaitem_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/recibonomina/` | core_recibonomina_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/recibonomina/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/recibonomina/<path:object_id>/change/` | core_recibonomina_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/recibonomina/<path:object_id>/delete/` | core_recibonomina_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/recibonomina/<path:object_id>/history/` | core_recibonomina_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/recibonomina/add/` | core_recibonomina_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/registroasistencia/` | core_registroasistencia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/registroasistencia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/registroasistencia/<path:object_id>/change/` | core_registroasistencia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/registroasistencia/<path:object_id>/delete/` | core_registroasistencia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/registroasistencia/<path:object_id>/history/` | core_registroasistencia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/registroasistencia/add/` | core_registroasistencia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/reglalocalia/` | core_reglalocalia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/reglalocalia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/reglalocalia/<path:object_id>/change/` | core_reglalocalia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/reglalocalia/<path:object_id>/delete/` | core_reglalocalia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/reglalocalia/<path:object_id>/history/` | core_reglalocalia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/reglalocalia/add/` | core_reglalocalia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/resultadoparametro/` | core_resultadoparametro_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/resultadoparametro/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/resultadoparametro/<path:object_id>/change/` | core_resultadoparametro_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/resultadoparametro/<path:object_id>/delete/` | core_resultadoparametro_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/resultadoparametro/<path:object_id>/history/` | core_resultadoparametro_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/resultadoparametro/add/` | core_resultadoparametro_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/salesreturn/` | core_salesreturn_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/salesreturn/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/salesreturn/<path:object_id>/change/` | core_salesreturn_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/salesreturn/<path:object_id>/delete/` | core_salesreturn_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/salesreturn/<path:object_id>/history/` | core_salesreturn_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/salesreturn/add/` | core_salesreturn_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/seccionlaboratorio/` | core_seccionlaboratorio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/seccionlaboratorio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/seccionlaboratorio/<path:object_id>/change/` | core_seccionlaboratorio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/seccionlaboratorio/<path:object_id>/delete/` | core_seccionlaboratorio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/seccionlaboratorio/<path:object_id>/history/` | core_seccionlaboratorio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/seccionlaboratorio/add/` | core_seccionlaboratorio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/signosvitales/` | core_signosvitales_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/signosvitales/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/signosvitales/<path:object_id>/change/` | core_signosvitales_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/signosvitales/<path:object_id>/delete/` | core_signosvitales_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/signosvitales/<path:object_id>/history/` | core_signosvitales_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/signosvitales/add/` | core_signosvitales_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/solicitudautorizacion/` | core_solicitudautorizacion_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/solicitudautorizacion/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/solicitudautorizacion/<path:object_id>/change/` | core_solicitudautorizacion_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/solicitudautorizacion/<path:object_id>/delete/` | core_solicitudautorizacion_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/solicitudautorizacion/<path:object_id>/history/` | core_solicitudautorizacion_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/solicitudautorizacion/add/` | core_solicitudautorizacion_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/sucursal/` | core_sucursal_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/sucursal/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/sucursal/<path:object_id>/change/` | core_sucursal_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/sucursal/<path:object_id>/delete/` | core_sucursal_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/sucursal/<path:object_id>/history/` | core_sucursal_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/sucursal/add/` | core_sucursal_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/tomamuestra/` | core_tomamuestra_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/tomamuestra/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/tomamuestra/<path:object_id>/change/` | core_tomamuestra_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/tomamuestra/<path:object_id>/delete/` | core_tomamuestra_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/tomamuestra/<path:object_id>/history/` | core_tomamuestra_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/tomamuestra/add/` | core_tomamuestra_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/usorecursosia/` | core_usorecursosia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/usorecursosia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/usorecursosia/<path:object_id>/change/` | core_usorecursosia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/usorecursosia/<path:object_id>/delete/` | core_usorecursosia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/usorecursosia/<path:object_id>/history/` | core_usorecursosia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/usorecursosia/add/` | core_usorecursosia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/usuario/` | core_usuario_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/usuario/<id>/password/` | auth_user_password_change | `django.contrib.auth.admin.user_change_password` | ui |
| `/admin/core/usuario/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/usuario/<path:object_id>/change/` | core_usuario_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/usuario/<path:object_id>/delete/` | core_usuario_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/usuario/<path:object_id>/history/` | core_usuario_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/usuario/add/` | core_usuario_add | `django.contrib.auth.admin.add_view` | ui |
| `/admin/core/venta/` | core_venta_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/venta/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/venta/<path:object_id>/change/` | core_venta_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/venta/<path:object_id>/delete/` | core_venta_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/venta/<path:object_id>/history/` | core_venta_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/venta/add/` | core_venta_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/core/voiceauditlog/` | core_voiceauditlog_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/core/voiceauditlog/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/core/voiceauditlog/<path:object_id>/change/` | core_voiceauditlog_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/core/voiceauditlog/<path:object_id>/delete/` | core_voiceauditlog_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/core/voiceauditlog/<path:object_id>/history/` | core_voiceauditlog_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/core/voiceauditlog/add/` | core_voiceauditlog_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/farmacia/aperturacaja/` | farmacia_aperturacaja_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/farmacia/aperturacaja/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/farmacia/aperturacaja/<path:object_id>/change/` | farmacia_aperturacaja_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/farmacia/aperturacaja/<path:object_id>/delete/` | farmacia_aperturacaja_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/farmacia/aperturacaja/<path:object_id>/history/` | farmacia_aperturacaja_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/farmacia/aperturacaja/add/` | farmacia_aperturacaja_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/farmacia/cierreturnofarmacia/` | farmacia_cierreturnofarmacia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/farmacia/cierreturnofarmacia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/farmacia/cierreturnofarmacia/<path:object_id>/change/` | farmacia_cierreturnofarmacia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/farmacia/cierreturnofarmacia/<path:object_id>/delete/` | farmacia_cierreturnofarmacia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/farmacia/cierreturnofarmacia/<path:object_id>/history/` | farmacia_cierreturnofarmacia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/farmacia/cierreturnofarmacia/add/` | farmacia_cierreturnofarmacia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/farmacia/devolucionventa/` | farmacia_devolucionventa_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/farmacia/devolucionventa/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/farmacia/devolucionventa/<path:object_id>/change/` | farmacia_devolucionventa_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/farmacia/devolucionventa/<path:object_id>/delete/` | farmacia_devolucionventa_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/farmacia/devolucionventa/<path:object_id>/history/` | farmacia_devolucionventa_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/farmacia/devolucionventa/add/` | farmacia_devolucionventa_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/farmacia/mermafarmacia/` | farmacia_mermafarmacia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/farmacia/mermafarmacia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/farmacia/mermafarmacia/<path:object_id>/change/` | farmacia_mermafarmacia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/farmacia/mermafarmacia/<path:object_id>/delete/` | farmacia_mermafarmacia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/farmacia/mermafarmacia/<path:object_id>/history/` | farmacia_mermafarmacia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/farmacia/mermafarmacia/add/` | farmacia_mermafarmacia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/farmacia/motivoajuste/` | farmacia_motivoajuste_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/farmacia/motivoajuste/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/farmacia/motivoajuste/<path:object_id>/change/` | farmacia_motivoajuste_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/farmacia/motivoajuste/<path:object_id>/delete/` | farmacia_motivoajuste_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/farmacia/motivoajuste/<path:object_id>/history/` | farmacia_motivoajuste_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/farmacia/motivoajuste/add/` | farmacia_motivoajuste_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/farmacia/movimientoinventario/` | farmacia_movimientoinventario_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/farmacia/movimientoinventario/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/farmacia/movimientoinventario/<path:object_id>/change/` | farmacia_movimientoinventario_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/farmacia/movimientoinventario/<path:object_id>/delete/` | farmacia_movimientoinventario_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/farmacia/movimientoinventario/<path:object_id>/history/` | farmacia_movimientoinventario_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/farmacia/movimientoinventario/add/` | farmacia_movimientoinventario_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/farmacia/proveedor/` | farmacia_proveedor_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/farmacia/proveedor/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/farmacia/proveedor/<path:object_id>/change/` | farmacia_proveedor_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/farmacia/proveedor/<path:object_id>/delete/` | farmacia_proveedor_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/farmacia/proveedor/<path:object_id>/history/` | farmacia_proveedor_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/farmacia/proveedor/add/` | farmacia_proveedor_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/farmacia/registroantibiotico/` | farmacia_registroantibiotico_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/farmacia/registroantibiotico/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/farmacia/registroantibiotico/<path:object_id>/change/` | farmacia_registroantibiotico_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/farmacia/registroantibiotico/<path:object_id>/delete/` | farmacia_registroantibiotico_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/farmacia/registroantibiotico/<path:object_id>/history/` | farmacia_registroantibiotico_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/farmacia/registroantibiotico/add/` | farmacia_registroantibiotico_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/ia/cotizacionocr/` | ia_cotizacionocr_changelist | `ia.admin.changelist_view` | ui |
| `/admin/ia/cotizacionocr/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/ia/cotizacionocr/<path:object_id>/change/` | ia_cotizacionocr_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/ia/cotizacionocr/<path:object_id>/delete/` | ia_cotizacionocr_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/ia/cotizacionocr/<path:object_id>/history/` | ia_cotizacionocr_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/ia/cotizacionocr/add/` | ia_cotizacionocr_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/ia/transcripcionvoz/` | ia_transcripcionvoz_changelist | `ia.admin.changelist_view` | ui |
| `/admin/ia/transcripcionvoz/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/ia/transcripcionvoz/<path:object_id>/change/` | ia_transcripcionvoz_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/ia/transcripcionvoz/<path:object_id>/delete/` | ia_transcripcionvoz_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/ia/transcripcionvoz/<path:object_id>/history/` | ia_transcripcionvoz_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/ia/transcripcionvoz/add/` | ia_transcripcionvoz_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/catalogoinsumoconsultorio/` | inventario_catalogoinsumoconsultorio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/catalogoinsumoconsultorio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/catalogoinsumoconsultorio/<path:object_id>/change/` | inventario_catalogoinsumoconsultorio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/catalogoinsumoconsultorio/<path:object_id>/delete/` | inventario_catalogoinsumoconsultorio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/catalogoinsumoconsultorio/<path:object_id>/history/` | inventario_catalogoinsumoconsultorio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/catalogoinsumoconsultorio/add/` | inventario_catalogoinsumoconsultorio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/catalogoinsumogeneral/` | inventario_catalogoinsumogeneral_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/catalogoinsumogeneral/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/catalogoinsumogeneral/<path:object_id>/change/` | inventario_catalogoinsumogeneral_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/catalogoinsumogeneral/<path:object_id>/delete/` | inventario_catalogoinsumogeneral_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/catalogoinsumogeneral/<path:object_id>/history/` | inventario_catalogoinsumogeneral_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/catalogoinsumogeneral/add/` | inventario_catalogoinsumogeneral_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/catalogoreactivolab/` | inventario_catalogoreactivolab_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/catalogoreactivolab/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/catalogoreactivolab/<path:object_id>/change/` | inventario_catalogoreactivolab_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/catalogoreactivolab/<path:object_id>/delete/` | inventario_catalogoreactivolab_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/catalogoreactivolab/<path:object_id>/history/` | inventario_catalogoreactivolab_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/catalogoreactivolab/add/` | inventario_catalogoreactivolab_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/loteinsumoconsultorio/` | inventario_loteinsumoconsultorio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/loteinsumoconsultorio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/loteinsumoconsultorio/<path:object_id>/change/` | inventario_loteinsumoconsultorio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/loteinsumoconsultorio/<path:object_id>/delete/` | inventario_loteinsumoconsultorio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/loteinsumoconsultorio/<path:object_id>/history/` | inventario_loteinsumoconsultorio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/loteinsumoconsultorio/add/` | inventario_loteinsumoconsultorio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/loteinsumogeneral/` | inventario_loteinsumogeneral_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/loteinsumogeneral/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/loteinsumogeneral/<path:object_id>/change/` | inventario_loteinsumogeneral_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/loteinsumogeneral/<path:object_id>/delete/` | inventario_loteinsumogeneral_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/loteinsumogeneral/<path:object_id>/history/` | inventario_loteinsumogeneral_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/loteinsumogeneral/add/` | inventario_loteinsumogeneral_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/lotereactivolab/` | inventario_lotereactivolab_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/lotereactivolab/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/lotereactivolab/<path:object_id>/change/` | inventario_lotereactivolab_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/lotereactivolab/<path:object_id>/delete/` | inventario_lotereactivolab_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/lotereactivolab/<path:object_id>/history/` | inventario_lotereactivolab_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/lotereactivolab/add/` | inventario_lotereactivolab_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/ordendecompra/` | inventario_ordendecompra_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/ordendecompra/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/ordendecompra/<path:object_id>/change/` | inventario_ordendecompra_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/ordendecompra/<path:object_id>/delete/` | inventario_ordendecompra_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/ordendecompra/<path:object_id>/history/` | inventario_ordendecompra_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/ordendecompra/add/` | inventario_ordendecompra_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/proveedorcompras/` | inventario_proveedorcompras_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/proveedorcompras/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/proveedorcompras/<path:object_id>/change/` | inventario_proveedorcompras_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/proveedorcompras/<path:object_id>/delete/` | inventario_proveedorcompras_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/proveedorcompras/<path:object_id>/history/` | inventario_proveedorcompras_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/proveedorcompras/add/` | inventario_proveedorcompras_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/salidaanaliticalab/` | inventario_salidaanaliticalab_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/salidaanaliticalab/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/salidaanaliticalab/<path:object_id>/change/` | inventario_salidaanaliticalab_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/salidaanaliticalab/<path:object_id>/delete/` | inventario_salidaanaliticalab_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/salidaanaliticalab/<path:object_id>/history/` | inventario_salidaanaliticalab_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/salidaanaliticalab/add/` | inventario_salidaanaliticalab_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/salidaconsumoconsultorio/` | inventario_salidaconsumoconsultorio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/salidaconsumoconsultorio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/salidaconsumoconsultorio/<path:object_id>/change/` | inventario_salidaconsumoconsultorio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/salidaconsumoconsultorio/<path:object_id>/delete/` | inventario_salidaconsumoconsultorio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/salidaconsumoconsultorio/<path:object_id>/history/` | inventario_salidaconsumoconsultorio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/salidaconsumoconsultorio/add/` | inventario_salidaconsumoconsultorio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/salidatecnicalab/` | inventario_salidatecnicalab_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/salidatecnicalab/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/salidatecnicalab/<path:object_id>/change/` | inventario_salidatecnicalab_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/salidatecnicalab/<path:object_id>/delete/` | inventario_salidatecnicalab_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/salidatecnicalab/<path:object_id>/history/` | inventario_salidatecnicalab_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/salidatecnicalab/add/` | inventario_salidatecnicalab_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/inventario/valerequisicion/` | inventario_valerequisicion_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/inventario/valerequisicion/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/inventario/valerequisicion/<path:object_id>/change/` | inventario_valerequisicion_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/inventario/valerequisicion/<path:object_id>/delete/` | inventario_valerequisicion_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/inventario/valerequisicion/<path:object_id>/history/` | inventario_valerequisicion_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/inventario/valerequisicion/add/` | inventario_valerequisicion_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/iot/kiosco/` | iot_kiosco_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/iot/kiosco/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/iot/kiosco/<path:object_id>/change/` | iot_kiosco_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/iot/kiosco/<path:object_id>/delete/` | iot_kiosco_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/iot/kiosco/<path:object_id>/history/` | iot_kiosco_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/iot/kiosco/add/` | iot_kiosco_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/iot/verificacionkiosco/` | iot_verificacionkiosco_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/iot/verificacionkiosco/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/iot/verificacionkiosco/<path:object_id>/change/` | iot_verificacionkiosco_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/iot/verificacionkiosco/<path:object_id>/delete/` | iot_verificacionkiosco_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/iot/verificacionkiosco/<path:object_id>/history/` | iot_verificacionkiosco_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/iot/verificacionkiosco/add/` | iot_verificacionkiosco_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/jsi18n/` | jsi18n | `django.contrib.admin.sites.i18n_javascript` | ui |
| `/admin/laboratorio/bitacoramantenimiento/` | laboratorio_bitacoramantenimiento_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/bitacoramantenimiento/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/bitacoramantenimiento/<path:object_id>/change/` | laboratorio_bitacoramantenimiento_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/bitacoramantenimiento/<path:object_id>/delete/` | laboratorio_bitacoramantenimiento_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/bitacoramantenimiento/<path:object_id>/history/` | laboratorio_bitacoramantenimiento_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/bitacoramantenimiento/add/` | laboratorio_bitacoramantenimiento_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/categoriaexamen/` | laboratorio_categoriaexamen_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/categoriaexamen/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/categoriaexamen/<path:object_id>/change/` | laboratorio_categoriaexamen_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/categoriaexamen/<path:object_id>/delete/` | laboratorio_categoriaexamen_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/categoriaexamen/<path:object_id>/history/` | laboratorio_categoriaexamen_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/categoriaexamen/add/` | laboratorio_categoriaexamen_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/codigoparametroequipo/` | laboratorio_codigoparametroequipo_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/codigoparametroequipo/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/codigoparametroequipo/<path:object_id>/change/` | laboratorio_codigoparametroequipo_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/codigoparametroequipo/<path:object_id>/delete/` | laboratorio_codigoparametroequipo_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/codigoparametroequipo/<path:object_id>/history/` | laboratorio_codigoparametroequipo_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/codigoparametroequipo/add/` | laboratorio_codigoparametroequipo_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/controlcalidad/` | laboratorio_controlcalidad_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/controlcalidad/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/controlcalidad/<path:object_id>/change/` | laboratorio_controlcalidad_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/controlcalidad/<path:object_id>/delete/` | laboratorio_controlcalidad_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/controlcalidad/<path:object_id>/history/` | laboratorio_controlcalidad_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/controlcalidad/add/` | laboratorio_controlcalidad_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/equipo/` | laboratorio_equipo_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/equipo/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/equipo/<path:object_id>/change/` | laboratorio_equipo_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/equipo/<path:object_id>/delete/` | laboratorio_equipo_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/equipo/<path:object_id>/history/` | laboratorio_equipo_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/equipo/add/` | laboratorio_equipo_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/estudio/` | laboratorio_estudio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/estudio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/estudio/<path:object_id>/change/` | laboratorio_estudio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/estudio/<path:object_id>/delete/` | laboratorio_estudio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/estudio/<path:object_id>/history/` | laboratorio_estudio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/estudio/add/` | laboratorio_estudio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/historialresultados/` | laboratorio_historialresultados_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/historialresultados/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/historialresultados/<path:object_id>/change/` | laboratorio_historialresultados_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/historialresultados/<path:object_id>/delete/` | laboratorio_historialresultados_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/historialresultados/<path:object_id>/history/` | laboratorio_historialresultados_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/historialresultados/add/` | laboratorio_historialresultados_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/medico/` | laboratorio_medico_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/medico/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/medico/<path:object_id>/change/` | laboratorio_medico_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/medico/<path:object_id>/delete/` | laboratorio_medico_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/medico/<path:object_id>/history/` | laboratorio_medico_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/medico/add/` | laboratorio_medico_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/notificacionpanico/` | laboratorio_notificacionpanico_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/notificacionpanico/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/notificacionpanico/<path:object_id>/change/` | laboratorio_notificacionpanico_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/notificacionpanico/<path:object_id>/delete/` | laboratorio_notificacionpanico_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/notificacionpanico/<path:object_id>/history/` | laboratorio_notificacionpanico_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/notificacionpanico/add/` | laboratorio_notificacionpanico_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/orden/` | laboratorio_orden_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/orden/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/orden/<path:object_id>/change/` | laboratorio_orden_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/orden/<path:object_id>/delete/` | laboratorio_orden_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/orden/<path:object_id>/history/` | laboratorio_orden_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/orden/add/` | laboratorio_orden_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/parametro/` | laboratorio_parametro_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/parametro/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/parametro/<path:object_id>/change/` | laboratorio_parametro_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/parametro/<path:object_id>/delete/` | laboratorio_parametro_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/parametro/<path:object_id>/history/` | laboratorio_parametro_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/parametro/add/` | laboratorio_parametro_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/perfillaboratorio/` | laboratorio_perfillaboratorio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/perfillaboratorio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/perfillaboratorio/<path:object_id>/change/` | laboratorio_perfillaboratorio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/perfillaboratorio/<path:object_id>/delete/` | laboratorio_perfillaboratorio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/perfillaboratorio/<path:object_id>/history/` | laboratorio_perfillaboratorio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/perfillaboratorio/add/` | laboratorio_perfillaboratorio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/rangoreferenciaparametro/` | laboratorio_rangoreferenciaparametro_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/rangoreferenciaparametro/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/rangoreferenciaparametro/<path:object_id>/change/` | laboratorio_rangoreferenciaparametro_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/rangoreferenciaparametro/<path:object_id>/delete/` | laboratorio_rangoreferenciaparametro_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/rangoreferenciaparametro/<path:object_id>/history/` | laboratorio_rangoreferenciaparametro_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/rangoreferenciaparametro/add/` | laboratorio_rangoreferenciaparametro_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/responsablesanitario/` | laboratorio_responsablesanitario_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/responsablesanitario/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/responsablesanitario/<path:object_id>/change/` | laboratorio_responsablesanitario_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/responsablesanitario/<path:object_id>/delete/` | laboratorio_responsablesanitario_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/responsablesanitario/<path:object_id>/history/` | laboratorio_responsablesanitario_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/responsablesanitario/add/` | laboratorio_responsablesanitario_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/resultado/` | laboratorio_resultado_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/resultado/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/resultado/<path:object_id>/change/` | laboratorio_resultado_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/resultado/<path:object_id>/delete/` | laboratorio_resultado_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/resultado/<path:object_id>/history/` | laboratorio_resultado_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/resultado/add/` | laboratorio_resultado_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/resultadohl7/` | laboratorio_resultadohl7_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/resultadohl7/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/resultadohl7/<path:object_id>/change/` | laboratorio_resultadohl7_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/resultadohl7/<path:object_id>/delete/` | laboratorio_resultadohl7_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/resultadohl7/<path:object_id>/history/` | laboratorio_resultadohl7_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/resultadohl7/add/` | laboratorio_resultadohl7_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/laboratorio/valorreferencia/` | laboratorio_valorreferencia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/laboratorio/valorreferencia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/laboratorio/valorreferencia/<path:object_id>/change/` | laboratorio_valorreferencia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/laboratorio/valorreferencia/<path:object_id>/delete/` | laboratorio_valorreferencia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/laboratorio/valorreferencia/<path:object_id>/history/` | laboratorio_valorreferencia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/laboratorio/valorreferencia/add/` | laboratorio_valorreferencia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/lims/analito/` | lims_analito_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/lims/analito/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/lims/analito/<path:object_id>/change/` | lims_analito_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/lims/analito/<path:object_id>/delete/` | lims_analito_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/lims/analito/<path:object_id>/history/` | lims_analito_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/lims/analito/add/` | lims_analito_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/lims/paquetelims/` | lims_paquetelims_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/lims/paquetelims/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/lims/paquetelims/<path:object_id>/change/` | lims_paquetelims_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/lims/paquetelims/<path:object_id>/delete/` | lims_paquetelims_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/lims/paquetelims/<path:object_id>/history/` | lims_paquetelims_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/lims/paquetelims/add/` | lims_paquetelims_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/lims/perfillims/` | lims_perfillims_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/lims/perfillims/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/lims/perfillims/<path:object_id>/change/` | lims_perfillims_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/lims/perfillims/<path:object_id>/delete/` | lims_perfillims_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/lims/perfillims/<path:object_id>/history/` | lims_perfillims_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/lims/perfillims/add/` | lims_perfillims_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/lims/precioitem/` | lims_precioitem_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/lims/precioitem/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/lims/precioitem/<path:object_id>/change/` | lims_precioitem_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/lims/precioitem/<path:object_id>/delete/` | lims_precioitem_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/lims/precioitem/<path:object_id>/history/` | lims_precioitem_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/lims/precioitem/add/` | lims_precioitem_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/login/` | login | `django.contrib.admin.sites.login` | ui |
| `/admin/logistica/detalletransferencia/` | logistica_detalletransferencia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/logistica/detalletransferencia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/logistica/detalletransferencia/<path:object_id>/change/` | logistica_detalletransferencia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/logistica/detalletransferencia/<path:object_id>/delete/` | logistica_detalletransferencia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/logistica/detalletransferencia/<path:object_id>/history/` | logistica_detalletransferencia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/logistica/detalletransferencia/add/` | logistica_detalletransferencia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/logistica/logtransferencia/` | logistica_logtransferencia_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/logistica/logtransferencia/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/logistica/logtransferencia/<path:object_id>/change/` | logistica_logtransferencia_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/logistica/logtransferencia/<path:object_id>/delete/` | logistica_logtransferencia_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/logistica/logtransferencia/<path:object_id>/history/` | logistica_logtransferencia_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/logistica/logtransferencia/add/` | logistica_logtransferencia_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/logistica/rutarecoleccion/` | logistica_rutarecoleccion_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/logistica/rutarecoleccion/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/logistica/rutarecoleccion/<path:object_id>/change/` | logistica_rutarecoleccion_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/logistica/rutarecoleccion/<path:object_id>/delete/` | logistica_rutarecoleccion_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/logistica/rutarecoleccion/<path:object_id>/history/` | logistica_rutarecoleccion_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/logistica/rutarecoleccion/add/` | logistica_rutarecoleccion_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/logistica/transferenciainventario/` | logistica_transferenciainventario_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/logistica/transferenciainventario/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/logistica/transferenciainventario/<path:object_id>/change/` | logistica_transferenciainventario_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/logistica/transferenciainventario/<path:object_id>/delete/` | logistica_transferenciainventario_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/logistica/transferenciainventario/<path:object_id>/history/` | logistica_transferenciainventario_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/logistica/transferenciainventario/add/` | logistica_transferenciainventario_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/logistica/visitadomicilio/` | logistica_visitadomicilio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/logistica/visitadomicilio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/logistica/visitadomicilio/<path:object_id>/change/` | logistica_visitadomicilio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/logistica/visitadomicilio/<path:object_id>/delete/` | logistica_visitadomicilio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/logistica/visitadomicilio/<path:object_id>/history/` | logistica_visitadomicilio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/logistica/visitadomicilio/add/` | logistica_visitadomicilio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/logout/` | logout | `django.contrib.admin.sites.logout` | ui |
| `/admin/mantenimiento/arboldiagnostico/` | mantenimiento_arboldiagnostico_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/mantenimiento/arboldiagnostico/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/mantenimiento/arboldiagnostico/<path:object_id>/change/` | mantenimiento_arboldiagnostico_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/mantenimiento/arboldiagnostico/<path:object_id>/delete/` | mantenimiento_arboldiagnostico_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/mantenimiento/arboldiagnostico/<path:object_id>/history/` | mantenimiento_arboldiagnostico_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/mantenimiento/arboldiagnostico/add/` | mantenimiento_arboldiagnostico_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/mantenimiento/bypasschecklistautorizacion/` | mantenimiento_bypasschecklistautorizacion_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/mantenimiento/bypasschecklistautorizacion/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/mantenimiento/bypasschecklistautorizacion/<path:object_id>/change/` | mantenimiento_bypasschecklistautorizacion_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/mantenimiento/bypasschecklistautorizacion/<path:object_id>/delete/` | mantenimiento_bypasschecklistautorizacion_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/mantenimiento/bypasschecklistautorizacion/<path:object_id>/history/` | mantenimiento_bypasschecklistautorizacion_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/mantenimiento/bypasschecklistautorizacion/add/` | mantenimiento_bypasschecklistautorizacion_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/mantenimiento/ejecucionprotocolo/` | mantenimiento_ejecucionprotocolo_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/mantenimiento/ejecucionprotocolo/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/mantenimiento/ejecucionprotocolo/<path:object_id>/change/` | mantenimiento_ejecucionprotocolo_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/mantenimiento/ejecucionprotocolo/<path:object_id>/delete/` | mantenimiento_ejecucionprotocolo_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/mantenimiento/ejecucionprotocolo/<path:object_id>/history/` | mantenimiento_ejecucionprotocolo_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/mantenimiento/ejecucionprotocolo/add/` | mantenimiento_ejecucionprotocolo_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/mantenimiento/expedienteequipo/` | mantenimiento_expedienteequipo_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/mantenimiento/expedienteequipo/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/mantenimiento/expedienteequipo/<path:object_id>/change/` | mantenimiento_expedienteequipo_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/mantenimiento/expedienteequipo/<path:object_id>/delete/` | mantenimiento_expedienteequipo_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/mantenimiento/expedienteequipo/<path:object_id>/history/` | mantenimiento_expedienteequipo_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/mantenimiento/expedienteequipo/add/` | mantenimiento_expedienteequipo_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/mantenimiento/procedimientoreparacion/` | mantenimiento_procedimientoreparacion_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/mantenimiento/procedimientoreparacion/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/mantenimiento/procedimientoreparacion/<path:object_id>/change/` | mantenimiento_procedimientoreparacion_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/mantenimiento/procedimientoreparacion/<path:object_id>/delete/` | mantenimiento_procedimientoreparacion_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/mantenimiento/procedimientoreparacion/<path:object_id>/history/` | mantenimiento_procedimientoreparacion_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/mantenimiento/procedimientoreparacion/add/` | mantenimiento_procedimientoreparacion_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/mantenimiento/protocoloequipo/` | mantenimiento_protocoloequipo_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/mantenimiento/protocoloequipo/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/mantenimiento/protocoloequipo/<path:object_id>/change/` | mantenimiento_protocoloequipo_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/mantenimiento/protocoloequipo/<path:object_id>/delete/` | mantenimiento_protocoloequipo_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/mantenimiento/protocoloequipo/<path:object_id>/history/` | mantenimiento_protocoloequipo_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/mantenimiento/protocoloequipo/add/` | mantenimiento_protocoloequipo_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/mantenimiento/registrotco/` | mantenimiento_registrotco_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/mantenimiento/registrotco/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/mantenimiento/registrotco/<path:object_id>/change/` | mantenimiento_registrotco_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/mantenimiento/registrotco/<path:object_id>/delete/` | mantenimiento_registrotco_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/mantenimiento/registrotco/<path:object_id>/history/` | mantenimiento_registrotco_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/mantenimiento/registrotco/add/` | mantenimiento_registrotco_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/mantenimiento/ticketmantenimientocmms/` | mantenimiento_ticketmantenimientocmms_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/mantenimiento/ticketmantenimientocmms/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/mantenimiento/ticketmantenimientocmms/<path:object_id>/change/` | mantenimiento_ticketmantenimientocmms_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/mantenimiento/ticketmantenimientocmms/<path:object_id>/delete/` | mantenimiento_ticketmantenimientocmms_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/mantenimiento/ticketmantenimientocmms/<path:object_id>/history/` | mantenimiento_ticketmantenimientocmms_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/mantenimiento/ticketmantenimientocmms/add/` | mantenimiento_ticketmantenimientocmms_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/marketing/campanamarketing/` | marketing_campanamarketing_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/marketing/campanamarketing/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/marketing/campanamarketing/<path:object_id>/change/` | marketing_campanamarketing_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/marketing/campanamarketing/<path:object_id>/delete/` | marketing_campanamarketing_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/marketing/campanamarketing/<path:object_id>/history/` | marketing_campanamarketing_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/marketing/campanamarketing/add/` | marketing_campanamarketing_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/marketing/cuponmarketing/` | marketing_cuponmarketing_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/marketing/cuponmarketing/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/marketing/cuponmarketing/<path:object_id>/change/` | marketing_cuponmarketing_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/marketing/cuponmarketing/<path:object_id>/delete/` | marketing_cuponmarketing_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/marketing/cuponmarketing/<path:object_id>/history/` | marketing_cuponmarketing_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/marketing/cuponmarketing/add/` | marketing_cuponmarketing_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/marketing/prospectocrm/` | marketing_prospectocrm_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/marketing/prospectocrm/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/marketing/prospectocrm/<path:object_id>/change/` | marketing_prospectocrm_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/marketing/prospectocrm/<path:object_id>/delete/` | marketing_prospectocrm_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/marketing/prospectocrm/<path:object_id>/history/` | marketing_prospectocrm_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/marketing/prospectocrm/add/` | marketing_prospectocrm_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/marketing/seguimientocrm/` | marketing_seguimientocrm_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/marketing/seguimientocrm/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/marketing/seguimientocrm/<path:object_id>/change/` | marketing_seguimientocrm_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/marketing/seguimientocrm/<path:object_id>/delete/` | marketing_seguimientocrm_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/marketing/seguimientocrm/<path:object_id>/history/` | marketing_seguimientocrm_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/marketing/seguimientocrm/add/` | marketing_seguimientocrm_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/pacientes/accesoexpedienteportal/` | pacientes_accesoexpedienteportal_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/pacientes/accesoexpedienteportal/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/pacientes/accesoexpedienteportal/<path:object_id>/change/` | pacientes_accesoexpedienteportal_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/pacientes/accesoexpedienteportal/<path:object_id>/delete/` | pacientes_accesoexpedienteportal_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/pacientes/accesoexpedienteportal/<path:object_id>/history/` | pacientes_accesoexpedienteportal_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/pacientes/accesoexpedienteportal/add/` | pacientes_accesoexpedienteportal_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/pacientes/paciente/` | pacientes_paciente_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/pacientes/paciente/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/pacientes/paciente/<path:object_id>/change/` | pacientes_paciente_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/pacientes/paciente/<path:object_id>/delete/` | pacientes_paciente_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/pacientes/paciente/<path:object_id>/history/` | pacientes_paciente_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/pacientes/paciente/add/` | pacientes_paciente_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/pacientes/solicitudaccesoportal/` | pacientes_solicitudaccesoportal_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/pacientes/solicitudaccesoportal/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/pacientes/solicitudaccesoportal/<path:object_id>/change/` | pacientes_solicitudaccesoportal_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/pacientes/solicitudaccesoportal/<path:object_id>/delete/` | pacientes_solicitudaccesoportal_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/pacientes/solicitudaccesoportal/<path:object_id>/history/` | pacientes_solicitudaccesoportal_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/pacientes/solicitudaccesoportal/add/` | pacientes_solicitudaccesoportal_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/pacientes/usuariopaciente/` | pacientes_usuariopaciente_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/pacientes/usuariopaciente/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/pacientes/usuariopaciente/<path:object_id>/change/` | pacientes_usuariopaciente_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/pacientes/usuariopaciente/<path:object_id>/delete/` | pacientes_usuariopaciente_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/pacientes/usuariopaciente/<path:object_id>/history/` | pacientes_usuariopaciente_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/pacientes/usuariopaciente/add/` | pacientes_usuariopaciente_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/password_change/` | password_change | `django.contrib.admin.sites.password_change` | ui |
| `/admin/password_change/done/` | password_change_done | `django.contrib.admin.sites.password_change_done` | ui |
| `/admin/r/<int:content_type_id>/<path:object_id>/` | view_on_site | `django.contrib.contenttypes.views.shortcut` | ui |
| `/admin/reglas_negocio/ejecucionregla/` | reglas_negocio_ejecucionregla_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/reglas_negocio/ejecucionregla/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/reglas_negocio/ejecucionregla/<path:object_id>/change/` | reglas_negocio_ejecucionregla_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/reglas_negocio/ejecucionregla/<path:object_id>/delete/` | reglas_negocio_ejecucionregla_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/reglas_negocio/ejecucionregla/<path:object_id>/history/` | reglas_negocio_ejecucionregla_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/reglas_negocio/ejecucionregla/add/` | reglas_negocio_ejecucionregla_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/reglas_negocio/reglanegocio/` | reglas_negocio_reglanegocio_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/reglas_negocio/reglanegocio/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/reglas_negocio/reglanegocio/<path:object_id>/change/` | reglas_negocio_reglanegocio_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/reglas_negocio/reglanegocio/<path:object_id>/delete/` | reglas_negocio_reglanegocio_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/reglas_negocio/reglanegocio/<path:object_id>/history/` | reglas_negocio_reglanegocio_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/reglas_negocio/reglanegocio/add/` | reglas_negocio_reglanegocio_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/seguridad/alertapanico/` | seguridad_alertapanico_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/seguridad/alertapanico/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/seguridad/alertapanico/<path:object_id>/change/` | seguridad_alertapanico_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/seguridad/alertapanico/<path:object_id>/delete/` | seguridad_alertapanico_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/seguridad/alertapanico/<path:object_id>/history/` | seguridad_alertapanico_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/seguridad/alertapanico/add/` | seguridad_alertapanico_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/seguridad/codigobackup2fa/` | seguridad_codigobackup2fa_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/seguridad/codigobackup2fa/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/seguridad/codigobackup2fa/<path:object_id>/change/` | seguridad_codigobackup2fa_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/seguridad/codigobackup2fa/<path:object_id>/delete/` | seguridad_codigobackup2fa_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/seguridad/codigobackup2fa/<path:object_id>/history/` | seguridad_codigobackup2fa_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/seguridad/codigobackup2fa/add/` | seguridad_codigobackup2fa_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/seguridad/configuracionseguridad/` | seguridad_configuracionseguridad_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/seguridad/configuracionseguridad/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/seguridad/configuracionseguridad/<path:object_id>/change/` | seguridad_configuracionseguridad_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/seguridad/configuracionseguridad/<path:object_id>/delete/` | seguridad_configuracionseguridad_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/seguridad/configuracionseguridad/<path:object_id>/history/` | seguridad_configuracionseguridad_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/seguridad/configuracionseguridad/add/` | seguridad_configuracionseguridad_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/seguridad/dispositivosms/` | seguridad_dispositivosms_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/seguridad/dispositivosms/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/seguridad/dispositivosms/<path:object_id>/change/` | seguridad_dispositivosms_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/seguridad/dispositivosms/<path:object_id>/delete/` | seguridad_dispositivosms_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/seguridad/dispositivosms/<path:object_id>/history/` | seguridad_dispositivosms_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/seguridad/dispositivosms/add/` | seguridad_dispositivosms_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/seguridad/dispositivototp/` | seguridad_dispositivototp_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/seguridad/dispositivototp/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/seguridad/dispositivototp/<path:object_id>/change/` | seguridad_dispositivototp_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/seguridad/dispositivototp/<path:object_id>/delete/` | seguridad_dispositivototp_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/seguridad/dispositivototp/<path:object_id>/history/` | seguridad_dispositivototp_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/seguridad/dispositivototp/add/` | seguridad_dispositivototp_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/seguridad/logaccionsensible/` | seguridad_logaccionsensible_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/seguridad/logaccionsensible/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/seguridad/logaccionsensible/<path:object_id>/change/` | seguridad_logaccionsensible_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/seguridad/logaccionsensible/<path:object_id>/delete/` | seguridad_logaccionsensible_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/seguridad/logaccionsensible/<path:object_id>/history/` | seguridad_logaccionsensible_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/seguridad/logaccionsensible/add/` | seguridad_logaccionsensible_add | `django.contrib.admin.options.add_view` | ui |
| `/admin/seguridad/sesionactiva/` | seguridad_sesionactiva_changelist | `django.contrib.admin.options.changelist_view` | ui |
| `/admin/seguridad/sesionactiva/<path:object_id>/` | — | `django.views.generic.base.view` | ui |
| `/admin/seguridad/sesionactiva/<path:object_id>/change/` | seguridad_sesionactiva_change | `django.contrib.admin.options.change_view` | ui |
| `/admin/seguridad/sesionactiva/<path:object_id>/delete/` | seguridad_sesionactiva_delete | `django.contrib.admin.options.delete_view` | ui |
| `/admin/seguridad/sesionactiva/<path:object_id>/history/` | seguridad_sesionactiva_history | `django.contrib.admin.options.history_view` | ui |
| `/admin/seguridad/sesionactiva/add/` | seguridad_sesionactiva_add | `django.contrib.admin.options.add_view` | ui |

## Prefijo `/analytics/` (3 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/analytics/` | dashboard_analytics | `core.views.analytics.dashboard_analytics` | ui |
| `/analytics/api/metricas-tiempo-real/` | api_metricas_tiempo_real | `core.views.analytics.api_metricas_tiempo_real` | api |
| `/analytics/trazabilidad/` | reporte_trazabilidad | `core.views.analytics.reporte_trazabilidad` | ui |

## Prefijo `/api/` (53 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/api/audio/sellar/` | api_sellar_audio | `core.views.audio_legal.api_sellar_audio` | api |
| `/api/audio/verificar-integridad/<int:registro_id>/` | api_verificar_integridad_audio | `core.views.audio_legal.api_verificar_integridad_audio` | api |
| `/api/auditoria/campo/` | api_auditoria_campo | `core.views.auditoria_campo.api_auditoria_campo` | api |
| `/api/autorizaciones/<int:solicitud_id>/aprobar/` | api_aprobar_solicitud | `core.views.autorizaciones.api_aprobar_solicitud` | api |
| `/api/autorizaciones/<int:solicitud_id>/rechazar/` | api_rechazar_solicitud | `core.views.autorizaciones.api_rechazar_solicitud` | api |
| `/api/autorizaciones/<int:solicitud_id>/verificar/` | verificar_estado_solicitud | `core.views.autorizaciones.verificar_estado_solicitud` | api |
| `/api/autorizaciones/crear/` | crear_solicitud_autorizacion | `core.views.autorizaciones.crear_solicitud_autorizacion` | api |
| `/api/caja/corte-unificado/` | corte_caja_unificado | `farmacia.views.corte_caja_api.api_corte_caja_unificado` | api |
| `/api/cerebro/preguntar/` | api_cerebro_preguntar | `core.views.cerebro.api_cerebro_preguntar` | api |
| `/api/consentimiento/guardar/<int:orden_id>/` | api_guardar_consentimiento | `core.views.consentimientos.api_guardar_consentimiento` | api |
| `/api/consentimiento/verificar/<int:orden_id>/` | api_verificar_consentimiento | `core.views.consentimientos.api_verificar_consentimiento` | api |
| `/api/flags/estado/` | api_flags_estado | `core.views.feature_flags_admin.api_flags_estado` | api |
| `/api/ia/byok/` | api_guardar_byok | `core.views.configuracion.api_guardar_byok` | api |
| `/api/ia/chat/` | api_ia_chat | `core.views.ia_dashboard.api_ia_chat` | api |
| `/api/ia/consultar-negocios/` | api_ia_consultar_negocios | `core.views.ia_dashboard.api_ia_consultar_negocios` | api |
| `/api/ia/consumo/` | api_ia_consumo | `core.views.configuracion.api_ia_consumo` | api |
| `/api/ia/diagnostico/` | api_ia_diagnostico | `core.views.ia_dashboard.api_ia_diagnostico` | api |
| `/api/ia/modo/` | api_cambiar_modo_ia | `core.views.configuracion.api_cambiar_modo_ia` | api |
| `/api/incidencias/<int:incidencia_id>/marcar-revisada/` | marcar_incidencia_revisada | `core.views.incidencias.marcar_incidencia_revisada` | api |
| `/api/incidencias/registrar/` | registrar_incidencia | `core.views.incidencias.registrar_incidencia` | api |
| `/api/iot/hl7/` | hl7_receptor | `laboratorio.views.hl7_receptor.receptor_hl7` | api |
| `/api/lab/imprimir-zpl/<int:orden_id>/` | imprimir_zpl | `laboratorio.views.imprimir_zpl.imprimir_etiqueta_zpl` | api |
| `/api/lab/imprimir-zpl/lote/` | imprimir_zpl_lote | `laboratorio.views.imprimir_zpl.imprimir_etiquetas_lote_zpl` | api |
| `/api/log-frontend-error/` | log_frontend_error | `core.views.general.log_frontend_error` | api |
| `/api/logistica/transferencia/<int:transferencia_id>/temperatura/` | api_cadena_frio_temperatura | `logistica.views.api_cadena_frio_temperatura` | api |
| `/api/notificaciones/crear/` | api_crear_notificacion | `core.views.notificaciones.api_crear_notificacion` | api |
| `/api/omnisearch/` | api_omnisearch | `core.views.omnisearch.api_omnisearch` | api |
| `/api/pacientes/buscar/` | api_buscar_pacientes | `core.views.pacientes.api_buscar_pacientes` | api |
| `/api/pacientes/guardar/` | api_guardar_paciente | `core.views.pacientes.api_guardar_paciente` | api |
| `/api/pris-ayuda/` | api_pris_ayuda | `core.views.reporte_friccion.api_pris_ayuda` | api |
| `/api/pris/accion/<int:accion_id>/confirmar/` | pris_jarvis_confirmar | `core.views.pris_jarvis.api_confirmar_accion` | api |
| `/api/pris/accion/<int:accion_id>/rechazar/` | pris_jarvis_rechazar | `core.views.pris_jarvis.api_rechazar_accion` | api |
| `/api/pris/alerta-clinica/` | pris_alerta_clinica | `core.views.pris_jarvis.api_crear_alerta_clinica` | api |
| `/api/pris/archivo-raw/` | pris_crear_archivo_raw | `core.views.pris_jarvis.api_crear_archivo_raw` | api |
| `/api/pris/coach-toma-muestra/` | pris_coach_toma_muestra | `core.views.pris_jarvis.api_coach_toma_muestra` | api |
| `/api/pris/consulta-voz/` | pris_consulta_voz | `core.views.pris_jarvis.api_consulta_voz` | api |
| `/api/pris/dictado/buscar/` | pris_dictado_busqueda | `core.views.pris_jarvis.api_dictado_busqueda` | api |
| `/api/pris/dictado/inventario/` | pris_dictado_inventario | `core.views.pris_jarvis.api_dictado_inventario` | api |
| `/api/pris/dictado/resultado/` | pris_dictado_resultado | `core.views.pris_jarvis.api_dictado_resultado` | api |
| `/api/pris/dictado/validar-orden/` | pris_dictado_validar_orden | `core.views.pris_jarvis.api_dictado_validar_orden` | api |
| `/api/pris/hoja-trabajo/` | pris_hoja_trabajo | `core.views.pris_jarvis.api_generar_hoja_trabajo` | api |
| `/api/pris/ocr/` | pris_ocr_documento | `core.views.pris_jarvis.api_ocr_documento` | api |
| `/api/push/desuscribir/` | push_desuscribir | `core.views.push.desuscribir_push` | api |
| `/api/push/estado/` | push_estado | `core.views.push.estado_suscripciones` | api |
| `/api/push/suscribir/` | push_suscribir | `core.views.push.suscribir_push` | api |
| `/api/push/test/` | push_test | `core.views.push.test_notificacion` | api |
| `/api/push/vapid/` | push_vapid_key | `core.views.push.obtener_vapid_key` | api |
| `/api/sentinel/diagnostico/` | sentinel_diagnostico | `core.views.sentinel_api.api_sentinel_diagnostico` | api |
| `/api/sentinel/reset/` | sentinel_reset | `core.views.sentinel_api.api_sentinel_reset` | api |
| `/api/sentinel/shield-telemetry/` | sentinel_shield_telemetry | `core.views.sentinel_api.api_shield_telemetry` | api |
| `/api/voice/history/` | voice_history | `core.views.voice.historial_comandos` | api |
| `/api/voice/process/` | voice_process | `core.views.voice.procesar_comando_api` | api |
| `/api/voice/verify-auth/` | voice_verify_auth | `core.views.voice.verificar_webauthn` | api |

## Prefijo `/asistencia/` (8 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/asistencia/` | dashboard_asistencia | `core.views.asistencia.dashboard_asistencia` | ui |
| `/asistencia/crear-horario/` | crear_horario | `core.views.asistencia.crear_horario` | ui |
| `/asistencia/crear-incidencia/` | crear_incidencia | `core.views.asistencia.crear_incidencia` | ui |
| `/asistencia/horarios/` | horarios_trabajo | `core.views.asistencia.horarios_trabajo` | ui |
| `/asistencia/incidencia/<int:incidencia_id>/autorizar/` | autorizar_incidencia | `core.views.asistencia.autorizar_incidencia` | ui |
| `/asistencia/incidencias/` | incidencias_asistencia | `core.views.asistencia.incidencias_asistencia` | ui |
| `/asistencia/registrar/` | registrar_entrada_salida | `core.views.asistencia.registrar_entrada_salida` | ui |
| `/asistencia/registros/` | registro_asistencia | `core.views.asistencia.registro_asistencia` | ui |

## Prefijo `/auth/` (3 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/auth/2fa/configurar/` | setup_2fa | `core.views.autenticacion_2fa.setup_2fa` | ui |
| `/auth/2fa/desactivar/` | desactivar_2fa | `core.views.autenticacion_2fa.desactivar_2fa` | ui |
| `/auth/2fa/verificar/` | verificar_2fa | `core.views.autenticacion_2fa.verificar_2fa` | ui |

## Prefijo `/bienestar/` (21 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/bienestar/` | bienestar_dashboard | `core.views.bienestar.dashboard_bienestar` | ui |
| `/bienestar/` | dashboard_bienestar | `bienestar.views.dashboard_bienestar` | ui |
| `/bienestar/alertas-rrhh/` | bienestar_alertas_rrhh | `core.views.bienestar.alertas_rrhh` | ui |
| `/bienestar/api/chat/` | api_chat_bienestar | `bienestar.views.api_chat_bienestar` | api |
| `/bienestar/capacitaciones/` | capacitaciones_bienestar | `core.views.bienestar.capacitaciones` | ui |
| `/bienestar/chat/` | chat_bienestar | `bienestar.views.chat_bienestar` | ui |
| `/bienestar/consultorio/agendar/` | agendar_consultorio | `bienestar.views.agendar_consultorio_bienestar` | ui |
| `/bienestar/diario/` | diario_emocional | `core.views.bienestar.diario_emocional` | ui |
| `/bienestar/diario/` | diario_emocional | `bienestar.views.diario_emocional` | ui |
| `/bienestar/diario/estadisticas/` | estadisticas_diario | `bienestar.views.estadisticas_diario` | ui |
| `/bienestar/diario/lista/` | diario_lista | `bienestar.views.diario_emocional` | ui |
| `/bienestar/diario/nueva/` | nueva_entrada_diario | `bienestar.views.nueva_entrada_diario` | ui |
| `/bienestar/diario/nueva/entrada/` | nueva_entrada | `bienestar.views.nueva_entrada_diario` | ui |
| `/bienestar/nom035/` | evaluacion_nom035 | `core.views.bienestar.evaluacion_nom035` | ui |
| `/bienestar/pris/alertas/` | alertas_bienestar_director | `core.views.bienestar_mejorado.alertas_bienestar_director` | ui |
| `/bienestar/pris/alertas/<int:alerta_id>/vista/` | marcar_alerta_vista | `core.views.bienestar_mejorado.marcar_alerta_vista` | ui |
| `/bienestar/pris/chat/` | chat_bienestar | `core.views.bienestar_mejorado.chat_bienestar` | ui |
| `/bienestar/pris/chat/enviar/` | enviar_mensaje_bienestar | `core.views.bienestar_mejorado.enviar_mensaje_bienestar` | ui |
| `/bienestar/recursos/` | recursos_bienestar | `bienestar.views.recursos_bienestar` | ui |
| `/bienestar/recursos/<int:recurso_id>/` | detalle_recurso | `bienestar.views.detalle_recurso` | ui |
| `/bienestar/recursos/lista/` | recursos_lista | `bienestar.views.recursos_bienestar` | ui |

## Prefijo `/buscar-paciente/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/buscar-paciente/` | buscar_paciente | `core.views.pacientes.buscar_paciente` | ui |

## Prefijo `/capacitacion/` (10 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/capacitacion/ejecutiva/` | capacitacion_ejecutiva | `core.views.capacitacion.capacitacion_ejecutiva` | ui |
| `/capacitacion/personal/` | capacitacion_personal | `core.views.capacitacion.capacitacion_personal` | ui |
| `/capacitacion/rag/` | dashboard_capacitacion | `core.views.capacitacion_rag.dashboard_capacitacion` | ui |
| `/capacitacion/rag/consultar/` | consultar_pris_rag | `core.views.capacitacion_rag.consultar_pris_rag` | ui |
| `/capacitacion/rag/eliminar/<int:documento_id>/` | eliminar_documento_rag | `core.views.capacitacion_rag.eliminar_documento` | ui |
| `/capacitacion/rag/estado/<int:documento_id>/` | estado_documento_rag | `core.views.capacitacion_rag.estado_documento_rag` | ui |
| `/capacitacion/rag/reprocesar/<int:documento_id>/` | reprocesar_documento_rag | `core.views.capacitacion_rag.reprocesar_documento` | ui |
| `/capacitacion/rag/subir/` | subir_documento_capacitacion | `core.views.capacitacion_rag.subir_documento_capacitacion` | ui |
| `/capacitacion/rag/tip/` | obtener_tip_dia | `core.views.capacitacion_rag.obtener_tip_dia` | ui |
| `/capacitacion/rag/worklist/` | consultar_pris_worklist | `core.views.capacitacion_rag.consultar_pris_worklist` | ui |

## Prefijo `/catalogos/` (4 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/catalogos/convenios/` | catalogo_convenios | `core.views.catalogos.catalogo_convenios` | ui |
| `/catalogos/convenios/<int:convenio_id>/precios/` | convenio_precios | `core.views.catalogos.convenio_precios` | ui |
| `/catalogos/estudios/` | lista_estudios | `core.views.catalogos.lista_estudios` | ui |
| `/catalogos/medicos/` | catalogo_medicos | `core.views.catalogos.catalogo_medicos` | ui |

## Prefijo `/cerebro/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/cerebro/chat/` | chat_experto | `core.views.cerebro.chat_experto` | ui |

## Prefijo `/chat/` (6 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/chat/` | pris_chat | `core.views.comunicacion.chat_page` | ui |
| `/chat/api/conversaciones/` | api_listar_conversaciones | `core.views.comunicacion.api_listar_conversaciones` | api |
| `/chat/api/enviar-audio/` | api_enviar_audio | `core.views.comunicacion.api_enviar_audio` | api |
| `/chat/api/enviar/` | api_enviar_mensaje | `core.views.comunicacion.api_enviar_mensaje` | api |
| `/chat/api/mensajes/` | api_obtener_mensajes | `core.views.comunicacion.api_obtener_mensajes` | api |
| `/chat/api/usuarios/` | api_listar_usuarios | `core.views.comunicacion.api_listar_usuarios` | api |

## Prefijo `/configuracion/` (4 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/configuracion/` | configuracion_dashboard | `core.views.configuracion.configuracion_dashboard` | ui |
| `/configuracion/flags/` | panel_feature_flags | `core.views.feature_flags_admin.panel_feature_flags` | ui |
| `/configuracion/flags/<str:codigo>/toggle/` | api_toggle_flag | `core.views.feature_flags_admin.api_toggle_flag` | ui |
| `/configuracion/usuarios/` | gestionar_usuarios | `core.views.administracion_usuarios.gestionar_usuarios` | ui |

## Prefijo `/consentimiento/` (3 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/consentimiento/<int:orden_id>/` | consentimiento_digital | `core.views.consentimiento_digital.pagina_consentimiento` | ui |
| `/consentimiento/<int:orden_id>/guardar/` | api_guardar_consentimiento | `core.views.consentimiento_digital.api_guardar_consentimiento` | ui |
| `/consentimiento/pdf/<str:folio>/` | descargar_pdf_consentimiento | `core.views.consentimiento_digital.descargar_pdf_consentimiento` | pdf |

## Prefijo `/consultorio/` (67 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/consultorio/` | dashboard_consultorio | `consultorio.views.dashboard_consultorio` | ui |
| `/consultorio/agenda/` | agenda_medico | `consultorio.views.agenda_medico` | ui |
| `/consultorio/analisis-patrones/` | analisis_patrones | `consultorio.views.analisis_patrones` | ui |
| `/consultorio/api/analizar-transcripcion/` | api_analizar_transcripcion | `consultorio.views.api_analizar_transcripcion` | api |
| `/consultorio/api/buscar-pacientes/` | api_buscar_pacientes | `consultorio.views.api_buscar_pacientes` | api |
| `/consultorio/api/buscar-vademecum/` | api_buscar_vademecum | `consultorio.views.api_buscar_vademecum` | api |
| `/consultorio/api/crear-consulta-directa/` | api_crear_consulta_directa | `consultorio.views.api_crear_consulta_directa` | api |
| `/consultorio/api/crear-paciente-y-consulta/` | api_crear_paciente_y_consulta | `consultorio.views.api_crear_paciente_y_consulta` | api |
| `/consultorio/api/eliminar-archivo/<int:archivo_id>/` | api_eliminar_archivo | `consultorio.views.api_eliminar_archivo` | api |
| `/consultorio/api/generar-analisis-patron/` | api_generar_analisis_patron | `consultorio.views.api_generar_analisis_patron` | api |
| `/consultorio/api/generar-certificado-inmediato/` | api_generar_certificado_inmediato | `consultorio.views.api_generar_certificado_inmediato` | api |
| `/consultorio/api/generar-orden-laboratorio-inmediata/` | api_generar_orden_laboratorio_inmediata | `consultorio.views.api_generar_orden_laboratorio_inmediata` | api |
| `/consultorio/api/generar-receta-inmediata/` | api_generar_receta_inmediata | `consultorio.views.api_generar_receta_inmediata` | api |
| `/consultorio/api/liquidar-vale/` | api_liquidar_vale | `consultorio.views.api_liquidar_vale` | api |
| `/consultorio/api/lista-espera/agregar/` | api_agregar_lista_espera | `consultorio.views.api_agregar_lista_espera` | api |
| `/consultorio/api/plantillas/` | api_plantillas_especialidad | `consultorio.views.api_plantillas_especialidad` | api |
| `/consultorio/api/plantillas/<int:plantilla_id>/usar/` | api_usar_plantilla | `consultorio.views.api_usar_plantilla` | api |
| `/consultorio/api/procesar-audio-consulta/` | api_procesar_audio_consulta | `consultorio.api_views.procesar_audio_consulta` | api |
| `/consultorio/api/receta-pdf/<int:consulta_id>/` | api_receta_pdf | `consultorio.pdf_views_prislab.api_generar_receta_pdf` | api |
| `/consultorio/api/registrar-cobro/` | api_registrar_cobro | `consultorio.views.api_registrar_cobro` | api |
| `/consultorio/api/resultados-disponibles/` | api_resultados_disponibles | `consultorio.views.api_resultados_disponibles` | api |
| `/consultorio/api/sentinel/exportar/<int:incidencia_id>/` | api_sentinel_exportar_cursor | `consultorio.views.api_sentinel_exportar_cursor` | api |
| `/consultorio/api/sentinel/feedback-lista/` | api_sentinel_listar_feedback | `consultorio.views.api_sentinel_listar_feedback` | api |
| `/consultorio/api/sentinel/feedback/` | api_sentinel_feedback | `consultorio.views.api_sentinel_feedback` | api |
| `/consultorio/api/sentinel/resolver-conocidas/` | api_resolver_incidencias_sentinel | `consultorio.views.api_resolver_incidencias_sentinel` | api |
| `/consultorio/api/sentinel/ssh/<int:incidencia_id>/` | api_sentinel_ssh | `consultorio.views.api_sentinel_ssh` | api |
| `/consultorio/api/sentinel/test-github/` | api_test_github_sentinel | `consultorio.views.api_test_github_sentinel` | api |
| `/consultorio/api/signos-vitales/<int:paciente_id>/tendencia/` | api_signos_vitales_tendencia | `consultorio.views.api_signos_vitales_tendencia` | api |
| `/consultorio/api/subir-archivo/` | api_subir_archivo | `consultorio.views.api_subir_archivo` | api |
| `/consultorio/api/verificar-gemini/` | api_verificar_gemini | `consultorio.api_views.verificar_api_gemini` | api |
| `/consultorio/certificado/<int:certificado_id>/` | ver_certificado | `consultorio.views.ver_certificado` | ui |
| `/consultorio/certificado/nuevo/` | generar_certificado | `consultorio.views.generar_certificado` | ui |
| `/consultorio/certificado/nuevo/<int:consulta_id>/` | generar_certificado_consulta | `consultorio.views.generar_certificado` | ui |
| `/consultorio/cobros/` | cobro_consulta | `consultorio.views.cobro_consulta` | ui |
| `/consultorio/cobros/liquidacion/` | reporte_liquidacion | `consultorio.views.reporte_liquidacion` | ui |
| `/consultorio/configuracion/` | configuracion_medico | `consultorio.views.configuracion_medico` | ui |
| `/consultorio/consulta/<int:cita_id>/` | consulta_soap_alt | `consultorio.views.nueva_consulta_soap` | ui |
| `/consultorio/encuestas/satisfaccion/` | encuestas_satisfaccion | `consultorio.views.encuestas_satisfaccion` | ui |
| `/consultorio/enfermeria/triage/` | lista_triage | `consultorio.views.lista_triage` | ui |
| `/consultorio/enfermeria/triage/<int:cita_id>/signos/` | captura_signos_vitales | `consultorio.views.captura_signos_vitales` | ui |
| `/consultorio/lista-espera/` | lista_espera | `consultorio.views.lista_espera` | ui |
| `/consultorio/marketing/campanas/` | campanas_marketing | `consultorio.views.campanas_marketing` | ui |
| `/consultorio/medico/captura/<int:cita_id>/` | captura_consulta | `consultorio.views.nueva_consulta_soap` | ui |
| `/consultorio/medico/consulta-sin-cita/` | consulta_sin_cita | `consultorio.views.consulta_sin_cita` | ui |
| `/consultorio/medico/consulta/<int:cita_id>/` | nueva_consulta_soap | `consultorio.views.nueva_consulta_soap` | ui |
| `/consultorio/medico/consulta/nueva/<uuid:paciente_uuid>/` | nueva_consulta_paciente | `consultorio.views.nueva_consulta_con_paciente` | ui |
| `/consultorio/medico/consulta/ver/<int:consulta_id>/` | ver_consulta_detalle | `consultorio.views.ver_consulta_detalle` | ui |
| `/consultorio/medico/detalle/<int:cita_id>/` | detalle_consulta | `consultorio.views.nueva_consulta_soap` | ui |
| `/consultorio/medico/lista-trabajo/` | lista_trabajo_medico | `consultorio.views.lista_trabajo_medico` | ui |
| `/consultorio/medico/nueva-consulta/` | nueva_consulta | `consultorio.views.nueva_consulta_simplificada` | ui |
| `/consultorio/paciente/<int:paciente_id>/archivos/` | archivos_paciente | `consultorio.views.archivos_paciente` | ui |
| `/consultorio/paciente/<int:paciente_id>/historial/` | historial_clinico_paciente | `consultorio.views.historial_clinico_paciente` | ui |
| `/consultorio/paciente/<int:paciente_id>/signos-vitales/` | historial_signos_vitales | `consultorio.views.historial_signos_vitales` | ui |
| `/consultorio/paciente/nuevo/` | crear_paciente_express | `consultorio.views.crear_paciente_express` | ui |
| `/consultorio/pdf/forense/<int:consulta_id>/` | pdf_expediente_forense | `consultorio.pdf_views.imprimir_expediente_forense` | pdf |
| `/consultorio/pdf/receta/<int:consulta_id>/` | pdf_receta_paciente | `consultorio.pdf_views_prislab.imprimir_receta_profesional` | pdf |
| `/consultorio/recepcion/` | tablero_recepcion | `consultorio.views.tablero_recepcion` | ui |
| `/consultorio/recepcion/agendar/` | agendar_cita | `consultorio.views.agendar_cita` | ui |
| `/consultorio/recepcion/check-in/<int:cita_id>/` | check_in_cita | `consultorio.views.check_in_cita` | ui |
| `/consultorio/reportes/productividad/` | reportes_productividad | `consultorio.views.reportes_productividad` | ui |
| `/consultorio/seguimiento/tratamiento/` | seguimiento_tratamiento | `consultorio.views.seguimiento_tratamiento` | ui |
| `/consultorio/sentinel/` | sentinel_dashboard | `consultorio.views.sentinel_dashboard` | ui |
| `/consultorio/sentinel/<int:incidencia_id>/` | sentinel_detalle | `consultorio.views.sentinel_detalle` | ui |
| `/consultorio/sentinel/ssh-guide/` | sentinel_ssh_guide | `consultorio.views.sentinel_ssh_guide` | ui |
| `/consultorio/telemedicina/` | videollamada_segura | `consultorio.views.videollamada_segura` | ui |
| `/consultorio/triaje-pre-cita/` | triaje_pre_cita | `consultorio.views.triaje_pre_cita` | ui |
| `/consultorio/vademecum/` | vademecum_lista | `consultorio.views.vademecum_lista` | ui |

## Prefijo `/contabilidad/` (16 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/contabilidad/` | dashboard_contabilidad | `core.views.contabilidad.dashboard_contabilidad` | ui |
| `/contabilidad/api/clientes/buscar/` | api_buscar_cliente | `contabilidad.views.api_buscar_cliente` | api |
| `/contabilidad/api/cuentas/` | api_cuentas | `core.views.contabilidad.api_cuentas` | api |
| `/contabilidad/catalogo-cuentas/` | catalogo_cuentas | `core.views.contabilidad.catalogo_cuentas` | ui |
| `/contabilidad/clientes/` | lista_clientes | `contabilidad.views.lista_clientes` | ui |
| `/contabilidad/clientes/crear/` | crear_cliente | `contabilidad.views.crear_cliente` | ui |
| `/contabilidad/crear-cuenta/` | crear_cuenta | `core.views.contabilidad.crear_cuenta` | ui |
| `/contabilidad/crear-poliza/` | crear_poliza | `core.views.contabilidad.crear_poliza` | ui |
| `/contabilidad/facturas/` | lista_facturas | `contabilidad.views.lista_facturas` | ui |
| `/contabilidad/facturas/<int:factura_id>/` | detalle_factura | `contabilidad.views.detalle_factura` | ui |
| `/contabilidad/facturas/<int:factura_id>/pdf/` | descargar_pdf | `contabilidad.views.descargar_pdf` | pdf |
| `/contabilidad/facturas/<int:factura_id>/timbrar/` | timbrar_factura | `contabilidad.views.timbrar_factura` | ui |
| `/contabilidad/facturas/crear/` | crear_factura | `contabilidad.views.crear_factura` | ui |
| `/contabilidad/poliza/<int:poliza_id>/` | ver_poliza | `core.views.contabilidad.ver_poliza` | ui |
| `/contabilidad/poliza/<int:poliza_id>/autorizar/` | autorizar_poliza | `core.views.contabilidad.autorizar_poliza` | ui |
| `/contabilidad/polizas/` | lista_polizas | `core.views.contabilidad.lista_polizas` | ui |

## Prefijo `/cotizacion/` (6 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/cotizacion/` | cotizacion_rapida | `core.views.cotizacion.cotizacion_rapida` | ui |
| `/cotizacion/api/buscar-estudios/` | api_buscar_estudios_cotizacion | `core.views.cotizacion.api_buscar_estudios_cotizacion` | api |
| `/cotizacion/api/buscar-paciente/` | api_buscar_paciente_cotizacion | `core.views.cotizacion.api_buscar_paciente_cotizacion` | api |
| `/cotizacion/api/convertir-orden/` | convertir_cotizacion_orden | `core.views.cotizacion.convertir_cotizacion_orden` | api |
| `/cotizacion/api/crear-paciente/` | api_crear_paciente_rapido | `core.views.cotizacion.api_crear_paciente_rapido` | api |
| `/cotizacion/api/enviar-whatsapp/` | api_enviar_whatsapp_cotizacion | `core.views.cotizacion.api_enviar_whatsapp_cotizacion` | api |

## Prefijo `/crm/` (14 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/crm/` | crm_dashboard | `core.views.crm.dashboard_crm` | ui |
| `/crm/api/kanban/` | crm_api_kanban | `core.views.crm.api_kanban_crm` | api |
| `/crm/clientes/` | lista_clientes_crm | `core.views.crm.lista_clientes_crm` | ui |
| `/crm/clientes/<int:cliente_id>/` | ver_cliente_crm | `core.views.crm.ver_cliente_crm` | ui |
| `/crm/clientes/<int:cliente_id>/interaccion/` | crear_interaccion_crm | `core.views.crm.crear_interaccion_crm` | ui |
| `/crm/clientes/crear/` | crear_cliente_crm | `core.views.crm.crear_cliente_crm` | ui |
| `/crm/oportunidades/` | lista_oportunidades_crm | `core.views.crm.lista_oportunidades_crm` | ui |
| `/crm/oportunidades/<int:oportunidad_id>/` | ver_oportunidad_crm | `core.views.crm.ver_oportunidad_crm` | ui |
| `/crm/oportunidades/<int:oportunidad_id>/cerrar/` | cerrar_oportunidad | `core.views.crm.cerrar_oportunidad` | ui |
| `/crm/oportunidades/crear/` | crear_oportunidad_crm | `core.views.crm.crear_oportunidad_crm` | ui |
| `/crm/prospectos/` | crm_lista_prospectos | `core.views.crm.lista_prospectos` | ui |
| `/crm/prospectos/<int:pk>/` | crm_detalle_prospecto | `core.views.crm.detalle_prospecto` | ui |
| `/crm/prospectos/<int:pk>/seguimiento/` | crm_agregar_seguimiento | `core.views.crm.agregar_seguimiento` | ui |
| `/crm/prospectos/nuevo/` | crm_crear_prospecto | `core.views.crm.crear_prospecto` | ui |

## Prefijo `/cron/` (2 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/cron/check-metrologia/` | cron_check_metrologia | `core.views.cron_tasks.cron_check_metrologia` | ui |
| `/cron/check-stock-critico/` | cron_check_stock_critico | `core.views.cron_tasks.cron_check_stock_critico` | ui |

## Prefijo `/dashboard/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/dashboard/` | dashboard | `core.views.director.dashboard_director` | ui |

## Prefijo `/dashboard-unificado/` (2 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/dashboard-unificado/` | dashboard_unificado | `core.views.dashboard_unificado.dashboard_unificado` | ui |
| `/dashboard-unificado/api/kpis-tiempo-real/` | api_kpis_tiempo_real | `core.views.dashboard_unificado.api_kpis_tiempo_real` | api |

## Prefijo `/director/` (23 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/director/` | dashboard_director | `core.views.director.dashboard_director` | ui |
| `/director/analizadores/` | director_analizadores | `core.views.director.director_analizadores` | ui |
| `/director/analizadores/<int:equipo_id>/mapeos/` | director_analizadores_mapeos | `core.views.director.director_analizadores_mapeos` | ui |
| `/director/analizadores/<int:equipo_id>/toggle/` | director_analizadores_toggle | `core.views.director.director_analizadores_toggle` | ui |
| `/director/analizadores/crear/` | director_analizadores_crear | `core.views.director.director_analizadores_crear` | ui |
| `/director/analizadores/mapeo/<int:mapeo_id>/eliminar/` | director_analizadores_eliminar_mapeo | `core.views.director.director_analizadores_eliminar_mapeo` | ui |
| `/director/analizadores/probar-conexion/` | director_analizadores_probar_conexion | `core.views.director.director_analizadores_probar_conexion` | ui |
| `/director/auditoria/incidencias/` | panel_auditoria_incidencias | `core.views.incidencias.panel_auditoria_incidencias` | ui |
| `/director/autorizaciones/` | listar_autorizaciones_pendientes | `core.views.autorizaciones.listar_autorizaciones_pendientes` | ui |
| `/director/autorizar/<uuid:uuid>/` | autorizar_solicitud | `core.views.autorizaciones.autorizar_solicitud` | ui |
| `/director/biblioteca/` | biblioteca_liderazgo | `core.views.biblioteca.biblioteca_liderazgo` | ui |
| `/director/biblioteca/agregar/` | agregar_libro | `core.views.biblioteca.agregar_libro` | ui |
| `/director/biblioteca/api/cambiar-estado/<int:libro_id>/` | api_cambiar_estado_libro | `core.views.biblioteca.api_cambiar_estado_libro` | api |
| `/director/buzon/` | buzon_kanban | `core.views.reporte_friccion.buzon_kanban` | ui |
| `/director/buzon/api/cambiar-estado/<int:queja_id>/` | api_cambiar_estado_queja | `core.views.buzon.api_cambiar_estado_queja` | api |
| `/director/buzon/api/obtener/` | api_obtener_quejas | `core.views.buzon.api_obtener_quejas` | api |
| `/director/calidad/` | dashboard_calidad | `core.views.reporte_friccion.buzon_kanban` | ui |
| `/director/coach/` | coach_ejecutivo | `core.views.coach.coach_ejecutivo` | ui |
| `/director/coach/api/preguntar/` | api_coach_preguntar | `core.views.coach.api_coach_preguntar` | api |
| `/director/ranking/` | ranking_desempeno | `core.views.ranking.ranking_desempeno` | ui |
| `/director/ranking/empleado/<int:empleado_id>/` | detalle_empleado_ranking | `core.views.ranking.detalle_empleado_ranking` | ui |
| `/director/war-room/` | war_room | `core.views.war_room.war_room` | ui |
| `/director/war-room/api/anomalias/` | api_war_room_anomalias | `core.views.war_room.api_war_room_anomalias` | api |

## Prefijo `/enfermeria/` (6 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/enfermeria/` | dashboard_enfermeria | `enfermeria.views.dashboard_enfermeria` | ui |
| `/enfermeria/alertas/` | alertas_signos_criticos | `enfermeria.views.alertas_signos_criticos` | ui |
| `/enfermeria/capturar-signos/<int:cita_id>/` | capturar_signos_vitales | `enfermeria.views.capturar_signos_vitales` | ui |
| `/enfermeria/graficas/<int:paciente_id>/` | graficas_tendencias | `enfermeria.views.graficas_tendencias` | ui |
| `/enfermeria/historial/<int:paciente_id>/` | historial_signos_paciente | `enfermeria.views.historial_signos_paciente` | ui |
| `/enfermeria/lista-triage/` | lista_pacientes_triage | `enfermeria.views.lista_pacientes_triage` | ui |

## Prefijo `/facturacion/` (3 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/facturacion/autofactura/` | autofactura_publica | `core.views.autofactura.autofactura_publica` | ui |
| `/facturacion/cfdi/<int:factura_id>/timbrar/` | api_marcar_cfdi_timbrada | `core.views.autofactura.api_marcar_cfdi_timbrada` | ui |
| `/facturacion/solicitudes/` | bandeja_cfdi | `core.views.autofactura.bandeja_cfdi` | ui |

## Prefijo `/farmacia/` (52 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/farmacia/` | dashboard_farmacia | `core.views.farmacia.dashboard_farmacia` | ui |
| `/farmacia/almacen/ajustes/` | ajustes_inventario | `core.views.farmacia.ajustes_inventario` | ui |
| `/farmacia/almacen/entradas/` | entrada_mercancia | `core.views.farmacia.entrada_mercancia` | ui |
| `/farmacia/api/buscar-producto-pdv/` | api_buscar_producto_pdv | `core.views.farmacia.api_buscar_producto_pdv` | api |
| `/farmacia/api/buscar-productos-compra/` | api_buscar_productos_compra | `core.views.farmacia.api_buscar_productos_compra` | api |
| `/farmacia/api/buscar-productos-lectura/` | api_buscar_productos_lectura | `core.views.farmacia.api_buscar_productos_lectura` | api |
| `/farmacia/api/carga-masiva/` | api_carga_masiva_productos | `core.views.farmacia.api_carga_masiva_productos` | api |
| `/farmacia/api/kpis/` | api_farmacia_kpis | `core.views.farmacia.api_farmacia_kpis` | api |
| `/farmacia/api/lotes-producto/<int:producto_id>/` | api_lotes_producto | `core.views.farmacia.api_lotes_producto` | api |
| `/farmacia/api/saldo-caja/` | api_saldo_caja | `core.views.farmacia.api_saldo_caja` | api |
| `/farmacia/api/validar-cupon/` | api_validar_cupon | `core.views.farmacia.api_validar_cupon` | api |
| `/farmacia/api/validar-pin-neto/` | validar_pin_precio_neto | `core.views.farmacia.validar_pin_precio_neto` | api |
| `/farmacia/compras/registrar/` | registrar_compra | `core.views.farmacia.registrar_compra` | ui |
| `/farmacia/corte-caja/` | corte_caja_legacy | `django.views.generic.base.view` | ui |
| `/farmacia/dashboard/` | dashboard_farmacia_v2 | `core.views.farmacia.dashboard_farmacia` | ui |
| `/farmacia/devoluciones/` | historial_devoluciones | `core.views.farmacia.historial_devoluciones` | ui |
| `/farmacia/devoluciones/buscar/` | buscar_venta_devolucion | `core.views.farmacia.buscar_venta_devolucion` | ui |
| `/farmacia/devoluciones/procesar/` | procesar_devolucion | `core.views.farmacia.procesar_devolucion` | ui |
| `/farmacia/erp/alertas/` | dashboard_alertas | `farmacia.views.view` | ui |
| `/farmacia/erp/antibioticos/reporte-cofepris/` | reporte_cofepris | `farmacia.views.soporte.reporte_cofepris` | ui |
| `/farmacia/erp/antibioticos/validar/` | validar_antibiotico | `farmacia.views.soporte.validar_venta_antibiotico` | ui |
| `/farmacia/erp/api/agregar-multi-lote/` | api_agregar_multi_lote | `farmacia.views.api_agregar_multi_lote` | api |
| `/farmacia/erp/api/agregar-producto-compra/` | api_agregar_producto_compra | `farmacia.views.api_agregar_producto_compra` | api |
| `/farmacia/erp/api/eliminar-producto-compra/<int:index>/` | api_eliminar_producto_compra | `farmacia.views.api_eliminar_producto_compra` | api |
| `/farmacia/erp/api/lotes-producto/<int:producto_id>/` | api_lotes_producto | `farmacia.views.api_lotes_producto` | api |
| `/farmacia/erp/caja/abrir/` | abrir_caja | `farmacia.views.soporte.abrir_caja` | ui |
| `/farmacia/erp/caja/verificar/` | verificar_apertura_caja | `farmacia.views.soporte.verificar_apertura_caja` | ui |
| `/farmacia/erp/compras/registrar/` | registrar_compra | `farmacia.views.registrar_compra` | ui |
| `/farmacia/erp/corte-caja/` | corte_caja | `farmacia.views.corte_caja_farmacia` | ui |
| `/farmacia/erp/devoluciones/` | dashboard_devoluciones | `farmacia.views.soporte.dashboard_devoluciones` | ui |
| `/farmacia/erp/devoluciones/autorizar/<int:devolucion_id>/` | autorizar_devolucion | `farmacia.views.soporte.autorizar_devolucion` | ui |
| `/farmacia/erp/devoluciones/buscar/` | buscar_venta_devolucion | `farmacia.views.soporte.buscar_venta_para_devolucion` | ui |
| `/farmacia/erp/devoluciones/procesar/` | procesar_devolucion | `farmacia.views.soporte.procesar_devolucion` | ui |
| `/farmacia/erp/entrada-express/` | entrada_express | `farmacia.views.soporte.entrada_express` | ui |
| `/farmacia/erp/generar-etiquetas/` | generar_etiquetas | `farmacia.views.generar_etiquetas` | ui |
| `/farmacia/erp/kardex/` | kardex_list | `farmacia.views.view` | ui |
| `/farmacia/erp/kardex/autorizar/<int:movimiento_id>/` | autorizar_movimiento | `farmacia.views.autorizar_movimiento` | ui |
| `/farmacia/erp/kardex/crear-movimiento/` | crear_movimiento | `farmacia.views.crear_movimiento_manual` | ui |
| `/farmacia/erp/reporte/valorizacion/` | reporte_valorizacion | `farmacia.views.reporte_valorizacion_inventario` | ui |
| `/farmacia/erp/semaforo-caducidad/` | dashboard_semaforo_caducidad | `farmacia.views.semaforo.dashboard_semaforo_caducidad` | ui |
| `/farmacia/erp/stock-critico/` | dashboard_stock_critico | `farmacia.views.semaforo.dashboard_stock_critico` | ui |
| `/farmacia/estadisticas/` | estadisticas_ventas | `core.views.farmacia.estadisticas_ventas` | ui |
| `/farmacia/etiquetas/imprimir/` | imprimir_etiquetas | `core.views.farmacia.imprimir_etiquetas` | pdf |
| `/farmacia/historial-ventas/` | lista_ventas_farmacia | `core.views.farmacia.lista_ventas_farmacia` | ui |
| `/farmacia/inventario/` | farmacia_inventario_general | `core.views.farmacia.inventario_general` | ui |
| `/farmacia/libro-control/` | libro_control | `core.views.farmacia.libro_control_antibioticos` | ui |
| `/farmacia/pdv/` | pdv_farmacia | `core.views.farmacia.pdv_farmacia` | ui |
| `/farmacia/pdv/buscar-fragmento/` | pdv_buscar_fragmento | `core.views.farmacia.pdv_buscar_fragmento` | ui |
| `/farmacia/politicas-descuento/` | politicas_descuento | `core.views.farmacia.gestionar_politicas_descuento` | ui |
| `/farmacia/ticket/<int:venta_id>/` | imprimir_ticket | `core.views.farmacia.imprimir_ticket` | ui |
| `/farmacia/ticket/<int:venta_id>/raw/` | imprimir_ticket_venta_raw | `core.views.farmacia.imprimir_ticket_raw` | ui |
| `/farmacia/ventas/cancelar/<int:venta_id>/` | cancelar_venta | `core.views.farmacia.cancelar_venta` | ui |

## Prefijo `/favicon.ico/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/favicon.ico` | — | `django.views.generic.base.view` | ui |

## Prefijo `/finanzas/` (13 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/finanzas/api/crear-convenio/` | api_crear_convenio | `core.views.cuentas_por_cobrar.api_crear_convenio` | api |
| `/finanzas/api/crear-cxc/` | api_crear_cxc | `core.views.cuentas_por_cobrar.api_crear_cxc` | api |
| `/finanzas/api/pago-cxc/` | api_pago_cxc | `core.views.cuentas_por_cobrar.api_registrar_pago_cxc` | api |
| `/finanzas/api/registro-gasto/` | api_registro_gasto | `core.views.farmacia.registrar_gasto` | api |
| `/finanzas/convenios/` | convenios_lista | `core.views.cuentas_por_cobrar.convenios_lista` | ui |
| `/finanzas/corte/` | corte_dia | `core.views.farmacia.corte_caja_dia` | ui |
| `/finanzas/cuentas-por-cobrar/` | cuentas_por_cobrar | `core.views.cuentas_por_cobrar.cuentas_por_cobrar_dashboard` | ui |
| `/finanzas/facturacion/` | facturacion_40 | `core.views.farmacia.facturacion_40` | ui |
| `/finanzas/farmacia/caja/` | caja_farmacia | `core.views.finanzas.view` | ui |
| `/finanzas/lab/caja/` | caja_laboratorio | `core.views.finanzas.view` | ui |
| `/finanzas/master/` | master_dashboard | `core.views.finanzas.view` | ui |
| `/finanzas/registro-gasto/` | registro_gasto | `core.views.farmacia.registrar_gasto` | ui |
| `/finanzas/reporte-fiscal/` | reporte_fiscal | `core.views.cuentas_por_cobrar.reporte_fiscal_mensual` | ui |

## Prefijo `/historial-resultados/` (4 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/historial-resultados/` | historial_resultados | `core.views.historial_resultados.historial_resultados` | ui |
| `/historial-resultados/<int:paciente_id>/` | historial_resultados_paciente | `core.views.historial_resultados.historial_resultados` | ui |
| `/historial-resultados/<int:paciente_id>/api/grafica/<int:estudio_id>/` | api_resultados_grafica | `core.views.historial_resultados.api_resultados_grafica` | api |
| `/historial-resultados/<int:paciente_id>/comparar/` | comparar_resultados | `core.views.historial_resultados.comparar_resultados` | ui |

## Prefijo `/home/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/home/` | home | `core.views.general.home_view` | ui |

## Prefijo `/ia/` (14 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/ia/` | dashboard | `ia.views.dashboard_ia` | ui |
| `/ia/api/analizar-sintomas/` | api_analizar_sintomas | `ia.views.analizar_sintomas` | api |
| `/ia/api/consultar/` | api_consultar_asistente | `ia.views.api_consultar_asistente` | api |
| `/ia/api/verificar-interacciones/` | api_verificar_interacciones | `ia.views.verificar_interacciones` | api |
| `/ia/asistente/` | asistente_medico | `ia.views.asistente_medico` | ui |
| `/ia/asistente/` | pris_ia_asistente | `core.views.pris_ia.asistente_page` | ui |
| `/ia/asistente/chat/` | pris_ia_chat | `core.views.pris_ia.asistente_chat` | ui |
| `/ia/asistente/reset/` | pris_ia_reset | `core.views.pris_ia.asistente_reset` | ui |
| `/ia/ocr/crear-orden/<int:pk>/` | crear_orden_desde_ocr | `ia.views.crear_orden_desde_ocr` | ui |
| `/ia/ocr/procesar/` | procesar_receta | `ia.views.procesar_receta_ocr` | ui |
| `/ia/ocr/resultados/<int:pk>/` | resultados_ocr | `ia.views.resultados_ocr` | ui |
| `/ia/panel/` | ia_dashboard | `core.views.ia_dashboard.ia_dashboard` | ui |
| `/ia/voz/resultados/<int:pk>/` | resultados_transcripcion | `ia.views.resultados_transcripcion` | ui |
| `/ia/voz/transcribir/` | transcribir_audio | `ia.views.transcribir_audio` | ui |

## Prefijo `/inventario/` (4 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/inventario/` | inventario_general | `inventario.views.dashboard_reactivos` | ui |
| `/inventario/api/registrar-merma/` | registrar_merma | `core.views.excepciones_lab.registrar_merma` | api |
| `/inventario/prediccion/` | inventario_prediccion | `core.views.inventario_predictivo.reporte_prediccion_stock` | ui |
| `/inventario/prediccion/api/` | api_prediccion_stock | `core.views.inventario_predictivo.api_prediccion_stock` | api |

## Prefijo `/iot/` (7 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/iot/` | dashboard_kioscos | `iot.views.dashboard_kioscos` | ui |
| `/iot/api/confirmar/<int:verificacion_id>/` | api_confirmar | `iot.views.api_kiosco_confirmar` | api |
| `/iot/api/crear-kiosco/` | api_crear_kiosco | `iot.views.api_crear_kiosco` | api |
| `/iot/api/enviar/` | api_enviar | `iot.views.api_enviar_a_kiosco` | api |
| `/iot/api/heartbeat/<int:kiosco_id>/` | api_heartbeat | `iot.views.api_kiosco_heartbeat` | api |
| `/iot/api/rechazar/<int:verificacion_id>/` | api_rechazar | `iot.views.api_kiosco_rechazar` | api |
| `/iot/api/toggle/<int:kiosco_id>/` | api_toggle_kiosco | `iot.views.api_toggle_kiosco` | api |

## Prefijo `/kiosko/` (2 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/kiosko/` | kiosko_index | `laboratorio.views.imprimir_zpl.kiosko_index` | ui |
| `/kiosko/check-in/<str:qr_token>/` | kiosko_check_in | `laboratorio.views.imprimir_zpl.kiosko_check_in_qr` | ui |

## Prefijo `/laboratorio/` (114 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/laboratorio/` | laboratorio_dashboard | `core.views.laboratorio.recepcion_lab` | ui |
| `/laboratorio/admin/cargar-tarifas-csv/` | cargar_tarifas_csv | `laboratorio.views_admin.cargar_tarifas_desde_csv` | ui |
| `/laboratorio/admin/cargar-tarifas/` | vista_cargar_tarifas | `laboratorio.views_admin.vista_cargar_tarifas` | ui |
| `/laboratorio/api/agregar-estudio/<int:orden_id>/` | agregar_estudio_orden | `core.views.excepciones_lab.agregar_estudio_orden` | api |
| `/laboratorio/api/bulk-imprimir/` | api_bulk_imprimir | `core.views.laboratorio.api_bulk_imprimir` | api |
| `/laboratorio/api/bulk-validar/` | api_bulk_validar | `core.views.laboratorio.api_bulk_validar` | api |
| `/laboratorio/api/buscar-estudios/` | api_buscar_estudios | `core.views.laboratorio.api_buscar_estudios` | api |
| `/laboratorio/api/buscar-estudios/` | api_buscar_estudios | `core.views.laboratorio.api_buscar_estudios` | api |
| `/laboratorio/api/cancelar-orden/<int:orden_id>/` | api_cancelar_orden | `core.views.excepciones_lab.cancelar_orden` | api |
| `/laboratorio/api/cancelar-orden/<int:orden_id>/` | cancelar_orden | `core.views.excepciones_lab.cancelar_orden` | api |
| `/laboratorio/api/cargar-preorden/` | api_cargar_preorden | `core.views.laboratorio.api_cargar_preorden` | api |
| `/laboratorio/api/cargar-preorden/` | api_cargar_preorden | `core.views.laboratorio.api_cargar_preorden` | api |
| `/laboratorio/api/cobrar-orden/<int:orden_id>/` | api_cobrar_orden | `core.views.laboratorio.api_cobrar_orden` | api |
| `/laboratorio/api/cobrar-orden/<int:orden_id>/` | api_cobrar_orden | `core.views.laboratorio.api_cobrar_orden` | api |
| `/laboratorio/api/convenios/` | api_convenios | `core.views.laboratorio.api_listar_convenios` | api |
| `/laboratorio/api/convenios/` | api_listar_convenios | `core.views.laboratorio.api_listar_convenios` | api |
| `/laboratorio/api/convenios/<int:convenio_id>/precios/` | api_precios_convenio | `core.views.laboratorio.api_precios_convenio` | api |
| `/laboratorio/api/convenios/<int:convenio_id>/precios/` | api_precios_convenio | `core.views.laboratorio.api_precios_convenio` | api |
| `/laboratorio/api/crear-medico/` | api_crear_medico | `laboratorio.views.crear_medico_ajax` | api |
| `/laboratorio/api/crear-orden/` | api_crear_orden | `core.views.laboratorio.crear_orden_servicio` | api |
| `/laboratorio/api/crear-orden/` | crear_orden_servicio | `core.views.laboratorio.crear_orden_servicio` | api |
| `/laboratorio/api/detalle-orden-completo/<int:orden_id>/` | api_detalle_orden_completo | `core.views.consulta_ordenes.api_detalle_orden_completo` | api |
| `/laboratorio/api/detalle-orden/<int:orden_id>/` | api_detalle_orden | `core.views.excepciones_lab.api_detalle_orden` | api |
| `/laboratorio/api/editar-paciente/<int:orden_id>/` | api_editar_paciente | `core.views.excepciones_lab.editar_paciente_orden` | api |
| `/laboratorio/api/editar-paciente/<int:orden_id>/` | editar_paciente_orden | `core.views.excepciones_lab.editar_paciente_orden` | api |
| `/laboratorio/api/eliminar-estudio/<int:orden_id>/<int:detalle_id>/` | eliminar_estudio_orden | `core.views.excepciones_lab.eliminar_estudio_orden` | api |
| `/laboratorio/api/escanear-identidad/` | api_escanear_identidad | `core.views.laboratorio.escanear_identidad_ia` | api |
| `/laboratorio/api/escanear-identidad/` | escanear_identidad_ia | `core.views.laboratorio.escanear_identidad_ia` | api |
| `/laboratorio/api/escanear-receta/` | api_escanear_receta | `core.views.laboratorio.escanear_receta_ia` | api |
| `/laboratorio/api/escanear-receta/` | escanear_receta_ia | `core.views.laboratorio.escanear_receta_ia` | api |
| `/laboratorio/api/estado/<int:orden_id>/` | api_estado_orden | `core.views.laboratorio.api_estado_orden` | api |
| `/laboratorio/api/estudios/<int:estudio_id>/parametros/` | api_parametros_estudio | `core.views.laboratorio_config.api_parametros_estudio` | api |
| `/laboratorio/api/generar-reporte/<int:orden_id>/` | api_generar_reporte | `core.views.laboratorio_reportes.api_generar_y_guardar_reporte` | api |
| `/laboratorio/api/guardar-resultados/<int:orden_id>/` | api_guardar_resultados | `core.views.laboratorio.api_guardar_resultados` | api |
| `/laboratorio/api/guardar-resultados/<int:orden_id>/` | api_guardar_resultados | `core.views.laboratorio.api_guardar_resultados` | api |
| `/laboratorio/api/medicos/` | api_listar_medicos | `core.views.laboratorio.api_listar_medicos` | api |
| `/laboratorio/api/medicos/` | api_medicos | `core.views.laboratorio.api_listar_medicos` | api |
| `/laboratorio/api/orden/<int:orden_id>/datos/` | api_datos_orden | `core.views.laboratorio.api_datos_orden` | api |
| `/laboratorio/api/orden/<int:orden_id>/editar-datos/` | api_editar_datos_orden | `core.views.laboratorio.api_editar_datos_orden` | api |
| `/laboratorio/api/orden/<int:orden_id>/editar-estudios/` | api_editar_estudios_orden | `core.views.laboratorio.api_editar_estudios_orden` | api |
| `/laboratorio/api/orden/<int:orden_id>/pagos/` | api_historial_pagos | `core.views.laboratorio.api_historial_pagos` | api |
| `/laboratorio/api/ordenes-recientes/` | api_ordenes_recientes | `core.views.laboratorio.api_ordenes_recientes` | api |
| `/laboratorio/api/ordenes-recientes/` | api_ordenes_recientes | `core.views.laboratorio.api_ordenes_recientes` | api |
| `/laboratorio/api/pago/<int:pago_id>/cancelar/` | api_cancelar_pago | `core.views.laboratorio.api_cancelar_pago` | api |
| `/laboratorio/api/preordenes-pendientes/` | api_preordenes_pendientes | `core.views.laboratorio.api_preordenes_pendientes` | api |
| `/laboratorio/api/preordenes-pendientes/` | api_preordenes_pendientes | `core.views.laboratorio.api_preordenes_pendientes` | api |
| `/laboratorio/api/rechazar-muestra/<int:detalle_id>/` | api_rechazar_muestra | `core.views.excepciones_lab.rechazar_muestra` | api |
| `/laboratorio/api/rechazar-muestra/<int:detalle_id>/` | rechazar_muestra | `core.views.excepciones_lab.rechazar_muestra` | api |
| `/laboratorio/api/toma-muestra/<int:orden_id>/` | api_toma_muestra | `core.views.laboratorio.api_toma_muestra` | api |
| `/laboratorio/api/toma-muestra/<int:orden_id>/` | api_toma_muestra | `core.views.laboratorio.api_toma_muestra` | api |
| `/laboratorio/api/toma-muestra/<int:orden_id>/finalizar/` | api_finalizar_toma | `core.views.laboratorio.api_finalizar_toma` | api |
| `/laboratorio/api/toma-muestra/<int:orden_id>/iniciar/` | api_iniciar_toma | `core.views.laboratorio.api_iniciar_toma` | api |
| `/laboratorio/api/validar-pin/<int:orden_id>/` | api_validar_pin | `core.views.laboratorio.api_validar_pin` | api |
| `/laboratorio/api/validar-valor-critico/<int:detalle_id>/` | api_validar_critico | `core.views.excepciones_lab.validar_valor_critico` | api |
| `/laboratorio/api/validar-valor-critico/<int:detalle_id>/` | validar_valor_critico | `core.views.excepciones_lab.validar_valor_critico` | api |
| `/laboratorio/captura/` | captura_sin_id | `core.views.laboratorio.registro_resultados_entrada` | ui |
| `/laboratorio/captura/<int:orden_id>/` | captura_resultados | `core.views.laboratorio_captura.captura_resultados_industrial` | ui |
| `/laboratorio/captura/<int:orden_id>/` | captura_resultados | `core.views.laboratorio_captura.captura_resultados_industrial` | ui |
| `/laboratorio/consulta-ordenes/` | consulta_ordenes | `core.views.consulta_ordenes.consulta_ordenes` | ui |
| `/laboratorio/control-calidad/` | control_calidad | `core.views.laboratorio.control_calidad` | ui |
| `/laboratorio/control-calidad/` | control_calidad | `core.views.laboratorio.control_calidad` | ui |
| `/laboratorio/dashboard-pendientes/` | dashboard_pendientes | `core.views.laboratorio.dashboard_pendientes` | ui |
| `/laboratorio/dashboard/` | dashboard_laboratorio | `core.views.laboratorio.dashboard_laboratorio` | ui |
| `/laboratorio/detalle-orden/<int:orden_id>/` | detalle_orden_view | `core.views.consulta_ordenes.detalle_orden_view` | ui |
| `/laboratorio/entrega-resultados/` | entrega_resultados | `core.views.entrega_resultados.entrega_resultados` | ui |
| `/laboratorio/entrega-resultados/<int:orden_id>/marcar-entregado/` | marcar_entregado | `core.views.entrega_resultados.marcar_entregado` | ui |
| `/laboratorio/entrega-resultados/<int:orden_id>/whatsapp-enviado/` | api_marcar_whatsapp_enviado | `core.views.entrega_resultados.api_marcar_whatsapp_enviado` | ui |
| `/laboratorio/entrega-resultados/api/enviar-email/` | api_enviar_email_masivo_resultados | `core.views.entrega_resultados.api_enviar_email_masivo_resultados` | api |
| `/laboratorio/etiqueta-previa/<int:orden_id>/` | vista_previa_etiqueta | `laboratorio.views.etiquetas.vista_previa_etiqueta` | ui |
| `/laboratorio/etiqueta-termica-qr/<int:orden_id>/` | imprimir_etiqueta_qr | `laboratorio.views.etiquetas.imprimir_etiqueta_qr` | ui |
| `/laboratorio/etiqueta-termica/<int:orden_id>/` | imprimir_etiqueta_tubo | `laboratorio.views.etiquetas.imprimir_etiqueta_tubo` | ui |
| `/laboratorio/etiquetas-lote/` | imprimir_etiquetas_lote | `laboratorio.views.etiquetas.imprimir_etiquetas_lote` | ui |
| `/laboratorio/etiquetas/<int:orden_id>/` | etiquetas | `core.views.laboratorio.imprimir_etiquetas_lab` | ui |
| `/laboratorio/etiquetas/<int:orden_id>/` | imprimir_etiquetas_lab | `core.views.laboratorio.imprimir_etiquetas_lab` | ui |
| `/laboratorio/etiquetas/<int:orden_id>/raw/` | etiquetas_raw | `core.views.impresion.imprimir_etiquetas_raw` | ui |
| `/laboratorio/etiquetas/<int:orden_id>/raw/` | imprimir_etiquetas_raw | `core.views.impresion.imprimir_etiquetas_raw` | ui |
| `/laboratorio/hoja-trabajo/pdf/` | hoja_trabajo_pdf | `core.views.laboratorio.imprimir_hoja_trabajo_pdf` | pdf |
| `/laboratorio/hoja-trabajo/pdf/` | imprimir_hoja_trabajo_pdf | `core.views.laboratorio.imprimir_hoja_trabajo_pdf` | pdf |
| `/laboratorio/imprimir/<int:orden_id>/` | imprimir_resultados | `core.views.laboratorio_reportes.imprimir_resultados` | pdf |
| `/laboratorio/imprimir/<int:orden_id>/` | imprimir_resultados | `core.views.laboratorio_reportes.imprimir_resultados` | pdf |
| `/laboratorio/lims/estudios/` | lista_pruebas | `core.views.laboratorio_config.lista_pruebas` | ui |
| `/laboratorio/lims/estudios/<int:estudio_id>/duplicar/` | duplicar_prueba | `core.views.laboratorio_config.duplicar_prueba` | ui |
| `/laboratorio/lims/estudios/<int:estudio_id>/editar/` | configurar_prueba_editar | `core.views.laboratorio_config.configurar_prueba` | ui |
| `/laboratorio/lims/estudios/<int:estudio_id>/eliminar/` | eliminar_prueba | `core.views.laboratorio_config.eliminar_prueba` | ui |
| `/laboratorio/lims/estudios/nuevo/` | configurar_prueba | `core.views.laboratorio_config.configurar_prueba` | ui |
| `/laboratorio/lims/parametros/<int:parametro_id>/rangos/` | configurar_rangos | `core.views.laboratorio_config.configurar_rangos` | ui |
| `/laboratorio/lista-trabajo/` | lista_trabajo | `core.views.laboratorio.lista_trabajo_lab` | ui |
| `/laboratorio/lista-trabajo/` | lista_trabajo_lab | `core.views.laboratorio.lista_trabajo_lab` | ui |
| `/laboratorio/maquila/` | maquila_envios | `core.views.maquila.maquila_envios` | ui |
| `/laboratorio/maquila/<int:orden_id>/enviar/` | enviar_a_maquila | `core.views.maquila.enviar_a_maquila` | ui |
| `/laboratorio/monitor/` | monitor_produccion | `core.views.monitor_produccion.monitor_produccion` | ui |
| `/laboratorio/monitor/api/avanzar-estado/` | api_avanzar_estado | `core.views.monitor_produccion.api_avanzar_estado` | api |
| `/laboratorio/monitor/api/datos/` | api_monitor_datos | `core.views.monitor_produccion.api_monitor_datos` | api |
| `/laboratorio/notificacion-panico/<int:orden_id>/` | notificacion_panico | `core.views.laboratorio_captura.registrar_notificacion_panico` | ui |
| `/laboratorio/notificacion-panico/<int:orden_id>/` | registrar_notificacion_panico | `core.views.laboratorio_captura.registrar_notificacion_panico` | ui |
| `/laboratorio/paciente/<int:paciente_id>/historial/` | historial_paciente | `core.views.laboratorio.historial_lab_paciente` | ui |
| `/laboratorio/pacientes/` | lista_pacientes | `core.views.laboratorio.lista_pacientes_lab` | ui |
| `/laboratorio/recepcion/` | recepcion | `core.views.laboratorio.recepcion_lab` | ui |
| `/laboratorio/recepcion/` | recepcion_lab | `core.views.laboratorio.recepcion_lab` | ui |
| `/laboratorio/registro-resultados/` | registro_resultados | `core.views.laboratorio.registro_resultados_entrada` | ui |
| `/laboratorio/reporte-tiempos-proceso/` | reporte_tiempos_proceso_v2 | `core.views.laboratorio.reporte_tiempos_proceso` | ui |
| `/laboratorio/reporte-tiempos/` | reporte_tiempos_proceso | `core.views.laboratorio.reporte_tiempos_proceso` | ui |
| `/laboratorio/resultados/<int:orden_id>/pdf/` | imprimir_resultados_pdf | `core.views.laboratorio.imprimir_resultados_pdf` | pdf |
| `/laboratorio/resultados/<int:orden_id>/pdf/` | resultados_pdf | `core.views.laboratorio.imprimir_resultados_pdf` | pdf |
| `/laboratorio/resultados/publico/<str:token>/` | resultados_publicos | `core.views.entrega_resultados.resultados_publicos` | ui |
| `/laboratorio/ticket/<int:orden_id>/` | imprimir_ticket_lab | `core.views.laboratorio.imprimir_ticket_lab` | ui |
| `/laboratorio/ticket/<int:orden_id>/` | ticket | `core.views.laboratorio.imprimir_ticket_lab` | ui |
| `/laboratorio/ticket/<int:orden_id>/raw/` | imprimir_ticket_raw | `core.views.impresion.imprimir_ticket_raw` | ui |
| `/laboratorio/ticket/<int:orden_id>/raw/` | ticket_raw | `core.views.impresion.imprimir_ticket_raw` | ui |
| `/laboratorio/toma-muestra/` | toma_muestra | `core.views.laboratorio.toma_muestra_index` | ui |
| `/laboratorio/toma-muestra/` | toma_muestra_index | `core.views.laboratorio.toma_muestra_index` | ui |
| `/laboratorio/toma-muestra/<int:orden_id>/preparacion/` | preparacion_toma | `core.views.laboratorio.preparacion_toma` | ui |
| `/laboratorio/worklist/qr/<str:token>/` | abrir_worklist_qr | `core.views.laboratorio.abrir_worklist_qr` | ui |
| `/laboratorio/worklist/qr/<str:token>/` | worklist_qr | `core.views.laboratorio.abrir_worklist_qr` | ui |

## Prefijo `/lims/` (41 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/lims/analitos/` | lims_analitos | `lims.views.analitos.lista` | ui |
| `/lims/analitos/<int:pk>/` | lims_analito_detalle | `lims.views.analitos.detalle` | ui |
| `/lims/analitos/<int:pk>/editar/` | lims_analito_editar | `lims.views.analitos.editar` | ui |
| `/lims/api/analitos/<int:pk>/rangos/` | lims_api_rangos | `lims.views.analitos.api_rangos` | api |
| `/lims/api/analitos/buscar/` | lims_api_buscar_analitos | `lims.views.perfiles.api_buscar_analitos` | api |
| `/lims/api/estudios/<int:estudio_id>/parametros/` | api_parametros_estudio | `core.views.laboratorio_config.api_parametros_estudio` | api |
| `/lims/api/parametros/<int:parametro_id>/eliminar/` | api_soft_delete_parametro | `core.views.laboratorio_config.api_soft_delete_parametro` | api |
| `/lims/api/parametros/<int:parametro_id>/rangos/` | api_rangos_parametro | `core.views.laboratorio_config.api_rangos_parametro` | api |
| `/lims/api/parametros/<int:parametro_id>/rangos/<int:rango_id>/` | api_rango_detalle | `core.views.laboratorio_config.api_rango_detalle` | api |
| `/lims/api/parametros/buscar/` | api_buscar_parametros | `core.views.laboratorio_config.api_buscar_parametros` | api |
| `/lims/api/perfiles/` | lims_api_perfiles | `lims.urls._api_perfiles_lista` | api |
| `/lims/api/precios/agregar-analito/` | lims_api_precios_agregar_analito | `lims.views.precios.api_agregar_analito_precio` | api |
| `/lims/api/precios/buscar-analitos/` | lims_api_precios_buscar_analitos | `lims.views.precios.api_buscar_analitos_precios` | api |
| `/lims/api/rangos/<int:rango_pk>/eliminar/` | lims_api_rango_eliminar | `lims.views.analitos.api_rango_eliminar` | api |
| `/lims/estudios/` | lista_pruebas | `core.views.laboratorio_config.lista_pruebas` | ui |
| `/lims/estudios/<int:estudio_id>/duplicar/` | duplicar_prueba | `core.views.laboratorio_config.duplicar_prueba` | ui |
| `/lims/estudios/<int:estudio_id>/editar/` | editar_prueba_lims | `core.views.laboratorio_config.configurar_prueba` | ui |
| `/lims/estudios/<int:estudio_id>/eliminar/` | eliminar_prueba | `core.views.laboratorio_config.eliminar_prueba` | ui |
| `/lims/estudios/nuevo/` | configurar_prueba | `core.views.laboratorio_config.configurar_prueba` | ui |
| `/lims/paquetes/` | lims_paquetes | `lims.views.paquetes.lista` | ui |
| `/lims/paquetes/<int:pk>/` | lims_paquete_detalle | `lims.views.paquetes.detalle` | ui |
| `/lims/paquetes/<int:pk>/api/agregar-analito/` | lims_paquete_agregar_analito | `lims.views.paquetes.api_agregar_analito` | api |
| `/lims/paquetes/<int:pk>/api/agregar-perfil/` | lims_paquete_agregar_perfil | `lims.views.paquetes.api_agregar_perfil` | api |
| `/lims/paquetes/<int:pk>/api/quitar-analito/<int:analito_pk>/` | lims_paquete_quitar_analito | `lims.views.paquetes.api_quitar_analito` | api |
| `/lims/paquetes/<int:pk>/api/quitar-perfil/<int:perfil_pk>/` | lims_paquete_quitar_perfil | `lims.views.paquetes.api_quitar_perfil` | api |
| `/lims/paquetes/<int:pk>/editar/` | lims_paquete_editar | `lims.views.paquetes.editar` | ui |
| `/lims/paquetes/nuevo/` | lims_paquete_nuevo | `lims.views.paquetes.nuevo` | ui |
| `/lims/parametros/` | lista_parametros | `core.views.laboratorio_config.lista_parametros` | ui |
| `/lims/parametros/<int:parametro_id>/editar/` | editar_parametro | `core.views.laboratorio_config.editar_parametro` | ui |
| `/lims/parametros/<int:parametro_id>/rangos/` | configurar_rangos | `core.views.laboratorio_config.configurar_rangos` | ui |
| `/lims/parametros/nuevo/` | nuevo_parametro | `core.views.laboratorio_config.editar_parametro` | ui |
| `/lims/parametros/nuevo/estudio/<int:estudio_id>/` | nuevo_parametro_estudio | `core.views.laboratorio_config.editar_parametro` | ui |
| `/lims/perfiles/` | lims_perfiles | `lims.views.perfiles.lista` | ui |
| `/lims/perfiles/<int:pk>/` | lims_perfil_detalle | `lims.views.perfiles.detalle` | ui |
| `/lims/perfiles/<int:pk>/api/agregar-analito/` | lims_perfil_agregar_analito | `lims.views.perfiles.api_agregar_analito` | api |
| `/lims/perfiles/<int:pk>/api/quitar-analito/<int:analito_pk>/` | lims_perfil_quitar_analito | `lims.views.perfiles.api_quitar_analito` | api |
| `/lims/perfiles/<int:pk>/editar/` | lims_perfil_editar | `lims.views.perfiles.editar` | ui |
| `/lims/perfiles/nuevo/` | lims_perfil_nuevo | `lims.views.perfiles.nuevo` | ui |
| `/lims/precios/` | lims_precios | `lims.views.precios.lista` | ui |
| `/lims/precios/<int:precio_pk>/actualizar/` | lims_precio_actualizar | `lims.views.precios.actualizar_precio` | ui |
| `/lims/precios/ajuste-masivo/` | lims_ajuste_masivo | `lims.views.precios.ajuste_masivo` | ui |

## Prefijo `/login/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/login/` | login | `core.views.general.view` | ui |

## Prefijo `/logistica/` (11 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/logistica/` | monitor_rutas | `logistica.views.monitor_rutas` | ui |
| `/logistica/mapa/` | mapa_rutas | `logistica.views.mapa_rutas` | ui |
| `/logistica/rastrear/<uuid:token>/` | rastrear_transferencia | `logistica.views.rastrear_transferencia` | ui |
| `/logistica/rutas-recoleccion/` | rutas_recoleccion | `core.views.operaciones.rutas_recoleccion` | ui |
| `/logistica/transferencias/` | lista_transferencias | `logistica.views.lista_transferencias` | ui |
| `/logistica/transferencias/<int:transferencia_id>/` | detalle_transferencia | `logistica.views.detalle_transferencia` | ui |
| `/logistica/transferencias/<int:transferencia_id>/agregar-producto/` | agregar_producto_transferencia | `logistica.views.agregar_producto_transferencia` | ui |
| `/logistica/transferencias/<int:transferencia_id>/enviar/` | enviar_transferencia | `logistica.views.enviar_transferencia` | ui |
| `/logistica/transferencias/<int:transferencia_id>/recibir/` | recibir_transferencia | `logistica.views.recibir_transferencia` | ui |
| `/logistica/transferencias/crear/` | crear_transferencia | `logistica.views.crear_transferencia` | ui |
| `/logistica/visita/<int:visita_id>/asignar/` | asignar_visita | `logistica.views.asignar_visita` | ui |

## Prefijo `/logout/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/logout/` | logout | `core.views.general.logout_view` | ui |

## Prefijo `/mantenimiento/` (32 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/mantenimiento/` | mantenimiento_root | `django.views.generic.base.view` | ui |
| `/mantenimiento/api/checklist-bloqueado/` | api_checklist_bloqueado | `mantenimiento.views.api_checklist_bloqueado` | api |
| `/mantenimiento/api/iot/lectura/` | api_iot_lectura | `mantenimiento.views_metrologia.api_iot_lectura` | api |
| `/mantenimiento/api/stock-lote/` | api_stock_lote | `mantenimiento.views.api_stock_lote_para_refaccion` | api |
| `/mantenimiento/checklist/<int:protocolo_pk>/<int:expediente_pk>/` | ejecutar_checklist | `mantenimiento.views.ejecutar_checklist` | ui |
| `/mantenimiento/checklist/bypass/<int:ejecucion_pk>/` | bypass_checklist | `mantenimiento.views.bypass_checklist` | ui |
| `/mantenimiento/diagnostico/<int:expediente_pk>/` | diagnostico_inicio | `mantenimiento.views.diagnostico_inicio` | ui |
| `/mantenimiento/diagnostico/arbol/<int:arbol_pk>/` | diagnostico_nodo_raiz | `mantenimiento.views.diagnostico_nodo` | ui |
| `/mantenimiento/diagnostico/arbol/<int:arbol_pk>/nodo/<int:nodo_pk>/` | diagnostico_nodo | `mantenimiento.views.diagnostico_nodo` | ui |
| `/mantenimiento/equipos/` | lista_expedientes | `mantenimiento.views.lista_expedientes` | ui |
| `/mantenimiento/equipos/<int:pk>/` | detalle_expediente | `mantenimiento.views.detalle_expediente` | ui |
| `/mantenimiento/equipos/nuevo/` | crear_expediente | `mantenimiento.views.crear_expediente` | ui |
| `/mantenimiento/metrologia/` | lista_certificados | `mantenimiento.views_metrologia.lista_certificados` | ui |
| `/mantenimiento/metrologia/<int:pk>/eliminar/` | eliminar_certificado | `mantenimiento.views_metrologia.eliminar_certificado` | ui |
| `/mantenimiento/metrologia/equipo/<int:expediente_pk>/` | subir_certificado_equipo | `mantenimiento.views_metrologia.subir_certificado` | ui |
| `/mantenimiento/metrologia/nuevo/` | subir_certificado | `mantenimiento.views_metrologia.subir_certificado` | ui |
| `/mantenimiento/operativo/` | lista_equipos_operativo | `mantenimiento.views.lista_equipos_operativo` | ui |
| `/mantenimiento/qr/<uuid:uid>/` | qr_equipo | `mantenimiento.views.qr_equipo_publico` | ui |
| `/mantenimiento/sensores/` | lista_sensores | `mantenimiento.views_metrologia.lista_sensores` | ui |
| `/mantenimiento/sensores/dashboard/` | dashboard_sensores | `mantenimiento.views_metrologia.dashboard_sensores` | ui |
| `/mantenimiento/sensores/lectura/` | registrar_lectura | `mantenimiento.views_metrologia.registrar_lectura_manual` | ui |
| `/mantenimiento/sensores/nuevo/` | crear_sensor | `mantenimiento.views_metrologia.crear_sensor` | ui |
| `/mantenimiento/tco/` | dashboard_tco | `mantenimiento.views.dashboard_tco` | ui |
| `/mantenimiento/tickets/` | lista_tickets | `mantenimiento.views.lista_tickets` | ui |
| `/mantenimiento/tickets/<int:pk>/` | detalle_ticket | `mantenimiento.views.detalle_ticket` | ui |
| `/mantenimiento/tickets/nuevo/` | crear_ticket | `mantenimiento.views.crear_ticket` | ui |
| `/mantenimiento/tickets/nuevo/<int:expediente_pk>/` | crear_ticket_equipo | `mantenimiento.views.crear_ticket` | ui |
| `/mantenimiento/wizard/` | wizard_dashboard | `mantenimiento.views.wizard_dashboard` | ui |
| `/mantenimiento/wizard/arbol/<int:pk>/` | wizard_arbol_editar | `mantenimiento.views.wizard_arbol` | ui |
| `/mantenimiento/wizard/arbol/nuevo/` | wizard_arbol_nuevo | `mantenimiento.views.wizard_arbol` | ui |
| `/mantenimiento/wizard/protocolo/<int:pk>/` | wizard_protocolo_editar | `mantenimiento.views.wizard_protocolo` | ui |
| `/mantenimiento/wizard/protocolo/nuevo/` | wizard_protocolo_nuevo | `mantenimiento.views.wizard_protocolo` | ui |

## Prefijo `/manual/` (2 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/manual/` | manual_operativo | `core.views.manual.manual_operativo` | ui |
| `/manual/pdf/` | manual_operativo_pdf | `core.views.manual.manual_operativo_pdf` | pdf |

## Prefijo `/marketing/` (14 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/marketing/` | dashboard_marketing | `marketing.views.dashboard_marketing` | ui |
| `/marketing/api/crear-campana/` | api_crear_campana | `marketing.views.api_crear_campana` | api |
| `/marketing/api/generar-cupon/` | api_generar_cupon | `marketing.views.api_generar_cupon` | api |
| `/marketing/api/ia/pacientes-inactivos/` | api_pacientes_inactivos | `marketing.views.api_detectar_pacientes_inactivos` | api |
| `/marketing/campanas/` | lista_campanas | `marketing.views.lista_campanas` | ui |
| `/marketing/campanas/<int:campana_id>/editar/` | editar_campana | `marketing.views.editar_campana` | ui |
| `/marketing/campanas/crear/` | crear_campana | `marketing.views.crear_campana` | ui |
| `/marketing/campanas/dashboard/` | dashboard_campanas | `marketing.views.dashboard_campanas` | ui |
| `/marketing/contactos/` | lista_contactos | `marketing.views.lista_contactos` | ui |
| `/marketing/contactos/importar/` | importar_contactos | `marketing.views.importar_contactos` | ui |
| `/marketing/cupones/` | lista_cupones | `marketing.views.lista_cupones` | ui |
| `/marketing/cupones/generar/` | generar_cupon | `marketing.views.generar_cupon` | ui |
| `/marketing/entrenamiento/` | entrenamiento_ia | `marketing.views.entrenamiento_ia` | ui |
| `/marketing/ia/reactivacion/` | reactivacion_ia | `marketing.views.dashboard_reactivacion_ia` | ui |

## Prefijo `/media/` (2 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/^media/(?P<path>.*)$` | — | `django.views.static.serve` | ui |
| `/media/logos/LOGO_PRISLAB.png` | — | `django.views.generic.base.view` | ui |

## Prefijo `/medico/` (14 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/medico/` | medico | `core.views.general.dashboard_medico` | ui |
| `/medico/api/buscar-paciente-avanzado/` | api_buscar_paciente_avanzado | `core.views.expediente.api_buscar_paciente_avanzado` | api |
| `/medico/api/buscar-paciente/` | buscar_paciente | `core.views.pacientes.buscar_paciente` | api |
| `/medico/api/verificar-existencia-farmacia/` | verificar_existencia_farmacia | `core.views.medico.verificar_existencia_farmacia` | api |
| `/medico/api/verificar-qr-receta/` | verificar_qr_receta | `core.views.medico.verificar_qr_receta` | api |
| `/medico/consulta/` | consulta_medica | `core.views.medico.consulta_medica` | ui |
| `/medico/consulta/<int:paciente_id>/` | consulta_medica | `core.views.medico.consulta_medica` | ui |
| `/medico/expediente/<int:paciente_id>/` | expediente_clinico_medico | `core.views.expediente.expediente_clinico` | ui |
| `/medico/receta/<int:receta_id>/` | ver_receta_medica | `core.views.medico.ver_receta_medica` | ui |
| `/medico/receta/<int:receta_id>/pdf/` | generar_pdf_receta | `core.views.medico.generar_pdf_receta` | pdf |
| `/medico/ultrasonido/<int:reporte_id>/pdf/` | descargar_pdf_ultrasonido | `core.views.medico.descargar_pdf_ultrasonido` | pdf |
| `/medico/ultrasonido/captura/` | captura_reporte_usg | `core.views.medico.captura_reporte_usg` | ui |
| `/medico/ultrasonido/captura/<int:paciente_id>/` | captura_reporte_usg_paciente | `core.views.medico.captura_reporte_usg` | ui |
| `/medico/ultrasonido/lista-trabajo/` | lista_trabajo_usg | `core.views.medico.lista_trabajo_usg` | ui |

## Prefijo `/nomina/` (9 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/nomina/` | nomina_dashboard | `core.views.nomina.dashboard_nomina` | ui |
| `/nomina/api/resumen/` | nomina_api_resumen | `core.views.nomina.api_resumen_nomina` | api |
| `/nomina/periodos/` | nomina_lista_periodos | `core.views.nomina.lista_periodos` | ui |
| `/nomina/periodos/<int:periodo_id>/calcular/` | calcular_nomina | `core.views.nomina.calcular_nomina` | ui |
| `/nomina/periodos/<int:pk>/` | nomina_detalle_periodo | `core.views.nomina.detalle_periodo` | ui |
| `/nomina/periodos/<int:pk>/pagar/` | nomina_marcar_pagado | `core.views.nomina.marcar_periodo_pagado` | ui |
| `/nomina/periodos/nuevo/` | nomina_crear_periodo | `core.views.nomina.crear_periodo` | ui |
| `/nomina/recibos/<int:nomina_id>/autorizar/` | autorizar_nomina | `core.views.nomina.autorizar_nomina` | ui |
| `/nomina/recibos/<int:pk>/editar/` | nomina_editar_recibo | `core.views.nomina.editar_recibo` | ui |

## Prefijo `/notificaciones/` (9 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/notificaciones/` | notificaciones_lista | `core.views.notificaciones.lista_notificaciones` | ui |
| `/notificaciones/<int:notificacion_id>/leer/` | notificacion_leer | `core.views.notificaciones.marcar_leida` | ui |
| `/notificaciones/<int:notificacion_id>/marcar-leida/` | marcar_notificacion_leida | `core.views.notificaciones.marcar_leida` | ui |
| `/notificaciones/api/no-leidas/` | api_notificaciones_no_leidas | `core.views.notificaciones.api_notificaciones_badge` | api |
| `/notificaciones/badge/` | notificaciones_badge | `core.views.notificaciones.api_notificaciones_badge` | ui |
| `/notificaciones/configurar/` | configurar_notificaciones | `core.views.notificaciones.configurar_notificaciones` | ui |
| `/notificaciones/ejecutar-verificaciones/` | ejecutar_verificaciones | `core.views.notificaciones.ejecutar_verificaciones` | ui |
| `/notificaciones/marcar-todas-leidas/` | marcar_todas_leidas | `core.views.notificaciones.marcar_todas_leidas` | ui |
| `/notificaciones/marcar-todas/` | notificaciones_marcar_todas | `core.views.notificaciones.marcar_todas_leidas` | ui |

## Prefijo `/onboarding/` (4 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/onboarding/` | onboarding_wizard | `core.views.onboarding.view` | ui |
| `/onboarding/crear/` | onboarding_crear_empresa | `core.views.onboarding.view` | ui |
| `/onboarding/empresas/` | onboarding_listar_empresas | `core.views.onboarding.api_listar_empresas` | ui |
| `/onboarding/parse-excel/` | onboarding_parse_excel | `core.views.onboarding.api_parse_excel_personal` | ui |

## Prefijo `/pacientes/` (18 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/pacientes/` | lista_pacientes | `pacientes.views.lista_pacientes` | ui |
| `/pacientes/<int:paciente_id>/exportar-historial/` | exportar_historial_pdf | `core.views.paciente_detalle.exportar_historial_pdf` | ui |
| `/pacientes/<int:paciente_id>/graficas-signos/` | graficas_signos | `pacientes.views.graficas_signos_vitales` | ui |
| `/pacientes/<int:paciente_id>/historia-clinica/` | historia_clinica | `pacientes.views.historia_clinica_completa` | ui |
| `/pacientes/<int:paciente_id>/historial-360/` | historial_360 | `pacientes.views.historial_360_paciente` | ui |
| `/pacientes/<int:paciente_id>/timeline/` | timeline_consultas | `pacientes.views.timeline_consultas` | ui |
| `/pacientes/<int:pk>/expediente/` | expediente_clinico | `core.views.paciente_detalle.view` | ui |
| `/pacientes/api/<int:paciente_id>/datos-graficas/` | api_datos_graficas | `pacientes.views.api_datos_graficas_signos` | api |
| `/pacientes/portal/` | portal_login | `pacientes.portal_views.portal_login` | ui |
| `/pacientes/portal/cambiar-password/` | portal_cambiar_password | `pacientes.portal_views.wrapper` | ui |
| `/pacientes/portal/descargar-resultado/<int:orden_id>/` | portal_descargar_resultado | `pacientes.portal_views.wrapper` | ui |
| `/pacientes/portal/inicio/` | portal_dashboard | `pacientes.portal_views.wrapper` | ui |
| `/pacientes/portal/logout/` | portal_logout | `pacientes.portal_views.portal_logout` | ui |
| `/pacientes/portal/mi-perfil/` | portal_mi_perfil | `pacientes.portal_views.wrapper` | ui |
| `/pacientes/portal/mis-consultas/` | portal_mis_consultas | `pacientes.portal_views.wrapper` | ui |
| `/pacientes/portal/mis-estudios/` | portal_mis_estudios | `pacientes.portal_views.wrapper` | ui |
| `/pacientes/portal/mis-recetas/` | portal_mis_recetas | `pacientes.portal_views.wrapper` | ui |
| `/pacientes/portal/solicitar-acceso/` | solicitar_acceso | `pacientes.portal_views.solicitar_acceso` | ui |

## Prefijo `/pris/` (14 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/pris/acciones/` | lista_acciones_pris | `core.views.pris_jarvis.lista_acciones_pris` | ui |
| `/pris/acciones/<int:accion_id>/validar/` | validar_accion_pris | `core.views.pris_jarvis.validar_accion_pris` | ui |
| `/pris/api/accion/<int:accion_id>/confirmar/` | pris_confirmar_accion | `core.views.pris_ia.api_confirmar_accion` | api |
| `/pris/api/accion/<int:accion_id>/rechazar/` | pris_rechazar_accion | `core.views.pris_ia.api_rechazar_accion` | api |
| `/pris/api/acciones/pendientes/` | pris_acciones_pendientes | `core.views.pris_ia.api_acciones_pendientes` | api |
| `/pris/api/checklist-guia/` | pris_checklist_guia | `core.views.pris_checklist.api_guia_preguntas` | api |
| `/pris/api/checklist-nlp/` | pris_checklist_nlp | `core.views.pris_checklist.api_detectar_intents_checklist` | api |
| `/pris/api/consulta-voz/` | api_consulta_voz | `core.views.pris_jarvis.api_consulta_voz` | api |
| `/pris/api/crear-alerta-clinica/` | api_crear_alerta_clinica | `core.views.pris_jarvis.api_crear_alerta_clinica` | api |
| `/pris/api/crear-archivo-raw/` | api_crear_archivo_raw | `core.views.pris_jarvis.api_crear_archivo_raw` | api |
| `/pris/api/dictado-inventario/` | api_dictado_inventario | `core.views.pris_jarvis.api_dictado_inventario` | api |
| `/pris/api/dictado-resultado/` | api_dictado_resultado | `core.views.pris_jarvis.api_dictado_resultado` | api |
| `/pris/api/generar-hoja-trabajo/` | api_generar_hoja_trabajo | `core.views.pris_jarvis.api_generar_hoja_trabajo` | api |
| `/pris/api/ocr-documento/` | api_ocr_documento | `core.views.pris_jarvis.api_ocr_documento` | api |

## Prefijo `/recepcion/` (7 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/recepcion/` | dashboard_recepcion | `recepcion.views.dashboard_recepcion` | ui |
| `/recepcion/agendar-cita/` | agendar_cita | `recepcion.views.agendar_cita` | ui |
| `/recepcion/buscar-paciente/` | buscar_paciente | `recepcion.views.buscar_paciente` | ui |
| `/recepcion/check-in/<int:cita_id>/` | check_in_paciente | `recepcion.views.check_in_paciente` | ui |
| `/recepcion/cobrar/<int:cita_id>/` | cobrar_consulta | `recepcion.views.cobrar_consulta` | ui |
| `/recepcion/lista-espera/` | lista_espera | `recepcion.views.lista_espera` | ui |
| `/recepcion/registrar-paciente/` | registrar_paciente | `recepcion.views.registrar_paciente` | ui |

## Prefijo `/reporte-friccion/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/reporte-friccion/` | reporte_friccion | `core.views.reporte_friccion.reporte_friccion` | ui |

## Prefijo `/reportes/` (8 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/reportes/api/ventas-por-mes/` | api_ventas_por_mes | `core.views.reportes_financieros.api_ventas_por_mes` | api |
| `/reportes/balance-general/` | reporte_balance_general | `core.views.reportes_financieros.reporte_balance_general` | ui |
| `/reportes/balance-general/excel/` | exportar_excel_balance | `core.views.reportes_financieros.exportar_excel_balance` | ui |
| `/reportes/flujo-caja/` | reporte_flujo_caja | `core.views.reportes_financieros.reporte_flujo_caja` | ui |
| `/reportes/flujo-caja/excel/` | exportar_excel_flujo_caja | `core.views.reportes_financieros.exportar_excel_flujo_caja` | ui |
| `/reportes/ingresos-egresos/` | reporte_ingresos_egresos | `core.views.reportes_financieros.reporte_ingresos_egresos` | ui |
| `/reportes/ingresos-egresos/excel/` | exportar_excel_ingresos_egresos | `core.views.reportes_financieros.exportar_excel_ingresos_egresos` | ui |
| `/reportes/reporte-caja/` | genera_reporte_caja | `core.views.motor_financiero.genera_reporte_caja` | ui |

## Prefijo `/rh/` (10 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/rh/desempeno/<int:evaluacion_id>/` | ver_evaluacion_desempeno | `core.views.rh.ver_evaluacion_desempeno` | ui |
| `/rh/desempeno/nueva/` | nueva_evaluacion_desempeno | `core.views.rh.nueva_evaluacion_desempeno` | ui |
| `/rh/desempeno/nueva/<int:empleado_id>/` | nueva_evaluacion_desempeno | `core.views.rh.nueva_evaluacion_desempeno` | ui |
| `/rh/evaluaciones/` | lista_evaluaciones_39a | `core.views.rh.lista_evaluaciones_39a` | ui |
| `/rh/evaluaciones/<int:evaluacion_id>/` | ver_evaluacion_39a | `core.views.rh.ver_evaluacion_39a` | ui |
| `/rh/evaluaciones/<int:evaluacion_id>/pdf/` | descargar_pdf_evaluacion_39a | `core.views.rh.descargar_pdf_evaluacion_39a` | pdf |
| `/rh/evaluaciones/crear/` | crear_evaluacion_39a | `core.views.rh.crear_evaluacion_39a` | ui |
| `/rh/evaluaciones/crear/<int:empleado_id>/` | crear_evaluacion_39a | `core.views.rh.crear_evaluacion_39a` | ui |
| `/rh/matriz-talento/` | matriz_talento | `core.views.rh.matriz_talento` | ui |
| `/rh/mis-resultados/` | mis_resultados | `core.views.rh.mis_resultados` | ui |

## Prefijo `/seguridad/` (13 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/seguridad/2fa/` | configuracion_2fa | `seguridad.views.configuracion_2fa` | ui |
| `/seguridad/2fa/activar-totp/` | activar_totp | `seguridad.views.activar_totp` | ui |
| `/seguridad/2fa/codigos-backup/` | mostrar_codigos_backup | `seguridad.views.mostrar_codigos_backup` | ui |
| `/seguridad/2fa/confirmar-totp/<int:dispositivo_id>/` | confirmar_totp | `seguridad.views.confirmar_totp` | ui |
| `/seguridad/2fa/desactivar-totp/<int:dispositivo_id>/` | desactivar_totp | `seguridad.views.desactivar_totp` | ui |
| `/seguridad/2fa/regenerar-codigos/` | regenerar_codigos_backup | `seguridad.views.regenerar_codigos_backup` | ui |
| `/seguridad/api/estadisticas/` | api_estadisticas | `seguridad.views.api_estadisticas_seguridad` | api |
| `/seguridad/api/verificar-2fa/` | api_verificar_2fa | `seguridad.views.api_verificar_codigo_2fa` | api |
| `/seguridad/auditoria/` | dashboard_auditoria | `seguridad.views.dashboard_auditoria` | ui |
| `/seguridad/auditoria/logs/` | logs_auditoria | `seguridad.views.logs_auditoria` | ui |
| `/seguridad/sesiones/` | sesiones_activas | `seguridad.views.sesiones_activas` | ui |
| `/seguridad/sesiones/cerrar-todas/` | cerrar_todas_las_sesiones | `seguridad.views.cerrar_todas_las_sesiones` | ui |
| `/seguridad/sesiones/cerrar/<int:sesion_id>/` | cerrar_sesion_remota | `seguridad.views.cerrar_sesion_remota` | ui |

## Prefijo `/silo-lab/` (50 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/silo-lab/` | inventario_root | `django.views.generic.base.view` | ui |
| `/silo-lab/api/lotes-silo/` | api_lotes_silo | `inventario.views_traspasos.api_lotes_silo` | api |
| `/silo-lab/compras/` | lista_ordenes_compra | `inventario.views_compras.lista_ordenes_compra` | ui |
| `/silo-lab/compras/<int:pk>/` | detalle_oc | `inventario.views_compras.detalle_oc` | ui |
| `/silo-lab/compras/api/criticos/` | api_articulos_criticos | `inventario.views_compras.api_articulos_criticos` | api |
| `/silo-lab/compras/nueva/` | crear_orden_compra | `inventario.views_compras.crear_orden_compra` | ui |
| `/silo-lab/compras/proveedores/` | lista_proveedores | `inventario.views_compras.lista_proveedores` | ui |
| `/silo-lab/compras/proveedores/nuevo/` | crear_proveedor | `inventario.views_compras.crear_proveedor` | ui |
| `/silo-lab/consultorio/` | dashboard_consultorio | `inventario.views_consultorio.dashboard_consultorio` | ui |
| `/silo-lab/consultorio/catalogo/` | lista_insumos_consultorio | `inventario.views_consultorio.lista_insumos_consultorio` | ui |
| `/silo-lab/consultorio/catalogo/<int:pk>/editar/` | editar_insumo_consultorio | `inventario.views_consultorio.editar_insumo_consultorio` | ui |
| `/silo-lab/consultorio/catalogo/nuevo/` | crear_insumo_consultorio | `inventario.views_consultorio.crear_insumo_consultorio` | ui |
| `/silo-lab/consultorio/lotes/` | lista_lotes_consultorio | `inventario.views_consultorio.lista_lotes_consultorio` | ui |
| `/silo-lab/consultorio/lotes/nuevo/` | crear_lote_consultorio | `inventario.views_consultorio.crear_lote_consultorio` | ui |
| `/silo-lab/consultorio/salidas/` | lista_salidas_consultorio | `inventario.views_consultorio.lista_salidas_consultorio` | ui |
| `/silo-lab/consultorio/salidas/nueva/` | registrar_salida_consultorio | `inventario.views_consultorio.registrar_salida_consultorio` | ui |
| `/silo-lab/generales/` | dashboard_generales | `inventario.views_generales.dashboard_generales` | ui |
| `/silo-lab/generales/catalogo/` | lista_insumos_generales | `inventario.views_generales.lista_insumos_generales` | ui |
| `/silo-lab/generales/catalogo/<int:pk>/editar/` | editar_insumo_general | `inventario.views_generales.editar_insumo_general` | ui |
| `/silo-lab/generales/catalogo/nuevo/` | crear_insumo_general | `inventario.views_generales.crear_insumo_general` | ui |
| `/silo-lab/generales/lotes/` | lista_lotes_generales | `inventario.views_generales.lista_lotes_generales` | ui |
| `/silo-lab/generales/lotes/nuevo/` | crear_lote_general | `inventario.views_generales.crear_lote_general` | ui |
| `/silo-lab/generales/vales/` | lista_vales | `inventario.views_generales.lista_vales` | ui |
| `/silo-lab/generales/vales/<int:pk>/` | detalle_vale | `inventario.views_generales.detalle_vale` | ui |
| `/silo-lab/generales/vales/<int:pk>/cancelar/` | cancelar_vale | `inventario.views_generales.cancelar_vale` | ui |
| `/silo-lab/generales/vales/nuevo/` | crear_vale | `inventario.views_generales.crear_vale` | ui |
| `/silo-lab/lab/` | dashboard_reactivos | `inventario.views.dashboard_reactivos` | ui |
| `/silo-lab/lab/api/lotes/<int:reactivo_id>/` | api_lotes_por_reactivo | `inventario.views.api_lotes_por_reactivo` | api |
| `/silo-lab/lab/api/stock-critico/` | api_stock_critico | `inventario.views.api_stock_critico` | api |
| `/silo-lab/lab/catalogo/` | lista_reactivos | `inventario.views.lista_reactivos` | ui |
| `/silo-lab/lab/catalogo/<int:pk>/` | editar_reactivo | `inventario.views.editar_reactivo` | ui |
| `/silo-lab/lab/catalogo/<int:pk>/eliminar/` | eliminar_reactivo | `inventario.views.eliminar_reactivo` | ui |
| `/silo-lab/lab/catalogo/nuevo/` | crear_reactivo | `inventario.views.crear_reactivo` | ui |
| `/silo-lab/lab/consumo/` | lista_consumo | `inventario.views.lista_consumo` | ui |
| `/silo-lab/lab/consumo/<int:pk>/editar/` | editar_consumo | `inventario.views.editar_consumo` | ui |
| `/silo-lab/lab/consumo/<int:pk>/eliminar/` | eliminar_consumo | `inventario.views.eliminar_consumo` | ui |
| `/silo-lab/lab/consumo/nuevo/` | crear_consumo | `inventario.views.crear_consumo` | ui |
| `/silo-lab/lab/lotes/` | lista_lotes | `inventario.views.lista_lotes` | ui |
| `/silo-lab/lab/lotes/<int:pk>/` | detalle_lote | `inventario.views.detalle_lote` | ui |
| `/silo-lab/lab/lotes/<int:pk>/baja/` | baja_lote | `inventario.views.baja_lote` | ui |
| `/silo-lab/lab/lotes/<int:pk>/liberar/` | liberar_lote_qc | `inventario.views.liberar_lote_qc` | ui |
| `/silo-lab/lab/lotes/nuevo/` | crear_lote | `inventario.views.crear_lote` | ui |
| `/silo-lab/lab/salidas-tecnicas/` | lista_salidas_tecnicas | `inventario.views.lista_salidas_tecnicas` | ui |
| `/silo-lab/lab/salidas-tecnicas/nueva/` | crear_salida_tecnica | `inventario.views.crear_salida_tecnica` | ui |
| `/silo-lab/lab/trazabilidad/` | trazabilidad_lote | `inventario.views.trazabilidad_lote` | ui |
| `/silo-lab/notificaciones/` | lista_notificaciones | `inventario.views_traspasos.lista_notificaciones` | ui |
| `/silo-lab/notificaciones/<int:pk>/resolver/` | resolver_notificacion | `inventario.views_traspasos.resolver_notificacion` | ui |
| `/silo-lab/traspasos/` | lista_traspasos | `inventario.views_traspasos.lista_traspasos` | ui |
| `/silo-lab/traspasos/<int:pk>/` | detalle_traspaso | `inventario.views_traspasos.detalle_traspaso` | ui |
| `/silo-lab/traspasos/nuevo/` | crear_traspaso | `inventario.views_traspasos.crear_traspaso` | ui |

## Prefijo `/sw.js/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/sw.js` | service_worker | `core.views.general.service_worker_view` | ui |

## Prefijo `/transferencias/` (6 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/transferencias/` | lista_transferencias | `core.views.transferencias.lista_transferencias` | ui |
| `/transferencias/<int:transferencia_id>/` | ver_transferencia | `core.views.transferencias.ver_transferencia` | ui |
| `/transferencias/<int:transferencia_id>/enviar/` | enviar_transferencia | `core.views.transferencias.enviar_transferencia` | ui |
| `/transferencias/<int:transferencia_id>/recibir/` | recibir_transferencia | `core.views.transferencias.recibir_transferencia` | ui |
| `/transferencias/api/buscar-productos/` | api_buscar_productos_transferencia | `core.views.transferencias.api_buscar_productos_transferencia` | api |
| `/transferencias/crear/` | crear_transferencia | `core.views.transferencias.crear_transferencia` | ui |

## Prefijo `/tu-opinion/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/tu-opinion/` | tu_opinion | `core.views.buzon.tu_opinion` | ui |

## Prefijo `/validar/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/validar/resultado/<uuid:token>/` | validar_resultado | `core.views.laboratorio_reportes.validar_resultado` | ui |

## Prefijo `/voice/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/voice/logs/` | voice_logs_dashboard | `core.views.voice.dashboard_voice_logs` | ui |

## Prefijo `/root/` (1 rutas)

| Path | name | Vista (callback) | kind |
| :--- | :--- | :--- | :--- |
| `/` | login_root | `core.views.general.view` | ui |
