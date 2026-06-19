from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import Empresa


class CursoAcademia(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="academia_cursos")
    slug = models.SlugField(max_length=120)
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, default="")
    autor_externo = models.CharField(max_length=255, blank=True, default="")
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = "Curso de academia"
        verbose_name_plural = "Cursos de academia"
        constraints = [
            models.UniqueConstraint(fields=["empresa", "slug"], name="uq_academia_curso_empresa_slug"),
        ]
        ordering = ["titulo"]

    def __str__(self) -> str:
        return self.titulo


class VideoAcademia(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="academia_videos")
    curso = models.ForeignKey(CursoAcademia, on_delete=models.CASCADE, related_name="videos")
    titulo = models.CharField(max_length=255)
    orden = models.PositiveIntegerField(default=0)
    bunny_video_id = models.CharField(max_length=64)
    duracion_segundos = models.PositiveIntegerField(null=True, blank=True)
    creado_en = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = "Video de academia"
        verbose_name_plural = "Videos de academia"
        ordering = ["orden", "id"]
        constraints = [
            models.UniqueConstraint(fields=["curso", "orden"], name="uq_academia_video_curso_orden"),
            models.UniqueConstraint(fields=["curso", "bunny_video_id"], name="uq_academia_video_curso_bunny"),
        ]

    def __str__(self) -> str:
        return f"{self.orden}. {self.titulo}"


class AccesoAcademia(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="academia_accesos")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="academia_accesos")
    curso = models.ForeignKey(CursoAcademia, on_delete=models.CASCADE, related_name="accesos")
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_expiracion = models.DateTimeField()
    activo = models.BooleanField(default=True)
    otorgado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="academia_accesos_otorgados",
    )
    creado_en = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = "Acceso a academia"
        verbose_name_plural = "Accesos a academia"
        constraints = [
            models.UniqueConstraint(fields=["empresa", "usuario", "curso"], name="uq_academia_acceso_empresa_usuario_curso"),
        ]
        ordering = ["-creado_en"]

    def __str__(self) -> str:
        return f"{self.usuario} -> {self.curso}"

    def vigente(self) -> bool:
        return self.activo and timezone.now() < self.fecha_expiracion


class SesionVisualizacion(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="academia_sesiones")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="academia_sesiones")
    video = models.ForeignKey(VideoAcademia, on_delete=models.CASCADE, related_name="sesiones")
    inicio = models.DateTimeField(default=timezone.now)
    ultima_actividad = models.DateTimeField(default=timezone.now)
    segundos_acumulados = models.PositiveIntegerField(default=0)
    finalizada = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Sesion de visualizacion"
        verbose_name_plural = "Sesiones de visualizacion"
        ordering = ["-ultima_actividad"]

    def __str__(self) -> str:
        return f"{self.usuario} / {self.video}"
