"""
core/math_solver.py - deterministic arithmetic for simple "what's X% of Y" /
"what is A + B" style questions.

The local Duke Brain (a small local language model - see ml/duke_brain.py)
has no real arithmetic ability; it pattern-matches a plausible-looking
answer for basic math the same way it would for any other text, and gets
it wrong (proven live: "what's 15% of 240?" -> hallucinated 45 instead of
36). Simple, unambiguous arithmetic questions are solved exactly instead of
asking the model to guess - the same approach DATE_TIME_PATTERN in
duke_brain.py already uses for date/time questions.
"""
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


def try_solve(question: str) -> Optional[str]:
    """Returns a plain-language answer for simple arithmetic, or None if the
    question isn't a bare arithmetic expression this can solve exactly.
    Anchored to the whole question (not a substring search) so it never
    fires on a question that merely mentions a number in passing."""
    text = question.strip()

    m = _PERCENT_OF.match(text)
    if m:
        pct, base = float(m.group(1)), float(m.group(2))
        result = pct / 100 * base
        return f"{_fmt(pct)}% of {_fmt(base)} is {_fmt(result)}."

    m = _ARITHMETIC.match(text)
    if m:
        a, op_raw, b = float(m.group(1)), m.group(2).lower(), float(m.group(3))
        op = _OP_WORDS.get(op_raw, op_raw)
        if op in ("*", "x", "×"):
            result = a * b
        elif op == "/":
            if b == 0:
                return "That's dividing by zero, which has no defined answer."
            result = a / b
        elif op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        else:
            return None
        return f"{_fmt(a)} {op} {_fmt(b)} = {_fmt(result)}."

    return None


def _fmt(n: float) -> str:
    return str(int(n)) if n == int(n) else str(n)
