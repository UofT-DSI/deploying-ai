# services/mitre_search_service.py — Service 2: Semantic Search via ChromaDB

import os
import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_DB_DIR, CHROMA_COLLECTION_NAME, TOP_K_RESULTS, OPENAI_API_KEY, GATEWAY_URL, GATEWAY_HEADERS

# --- Load the persistent ChromaDB client (embeddings already generated) ---
_client = None
_collection = None


def _get_collection():
    """Load the persisted ChromaDB collection (created by build_embeddings.py)."""
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            api_base=GATEWAY_URL,
            model_name="text-embedding-3-small",
            default_headers=GATEWAY_HEADERS,
        )
        _collection = _client.get_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=ef,
        )
    return _collection


def search_mitre(query: str, top_k: int = TOP_K_RESULTS) -> dict:
    """
    Perform a semantic search over MITRE ATT&CK techniques.

    Returns structured results (not formatted text — the LLM will format it).
    """
    collection = _get_collection()

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for i in range(len(results["ids"][0])):
        hits.append({
            "technique_id": results["metadatas"][0][i].get("technique_id", ""),
            "name": results["metadatas"][0][i].get("name", ""),
            "tactics": results["metadatas"][0][i].get("tactics", ""),
            "snippet": results["documents"][0][i][:300],  # first 300 chars
        })

    return {
        "query": query,
        "top_k": top_k,
        "results": hits,
    }
