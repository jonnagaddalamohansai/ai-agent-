"""Small, bounded tools available to both demo mode and the AI model."""

import ast
import math
import operator
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Calculate arithmetic with +, -, *, /, %, **, and parentheses.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "current_time",
            "description": "Get the current date and time in an IANA zone, such as Asia/Kolkata.",
            "parameters": {
                "type": "object",
                "properties": {"timezone": {"type": "string"}},
                "required": ["timezone"],
                "additionalProperties": False,
            },
        },
    },
]


def calculate(expression: str) -> str:
    """Evaluate bounded numeric AST nodes, never arbitrary Python code."""
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 200:
        raise ValueError("Use an arithmetic expression of 1 to 200 characters.")
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("Invalid arithmetic expression.") from exc
    if sum(1 for _ in ast.walk(tree)) > 64:
        raise ValueError("Expression is too complex.")

    operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    def bounded(value: int | float) -> int | float:
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e12:
            raise ValueError("Numbers and results must be finite and at most 1 trillion.")
        return value

    def visit(node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant):
            return bounded(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = visit(node.operand)
            return bounded(operand if isinstance(node.op, ast.UAdd) else -operand)
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 12:
                raise ValueError("Exponents must be between -12 and 12.")
            try:
                return bounded(operations[type(node.op)](left, right))
            except (ZeroDivisionError, OverflowError, TypeError) as exc:
                raise ValueError("This expression has no supported finite result.") from exc
        raise ValueError("Only numbers and arithmetic operators are allowed.")

    result = visit(tree.body)
    return str(result) if isinstance(result, int) else format(result, ".12g")


def current_time(timezone: str = "UTC") -> str:
    if not isinstance(timezone, str) or not timezone or len(timezone) > 100:
        raise ValueError("Provide a valid IANA timezone, such as UTC or Asia/Kolkata.")
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("Unknown timezone. Use an IANA name such as Asia/Kolkata.") from exc
    return f"{datetime.now(zone).isoformat(timespec='seconds')} ({timezone})"


def run_tool(name: str, arguments: dict) -> str:
    if name == "calculator" and set(arguments) == {"expression"}:
        return calculate(arguments["expression"])
    if name == "current_time" and set(arguments) <= {"timezone"}:
        return current_time(arguments.get("timezone", "UTC"))
    raise ValueError("Unknown tool or invalid tool arguments.")
