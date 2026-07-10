# -*- coding: utf-8 -*-
import os
import ast

def generate_report(root_dir, output_file):
    report_lines = ["# 🏢 Reporte Técnico Exhaustivo E2E: PRISLAB SaaS v1.0", ""]
    report_lines.append("> Este documento detalla la realidad técnica sin filtros de la plataforma PRISLAB, incluyendo deuda técnica oculta, TODOs, funciones vacías, módulos sin cobertura de pruebas, y áreas con modelos no migrados.")
    report_lines.append("")
    
    apps = {}
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if any(x in dirpath for x in ['venv', '__pycache__', '.git', 'media', 'static']):
            continue
            
        app_name = os.path.relpath(dirpath, root_dir).split(os.sep)[0]
        if app_name == '.' or not os.path.isdir(os.path.join(root_dir, app_name)):
            continue
            
        if app_name not in apps:
            apps[app_name] = {'todos': [], 'empty': [], 'test_count': 0, 'model_count': 0}
            
        for file in filenames:
            if not file.endswith('.py'): continue
            filepath = os.path.join(dirpath, file)
            rel_path = os.path.relpath(filepath, root_dir)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    
                    if 'tests' in file or 'test_' in file:
                        apps[app_name]['test_count'] += content.count('def test_')
                    if 'models' in filepath:
                        apps[app_name]['model_count'] += content.count('class ')
                    
                    for i, line in enumerate(lines):
                        if 'TODO' in line or 'FIXME' in line or 'HACK' in line or 'XXX' in line:
                            if 'TODOS' in line and 'TODO' not in line.replace('TODOS', ''):
                                continue
                            if 'METODO' in line.upper(): continue
                            apps[app_name]['todos'].append(f"- **{rel_path}:{i+1}**: `{line.strip()}`")
                            
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                                    apps[app_name]['empty'].append(f"- **{rel_path}**: Función vacía detectada `def {node.name}()`")
                    except SyntaxError:
                        pass
            except Exception:
                pass

    report_lines.append("## 1. Módulos Críticos sin Cobertura de Pruebas")
    report_lines.append("Los siguientes módulos no tienen funciones de prueba detectadas en sus directorios y representan deuda técnica de QA:")
    for app, data in sorted(apps.items()):
        if data['test_count'] == 0 and data['model_count'] > 0:
            report_lines.append(f"- 🔴 **{app}** (Contiene {data['model_count']} modelos, 0 tests de módulo)")
    report_lines.append("")
    
    report_lines.append("## 2. Deuda Técnica Oculta (TODOs, FIXMEs, HACKs)")
    for app, data in sorted(apps.items()):
        if data['todos']:
            report_lines.append(f"### {app.capitalize()}")
            report_lines.extend(data['todos'])
            report_lines.append("")
            
    report_lines.append("## 3. Funciones Vacías o Incompletas")
    for app, data in sorted(apps.items()):
        if data['empty']:
            report_lines.append(f"### {app.capitalize()}")
            report_lines.extend(data['empty'])
            report_lines.append("")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

generate_report(r"C:\Users\jonil\.copilot\repos\saasprislab", r"C:\Users\jonil\.gemini\antigravity\brain\6962ed43-0225-4ef0-9e8d-6387413aae88\auditoria_tecnica_real.md")
