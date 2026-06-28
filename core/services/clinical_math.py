"""
Motor seguro de fórmulas clínicas LIMS (Punto 10 v7.5).
Sin eval(); solo AST restringido + funciones matemáticas permitidas.
Las variables se resuelven por código o abreviatura de analito (mayúsculas).
"""
from __future__ import annotations

import ast
import math
import operator
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, Optional, Set, Tuple

from django.utils import timezone


# ── Funciones permitidas en Call(función simple, un solo nombre) ────────────
_MATH_FUNCS: Dict[str, Callable[..., float]] = {
    'sqrt': math.sqrt,
    'log': math.log,
    'log10': math.log10,
    'log1p': math.log1p,
    'exp': math.exp,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'pow': pow,
    'min': min,
    'max': max,
    'abs': abs,
    'round': round,
}


_BINOPS: Dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY: Dict[type, Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class FormulaUnsafeError(ValueError):
    """Expresión rechazada por política de seguridad."""


def _reject_unsafe_nodes(tree: ast.AST) -> None:
    """Rechaza construcciones peligrosas; permite expresión numérica segura."""
    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
                ast.Attribute,
                ast.Subscript,
                ast.List,
                ast.Dict,
                ast.Set,
                ast.Tuple,
                ast.Lambda,
                ast.ListComp,
                ast.DictComp,
                ast.SetComp,
                ast.GeneratorExp,
                ast.Await,
                ast.Yield,
                ast.YieldFrom,
                ast.NamedExpr,
                ast.Match,
                ast.Compare,
                ast.BoolOp,
                ast.IfExp,
            ),
        ):
            raise FormulaUnsafeError(f'Nodo no permitido: {type(node).__name__}')
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise FormulaUnsafeError('Solo se permiten llamadas del tipo nombre(args), ej. sqrt(x)')
            if node.keywords:
                raise FormulaUnsafeError('No se permiten argumentos por nombre en fórmulas')
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float, type(None))):
                raise FormulaUnsafeError('Solo constantes numéricas')


def _function_names_in_formula(tree: ast.AST) -> Set[str]:
    out: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            out.add(node.func.id.upper())
    return out


def formula_dependency_names(formula: str) -> Set[str]:
    """Identificadores usados como variables (excluye nombres de función)."""
    formula = (formula or '').strip()
    if not formula:
        return set()
    tree = ast.parse(formula, mode='eval')
    funcs = _function_names_in_formula(tree)
    names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id.upper() in funcs:
                continue
            names.add(node.id.upper())
    return names


def _eval_ast(node: ast.AST, variables: Dict[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body, variables)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise FormulaUnsafeError('Constante no numérica')
    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _UNARY:
            raise FormulaUnsafeError('Operador unario no permitido')
        return _UNARY[type(node.op)](_eval_ast(node.operand, variables))
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _BINOPS:
            raise FormulaUnsafeError('Operador binario no permitido')
        left = _eval_ast(node.left, variables)
        right = _eval_ast(node.right, variables)
        if isinstance(node.op, ast.Div) and right == 0.0:
            raise ZeroDivisionError('División por cero')
        if isinstance(node.op, ast.Mod) and right == 0.0:
            raise ZeroDivisionError('Módulo con divisor cero')
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.Name):
        key = node.id.upper()
        if key not in variables:
            raise KeyError(key)
        return float(variables[key])
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise FormulaUnsafeError('Llamada inválida')
        fname = node.func.id
        if fname not in _MATH_FUNCS:
            raise FormulaUnsafeError(f'Función no permitida: {fname}')
        args = [_eval_ast(a, variables) for a in node.args]
        try:
            return float(_MATH_FUNCS[fname](*args))
        except (ValueError, OverflowError) as e:
            raise FormulaUnsafeError(str(e)) from e
    raise FormulaUnsafeError(f'Expresión no soportada: {type(node).__name__}')


def parse_numeric_text(raw: str) -> Tuple[Optional[float], Optional[str]]:
    """Convierte texto de captura a float; None si no es numérico."""
    s = (raw or '').strip().replace(',', '.')
    if not s:
        return None, None
    try:
        return float(s), None
    except ValueError:
        return None, 'no_numero'


def evaluate_formula(
    formula: str,
    variables: Dict[str, float],
) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Evalúa fórmula con variables ya resueltas (claves en MAYÚSCULAS).
    Retorna (Decimal redondeado o None, mensaje_error).
    """
    formula = (formula or '').strip()
    if not formula:
        return None, 'formula_vacia'

    try:
        tree = ast.parse(formula, mode='eval')
    except SyntaxError as e:
        return None, f'sintaxis: {e}'

    try:
        _reject_unsafe_nodes(tree)
        raw = _eval_ast(tree, variables)
    except ZeroDivisionError:
        return None, 'division_cero'
    except KeyError as e:
        return None, f'variable_faltante:{e}'
    except FormulaUnsafeError as e:
        return None, str(e)
    except (TypeError, ValueError) as e:
        return None, str(e)

    try:
        d = Decimal(str(raw))
    except InvalidOperation:
        return None, 'resultado_no_decimal'

    return d, None


def format_result_value(value: Decimal, decimales: int) -> str:
    if decimales < 0:
        decimales = 0
    if decimales > 8:
        decimales = 8
    quant = Decimal('1.' + '0' * decimales) if decimales else Decimal('1')
    return str(value.quantize(quant))


def build_variables_map_for_orden(
    analitos_en_orden,
    valores_por_analito_id: Dict[int, str],
    *,
    exclude_calculated_ids: Optional[Set[int]] = None,
) -> Dict[str, float]:
    """
    Construye mapa NOMBRE_MAYUS -> float a partir de analitos en la orden
    y valores por analito_id (típicamente desde ResultadoParametro o overrides).
    """
    exclude_calculated_ids = exclude_calculated_ids or set()
    out: Dict[str, float] = {}
    for a in analitos_en_orden:
        if a.id in exclude_calculated_ids:
            continue
        if a.es_calculado:
            continue
        raw = valores_por_analito_id.get(a.id, '') or ''
        num, err = parse_numeric_text(raw)
        if num is None or err:
            continue
        cod = (a.codigo or '').strip().upper()
        abr = (a.abreviatura or '').strip().upper()
        if cod:
            out[cod] = num
        if abr:
            out[abr] = num
    return out


def merge_override_variables(
    base: Dict[str, float],
    analitos_por_id: Dict[int, Any],
    overrides: Dict[int, str],
) -> Dict[str, float]:
    """Superpone valores enviados por el cliente (preview) sobre base."""
    merged = dict(base)
    for aid, texto in overrides.items():
        a = analitos_por_id.get(int(aid))
        if not a or a.es_calculado:
            continue
        num, err = parse_numeric_text(texto)
        if num is None:
            continue
        cod = (a.codigo or '').strip().upper()
        abr = (a.abreviatura or '').strip().upper()
        if cod:
            merged[cod] = num
        if abr:
            merged[abr] = num
    return merged


def sync_calculated_resultados_for_orden(
    orden,
    user,
    *,
    accion_validar: bool,
    valores_por_analito_id: Optional[Dict[int, str]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Calcula y persiste ResultadoParametro para analitos con es_calculado=True.
    No acepta valores manuales del cliente para esos analitos (se ignoran en la API).

    valores_por_analito_id: si se pasa, sustituye la lectura desde BD para esos IDs
    (útil en preview sin persistir). Si es None, lee ResultadoParametro actual en BD.
    """
    from core.models import DetalleOrden, ResultadoParametro

    detalles = (
        DetalleOrden.objects.filter(orden=orden, analito__isnull=False)
        .select_related('analito')
    )
    analitos_orden = [d.analito for d in detalles]
    calc_ids = {a.id for a in analitos_orden if a.es_calculado}

    rps = {
        rp.analito_id: rp
        for rp in ResultadoParametro.objects.filter(orden=orden)
    }

    if valores_por_analito_id is not None:
        valores: Dict[int, str] = {}
        for a in analitos_orden:
            if a.id in valores_por_analito_id:
                valores[a.id] = valores_por_analito_id[a.id] or ''
            else:
                rp = rps.get(a.id)
                valores[a.id] = (rp.valor if rp else '') or ''
    else:
        valores = {
            a.id: (rps[a.id].valor if a.id in rps else '') or ''
            for a in analitos_orden
        }

    vars_map = build_variables_map_for_orden(
        analitos_orden,
        valores,
        exclude_calculated_ids=calc_ids,
    )

    calculados = [a for a in analitos_orden if a.es_calculado and (a.formula or '').strip()]
    if not calculados:
        return {'ok': True, 'computados': {}, 'avisos': []}

    avisos: list = []
    computados: Dict[str, str] = {}
    pending = list(calculados)
    max_passes = len(calculados) + 4

    for _ in range(max_passes):
        if not pending:
            break
        still: list = []
        for a in pending:
            deps = formula_dependency_names(a.formula)
            missing = [d for d in deps if d not in vars_map]
            if missing:
                still.append(a)
                continue
            dec = a.decimales if a.decimales is not None else 2
            num, err = evaluate_formula(a.formula, vars_map)
            if err:
                avisos.append({'analito_id': a.id, 'codigo': a.codigo, 'error': err})
                still.append(a)
                continue
            if num is None:
                still.append(a)
                continue

            if a.tipo_resultado == 'NUMERICO' and num < 0:
                avisos.append({
                    'analito_id': a.id,
                    'codigo': a.codigo,
                    'error': 'resultado_negativo_no_permitido',
                })
                still.append(a)
                continue

            valor_txt = format_result_value(num, int(dec))
            computados[str(a.id)] = valor_txt

            cod = (a.codigo or '').strip().upper()
            abr = (a.abreviatura or '').strip().upper()
            try:
                fv = float(num)
                if cod:
                    vars_map[cod] = fv
                if abr:
                    vars_map[abr] = fv
            except (ValueError, OverflowError) as _e:
                avisos.append({
                    'analito_id': a.id,
                    'codigo': cod,
                    'error': f'No se pudo registrar {num!r} como float para fórmulas en cascada: {_e}',
                })

            if not dry_run:
                rp, _ = ResultadoParametro.objects.update_or_create(
                    orden=orden,
                    analito=a,
                    defaults={
                        'valor': valor_txt,
                        'capturado_por': user,
                        'fecha_captura': timezone.now(),
                        'metodo_captura': 'INTERFAZ',
                        'validado': accion_validar,
                        'aprobado_por_humano': bool(accion_validar),
                    },
                )
                if accion_validar:
                    rp.validado_por = user
                    rp.fecha_validacion = timezone.now()
                    rp.save(update_fields=['validado_por', 'fecha_validacion'])
        pending = still

    for a in pending:
        avisos.append({
            'analito_id': a.id,
            'codigo': a.codigo,
            'error': 'dependencias_insatisfechas_o_ciclo',
        })

    return {'ok': True, 'computados': computados, 'avisos': avisos}
