from chromadb.config import Settings
import chromadb

def main():
    c = chromadb.PersistentClient(
        path="chroma_store",
        settings=Settings(anonymized_telemetry=False),
    )

    col = c.get_or_create_collection("test_col")  # valid name (>=3 chars)

    # Known-good embedding payload (all python floats)
    emb = [[0.0] * 1536]

    col.add(ids=["doc-1"], documents=["hello"], embeddings=emb)
    print("✅ chroma add ok")

if __name__ == "__main__":
    main()