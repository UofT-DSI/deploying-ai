from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from openai import OpenAI


@dataclass
class RetrievedDoc:
    doc_id: str
    text: str
    score: float


class SemanticStore:
    def __init__(self, persist_dir: str, collection_name: str, openai_client: OpenAI):
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.col = self.client.get_or_create_collection(collection_name)
        self.oai = openai_client

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self.oai.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        return [d.embedding for d in resp.data]

    def add_documents(self, docs: list[dict[str, Any]], batch_size: int = 32) -> None:
        # Basic validation (prevents weird failures)
        seen = set()
        for d in docs:
            if "id" not in d or "text" not in d:
                raise ValueError("Each doc must contain 'id' and 'text'")
            if not isinstance(d["id"], str) or len(d["id"]) < 1:
                raise ValueError("Doc 'id' must be a non-empty string")
            if d["id"] in seen:
                raise ValueError(f"Duplicate doc id: {d['id']}")
            seen.add(d["id"])

        # Batch inserts (stability improvement on Windows)
        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            ids = [d["id"] for d in batch]
            texts = [d["text"] for d in batch]
            metas = [{"source": d.get("source", ""), "title": d.get("title", "")} for d in batch]

            embs = self.embed(texts)
            self.col.add(ids=ids, documents=texts, metadatas=metas, embeddings=embs)

            # progress marker
            if (i // batch_size) % 5 == 0:
                print(f"Added {min(i + batch_size, len(docs))}/{len(docs)} docs")

    def search(self, query: str, k: int = 4) -> list[RetrievedDoc]:
        q_emb = self.embed([query])[0]
        res = self.col.query(
            query_embeddings=[q_emb],
            n_results=k,
            include=["documents", "distances"],  # <-- no "ids" here
        )
        print("Retrieved ids:", res.get("ids", [[]])[0])
        print("Top distances:", res.get("distances", [[]])[0])
        docs = res.get("documents", [[]])[0]
        dists = res.get("distances", [[]])[0]
        ids = res.get("ids", [[]])[0]  # ids still returned by default

        out: list[RetrievedDoc] = []
        for doc_id, text, dist in zip(ids, docs, dists):
            score = float(1.0 / (1.0 + float(dist)))
            out.append(RetrievedDoc(doc_id=str(doc_id), text=str(text), score=score))
        
        return out


def load_jsonl(path: str) -> list[dict]:
    docs: list[dict] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            docs.append(json.loads(line))
    return docs