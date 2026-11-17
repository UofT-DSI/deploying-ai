from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
import os

# Load secrets from 05_src/.secrets
load_dotenv(Path(__file__).parent.parent / ".secrets")

client = OpenAI(
    base_url='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1',
    api_key='any value',
    default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')}
)

# Read knowledge.txt
text = Path("data/knowledge.txt").read_text()
print(f"Loaded {len(text)} characters")

# Split by Section, each Section is one chunk
chunks = [c.strip() for c in text.split("Section") if c.strip()]
print(f"Split into {len(chunks)} chunks")

# Create ChromaDB with file persistence
chroma = chromadb.PersistentClient(path="./chroma_db")

try:
    chroma.delete_collection("production_ai")
except:
    pass

collection = chroma.create_collection("production_ai")

# Embed each chunk and save
for i, chunk in enumerate(chunks):
    emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=chunk
    ).data[0].embedding

    collection.add(
        ids=[f"chunk-{i}"],
        documents=[chunk],
        metadatas=[{"source": "knowledge.txt"}],
        embeddings=[emb]
    )

print("Done, added", len(chunks), "chunks to ChromaDB")