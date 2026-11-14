import sys
from pathlib import Path
from functools import lru_cache

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assignment_chat.main import get_graph
from langchain_core.messages import HumanMessage, AIMessage
import gradio as gr
from dotenv import load_dotenv
import logging

load_dotenv('.secrets')
_logs = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def graph():
    return get_graph()

def assignment_chat(message: str, history: list[dict]) -> str:
    langchain_messages = []
    n = 0
    _logs.debug(f"History: {history}")
    for msg in history:
        if msg['role'] == 'user':
            langchain_messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            langchain_messages.append(AIMessage(content=msg['content']))
            n += 1
    langchain_messages.append(HumanMessage(content=message))

    state = {
        "messages": langchain_messages,
        "llm_calls": n
    }

    response = graph().invoke(state)
    return response['messages'][len(response['messages']) - 1].content

chat = gr.ChatInterface(
    fn=assignment_chat
)

if __name__ == "__main__":
    _logs.info('Starting Assignment Chat App...')
    chat.launch()
