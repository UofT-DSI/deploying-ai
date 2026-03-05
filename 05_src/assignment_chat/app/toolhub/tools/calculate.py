from __future__ import annotations

import ast
import operator as op
from typing import Any, Dict
from app.toolhub.registry import ToolContext

_ALLOWED = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.USub: op.neg,
}

def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED:
        return _ALLOWED[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED:
        return _ALLOWED[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")

class CalculateTool:
    name = "calculate"
    description = "Evaluate a simple arithmetic expression (+, -, *, /, parentheses)."
    json_schema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    }

    def run(self, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        expr = args["expression"]
        tree = ast.parse(expr, mode="eval")
        return {"result": float(_eval(tree.body))}