from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSIGNMENT_ROOT = Path(__file__).resolve().parent

load_dotenv(str(PROJECT_ROOT / "05_src" / ".env"))
load_dotenv(str(PROJECT_ROOT / "05_src" / ".secrets"))

LABS_DIR = PROJECT_ROOT / "01_materials" / "labs"
SLIDES_DIR = PROJECT_ROOT / "01_materials" / "slides"

CHROMA_DIR = ASSIGNMENT_ROOT / "chroma_store"
COLLECTION_NAME = "service2_semantic_collection"
PITCHFORK_DOCUMENTS_DIR = PROJECT_ROOT / "05_src" / "documents"

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
MAX_HISTORY_TURNS = int(os.getenv("ASSIGNMENT_CHAT_MAX_TURNS", "10"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_GATEWAY_KEY = os.getenv("API_GATEWAY_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
WEATHERSTACK_API_KEY = os.getenv("WEATHERSTACK_API_KEY")
DEFAULT_GATEWAY_BASE_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"

SYSTEM_PROMPT = (
    "You are Nova, a practical study companion for the Deploying AI course. "
    "Your tone is concise, encouraging, and concrete. "
    "Offer actionable steps and brief examples when useful."
)


def get_openai_client_kwargs() -> dict:
    base_url = OPENAI_BASE_URL
    if not base_url and API_GATEWAY_KEY:
        base_url = DEFAULT_GATEWAY_BASE_URL

    api_key = OPENAI_API_KEY
    if not api_key and API_GATEWAY_KEY:
        api_key = "any_value"

    kwargs = {}
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    if API_GATEWAY_KEY:
        kwargs["default_headers"] = {"x-api-key": API_GATEWAY_KEY}
    return kwargs


def has_openai_access() -> bool:
    return bool(OPENAI_API_KEY or API_GATEWAY_KEY)


def get_weatherstack_api_key() -> str | None:
    return WEATHERSTACK_API_KEY
