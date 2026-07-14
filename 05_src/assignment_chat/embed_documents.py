# One-time script to embed ai_report_2025.pdf into a persistent ChromaDB.
# Run once from 05_src/:
#   python -m assignment_chat.embed_documents
#
# Adapted from 04_5_vectordb.ipynb and 04_6_embeddings_at_scale.ipynb.
# Uses the same OpenAIEmbeddingFunction pattern from class.

import os
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from pypdf import PdfReader
from dotenv import load_dotenv
from utils.logger import get_logger

load_dotenv(".env")
load_dotenv(".secrets")

_logs = get_logger(__name__)

PDF_PATH      = os.path.join("..", "02_activities", "documents", "ai_report_2025.pdf")
CHROMA_PATH   = os.path.join("assignment_chat", "chroma_db")
COLLECTION    = "ai_report"
EMBED_MODEL   = "text-embedding-3-small"
CHUNK_SIZE    = 5          # sentences per chunk, same approach as 0_data_prep.ipynb


def extract_chunks(pdf_path: str, chunk_size: int) -> list[str]:
    """
    Read every page of the PDF and split into chunks of `chunk_size` sentences.
    Adapted from the paragraph-splitting logic in 0_data_prep.ipynb.
    """
    import re
    reader = PdfReader(pdf_path)
    full_text = " ".join(page.extract_text() or "" for page in reader.pages)
    full_text = full_text.replace("\n", " ")

    # Split on sentence-ending punctuation, same regex as 0_data_prep.ipynb
    sentences = re.split(r'(?<=[.!?])\s+', full_text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    chunks = []
    for i in range(0, len(sentences), chunk_size):
        chunk = " ".join(sentences[i:i + chunk_size])
        chunks.append(chunk)

    _logs.info(f"Extracted {len(sentences)} sentences -> {len(chunks)} chunks")
    return chunks


def build_collection(chunks: list[str], chroma_path: str, collection_name: str):
    """
    Create a persistent ChromaDB collection and add all chunks.
    Uses OpenAIEmbeddingFunction exactly as shown in 04_5_vectordb.ipynb.
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

    # PersistentClient = file-based ChromaDB required by assignment spec
    client = chromadb.PersistentClient(path=chroma_path)

    # Delete existing collection so re-runs start clean
    existing = [c.name for c in client.list_collections()]
    if collection_name in existing:
        client.delete_collection(collection_name)
        _logs.info(f"Deleted existing collection: {collection_name}")

    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
    )

    ids = [f"chunk_{i}" for i in range(len(chunks))]

    # Add in batches of 100 to avoid hitting API limits
    # Same batching approach as 04_6_embeddings_at_scale.ipynb
    batch_size = 100
    for start in range(0, len(chunks), batch_size):
        batch_chunks = chunks[start:start + batch_size]
        batch_ids    = ids[start:start + batch_size]
        collection.add(documents=batch_chunks, ids=batch_ids)
        _logs.info(f"Embedded chunks {start} – {start + len(batch_chunks) - 1}")

    _logs.info(f"Collection '{collection_name}' ready with {collection.count()} chunks")


if __name__ == "__main__":
    _logs.info(f"Reading PDF: {PDF_PATH}")
    chunks = extract_chunks(PDF_PATH, CHUNK_SIZE)
    build_collection(chunks, CHROMA_PATH, COLLECTION)
    _logs.info("Done. ChromaDB saved to: " + CHROMA_PATH)
