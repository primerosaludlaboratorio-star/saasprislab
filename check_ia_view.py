import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from core.models import Usuario, Empresa
from core.views import ia_dashboard

def test_ia_view():
    print("Iniciando prueba de vista IA Dashboard...")

    try:
        eid = os.environ.get("PRISLAB_EMPRESA_ID")
        if not eid:
            print("[ERROR] Defina PRISLAB_EMPRESA_ID (pk de Empresa existente).")
            return
        try:
            empresa = Empresa.objects.get(pk=int(eid))
        except (ValueError, Empresa.DoesNotExist):
            print(f"[ERROR] Empresa id={eid!r} no válida.")
            return
            
        user = Usuario.objects.filter(empresa=empresa).first()
        if not user:
            user = Usuario.objects.create(username="testuser_ia", empresa=empresa)
            user.set_password("testpass")
            user.save()
            
        print(f"Usuario: {user.username}")
        
        factory = RequestFactory()
        request = factory.get('/ia/')
        request.user = user
        
        try:
            response = ia_dashboard(request)
            if response.status_code == 200:
                print("Vista IA Dashboard: OK (200)")
            else:
                print(f"Vista IA Dashboard: Fallo con status {response.status_code}")
        except Exception as e:
            print(f"Vista IA Dashboard: Excepcion - {str(e)}")

    except Exception as e:
        print(f"Error general: {str(e)}")

if __name__ == "__main__":
    test_ia_view()
