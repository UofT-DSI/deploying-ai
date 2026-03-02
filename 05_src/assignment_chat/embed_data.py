import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid

# Load text
with open("./data/sherlock.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Chunk text
def chunk_text(text, size=800):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end
    return chunks

chunks = chunk_text(text)

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Chroma persistent DB
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma"))
collection = client.get_or_create_collection("sherlock")

# Insert chunks
for chunk in chunks:
    emb = model.encode(chunk).tolist()
    collection.add(
        ids=[str(uuid.uuid4())],
        embeddings=[emb],
        documents=[chunk]
    )

client.persist()
print("Embedding complete.")
