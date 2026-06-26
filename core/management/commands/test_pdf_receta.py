"""
Comando de prueba para generar PDF de receta.
Uso: python manage.py test_pdf_receta [receta_id]
"""
from django.core.management.base import BaseCommand
from core.models import Receta, Empresa, Paciente, Medico
from django.contrib.auth import get_user_model
from core.views.medico import generar_pdf_receta
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from datetime import date
import logging

class Command(BaseCommand):
    help = 'Prueba la generación de PDF de receta'

    def add_arguments(self, parser):
        parser.add_argument('receta_id', type=int, nargs='?', help='ID de la receta a probar')
        parser.add_argument('--create-test', action='store_true', help='Crear receta de prueba si no existe')
        parser.add_argument(
            '--empresa-id',
            type=int,
            default=None,
            help='Obligatorio con --create-test: tenant donde crear la receta de prueba.',
        )

    def handle(self, *args, **options):
        receta_id = options.get('receta_id')
        create_test = options.get('create_test', False)
        
        if receta_id:
            try:
                receta = Receta.objects.get(id=receta_id)
                self.stdout.write(self.style.SUCCESS(f'Receta encontrada: {receta.folio_receta}'))
            except Receta.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Receta {receta_id} no encontrada'))
                return
        else:
            # Buscar primera receta disponible
            receta = Receta.objects.first()
            if not receta:
                if create_test:
                    eid = options.get('empresa_id')
                    if not eid:
                        self.stdout.write(
                            self.style.ERROR(
                                'Con --create-test debe indicar --empresa-id=<pk> (sin empresa implícita).'
                            )
                        )
                        return
                    try:
                        empresa_ctx = Empresa.objects.get(pk=eid)
                    except Empresa.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'Empresa id={eid} no existe'))
                        return
                    receta = self.crear_receta_prueba(empresa_ctx)
                    self.stdout.write(self.style.SUCCESS(f'Receta de prueba creada: {receta.folio_receta}'))
                else:
                    self.stdout.write(self.style.ERROR('No hay recetas en el sistema. Use --create-test para crear una.'))
                    return
            else:
                self.stdout.write(self.style.SUCCESS(f'Usando receta existente: {receta.folio_receta}'))
        
        # Verificar datos de la receta
        self.stdout.write('\n=== DATOS DE LA RECETA ===')
        self.stdout.write(f'Folio: {receta.folio_receta}')
        self.stdout.write(f'Paciente: {receta.paciente.nombre_completo if receta.paciente else "N/A"}')
        self.stdout.write(f'Médico: {receta.medico_nombre_completo}')
        self.stdout.write(f'Cédula: {receta.medico_cedula}')
        self.stdout.write(f'Universidad: {receta.medico_universidad or "No especificada"}')
        self.stdout.write(f'Firma Digital: {"Sí" if receta.medico_firma_digital else "No"}')
        self.stdout.write(f'Indicaciones: {len(receta.indicaciones)} caracteres')
        
        # Simular request
        factory = RequestFactory()
        User = get_user_model()
        
        # Obtener usuario con empresa
        if receta.empresa:
            usuario = User.objects.filter(empresa=receta.empresa).first()
        else:
            usuario = User.objects.first()
            # Asignar empresa a la receta si no tiene
            if usuario and usuario.empresa:
                receta.empresa = usuario.empresa
                receta.save()
        
        if not usuario:
            self.stdout.write(self.style.ERROR('No hay usuarios en el sistema'))
            return
        
        request = factory.get(f'/medico/receta/{receta.id}/pdf/')
        request.user = usuario
        # Asegurar que el usuario tenga empresa
        if not request.user.empresa and receta.empresa:
            request.user.empresa = receta.empresa
            request.user.save()
        
        try:
            # Generar PDF
            self.stdout.write('\n=== GENERANDO PDF ===')
            response = generar_pdf_receta(request, receta.id)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS(f'✓ PDF generado exitosamente'))
                self.stdout.write(f'  Tamaño: {len(response.content)} bytes')
                self.stdout.write(f'  Content-Type: {response["Content-Type"]}')
                
                # Guardar PDF de prueba
                import os
                test_dir = 'test_pdfs'
                os.makedirs(test_dir, exist_ok=True)
                pdf_path = os.path.join(test_dir, f'receta_{receta.folio_receta}.pdf')
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                self.stdout.write(self.style.SUCCESS(f'✓ PDF guardado en: {pdf_path}'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ Error al generar PDF: Status {response.status_code}'))
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (test_pdf_receta.py)")
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())
    
    def crear_receta_prueba(self, empresa):
        """Crea una receta de prueba con todos los datos necesarios."""
        if not empresa:
            raise ValueError('empresa requerida')
        
        paciente = Paciente.objects.filter(empresa=empresa).first()
        if not paciente:
            paciente = Paciente.objects.create(
                nombre_completo='Juan Pérez García',
                fecha_nacimiento=date(1985, 5, 15),
                telefono='5551234567',
                empresa=empresa
            )
        
        medico = Medico.objects.first()
        if not medico:
            medico = Medico.objects.create(
                nombre_completo='Dra. María González',
                cedula_profesional='12345678',
                especialidad='Medicina General',
                empresa=empresa
            )
        
        from datetime import datetime
        from decimal import Decimal
        
        receta = Receta.objects.create(
            folio_receta=f'REC-TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            fecha_emision=date.today(),
            medico=medico,
            paciente=paciente,
            empresa=empresa,
            # Signos vitales
            presion_arterial_sistolica=120,
            presion_arterial_diastolica=80,
            frecuencia_cardiaca=72,
            temperatura=Decimal('36.5'),
            peso=Decimal('70.0'),
            talla=Decimal('1.70'),
            # Diagnóstico
            diagnostico_principal='Hipertensión arterial leve',
            diagnostico_secundario='Sobrepeso',
            # Indicaciones con formato estructurado
            indicaciones='''Paracetamol 500mg - 1 tableta - Cada 8 horas por 5 días
Ibuprofeno 400mg - 1 tableta - Cada 12 horas si hay dolor
Omeprazol 20mg - 1 cápsula - En ayunas por 7 días
Amoxicilina 500mg - 1 cápsula - Cada 12 horas por 7 días''',
            # Datos del médico
            medico_nombre_completo='Dra. María González López',
            medico_cedula='12345678',
            medico_especialidad='Medicina General',
            medico_universidad='Universidad Nacional Autónoma de México',
            cedula_vigente=True
        )
        
        # Calcular IMC
        receta.calcular_imc()
        receta.save()
        
        return receta