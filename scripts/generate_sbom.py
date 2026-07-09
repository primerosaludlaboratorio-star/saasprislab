#!/usr/bin/env python
"""
generate_sbom.py

Genera un SBOM (Software Bill of Materials) en formato CycloneDX JSON a partir de
requirements.txt. No requiere instalar las dependencias.

Uso:
    python scripts/generate_sbom.py
    python scripts/generate_sbom.py --output sbom.json
    python scripts/generate_sbom.py --input requirements.txt --output sbom.json
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_requirement(line: str) -> dict | None:
    """
    Parsea una línea de requirements.txt y retorna un componente SBOM básico.
    Soporta: package>=1.0, package==1.0, package[extra]>=1.0, etc.
    """
    line = line.strip()
    if not line or line.startswith(('#', '-', '--')):
        return None

    # Elimina extras y espacios
    line = re.sub(r'\s+', '', line)
    line = re.sub(r'\[.*?\]', '', line)

    # Separa nombre y especificadores
    match = re.match(r'^([A-Za-z0-9_.-]+)(.*)$', line)
    if not match:
        return None

    name = match.group(1)
    spec = match.group(2)

    version = None
    # Buscar la primera versión explícita
    for op, ver in re.findall(r'(==|>=|<=|~=|!=|>|<)=?([^,;\s]+)', spec):
        if op in ('==', '>=', '<=', '~='):
            version = ver
            break

    component = {
        "type": "library",
        "name": name,
        "purl": f"pkg:pypi/{_normalize(name)}@{version}" if version else f"pkg:pypi/{_normalize(name)}",
        "bom-ref": f"pkg:pypi/{_normalize(name)}@{version}" if version else f"pkg:pypi/{_normalize(name)}",
    }
    if version:
        component["version"] = version

    return component


def generate_sbom(requirements_path: Path, output_path: Path) -> None:
    components = []
    with requirements_path.open('r', encoding='utf-8') as f:
        for line in f:
            component = _parse_requirement(line)
            if component:
                components.append(component)

    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:prislab-sbom-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": [
                {
                    "vendor": "PRISLAB",
                    "name": "generate_sbom",
                    "version": "1.0.0",
                }
            ]
        },
        "components": components,
    }

    with output_path.open('w', encoding='utf-8') as f:
        json.dump(bom, f, indent=2)

    print(f"SBOM generado: {output_path} ({len(components)} componentes)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera SBOM CycloneDX desde requirements.txt")
    parser.add_argument("--input", default="requirements.txt", help="Ruta a requirements.txt")
    parser.add_argument("--output", default="sbom.json", help="Ruta de salida del SBOM")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: no se encontró {input_path}", file=sys.stderr)
        return 1

    generate_sbom(input_path, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
