"""Gradio entrypoint and high-level request router for TripSmith."""

import gradio as gr

from services.api_service import handle_weather_query, is_weather_query
from services.guardrails import check_guardrails
from services.semantic_service import handle_semantic_query
from services.tools_service import handle_tools_query, is_tools_query


def process_message(message: str, history: list[dict]) -> str:
    # Guardrails always run first so blocked content never reaches services.
    blocked_response = check_guardrails(message)
    if blocked_response:
        return blocked_response

    # Route to specialized handlers by intent, then fall back to semantic QA.
    if is_weather_query(message):
        return handle_weather_query(message, history=history)

    if is_tools_query(message):
        return handle_tools_query(message, history=history)

    return handle_semantic_query(message, history=history)


interface = gr.ChatInterface(
    fn=process_message,
    type="messages",
    title="TripSmith: Travel Planner AI",
    description="Pragmatic travel planning with weather, knowledge search, and function tools.",
)


if __name__ == "__main__":
    interface.launch()
