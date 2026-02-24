from assignment_chat.main import get_graph
from langchain_core.messages import HumanMessage, AIMessage
import gradio as gr
from dotenv import load_dotenv
from utils.logger import get_logger

_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")

llm = get_graph()


def assignment_chat(message: str, history: list[dict]) -> str:
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
        "llm_calls": n
    }

    response = llm.invoke(state)
    return response["messages"][-1].content


chat = gr.ChatInterface(
    fn=assignment_chat,
    type="messages",
    title="Humanitarian & disaster assistant",
    description="Uses: (1) HDX HAPI (structured indicators), (2) JIAF+EM-DAT semantic search, (3) simple web search (MCP)."
)

if __name__ == "__main__":
    _logs.info("Starting Assignment Chat App...")
    chat.launch()