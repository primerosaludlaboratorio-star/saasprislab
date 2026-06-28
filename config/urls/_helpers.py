from django.utils.module_loading import import_string


def lazy_view(dotted_path):
    """
    Retrasa imports pesados de vistas hasta que realmente se consume la ruta.
    Reduce el cold-start de requests que no usan IA, voz, CRM, nómina o chat.
    """
    def _wrapped_view(request, *args, **kwargs):
        return import_string(dotted_path)(request, *args, **kwargs)
    _wrapped_view.__name__ = dotted_path.rsplit('.', 1)[-1]
    return _wrapped_view
