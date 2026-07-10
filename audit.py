import os
import ast
from collections import defaultdict

def audit_directory(root_dir):
    app_stats = defaultdict(lambda: {'models': 0, 'views': 0, 'tests': 0, 'todos': 0, 'not_implemented': 0, 'empty_functions': 0, 'lines': 0})
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if 'venv' in dirpath or '__pycache__' in dirpath or '.git' in dirpath:
            continue
            
        app_name = os.path.relpath(dirpath, root_dir).split(os.sep)[0]
        if app_name == '.': continue
        
        for file in filenames:
            if not file.endswith('.py'): continue
            
            filepath = os.path.join(dirpath, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    app_stats[app_name]['lines'] += len(lines)
                    
                    app_stats[app_name]['todos'] += sum(1 for line in lines if 'TODO' in line or 'FIXME' in line)
                    app_stats[app_name]['not_implemented'] += content.count('NotImplementedError')
                    
                    if 'tests' in file or 'test_' in file:
                        app_stats[app_name]['tests'] += content.count('def test_')
                    elif 'models' in filepath:
                        app_stats[app_name]['models'] += content.count('class ')
                    elif 'views' in filepath:
                        app_stats[app_name]['views'] += content.count('def ') + content.count('class ')
                        
                    # Find empty functions (just pass)
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                                    app_stats[app_name]['empty_functions'] += 1
                    except SyntaxError:
                        pass
            except Exception as e:
                pass
                
    return app_stats

stats = audit_directory(r"C:\Users\jonil\.copilot\repos\saasprislab")
print(f"{'App':<20} | {'Lines':<8} | {'Models':<8} | {'Views':<8} | {'Tests':<8} | {'TODOs':<8} | {'NotImpl':<8} | {'EmptyFuncs':<8}")
print("-" * 90)
for app, data in sorted(stats.items()):
    if data['lines'] > 0:
        print(f"{app:<20} | {data['lines']:<8} | {data['models']:<8} | {data['views']:<8} | {data['tests']:<8} | {data['todos']:<8} | {data['not_implemented']:<8} | {data['empty_functions']:<8}")
