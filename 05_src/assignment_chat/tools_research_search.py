
"""Semantic search over indexed ArXiv research papers."""

import os
from functools import lru_cache

import chromadb
from dotenv import load_dotenv
from langchain_core.tools import tool
from openai import OpenAI

from assignment_chat.build_index import (
    ROOT,
    INDEX_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
)

load_dotenv(ROOT / ".secrets")


@lru_cache(maxsize=1)
def get_collection():
    """Connect to the persisted research-paper collection."""

    client = chromadb.PersistentClient(
        path=str(INDEX_DIR)
    )

    return client.get_collection(
        name=COLLECTION_NAME
    )


def retrieve_passages(
    question: str,
    top_k: int = 4,
) -> list[dict]:
    """Find the most semantically relevant paper passages."""

    if not question.strip():
        raise ValueError("A research question is required")

    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing")

    collection = get_collection()

    if collection.count() == 0:
        return []

    client = OpenAI()

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=question.strip(),
    )

    query_embedding = response.data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    passages = []

    for text, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        passages.append({
            "text": text,
            "title": metadata["title"],
            "arxiv_id": metadata["arxiv_id"],
            "page": metadata["page"],
            "source": metadata["source"],
            "distance": distance,
        })

    return passages


@tool
def search_research_papers(
    question: str,
    top_k: int = 4,
) -> list[dict]:
    """Search the full text of indexed academic papers.

    Use this tool to answer questions about paper findings,
    methodologies, architectures, experiments, and conclusions.
    Unlike OpenAlex, this searches actual PDF passages.
    """
    return retrieve_passages(question, top_k)
