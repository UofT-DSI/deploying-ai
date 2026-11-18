"""Query the included course-material index without a database server."""

import json
import re
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

import chromadb
import numpy as np
from langchain.tools import tool
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

HERE = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def search_assets():
    model = json.loads((HERE / "search_model.json").read_text(encoding="utf-8"))
    client = chromadb.PersistentClient(path=str(HERE / "index"))
    return model, client.get_collection("course_materials")


def embed_query(query: str, model: dict) -> list[float]:
    tokens = [word for word in re.findall(r"(?u)\b\w\w+\b", query.lower()) if word not in ENGLISH_STOP_WORDS]
    terms = tokens + [f"{a} {b}" for a, b in pairwise(tokens)]
    vector = np.zeros(len(model["vocabulary"]), dtype=float)
    for term in terms:
        if term in model["vocabulary"]:
            vector[model["vocabulary"][term]] += 1
    vector *= np.asarray(model["idf"])
    length = np.linalg.norm(vector)
    if length:
        vector /= length
    return (np.asarray(model["components"]) @ vector).tolist()


@tool
def search_course_materials(question: str) -> str:
    """Find relevant passages in the included course and assignment documents."""
    model, collection = search_assets()
    embedding = embed_query(question, model)
    if not any(embedding):
        return "No matching course passage was found."
    result = collection.query(query_embeddings=[embedding], n_results=4,
                              include=["documents", "metadatas", "distances"])
    passages = []
    for text, metadata in zip(result["documents"][0], result["metadatas"][0]):
        passages.append(f"{metadata['source']}: {text[:500]}")
    return "\n\n".join(passages)
