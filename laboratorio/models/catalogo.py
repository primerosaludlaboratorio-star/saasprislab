"""
MÓDULO DE LABORATORIO - Catálogo de estudios, categorías, insumos y perfiles.
"""
from django.db import models


class CategoriaExamen(models.Model):
    """
    Agrupa estudios de laboratorio (p. ej. Química Clínica, Hematología).
    """
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Categoría de Examen'
        verbose_name_plural = 'Categorías de Examen'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre


# ==============================================================================
# CEREBRO DE INVENTARIO: INSUMOS POR ESTUDIO (R107)
# ==============================================================================

class InsumoEstudio(models.Model):
    """
    Vincula un estudio de laboratorio con los insumos/materiales que consume.
    Al finalizar un estudio, el sistema descuenta automáticamente estos insumos.

    Ejemplo: Estudio "Glucosa" consume:
      - 1 Tubo rojo (Producto #42)
      - 1 Aguja vacutainer (Producto #15)
      - 0.5 mL Reactivo glucosa (Producto #88)
    """
    estudio = models.ForeignKey(
        'laboratorio.Estudio',
        on_delete=models.CASCADE,
        related_name='insumos_requeridos',
        verbose_name='Estudio',
    )
    producto = models.ForeignKey(
        'core.Producto',
        on_delete=models.PROTECT,
        related_name='uso_en_estudios',
        verbose_name='Insumo / Reactivo',
        help_text='Producto del inventario que se consume al realizar este estudio.',
    )
    cantidad = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=1,
        verbose_name='Cantidad por estudio',
        help_text='Unidades consumidas por cada vez que se realiza este estudio.',
    )
    es_critico = models.BooleanField(
        default=False,
        verbose_name='Insumo Crítico',
        help_text='Si es True, el sistema alerta cuando este insumo está por agotarse.',
    )

    class Meta:
        verbose_name = 'Insumo de Estudio'
        verbose_name_plural = 'Insumos de Estudios'
        unique_together = ('estudio', 'producto')
        ordering = ['estudio__nombre', 'producto__nombre']

    def __str__(self):
        return f'{self.estudio.nombre} → {self.producto.nombre} x{self.cantidad}'


# ==============================================================================
# PERFILES DE LABORATORIO
# ==============================================================================

class PerfilLaboratorio(models.Model):
    """
    Perfil de laboratorio que agrupa múltiples estudios individuales.
    Permite ofrecer paquetes a precio especial independiente de la suma de estudios.
    """
    nombre = models.CharField(
        max_length=200,
        verbose_name="Nombre del Perfil",
        help_text="Ej: 'Química Básica', 'Perfil Hepático', 'Perfil de Lípidos'"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción del Perfil",
        help_text="Descripción detallada de qué incluye el perfil"
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Precio del Perfil",
        help_text="Precio del paquete (puede ser diferente a la suma de estudios individuales)"
    )
    area_pertenencia = models.ForeignKey(
        CategoriaExamen,
        on_delete=models.PROTECT,
        related_name='perfiles',
        verbose_name="Área de Pertenencia",
        help_text="Área principal del perfil (ej: Química Clínica, Hematología)"
    )
    pruebas = models.ManyToManyField(
        'laboratorio.Estudio',
        related_name='perfiles',
        verbose_name="Pruebas Incluidas",
        help_text="Estudios individuales que incluye este perfil"
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Perfil Activo",
        help_text="Indica si el perfil está disponible para ordenar"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil de Laboratorio'
        verbose_name_plural = 'Perfiles de Laboratorio'
        ordering = ['area_pertenencia__nombre', 'nombre']

    def __str__(self) -> str:
        return f'{self.nombre} ({self.area_pertenencia.nombre})'

    def calcular_precio_total_individual(self):
        """Calcula el precio total si se cobraran las pruebas individuales."""
        return sum(prueba.precio_base for prueba in self.pruebas.all())

    def ahorro_porcentual(self):
        """Calcula el porcentaje de ahorro al comprar el perfil vs individual."""
        total_individual = self.calcular_precio_total_individual()
        if total_individual <= 0:
            return 0
        ahorro = total_individual - self.precio
        if ahorro <= 0:
            return 0
        return (ahorro / total_individual) * 100

    def agregar_estudios_a_orden(self, orden, precio_perfil=None):
        """
        Agrega todos los estudios del perfil a una orden.
        Si una prueba ya existe en la orden, no la duplica.
        
        Args:
            orden: Instancia de Orden
            precio_perfil: Precio total del perfil (opcional, usa self.precio si no se especifica)
            
        Returns:
            tuple: (estudios_agregados, estudios_duplicados, precio_distribuido)
        """
        from laboratorio.models import DetalleOrden

        if precio_perfil is None:
            precio_perfil = self.precio
        
        estudios_agregados = []
        estudios_duplicados = []
        estudios_perfil = list(self.pruebas.all())
        total_estudios = len(estudios_perfil)

        # Si no hay estudios, retornar
        if not total_estudios:
            return estudios_agregados, estudios_duplicados, 0

        # Precio por estudio (distribución proporcional del precio del perfil)
        precio_por_estudio = precio_perfil / total_estudios
        
        for estudio in estudios_perfil:
            # Verificar si el estudio ya existe en la orden (evitar duplicados)
            detalle_existente = DetalleOrden.objects.filter(orden=orden, estudio=estudio).first()
            
            if detalle_existente:
                # Ya existe, marcarlo pero no duplicarlo
                estudios_duplicados.append(estudio)
                # Actualizar el perfil de origen si no tiene uno
                if not detalle_existente.perfil:
                    detalle_existente.perfil = self
                    detalle_existente.save()
            else:
                # Crear nuevo detalle
                DetalleOrden.objects.create(
                    orden=orden,
                    estudio=estudio,
                    perfil=self,
                    precio_unitario=precio_por_estudio,
                    cantidad=1
                )
                estudios_agregados.append(estudio)
        
        return estudios_agregados, estudios_duplicados, precio_por_estudio
