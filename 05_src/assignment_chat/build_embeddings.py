# build_embeddings.py
# Run this ONCE locally to generate and persist the ChromaDB collection.
# Graders do NOT need to run this — the chroma_db/ folder is committed to the repo.

import os
import json
import re
import chromadb
from chromadb.utils import embedding_functions
from config import MITRE_MD_DIR, CHROMA_DB_DIR, CHROMA_COLLECTION_NAME, OPENAI_API_KEY, GATEWAY_URL, GATEWAY_HEADERS

STIX_FILE = os.path.join(os.path.dirname(__file__), "data", "raw", "enterprise-attack.json")
MAX_TECHNIQUES = 100


def parse_stix(stix_path: str) -> list[dict]:
    """Extract top-level MITRE techniques (T#### only) from STIX JSON."""
    with open(stix_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    techniques = []
    for obj in bundle.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue

        ext_refs = obj.get("external_references", [])
        mitre_ref = next(
            (r for r in ext_refs if r.get("source_name") == "mitre-attack"), None
        )
        if not mitre_ref:
            continue

        ext_id = mitre_ref.get("external_id", "")
        # Only top-level techniques (T#### not T####.###)
        if not re.match(r"^T\d{4}$", ext_id):
            continue

        tactics = [
            phase["phase_name"]
            for phase in obj.get("kill_chain_phases", [])
            if phase.get("kill_chain_name") == "mitre-attack"
        ]

        techniques.append({
            "id": ext_id,
            "name": obj.get("name", ""),
            "description": obj.get("description", ""),
            "tactics": tactics,
        })

    return techniques[:MAX_TECHNIQUES]


def write_markdown(techniques: list[dict]) -> None:
    """Write one markdown file per technique."""
    os.makedirs(MITRE_MD_DIR, exist_ok=True)
    for t in techniques:
        content = f"""# {t['id']} — {t['name']}

## Tactics
{", ".join(t['tactics']) if t['tactics'] else "N/A"}

## Description
{t['description']}
"""
        filepath = os.path.join(MITRE_MD_DIR, f"{t['id']}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"Wrote {len(techniques)} markdown files to {MITRE_MD_DIR}")


def build_chroma(techniques: list[dict]) -> None:
    """Embed technique docs and persist to ChromaDB."""
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        api_base=GATEWAY_URL,
        model_name="text-embedding-3-small",
        default_headers=GATEWAY_HEADERS,
    )

    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

    # Delete existing collection if rebuilding
    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        embedding_function=ef,
    )

    ids, documents, metadatas = [], [], []
    for t in techniques:
        doc_text = f"{t['id']} — {t['name']}\nTactics: {', '.join(t['tactics'])}\n\n{t['description']}"
        ids.append(t["id"])
        documents.append(doc_text)
        metadatas.append({
            "technique_id": t["id"],
            "name": t["name"],
            "tactics": ", ".join(t["tactics"]),
        })

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"Embedded and stored {len(ids)} techniques in ChromaDB at {CHROMA_DB_DIR}")


if __name__ == "__main__":
    print("Parsing STIX file...")
    techniques = parse_stix(STIX_FILE)
    print(f"Found {len(techniques)} top-level techniques.")

    print("Writing markdown files...")
    write_markdown(techniques)

    print("Building ChromaDB...")
    build_chroma(techniques)

    print("Done. Commit the chroma_db/ folder to your repo.")
