import os
import json
import requests
import chromadb
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load secrets
load_dotenv(Path(__file__).parent.parent / ".secrets")

# Gateway client, same as build_embeddings.py
client = OpenAI(
    base_url='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1',
    api_key='any value',
    default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')}
)

chroma = chromadb.PersistentClient(path="./chroma_db")
collection = chroma.get_collection("production_ai")

# Service 1: API Calls - Open-Meteo, free, no key
def get_weather(city="Toronto"):
    coords = {"Toronto": (43.65, -79.38), "Beijing": (39.9, 116.4), "London": (51.5, -0.12)}
    lat, lon = coords.get(city, (43.65, -79.38))
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m"
    data = requests.get(url).json()
    temp = data["current"]["temperature_2m"]
    wind = data["current"]["wind_speed_10m"]
    # Return raw data for LLM to rewrite, not verbatim to user
    return f"In {city}, temperature is {temp} C, wind speed is {wind} km/h."

# Service 2: Semantic Query - ChromaDB
def search_knowledge(query):
    emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding
    res = collection.query(query_embeddings=[emb], n_results=3)
    return "\n".join(res["documents"][0])

# Service 3: Function Calling - tools for LLM to choose
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search knowledge about production AI, caching, routing, guardrails",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        }
    }
]