import gradio as gr
from assignment2_chat.main import alva_chat
from dotenv import load_dotenv
from typing import Optional
import os

from utils.logger import get_logger

_logs = get_logger(__name__)

load_dotenv('.secrets')

chat = gr.ChatInterface(
    fn=alva_chat
)

if __name__ == "__main__":
    _logs.info('Starting Alva Chat App...')
    chat.launch()
