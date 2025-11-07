# 05_src/assignment_chat/services.py
from __future__ import annotations
from typing import Dict, List, Any
import requests
from pathlib import Path
import chromadb
from chromadb.config import Settings
import csv

# ---------- Service 1: Public API (Open-Meteo) ----------
def weather_api_summary(city: str = "Toronto") -> str:
    """
    Calls Open-Meteo geocoding + forecast (no API key).
    Transforms raw JSON into a clean 1-2 sentence summary.
    """
    r = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1})
    r.raise_for_status()
    data = r.json()
    if not data.get("results"):
        return f"Sorry, I couldn’t find {city} on the map."

    lat = data["results"][0]["latitude"]
    lon = data["results"][0]["longitude"]
    label = data["results"][0].get("name", city)

    f = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "hourly": "temperature_2m,precipitation", "forecast_days": 1},
    )
    f.raise_for_status()
    fj = f.json()
    temps = fj.get("hourly", {}).get("temperature_2m", [])
    prcp = fj.get("hourly", {}).get("precipitation", [])
    if not temps:
        return f"Weather for {label}: no hourly data available."
    hi = max(temps)
    lo = min(temps)
    wet = sum(1 for p in prcp if p and p > 0) if prcp else 0
    rain_hint = "with some precipitation expected" if wet > 0 else "with low chance of rain"
    return f"{label}: temperatures between {round(lo)}°C and {round(hi)}°C today, {rain_hint}."


# ---------- Service 2: Semantic Search (Chroma + small CSV) ----------
def _chroma_client(persist_dir: Path) -> chromadb.Client:
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir), settings=Settings(allow_reset=True))


def _load_seed_data(csv_path: Path) -> List[Dict[str, str]]:
    rows = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def ensure_kb_index(data_dir: Path, persist_dir: Path, collection_name: str = "kb_main"):
    """
    Creates a tiny semantic KB if not present. Meant for ≤40MB CSV.
    Embeddings are computed via Chroma default embedding function (no extra libs).
    """
    client = _chroma_client(persist_dir)
    try:
        col = client.get_collection(collection_name)
        if col.count() > 0:
            return
    except Exception:
        col = client.create_collection(collection_name)

    csv_path = data_dir / "kb_small.csv"
    if not csv_path.exists():
        seeds = [
            {"id": "1", "title": "AI Guardrails", "text": "Prompt privacy, topic blocking, safety."},
            {"id": "2", "title": "Semantic Search", "text": "Use embeddings to retrieve relevant passages."},
            {"id": "3", "title": "Function Calling", "text": "Let the model trigger tools programmatically."},
        ]
    else:
        rows = _load_seed_data(csv_path)
        seeds = [{"id": r.get("id") or str(i + 1), "title": r.get("title", ""), "text": r.get("text", "")} for i, r in enumerate(rows)]

    ids = [s["id"] for s in seeds]
    docs = [f"{s['title']}\n{s['text']}".strip() for s in seeds]
    meta = [{"title": s["title"]} for s in seeds]
    col.add(ids=ids, documents=docs, metadatas=meta)


def semantic_query(question: str, data_dir: Path, persist_dir: Path, top_k: int = 3) -> str:
    client = _chroma_client(persist_dir)
    try:
        col = client.get_collection("kb_main")
    except Exception:
        ensure_kb_index(data_dir, persist_dir, "kb_main")
        col = client.get_collection("kb_main")

    q = col.query(query_texts=[question], n_results=top_k)
    docs = q.get("documents") or [[]]
    metas = q.get("metadatas") or [[]]
    pairs = list(zip(docs[0], metas[0]))
    if not pairs:
        return "I searched the knowledge base but found no matching passages."
    bullets = "\n".join([f"• {m.get('title', 'Note')}: {d[:200]}…" for d, m in pairs])
    return f"Here’s what I found:\n{bullets}\n\n(Answer synthesized from nearest passages.)"


# ---------- Service 3: Function Calling tools ----------
def tool_calculate(expr: str) -> str:
    try:
        allowed = set("0123456789+-*/(). ")
        if not set(expr) <= allowed:
            return "Calculator supports only + - * / and parentheses."
        result = eval(expr, {"__builtins__": {}}, {})
        return f"{expr} = {result}"
    except Exception:
        return "I couldn’t compute that expression."


def tool_convert(value: float, unit_from: str, unit_to: str) -> str:
    unit_from = unit_from.lower()
    unit_to = unit_to.lower()
    if unit_from == unit_to:
        return f"{value} {unit_from} equals {value} {unit_to}."
    if unit_from in ("c", "celsius") and unit_to in ("f", "fahrenheit"):
        return f"{value}°C = {round(value * 9 / 5 + 32, 2)}°F"
    if unit_from in ("f", "fahrenheit") and unit_to in ("c", "celsius"):
        return f"{value}°F = {round((value - 32) * 5 / 9, 2)}°C"
    if unit_from in ("km", "kilometer", "kilometers") and unit_to in ("mi", "mile", "miles"):
        return f"{value} km = {round(value * 0.621371, 3)} miles"
    if unit_from in ("mi", "mile", "miles") and unit_to in ("km", "kilometer", "kilometers"):
        return f"{value} miles = {round(value / 0.621371, 3)} km"
    return "Unsupported conversion. Try C↔F or km↔miles."
