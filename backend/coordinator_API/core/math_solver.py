"""
core/math_solver.py - deterministic arithmetic, percentage, and unit
conversion for questions the local Duke Brain has no real ability to get
right (proven live: "what's 15% of 240?" -> hallucinated 45 instead of
36). Solved exactly instead of asking the model to guess - the same
approach core/grounding.py uses for date/time/weather.

Expression evaluation uses Python's `ast` module with a strict node-type
whitelist (numbers and +-*/%** only) rather than eval() - it can never
execute arbitrary code, only compute arithmetic.
"""
import ast
import operator
import re
from typing import Optional

_PERCENT_OF = re.compile(
    r"^\s*(?:what'?s?|what\s+is)?\s*(-?\d+(?:\.\d+)?)\s*%\s*of\s*(-?\d+(?:\.\d+)?)\s*\??\s*$",
    re.IGNORECASE,
)

_OP_WORDS = {
    "plus": "+",
    "add": "+",
    "minus": "-",
    "subtract": "-",
    "times": "*",
    "multiplied by": "*",
    "multiply": "*",
    "divided by": "/",
    "divide": "/",
}

_ARITHMETIC = re.compile(
    r"^\s*(?:what'?s?|what\s+is)?\s*(-?\d+(?:\.\d+)?)\s*"
    r"(\+|-|\*|x|×|/|plus|minus|times|multiplied by|multiply|divided by|divide)\s*"
    r"(-?\d+(?:\.\d+)?)\s*\??\s*$",
    re.IGNORECASE,
)

_PERCENT_CHANGE = re.compile(
    r"(increase|decrease|raise|reduce)\s+(-?\d+(?:\.\d+)?)\s+by\s+(-?\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)

_WHAT_PERCENT = re.compile(
    r"(-?\d+(?:\.\d+)?)\s+is\s+what\s+percent(?:age)?\s+of\s+(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Only tried when a math "cue" phrase or parentheses/exponent is present -
# a bare digit-and-dash string with no cue (e.g. a phone number or a date)
# should never be silently reinterpreted as arithmetic.
_MATH_CUE = re.compile(
    r"^\s*(?:what'?s|what\s+is|calculate|compute|solve)\b|[()^]|\*\*",
    re.IGNORECASE,
)
_EXPR_CHARS = re.compile(r"^[\d\s+\-*/().%^]+$")
_STRIP_CUE = re.compile(
    r"^\s*(?:what'?s|what\s+is)\s+(?:the\s+(?:result|answer|value)\s+of\s+)?|^\s*(?:calculate|compute|solve)\s*:?\s*",
    re.IGNORECASE,
)

_UNIT_ALIASES = {
    "f": "f", "°f": "f", "fahrenheit": "f", "degrees fahrenheit": "f",
    "c": "c", "°c": "c", "celsius": "c", "degrees celsius": "c",
    "mi": "mi", "mile": "mi", "miles": "mi",
    "km": "km", "kilometer": "km", "kilometers": "km", "kilometre": "km", "kilometres": "km",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
}

_UNIT_PATTERN = "|".join(sorted(_UNIT_ALIASES.keys(), key=len, reverse=True)).replace(".", r"\.")

_CONVERSION = re.compile(
    rf"(-?\d+(?:\.\d+)?)\s*(°?\s*(?:{_UNIT_PATTERN}))\s+(?:to|in)\s+(°?\s*(?:{_UNIT_PATTERN}))\b",
    re.IGNORECASE,
)


def _fmt(n: float) -> str:
    n = round(n, 4)
    return str(int(n)) if n == int(n) else str(n)


_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_ALLOWED_UNARYOPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval_node(node):
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        if isinstance(node.op, (ast.Div, ast.Mod)) and right == 0:
            raise ZeroDivisionError()
        return _ALLOWED_BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_safe_eval_node(node.operand))
    raise ValueError("disallowed expression")


def _try_expression(text: str) -> Optional[str]:
    if not _MATH_CUE.search(text):
        return None
    candidate = _STRIP_CUE.sub("", text.strip()).strip().rstrip("?.! ")
    candidate = candidate.replace("^", "**").replace("×", "*")
    if not candidate or not _EXPR_CHARS.match(candidate.replace("**", "^")):
        return None
    # Require at least one operator - a bare number alone isn't a "solve this" case.
    if not re.search(r"[+\-*/%]", candidate):
        return None
    try:
        tree = ast.parse(candidate, mode="eval")
        result = _safe_eval_node(tree)
    except Exception:
        return None
    return f"{candidate.strip()} = {_fmt(result)}."


def _try_percent_change(text: str) -> Optional[str]:
    m = _PERCENT_CHANGE.search(text)
    if not m:
        return None
    direction, base_s, pct_s = m.group(1).lower(), m.group(2), m.group(3)
    base, pct = float(base_s), float(pct_s)
    delta = base * pct / 100
    result = base + delta if direction in ("increase", "raise") else base - delta
    verb = "increased" if direction in ("increase", "raise") else "decreased"
    return f"{_fmt(base)} {verb} by {_fmt(pct)}% is {_fmt(result)}."


def _try_what_percent(text: str) -> Optional[str]:
    m = _WHAT_PERCENT.search(text)
    if not m:
        return None
    a, b = float(m.group(1)), float(m.group(2))
    if b == 0:
        return "That's dividing by zero, which has no defined answer."
    return f"{_fmt(a)} is {_fmt(a / b * 100)}% of {_fmt(b)}."


def _convert_units(value: float, from_u: str, to_u: str) -> Optional[float]:
    if from_u == to_u:
        return value
    if {from_u, to_u} == {"f", "c"}:
        return (value - 32) * 5 / 9 if from_u == "f" else value * 9 / 5 + 32
    if {from_u, to_u} == {"mi", "km"}:
        return value * 1.60934 if from_u == "mi" else value / 1.60934
    if {from_u, to_u} == {"lb", "kg"}:
        return value * 0.453592 if from_u == "lb" else value / 0.453592
    return None


_UNIT_LABELS = {"f": "°F", "c": "°C", "mi": "miles", "km": "km", "lb": "lbs", "kg": "kg"}


def _try_conversion(text: str) -> Optional[str]:
    m = _CONVERSION.search(text)
    if not m:
        return None
    value = float(m.group(1))
    from_key = _UNIT_ALIASES.get(re.sub(r"[°\s]", "", m.group(2).lower()))
    to_key = _UNIT_ALIASES.get(re.sub(r"[°\s]", "", m.group(3).lower()))
    if not from_key or not to_key:
        return None
    result = _convert_units(value, from_key, to_key)
    if result is None:
        return None
    return f"{_fmt(value)} {_UNIT_LABELS[from_key]} is {_fmt(result)} {_UNIT_LABELS[to_key]}."


def try_solve(question: str) -> Optional[str]:
    """Returns a plain-language, exact answer for arithmetic, percentage, or
    unit-conversion questions, or None if this can't solve the question
    exactly - callers should fall back to the model when None comes back."""
    text = question.strip()

    m = _PERCENT_OF.match(text)
    if m:
        pct, base = float(m.group(1)), float(m.group(2))
        return f"{_fmt(pct)}% of {_fmt(base)} is {_fmt(pct / 100 * base)}."

    m = _ARITHMETIC.match(text)
    if m:
        a, op_raw, b = float(m.group(1)), m.group(2).lower(), float(m.group(3))
        op = _OP_WORDS.get(op_raw, op_raw)
        if op == "/" and b == 0:
            return "That's dividing by zero, which has no defined answer."
        result = {"+": operator.add, "-": operator.sub, "*": operator.mul,
                  "x": operator.mul, "×": operator.mul, "/": operator.truediv}[op](a, b)
        return f"{_fmt(a)} {op} {_fmt(b)} = {_fmt(result)}."

    for fn in (_try_percent_change, _try_what_percent, _try_conversion, _try_expression):
        result = fn(text)
        if result:
            return result

    return None
