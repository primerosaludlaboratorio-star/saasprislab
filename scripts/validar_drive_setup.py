import json
import os
from pathlib import Path
import logging


def _load_json(path_str: str) -> dict:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de credenciales: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    folder_id = (
        os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "").strip()
        or os.environ.get("DRIVE_FOLDER_ID", "").strip()
    )

    print("=== VALIDACION GOOGLE DRIVE / PRISLAB ===")

    if not creds_path:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS no esta configurada.")
        return 1

    try:
        data = _load_json(creds_path)
    except Exception as exc:
        logging.getLogger(__name__).exception("Error inesperado en main (validar_drive_setup.py)")
        print(f"ERROR: no se pudo leer el JSON de credenciales: {exc}")
        return 1

    sa_type = data.get("type")
    sa_email = data.get("client_email")
    project_id = data.get("project_id")
    has_key = bool(data.get("private_key"))

    print(f"Credenciales: {creds_path}")
    print(f"Tipo: {sa_type}")
    print(f"Proyecto: {project_id}")
    print(f"Service Account: {sa_email}")
    print(f"Llave privada presente: {'SI' if has_key else 'NO'}")
    print(f"Folder ID configurado: {folder_id or '[VACIO]'}")

    if sa_type != "service_account":
        print("ERROR: el archivo no es una cuenta de servicio valida.")
        return 1

    if not sa_email:
        print("ERROR: el JSON no contiene client_email.")
        return 1

    if not has_key:
        print("ERROR: el JSON no contiene private_key.")
        return 1

    if not folder_id:
        print("WARN: falta GOOGLE_DRIVE_FOLDER_ID o DRIVE_FOLDER_ID.")

    print()
    print("Checklist operativo:")
    print("1. Compartir la carpeta o Shared Drive exactamente con ese Service Account.")
    print("2. Si la carpeta vive en My Drive, la escritura puede fallar con 403 storageQuotaExceeded.")
    print("3. La opcion recomendada para PRISLAB es usar Shared Drive.")
    print("4. Reintentar subida real solo despues de confirmar el share y el folder ID correcto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())