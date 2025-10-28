import gradio as gr
from horoscope_chat.main import horoscope_chat
from dotenv import load_dotenv
from typing import Optional
import os

from utils.logger import get_logger

_logs = get_logger(__name__)

load_dotenv('.secrets')

chat = gr.ChatInterface(
    fn=horoscope_chat,
    type="messages"
)

if __name__ == "__main__":
    _logs.info('Starting Horoscope Chat App...')
    chat.launch()
