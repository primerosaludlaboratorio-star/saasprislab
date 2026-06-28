from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from core.models import Empresa
from academia.models import CursoAcademia, VideoAcademia
from academia.services import bunny_stream


def _sort_key(path: Path):
    stem = path.stem
    prefix = ""
    for ch in stem:
        if ch.isdigit():
            prefix += ch
        else:
            break
    return (int(prefix) if prefix else 999999, stem.lower())


class Command(BaseCommand):
    help = "Sincroniza una carpeta de videos con Bunny Stream y crea el curso/videos en PRISLAB."

    def add_arguments(self, parser):
        parser.add_argument("carpeta", type=str, help="Ruta a la carpeta local con los videos")
        parser.add_argument("--empresa-id", type=int, required=True, help="Empresa destino")
        parser.add_argument("--curso-titulo", type=str, required=True, help="Titulo del diplomado/curso")
        parser.add_argument("--curso-slug", type=str, default="", help="Slug del curso (opcional)")
        parser.add_argument("--autor", type=str, default="", help="Autor externo o instructor")
        parser.add_argument("--descripcion", type=str, default="", help="Descripcion del curso")
        parser.add_argument("--json-salida", type=str, default="", help="Archivo JSON con el mapeo final")
        parser.add_argument("--no-subir", action="store_true", help="Solo crea/actualiza la estructura local sin subir a Bunny")

    def handle(self, *args, **options):
        carpeta = Path(options["carpeta"]).expanduser().resolve()
        if not carpeta.exists() or not carpeta.is_dir():
            raise CommandError(f"La carpeta no existe o no es valida: {carpeta}")

        empresa = Empresa.objects.filter(id=options["empresa_id"]).first()
        if not empresa:
            raise CommandError(f"No existe la empresa con id={options['empresa_id']}")

        curso_slug = options["curso_slug"] or slugify(options["curso_titulo"])
        curso, _created = CursoAcademia.objects.get_or_create(
            empresa=empresa,
            slug=curso_slug,
            defaults={
                "titulo": options["curso_titulo"],
                "descripcion": options["descripcion"],
                "autor_externo": options["autor"],
                "activo": True,
            },
        )
        curso.titulo = options["curso_titulo"]
        curso.descripcion = options["descripcion"]
        curso.autor_externo = options["autor"]
        curso.activo = True
        curso.save()

        extensiones = {".mp4", ".mkv", ".mov", ".webm", ".m4v"}
        archivos = [p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in extensiones]
        archivos.sort(key=_sort_key)

        if not archivos:
            raise CommandError("No se encontraron videos compatibles en la carpeta")

        mapeo = []
        for idx, archivo in enumerate(archivos, start=1):
            titulo = archivo.stem.replace("_", " ").replace("-", " ").strip()
            bunny_id = ""
            if not options["no_subir"]:
                self.stdout.write(f"Subiendo {archivo.name} ...")
                bunny_id = bunny_stream.crear_video(titulo)
                bunny_stream.subir_archivo_video(bunny_id, archivo)
                self.stdout.write(self.style.SUCCESS(f"  Bunny ID: {bunny_id}"))
            else:
                bunny_id = f"pendiente-{idx}"

            video, _ = VideoAcademia.objects.update_or_create(
                empresa=empresa,
                curso=curso,
                orden=idx,
                defaults={
                    "titulo": titulo,
                    "bunny_video_id": bunny_id,
                },
            )
            mapeo.append(
                {
                    "orden": idx,
                    "archivo": archivo.name,
                    "titulo": video.titulo,
                    "bunny_video_id": video.bunny_video_id,
                    "video_id": video.id,
                }
            )

        if options["json_salida"]:
            salida = Path(options["json_salida"]).expanduser().resolve()
        else:
            salida = carpeta / "mapeo_videos_bunny.json"
        salida.write_text(json.dumps(mapeo, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Curso sincronizado: {curso.titulo}"))
        self.stdout.write(self.style.SUCCESS(f"Videos procesados: {len(mapeo)}"))
        self.stdout.write(self.style.SUCCESS(f"Mapa guardado en: {salida}"))
