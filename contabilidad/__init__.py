"""
Modulo de Contabilidad Operativa - PRISLAB SaaS
================================================
ALCANCE REAL (no ERP completo):
  - Facturacion electronica CFDI 4.0 (borrador automatico + timbrado PAC via Facturama)
  - Catalogo de clientes de facturacion (ClienteFacturacion)
  - Polizas contables basicas vinculadas a operaciones (ventas, gastos)
  - Reportes fiscales operativos (no balances generales)

LO QUE NO ES:
  - No es un ERP contable completo: sin balance general, estado de resultados,
    cuentas contables mayores, depreciaciones, ni consolidacion.
  - No reemplaza al contador: los XML timbrados se entregan al despacho contable.

Las polizas, el balance y el catalogo contable son OPERATIVOS:
sirven para trazabilidad fiscal inmediata, no para cierre contable anual.

Deuda arquitectonica pendiente (si se requiere ERP completo en el futuro):
  - Automatizar asientos desde ventas (core.Venta -> poliza diario)
  - Automatizar asientos desde gastos (core.GastoOperativo -> poliza egreso)
  - Automatizar asientos desde nomina (core.ReciboNomina -> poliza nomina)
  - Automatizar asientos desde inventario (core.AjusteInventario -> poliza almacen)
"""
