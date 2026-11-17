
"""ResearchMate AI - Gradio application with MCP support."""

import sys
import asyncio
import logging
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".secrets")

from assignment_chat.main import get_graph


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_graph = None
_graph_lock = None


async def graph():
    """Initialize the graph once for this application process."""

    global _graph, _graph_lock

    if _graph is not None:
        return _graph

    if _graph_lock is None:
        _graph_lock = asyncio.Lock()

    async with _graph_lock:
        if _graph is None:
            _graph = await get_graph()

    return _graph


async def researchmate_chat(
    message: str,
    history: list[dict],
) -> str:
    """Process a conversation through LangGraph."""

    langchain_messages = []

    for item in history:
        if item["role"] == "user":
            langchain_messages.append(
                HumanMessage(content=item["content"])
            )
        elif item["role"] == "assistant":
            langchain_messages.append(
                AIMessage(content=item["content"])
            )

    langchain_messages.append(
        HumanMessage(content=message)
    )

    try:
        agent = await graph()

        result = await agent.ainvoke({
            "messages": langchain_messages
        })

        return str(result["messages"][-1].content)

    except Exception:
        logger.exception("ResearchMate AI request failed")
        return (
            "Sorry, I couldn't complete your research "
            "request. Please try again."
        )


chat = gr.ChatInterface(
    fn=researchmate_chat,
    title="ResearchMate AI",
    description=(
        "Explore academic research using OpenAlex, "
        "ChromaDB semantic search, and ArXiv MCP."
    ),
    examples=[
        "Find five RAG papers published between 2023 and 2025.",
        "Explain the original RAG architecture.",
        "Search ArXiv for recent research about AI agents.",
    ],
)


if __name__ == "__main__":
    logger.info("Starting ResearchMate AI...")
    chat.launch()
