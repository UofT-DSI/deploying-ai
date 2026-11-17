
"""Build the ResearchMate AI research-paper vector index."""

import hashlib
import os
import time
from pathlib import Path

import chromadb
import requests
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

load_dotenv(ROOT / ".secrets")

PAPERS_DIR = HERE / "data" / "papers"
INDEX_DIR = HERE / "research_index"

COLLECTION_NAME = "research_papers"
EMBEDDING_MODEL = "text-embedding-3-small"

PAPERS = {
    "1706.03762": "Attention Is All You Need",
    "2005.11401": (
        "Retrieval-Augmented Generation for "
        "Knowledge-Intensive NLP Tasks"
    ),
    "2307.03172": (
        "Lost in the Middle: How Language "
        "Models Use Long Contexts"
    ),
}


def download_paper(arxiv_id: str) -> Path:
    """Download an ArXiv PDF if it is not already cached."""

    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    destination = PAPERS_DIR / f"{arxiv_id}.pdf"

    if destination.exists():
        return destination

    url = f"https://arxiv.org/pdf/{arxiv_id}"

    response = requests.get(
        url,
        timeout=60,
        headers={"User-Agent": "ResearchMateAI/1.0"},
    )
    response.raise_for_status()

    # Check that the response is actually a PDF.
    if not response.content.startswith(b"%PDF"):
        raise ValueError(f"Invalid PDF response: {arxiv_id}")

    destination.write_bytes(response.content)

    return destination


def extract_pages(pdf_path: Path) -> list[dict]:
    """Extract text from individual PDF pages."""

    reader = PdfReader(str(pdf_path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            pages.append({
                "page": page_number,
                "text": " ".join(text.split()),
            })

    return pages


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[str]:
    """Split text into overlapping character-based chunks."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if not 0 <= overlap < chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size"
        )

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def prepare_documents() -> list[dict]:
    """Download papers and prepare chunks with source metadata."""

    documents = []

    for arxiv_id, title in PAPERS.items():
        print(f"Processing: {title}")

        pdf_path = download_paper(arxiv_id)
        pages = extract_pages(pdf_path)

        for page in pages:
            chunks = chunk_text(page["text"])

            for chunk_number, text in enumerate(chunks):
                unique_key = (
                    f"{arxiv_id}:{page['page']}:{chunk_number}"
                )

                chunk_id = hashlib.sha256(
                    unique_key.encode("utf-8")
                ).hexdigest()

                documents.append({
                    "id": chunk_id,
                    "text": text,
                    "metadata": {
                        "title": title,
                        "arxiv_id": arxiv_id,
                        "page": page["page"],
                        "source": (
                            f"https://arxiv.org/abs/{arxiv_id}"
                        ),
                    },
                })

    return documents


def embed_texts(
    texts: list[str],
    client: OpenAI,
    batch_size: int = 50,
) -> list[list[float]]:
    """Generate OpenAI embeddings in batches."""

    embeddings = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )

        ordered = sorted(
            response.data,
            key=lambda item: item.index,
        )

        embeddings.extend(
            item.embedding for item in ordered
        )

        print(
            f"Embedded {min(start + batch_size, len(texts))}"
            f"/{len(texts)} chunks"
        )

    return embeddings


def build_index():
    """Create and persist the ChromaDB research index."""

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing")

    openai_client = OpenAI()

    chroma_client = chromadb.PersistentClient(
        path=str(INDEX_DIR)
    )

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    documents = prepare_documents()

    if not documents:
        raise RuntimeError("No PDF text was extracted")

    # Only embed chunks not already in the collection.
    existing_ids = set(
        collection.get(include=[])["ids"]
    )

    new_documents = [
        doc for doc in documents
        if doc["id"] not in existing_ids
    ]

    if not new_documents:
        print("All chunks are already indexed.")
        return

    # Process in small batches to limit memory and API usage.
    batch_size = 50

    for start in range(0, len(new_documents), batch_size):
        batch = new_documents[start:start + batch_size]

        embeddings = embed_texts(
            [doc["text"] for doc in batch],
            openai_client,
            batch_size=batch_size,
        )

        collection.upsert(
            ids=[doc["id"] for doc in batch],
            documents=[doc["text"] for doc in batch],
            metadatas=[doc["metadata"] for doc in batch],
            embeddings=embeddings,
        )

        print(f"Indexed {collection.count()} total chunks")

    print("Research index build completed.")


if __name__ == "__main__":
    build_index()
