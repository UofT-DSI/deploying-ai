
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain.tools import tool

# Find the 05_src directory
SRC_DIR = Path(__file__).resolve().parents[2]

# Load course environment settings
load_dotenv(SRC_DIR / ".env")
load_dotenv(SRC_DIR / ".secrets")

# Make course utilities available
sys.path.insert(0, str(SRC_DIR))

from utils.clients import get_client


# Connect to the course API
client = get_client()


# Generate embeddings
def get_embedding(text: str) -> list[float]:
    text = text.replace("\n", " ")

    result = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )

    return result.data[0].embedding


# Create persistent ChromaDB
DB_PATH = Path(__file__).resolve().parent.parent / "chroma_db"

chroma_client = chromadb.PersistentClient(
    path=str(DB_PATH)
)

collection = chroma_client.get_or_create_collection(
    name="fitness_knowledge"
)


# Store fitness documents
def add_knowledge(documents: list[str]) -> None:
    for index, document in enumerate(documents):
        collection.upsert(
            ids=[f"fitness_{index}"],
            documents=[document],
            embeddings=[get_embedding(document)]
        )

@tool
def search_knowledge(query: str, n_results: int = 6) -> str:
    """
    Search the fitness knowledge base for relevant information
    about exercise, muscle growth, recovery, and nutrition.
    """
    query_embedding = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    documents = results.get("documents", [[]])[0]

    if not documents:
        return "No relevant fitness information was found."

    return "\n\n".join(documents)
