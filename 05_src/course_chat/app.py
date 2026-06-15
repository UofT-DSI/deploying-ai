import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="gradio")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette")

from course_chat.main import get_agent
import gradio as gr
from dotenv import load_dotenv

from utils.logger import get_logger

_logs = get_logger(__name__)

load_dotenv(".secrets")

agent = get_agent()


def course_chat(message: str, history: list[dict]) -> str:
    messages = [(msg["role"], msg["content"]) for msg in history]
    messages.append(("user", message))
    _logs.debug(f"Invoking agent with {len(messages)} messages")
    result = agent.invoke({"messages": messages})
    return result["messages"][-1].content


chat = gr.ChatInterface(
    fn=course_chat,
)

if __name__ == "__main__":
    _logs.info("Starting Course Chat App...")
    chat.launch()
