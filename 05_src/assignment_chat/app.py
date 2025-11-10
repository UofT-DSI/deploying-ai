from dotenv import load_dotenv
import os
from utils.logger import get_logger
import requests
import gradio as gr
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage
from main import get_graph

_logs = get_logger(__name__)

load_dotenv('.secrets')

llm = get_graph()


def reply(text: str, intensity: int, history=[]):
    langchain_messages = []
    n = 0
    _logs.debug(f"History: {history}")
    for msg in history:
        if msg['role'] == 'user':
            langchain_messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            langchain_messages.append(AIMessage(content=msg['content']))
            n += 1
    langchain_messages.append(HumanMessage(content=text))

    state = {
        "messages": langchain_messages,
        "llm_calls": n
    }
    response = llm.invoke(state)
    return response['messages'][len(response['messages']) - 1].content

demo = gr.Interface(
    fn=reply,
    inputs=["text", "slider"],
    outputs=["text"],
)

demo.launch()