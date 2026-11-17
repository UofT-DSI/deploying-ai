"""Shared configuration and the LLM client (course API gateway)."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).parent
# Secrets live in 05_src/.secrets (same file used in the course notebooks). Never hard-code keys here.
load_dotenv(BASE_DIR.parent / ".secrets", override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("assignment_chat")

# ---- Gateway settings (same values that worked in Assignment 1). The key itself comes from .secrets ----
GATEWAY_BASE_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"
GATEWAY_HEADER = "x-api-key"

CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"

# ---- Paths ----
DATA_CSV = BASE_DIR / "data" / "destinations.csv"
CHROMA_PATH = BASE_DIR / "chroma_db"
COLLECTION_NAME = "destinations"


def get_client() -> OpenAI:
    if GATEWAY_BASE_URL.startswith("PASTE"):
        raise RuntimeError("Set GATEWAY_BASE_URL in config.py before running.")
    return OpenAI(
        base_url=GATEWAY_BASE_URL,
        api_key="not-used",  # the gateway key goes in the header instead
        default_headers={GATEWAY_HEADER: os.getenv("API_GATEWAY_KEY")},
    )


_client = None


def client() -> OpenAI:
    """Create the client lazily so that importing modules never fails."""
    global _client
    if _client is None:
        _client = get_client()
    return _client


def embed(texts: list[str]) -> list[list[float]]:
    """Embed texts through the gateway (used both for indexing and for queries)."""
    resp = client().embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]
