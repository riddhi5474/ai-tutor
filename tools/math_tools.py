"""
Math utility tools for Streamlit AI Tutor.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

import matplotlib.pyplot as plt
import numpy as np
import pint
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


ureg = pint.UnitRegistry()
_TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def _normalize_expression(expr: str) -> str:
    """
    Make casual math input more parser-friendly.
    Examples: sinx -> sin(x), cos t -> cos(t), lnx -> log(x)
    """
    text = (expr or "").strip()
    if not text:
        return text
    text = re.sub(r"\bln\s*\(", "log(", text)
    text = re.sub(r"\bln\s+([A-Za-z0-9_]+)\b", r"log(\1)", text)
    text = re.sub(r"\bln([A-Za-z])\b", r"log(\1)", text)
    text = re.sub(
        r"\b(sin|cos|tan|sec|csc|cot|sqrt|log)\s+([A-Za-z0-9_]+)\b",
        r"\1(\2)",
        text,
    )
    text = re.sub(
        r"\b(sin|cos|tan|sec|csc|cot|sqrt|log)([A-Za-z])\b",
        r"\1(\2)",
        text,
    )
    return text


def _friendly_sympify(expr: str) -> sp.Expr:
    return parse_expr(_normalize_expression(expr), transformations=_TRANSFORMS)


@dataclass
class AlgebraResult:
    operation: str
    input_expr: str
    output: str


def _parse_equation(expr: str) -> sp.Expr:
    if "=" in expr:
        left, right = expr.split("=", 1)
        return sp.Eq(_friendly_sympify(left.strip()), _friendly_sympify(right.strip()))
    return _friendly_sympify(expr)


def run_computer_algebra(
    expression: str,
    operation: str,
    variable: str = "x",
    at_value: float | None = None,
) -> AlgebraResult:
    x = sp.Symbol(variable)
    op = operation.strip().lower()

    if op == "solve":
        eq = _parse_equation(expression)
        solved = sp.solve(eq, x)
        return AlgebraResult(op, expression, str(solved))

    expr = _friendly_sympify(expression)
    if op == "simplify":
        out = sp.simplify(expr)
    elif op == "expand":
        out = sp.expand(expr)
    elif op == "factor":
        out = sp.factor(expr)
    elif op == "differentiate":
        out = sp.diff(expr, x)
    elif op == "integrate":
        out = sp.integrate(expr, x)
    elif op == "limit":
        if at_value is None:
            raise ValueError("Limit requires a numeric point.")
        out = sp.limit(expr, x, at_value)
    else:
        raise ValueError(f"Unsupported operation: {operation}")

    return AlgebraResult(op, expression, str(out))


def build_plot_figure(
    expression: str,
    variable: str = "x",
    x_min: float = -10.0,
    x_max: float = 10.0,
    points: int = 400,
):
    if x_max <= x_min:
        raise ValueError("x_max must be greater than x_min.")
    points = max(50, min(points, 5000))

    x = sp.Symbol(variable)
    expr = _friendly_sympify(expression)
    fn = sp.lambdify(x, expr, modules=["numpy"])
    xs = np.linspace(x_min, x_max, points)
    ys = np.asarray(fn(xs), dtype=float)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(xs, ys, color="#5b8dee", linewidth=2)
    ax.axhline(0, color="#64748b", linewidth=0.8)
    ax.axvline(0, color="#64748b", linewidth=0.8)
    ax.set_title(f"y = {sp.sstr(expr)}")
    ax.set_xlabel(variable)
    ax.set_ylabel("y")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    return fig


def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    q = value * ureg(from_unit)
    converted = q.to(to_unit)
    return f"{value:g} {from_unit} = {converted.magnitude:g} {to_unit}"
