from django.contrib import admin

from .models import AccesoAcademia, CursoAcademia, SesionVisualizacion, VideoAcademia


class VideoAcademiaInline(admin.TabularInline):
    model = VideoAcademia
    extra = 0
    fields = ("orden", "titulo", "bunny_video_id", "duracion_segundos")
    ordering = ("orden", "id")


class AccesoAcademiaInline(admin.TabularInline):
    model = AccesoAcademia
    extra = 0
    fields = ("usuario", "fecha_expiracion", "activo", "otorgado_por")
    autocomplete_fields = ("usuario", "otorgado_por")


@admin.register(CursoAcademia)
class CursoAcademiaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "empresa", "slug", "activo", "creado_en")
    list_filter = ("empresa", "activo")
    search_fields = ("titulo", "slug", "autor_externo")
    prepopulated_fields = {"slug": ("titulo",)}
    inlines = (VideoAcademiaInline, AccesoAcademiaInline)


@admin.register(VideoAcademia)
class VideoAcademiaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "empresa", "curso", "orden", "bunny_video_id", "duracion_segundos")
    list_filter = ("empresa", "curso")
    search_fields = ("titulo", "bunny_video_id")
    autocomplete_fields = ("curso",)


@admin.register(AccesoAcademia)
class AccesoAcademiaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "empresa", "curso", "fecha_expiracion", "activo", "otorgado_por")
    list_filter = ("empresa", "activo")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name", "curso__titulo")
    autocomplete_fields = ("usuario", "curso", "otorgado_por")


@admin.register(SesionVisualizacion)
class SesionVisualizacionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "empresa", "video", "segundos_acumulados", "inicio", "ultima_actividad", "finalizada")
    list_filter = ("empresa", "finalizada")
    search_fields = ("usuario__username", "video__titulo")
    autocomplete_fields = ("usuario", "video")
