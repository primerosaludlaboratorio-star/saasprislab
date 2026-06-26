"""
LIMS — Arquitectura de 4 Niveles
=================================
Nivel 1: Analito + ValorReferenciaAnalito  (ingeniería del analito)
Nivel 2: PerfilLims                        (agrupación técnica para reportes)
Nivel 3: PaqueteLims                       (oferta comercial)
Nivel 4: PrecioItem                        (gestión financiera independiente)
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db import models

from core.models import Empresa
from core.tenant import TenantModel
import logging

# ─────────────────────────────────────────────────────────────────────────────
# NIVEL 1-A : ANALITO  (el átomo del sistema)
# ─────────────────────────────────────────────────────────────────────────────
class Analito(TenantModel):
    TIPO_RESULTADO = [
        ('NUMERICO',  'Numérico'),
        ('TEXTO',     'Texto libre'),
        ('OPCIONES',  'Opciones predefinidas'),
        ('CALCULO',   'Calculado por fórmula'),
    ]

    empresa         = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='analitos_lims')

    # Referencia al Id_parametro del CSV legacy (para cruzar datos en importación)
    id_legacy       = models.IntegerField(unique=True, null=True, blank=True,
                                          verbose_name='ID legacy (CSV)')

    # Identificadores
    codigo          = models.CharField(max_length=50, unique=True, verbose_name='Código')
    codigo_rastreo_iso = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        verbose_name='Código rastreo ISO',
        help_text='Identificador estable para trazabilidad (único). Se rellena al migrar; obligatorio en nuevos registros vía admin/LIMS.',
    )
    abreviatura     = models.CharField(max_length=50, verbose_name='Abreviatura')
    nombre          = models.CharField(max_length=300, verbose_name='Descripción / Nombre')
    clave_hoja      = models.CharField(max_length=50, blank=True,
                                       verbose_name='Clave hoja de trabajo')

    # Clasificación
    departamento    = models.CharField(max_length=100, verbose_name='Departamento')
    tipo_muestra    = models.CharField(max_length=100, blank=True, verbose_name='Tipo de muestra')

    # Configuración técnica
    metodologia     = models.TextField(blank=True, verbose_name='Método analítico')
    tipo_resultado  = models.CharField(max_length=12, choices=TIPO_RESULTADO,
                                       default='NUMERICO', verbose_name='Tipo de resultado')
    unidades        = models.CharField(max_length=100, blank=True, verbose_name='Unidades')
    decimales       = models.PositiveSmallIntegerField(default=2,
                                                       verbose_name='Decimales en reporte')
    formula         = models.TextField(
        blank=True,
        verbose_name='Fórmula',
        help_text='Expresión desde Parametros.csv (Formula). Puede referenciar otros analitos o variables.',
    )
    es_calculado    = models.BooleanField(
        default=False,
        verbose_name='¿Calculado?',
        help_text=(
            'True si el resultado se obtiene por motor interno (no se espera valor del equipo). '
            'Útil para HL7/receptor: disparar cálculo en lugar de esperar OBX.'
        ),
    )
    opciones_texto  = models.TextField(blank=True,
                                       verbose_name='Opciones predefinidas (una por línea)')

    # Presentación
    imprime_en_negritas = models.BooleanField(default=False)
    imprimir_metodo     = models.BooleanField(default=False,
                                              verbose_name='Imprimir método en resultado')

    # Oferta individual (catálogo de ventas / listas de precio LIMS)
    es_vendible_individualmente = models.BooleanField(
        default=False,
        help_text=(
            'True → puede ofertarse solo en recepción y en lista de precios (ej. ácido úrico). '
            'False → solo como parte de perfiles/paquetes o procesamiento interno (ej. plaquetas).'
        ),
        verbose_name='¿Vendible individualmente?',
    )

    # Textos clínicos
    indicaciones    = models.TextField(blank=True, verbose_name='Indicaciones para el paciente')
    notas           = models.TextField(blank=True, verbose_name='Notas técnicas')

    # Metrología (CSV Parametros.Costo → Nivel 4 inicial)
    costo_lista     = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Costo lista (CSV)',
        help_text='Precio/costo de referencia importado desde Parametros.csv.',
    )

    # Control
    activo          = models.BooleanField(default=True)
    fecha_creacion  = models.DateTimeField(auto_now_add=True)
    fecha_actualiz  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Analito'
        verbose_name_plural = 'Analitos'
        ordering            = ['departamento', 'nombre']
        indexes             = [
            models.Index(fields=['departamento']),
            models.Index(fields=['es_vendible_individualmente']),
            models.Index(fields=['es_calculado']),
        ]

    def __str__(self):
        return f'{self.abreviatura} — {self.nombre}'


# ─────────────────────────────────────────────────────────────────────────────
# NIVEL 1-B : VALOR DE REFERENCIA  (Sentinel)
# ─────────────────────────────────────────────────────────────────────────────
class ValorReferenciaAnalito(models.Model):
    SEXO_CHOICES = [
        ('I', 'Indistinto'),
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]
    UNIDAD_EDAD_CHOICES = [
        ('DIAS', 'Días (0–364 días de vida)'),
        ('ANOS', 'Años (≥ 1 año)'),
    ]

    analito     = models.ForeignKey(
        Analito, on_delete=models.CASCADE,
        related_name='rangos', verbose_name='Analito',
    )
    sexo        = models.CharField(max_length=1, choices=SEXO_CHOICES,
                                   verbose_name='Sexo')
    unidad_edad = models.CharField(max_length=5, choices=UNIDAD_EDAD_CHOICES,
                                   verbose_name='Unidad de edad',
                                   help_text='DIAS: paciente < 1 año. ANOS: paciente ≥ 1 año.')
    edad_minima = models.PositiveIntegerField(verbose_name='Edad mínima')
    edad_maxima = models.PositiveIntegerField(verbose_name='Edad máxima')
    ref_minimo  = models.DecimalField(max_digits=14, decimal_places=4,
                                      null=True, blank=True,
                                      verbose_name='Referencia mínima')
    ref_maximo  = models.DecimalField(max_digits=14, decimal_places=4,
                                      null=True, blank=True,
                                      verbose_name='Referencia máxima')
    texto_referencia = models.CharField(max_length=200, blank=True,
                                        verbose_name='Referencia en texto')

    # ── Escudo clínico v1.14 (LIMS autónomo; sin Parametro legacy en este flujo) ──
    valor_critico_bajo = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
        verbose_name='Umbral crítico bajo',
        help_text='Valor estrictamente por debajo de este límite = pánico (si está definido).',
    )
    valor_critico_alto = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
        verbose_name='Umbral crítico alto',
        help_text='Valor estrictamente por encima de este límite = pánico (si está definido).',
    )
    es_critico_si_fuera_de_rango = models.BooleanField(
        default=False,
        verbose_name='Pánico si fuera de referencia',
        help_text='Si está activo, cualquier valor fuera de ref_mín/ref_máx se considera crítico.',
    )
    mensaje_critico = models.CharField(
        max_length=300, blank=True, default='',
        verbose_name='Mensaje crítico (push / notificación)',
        help_text='Texto para notificaciones; si va vacío se arma un mensaje estándar.',
    )

    class Meta:
        verbose_name        = 'Valor de referencia'
        verbose_name_plural = 'Valores de referencia'
        ordering            = ['analito', 'unidad_edad', 'edad_minima']
        indexes             = [
            models.Index(fields=['analito', 'unidad_edad', 'sexo']),
        ]

    def __str__(self):
        return (
            f'{self.analito.abreviatura} | {self.get_sexo_display()} | '
            f'{self.get_unidad_edad_display()} {self.edad_minima}–{self.edad_maxima}'
        )

    def evaluar_valor_numerico(self, valor_num) -> dict:
        """
        Clasifica un valor numérico contra referencia y umbrales LIMS (v1.14).
        Retorna: fuera_rango, es_critico, estado, mensaje_critico (texto para UI/push).
        """
        try:
            v = Decimal(str(valor_num).replace(',', '.'))
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en evaluar_valor_numerico (models.py)")
            return {
                'fuera_rango': False,
                'es_critico': False,
                'estado': 'NO_NUMERICO',
                'mensaje_critico': '',
            }

        ref_lo = self.ref_minimo
        ref_hi = self.ref_maximo
        fuera = False
        if ref_lo is not None and ref_hi is not None:
            fuera = v < ref_lo or v > ref_hi
        elif ref_lo is not None:
            fuera = v < ref_lo
        elif ref_hi is not None:
            fuera = v > ref_hi

        cb = self.valor_critico_bajo
        ca = self.valor_critico_alto
        critico = False
        estado = 'NORMAL'

        if cb is not None and v < cb:
            critico = True
            estado = 'CRITICO_BAJO'
        elif ca is not None and v > ca:
            critico = True
            estado = 'CRITICO_ALTO'
        elif self.es_critico_si_fuera_de_rango and fuera:
            critico = True
            estado = 'CRITICO_FUERA_REF'
        elif fuera:
            estado = 'ALTO' if ref_hi is not None and v > ref_hi else 'BAJO'

        base_msg = (self.mensaje_critico or '').strip()
        if not base_msg and critico:
            an = getattr(self.analito, 'nombre', '') or getattr(self.analito, 'abreviatura', '')
            base_msg = f'Valor crítico LIMS ({an}): {v}'
        return {
            'fuera_rango': fuera,
            'es_critico': critico,
            'estado': estado,
            'mensaje_critico': base_msg,
        }


# ─────────────────────────────────────────────────────────────────────────────
# NIVEL 2 : PERFIL  (contenedor técnico para reportes)
# ─────────────────────────────────────────────────────────────────────────────
class PerfilLims(TenantModel):
    # Clave estable desde Examenes.csv + Examenes_Perfil: "{Codigo}|{Abreviatura}" (unico por fila en Examenes)
    empresa      = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='perfiles_lims')
    id_perfil_legacy = models.CharField(
        max_length=220, unique=True, null=True, blank=True,
        verbose_name='ID perfil (legacy CSV)',
        help_text='Codigo|Abreviatura del examen (Examenes.csv / Examenes_Perfil).',
    )
    id_examen_legacy = models.IntegerField(
        null=True, blank=True, unique=True,
        verbose_name='Id_examen (CSV)',
    )
    costo_lista     = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Costo lista (Examenes.csv)',
    )
    nombre      = models.CharField(max_length=200, unique=True,
                                   verbose_name='Nombre del perfil')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    # M2M a Analito — sin filtro es_vendible_individualmente (todos los analitos son buscables)
    analitos    = models.ManyToManyField(
        Analito, blank=True,
        related_name='perfiles',
        verbose_name='Analitos incluidos',
        help_text='Buscador inteligente: cualquier analito del catálogo.',
    )
    activo      = models.BooleanField(default=True)
    fecha_creacion  = models.DateTimeField(auto_now_add=True)
    fecha_actualiz  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Perfil LIMS'
        verbose_name_plural = 'Perfiles LIMS'
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre

    def total_analitos(self):
        return self.analitos.count()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# NIVEL 3 : PAQUETE  (oferta comercial)
# ─────────────────────────────────────────────────────────────────────────────
class PaqueteLims(TenantModel):
    empresa        = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='paquetes_lims')
    id_paquete_legacy = models.CharField(
        max_length=200, unique=True, null=True, blank=True,
        verbose_name='Abreviatura paquete (CSV)',
    )
    costo_lista     = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Costo lista (Paquetes.csv)',
    )
    nombre        = models.CharField(max_length=200, unique=True,
                                     verbose_name='Nombre del paquete')
    descripcion   = models.TextField(blank=True, verbose_name='Descripción')
    # Composición: analitos individuales + perfiles completos
    analitos      = models.ManyToManyField(
        Analito, blank=True,
        related_name='paquetes',
        verbose_name='Analitos individuales incluidos',
    )
    perfiles      = models.ManyToManyField(
        PerfilLims, blank=True,
        related_name='paquetes',
        verbose_name='Perfiles incluidos',
    )
    venta_publico = models.BooleanField(
        default=True,
        verbose_name='¿Disponible para venta al público?',
    )
    activo        = models.BooleanField(default=True)
    fecha_creacion  = models.DateTimeField(auto_now_add=True)
    fecha_actualiz  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Paquete LIMS'
        verbose_name_plural = 'Paquetes LIMS'
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre

    def get_todos_analitos(self):
        """Retorna el queryset unificado de todos los analitos (directos + vía perfiles)."""
        ids_directos = self.analitos.values_list('id', flat=True)
        ids_perfiles = Analito.objects.filter(
            perfiles__paquetes=self
        ).values_list('id', flat=True)
        return Analito.objects.filter(
            id__in=set(list(ids_directos) + list(ids_perfiles))
        ).distinct()


# ─────────────────────────────────────────────────────────────────────────────
# NIVEL 4 : PRECIO ITEM  (gestión financiera independiente)
# ─────────────────────────────────────────────────────────────────────────────
class PrecioItem(TenantModel):
    TIPO = [
        ('A', 'Analito'),
        ('P', 'Perfil'),
        ('Q', 'Paquete'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='precios_lims')
    tipo    = models.CharField(max_length=1, choices=TIPO, verbose_name='Tipo de ítem')
    analito = models.OneToOneField(
        Analito, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='precio',
        verbose_name='Analito',
    )
    perfil  = models.OneToOneField(
        PerfilLims, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='precio',
        verbose_name='Perfil',
    )
    paquete = models.OneToOneField(
        PaqueteLims, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='precio',
        verbose_name='Paquete',
    )
    precio_venta = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Precio de venta',
    )
    activo  = models.BooleanField(default=True)
    fecha_actualiz = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Precio'
        verbose_name_plural = 'Precios'

    def __str__(self):
        return f'{self.get_nombre()} → ${self.precio_venta}'

    def get_nombre(self):
        if self.analito:
            return self.analito.nombre
        if self.perfil:
            return self.perfil.nombre
        if self.paquete:
            return self.paquete.nombre
        return '(sin asignar)'

    def aplicar_inflacion(self, factor: Decimal):
        """Aplica un multiplicador al precio_venta y guarda.
        Ejemplo: factor=Decimal('1.05') → +5 %.
        """
        self.precio_venta = (self.precio_venta * factor).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        self.save(update_fields=['precio_venta', 'fecha_actualiz'])

    def save(self, *args, **kwargs):
        if self.analito_id:
            self.empresa_id = self.analito.empresa_id
        elif self.perfil_id:
            self.empresa_id = self.perfil.empresa_id
        elif self.paquete_id:
            self.empresa_id = self.paquete.empresa_id
        super().save(*args, **kwargs)

    @classmethod
    def aplicar_inflacion_bulk(cls, ids: list, factor: Decimal):
        """Actualiza en bloque los precios de los PrecioItem con los IDs dados."""
        items = cls.objects.filter(id__in=ids)
        for item in items:
            item.precio_venta = (item.precio_venta * factor).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        cls.objects.bulk_update(items, ['precio_venta'])