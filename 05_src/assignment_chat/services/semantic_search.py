import os
import json
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings

from ..llm import get_client

PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_store")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "handbook.jsonl")
COLLECTION_NAME = "ai_handbook"

def _load_docs() -> List[Dict[str, Any]]:
    docs = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            docs.append(json.loads(line))
    return docs

def _embed_texts(texts: List[str]) -> List[List[float]]:
    client = get_client()
    emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [d.embedding for d in emb.data]

def get_collection():
    os.makedirs(PERSIST_DIR, exist_ok=True)
    chroma = chromadb.PersistentClient(path=PERSIST_DIR, settings=Settings(allow_reset=False))
    return chroma.get_or_create_collection(name=COLLECTION_NAME)

def ensure_index_built() -> None:
    col = get_collection()
    if col.count() > 0:
        return

    docs = _load_docs()
    ids = [d["id"] for d in docs]
    texts = [d["text"] for d in docs]
    metas = [{"source": d.get("source", ""), "title": d.get("title", "")} for d in docs]

    vectors = _embed_texts(texts)
    col.add(ids=ids, documents=texts, metadatas=metas, embeddings=vectors)

def semantic_answer(query: str, k: int = 4) -> str:
    ensure_index_built()
    col = get_collection()

    qvec = _embed_texts([query])[0]
    res = col.query(query_embeddings=[qvec], n_results=k, include=["documents", "metadatas"])

    docs = res["documents"][0]
    metas = res["metadatas"][0]

    context = "\n\n".join([f"[{m.get('title','')}] {d}" for d, m in zip(docs, metas)])

    client = get_client()
    dev = (
        "You answer questions using the provided retrieved context. "
        "If the context is insufficient, say so and suggest a better query. "
        "Tone: comically bureaucratic, but clear."
    )
    user = f"Question: {query}\n\nRetrieved context:\n{context}"
    resp = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "developer", "content": dev},
            {"role": "user", "content": user},
        ],
    )
    return resp.output[0].content[0].text