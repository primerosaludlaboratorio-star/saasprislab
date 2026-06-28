from __future__ import annotations

import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.models import Paciente


@login_required
def lista_contactos(request):
    """Lista de contactos/leads."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    busqueda = request.GET.get('q', '').strip()
    segmento = request.GET.get('segmento', 'todos')

    contactos = Paciente.objects.filter(empresa=empresa)

    if busqueda:
        contactos = contactos.filter(nombre_completo__icontains=busqueda)

    contactos = contactos.order_by('nombre_completo')[:200]

    return render(request, "marketing/contactos/lista.html", {
        "contactos": contactos,
        "empresa": empresa,
        "busqueda": busqueda,
        "segmento": segmento,
    })


@login_required
def importar_contactos(request):
    """Importar contactos desde CSV."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']

        if not archivo.name.endswith(('.csv', '.xlsx', '.xls')):
            messages.error(request, 'Solo se permiten archivos CSV o Excel.')
            return redirect('marketing:importar_contactos')

        try:
            decoded_file = archivo.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            contactos_importados = 0
            for row in reader:
                nombre = row.get('nombre', '').strip()
                telefono = row.get('telefono', '').strip()
                email = row.get('email', '').strip()

                if nombre:
                    Paciente.objects.get_or_create(
                        empresa=empresa,
                        nombre_completo=nombre,
                        defaults={
                            'telefono': telefono,
                            'email': email,
                        }
                    )
                    contactos_importados += 1

            messages.success(request, f'{contactos_importados} contacto(s) importado(s) exitosamente.')
            return redirect('marketing:lista_contactos')

        except (UnicodeDecodeError, csv.Error) as e:
            messages.error(request, f'Error al importar: {str(e)}')
            return redirect('marketing:importar_contactos')

    return render(request, "marketing/contactos/importar.html", {
        "empresa": empresa,
    })
