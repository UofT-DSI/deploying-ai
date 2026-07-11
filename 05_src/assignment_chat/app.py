import gradio as gr
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage

from main import get_graph

graph = get_graph()


def chat(message, history):
    messages = []

    for item in history:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        elif item["role"] == "assistant":
            messages.append(AIMessage(content=item["content"]))

    messages.append(HumanMessage(content=message))

    response = graph.invoke({"messages": messages})

    return response["messages"][-1].content


demo = gr.ChatInterface(
    fn=chat,
    title="AI Study Buddy",
    description="Ask questions about AI concepts, request a study quiz, or get a programming quote.",
)


if __name__ == "__main__":
    demo.launch()

