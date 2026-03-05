from __future__ import annotations

from typing import Any, Dict
from app.toolhub.registry import ToolContext

class SummarizeTool:
    name = "summarize"
    description = "Summarize user-provided text in a specified style."
    json_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "style": {"type": "string", "enum": ["bullet", "short", "study-notes"], "default": "short"},
        },
        "required": ["text"],
    }

    def run(self, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        # Deterministic tool: returns an instruction payload; LLM writes final summary.
        # This keeps the tool simple and still demonstrates tool selection.
        return {"text": args["text"], "style": args.get("style", "short")}