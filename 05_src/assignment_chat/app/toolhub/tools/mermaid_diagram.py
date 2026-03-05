from __future__ import annotations
import re
from typing import Any, Dict
from app.toolhub.registry import ToolContext

class MermaidArchDiagramTool:
    name = "mermaid_diagram"
    description = "Generate a Mermaid diagram for the project's architecture (returns Mermaid code)."
    json_schema = {
        "type": "object",
        "properties": {
            "detail": {"type": "string", "enum": ["simple", "full"], "default": "full"},
        },
        "required": [],
    }

    def sanitize_mermaid(self, code: str) -> str:
       # Convert HTML breaks to newlines
       code = re.sub(r"<br\s*/?>", r"\n", code, flags=re.IGNORECASE)

       # Remove stray HTML tags (optional, safe)
       code = re.sub(r"</?[^>]+>", "", code)

       return code

    def run(self, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        detail = args.get("detail", "full")

        if detail == "simple":
            code = """flowchart LR
                    User --> Gradio
                    Gradio --> FastAPI
                    FastAPI --> Router
                    Router --> WeatherAPI
                    Router --> SemanticSearch
                    Router --> ToolHub
                    SemanticSearch --> ChromaDB
                """
        else:
            code = """flowchart TD

subgraph UI["Chat Interface"]
U["Gradio Chat UI\nPersona: StudyMate"]
end

subgraph BE["Backend"]
A["FastAPI: POST /chat"]
G["Guardrails Filter"]
M["Session Memory Manager"]
R["LLM Router (Function Calling)"]
end

subgraph S1["Service 1: Public API Service"]
W["Open-Meteo Weather API Client"]
end

subgraph S2["Service 2: Semantic Query Service"]
S["Semantic Search Service (RAG)"]
C[(ChromaDB Persistent Store)]
E["Embeddings via Hosted Gateway"]
end

subgraph S3["Service 3: Tool Hub"]
T["Tool Registry"]
F["Function Tools\ncalculate / summarize / flashcards / mermaid"]
B["Web Search Tool\n(Wikipedia)"]
end

U --> A --> G --> M --> R
R --> W --> R
R --> S --> R
S --> C
S --> E
R --> T
T --> F
T --> B
T --> R
R --> A --> U"""
            mermaid = self.sanitize_mermaid(code)
            return {"mermaid": f"```mermaid\n{mermaid.strip()}\n```"}