from __future__ import annotations

import re
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

from .config import MAX_HISTORY_TURNS, MODEL_NAME, SYSTEM_PROMPT, get_openai_client_kwargs, has_openai_access
from .guardrails import evaluate_guardrails
from .semantic_service import build_or_refresh_index
from .services import planning_tool_service, semantic_course_qa, weather_api_summary

load_dotenv(str(Path(__file__).resolve().parents[1] / ".env"))
load_dotenv(str(Path(__file__).resolve().parents[1] / ".secrets"))


def _trim_history(history: list[dict]) -> list[dict]:
    max_messages = MAX_HISTORY_TURNS * 2
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]


def _general_chat(message: str, history: list[dict]) -> str:
    if not has_openai_access():
        return (
            "OPENAI_API_KEY is missing. You can still use /weather and /search if indexing is prepared. "
            "Set OPENAI_API_KEY for full chat and /plan."
        )

    client = OpenAI(**get_openai_client_kwargs())

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in _trim_history(history):
        role = item.get("role")
        content = item.get("content", "")
        if role in {"user", "assistant"}:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
        )
        return response.choices[0].message.content or "I’m not sure yet."
    except Exception:
        return (
            "I can’t reach the model service right now. "
            "Please try again in a moment, or use /weather, /search, or /plan for focused tasks."
        )


def assignment_chat(message: str, history: list[dict]) -> str:
    guardrail_reply = evaluate_guardrails(message)
    if guardrail_reply:
        return guardrail_reply

    text = (message or "").strip()
    lower = text.lower()

    if lower.startswith("/weather"):
        query = text[len("/weather") :].strip()
        return weather_api_summary(query)

    if lower.startswith("/forecast"):
        query = text[len("/forecast") :].strip()
        if not query:
            return "Usage: /forecast <city name>"
        return weather_api_summary(f"forecast for {query}")

    if lower.startswith("/search"):
        question = text[len("/search") :].strip()
        return semantic_course_qa(question)

    if lower.startswith("/plan"):
        request = text[len("/plan") :].strip()
        if not request:
            request = "Create a 7-day plan for reviewing RAG, tools, and evaluation with 60 minutes per day."
        return planning_tool_service(request)

    if lower.startswith("/reindex"):
        return build_or_refresh_index(force=True)

    if re.search(r"\b(weather|forecast)\b", lower):
        return weather_api_summary(text)

    return _general_chat(text, history)


chat = gr.ChatInterface(
    fn=assignment_chat,
    type="messages",
    title="Nova - Assignment 2 Chat",
    # description=(
    #     "Commands: /weather <city>, /search <food/friendship/community question>, /plan <study request>, /reindex"
    # ),
)


if __name__ == "__main__":
    chat.launch()
