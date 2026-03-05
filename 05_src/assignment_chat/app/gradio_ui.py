from __future__ import annotations

import uuid
import requests
import gradio as gr

API_URL = "http://127.0.0.1:8000/chat"


def call_backend(session_id: str, message: str) -> str:
    payload = {"session_id": session_id, "message": message}
    r = requests.post(API_URL, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["reply"]


def chat_fn(message, history, session_id):
    if history is None:
        history = []

    reply = call_backend(session_id, message)

    # Append in new messages format
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})

    return "", history, session_id


def new_session():
    return str(uuid.uuid4()), []


with gr.Blocks(title="StudyMate 🤖📚") as demo:
    gr.Markdown("## StudyMate 🤖📚")
    gr.Markdown(
        "Ask about embeddings, ChromaDB, RAG, or generate Mermaid diagrams."
    )

    session_id = gr.State(str(uuid.uuid4()))
    chatbot = gr.Chatbot(height=450)  # works across versions
    msg = gr.Textbox(
        placeholder="Ask something...",
        show_label=False,
        container=False,
    )

    clear_btn = gr.Button("New Session")

    msg.submit(
        chat_fn,
        inputs=[msg, chatbot, session_id],
        outputs=[msg, chatbot, session_id],
    )

    clear_btn.click(
        fn=new_session,
        inputs=None,
        outputs=[session_id, chatbot],
    )


if __name__ == "__main__":
    demo.launch()