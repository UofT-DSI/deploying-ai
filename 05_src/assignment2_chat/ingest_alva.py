"""One-time ChromaDB ingestion for Alva Service 2.

From 05_src/, run: python -m assignment2_chat.ingest_alva
Adapted from the DSI 04_5_vectordb.ipynb class example.
"""



import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

import os
from dotenv import load_dotenv

from pathlib import Path
import re


APP_DIR = Path(__file__).resolve().parent
SRC_DIR = APP_DIR.parent
DOCS_DIR = APP_DIR / "documents" / "alva"
DB_DIR = APP_DIR / "chroma" / "alva_knowledge"

load_dotenv(SRC_DIR / ".env")
load_dotenv(SRC_DIR / ".secrets")
load_dotenv(APP_DIR / ".secrets")

gateway_key = os.getenv("API_GATEWAY_KEY")
if not gateway_key:
    raise RuntimeError("API_GATEWAY_KEY not found in environment or 05_src/.secrets")

embedding_function = OpenAIEmbeddingFunction(
    model_name="text-embedding-3-small",
    api_key="any value",  # DSI gateway uses x-api-key belowapi_key="any value",
    api_base="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
    default_headers={"x-api-key": gateway_key},
)

chroma = chromadb.PersistentClient(path=str(DB_DIR))

collection = chroma.get_or_create_collection(
    name="alva_workforce_readiness",
    embedding_function=embedding_function,
)


def document_metadata(content: str, filename: str) -> dict:
    title_match = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)

    
    source_match = re.search(
        r"^\*\*Primary source\(s\):\*\*\s*(.+)$",
        content,
        flags=re.MULTILINE
    )

    urls = re.findall(r"https?://[^\s)]+", content)

    return {
        "filename": filename,
        "title": title_match.group(1).strip() if title_match else filename,
        "source": source_match.group(1).strip() if source_match else "Unknown",
        "url": urls[0].rstrip(".,") if urls else "",
    }


def split_document(content: str, max_chars: int = 1200) -> list[str]:
    chunks = []

    sections = re.split(
        r"(?=^##\s+)",
        content.strip(),
        flags=re.MULTILINE,
    )

    for section in sections:
        section = section.strip()

        if not section:
            continue

        if len(section) <= max_chars:
            chunks.append(section)
            continue

        paragraphs = re.split(
            r"\n\s*\n",
            section,
        )

        current = ""

        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) + 2 > max_chars:
                chunks.append(current.strip())
                current = ""

            if len(paragraph) > max_chars:
                if current:
                    chunks.append(current.strip())
                    current = ""

                for start in range(0, len(paragraph), max_chars):
                    chunks.append(paragraph[start:start + max_chars])
            else:
                current += ("\n\n" if current else "") + paragraph

        if current:
            chunks.append(current.strip())

    return chunks


def prepare_documents() -> tuple[list[str], list[str], list[dict]]:
    if not DOCS_DIR.is_dir():
        raise FileNotFoundError(
            f"Missing {DOCS_DIR}. Place the 10 Markdown files there first."
        )

    ids, documents, metadatas = [], [], []

    # NEW: Ignore README.md, which describes the knowledge base but is not a source.
    for file in sorted(DOCS_DIR.glob("*.md")):
        if file.name.lower() == "readme.md":
            continue

        content = file.read_text(encoding="utf-8")
        metadata = document_metadata(content, file.name)

        for i, chunk in enumerate(split_document(content)):
            ids.append(f"{file.stem}_{i:03d}")
            documents.append(chunk)
            metadatas.append({**metadata, "chunk_index": i})

    if not documents:
        raise ValueError(f"No Markdown documents found in {DOCS_DIR}")

    return ids, documents, metadatas


def main() -> None:
    ids, documents, metadatas = prepare_documents()

    filenames = {meta["filename"] for meta in metadatas}
    print(
        f"Preparing {len(documents)} passages from "
        f"{len(filenames)} source files."
    )

    # EDIT: upsert() instead of notebook add(),
    # so rerunning updates existing IDs.
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"Saved collection '{collection.name}' to: {DB_DIR}")
    print(f"Stored passages: {collection.count()}")

    # NEW: Test a semantic query.
    results = collection.query(
        query_texts=["How can managers support employee adoption of AI?"],
        n_results=min(3, collection.count()),
        include=["documents", "metadatas"],
    )

    print("Sample retrieval:")

    for meta in results["metadatas"][0]:
        print(f" - {meta.get('title')} ({meta.get('filename')})")


if __name__ == "__main__":
    main()