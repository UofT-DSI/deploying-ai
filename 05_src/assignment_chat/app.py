import gradio as gr
from assignment_chat.main import ipstack_chat

from dotenv import load_dotenv
from typing import Optional
import os

from utils.logger import get_logger

_logs = get_logger(__name__)

load_dotenv('.secrets')

chat = gr.ChatInterface(
    fn=ipstack_chat,    # need to be replaced
    type="messages"
)

if __name__ == "__main__":
    _logs.info('Starting IPStack Chat App...')    # need to be replaced
    chat.launch()
