from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Empresa, Medico, FirmaDigital

User = get_user_model()


class Command(BaseCommand):
    help = 'Provisiona usuarios base del sistema y vincula perfil médico/firma de Brizia.'

    def obtener_empresa(self):
        empresa, created = Empresa.objects.get_or_create(
            nombre='PRISLAB S.A. de C.V.',
            defaults={
                'rfc': 'PRI260101XXX',
                'periodo_vigencia': '2024-2030',
                'color_primario': '#D9230F',
                'color_secundario': '#2B3A42',
            }
        )
        if created:
            self.stdout.write(f'[+] Empresa creada: {empresa.nombre}')
        return empresa

    def crear_admin(self, empresa):
        from os import environ
        username = 'admin'
        password = environ.get('PRISLAB_INIT_PASSWORD', environ.get('PRISLAB_INIT_ADMIN_PASSWORD', 'PrislabV5_2026'))
        email = 'admin@prislab.com'

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': 'Administrador',
                'last_name': 'Sistema',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
                'empresa': empresa,
                'rol': 'ADMIN',
                'puede_usar_ia': True,
                'nivel_ia': 'IA_MASTER',
            }
        )

        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.empresa = empresa
        user.rol = 'ADMIN'
        user.puede_usar_ia = True
        user.nivel_ia = 'IA_MASTER'
        user.save()

        action = 'CREADO' if created else 'ACTUALIZADO'
        self.stdout.write(f'[OK] Admin {action}: {username}')
        return user

    def crear_dra_brizia(self, empresa):
        from os import environ
        username = 'brizia.nolasco'
        password = environ.get('PRISLAB_INIT_PASSWORD_BRIZIA', environ.get('PRISLAB_INIT_PASSWORD', 'Prislab2026!'))
        cedula = '11852035'

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': 'Brizia Itzel',
                'last_name': 'Nolasco Polito',
                'email': 'brizia@prislab.mx',
                'empresa': empresa,
                'rol': 'MEDICO',
                'puede_usar_ia': True,
                'nivel_ia': 'IA_TECNICA',
                'departamento': 'Consultorio Médico',
                'cedula_interna': cedula,
                'is_staff': False,
                'is_active': True,
            }
        )

        if created:
            user.set_password(password)
        user.first_name = 'Brizia Itzel'
        user.last_name = 'Nolasco Polito'
        user.empresa = empresa
        user.rol = 'MEDICO'
        user.puede_usar_ia = True
        user.nivel_ia = 'IA_TECNICA'
        user.departamento = 'Consultorio Médico'
        user.cedula_interna = cedula
        user.is_active = True
        user.save()
        self.stdout.write(f'[OK] Dra. Brizia {"CREADA" if created else "ACTUALIZADA"}: {username}')

        medico, m_created = Medico.objects.get_or_create(
            cedula_profesional=cedula,
            defaults={
                'nombre_completo': 'Brizia Itzel Nolasco Polito',
                'especialidad': 'Médico Cirujano General',
            }
        )
        if not m_created:
            medico.nombre_completo = 'Brizia Itzel Nolasco Polito'
            medico.especialidad = 'Médico Cirujano General'
            medico.save()
        self.stdout.write(f'[OK] Perfil Médico {"CREADO" if m_created else "ACTUALIZADO"}: {medico.nombre_completo}')

        firma_path = 'firmas/firma_brizia_processed.png'
        firmas_existentes = FirmaDigital.objects.filter(medico=user, cedula_profesional=cedula)
        if firmas_existentes.count() > 1:
            firma_principal = firmas_existentes.order_by('-fecha_registro').first()
            firmas_existentes.exclude(id=firma_principal.id).delete()
            firma_principal.imagen_firma = firma_path
            firma_principal.activa = True
            firma_principal.save()
            self.stdout.write(f'[OK] Firma Digital LIMPIADA para cédula {cedula}')
        elif firmas_existentes.count() == 1:
            firma = firmas_existentes.first()
            firma.imagen_firma = firma_path
            firma.activa = True
            firma.save()
            self.stdout.write(f'[OK] Firma Digital ACTUALIZADA para cédula {cedula}')
        else:
            FirmaDigital.objects.create(
                medico=user,
                cedula_profesional=cedula,
                imagen_firma=firma_path,
                activa=True,
            )
            self.stdout.write(f'[OK] Firma Digital CREADA para cédula {cedula}')
        return user

    def handle(self, *args, **options):
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write('  PRISLAB V5 — Provisionamiento de Usuarios')
        self.stdout.write('=' * 70)
        empresa = self.obtener_empresa()
        self.crear_admin(empresa)
        self.crear_dra_brizia(empresa)
        self.stdout.write('=' * 70)
        self.stdout.write(f'  Empresa: {empresa.nombre}')
        self.stdout.write(f'  Total usuarios: {User.objects.count()}')
        self.stdout.write('=' * 70)
