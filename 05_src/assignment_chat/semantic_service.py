from __future__ import annotations

import json
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from .config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    API_GATEWAY_KEY,
    DEFAULT_GATEWAY_BASE_URL,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    PITCHFORK_DOCUMENTS_DIR,
    get_openai_client_kwargs,
    has_openai_access,
)


def _load_jsonl_rows(path, text_key: str, id_key: str, topic: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except Exception:
                continue
            text = str(record.get(text_key, "")).strip()
            if not text:
                continue
            rows.append(
                {
                    "id": str(record.get(id_key, "")),
                    "topic": topic,
                    "text": text,
                }
            )
    return rows


def _load_pitchfork_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    jsonl_files = sorted(PITCHFORK_DOCUMENTS_DIR.glob("pitchfork_*.jsonl"))
    if not jsonl_files:
        return rows

    for path in jsonl_files:
        stem = path.stem.lower()

        if stem == "pitchfork_content":
            rows.extend(
                _load_jsonl_rows(
                    path=path,
                    text_key="content",
                    id_key="reviewid",
                    topic="pitchfork_content",
                )
            )
            continue

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    continue

                review_id = str(record.get("reviewid", "")).strip()
                if not review_id:
                    continue

                text_parts: list[str] = []
                for key in ("artist", "genre", "label", "title", "author", "pub_date", "year"):
                    value = record.get(key)
                    if value is None:
                        continue
                    value_text = str(value).strip()
                    if value_text:
                        text_parts.append(f"{key}: {value_text}")

                score = record.get("score")
                if score is not None:
                    text_parts.append(f"score: {score}")

                if not text_parts:
                    continue

                rows.append(
                    {
                        "id": f"{stem}:{review_id}",
                        "topic": stem,
                        "text": "; ".join(text_parts),
                    }
                )

    return rows


def _active_dataset() -> tuple[list[dict[str, str]], str]:
    pitchfork_rows = _load_pitchfork_rows()
    return pitchfork_rows, "05_src/documents/pitchfork_*.jsonl"


def _get_embedding_function() -> OpenAIEmbeddingFunction | None:
    if not has_openai_access():
        return None

    client_kwargs = get_openai_client_kwargs()
    api_key = client_kwargs.get("api_key") or OPENAI_API_KEY or "any_value"
    api_base = client_kwargs.get("base_url") or OPENAI_BASE_URL
    if not api_base and API_GATEWAY_KEY:
        api_base = DEFAULT_GATEWAY_BASE_URL

    emb_kwargs: dict[str, Any] = {
        "api_key": api_key,
        "model_name": EMBEDDING_MODEL,
    }
    if api_base:
        emb_kwargs["api_base"] = api_base
    if API_GATEWAY_KEY:
        emb_kwargs["default_headers"] = {"x-api-key": API_GATEWAY_KEY}
    return OpenAIEmbeddingFunction(**emb_kwargs)


def _prepare_documents() -> list[dict[str, Any]]:
    rows, source_path = _active_dataset()
    return [
        {
            "id": row["id"] or f"row_{index}",
            "source": source_path,
            "chunk": index,
            "topic": row["topic"],
            "text": row["text"],
        }
        for index, row in enumerate(rows)
    ]


def build_or_refresh_index(force: bool = False) -> str:
    records = _prepare_documents()
    if not records:
        return "No Pitchfork JSONL records were found in 05_src/documents."

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
    embedding_function = _get_embedding_function()

    if embedding_function is not None:
        try:
            collection = chroma.get_collection(name=COLLECTION_NAME, embedding_function=embedding_function)
        except chromadb.errors.NotFoundError:
            collection = chroma.create_collection(name=COLLECTION_NAME, embedding_function=embedding_function)
        except ValueError:
            collection = chroma.get_collection(name=COLLECTION_NAME)
    else:
        collection = chroma.get_or_create_collection(name=COLLECTION_NAME)

    if force:
        existing = collection.get(include=[])
        existing_ids = existing.get("ids", []) if existing else []
        if existing_ids:
            collection.delete(ids=existing_ids)

    ids = [row["id"] for row in records]
    texts = [row["text"] for row in records]
    metadatas = [
        {"source": row["source"], "chunk": row["chunk"], "topic": row["topic"]}
        for row in records
    ]

    try:
        collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
    except Exception:
        return f"Prepared {len(records)} dataset records; semantic indexing is temporarily unavailable."

    if embedding_function is None:
        source = records[0]["source"] if records else "dataset"
        return f"Prepared {len(records)} records from {source}; running in lexical fallback mode until OpenAI access is available."

    source = records[0]["source"] if records else "dataset"
    return f"Indexed {len(records)} records from {source} into persistent ChromaDB."


def _lexical_search(query: str, limit: int = 4) -> list[dict[str, Any]]:
    query_terms = {term.lower() for term in query.split() if term.strip()}
    if not query_terms:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    for row in _prepare_documents():
        text = row.get("text", "").lower()
        score = sum(1 for term in query_terms if term in text)
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [pair[1] for pair in scored[:limit]]


def semantic_or_hybrid_search(query: str, limit: int = 4) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    if not has_openai_access():
        return _lexical_search(query, limit=limit)

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
    embedding_function = _get_embedding_function()
    try:
        collection = chroma.get_collection(name=COLLECTION_NAME, embedding_function=embedding_function)
    except Exception:
        build_or_refresh_index(force=False)
        collection = chroma.get_collection(name=COLLECTION_NAME, embedding_function=embedding_function)

    count = collection.count()
    if count == 0:
        build_or_refresh_index(force=False)

    try:
        result = collection.query(
            query_texts=[query],
            n_results=limit,
            include=["documents", "metadatas"],
        )
    except Exception:
        return _lexical_search(query, limit=limit)

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]

    items = []
    for doc, meta in zip(documents, metadatas):
        items.append(
            {
                "text": doc,
                "source": (meta or {}).get("source", "unknown"),
                "chunk": (meta or {}).get("chunk", -1),
            }
        )

    return items if items else _lexical_search(query, limit=limit)


def answer_from_course_materials(question: str) -> str:
    matches = semantic_or_hybrid_search(question, limit=4)
    if not matches:
        return "I couldn’t find relevant content in the Service 2 dataset yet. Try running /reindex first."

    snippets = []
    sources = []
    for row in matches:
        text = " ".join(row["text"].split())
        snippets.append(f"- {text[:260]}...")
        sources.append(f"- {row['source']}")

    unique_sources = sorted(set(sources))

    return (
        "Here are the most relevant points from the Service 2 dataset:\n"
        + "\n".join(snippets)
        + "\n\nSources:\n"
        + "\n".join(unique_sources)
    )
