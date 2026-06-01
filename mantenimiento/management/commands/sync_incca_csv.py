"""Management Command: sync_incca_csv

Sincroniza resultados de equipos InCCA (Química Clínica) que exportan resultados
mediante archivos CSV en una carpeta (OUTPUTPATH).

MVP:
- Escanea configs habilitadas (InCCAInterfaceConfig).
- Lee archivos CSV nuevos en OUTPUTPATH.
- Calcula sha256 para idempotencia.
- Registra bitácora InCCAFileEvent.
- Guarda filas en InCCAOutputRowStaging (staging, aún sin aplicar a Orden/Estudio).

Nota:
Este comando NO escribe aún archivos de entrada (INPUTPATH). Solo ingesta OUTPUT.
"""

from __future__ import annotations

import csv
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


@dataclass
class _FileInfo:
    path: Path
    size: int | None
    mtime: datetime | None


def _safe_make_aware(dt: datetime | None) -> datetime | None:
    if not dt:
        return None
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, timezone.get_current_timezone())


def _read_bytes(p: Path, max_bytes: int | None = None) -> bytes:
    if max_bytes is None:
        return p.read_bytes()
    with p.open('rb') as f:
        return f.read(max_bytes)


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _collect_files(output_dir: Path, prefix: str | None, max_files: int) -> list[_FileInfo]:
    if not output_dir.exists() or not output_dir.is_dir():
        return []

    files: list[Path] = []
    for p in output_dir.iterdir():
        if not p.is_file():
            continue
        if prefix and not p.name.startswith(prefix):
            continue
        if p.suffix.lower() != '.csv':
            continue
        files.append(p)

    # Orden: mtime asc (más viejo primero)
    files.sort(key=lambda x: x.stat().st_mtime)
    files = files[: max_files if max_files > 0 else len(files)]

    out: list[_FileInfo] = []
    for p in files:
        st = p.stat()
        mtime = datetime.fromtimestamp(st.st_mtime)
        out.append(_FileInfo(path=p, size=int(st.st_size), mtime=mtime))
    return out


class Command(BaseCommand):
    help = "Ingesta resultados InCCA por CSV (OUTPUTPATH) y los guarda en staging."

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, default=None, help='Filtra por empresa_id')
        parser.add_argument('--expediente-id', type=int, default=None, help='Filtra por expediente (equipo)')
        parser.add_argument('--max-files', type=int, default=30, help='Máximo archivos a procesar por config (default: 30)')
        parser.add_argument('--dry-run', action='store_true', help='No escribe a DB; solo reporta.')

    def handle(self, *args, **opts):
        from mantenimiento.models import (
            InCCAInterfaceConfig,
            InCCAFileEvent,
            InCCAOutputRowStaging,
        )

        empresa_id = opts.get('empresa_id')
        expediente_id = opts.get('expediente_id')
        max_files = int(opts.get('max_files') or 30)
        dry_run = bool(opts.get('dry_run'))

        qs = InCCAInterfaceConfig.objects.filter(habilitado=True).select_related('empresa', 'expediente__equipo')
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        if expediente_id:
            qs = qs.filter(expediente_id=expediente_id)

        total_files = 0
        total_rows = 0
        total_errors = 0

        for cfg in qs:
            base = (cfg.output_path or '').strip() or 'output'
            # Si el path es relativo, se interpreta respecto al directorio de ejecución.
            output_dir = Path(os.path.expandvars(base))
            prefix = (cfg.output_prefix or '').strip() or None

            self.stdout.write(f"[InCCA] Equipo={cfg.expediente.equipo} output_dir={output_dir} prefix={prefix or '-'}")

            files = _collect_files(output_dir, prefix=prefix, max_files=max_files)
            if not files:
                if not dry_run:
                    InCCAInterfaceConfig.objects.filter(pk=cfg.pk).update(last_output_scan=timezone.now())
                continue

            for fi in files:
                total_files += 1
                p = fi.path
                try:
                    sha256 = _sha256_file(p)

                    # Idempotencia: si ya procesamos este hash del archivo, skip.
                    if InCCAFileEvent.objects.filter(config=cfg, direction='OUT', filename=p.name, sha256=sha256, status='PROCESADO').exists():
                        continue

                    preview_bytes = _read_bytes(p, max_bytes=4000)
                    preview_txt = preview_bytes.decode('utf-8', errors='replace')

                    if dry_run:
                        self.stdout.write(f"  - {p.name} sha256={sha256[:10]}... size={fi.size}")
                        continue

                    with transaction.atomic():
                        fe = InCCAFileEvent.objects.create(
                            empresa=cfg.empresa,
                            config=cfg,
                            direction='OUT',
                            filename=p.name,
                            full_path=str(p),
                            file_mtime=_safe_make_aware(fi.mtime),
                            file_size=fi.size,
                            sha256=sha256,
                            status='DETECTADO',
                            raw_preview=preview_txt,
                        )

                        # Parse CSV
                        raw = p.read_text(encoding='utf-8', errors='replace')
                        # Normalizar finales de línea
                        raw = raw.replace('\r\n', '\n').replace('\r', '\n')
                        lines = [ln for ln in raw.split('\n') if ln.strip()]

                        reader = csv.reader(lines, delimiter=',')
                        rows_created = 0
                        for idx, row in enumerate(reader):
                            if not row:
                                continue

                            # Por doc: Patients output tiene al menos:
                            # Process number, Order number, Method name, PID, ... , Report, Blank, #redilutions
                            proc = row[0].strip() if len(row) > 0 else ''
                            order = row[1].strip() if len(row) > 1 else ''
                            method = row[2].strip() if len(row) > 2 else ''
                            pid = row[3].strip() if len(row) > 3 else ''
                            report = row[11].strip() if len(row) > 11 else ''

                            InCCAOutputRowStaging.objects.create(
                                empresa=cfg.empresa,
                                file_event=fe,
                                row_index=idx,
                                process_number=proc,
                                order_number=order,
                                method_name=method,
                                pid=pid,
                                report=report,
                                raw_fields_json={
                                    'fields': row,
                                },
                            )
                            rows_created += 1

                        fe.status = 'PROCESADO'
                        fe.processed_at = timezone.now()
                        fe.save(update_fields=['status', 'processed_at'])

                        InCCAInterfaceConfig.objects.filter(pk=cfg.pk).update(last_output_scan=timezone.now())

                    total_rows += rows_created
                    self.stdout.write(f"  OK {p.name}: rows={rows_created}")

                except Exception as exc:
                    total_errors += 1
                    self.stderr.write(f"  ERROR {p.name}: {exc}")
                    if not dry_run:
                        try:
                            InCCAFileEvent.objects.create(
                                empresa=cfg.empresa,
                                config=cfg,
                                direction='OUT',
                                filename=p.name,
                                full_path=str(p),
                                file_mtime=_safe_make_aware(fi.mtime),
                                file_size=fi.size,
                                sha256='',
                                status='ERROR',
                                error=str(exc),
                            )
                        except Exception:
                            pass

        msg = f"sync_incca_csv: files={total_files} rows={total_rows} errors={total_errors}"
        self.stdout.write(self.style.SUCCESS(msg))
