from django.contrib import admin
 
try:
    from .models import (
        Analito, ValorReferenciaAnalito,
        PerfilLims, PaqueteLims, PrecioItem,
    )
except ImportError:  # pragma: no cover
    Analito = None
    ValorReferenciaAnalito = None
    PerfilLims = None
    PaqueteLims = None
    PrecioItem = None


if ValorReferenciaAnalito is not None:
    class ValorReferenciaInline(admin.TabularInline):
        model = ValorReferenciaAnalito
        extra = 0
        fields = (
            'sexo', 'unidad_edad', 'edad_minima', 'edad_maxima',
            'ref_minimo', 'ref_maximo',
            'valor_critico_bajo', 'valor_critico_alto',
            'es_critico_si_fuera_de_rango', 'mensaje_critico',
        )


if ValorReferenciaAnalito is not None:
    @admin.register(ValorReferenciaAnalito)
    class ValorReferenciaAnalitoAdmin(admin.ModelAdmin):
        list_display = (
            'analito', 'sexo', 'unidad_edad', 'edad_minima', 'edad_maxima',
            'ref_minimo', 'ref_maximo', 'valor_critico_bajo', 'valor_critico_alto',
            'es_critico_si_fuera_de_rango',
        )
        list_filter = ('unidad_edad', 'sexo', 'es_critico_si_fuera_de_rango')
        search_fields = ('analito__nombre', 'analito__codigo', 'mensaje_critico')
        autocomplete_fields = ('analito',)


if Analito is not None:
    @admin.register(Analito)
    class AnalitoAdmin(admin.ModelAdmin):
        list_display = (
            'codigo', 'abreviatura', 'nombre', 'departamento',
            'es_vendible_individualmente', 'es_calculado', 'costo_lista', 'activo',
        )
        list_filter = ('departamento', 'es_vendible_individualmente', 'es_calculado', 'activo', 'tipo_resultado')
        search_fields = ('codigo', 'abreviatura', 'nombre')
        inlines = [ValorReferenciaInline] if ValorReferenciaAnalito is not None else []


if PerfilLims is not None:
    @admin.register(PerfilLims)
    class PerfilLimsAdmin(admin.ModelAdmin):
        list_display = ('nombre', 'id_perfil_legacy', 'activo')
        filter_horizontal = ('analitos',)
        search_fields = ('nombre', 'id_perfil_legacy')


if PaqueteLims is not None:
    @admin.register(PaqueteLims)
    class PaqueteLimsAdmin(admin.ModelAdmin):
        list_display = ('nombre', 'id_paquete_legacy', 'costo_lista', 'venta_publico', 'activo')
        filter_horizontal = ('analitos', 'perfiles')
        search_fields = ('nombre',)


if PrecioItem is not None:
    @admin.register(PrecioItem)
    class PrecioItemAdmin(admin.ModelAdmin):
        list_display = ('get_nombre', 'tipo', 'precio_venta', 'activo')
        list_filter = ('tipo', 'activo')
 
        def get_nombre(self, obj):
            if obj.analito:
                return obj.analito.nombre
            if obj.perfil:
                return obj.perfil.nombre
            if obj.paquete:
                return obj.paquete.nombre
            return '—'
        get_nombre.short_description = 'Nombre'
