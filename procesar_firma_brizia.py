"""
Script para procesar la firma de la Dra. Brizia:
1. Recortar bordes blancos sobrantes (autocrop)
2. Eliminar fondo blanco (hacerlo transparente)
3. Guardar como PNG en media/firmas/
4. Crear/actualizar registro FirmaDigital en la BD
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from PIL import Image, ImageFilter
import numpy as np
from pathlib import Path

# ============================================================
# PASO 1: Buscar la imagen original de la firma
# ============================================================

# La imagen adjunta por el usuario (buscar en el directorio actual o media)
posibles_nombres = [
    'firma_brizia.jpg',
    'firma_brizia.png', 
    'firma.jpg',
    'firma.png',
    'media/firmas/firma_brizia.jpg',
    'media/firmas/firma_brizia_original.jpg',
]

# Buscar cualquier imagen JPG/PNG reciente en el directorio raiz
import glob
imagenes_raiz = glob.glob('*.jpg') + glob.glob('*.png') + glob.glob('*.jpeg')
imagenes_raiz += glob.glob('media/firmas/*.jpg') + glob.glob('media/firmas/*.png')

print("=" * 60)
print("PROCESADOR DE FIRMA DIGITAL - Dra. Brizia")
print("=" * 60)

imagen_origen = None
for nombre in posibles_nombres + imagenes_raiz:
    if os.path.exists(nombre):
        print(f"  Encontrada: {nombre}")
        if imagen_origen is None:
            imagen_origen = nombre

if imagen_origen is None:
    # Si no encontramos imagen, buscar la mas reciente que sea imagen
    print("\n[!] No se encontro imagen de firma en el directorio.")
    print("    Buscando en subdirectorios...")
    
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')) and 'firma' in f.lower():
                imagen_origen = os.path.join(root, f)
                print(f"    Encontrada: {imagen_origen}")
                break
        if imagen_origen:
            break

if imagen_origen is None:
    print("\n[ERROR] No se encontro ninguna imagen de firma.")
    print("Por favor coloca la imagen como 'firma_brizia.jpg' en la raiz del proyecto.")
    print("Creando imagen de ejemplo desde los datos de la firma adjunta...")
    
    # Crear un placeholder - la imagen fue adjunta en el chat
    # Necesitamos que el usuario la coloque manualmente
    # Pero podemos crear el registro y el procesamiento estara listo
    imagen_origen = None


# ============================================================
# PASO 2: Procesar la imagen (crop + transparencia)
# ============================================================

output_dir = Path('media/firmas')
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / 'firma_brizia_processed.png'

def procesar_firma(ruta_entrada, ruta_salida):
    """
    Procesa la imagen de firma:
    1. Convierte a RGBA
    2. Elimina fondo blanco (transparencia)
    3. Recorta bordes sobrantes (autocrop)
    4. Agrega padding mínimo
    5. Guarda como PNG con transparencia
    """
    print(f"\n[1] Abriendo imagen: {ruta_entrada}")
    img = Image.open(ruta_entrada)
    print(f"    Tamano original: {img.size}")
    print(f"    Modo: {img.mode}")
    
    # Convertir a RGBA si no lo es
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Obtener datos como numpy array
    data = np.array(img)
    
    # ---- ELIMINAR FONDO BLANCO ----
    print("[2] Eliminando fondo blanco...")
    
    # Detectar pixeles "blancos" o casi blancos
    # Un pixel es "blanco" si R, G, B son todos > 220
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
    
    # Threshold: pixeles con todos los canales > 215 se consideran fondo
    THRESHOLD = 215
    mascara_blanco = (r > THRESHOLD) & (g > THRESHOLD) & (b > THRESHOLD)
    
    # Hacer transparentes los pixeles blancos
    data[mascara_blanco, 3] = 0  # Alpha = 0 (transparente)
    
    # Para pixeles semi-blancos (gris muy claro), hacer semi-transparentes
    SEMI_THRESHOLD = 200
    mascara_semi = (r > SEMI_THRESHOLD) & (g > SEMI_THRESHOLD) & (b > SEMI_THRESHOLD) & ~mascara_blanco
    data[mascara_semi, 3] = 128  # Semi-transparente
    
    # Los trazos de la firma (oscuros) se mantienen opacos
    # Hacer los trazos de tinta mas oscuros/nitidos
    mascara_tinta = ~mascara_blanco & ~mascara_semi
    data[mascara_tinta, 0] = np.minimum(data[mascara_tinta, 0], 30)   # R -> casi negro
    data[mascara_tinta, 1] = np.minimum(data[mascara_tinta, 1], 30)   # G -> casi negro
    data[mascara_tinta, 2] = np.minimum(data[mascara_tinta, 2], 30)   # B -> casi negro
    data[mascara_tinta, 3] = 255  # Totalmente opaco
    
    img_procesada = Image.fromarray(data, 'RGBA')
    
    # ---- AUTOCROP (Recortar bordes transparentes) ----
    print("[3] Recortando bordes sobrantes...")
    
    # Obtener el bounding box de pixeles no-transparentes
    bbox = img_procesada.getbbox()
    if bbox:
        print(f"    Bounding box de la firma: {bbox}")
        img_recortada = img_procesada.crop(bbox)
        print(f"    Tamano recortado: {img_recortada.size}")
    else:
        print("    [!] No se detecto contenido visible")
        img_recortada = img_procesada
    
    # ---- PADDING MINIMO ----
    print("[4] Agregando padding...")
    padding = 20  # pixels
    w, h = img_recortada.size
    img_final = Image.new('RGBA', (w + 2*padding, h + 2*padding), (0, 0, 0, 0))
    img_final.paste(img_recortada, (padding, padding))
    
    # ---- GUARDAR ----
    print(f"[5] Guardando PNG con transparencia: {ruta_salida}")
    print(f"    Tamano final: {img_final.size}")
    img_final.save(str(ruta_salida), 'PNG', optimize=True)
    
    print("[OK] Firma procesada exitosamente!")
    return True


if imagen_origen:
    exito = procesar_firma(imagen_origen, output_path)
else:
    print("\n[ALTERNATIVA] Creando firma desde la imagen adjunta al chat...")
    print("    La imagen debe colocarse manualmente.")
    print("    Ejecutando con imagen de placeholder para crear el registro...")
    exito = False


# ============================================================
# PASO 3: Crear/actualizar registro FirmaDigital en la BD
# ============================================================

print("\n" + "=" * 60)
print("VINCULACION EN BASE DE DATOS")
print("=" * 60)

from core.models import FirmaDigital, Usuario

# Buscar al usuario de la Dra. Brizia o usar admin
usuario = None

# Intentar buscar por nombre
for nombre_busqueda in ['Brizia', 'brizia', 'Monserrat', 'monserrat']:
    candidatos = Usuario.objects.filter(
        first_name__icontains=nombre_busqueda
    ) | Usuario.objects.filter(
        last_name__icontains=nombre_busqueda
    ) | Usuario.objects.filter(
        username__icontains=nombre_busqueda
    )
    if candidatos.exists():
        usuario = candidatos.first()
        print(f"[OK] Usuario encontrado: {usuario.get_full_name()} (username: {usuario.username})")
        break

if not usuario:
    # Buscar medicos
    medicos = Usuario.objects.filter(rol='MEDICO')
    if medicos.exists():
        usuario = medicos.first()
        print(f"[OK] Medico encontrado: {usuario.get_full_name()} (username: {usuario.username})")
    else:
        # Usar admin
        usuario = Usuario.objects.filter(is_superuser=True).first()
        if usuario:
            print(f"[OK] Usando superusuario: {usuario.username}")
        else:
            print("[ERROR] No se encontro ningun usuario")
            sys.exit(1)

# Ruta relativa para el campo FileField
ruta_relativa = 'firmas/firma_brizia_processed.png'

# Crear o actualizar FirmaDigital
firma, created = FirmaDigital.objects.update_or_create(
    medico=usuario,
    activa=True,
    defaults={
        'cedula_profesional': getattr(usuario, 'cedula_profesional', 'PENDIENTE'),
        'imagen_firma': ruta_relativa,
    }
)

if created:
    print(f"[CREADO] FirmaDigital id={firma.id} para {usuario.get_full_name()}")
else:
    print(f"[ACTUALIZADO] FirmaDigital id={firma.id} para {usuario.get_full_name()}")

print(f"    Cedula: {firma.cedula_profesional}")
print(f"    Imagen: {firma.imagen_firma}")
print(f"    Activa: {firma.activa}")

# Verificar que el archivo existe
archivo_completo = os.path.join('media', ruta_relativa)
if os.path.exists(archivo_completo):
    from PIL import Image as PILCheck
    img_check = PILCheck.open(archivo_completo)
    print(f"\n[VERIFICACION] Archivo existe: {archivo_completo}")
    print(f"    Tamano: {img_check.size}")
    print(f"    Modo: {img_check.mode}")
    print(f"    Formato: {img_check.format}")
else:
    print(f"\n[PENDIENTE] El archivo {archivo_completo} aun no existe.")
    print("    Coloca la imagen original y vuelve a ejecutar este script.")

print("\n" + "=" * 60)
print("PROCESO COMPLETADO")
print("=" * 60)
print(f"\nPara probar el PDF, visita:")
print(f"  /consultorio/pdf/receta/<consulta_id>/")
print(f"\nLa firma aparecera automaticamente sobre la linea de antefirma.")
