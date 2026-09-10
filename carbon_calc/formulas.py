"""Safe evaluation of the plain-text formula entries stored in the workbook.

Every formula in the Carbon Accounting Grid is an arithmetic expression over the
nine model variables (x, y, a-g), e.g.::

    (x*7.792208+y*10.38961)*(a*0.95+b*0.7+c*0.45+d*0.02+e*0.011+f*0.045+g*0.012)/1000

``p``/``q`` are the train/road shares carried by the two transport rows. They are
stored as text rather than live Excel formulas, so the calculator parses
them itself. ``eval`` is never used: expressions are compiled to an AST once and
only numeric literals, the model variables and the four arithmetic operators are
accepted.
"""

from __future__ import annotations

import ast
import operator
from typing import Callable, Dict, Mapping

VARIABLES = ("x", "y", "a", "b", "c", "d", "e", "f", "g", "p", "q")

_BIN_OPS: Dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}


class FormulaError(ValueError):
    """Raised when a formula string contains something the model will not evaluate."""


def _check(node: ast.AST) -> None:
    """Recursively reject any node outside the allowed arithmetic subset."""
    if isinstance(node, ast.Expression):
        _check(node.body)
    elif isinstance(node, ast.BinOp):
        if type(node.op) not in _BIN_OPS:
            raise FormulaError(f"unsupported operator: {type(node.op).__name__}")
        _check(node.left)
        _check(node.right)
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, (ast.UAdd, ast.USub)):
            raise FormulaError(f"unsupported unary operator: {type(node.op).__name__}")
        _check(node.operand)
    elif isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)) or isinstance(node.value, bool):
            raise FormulaError(f"unsupported constant: {node.value!r}")
    elif isinstance(node, ast.Name):
        if node.id not in VARIABLES:
            raise FormulaError(f"unknown variable: {node.id}")
    else:
        raise FormulaError(f"unsupported expression element: {type(node).__name__}")


def compile_formula(expression: str) -> ast.Expression:
    """Parse ``expression`` and validate it against the allowed arithmetic subset."""
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:  # pragma: no cover - malformed workbook cell
        raise FormulaError(f"could not parse formula {expression!r}: {exc}") from exc
    _check(tree)
    return tree


def evaluate(tree: ast.Expression, variables: Mapping[str, float]) -> float:
    """Evaluate a compiled formula with the given variable bindings."""

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.BinOp):
            return _BIN_OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp):
            value = walk(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.Name):
            return float(variables[node.id])
        raise FormulaError(f"unsupported expression element: {type(node).__name__}")

    return walk(tree)
