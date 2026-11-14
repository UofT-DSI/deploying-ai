"""Rebuild the small, committed course search index from course documents."""

import json
from pathlib import Path

import chromadb
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = (ROOT / "02_activities" / "assignment_2.md", ROOT / "README.md",
           ROOT / "03_instructional_team" / "review" / "README.md")


def sections(path: Path) -> list[tuple[str, str]]:
    heading = path.stem
    collected = []
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            if lines:
                collected.append((f"{path.name}: {heading}", "\n".join(lines)))
            heading = line.lstrip("# ").strip()
            lines = []
        elif line.strip():
            lines.append(line.strip())
    if lines:
        collected.append((f"{path.name}: {heading}", "\n".join(lines)))
    return [(title, text[:1200]) for title, text in collected if len(text) >= 40]


def main() -> None:
    chunks = [item for source in SOURCES for item in sections(source)]
    texts = [text for _, text in chunks]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    tfidf = vectorizer.fit_transform(texts)
    svd = TruncatedSVD(n_components=min(16, len(chunks) - 1), random_state=0)
    embeddings = svd.fit_transform(tfidf)
    model = {"vocabulary": vectorizer.vocabulary_, "idf": vectorizer.idf_.tolist(),
             "components": svd.components_.tolist()}
    (HERE / "search_model.json").write_text(json.dumps(model, separators=(",", ":")), encoding="utf-8")
    client = chromadb.PersistentClient(path=str(HERE / "index"))
    collection = client.get_or_create_collection("course_materials")
    existing = collection.get()["ids"]
    if existing:
        collection.delete(ids=existing)
    collection.add(ids=[f"section-{i}" for i in range(len(chunks))],
                   documents=texts, metadatas=[{"source": title} for title, _ in chunks],
                   embeddings=embeddings.tolist())
    print(f"Indexed {len(chunks)} course sections")


if __name__ == "__main__":
    main()
