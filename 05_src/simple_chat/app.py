import gradio as gr
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from typing import Optional
import os

from langchain.chat_models import init_chat_model

load_dotenv('.secrets')

if not os.environ.get("OPENAI_API_KEY"):
    raise ValueError("Missing OPENAI_API_KEY environment variable")

llm = init_chat_model("gpt-4o-mini", model_provider="openai")


def simple_chat(message: str, history: list[dict]) -> str:
    langchain_messages = []
    for msg in history:
        if msg['role'] == 'user':
            langchain_messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            langchain_messages.append(AIMessage(content=msg['content']))
    langchain_messages.append(HumanMessage(content=message))

    response = llm.invoke(langchain_messages)

    return response.content

    
gr.ChatInterface(
    fn=simple_chat,
    type="messages"
).launch()
