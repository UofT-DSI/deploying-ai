from app.core.openai_client import get_client
from app.services.semantic import SemanticStore, load_jsonl

def main():
    oai = get_client()
    print("Got client")
    store = SemanticStore("chroma_store", "course_kb", oai)
    print("Got store")
    docs = load_jsonl("data/course_kb.jsonl")
    print("Loaded docs")
    store.add_documents(docs)
    print(f"Indexed {len(docs)} docs into chroma_store/ collection=course_kb")

if __name__ == "__main__":
    main()