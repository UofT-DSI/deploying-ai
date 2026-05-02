import sys
import os

# Ensure 05_src is on the path so package imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Disable LangSmith tracing to avoid auth warnings
os.environ["LANGSMITH_TRACING"] = "false"

import gradio as gr
from assignment_chat.main import get_graph
from langchain_core.messages import HumanMessage, AIMessage

from utils.logger import get_logger

_logs = get_logger(__name__)

llm = get_graph()

def chat(message: str, history: list) -> str:
    langchain_messages = []
    for msg in history:
        if isinstance(msg, dict):
            if msg.get('role') == 'user':
                langchain_messages.append(HumanMessage(content=msg['content']))
            elif msg.get('role') == 'assistant':
                langchain_messages.append(AIMessage(content=msg['content']))
        elif isinstance(msg, (list, tuple)) and len(msg) == 2:
            if msg[0]:
                langchain_messages.append(HumanMessage(content=msg[0]))
            if msg[1]:
                langchain_messages.append(AIMessage(content=msg[1]))
    langchain_messages.append(HumanMessage(content=message))

    state = {"messages": langchain_messages}
    response = llm.invoke(state)
    return response['messages'][-1].content

chat_interface = gr.ChatInterface(
    fn=chat,
    title="CodeBot-7: Your Sci-Fi Chat Buddy",
    description="I do jokes, dataset search, and math."
)

if __name__ == "__main__":
    _logs.info('Starting CodeBot-7 Chat App...')
    chat_interface.launch()
