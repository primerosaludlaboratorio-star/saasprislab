"""
core/templatetags/tenant_tags.py
═══════════════════════════════════════════════════════════════════════════════
PRISLAB V6.0 — PILAR 2: AMPUTACIÓN VISUAL DE MÓDULOS

Template tags para controlar la visibilidad de menús, botones y secciones
enteras según los módulos contratados por la empresa en sesión.

Si el módulo está apagado en ConfiguracionModulos, el HTML desaparece.
El CSS/JS del módulo ni siquiera se carga → menor superficie de ataque.

DISPONIBLE EN: cualquier template que incluya {% load tenant_tags %}

TAGS DISPONIBLES:

  1. {% if_modulo 'laboratorio' %} ... {% endif_modulo %}
     Bloque condicional completo.

  2. {% modulo_activo 'farmacia' as activo %}
     Variable booleana para lógica compleja en templates.

  3. {{ empresa_color_primario }} — Variable de contexto inyectada
  4. {{ empresa_css }}           — CSS personalizado del tenant

CONTEXT PROCESSOR:
  Registrar en settings.py → TEMPLATES → OPTIONS → context_processors:
    'core.context_processors.tenant_context'
═══════════════════════════════════════════════════════════════════════════════
"""
from django import template

register = template.Library()


# ─── TAG DE BLOQUE CONDICIONAL ────────────────────────────────────────────────

class IfModuloNode(template.Node):
    """Nodo para el tag de bloque {% if_modulo %} ... {% endif_modulo %}"""

    def __init__(self, modulo, nodelist):
        self.modulo   = modulo
        self.nodelist = nodelist

    def render(self, context):
        request = context.get('request')
        if request is None:
            return self.nodelist.render(context)

        # Superusuario siempre ve todo
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_superuser', False):
            return self.nodelist.render(context)

        modulos_activos = getattr(request, 'modulos_activos', {})
        if modulos_activos.get(self.modulo, True):
            return self.nodelist.render(context)

        return ''  # Amputar el bloque


@register.tag('if_modulo')
def tag_if_modulo(parser, token):
    """
    Renderiza el bloque solo si el módulo está activo para la empresa.

    Uso:
        {% load tenant_tags %}

        {% if_modulo 'laboratorio' %}
          <a href="{% url 'laboratorio_dashboard' %}">Laboratorio</a>
        {% endif_modulo %}
    """
    try:
        _, modulo = token.split_contents()
        modulo = modulo.strip('"\'')
    except ValueError:
        raise template.TemplateSyntaxError(
            "{% if_modulo %} requiere un argumento: el nombre del módulo"
        )

    nodelist = parser.parse(('endif_modulo',))
    parser.delete_first_token()
    return IfModuloNode(modulo, nodelist)


# ─── TAG DE VARIABLE BOOLEANA ────────────────────────────────────────────────

@register.simple_tag(takes_context=True)
def modulo_activo(context, modulo: str) -> bool:
    """
    Retorna True si el módulo está activo para la empresa en sesión.

    Uso:
        {% load tenant_tags %}
        {% modulo_activo 'farmacia' as tiene_farmacia %}
        {% if tiene_farmacia %}
          ... mostrar elementos de farmacia ...
        {% endif %}
    """
    request = context.get('request')
    if request is None:
        return True

    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_superuser', False):
        return True

    modulos_activos = getattr(request, 'modulos_activos', {})
    return modulos_activos.get(modulo, True)


# ─── FILTRO DE VISIBILIDAD ───────────────────────────────────────────────────

@register.filter(name='requiere_modulo')
def requiere_modulo(value, modulo: str):
    """
    Filtro para usar en condicionales simples.

    Uso:
        {% if request|requiere_modulo:'ia' %}
    """
    if not hasattr(value, 'modulos_activos'):
        return True
    return getattr(value, 'modulos_activos', {}).get(modulo, True)


# ─── TAG DE IDENTIDAD VISUAL ─────────────────────────────────────────────────

@register.simple_tag(takes_context=True)
def empresa_css_vars(context) -> str:
    """
    Genera variables CSS inline para la identidad visual del tenant.

    Uso en base.html:
        <style>
          {% empresa_css_vars %}
        </style>

    Produce:
        :root {
          --color-primario: #003366;
          --color-secundario: #FFD700;
          --color-fondo: #F8F9FA;
        }
    """
    request = context.get('request')
    empresa = getattr(request, 'empresa_actual', None) if request else None

    if not empresa:
        return ':root { --color-primario: #003366; --color-secundario: #FFD700; --color-fondo: #F8F9FA; }'

    primario   = getattr(empresa, 'color_primario',   '#003366') or '#003366'
    secundario = getattr(empresa, 'color_secundario', '#FFD700') or '#FFD700'
    fondo      = getattr(empresa, 'color_fondo',      '#F8F9FA') or '#F8F9FA'

    return (
        f':root {{\n'
        f'  --color-primario: {primario};\n'
        f'  --color-secundario: {secundario};\n'
        f'  --color-fondo: {fondo};\n'
        f'}}'
    )


@register.simple_tag(takes_context=True)
def empresa_css_custom(context) -> str:
    """
    Inyecta el CSS personalizado del tenant (campo css_personalizado de Empresa).

    Uso en base.html:
        <style>{% empresa_css_custom %}</style>
    """
    request = context.get('request')
    empresa = getattr(request, 'empresa_actual', None) if request else None
    if not empresa:
        return ''
    return getattr(empresa, 'css_personalizado', '') or ''


@register.simple_tag(takes_context=True)
def empresa_logo_url(context) -> str:
    """
    Retorna la URL del logo del tenant (o vacío si no tiene).

    Uso:
        <img src="{% empresa_logo_url %}" alt="Logo">
    """
    request = context.get('request')
    empresa = getattr(request, 'empresa_actual', None) if request else None
    if not empresa:
        return ''
    logo = getattr(empresa, 'logo', None)
    if logo and hasattr(logo, 'url'):
        try:
            return logo.url
        except Exception:
            pass
    return ''


@register.simple_tag(takes_context=True)
def empresa_nombre(context) -> str:
    """Retorna el nombre del tenant en sesión."""
    request = context.get('request')
    empresa = getattr(request, 'empresa_actual', None) if request else None
    return getattr(empresa, 'nombre', 'PRISLAB') if empresa else 'PRISLAB'
