"""
One-time indexing script: indexes course material into ChromaDB 'course_material' collection.

Run from 05_src/ directory:
    python -m course_chat.index_course_material

Prerequisites:
    - ChromaDB running (CHROMA_URL env var, default: localhost)
    - OPENAI_API_KEY set (used by the embedding function)
"""
import json
import os
import sys
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

from utils.logger import get_logger

load_dotenv()
load_dotenv(".secrets")

_logs = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Source directories: (doc_type, base_dir, glob_pattern)
SOURCES = [
    ("notebook",   REPO_ROOT / "01_materials" / "labs",                        "*.ipynb"),
    ("slide",      REPO_ROOT / "03_instructional_team" / "markdown_slides",    "*.md"),
    ("assignment", REPO_ROOT / "02_activities",                                "*.ipynb"),
    ("assignment", REPO_ROOT / "02_activities",                                "*.md"),
    ("source",     REPO_ROOT / "05_src" / "course_chat",                       "*.py"),
]

COLLECTION_NAME = "course_material"
EMBEDDING_MODEL = "text-embedding-3-small"
MIN_CHUNK_CHARS = 80
MAX_CHUNK_CHARS = 1500
BATCH_SIZE = 500


def _chunk_notebook(path: Path, rel_path: str, doc_type: str) -> list[dict]:
    """One chunk per substantive cell; long cells are split at line boundaries."""
    with open(path, encoding="utf-8") as f:
        nb = json.load(f)

    chunks: list[dict] = []
    for cell_idx, cell in enumerate(nb.get("cells", [])):
        source = "".join(cell.get("source", []))
        if len(source) < MIN_CHUNK_CHARS:
            continue
        cell_type = cell.get("cell_type", "")
        base_meta = {"source": rel_path, "type": doc_type,
                     "title": path.stem, "cell_type": cell_type}

        if len(source) <= MAX_CHUNK_CHARS:
            chunks.append({"id": f"{rel_path}:{cell_idx}:0",
                           "text": source.strip(), "metadata": base_meta})
            continue

        # Split long cells at newlines
        lines = source.split("\n")
        buf = ""
        sub = 0
        for line in lines:
            if buf and len(buf) + len(line) > MAX_CHUNK_CHARS:
                chunks.append({"id": f"{rel_path}:{cell_idx}:{sub}",
                               "text": buf.strip(), "metadata": base_meta})
                buf = line + "\n"
                sub += 1
            else:
                buf += line + "\n"
        if buf.strip():
            chunks.append({"id": f"{rel_path}:{cell_idx}:{sub}",
                           "text": buf.strip(), "metadata": base_meta})
    return chunks


def _chunk_python(path: Path, rel_path: str, doc_type: str) -> list[dict]:
    """Split Python source into function/class-level chunks."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    chunks: list[dict] = []
    block_lines: list[str] = []
    block_heading = path.stem
    block_start = 0

    for i, line in enumerate(lines):
        is_def = line.startswith(("def ", "class ", "async def "))
        if is_def and block_lines:
            content = "\n".join(block_lines).strip()
            if len(content) >= MIN_CHUNK_CHARS:
                chunks.append({
                    "id": f"{rel_path}:{block_start}:0",
                    "text": content[:MAX_CHUNK_CHARS],
                    "metadata": {"source": rel_path, "type": doc_type, "title": block_heading},
                })
            block_heading = line.strip()
            block_start = i
            block_lines = [line]
        else:
            block_lines.append(line)

    if block_lines:
        content = "\n".join(block_lines).strip()
        if len(content) >= MIN_CHUNK_CHARS:
            chunks.append({
                "id": f"{rel_path}:{block_start}:0",
                "text": content[:MAX_CHUNK_CHARS],
                "metadata": {"source": rel_path, "type": doc_type, "title": block_heading},
            })
    return chunks


def _chunk_markdown(path: Path, rel_path: str, doc_type: str) -> list[dict]:
    """Split at ## headings; oversized sections are split by character window."""
    text = path.read_text(encoding="utf-8")
    sections: list[tuple[str, str]] = []
    heading = path.stem
    buf: list[str] = []

    for line in text.split("\n"):
        if line.startswith("## "):
            if buf:
                sections.append((heading, "\n".join(buf).strip()))
            heading = line[3:].strip()
            buf = [line]
        else:
            buf.append(line)
    if buf:
        sections.append((heading, "\n".join(buf).strip()))

    chunks: list[dict] = []
    for sec_idx, (sec_heading, content) in enumerate(sections):
        if len(content) < MIN_CHUNK_CHARS:
            continue
        base_meta = {"source": rel_path, "type": doc_type, "title": sec_heading}
        if len(content) <= MAX_CHUNK_CHARS:
            chunks.append({"id": f"{rel_path}:{sec_idx}:0",
                           "text": content, "metadata": base_meta})
        else:
            for window, start in enumerate(range(0, len(content), MAX_CHUNK_CHARS)):
                sub_text = content[start:start + MAX_CHUNK_CHARS].strip()
                if len(sub_text) >= MIN_CHUNK_CHARS:
                    chunks.append({"id": f"{rel_path}:{sec_idx}:{window}",
                                   "text": sub_text, "metadata": base_meta})
    return chunks


def main() -> None:
    chroma_host = os.getenv("CHROMA_URL", "localhost")
    chroma = chromadb.HttpClient(host=chroma_host)
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=EMBEDDING_MODEL,
        ),
    )
    _logs.info(f"Collection '{COLLECTION_NAME}' ready (existing docs: {collection.count()})")

    all_chunks: list[dict] = []
    for doc_type, base_dir, pattern in SOURCES:
        if not base_dir.exists():
            _logs.warning(f"[skip] {base_dir} not found")
            continue
        for path in sorted(base_dir.glob(pattern)):
            rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            chunks = (
                _chunk_notebook(path, rel, doc_type)
                if path.suffix == ".ipynb"
                else _chunk_python(path, rel, doc_type)
                if path.suffix == ".py"
                else _chunk_markdown(path, rel, doc_type)
            )
            _logs.info(f"{rel}: {len(chunks)} chunks")
            all_chunks.extend(chunks)

    if not all_chunks:
        _logs.error("No chunks found to index.")
        sys.exit(1)

    _logs.info(f"Upserting {len(all_chunks)} chunks in batches of {BATCH_SIZE}...")
    for start in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[start : start + BATCH_SIZE]
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
        )
        _logs.info(f"[{start + len(batch)}/{len(all_chunks)}] upserted")

    _logs.info(f"Done. Total documents in '{COLLECTION_NAME}': {collection.count()}")


if __name__ == "__main__":
    main()
