import uuid
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
import hashlib
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# CHOICES COMPARTIDAS
# =============================================================================

SILO_ORIGEN_CHOICES = [
    ('LAB',        'Silo Laboratorio (Reactivos / Refacciones analíticas)'),
    ('CONSULTORIO','Silo Consultorio (Material médico / Enfermería)'),
    ('GENERAL',    'Silo Insumos Generales (Infraestructura / Admin)'),
]

TIPO_EQUIPO_CHOICES = [
    ('ANALIZADOR',     'Analizador Clínico'),
    ('CENTRIFUGA',     'Centrífuga'),
    ('MICROSCOPIO',    'Microscopio'),
    ('REFRIGERADOR',   'Refrigerador / Congelador'),
    ('AUTOCLAVE',      'Autoclave'),
    ('PC_MEDICA',      'PC / Tablet Médica'),
    ('INFRAESTRUCTURA','Infraestructura (A/C, UPS, Planta, Iluminación)'),
    ('MOBILIARIO',     'Mobiliario Clínico (Camilla, Mesa, Silla)'),
    ('OTRO',           'Otro'),
]

NIVEL_AUTORIZACION_CHOICES = [
    ('TODOS',         'Todos los usuarios'),
    ('QUIMICO',       'Químico / Enfermería'),
    ('TECNICO',       'Técnico de Mantenimiento'),
    ('QUIMICO_JEFE',  'Químico Jefe / Responsable Sanitario'),
    ('DIRECTOR',      'Director / Admin'),
]

TIPO_VALIDACION_PASO_CHOICES = [
    ('CHECKBOX', 'Confirmación (Sí/No)'),
    ('FOTO',     'Fotografía requerida'),
    ('NUMERO',   'Valor numérico'),
    ('TEXTO',    'Texto libre'),
]

TIPO_PROTOCOLO_CHOICES = [
    ('ARRANQUE',           'Protocolo de Arranque / Inicio de Turno'),
    ('APAGADO',            'Protocolo de Apagado / Fin de Turno'),
    ('LIMPIEZA_DIARIA',    'Limpieza Diaria'),
    ('MANTENIMIENTO_PREV', 'Mantenimiento Preventivo (Periódico)'),
    ('CALIBRACION',        'Calibración'),
    ('EMERGENCIA',         'Procedimiento de Emergencia'),
]

TIPO_NODO_CHOICES = [
    ('PREGUNTA',      'Pregunta diagnóstica'),
    ('ACCION',        'Acción / Procedimiento'),
    ('ESCALAMIENTO',  'Escalamiento'),
    ('SOLUCIONADO',   'Problema Resuelto'),
]

NIVEL_ESCALAMIENTO_CHOICES = [
    ('QUIMICO',          'Químico (resolución propia)'),
    ('TECNICO_INTERNO',  'Ingeniería Interna'),
    ('DIRECTOR',         'Dirección — requiere autorización'),
    ('PROVEEDOR',        'Proveedor Externo — requiere firma de Director'),
]

TIPO_COMPONENTE_CHOICES = [
    ('BOMBA',       'Bomba peristáltica'),
    ('FILTRO',      'Filtro (agua, aire, reactivo)'),
    ('LAMPARA',     'Lámpara / Fuente de luz'),
    ('INYECTOR',    'Inyector / Aguja / Sonda'),
    ('MANGUERA',    'Manguera / Tubing'),
    ('VALVULA',     'Válvula'),
    ('ELECTRODO',   'Electrodo'),
    ('TARJETA',     'Tarjeta electrónica'),
    ('REFACCION_GEN','Refacción General'),
    ('OTRO',        'Otro'),
]

ESTADO_TICKET_CHOICES = [
    ('ABIERTO',       'Abierto'),
    ('EN_PROCESO',    'En Proceso'),
    ('ESPERANDO',     'Esperando Refacción / Autorización'),
    ('RESUELTO',      'Resuelto'),
    ('ESCALADO',      'Escalado a Proveedor'),
    ('CERRADO',       'Cerrado'),
]


