import sys
sys.path.append('../05_src/')


from dotenv import load_dotenv
#from helpers import generate_augemented_prompt


import os
import gradio as gr



load_dotenv("../05_src/.env")
load_dotenv("../05_src/.secrets")




    
chat = gr.ChatInterface(
    fn=simple_chat,
    type="messages"
)

if "__name__" == "__main__":
    chat.launch()
