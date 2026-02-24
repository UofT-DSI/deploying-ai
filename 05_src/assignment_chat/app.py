import os
import gradio as gr
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


load_dotenv(r'C:\Users\pca_9\Desktop\deploying-ai\05_src\.secrets')


gateway_key = os.getenv('API_GATEWAY_KEY')

llm = init_chat_model(
    "gpt-4o-mini", 
    model_provider="openai",
    base_url='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1',
    default_headers={"x-api-key": gateway_key},
    api_key="any_value"
)

def simple_chat(message, history):
    # Guardrails: No Cats, Dogs, Horoscopes, or Taylor Swift
    system_prompt = SystemMessage(content="You are a witty assistant. You refuse to talk about Taylor Swift, pets, or zodiac signs.")
    langchain_messages = [system_prompt]
    
    for msg in history:
        role = HumanMessage if msg['role'] == 'user' else AIMessage
        langchain_messages.append(role(content=msg['content']))
    
    langchain_messages.append(HumanMessage(content=message))
    response = llm.invoke(langchain_messages)
    return response.content

if __name__ == "__main__":
    demo = gr.ChatInterface(fn=simple_chat, type="messages")
    demo.launch()