# 05_src/assignment_chat/app.py
from __future__ import annotations
import os, json, re
from pathlib import Path
import gradio as gr
from openai import OpenAI

from services import weather_api_summary, semantic_query, ensure_kb_index, tool_calculate, tool_convert
from guardrails import blocks_restricted, blocks_prompt_access, REFUSAL, PROMPT_GUARD
from memory import ShortTermMemory

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PERSIST = DATA_DIR / "chroma"

# Ensure local KB exists (first run creates tiny index)
DATA_DIR.mkdir(parents=True, exist_ok=True)
ensure_kb_index(DATA_DIR, PERSIST, "kb_main")

print("[startup] Key detected:", bool(os.getenv("OPENAI_API_KEY")),
      "| prefix:", (os.getenv("OPENAI_API_KEY") or "")[:8])

client = OpenAI()  # picks up keys from env (managed outside this app)

PERSONA = (
    "You are 'Astra', a witty Product Ops Analyst. Be concise, kind, and practical. "
    "Favor bullet points. If you use tools, explain the result in plain English."
)

# Register tools for function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calc",
            "description": "Evaluate a basic math expression (+-*/ and parentheses).",
            "parameters": {
                "type": "object",
                "properties": {"expr": {"type": "string"}},
                "required": ["expr"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert",
            "description": "Convert units (C<->F, km<->miles).",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit_from": {"type": "string"},
                    "unit_to": {"type": "string"},
                },
                "required": ["value", "unit_from", "unit_to"],
            },
        },
    },
]

# ---- City extraction helpers (fixes the Toronto fallback issue) ----
KNOWN_CITIES = {
    "toronto", "vancouver", "montreal", "calgary", "ottawa",
    "edmonton", "winnipeg", "halifax", "victoria", "waterloo",
    "brampton", "mississauga", "surrey", "burnaby", "richmond",
    "quebec", "laval", "saskatoon"
}

def extract_city(text: str) -> str | None:
    """Return a city name if found in text, else None."""
    if not text:
        return None
    raw = text.strip()
    low = raw.lower()

    # 1) Allow-list match (fast & reliable for demo)
    for c in KNOWN_CITIES:
        if c in low:
            return c.title()

    # 2) Pattern: "in <City ...>" (handles 'Weather in Vancouver today?')
    m = re.search(r"\bin\s+([A-Za-z][A-Za-z\s\-']+)", raw)
    if m:
        candidate = m.group(1).strip()
        # trim trailing filler like "today", "now", "please"
        candidate = re.sub(r"\b(today|now|please|pls)\b\.?$", "", candidate, flags=re.IGNORECASE).strip()
        if candidate:
            return candidate

    # 3) Fallback: first capitalized token that isn't a common filler
    stop = {"Weather", "Forecast", "Temperature", "Temps", "Today", "In", "Please"}
    for w in re.findall(r"[A-Za-z]+", raw):
        if w[0].isupper() and w not in stop:
            return w

    return None


def call_llm(messages, tools=None):
    return client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.4,
        messages=messages,
        tools=tools or None,
    )


def route(user_text: str) -> str:
    """
    Router: decides which service to invoke from natural language.
    Soft rules for demo; you can make this smarter later.
    """
    raw = user_text or ""
    low = raw.lower()

    # Hard guardrails first
    if blocks_prompt_access(low):
        return PROMPT_GUARD
    if blocks_restricted(low):
        return REFUSAL

    # Route: weather
    if any(k in low for k in ["weather", "forecast", "temperature"]):
        city = extract_city(raw) or "Toronto"
        return weather_api_summary(city)

    # Route: semantic search
    if any(k in low for k in ["kb", "knowledge", "docs", "explain", "what is", "how do i"]):
        return semantic_query(raw, DATA_DIR, PERSIST)

    # Otherwise: LLM + tools (NOW with short-term memory injected)
    history_text = ""
    try:
        history_text = mem.as_text()
    except Exception:
        history_text = ""

    msgs = [
        {"role": "system", "content": PERSONA},
    ]
    if history_text and history_text.strip():
        msgs.append({"role": "system", "content": f"Short-term conversation memory:\n{history_text}"})
    msgs.append({"role": "user", "content": raw})

    resp = call_llm(msgs, tools=TOOLS)

    # If tool call requested
    choice = resp.choices[0]
    if getattr(choice, "finish_reason", None) == "tool_calls" and choice.message.tool_calls:
        results = []
        for tc in choice.message.tool_calls:
            fn = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            if fn == "calc":
                results.append(tool_calculate(args.get("expr", "")))
            elif fn == "convert":
                results.append(
                    tool_convert(
                        args.get("value", 0.0),
                        args.get("unit_from", ""),
                        args.get("unit_to", ""),
                    )
                )
        # return tool outputs merged
        return "\n".join(results) if results else "I tried to run a tool but got no result."

    # Else, just reply
    return choice.message.content or "I don’t have a good answer yet."


# Rolling short-term memory used by both the router and UI callback
mem = ShortTermMemory(max_turns=8)


def chat_fn(message, history):
    # Apply rolling memory (shown only to the model in future if needed)
    reply = route(message)
    mem.add(message, reply)
    return reply


with gr.Blocks(title="Assignment 2 — Conversational AI") as demo:
    gr.Markdown(
        "# Assignment 2 — Conversational AI (Astra)\n"
        "_Friendly Product Ops Analyst with API, Semantic Search, and Function Calling._"
    )
    chatbot = gr.ChatInterface(
        fn=chat_fn,
        chatbot=gr.Chatbot(height=380),  # ✅ default type works
        title="Astra",
        theme="soft",
        examples=[
            "Weather in Vancouver today?",
            "Explain 'semantic search' from the KB",
            "Convert 72 F to C",
            "Calculate (20+5)*3",
        ],
    )

if __name__ == "__main__":
    demo.launch()
