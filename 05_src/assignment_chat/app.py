
import sys
from pathlib import Path
import gradio as gr

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from assignment_chat.main import get_graph
from assignment_chat.guardrails import check_guardrails


graph = get_graph()


def chat(message, history):
    guardrail_response = check_guardrails(message)

    if guardrail_response:
        return guardrail_response
    
    messages = []

    for item in history:
        messages.append({
            "role": item["role"],
            "content": item["content"]
        })

    messages.append({
        "role": "user",
        "content": message
    })

    response = graph.invoke({
    "messages": messages
    })

    print("\n--- DEBUG: Conversation Messages ---")

    for msg in response["messages"]:
        print("\nType:", msg.type)

        if getattr(msg, "tool_calls", None):
            print("Tool calls:", msg.tool_calls)

        if msg.content:
            print("Content:", msg.content)

    return response["messages"][-1].content


demo = gr.ChatInterface(
    fn=chat,
    title="FitCoach AI",
    description="Your personal AI fitness and nutrition assistant."
)


if __name__ == "__main__":
    demo.launch()
