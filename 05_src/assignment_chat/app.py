# Gradio chat interface
# Adapted from course_chat/app.py - identical structure throughout.
# Run from 05_src/:
#   python -m assignment_chat.app

from assignment_chat.main import get_graph
from langchain_core.messages import HumanMessage, AIMessage
import gradio as gr
from dotenv import load_dotenv

from utils.logger import get_logger

_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")

llm = get_graph()


def aria_chat(message: str, history: list[dict]) -> str:
    """
    Chat function passed to Gradio.
    Converts Gradio message history into LangChain messages and invokes the graph.
    Identical to course_chat() in course_chat/app.py.
    """
    langchain_messages = []
    n = 0
    _logs.debug(f"History: {history}")

    for msg in history:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            langchain_messages.append(AIMessage(content=msg["content"]))
            n += 1

    langchain_messages.append(HumanMessage(content=message))

    state = {
        "messages": langchain_messages,
    }

    response = llm.invoke(state)
    return response["messages"][-1].content


chat = gr.ChatInterface(
    fn=aria_chat,
    title="Reenu Manderwal Assignment 2 Chat - Spaceflight News API",
    description=(
        "Ask me about AI trends (from the AI Report 2025), spaceflight news, "
        "or currency conversions. I won't discuss cats, dogs, horoscopes, or Taylor Swift."
    ),
    examples=[
        "What does the AI Report 2025 say about open source models?",
        "What is the latest SpaceX news?",
        "Convert 250 USD to EUR",
        "What does the AI Report 2025 say about AI safety and regulation?",
        "What are the latest NASA Mars mission updates?",
    ],
)

if __name__ == "__main__":
    _logs.info("Starting ARIA chat app...")
    chat.launch()
