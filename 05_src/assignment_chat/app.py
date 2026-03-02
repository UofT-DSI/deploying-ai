# Assignment 2: Conversational AI System (Gradio + 3 services + guardrails)

import os
import json
import requests
import gradio as gr
from openai import OpenAI
from chromadb import Client
from chromadb.config import Settings

# -----------------------------
# Config (DO NOT hardcode keys)
# -----------------------------
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TXT_PATH = os.path.join(BASE_DIR, "data", "sherlock.txt")
PERSIST_DIR = os.path.join(BASE_DIR, "data", "chroma")
os.makedirs(PERSIST_DIR, exist_ok=True)

# OpenAI client (expects OPENAI_API_KEY in env)
openai_client = OpenAI()

# ChromaDB persistent client
chroma_client = Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory=PERSIST_DIR,
    anonymized_telemetry=False
))
collection = chroma_client.get_or_create_collection(name="sherlock_collection")

# -----------------------------
# Guardrails
# -----------------------------
RESTRICTED_TOPICS = ["cats", "dogs", "horoscope", "zodiac", "taylor swift"]

PROMPT_ATTACK_PATTERNS = [
    "system prompt", "developer message", "hidden prompt", "reveal prompt",
    "show your instructions", "print your instructions",
    "ignore previous instructions", "override instructions",
    "change the system prompt", "modify the system prompt",
    "jailbreak", "dan"
]

def violates_prompt_guardrails(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in PROMPT_ATTACK_PATTERNS)

def violates_topic_guardrails(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in RESTRICTED_TOPICS)

# -----------------------------
# Service 1: API Calls (Weather)
# -----------------------------
def get_weather(city: str) -> str:
    if OPENWEATHER_API_KEY == "YOUR_OPENWEATHERMAP_KEY":
        return "Weather service isn't configured. Set OPENWEATHER_API_KEY in your environment."

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
    resp = requests.get(url, timeout=15).json()

    if resp.get("cod") != 200:
        return f"Sorry, I couldn't find weather data for '{city}'."

    temp = resp["main"]["temp"]
    description = resp["weather"][0]["description"]
    wind = resp["wind"]["speed"]

    # IMPORTANT: this line must be INDENTED (4 spaces)
    return f"[API] In {city}, it's {temp:.1f}°C with {description}. Wind speed is about {wind:.1f} m/s."
# -----------------------------
# Service 2: Semantic Query (Sherlock + ChromaDB)
# -----------------------------
def embed_text(text: str):
    emb = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return emb.data[0].embedding

def split_text(text: str, chunk_size: int = 1200, overlap: int = 200):
    chunks = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks

def load_sherlock_dataset_if_needed():
    # Only ingest if collection is empty
    existing = collection.get()
    if len(existing.get("ids", [])) > 0:
        return

    with open(TXT_PATH, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    chunks = split_text(text, chunk_size=1200, overlap=200)

    # Batch ingest embeddings
    BATCH = 64
    for i in range(0, len(chunks), BATCH):
        batch_chunks = chunks[i:i+BATCH]

        embeddings = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=batch_chunks
        )
        embs = [d.embedding for d in embeddings.data]

        ids = [f"chunk_{i+j}" for j in range(len(batch_chunks))]
        metas = [{"source": "sherlock.txt", "chunk": i+j} for j in range(len(batch_chunks))]

        collection.add(
            ids=ids,
            documents=batch_chunks,
            embeddings=embs,
            metadatas=metas
        )

    # Persist to disk
    try:
        chroma_client.persist()
    except Exception:
        pass

def semantic_query(query: str) -> str:
    q_emb = embed_text(query)
    results = collection.query(query_embeddings=[q_emb], n_results=3)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    if not docs:
        return "Sorry, I couldn't find anything relevant in the Sherlock text."

    sources = []
    for m in metas:
        if isinstance(m, dict) and "chunk" in m:
            sources.append(f"chunk_{m['chunk']}")
    sources = sorted(set(sources))[:5]

    excerpt = "\n\n---\n\n".join(docs)

    resp = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are HolmesBot. Answer clearly using ONLY the excerpts."
                ),
            },
            {"role": "user", "content": f"Question: {query}\n\nExcerpts:\n{excerpt}"}
        ],
    )

    answer = resp.choices[0].message.content.strip()
    answer = "[RAG] " + answer

    if sources:
        answer += f"\n\nSources: {', '.join(sources)}"

    return answer


# Ingest on first run only (empty collection)
load_sherlock_dataset_if_needed()

# -----------------------------
# Service 3: Function Calling (Tool) — Unit Conversion
# -----------------------------
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    conversions = {
        "miles_km": 1.60934,
        "km_miles": 0.621371,
        "lbs_kg": 0.453592,
        "kg_lbs": 2.20462
    }
    key = f"{from_unit}_{to_unit}"
    if key not in conversions:
        return "Sorry, I can only convert miles↔km or lbs↔kg."
    converted = value * conversions[key]
    return f"{value:g} {from_unit} is approximately {converted:.2f} {to_unit}."

CONVERT_TOOL = {
    "type": "function",
    "function": {
        "name": "convert_units",
        "description": "Convert between miles<->km or lbs<->kg.",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {"type": "number"},
                "from_unit": {"type": "string", "enum": ["miles", "km", "lbs", "kg"]},
                "to_unit": {"type": "string", "enum": ["miles", "km", "lbs", "kg"]}
            },
            "required": ["value", "from_unit", "to_unit"]
        }
    }
}

def run_conversion_tool(user_input: str) -> str:
    resp = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "If the user asks for a supported unit conversion, call the tool."},
            {"role": "user", "content": user_input},
        ],
        tools=[CONVERT_TOOL],
        tool_choice="auto",
    )

    msg = resp.choices[0].message

    if not msg.tool_calls:
        return "Try: 'Convert 10 miles to km' or 'Convert 180 lbs to kg'."

    tc = msg.tool_calls[0]
    args = json.loads(tc.function.arguments)

    # THIS return must be indented inside the function
    return "[TOOL] " + convert_units(
        float(args["value"]),
        args["from_unit"],
        args["to_unit"]
    )

# -----------------------------
# Router + Memory + Personality
# -----------------------------
CASE_FILE = ""  # rolling summary of earlier conversation

CASE_FILE = ""  # rolling summary of older conversation turns

def maybe_update_case_file(history, max_turns: int = 10) -> str:
    """
    If chat history gets long, compress older turns into CASE_FILE and keep only recent turns.
    Demonstrates short-term memory management (optional requirement).
    """
    global CASE_FILE
    if len(history) <= max_turns:
        return CASE_FILE

    older = history[:-6]  # compress all but last 6 turns
    recent = history[-6:]

    convo_text = "\n".join([f"User: {u}\nBot: {b}" for (u, b) in older])

    resp = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Summarize this conversation into a short case file of key facts and user goals."},
            {"role": "user", "content": convo_text}
        ],
    )

    new_summary = resp.choices[0].message.content.strip()
    CASE_FILE = (CASE_FILE + "\n" + new_summary).strip() if CASE_FILE else new_summary

    # Keep only recent messages in UI history
    history[:] = recent
    return CASE_FILE

SYSTEM_PERSONA = (
    "You are HolmesBot: concise, slightly witty, and helpful. "
    "You keep answers clear and practical."
)

def route(user_input: str, case_file: str) -> str:
    text = user_input.lower()

    if "weather" in text:
        city = user_input.split("in")[-1].strip()
        return get_weather(city)

    if "convert" in text:
        return run_conversion_tool(user_input)

    # Default: semantic search, enriched with compact conversation context
    if case_file:
        enriched_query = f"{user_input}\n\nConversation context (case file): {case_file}"
        return semantic_query(enriched_query)

    return semantic_query(user_input)

def chat(user_input, history):
    if violates_topic_guardrails(user_input):
        bot = "Sorry — I can’t help with that topic."
        history = history + [(user_input, bot)]
        return history, ""

    if violates_prompt_guardrails(user_input):
        bot = "Sorry — I can’t reveal or modify my system instructions."
        history = history + [(user_input, bot)]
        return history, ""

    # Memory management: compress older turns into CASE_FILE
    case_file = maybe_update_case_file(history, max_turns=10)

    bot = route(user_input, case_file)
    history = history + [(user_input, bot)]
    return history, ""

    # Memory management: compress old turns into CASE_FILE when needed
    case_file = maybe_update_case_file(history, max_turns=10)

    # Route to service using compact case file
    bot = route(user_input, case_file)

    history = history + [(user_input, bot)]
    return history, ""

#load gradio UI
with gr.Blocks() as demo:
    gr.Markdown(
        "### 🕵️ Fedya Holmes\n"
        "I’m your Sherlock-inspired assistant."
        "Ask about weather, Sherlock, or conversions between units."
    )

    chatbot = gr.Chatbot()
    user_input = gr.Textbox(label="Your message")
    state = gr.State([])

    user_input.submit(
        chat,
        inputs=[user_input, state],
        outputs=[chatbot, user_input]
    ).then(
        lambda h: h,
        inputs=chatbot,
        outputs=state
    )

demo.launch()