"""Semantic retrieval service using Chroma persistence plus safe fallbacks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    import chromadb
except Exception:  # noqa: BLE001
    chromadb = None

from .llm import create_response, get_client
from .memory import build_messages


SERVICE_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = SERVICE_ROOT / "data" / "travel_knowledge.jsonl"
CHROMA_PATH = SERVICE_ROOT / "chroma_store"
COLLECTION_NAME = "tripsmith_travel_knowledge"


def _load_dataset() -> list[dict[str, Any]]:
    """Load local JSONL travel records used to populate semantic index."""
    records: list[dict[str, Any]] = []
    if not DATA_FILE.exists():
        return records
    for line in DATA_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


class GatewayEmbeddingFunction:
    """Adapter so Chroma can request embeddings from our gateway-configured client."""

    def __init__(self, model_name: str = "text-embedding-3-small") -> None:
        self._model_name = model_name
        self._client = get_client()

    def __call__(self, input: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self._model_name,
            input=input,
        )
        return [item.embedding for item in response.data]


class SemanticSearchService:
    """Manages persisted semantic collection and retrieval operations."""

    def __init__(self) -> None:
        self._records = _load_dataset()
        self.collection = None
        self._bootstrapped = False

        # If Chroma is unavailable, service still runs in keyword fallback mode.
        if chromadb is None:
            return

        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))

        try:
            embedding_function = GatewayEmbeddingFunction(
                model_name="text-embedding-3-small"
            )
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=embedding_function,
            )
        except Exception:  # noqa: BLE001
            # Keep semantic search available even if embeddings are unavailable.
            self.collection = None

    def _bootstrap_if_needed(self) -> None:
        """Populate collection once per process when it is empty."""
        if self._bootstrapped:
            return
        self._bootstrapped = True

        if self.collection is None:
            return

        if self.collection.count() > 0:
            return

        entries = self._records
        if not entries:
            return

        ids = [item["id"] for item in entries]
        docs = [item["text"] for item in entries]
        metadatas = [
            {
                "destination": item.get("destination", "unknown"),
                "topic": item.get("topic", "general"),
                "source": item.get("source", "local_kb"),
            }
            for item in entries
        ]
        self.collection.add(ids=ids, documents=docs, metadatas=metadatas)

    def query(self, user_query: str, n_results: int = 4) -> list[dict[str, Any]]:
        """Retrieve nearest context chunks; degrade to lexical matching on failure."""
        if self.collection is None:
            return _keyword_fallback_query(self._records, user_query, n_results)

        try:
            self._bootstrap_if_needed()
            total = self.collection.count()
            if total == 0:
                return []

            response = self.collection.query(
                query_texts=[user_query],
                n_results=min(max(1, n_results), total),
                include=["documents", "metadatas", "distances"],
            )

            docs = response.get("documents", [[]])[0]
            metas = response.get("metadatas", [[]])[0]
            distances = response.get("distances", [[]])[0]

            matches: list[dict[str, Any]] = []
            for idx, doc in enumerate(docs):
                matches.append(
                    {
                        "document": doc,
                        "metadata": metas[idx] if idx < len(metas) else {},
                        "distance": distances[idx] if idx < len(distances) else None,
                    }
                )
            return matches
        except Exception:  # noqa: BLE001
            return _keyword_fallback_query(self._records, user_query, n_results)


def _keyword_fallback_query(
    records: list[dict[str, Any]],
    user_query: str,
    n_results: int,
) -> list[dict[str, Any]]:
    """Simple lexical ranking used when vector search is unavailable."""
    query_terms = {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", user_query.lower())
        if len(token) > 2
    }
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in records:
        text = item.get("text", "").lower()
        score = sum(1 for term in query_terms if term in text)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = scored[: max(1, n_results)]
    return [
        {
            "document": item.get("text", ""),
            "metadata": {
                "destination": item.get("destination", "unknown"),
                "topic": item.get("topic", "general"),
                "source": item.get("source", "local_kb"),
            },
            "distance": None,
        }
        for _, item in top
    ]


_SEMANTIC_SERVICE: SemanticSearchService | None = None


def _get_service() -> SemanticSearchService:
    """Singleton accessor to avoid rebuilding collection each request."""
    global _SEMANTIC_SERVICE
    if _SEMANTIC_SERVICE is None:
        _SEMANTIC_SERVICE = SemanticSearchService()
    return _SEMANTIC_SERVICE


def _format_context(matches: list[dict[str, Any]]) -> str:
    """Flatten retrieved chunks into a prompt-friendly context block."""
    chunks: list[str] = []
    for idx, match in enumerate(matches, start=1):
        meta = match.get("metadata", {})
        chunks.append(
            (
                f"[Source {idx}] destination={meta.get('destination', 'unknown')}; "
                f"topic={meta.get('topic', 'general')}; source={meta.get('source', 'local_kb')}\n"
                f"{match.get('document', '')}"
            )
        )
    return "\n\n".join(chunks)


def handle_semantic_query(user_text: str, *, history: list[dict] | None = None) -> str:
    """Serve destination Q&A with retrieved context and short-term chat memory."""
    service = _get_service()
    try:
        matches = service.query(user_text, n_results=4)
    except Exception as exc:  # noqa: BLE001
        return (
            "I could not run semantic search right now. "
            f"Please try again in a moment. Details: {exc}"
        )

    if not matches:
        return (
            "I do not have enough travel knowledge for that question in my local dataset yet. "
            "Try asking about destinations like Tokyo, Rome, Lisbon, Barcelona, New York, or Reykjavik."
        )

    context_block = _format_context(matches)
    messages = build_messages(history=history, user_message=user_text, max_turns=8)

    instructions = (
        "You are TripSmith, a concise and practical travel consultant.\n"
        "Answer using the retrieved context below.\n"
        "If context is missing key details, say what is unknown instead of inventing.\n"
        "Use 1 short paragraph and a short bullet list if helpful.\n\n"
        "Retrieved context:\n"
        f"{context_block}"
    )

    try:
        response = create_response(instructions=instructions, input_items=messages)
        return response.output_text.strip()
    except Exception:  # noqa: BLE001
        top = matches[0]
        meta = top.get("metadata", {})
        return (
            f"From my travel notes on {meta.get('destination', 'this destination')}: "
            f"{top.get('document', '')}"
        )
