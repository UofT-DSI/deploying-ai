from langchain.tools import tool
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from utils.logger import get_logger

_logs = get_logger(__name__)
load_dotenv()
load_dotenv(".secrets")

# Persistent ChromaDB (requirement: no Docker, file persistence)
chroma_client = chromadb.PersistentClient(path="./05_src/assignment_chat/chroma_db")
collection = chroma_client.get_or_create_collection(
    name="sample_reviews",
    embedding_function=OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY", "any_value"),
        model_name="text-embedding-3-small",
        api_base="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
        default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")}
    )
)

class ReviewResult(BaseModel):
    content: str = Field(..., description="Relevant text from the dataset matching the query")

@tool
def semantic_search(query: str, n_results: int = 1) -> list[ReviewResult]:
    """Performs semantic search over the local dataset using ChromaDB."""
    results = collection.query(query_texts=[query], n_results=n_results)
    if not results["documents"] or not results["documents"][0]:
        return []
    return [ReviewResult(content=doc) for doc in results["documents"][0]]

# One-time embedding code (describe in README, do not include in runtime):
# with open("05_src/assignment_chat/data/sample_reviews.txt") as f:
#     lines = [line.strip() for line in f if line.strip()]
# if lines:
#     collection.add(documents=lines, ids=[f"doc_{i}" for i in range(len(lines))])
