from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

ROOT = Path(__file__).resolve().parent
DB = ROOT / "chroma_db"
DATA = ROOT / "data" / "go_transit_info.txt"

def get_collection():
    client = chromadb.PersistentClient(path=str(DB))
    collection = client.get_or_create_collection(
        name="go_transit_knowledge",
        embedding_function=DefaultEmbeddingFunction(),
    )
    return collection

def build_index():
    text = DATA.read_text(encoding="utf-8")
    sections = [part.strip() for part in text.split("\n\n") if part.strip()]
    collection = get_collection()
    collection.upsert(ids=[f"section-{i}" for i in range(len(sections))], documents=sections)
    print(f"Indexed {len(sections)} sections into {DB}")

def search_knowledge(question: str) -> str:
    collection = get_collection()
    if collection.count() == 0:
        return "Knowledge base is empty. Run: python semantic_search.py"
    result = collection.query(query_texts=[question], n_results=min(3, collection.count()))
    docs = result.get("documents", [[]])[0]
    return "\n\n".join(docs) if docs else "No matching documents found."

if __name__ == "__main__":
    build_index()
