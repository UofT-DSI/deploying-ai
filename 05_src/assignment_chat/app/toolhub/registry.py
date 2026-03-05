from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol, List

@dataclass
class ToolContext:
    # you can add session_id, memory, etc later if needed
    pass

class Tool(Protocol):
    name: str
    description: str
    json_schema: dict
    def run(self, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]: ...

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list_openai_tools(self) -> List[dict]:
        """Return OpenAI 'tools' schema for function calling."""
        out = []
        for t in self._tools.values():
            out.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.json_schema,
                }
            })
        return out