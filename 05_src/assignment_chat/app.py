# app.py — Gradio chat interface (main entrypoint)

import json
import gradio as gr

from config import client, CHAT_MODEL, SYSTEM_PROMPT
from router import detect_intent, extract_date_range, extract_region
from guardrails.policy import check_message
from services.bank_holidays_service import get_holidays_in_range
from services.mitre_search_service import search_mitre
from services.soc_triage_tool import run_soc_triage


def llm(prompt: str) -> str:
    """Single helper to call the AWS-hosted LLM."""
    response = client.responses.create(
        model=CHAT_MODEL,
        input=prompt,
    )
    return response.output_text


def build_context(history: list) -> str:
    """
    Convert Gradio chat history into a plain text context string
    to prepend to the prompt.
    """
    lines = [f"System: {SYSTEM_PROMPT}\n"]
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
    return "\n".join(lines)


def chat(user_message: str, history: list) -> tuple[str, list]:
    """
    Main chat handler.
    history: list of [user_msg, assistant_msg] pairs (Gradio format)
    """

    # --- Step 1: Guardrails ---
    blocked = check_message(user_message)
    if blocked:
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": blocked})
        return "", history

    # --- Step 2: Build conversation context ---
    context = build_context(history)

    # --- Step 3: Route to correct service ---
    intent = detect_intent(user_message)

    if intent == "bank_holiday":
        start, end = extract_date_range(user_message)
        region = extract_region(user_message)

        if not start or not end:
            reply = (
                "Please provide a date range in YYYY-MM-DD format. "
                "For example: 'Show bank holidays in Scotland between 2026-01-01 and 2026-06-30'."
            )
        else:
            data = get_holidays_in_range(region, start, end)

            # "prompt" means we need more info from the user
            if "prompt" in data:
                reply = data["prompt"]
            # "message" means no holidays found
            elif "message" in data:
                reply = data["message"]
            # "error" means something went wrong
            elif "error" in data:
                reply = f"I encountered an issue: {data['error']}"
            else:
                prompt = (
                    f"{context}\n\n"
                    f"User: {user_message}\n\n"
                    f"Here is the bank holiday data in JSON:\n{json.dumps(data, indent=2)}\n\n"
                    f"Format this as a clear, friendly response in your SOC mentor tone. "
                    f"Do not show raw JSON to the user."
                )
                reply = llm(prompt)

    elif intent == "mitre_search":
        data = search_mitre(user_message)
        prompt = (
            f"{context}\n\n"
            f"User: {user_message}\n\n"
            f"Here are the top MITRE ATT&CK search results:\n{json.dumps(data, indent=2)}\n\n"
            f"Answer the analyst's question using these results. "
            f"List the top matching techniques clearly, then give a short explanation."
        )
        reply = llm(prompt)

    elif intent == "soc_triage":
        reply = run_soc_triage(user_message, context)

    else:
        # Normal conversation
        prompt = f"{context}\nUser: {user_message}\nAssistant:"
        reply = llm(prompt)

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    return "", history


# --- Gradio UI ---
with gr.Blocks(title="SOC Mentor") as demo:
    gr.Markdown("## 🛡️ SOC Mentor\n*Your calm, experienced security operations guide.*")

    chatbot = gr.Chatbot(height=500)
    msg = gr.Textbox(
        placeholder="Ask about MITRE techniques, UK bank holidays, or paste a Defender alert...",
        label="Your message",
    )
    clear = gr.Button("Clear conversation")

    msg.submit(chat, inputs=[msg, chatbot], outputs=[msg, chatbot])
    clear.click(lambda: ([], []), outputs=[msg, chatbot])

if __name__ == "__main__":
    demo.launch()