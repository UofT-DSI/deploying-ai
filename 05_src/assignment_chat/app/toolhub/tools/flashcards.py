from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.core.openai_client import get_client
from app.toolhub.registry import ToolContext


def _pick_text(args: Dict[str, Any]) -> str:
    for key in ("text", "content", "input", "topic"):
        v = args.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _pick_count(args: Dict[str, Any], default: int = 5) -> int:
    for key in ("count", "n", "k"):
        v = args.get(key)
        try:
            if v is not None:
                n = int(v)
                return max(1, min(n, 12))
        except Exception:
            pass
    return default


def _safe_json_extract(s: str) -> Optional[Any]:
    """
    Try hard to extract a JSON object/array from an LLM response.
    Accepts:
      - raw JSON
      - ```json ... ```
      - text that contains a JSON array/object
    """
    if not s:
        return None

    # strip fenced blocks
    s2 = re.sub(r"^```(?:json)?\s*|\s*```$", "", s.strip(), flags=re.IGNORECASE | re.MULTILINE)

    # try direct parse
    try:
        return json.loads(s2)
    except Exception:
        pass

    # try to find first JSON object/array in text
    m = re.search(r"(\[\s*\{.*\}\s*\]|\{\s*\".*\}\s*)", s2, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


class FlashcardsTool:
    name = "flashcards"
    description = "Generate study flashcards from provided text or a topic."
    json_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Source text to turn into flashcards."},
            "topic": {"type": "string", "description": "Optional topic if no text is provided."},
            "count": {"type": "integer", "default": 5, "minimum": 1, "maximum": 12},
        },
        "required": [],
    }

    def __init__(self):
        self.oai = get_client()

    def run(self, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        text = _pick_text(args)
        n = _pick_count(args, default=5)

        if not text:
            return {"flashcards": []}

        system = (
            "You generate study flashcards. "
            "Return ONLY valid JSON: an array of objects with keys 'question' and 'answer'. "
            "No markdown, no extra text."
        )

        user = (
            f"Create {n} flashcards from the following material.\n\n"
            f"Material:\n{text}\n"
        )

        resp = self.oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )

        raw = (resp.choices[0].message.content or "").strip()
        parsed = _safe_json_extract(raw)

        cards: List[Dict[str, str]] = []

        if isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                q = str(item.get("question", "")).strip()
                a = str(item.get("answer", "")).strip()
                if q and a:
                    cards.append({"question": q, "answer": a})

        # Ensure we ALWAYS return the expected schema
        return {"flashcards": cards[:n]}