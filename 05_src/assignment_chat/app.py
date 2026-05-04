from assignment_chat.main import get_graph
from langchain_core.messages import HumanMessage, AIMessage
import gradio as gr
from dotenv import load_dotenv

from utils.logger import get_logger
_logs = get_logger(__name__)

llm = get_graph()

load_dotenv('.secrets')

def chat_with_jack(message: str, history: list[dict]) -> str:
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
    fn=chat_with_jack,
    type="messages"
)

if __name__ == "__main__":
    _logs.info('Entering Jack Sparrow\'s Carribian world...')
    chat.launch()
