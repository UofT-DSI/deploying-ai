from animals_chat.main import get_animals_chat_agent
from langchain_core.messages import HumanMessage, AIMessage
import gradio as gr
from dotenv import load_dotenv
import os

from utils.logger import get_logger

_logs = get_logger(__name__)

llm = get_animals_chat_agent()

load_dotenv('.secrets')

def animals_chat(message: str, history: list[dict]) -> str:
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

    response = llm.invoke(state)
    return response['messages'][len(response['messages']) - 1].content

chat = gr.ChatInterface(
    fn=animals_chat,
    type="messages"
)

if __name__ == "__main__":
    _logs.info('Starting Animals Chat App...')
    chat.launch()
