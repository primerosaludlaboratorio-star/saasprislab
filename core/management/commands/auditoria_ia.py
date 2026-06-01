"""
Auditoría de Configuración de IA - PRISLAB v5
Verifica que todas las funciones de IA estén migradas a Google Gemini.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import re
from pathlib import Path
from colorama import init, Fore, Style

init(autoreset=True)


class Command(BaseCommand):
    help = 'Ejecuta una auditoría completa de la configuración de IA'

    def handle(self, *args, **options):
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}AUDITORÍA DE CONFIGURACIÓN DE IA - PRISLAB v5")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")

        resultados = []
        errores = []

        # 1. Verificar variables de entorno
        self.stdout.write(f"{Fore.YELLOW}[1] Verificando variables de entorno...\n")
        
        google_key = getattr(settings, 'GOOGLE_API_KEY', '')
        openai_key = getattr(settings, 'OPENAI_API_KEY', '')
        
        if google_key:
            resultados.append({
                'categoria': 'Variables de Entorno',
                'item': 'GOOGLE_API_KEY',
                'estado': f"{Fore.GREEN}[OK]",
                'detalle': 'Configurada correctamente'
            })
        else:
            errores.append('GOOGLE_API_KEY no configurada')
            resultados.append({
                'categoria': 'Variables de Entorno',
                'item': 'GOOGLE_API_KEY',
                'estado': f"{Fore.RED}[ERROR]",
                'detalle': 'NO configurada - Requerida para todas las funciones de IA'
            })
        
        if openai_key:
            resultados.append({
                'categoria': 'Variables de Entorno',
                'item': 'OPENAI_API_KEY',
                'estado': f"{Fore.YELLOW}[ADVERTENCIA]",
                'detalle': 'Aún configurada pero ya no se usa (puede eliminarse)'
            })
        else:
            resultados.append({
                'categoria': 'Variables de Entorno',
                'item': 'OPENAI_API_KEY',
                'estado': f"{Fore.GREEN}[OK]",
                'detalle': 'No configurada (correcto, ya no se necesita)'
            })

        # 2. Verificar dependencias en requirements.txt
        self.stdout.write(f"{Fore.YELLOW}[2] Verificando dependencias...\n")
        
        requirements_path = Path(settings.BASE_DIR) / 'requirements.txt'
        if requirements_path.exists():
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements_content = f.read()
            
            # Verificar google-generativeai
            if 'google-generativeai' in requirements_content:
                version_match = re.search(r'google-generativeai==([\d.]+)', requirements_content)
                version = version_match.group(1) if version_match else 'N/A'
                resultados.append({
                    'categoria': 'Dependencias',
                    'item': 'google-generativeai',
                    'estado': f"{Fore.GREEN}[OK]",
                    'detalle': f'Instalada (versión: {version})'
                })
            else:
                errores.append('google-generativeai no encontrada en requirements.txt')
                resultados.append({
                    'categoria': 'Dependencias',
                    'item': 'google-generativeai',
                    'estado': f"{Fore.RED}[ERROR]",
                    'detalle': 'NO encontrada en requirements.txt'
                })
            
            # Verificar openai (debe estar comentada o eliminada)
            if re.search(r'^openai==', requirements_content, re.MULTILINE):
                resultados.append({
                    'categoria': 'Dependencias',
                    'item': 'openai',
                    'estado': f"{Fore.YELLOW}[ADVERTENCIA]",
                    'detalle': 'Aún presente en requirements.txt (debería estar comentada o eliminada)'
                })
            elif '# openai' in requirements_content or '#openai' in requirements_content:
                resultados.append({
                    'categoria': 'Dependencias',
                    'item': 'openai',
                    'estado': f"{Fore.GREEN}[OK]",
                    'detalle': 'Comentada correctamente'
                })
            else:
                resultados.append({
                    'categoria': 'Dependencias',
                    'item': 'openai',
                    'estado': f"{Fore.GREEN}[OK]",
                    'detalle': 'No presente (correcto)'
                })
        else:
            errores.append('requirements.txt no encontrado')
            resultados.append({
                'categoria': 'Dependencias',
                'item': 'requirements.txt',
                'estado': f"{Fore.RED}[ERROR]",
                'detalle': 'Archivo no encontrado'
            })

        # 3. Verificar imports en código Python
        self.stdout.write(f"{Fore.YELLOW}[3] Verificando imports en código...\n")
        
        base_dir = Path(settings.BASE_DIR)
        python_files = list(base_dir.rglob('*.py'))
        python_files = [f for f in python_files if 'venv' not in str(f) and 'migrations' not in str(f)]
        
        archivos_con_openai = []
        archivos_con_google = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Buscar imports de OpenAI
                if re.search(r'from\s+openai\s+import|import\s+openai', content):
                    archivos_con_openai.append(str(py_file.relative_to(base_dir)))
                
                # Buscar imports de Google
                if re.search(r'import\s+google\.generativeai|from\s+google\s+import\s+generativeai', content):
                    archivos_con_google.append(str(py_file.relative_to(base_dir)))
            except Exception:
                pass
        
        if archivos_con_openai:
            errores.append(f'Se encontraron {len(archivos_con_openai)} archivos con imports de OpenAI')
            resultados.append({
                'categoria': 'Imports',
                'item': 'Archivos con OpenAI',
                'estado': f"{Fore.RED}[ERROR]",
                'detalle': f'{len(archivos_con_openai)} archivo(s): {", ".join(archivos_con_openai[:3])}...'
            })
        else:
            resultados.append({
                'categoria': 'Imports',
                'item': 'Archivos con OpenAI',
                'estado': f"{Fore.GREEN}[OK]",
                'detalle': 'No se encontraron imports de OpenAI'
            })
        
        if archivos_con_google:
            resultados.append({
                'categoria': 'Imports',
                'item': 'Archivos con Google Gemini',
                'estado': f"{Fore.GREEN}[OK]",
                'detalle': f'{len(archivos_con_google)} archivo(s) usando Google: {", ".join(archivos_con_google)}'
            })
        else:
            errores.append('No se encontraron archivos usando Google Gemini')
            resultados.append({
                'categoria': 'Imports',
                'item': 'Archivos con Google Gemini',
                'estado': f"{Fore.RED}[ERROR]",
                'detalle': 'No se encontraron imports de Google'
            })

        # 4. Verificar implementaciones específicas
        self.stdout.write(f"{Fore.YELLOW}[4] Verificando implementaciones específicas...\n")
        
        archivos_verificar = [
            ('core/views/coach.py', 'Coach Ejecutivo'),
            ('core/utils/rag_engine.py', 'RAG Engine'),
            ('core/ai_brain.py', 'AI Brain (PRIS/LIA)'),
            ('core/views/laboratorio.py', 'OCR Recetas'),
        ]
        
        for archivo, nombre in archivos_verificar:
            archivo_path = base_dir / archivo
            if archivo_path.exists():
                with open(archivo_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                tiene_openai = bool(re.search(r'from\s+openai|import\s+openai|OpenAI\(\)', content))
                tiene_google = bool(re.search(r'google\.generativeai|genai\.|GenerativeModel', content))
                
                if tiene_openai:
                    errores.append(f'{nombre} ({archivo}) aún tiene referencias a OpenAI')
                    resultados.append({
                        'categoria': 'Implementaciones',
                        'item': nombre,
                        'estado': f"{Fore.RED}[ERROR]",
                        'detalle': f'Aún tiene referencias a OpenAI'
                    })
                elif tiene_google:
                    resultados.append({
                        'categoria': 'Implementaciones',
                        'item': nombre,
                        'estado': f"{Fore.GREEN}[OK]",
                        'detalle': 'Migrado a Google Gemini'
                    })
                else:
                    resultados.append({
                        'categoria': 'Implementaciones',
                        'item': nombre,
                        'estado': f"{Fore.YELLOW}[ADVERTENCIA]",
                        'detalle': 'No se detectó ni OpenAI ni Google (verificar manualmente)'
                    })
            else:
                errores.append(f'{nombre} ({archivo}) no encontrado')
                resultados.append({
                    'categoria': 'Implementaciones',
                    'item': nombre,
                    'estado': f"{Fore.RED}[ERROR]",
                    'detalle': 'Archivo no encontrado'
                })

        # 5. Verificar uso de modelos
        self.stdout.write(f"{Fore.YELLOW}[5] Verificando modelos utilizados...\n")
        
        modelos_esperados = {
            'gemini-1.5-flash': 'Generación de texto (Coach, RAG, AI Brain)',
            'text-embedding-004': 'Embeddings para RAG',
            'models/text-embedding-004': 'Embeddings (formato alternativo)',
        }
        
        for modelo, descripcion in modelos_esperados.items():
            encontrado = False
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        if modelo in f.read():
                            encontrado = True
                            break
                except Exception:
                    pass
            
            if encontrado:
                resultados.append({
                    'categoria': 'Modelos',
                    'item': modelo,
                    'estado': f"{Fore.GREEN}[OK]",
                    'detalle': descripcion
                })
            else:
                resultados.append({
                    'categoria': 'Modelos',
                    'item': modelo,
                    'estado': f"{Fore.YELLOW}[ADVERTENCIA]",
                    'detalle': f'No encontrado en código: {descripcion}'
                })

        # Resumen
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}RESUMEN DE AUDITORÍA")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")
        
        ok_count = sum(1 for r in resultados if '[OK]' in r['estado'])
        warning_count = sum(1 for r in resultados if '[ADVERTENCIA]' in r['estado'])
        error_count = sum(1 for r in resultados if '[ERROR]' in r['estado'])
        total = len(resultados)
        
        self.stdout.write(f"{Fore.GREEN}[OK]: {ok_count}/{total}")
        self.stdout.write(f"{Fore.YELLOW}[ADVERTENCIA]: {warning_count}/{total}")
        self.stdout.write(f"{Fore.RED}[ERROR]: {error_count}/{total}\n")
        
        # Tabla de resultados
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}")
        self.stdout.write(f"{Fore.CYAN}TABLA DE RESULTADOS")
        self.stdout.write(f"{Fore.CYAN}{'='*80}\n")
        
        self.stdout.write(f"{'CATEGORÍA':<20} {'ITEM':<30} {'ESTADO':<15} {'DETALLE'}")
        self.stdout.write(f"{'-'*80}")
        
        for r in resultados:
            estado_limpio = r['estado'].replace(Fore.GREEN, '').replace(Fore.YELLOW, '').replace(Fore.RED, '').replace(Style.RESET_ALL, '')
            self.stdout.write(f"{r['categoria']:<20} {r['item']:<30} {estado_limpio:<15} {r['detalle']}")
        
        # Errores detallados
        if errores:
            self.stdout.write(f"\n{Fore.RED}{'='*80}")
            self.stdout.write(f"{Fore.RED}ERRORES ENCONTRADOS")
            self.stdout.write(f"{Fore.RED}{'='*80}\n")
            
            for i, error in enumerate(errores, 1):
                self.stdout.write(f"{Fore.RED}[{i}] {error}")
        
        self.stdout.write(f"\n{Fore.CYAN}{'='*80}\n")
        
        if error_count == 0:
            self.stdout.write(f"{Fore.GREEN}[OK] ¡Excelente! La migración a Google Gemini está completa.")
        else:
            self.stdout.write(f"{Fore.RED}[!] ATENCION: Se encontraron {error_count} error(es) que requieren corrección.")
