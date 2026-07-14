"""Build the single integrated audit report."""
import os

OUTPUT = 'audit/AUDITORIA_COMPLETA_E2E.md'

SECTIONS = [
    ('audit/00_INDICE.md', 'ÍNDICE'),
    ('audit/000_MANIFEST.md', 'MANIFIESTO'),
    ('audit/01_INTRODUCCION_ALCANCE.md', 'INTRODUCCIÓN Y ALCANCE'),
    ('audit/01_backend/_inventory_summary.md', 'INVENTARIO DE ARCHIVOS'),
    ('audit/01_backend/_domain_catalog.md', 'CATÁLOGO DE DOMINIOS'),
    ('audit/03_db/modelos_y_bd.md', 'BASE DE DATOS Y MODELOS'),
    ('audit/04_api/_api_inventory_summary.md', 'INVENTARIO DE URLS/API'),
    ('audit/05_pruebas/pruebas_y_calidad.md', 'PRUEBAS Y CALIDAD'),
    ('audit/06_seguridad/evidencias.md', 'EVIDENCIAS DE SEGURIDAD'),
    ('audit/07_infra/infraestructura.md', 'INFRAESTRUCTURA Y CI/CD'),
    ('audit/10_hallazgos/hallazgos.md', 'HALLAZGOS Y RIESGOS'),
    ('audit/11_conclusiones.md', 'CONCLUSIONES'),
    ('audit/12_roadmap.md', 'ROADMAP'),
]

with open(OUTPUT, 'w', encoding='utf-8') as out:
    out.write('# Auditoría Técnica E2E Completa — PRISLAB SaaS\n\n')
    out.write('**ID de auditoría:** AUD-20260713-210000  \n')
    out.write('**Rama:** `release/v1.0-local`  \n')
    out.write('**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`  \n')
    out.write('**Fecha:** 2026-07-13  \n')
    out.write('**Este documento integra toda la auditoría sin omisiones.**  \n\n')
    out.write('---\n\n')

    for path, title in SECTIONS:
        out.write(f'\n# {title}\n\n')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Remove top-level title if present to avoid duplicate h1
                lines = content.splitlines()
                if lines and lines[0].startswith('# '):
                    content = '\n'.join(lines[1:])
                out.write(content)
                if not content.endswith('\n'):
                    out.write('\n')
        else:
            out.write(f'**Archivo no encontrado:** {path}\n')
        out.write('\n---\n\n')

    out.write('\n# FIN DEL DOCUMENTO\n')

print(f'Wrote {OUTPUT}')
print(f'Size: {os.path.getsize(OUTPUT)} bytes')
