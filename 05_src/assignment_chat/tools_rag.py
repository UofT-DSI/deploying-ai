# Service 2: Semantic Search over ai_report_2025.pdf
# Adapted from:
#   - course_chat/tools_music.py  (tool structure + get_context pattern)
#   - 04_5_vectordb.ipynb         (PersistentClient, OpenAIEmbeddingFunction)
#   - 04_8_hybrid_rag.ipynb       (keyword filter via where_document)

import os
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from langchain.tools import tool
from dotenv import load_dotenv
from utils.logger import get_logger

load_dotenv(".env")
load_dotenv(".secrets")

_logs = get_logger(__name__)

CHROMA_PATH = os.path.join("assignment_chat", "chroma_db")
COLLECTION  = "ai_report"
EMBED_MODEL = "text-embedding-3-small"


def _get_collection() -> chromadb.api.models.Collection:
    """
    Open the persistent ChromaDB collection.
    Uses PersistentClient (file-based) as required by the assignment spec.
    Supports both direct OpenAI key and API gateway, same as utils/clients.py.
    """
    use_gateway = os.getenv("USE_GATEWAY", "FALSE").upper() == "TRUE"

    if use_gateway:
        embedding_fn = OpenAIEmbeddingFunction(
            api_key="any value",
            api_base="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
            model_name=EMBED_MODEL,
            default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
        )
    else:
        embedding_fn = OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=EMBED_MODEL,
        )

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(name=COLLECTION, embedding_function=embedding_fn)


# Load collection once at import time (same pattern as tools_music.py)
_collection = _get_collection()


@tool
def search_ai_report(query: str, n_results: int = 3) -> str:
    """
    Searches the AI Report 2025 document for content relevant to the query.
    Use this tool to answer questions about AI trends, models, applications,
    industry developments, and research findings from the 2025 AI report.
    Returns the top n_results most relevant passages.
    """
    _logs.debug(f"RAG query: {query}")
    context = _get_context(query, n_results)
    _logs.debug(f"RAG returned {len(context)} chunks")
    return context


def _get_context(query: str, n_results: int) -> str:
    """
    Query ChromaDB and return relevant chunks as a single string.
    Adapted from get_context_data() in 04_8_hybrid_rag.ipynb.
    Uses where_document keyword filter when query contains specific terms
    (hybrid approach: lexical pre-filter + vector ranking).
    """
    keyword = _extract_keyword(query)

    kwargs = dict(query_texts=[query], n_results=n_results)

    # Hybrid RAG: add keyword filter if a useful term was found
    # Same where_document pattern from 04_8_hybrid_rag.ipynb Section 2
    if keyword:
        kwargs["where_document"] = {"$contains": keyword}
        _logs.debug(f"Keyword filter applied: '{keyword}'")

    try:
        results = _collection.query(**kwargs)
    except Exception:
        # Fallback to pure vector search if keyword filter returns no results
        _logs.debug("Keyword filter returned no results, falling back to vector search")
        results = _collection.query(query_texts=[query], n_results=n_results)

    chunks = results.get("documents", [[]])[0]
    if not chunks:
        return "No relevant information found in the AI Report 2025."

    # Format chunks with numbering, same style as generate_prompt() in 04_8
    formatted = "\n\n".join(
        f"[Passage {i+1}]: {chunk}" for i, chunk in enumerate(chunks)
    )
    return formatted


def _extract_keyword(query: str) -> str:
    """
    Extract a single meaningful keyword from the query for the hybrid filter.
    Checks for known AI-domain terms that are worth filtering on literally.
    Returns empty string if no useful keyword found (falls back to pure vector).
    """
    ai_terms = [
        "transformer", "llm", "gpt", "claude", "gemini", "mistral",
        "fine-tuning", "finetuning", "rag", "retrieval", "embedding",
        "agent", "multimodal", "benchmark", "hallucination", "inference",
        "open source", "regulation", "safety", "alignment", "reasoning",
    ]
    query_lower = query.lower()
    for term in ai_terms:
        if term in query_lower:
            return term
    return ""
