from django.core.management.base import BaseCommand
from core.models import Empresa, Paciente
from core.tenant import set_current_empresa, clear_current_empresa

class Command(BaseCommand):
    help = 'Verifica que no hay fugas entre empresas'

    def handle(self, *args, **options):
        e1 = Empresa.objects.create(nombre='Aislada1')
        e2 = Empresa.objects.create(nombre='Aislada2')
        p1 = Paciente.objects.create(nombres='Paciente1', nombre_completo='Paciente1', empresa=e1)
        set_current_empresa(e2)
        try:
            leak = Paciente.objects.filter(id=p1.id).exists()
            if leak:
                self.stdout.write(self.style.ERROR('❌ FUGA DE DATOS: Paciente de empresa A visible en empresa B'))
                return
            self.stdout.write(self.style.SUCCESS('✅ Aislamiento multi-tenant funciona correctamente'))
        finally:
            clear_current_empresa()
