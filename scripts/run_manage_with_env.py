#!/usr/bin/env python3
"""
Ejecuta manage.py cargando un archivo .env estilo systemd sin usar `source`.

Uso:
  python scripts/run_manage_with_env.py migrate --noinput
  python scripts/run_manage_with_env.py sync_usuarios_auditoria --empresa-id 1 ...
  python scripts/run_manage_with_env.py shell -c "from django.conf import settings; print(settings.DATABASES)"
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT / ".env"


def load_env_file(env_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    if not env_path.exists():
        raise FileNotFoundError(f"No existe el archivo de entorno: {env_path}")

    for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def main(argv: list[str]) -> int:
    env_path = Path(os.environ.get("PRISLAB_ENV_FILE", str(DEFAULT_ENV_PATH))).expanduser()
    env = load_env_file(env_path)
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    if len(argv) < 2:
        print(
            "Uso: python scripts/run_manage_with_env.py <comando-manage.py> [args...]",
            file=sys.stderr,
        )
        return 2

    command = [sys.executable, str(ROOT / "manage.py"), *argv[1:]]
    completed = subprocess.run(command, cwd=str(ROOT), env=env)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
