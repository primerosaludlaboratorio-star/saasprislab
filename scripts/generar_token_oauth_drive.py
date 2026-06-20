r"""
Genera token.json OAuth 2.0 para Google Drive usando un client secret
de tipo "Desktop App".

Uso recomendado:

  .\.venv\Scripts\python.exe scripts\generar_token_oauth_drive.py ^
      --credentials "C:\Users\jonil\Downloads\credentials.json" ^
      --token "C:\Users\jonil\Downloads\token.json"

Abre el navegador local para autorizar con la cuenta Google del usuario.
No subir el token generado al repositorio.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera token OAuth 2.0 para Google Drive (PRISLAB)."
    )
    parser.add_argument(
        "--credentials",
        required=True,
        help="Ruta al credentials.json OAuth Desktop descargado desde Google Cloud.",
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Ruta destino para guardar token.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    credentials_path = Path(args.credentials).expanduser().resolve()
    token_path = Path(args.token).expanduser().resolve()

    if not credentials_path.exists():
        print(f"ERROR: no existe credentials.json en {credentials_path}")
        return 1

    token_path.parent.mkdir(parents=True, exist_ok=True)

    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_path),
        SCOPES,
    )
    creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"TOKEN_OK: {token_path}")
    print("No subas este archivo a GitHub ni lo pegues en chats.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
