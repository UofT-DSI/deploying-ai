"""Build the persistent ChromaDB index from data/destinations.csv.

Run once:  python 05_src/assignment_chat/build_index.py
The resulting chroma_db/ folder is small and is committed to the repo, so reviewers do not need to re-run this.
"""
import chromadb
import pandas as pd

from config import CHROMA_PATH, COLLECTION_NAME, DATA_CSV, embed, logger


def main():
    df = pd.read_csv(DATA_CSV)

    # One text per destination: this is what gets embedded.
    texts = [
        f"{r['name']}, {r['country']}. {r['description']} Tags: {r['tags'].replace(';', ', ')}. "
        f"Best time: {r['best_season']}."
        for _, r in df.iterrows()
    ]
    embeddings = embed(texts)

    db = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        db.delete_collection(COLLECTION_NAME)  # allow clean re-runs
    except Exception:
        pass
    col = db.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    col.add(
        ids=df["name"].tolist(),
        documents=texts,
        embeddings=embeddings,
        # Metadata is used for structured (lexical-style) filtering before semantic ranking.
        metadatas=[
            {"region": r["region"], "daily_budget_usd": int(r["daily_budget_usd"])}
            for _, r in df.iterrows()
        ],
    )
    logger.info("Indexed %d destinations into %s", col.count(), CHROMA_PATH)


if __name__ == "__main__":
    main()
