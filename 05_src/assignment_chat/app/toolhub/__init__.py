from app.toolhub.registry import ToolRegistry
from app.toolhub.tools.calculate import CalculateTool
from app.toolhub.tools.summarize import SummarizeTool
from app.toolhub.tools.flashcards import FlashcardsTool
from app.toolhub.tools.mermaid_diagram import MermaidArchDiagramTool
from app.toolhub.tools.websearch_wikipedia import WebSearchWikipediaTool

def build_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(CalculateTool())
    reg.register(SummarizeTool())
    reg.register(FlashcardsTool())
    reg.register(MermaidArchDiagramTool())
    reg.register(WebSearchWikipediaTool())
    return reg